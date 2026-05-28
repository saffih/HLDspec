from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hldspec import speckit_readiness as sr


ROOT = Path(__file__).resolve().parents[1]


class _RunStub:
    def __init__(self, *, git_root: Path | None = None, branch: str = "main", dirty: bool = False, help_ok: bool = True):
        self.git_root = git_root
        self.branch = branch
        self.dirty = dirty
        self.help_ok = help_ok
        self.calls: list[list[str]] = []

    def __call__(self, argv, cwd, text, capture_output, check):
        argv = list(argv)
        self.calls.append(argv)
        if argv and argv[0] == "git":
            if "rev-parse" in argv:
                if self.git_root is None:
                    return SimpleNamespace(returncode=1, stdout="", stderr="")
                return SimpleNamespace(returncode=0, stdout=f"{self.git_root}\n", stderr="")
            if "branch" in argv:
                if self.git_root is None:
                    return SimpleNamespace(returncode=1, stdout="", stderr="")
                return SimpleNamespace(returncode=0, stdout=f"{self.branch}\n", stderr="")
            if "status" in argv:
                if self.git_root is None:
                    return SimpleNamespace(returncode=1, stdout="", stderr="")
                return SimpleNamespace(returncode=0, stdout=(" M file.txt\n" if self.dirty else ""), stderr="")
        if argv and argv[0] in {"specify", "spec-kit", "uvx"} and ("--help" in argv or "--version" in argv):
            if self.help_ok:
                return SimpleNamespace(returncode=0, stdout="help\n", stderr="")
            return SimpleNamespace(returncode=1, stdout="", stderr="boom")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


def _which_only(*names: str):
    allowed = set(names)

    def inner(binary: str):
        return f"/mock/{binary}" if binary in allowed else None

    return inner


class SpeckitReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-speckit-readiness-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _report(self, target: Path, *, which=None, run=None):
        return sr.build_speckit_readiness_report(target, which=which, run=run)

    def test_missing_command_and_uninitialized_target_reports_action(self) -> None:
        target = self.root / "target"
        target.mkdir()
        report = self._report(target, which=lambda _: None, run=_RunStub())
        self.assertEqual("ACTION", report["status"])
        self.assertFalse(report["workspace_status"]["initialized"])
        self.assertTrue(any("Install `specify`, `spec-kit`, or `uvx`" in action for action in report["next_actions"]))

    def test_initialized_target_without_command_still_warns_action(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        report = self._report(target, which=lambda _: None, run=_RunStub(git_root=target))
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(report["workspace_status"]["initialized"])
        self.assertIsNone(report["selected_init_command"])
        self.assertIn("Real SpecKit init means `.specify/memory/` exists; `.specify/source/` alone is only the HLDspec mirror.", report["summary"])

    def test_source_mirror_only_is_not_initialized(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "source").mkdir(parents=True)
        report = self._report(target, which=lambda _: None, run=_RunStub(git_root=target))
        self.assertEqual("ACTION", report["status"])
        self.assertFalse(report["workspace_status"]["initialized"])
        self.assertTrue(report["workspace_status"]["source_mirror_exists"])
        self.assertFalse(report["workspace_status"]["memory_dir_exists"])

    def test_real_memory_workspace_is_reported_initialized(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        report = self._report(target, which=lambda _: None, run=_RunStub(git_root=target))
        self.assertTrue(report["workspace_status"]["initialized"])
        self.assertEqual("ACTION", report["status"])
        self.assertIn("Real SpecKit init means `.specify/memory/` exists", report["summary"])

    def test_uvx_fallback_is_reported_when_only_uvx_exists(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        report = self._report(target, which=_which_only("uvx"), run=_RunStub(git_root=target))
        self.assertEqual("uvx-spec-kit", report["selected_init_command"]["label"])
        self.assertTrue(any(item["label"] == "uvx-spec-kit" for item in report["available_init_commands"]))
        self.assertTrue(report["workspace_status"]["initialized"])

    def test_branch_hook_missing_reports_action(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        report = self._report(target, which=lambda _: None, run=_RunStub(git_root=target))
        self.assertEqual("ACTION", report["branch_hook_status"]["status"])
        self.assertIn("Create/switch to the approved feature branch manually before /speckit.specify, or install a before_specify hook later.", report["branch_hook_status"]["next_action"])

    def test_branch_hook_present_reports_pass(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        hook = target / ".specify" / "extensions.yml"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("before_specify: true\n", encoding="utf-8")
        report = self._report(target, which=lambda _: None, run=_RunStub(git_root=target))
        self.assertEqual("PASS", report["branch_hook_status"]["status"])

    def test_report_does_not_claim_hldspec_creates_specs_spec_md(self) -> None:
        target = self.root / "target"
        report = self._report(target, which=lambda _: None, run=_RunStub())
        text = sr.summarize_speckit_readiness(report)
        self.assertNotIn("specs/<feature>/spec.md", text)
        self.assertNotIn("HLDspec creates specs/<feature>/spec.md", text)

    def test_report_mentions_real_spec_init_not_mirror_only(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "source").mkdir(parents=True)
        report = self._report(target, which=lambda _: None, run=_RunStub(git_root=target))
        text = sr.summarize_speckit_readiness(report)
        self.assertIn("Real SpecKit init means `.specify/memory/` exists; `.specify/source/` alone is only the HLDspec mirror.", text)

    def test_cli_speckit_doctor_prints_status_and_next_actions(self) -> None:
        target = self.root / "target"
        target.mkdir()
        git = self.root / "git"
        git.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
        git.chmod(0o755)
        env = os.environ.copy()
        env["PATH"] = str(self.root)
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_agent_session.py"),
                "speckit-doctor",
                "--target",
                str(target),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("STATUS:", result.stdout)
        self.assertIn("Next actions:", result.stdout)
        self.assertIn("Branch hook/manual branch path ready:", result.stdout)
        self.assertIn("real SpecKit init", result.stdout)


if __name__ == "__main__":
    unittest.main()
