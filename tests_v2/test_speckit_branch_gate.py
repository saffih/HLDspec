from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hldspec import speckit_branch_gate as bg


class _RunStub:
    def __init__(self, *, git_root: Path | None, branch: str = "main") -> None:
        self.git_root = git_root
        self.branch = branch
        self.calls: list[list[str]] = []

    def __call__(self, argv, cwd, text, capture_output, check):
        argv = list(argv)
        self.calls.append(argv)
        if not argv or argv[0] != "git" or self.git_root is None:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if "rev-parse" in argv and "--show-toplevel" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.git_root}\n", stderr="")
        if "branch" in argv and "--show-current" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.branch}\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


class _NoCallRun:
    def __call__(self, *args, **kwargs):
        raise AssertionError("git must not be executed for this case")


class SpeckitBranchGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-branch-gate-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _target(self, name: str = "target") -> Path:
        target = self.root / name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _write_spec(self, target: Path, branch: str, *, spec: bool = True, plan: str | None = None, tasks: str | None = None) -> Path:
        spec_dir = target / "specs" / branch
        spec_dir.mkdir(parents=True, exist_ok=True)
        if spec:
            (spec_dir / "spec.md").write_text(f"# Spec for {branch}\n", encoding="utf-8")
        if plan is not None:
            (spec_dir / "plan.md").write_text(plan, encoding="utf-8")
        if tasks is not None:
            (spec_dir / "tasks.md").write_text(tasks, encoding="utf-8")
        return spec_dir

    # ------------------------------------------------------------------
    # Workspace root guard
    # ------------------------------------------------------------------

    def test_reserved_workspace_root_is_rejected_without_git_calls(self) -> None:
        target = self._target("target") / "firstrun"
        target.mkdir(parents=True, exist_ok=True)

        report = bg.write_speckit_branch_gate_report(target, run=_NoCallRun())

        self.assertEqual(bg.STATUS_WORKSPACE_ROOT_INVALID, report["gate_status"])
        self.assertEqual(bg.SAFETY_BLOCKED, report["safety_status"])
        self.assertEqual({}, report["report_paths"])

    def test_missing_target_does_not_call_git_or_write_reports(self) -> None:
        target = self.root / "missing"

        report = bg.write_speckit_branch_gate_report(target, run=_NoCallRun())

        self.assertEqual(bg.STATUS_NO_GIT, report["gate_status"])
        self.assertEqual({}, report["report_paths"])
        self.assertFalse(target.exists())

    # ------------------------------------------------------------------
    # Git/branch resolution
    # ------------------------------------------------------------------

    def test_no_git_repo_reports_no_git(self) -> None:
        target = self._target()

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=None))

        self.assertEqual(bg.STATUS_NO_GIT, report["gate_status"])
        self.assertEqual(bg.SAFETY_ACTION, report["safety_status"])

    # ------------------------------------------------------------------
    # Before /speckit.specify
    # ------------------------------------------------------------------

    def test_ready_for_speckit_specify_on_base_branch(self) -> None:
        target = self._target()

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(bg.STATUS_READY_FOR_SPECKIT_SPECIFY, report["gate_status"])
        self.assertEqual(bg.SAFETY_PASS, report["safety_status"])
        self.assertFalse(report["is_feature_branch"])
        report_path = (target / ".hldspec" / "sync" / bg.REPORT_JSON).resolve()
        self.assertTrue(report_path.is_file())
        persisted = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(str(report_path), persisted["report_paths"]["json"])

    def test_ready_for_speckit_specify_on_feature_branch_without_specs(self) -> None:
        target = self._target()

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertEqual(bg.STATUS_READY_FOR_SPECKIT_SPECIFY, report["gate_status"])
        self.assertEqual(bg.SAFETY_PASS, report["safety_status"])
        self.assertTrue(report["is_feature_branch"])

    # ------------------------------------------------------------------
    # After /speckit.specify
    # ------------------------------------------------------------------

    def test_speckit_branch_created_when_spec_dir_matches_branch(self) -> None:
        target = self._target()
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertEqual(bg.STATUS_SPECKIT_BRANCH_CREATED, report["gate_status"])
        self.assertEqual(bg.SAFETY_PASS, report["safety_status"])
        self.assertTrue(report["spec_md_exists"])
        self.assertTrue(report["plan_md_exists"])
        self.assertTrue(report["tasks_md_exists"])
        self.assertEqual([], report["blockers"])

    # ------------------------------------------------------------------
    # Branch / spec directory mismatch
    # ------------------------------------------------------------------

    def test_branch_spec_dir_mismatch_blocks(self) -> None:
        target = self._target()
        self._write_spec(target, "001-feature")

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=target, branch="002-other"))

        self.assertEqual(bg.STATUS_BRANCH_SPEC_DIR_MISMATCH, report["gate_status"])
        self.assertEqual(bg.SAFETY_BLOCKED, report["safety_status"])
        self.assertIn("001-feature", report["blockers"][0])

    # ------------------------------------------------------------------
    # Missing spec.md
    # ------------------------------------------------------------------

    def test_missing_spec_md_blocks(self) -> None:
        target = self._target()
        self._write_spec(target, "001-feature", spec=False, plan="plan body")

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertEqual(bg.STATUS_SPEC_MISSING, report["gate_status"])
        self.assertEqual(bg.SAFETY_BLOCKED, report["safety_status"])
        self.assertFalse(report["spec_md_exists"])

    # ------------------------------------------------------------------
    # Stale artifact from another branch
    # ------------------------------------------------------------------

    def test_stale_artifact_from_other_branch_blocks(self) -> None:
        target = self._target()
        self._write_spec(target, "001-feature", plan="shared plan body")
        self._write_spec(target, "002-other", spec=False, plan="shared plan body")

        report = bg.write_speckit_branch_gate_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertEqual(bg.STATUS_STALE_ARTIFACT_FROM_OTHER_BRANCH, report["gate_status"])
        self.assertEqual(bg.SAFETY_BLOCKED, report["safety_status"])
        self.assertEqual("plan.md", report["stale_artifact"]["file"])
        self.assertEqual("002-other", report["stale_artifact"]["other_branch"])


if __name__ == "__main__":
    unittest.main()
