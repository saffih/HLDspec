from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hldspec import speckit_operator_state as sos


ROOT = Path(__file__).resolve().parents[1]


class _RunStub:
    def __init__(self, *, git_root: Path | None = None, branch: str = "main", dirty: bool = False):
        self.git_root = git_root
        self.branch = branch
        self.dirty = dirty
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
        if argv[:2] in (["specify", "--help"], ["specify", "--version"], ["spec-kit", "--help"], ["spec-kit", "--version"]):
            return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        if argv[:6] == ["uvx", "--from", sos.sr.sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "--help"]:
            return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        if argv[:6] == ["uvx", "--from", sos.sr.sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "--version"]:
            return SimpleNamespace(returncode=0, stdout="ok\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


def _which_only(*names: str):
    allowed = set(names)

    def inner(binary: str):
        return f"/mock/{binary}" if binary in allowed else None

    return inner


class SpeckitOperatorStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-speckit-operator-state-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _report(self, target: Path | None, *, which=None, run=None):
        return sos.build_speckit_operator_state_report(target, which=which, run=run)

    def test_no_target_reports_action(self) -> None:
        report = self._report(None)
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("NO_TARGET", report["state"])
        self.assertIn("Choose or create a target workspace path", report["next_safe_action"])
        self.assertTrue(report["evidence"])
        self.assertIn("SpecKit Doctor is readiness/preflight only", report["doctor_note"])

    def test_missing_target_path_reports_action(self) -> None:
        target = self.root / "missing-target"
        report = self._report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("TARGET_MISSING", report["state"])
        self.assertIn("Create or choose the target workspace path", report["next_safe_action"])

    def test_no_git_repo_reports_action(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / ".hldspec" / "source_package").mkdir(parents=True)
        report = self._report(target, which=_which_only("specify"), run=_RunStub())
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("TARGET_NOT_GIT", report["state"])
        self.assertIn("git workspace", report["next_safe_action"])

    def test_dirty_tree_reports_action(self) -> None:
        target = self.root / "target"
        (target / ".hldspec" / "source_package").mkdir(parents=True)
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target, dirty=True))
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("TARGET_DIRTY", report["state"])
        self.assertIn("Clean, commit, or stash the target tree", report["next_safe_action"])

    def test_source_package_missing_reports_action(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("SOURCE_PACKAGE_MISSING", report["state"])
        self.assertIn("source-package generation", report["next_safe_action"])

    def test_specify_source_only_reports_not_initialized(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".hldspec" / "source_package").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("SPECKIT_NOT_INITIALIZED", report["state"])
        self.assertIn(".specify/memory", report["next_safe_action"])

    def test_ready_workspace_reports_ready_for_specify(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        (target / ".hldspec" / "source_package").mkdir(parents=True)
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        self.assertEqual("PASS", report["status"])
        self.assertEqual("READY_FOR_SPECIFY", report["state"])
        self.assertTrue(report["next_safe_action"])
        self.assertTrue(report["evidence"])
        self.assertTrue(report["source_facts_used"])
        self.assertEqual("PASS", report["readiness_report"]["status"])
        self.assertIn("readiness/preflight only", report["doctor_note"])

    def test_summary_is_boundary_safe_and_devin_free(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        (target / ".hldspec" / "source_package").mkdir(parents=True)
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        text = sos.summarize_speckit_operator_state(report)
        self.assertIn("STATUS: PASS", text)
        self.assertIn("State: READY_FOR_SPECIFY", text)
        self.assertIn("Next safe action:", text)
        self.assertIn("SpecKit Doctor is readiness/preflight only", text)
        self.assertNotIn("go/stop", text)
        self.assertNotIn("tmux", text)
        self.assertNotIn("session", text)
        self.assertNotIn("Devin", text)

    def test_cli_operator_state_prints_summary(self) -> None:
        target = self.root / "missing-target"
        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_agent_session.py"),
                "operator-state",
                "--target",
                str(target),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertNotEqual(0, result.returncode)
        self.assertIn("STATUS: ACTION", result.stdout)
        self.assertIn("State: TARGET_MISSING", result.stdout)
        self.assertIn("Next safe action:", result.stdout)


if __name__ == "__main__":
    unittest.main()
