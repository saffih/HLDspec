from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hldspec import git_lifecycle as gl


class _RunStub:
    def __init__(
        self,
        *,
        git_root: Path | None,
        branch: str = "001-feature",
        porcelain: str = "",
        head: str = "abc123",
    ) -> None:
        self.git_root = git_root
        self.branch = branch
        self.porcelain = porcelain
        self.head = head
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
        if "rev-parse" in argv and "HEAD" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.head}\n", stderr="")
        if "symbolic-ref" in argv:
            return SimpleNamespace(returncode=0, stdout="origin/main\n", stderr="")
        if "status" in argv:
            return SimpleNamespace(returncode=0, stdout=self.porcelain, stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


class GitLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-git-lifecycle-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _target(self, name: str = "target") -> Path:
        target = self.root / name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _hook(self, target: Path) -> None:
        path = target / ".specify" / "extensions.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("before_specify: true\n", encoding="utf-8")

    def test_no_git_reports_no_git_action_and_writes_report(self) -> None:
        target = self._target()
        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=None))

        self.assertEqual(gl.STATUS_NO_GIT, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_ACTION, report["safety_status"])
        report_path = (target / ".hldspec" / "sync" / gl.REPORT_JSON).resolve()
        self.assertTrue(report_path.is_file())
        persisted = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(str(report_path), persisted["report_paths"]["json"])
        self.assertFalse(report["merge_allowed"])

    def test_missing_target_does_not_create_target_or_report_dirs(self) -> None:
        target = self.root / "missing"
        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=None))

        self.assertEqual(gl.STATUS_NO_GIT, report["lifecycle_status"])
        self.assertFalse(target.exists())
        self.assertEqual({}, report["report_paths"])

    def test_clean_branch_with_hook_policy_is_branch_ready_but_not_enforced(self) -> None:
        target = self._target()
        self._hook(target)

        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=target))

        self.assertEqual(gl.STATUS_BRANCH_READY, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_PASS, report["safety_status"])
        self.assertEqual("PRESENT_UNVERIFIED", report["hook_policy_evidence"]["state"])
        self.assertIn("not proof", report["hook_policy_evidence"]["note"])

    def test_missing_hook_and_manual_equivalent_blocks(self) -> None:
        target = self._target()

        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=target))

        self.assertEqual(gl.STATUS_BRANCH_POLICY_MISSING, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_BLOCKED, report["safety_status"])

    def test_approved_manual_branch_equivalent_allows_branch_ready(self) -> None:
        target = self._target()
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "git_lifecycle_manual_branch_approval.json").write_text(
            json.dumps({"status": "APPROVED", "branch": "001-feature"}),
            encoding="utf-8",
        )

        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=target))

        self.assertEqual(gl.STATUS_BRANCH_READY, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_PASS, report["safety_status"])
        self.assertEqual("APPROVED", report["manual_branch_equivalent_evidence"]["state"])

    def test_dirty_product_files_before_phase_block(self) -> None:
        target = self._target()
        self._hook(target)

        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=target, porcelain=" M app.py\n"))

        self.assertEqual(gl.STATUS_DIRTY_BEFORE_PHASE, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_BLOCKED, report["safety_status"])
        self.assertIn("app.py", report["product_dirty_files"])

    def test_dirty_phase_artifacts_require_commit(self) -> None:
        target = self._target()
        self._hook(target)

        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=target, porcelain=" M specs/001/spec.md\n"))

        self.assertEqual(gl.STATUS_COMMIT_REQUIRED, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_BLOCKED, report["safety_status"])
        self.assertIn("specs/001/spec.md", report["phase_dirty_files"])

    def test_clean_existing_phase_artifacts_are_commit_recorded(self) -> None:
        target = self._target()
        self._hook(target)
        spec = target / "specs" / "001-feature" / "spec.md"
        spec.parent.mkdir(parents=True, exist_ok=True)
        spec.write_text("# Spec\n", encoding="utf-8")

        report = gl.write_git_lifecycle_report(target, run=_RunStub(git_root=target))

        self.assertEqual(gl.STATUS_COMMIT_RECORDED, report["lifecycle_status"])
        self.assertEqual(gl.SAFETY_PASS, report["safety_status"])


if __name__ == "__main__":
    unittest.main()
