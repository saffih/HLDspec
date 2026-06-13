"""Tests for the `hldspec refresh-target` <-> next-feature run-card integration.

Covers: NEEDS_CONSTITUTION recommends refresh-target (not /speckit.constitution
blindly), the recommendation is read-only, advisory recommendations for a
missing helper bootstrap and an unmanaged constitution, and that once support
files are current the run card proceeds to the normal next SpecKit action.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hldspec import next_feature_agents_md as nfa
from hldspec import next_feature_readiness as nfr
from hldspec import refresh_target as rt


class _RunStub:
    def __init__(self, *, git_root: Path | None, branch: str = "main", porcelain: str = "") -> None:
        self.git_root = git_root
        self.branch = branch
        self.porcelain = porcelain

    def __call__(self, argv, cwd, text, capture_output, check):
        argv = list(argv)
        if not argv or argv[0] != "git" or self.git_root is None:
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if "rev-parse" in argv and "--show-toplevel" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.git_root}\n", stderr="")
        if "branch" in argv and "--show-current" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.branch}\n", stderr="")
        if "rev-parse" in argv and "HEAD" in argv:
            return SimpleNamespace(returncode=0, stdout="abc123\n", stderr="")
        if "symbolic-ref" in argv:
            return SimpleNamespace(returncode=0, stdout="origin/main\n", stderr="")
        if "status" in argv:
            return SimpleNamespace(returncode=0, stdout=self.porcelain, stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


class RefreshTargetIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-next-feature-refresh-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _target(self, name: str = "target") -> Path:
        target = self.root / name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _init_speckit(self, target: Path, *, constitution_text: str | None = None) -> None:
        memory = target / ".specify" / "memory"
        memory.mkdir(parents=True, exist_ok=True)
        if constitution_text is not None:
            (memory / "constitution.md").write_text(constitution_text, encoding="utf-8")

    def _run(self, target: Path) -> _RunStub:
        return _RunStub(git_root=target, branch="main")

    # 1. missing constitution causes run card to recommend refresh-target dry-run
    def test_missing_constitution_recommends_refresh_target_dry_run(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=None)

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        self.assertEqual(nfr.PHASE_NEEDS_CONSTITUTION, report["phase"])
        self.assertIsNone(report["speckit_next_action"])
        self.assertIn(f"python3 {nfr.REFRESH_TARGET_SCRIPT}", report["next_safe_action"])
        self.assertIn("--dry-run", report["next_safe_action"])
        self.assertNotIn("/speckit.constitution", report["next_safe_action"])
        # The safer refresh-target path is named explicitly over blind /speckit.constitution.
        self.assertIn("/speckit.constitution", report["why_now"])

    # 2. refresh-target recommendation does not run or apply anything
    def test_recommendation_does_not_write_anything(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=None)

        nfr.build_next_feature_readiness_report(target, run=self._run(target))

        self.assertFalse((target / ".specify" / "memory" / "constitution.md").exists())
        sync = rt.control_paths.resolve_control_sync_dir(target, create=False)
        self.assertFalse((sync / nfa.BOOTSTRAP_FILE).exists())

    # Also check do-not-run-yet / report-back are tailored for this phase.
    def test_needs_constitution_do_not_run_yet_and_report_back(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=None)

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        for cmd in ("/speckit.specify", "/speckit.plan", "/speckit.tasks", "/speckit.implement"):
            self.assertIn(cmd, report["do_not_run_yet"])
        self.assertIn("--apply", report["do_not_run_yet"])
        self.assertIn("dry-run", report["report_back"])
        self.assertIn("conflict", report["report_back"])

    # 3. stale/missing managed helper file causes advisory refresh-target recommendation
    def test_missing_helper_bootstrap_is_advisory_only(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=rt.full_constitution_template())

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        # Phase proceeds normally; the missing helper is advisory, not blocking.
        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])
        advisory_text = " ".join(report["advisory_actions"])
        self.assertIn(nfa.BOOTSTRAP_FILE, advisory_text)
        self.assertIn(f"python3 {nfr.REFRESH_TARGET_SCRIPT}", advisory_text)
        self.assertIn("--dry-run", advisory_text)
        self.assertEqual(rt.MISSING_CAN_CREATE, report["refresh_target_status"]["helper"]["classification"])

    # 4. unowned/edited constitution produces review-required advisory, not overwrite
    def test_unmanaged_constitution_is_review_required_and_unmodified(self) -> None:
        target = self._target()
        custom_text = "# Our hand-written constitution\n\nNo HLDspec markers here.\n"
        self._init_speckit(target, constitution_text=custom_text)

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        self.assertTrue(report["refresh_target_status"]["constitution_review_required"])
        advisory_text = " ".join(report["advisory_actions"])
        self.assertIn("managed markers", advisory_text)
        self.assertIn(f"python3 {nfr.REFRESH_TARGET_SCRIPT}", advisory_text)
        # Read-only: file untouched and phase proceeds normally.
        self.assertEqual(custom_text, (target / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8"))
        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])

    # 5. once constitution exists and support files are current, run card proceeds normally
    def test_current_support_files_no_advisory_normal_next_action(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=rt.full_constitution_template())
        nfa.write_next_feature_agents_md(target)

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        self.assertEqual([], report["advisory_actions"])
        self.assertEqual(rt.OWNED_BY_SPECKIT_SAFE_TO_REFRESH, report["refresh_target_status"]["constitution"]["classification"])
        self.assertEqual(rt.OWNED_BY_HLDSPEC_SAFE_TO_UPDATE, report["refresh_target_status"]["helper"]["classification"])
        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])

    # 6. output still includes one next safe action only
    def test_next_safe_action_is_a_single_string(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=None)

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        self.assertIsInstance(report["next_safe_action"], str)
        self.assertNotIsInstance(report["next_safe_action"], (list, tuple))

    # 7. no product files/specs/plans/tasks are candidates for mutation
    def test_refresh_target_status_paths_stay_within_managed_set(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution_text=None)

        report = nfr.build_next_feature_readiness_report(target, run=self._run(target))

        status = report["refresh_target_status"]
        self.assertEqual(str(rt.CONSTITUTION_RELPATH), status["constitution"]["path"])
        helper_path = status["helper"]["path"]
        self.assertFalse(helper_path.startswith("specs/"))
        self.assertFalse(helper_path.startswith("src/"))
        self.assertIn(nfa.BOOTSTRAP_FILE, helper_path)


if __name__ == "__main__":
    unittest.main()
