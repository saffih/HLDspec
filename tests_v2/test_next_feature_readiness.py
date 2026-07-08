from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from hldspec import hld_source_package as sp
from hldspec import model_routing as mr
from hldspec import next_feature_readiness as nfr


class _RunStub:
    def __init__(
        self,
        *,
        git_root: Path | None,
        branch: str = "main",
        porcelain: str = "",
    ) -> None:
        self.git_root = git_root
        self.branch = branch
        self.porcelain = porcelain
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
            return SimpleNamespace(returncode=0, stdout="abc123\n", stderr="")
        if "symbolic-ref" in argv:
            return SimpleNamespace(returncode=0, stdout="origin/main\n", stderr="")
        if "status" in argv:
            return SimpleNamespace(returncode=0, stdout=self.porcelain, stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


class _NoCallRun:
    def __call__(self, *args, **kwargs):
        raise AssertionError("git must not be executed for this case")


class NextFeatureReadinessTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-next-feature-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _target(self, name: str = "target") -> Path:
        target = self.root / name
        target.mkdir(parents=True, exist_ok=True)
        return target

    def _init_speckit(self, target: Path, *, constitution: bool = True) -> None:
        memory = target / ".specify" / "memory"
        memory.mkdir(parents=True, exist_ok=True)
        if constitution:
            (memory / "constitution.md").write_text("# Constitution\n", encoding="utf-8")

    def _hook(self, target: Path) -> None:
        path = target / ".specify" / "extensions.yml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("before_specify: true\n", encoding="utf-8")

    def _write_spec(
        self,
        target: Path,
        branch: str,
        *,
        spec_text: str = "# Spec\n",
        plan: str | None = None,
        tasks: str | None = None,
        analyze: str | None = None,
    ) -> Path:
        spec_dir = target / "specs" / branch
        spec_dir.mkdir(parents=True, exist_ok=True)
        (spec_dir / "spec.md").write_text(spec_text, encoding="utf-8")
        if plan is not None:
            (spec_dir / "plan.md").write_text(plan, encoding="utf-8")
        if tasks is not None:
            (spec_dir / "tasks.md").write_text(tasks, encoding="utf-8")
        if analyze is not None:
            (spec_dir / "analyze_report.md").write_text(analyze, encoding="utf-8")
        return spec_dir

    # ------------------------------------------------------------------
    # Boundary / read-only guards
    # ------------------------------------------------------------------

    def test_reserved_workspace_root_is_rejected_without_git_calls(self) -> None:
        target = self._target("target") / "firstrun"
        target.mkdir(parents=True, exist_ok=True)

        report = nfr.write_next_feature_readiness_report(target, run=_NoCallRun())

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        self.assertEqual(nfr.SAFETY_BLOCKED, report["safety_status"])
        self.assertEqual({}, report["report_paths"])
        self.assertFalse(report["merge_allowed"])

    def test_missing_target_does_not_call_git_or_write_reports(self) -> None:
        target = self.root / "missing"

        report = nfr.write_next_feature_readiness_report(target, run=_NoCallRun())

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        self.assertEqual({}, report["report_paths"])
        self.assertFalse(target.exists())

    # ------------------------------------------------------------------
    # SpecKit init / constitution
    # ------------------------------------------------------------------

    def test_missing_speckit_init_reports_needs_init(self) -> None:
        target = self._target()

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        self.assertEqual(nfr.SAFETY_ACTION, report["safety_status"])
        self.assertFalse(report["merge_allowed"])
        report_path = (target / ".hldspec" / "sync" / nfr.REPORT_JSON).resolve()
        self.assertTrue(report_path.is_file())
        persisted = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(str(report_path), persisted["report_paths"]["json"])

    def test_missing_constitution_reports_needs_constitution(self) -> None:
        target = self._target()
        self._init_speckit(target, constitution=False)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_NEEDS_CONSTITUTION, report["phase"])
        self.assertEqual(nfr.SAFETY_ACTION, report["safety_status"])
        self.assertFalse(report["constitution_exists"])
        self.assertFalse(report["merge_allowed"])

    # ------------------------------------------------------------------
    # Setup readiness (init / hooks / branch / constitution)
    # ------------------------------------------------------------------

    # 1. missing .specify/ -> SPECKIT_INIT_MISSING, no /speckit.specify.
    def test_missing_specify_dir_is_init_missing_and_not_specify(self) -> None:
        target = self._target()

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        self.assertEqual(nfr.SPECKIT_INIT_MISSING, report["speckit_init_status"])
        self.assertEqual(nfr.SPECKIT_INIT_MISSING, report["setup_readiness"]["speckit_init_status"])
        setup = report["setup_readiness"]
        self.assertFalse(setup["specify_dir_exists"])
        self.assertFalse(setup["memory_dir_exists"])
        self.assertNotIn("refresh-target", report["next_safe_action"])
        self.assertNotIn("/speckit.specify", report["next_safe_action"])
        self.assertEqual(report["setup_next_action"], report["next_safe_action"])
        if setup["recommended_init_command"]:
            self.assertIn(setup["recommended_init_command"], report["next_safe_action"])
        else:
            self.assertIn("does not invent a command", report["next_safe_action"])

    # 2. missing .specify/memory/ -> SPECKIT_INIT_INCOMPLETE.
    def test_missing_memory_dir_is_init_incomplete(self) -> None:
        target = self._target()
        (target / ".specify").mkdir(parents=True, exist_ok=True)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        self.assertEqual(nfr.SPECKIT_INIT_INCOMPLETE, report["speckit_init_status"])
        setup = report["setup_readiness"]
        self.assertTrue(setup["specify_dir_exists"])
        self.assertFalse(setup["memory_dir_exists"])
        self.assertIn("Complete SpecKit init", report["setup_next_action"])
        self.assertNotIn("/speckit.specify", report["next_safe_action"])
        self.assertIn(".specify/memory/", report["blockers"][0])

    # 5. hooks unknown when there is no authoritative hook convention.
    def test_hooks_unknown_when_no_authoritative_convention(self) -> None:
        target = self._target()
        self._init_speckit(target)  # constitution present, no hook file at all

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_UNKNOWN, report["hooks_status"])
        self.assertEqual(nfr.HOOKS_UNKNOWN, report["setup_readiness"]["hooks_status"])
        # Unknown does not block and adds no hook advisory (a helper-bootstrap
        # advisory is unrelated and allowed).
        self.assertFalse(any("HOOKS" in item for item in report["advisory_actions"]))
        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])

    def test_hooks_unknown_when_specify_dir_missing(self) -> None:
        target = self._target()

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_UNKNOWN, report["setup_readiness"]["hooks_status"])
        self.assertEqual([], report["advisory_actions"])

    # 6. hooks ready when authoritative convention file present and valid.
    def test_hooks_ready_when_authoritative_convention_present(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_READY, report["setup_readiness"]["hooks_status"])
        self.assertFalse(any("HOOKS_MISSING" in item for item in report["advisory_actions"]))

    # 7. hooks missing when convention file present but misconfigured.
    def test_hooks_missing_when_convention_present_but_misconfigured(self) -> None:
        target = self._target()
        self._init_speckit(target)
        hook = target / ".specify" / "extensions.yml"
        hook.write_text("before_specify: creates specs/<feature>/spec.md\n", encoding="utf-8")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_MISSING, report["setup_readiness"]["hooks_status"])
        self.assertTrue(any("HOOKS_MISSING" in item for item in report["advisory_actions"]))
        # Still advisory -- does not block the normal next SpecKit action.
        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])

    # ------------------------------------------------------------------
    # Specify mirror freshness (pre-specify gate)
    # ------------------------------------------------------------------

    _MIRROR_HLD = "# HLD\n\n## HLD-001 - Demo\n\nHLD-ID: HLD-001\n\nText.\n"

    def _build_package(self, target: Path) -> None:
        src = target / "SourceHLD.md"
        src.write_text(self._MIRROR_HLD, encoding="utf-8")
        sp.build_source_package_content(
            target, self._MIRROR_HLD, hld_source_ref=str(src), layout="new"
        )

    def test_stale_specify_mirror_blocks_specify_phase(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._build_package(target)
        _, mirror_dir = sp.source_package_paths(target, layout="new")
        (mirror_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).write_text(
            "stale\n", encoding="utf-8"
        )

        report = nfr.write_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="main")
        )

        self.assertEqual(nfr.PHASE_SOURCE_MIRROR_STALE, report["phase"])
        self.assertEqual(nfr.SAFETY_BLOCKED, report["safety_status"])
        self.assertIsNone(report["speckit_next_action"])
        self.assertTrue(any("mirror" in b.lower() for b in report["blockers"]))
        self.assertNotIn("/speckit.specify", report["next_safe_action"])

    def test_fresh_specify_mirror_still_ready_for_specify(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._build_package(target)

        report = nfr.write_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="main")
        )

        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])

    def test_setup_readiness_rendered_in_run_card(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))
        rendered = nfr.render_next_feature_readiness_report(report)

        self.assertIn("## Setup readiness", rendered)
        self.assertIn("SpecKit init status: `SPECKIT_INIT_READY`", rendered)
        self.assertIn("HOOKS_READY", rendered)
        self.assertIn(".specify/ exists: `true`", rendered)
        self.assertIn(".specify/memory/ exists: `true`", rendered)

    # 8 + 9. no code path writes .git/hooks or mutates git config.
    def test_setup_readiness_does_not_run_speckit_install_hooks_or_mutate_git(self) -> None:
        target = self._target()
        self._init_speckit(target)
        (target / ".git" / "hooks").mkdir(parents=True, exist_ok=True)

        run = _RunStub(git_root=target, branch="main")
        nfr.build_next_feature_readiness_report(target, run=run)

        # Only read-only git plumbing commands are issued -- never config/hook/init/mutation.
        mutating = {"commit", "push", "checkout", "init", "merge", "reset", "config", "hook"}
        for argv in run.calls:
            self.assertEqual("git", argv[0])
            self.assertTrue(mutating.isdisjoint(argv), argv)
        # No hook files were installed under .git/hooks or .specify/.
        self.assertEqual([], list((target / ".git" / "hooks").iterdir()))
        self.assertFalse((target / ".specify" / "extensions.yml").exists())
        self.assertFalse((target / ".specify" / "hooks.yml").exists())

    # 12. run card still has exactly one main next safe action (a single string).
    def test_run_card_has_single_next_safe_action(self) -> None:
        target = self._target()
        self._init_speckit(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertIsInstance(report["next_safe_action"], str)
        self.assertNotIsInstance(report["next_safe_action"], (list, tuple))

    # ------------------------------------------------------------------
    # Before /speckit.specify
    # ------------------------------------------------------------------

    def test_clean_initialized_target_on_base_branch_is_ready_for_specify(self) -> None:
        target = self._target()
        self._init_speckit(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual(nfr.SAFETY_PASS, report["safety_status"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])
        self.assertFalse(report["merge_allowed"])

    # ------------------------------------------------------------------
    # SpecKit run card fields (recommended model, why now, do not run yet,
    # report back)
    # ------------------------------------------------------------------

    def test_run_card_fields_are_present_for_every_phase(self) -> None:
        target = self._target()
        self._init_speckit(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertIn(report["recommended_model"], (mr.MODEL_ROUTINE, mr.MODEL_DEFAULT, mr.MODEL_STRONG, mr.MODEL_CRITICAL))
        self.assertTrue(report["why_now"])
        self.assertEqual(nfr.DO_NOT_RUN_YET, report["do_not_run_yet"])
        self.assertIn(str(target.resolve()), report["report_back"])
        self.assertIn("scripts/next_feature_readiness_report.py", report["report_back"])

    def test_render_produces_speckit_run_card_with_required_sections(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))
        rendered = nfr.render_next_feature_readiness_report(report)

        self.assertTrue(rendered.startswith("# SpecKit Run Card"))
        for section in (
            "## Phase",
            "## Evidence",
            "## Missing",
            "## Blockers",
            "## Next safe action",
            "## Command to run",
            "## Recommended model",
            "## Why now",
            "## Do not run yet",
            "## Report back",
        ):
            self.assertIn(section, rendered)

    # ------------------------------------------------------------------
    # Spec/branch binding
    # ------------------------------------------------------------------

    def test_feature_branch_with_matching_spec_is_bound_and_ready_for_plan(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertIn(nfr.PHASE_SPEC_BRANCH_BOUND, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_PLAN, report["phase"])
        self.assertEqual(nfr.SAFETY_PASS, report["safety_status"])
        self.assertFalse(report["merge_allowed"])

    def test_spec_with_unresolved_clarification_marker_needs_clarify(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", spec_text="# Spec\n\n[NEEDS CLARIFICATION: what auth provider?]\n")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertEqual(nfr.PHASE_NEEDS_CLARIFY_OR_CHECKLIST, report["phase"])
        self.assertEqual(nfr.SAFETY_ACTION, report["safety_status"])
        self.assertTrue(any("NEEDS CLARIFICATION" in item for item in report["blockers"]))

    # ------------------------------------------------------------------
    # Plan / tasks / analyze ladder
    # ------------------------------------------------------------------

    def test_plan_present_tasks_missing_is_ready_for_tasks(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertIn(nfr.PHASE_PLAN_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_TASKS, report["phase"])
        self.assertEqual(nfr.SAFETY_PASS, report["safety_status"])

    def test_tasks_present_without_analyze_evidence_is_ready_for_analyze(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertIn(nfr.PHASE_TASKS_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_ANALYZE, report["phase"])
        self.assertEqual(nfr.SAFETY_PASS, report["safety_status"])

    # ------------------------------------------------------------------
    # Implementation phase
    # ------------------------------------------------------------------

    def test_analyze_done_clean_tree_is_ready_for_implement(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        self.assertIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_IMPLEMENT, report["phase"])
        self.assertEqual(nfr.SAFETY_PASS, report["safety_status"])
        self.assertFalse(report["merge_allowed"])

    def test_implementation_dirty_files_without_evidence_require_review(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")

        report = nfr.write_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature", porcelain=" M app.py\n")
        )

        self.assertEqual(nfr.PHASE_IMPLEMENTATION_REVIEW_REQUIRED, report["phase"])
        self.assertEqual(nfr.SAFETY_ACTION, report["safety_status"])
        self.assertIn("app.py", "\n".join(report["blockers"]))
        self.assertFalse(report["merge_allowed"])

    def test_implementation_dirty_files_with_test_evidence_is_ready_for_commit(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / nfr.EXECUTION_EVIDENCE_FILE).write_text(
            json.dumps({"status": nfr.EVIDENCE_TESTS_PASSED, "branch": "001-feature"}), encoding="utf-8"
        )

        report = nfr.write_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature", porcelain=" M app.py\n")
        )

        self.assertEqual(nfr.PHASE_READY_FOR_COMMIT, report["phase"])
        self.assertEqual(nfr.SAFETY_ACTION, report["safety_status"])

    def test_execution_evidence_for_a_different_branch_is_treated_as_stale(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / nfr.EXECUTION_EVIDENCE_FILE).write_text(
            json.dumps({"status": nfr.EVIDENCE_TESTS_PASSED, "branch": "002-other"}), encoding="utf-8"
        )

        report = nfr.write_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature", porcelain=" M app.py\n")
        )

        self.assertEqual(nfr.PHASE_IMPLEMENTATION_REVIEW_REQUIRED, report["phase"])
        self.assertEqual(nfr.SAFETY_ACTION, report["safety_status"])

    # ------------------------------------------------------------------
    # Analyze evidence from execution evidence (stdout-only analyze gap)
    # ------------------------------------------------------------------

    def _write_execution_evidence(self, target: Path, evidence: dict) -> None:
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / nfr.EXECUTION_EVIDENCE_FILE).write_text(
            json.dumps(evidence), encoding="utf-8"
        )

    def test_execution_evidence_analyze_status_unblocks_analyze_phase(self) -> None:
        """Stdout-only analyze records analyze_status in execution evidence;
        driver must accept it as analyze evidence when no file exists."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")
        self._write_execution_evidence(target, {
            "branch": "001-feature",
            "analyze_status": nfr.EVIDENCE_ANALYZE_PASSED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_IMPLEMENT, report["phase"])
        self.assertEqual("execution_evidence:analyze_status=PASSED",
                         report["verified_evidence"]["analyze_evidence"])

    def test_execution_evidence_analyze_and_implement_reaches_push_phase(self) -> None:
        """End-to-end: analyze_status + IMPLEMENTED_COMMITTED in execution
        evidence → READY_FOR_PUSH_OR_PR (not stuck at READY_FOR_ANALYZE)."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")
        self._write_execution_evidence(target, {
            "branch": "001-feature",
            "analyze_status": nfr.EVIDENCE_ANALYZE_PASSED,
            "status": nfr.EVIDENCE_IMPLEMENTED_COMMITTED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_PUSH_OR_PR, report["phase"])

    def test_execution_evidence_wrong_branch_does_not_unblock_analyze(self) -> None:
        """analyze_status for a different branch is stale; must not unblock."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")
        self._write_execution_evidence(target, {
            "branch": "002-other",
            "analyze_status": nfr.EVIDENCE_ANALYZE_PASSED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertEqual(nfr.PHASE_READY_FOR_ANALYZE, report["phase"])
        self.assertNotIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])

    def test_execution_evidence_missing_analyze_status_does_not_unblock(self) -> None:
        """Execution evidence without analyze_status → still READY_FOR_ANALYZE."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")
        self._write_execution_evidence(target, {
            "branch": "001-feature",
            "status": nfr.EVIDENCE_IMPLEMENTED_COMMITTED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertEqual(nfr.PHASE_READY_FOR_ANALYZE, report["phase"])

    def test_execution_evidence_non_passed_analyze_status_does_not_unblock(self) -> None:
        """analyze_status with a value other than PASSED → still READY_FOR_ANALYZE."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")
        self._write_execution_evidence(target, {
            "branch": "001-feature",
            "analyze_status": "FAILED",
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertEqual(nfr.PHASE_READY_FOR_ANALYZE, report["phase"])

    def test_malformed_execution_evidence_does_not_unblock_analyze(self) -> None:
        """Malformed JSON in execution evidence → still READY_FOR_ANALYZE."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body")
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / nfr.EXECUTION_EVIDENCE_FILE).write_text(
            "not valid json{{{", encoding="utf-8"
        )

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertEqual(nfr.PHASE_READY_FOR_ANALYZE, report["phase"])

    def test_file_analyze_evidence_takes_precedence_over_execution_evidence(self) -> None:
        """When analyze_report.md exists, it is the reported evidence source
        even if execution evidence also has analyze_status."""
        target = self._target()
        self._init_speckit(target)
        spec_dir = self._write_spec(
            target, "001-feature", plan="plan body", tasks="tasks body", analyze="report"
        )
        self._write_execution_evidence(target, {
            "branch": "001-feature",
            "analyze_status": nfr.EVIDENCE_ANALYZE_PASSED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])
        self.assertIn("analyze_report.md",
                       report["verified_evidence"]["analyze_evidence"])

    # ------------------------------------------------------------------
    # Implement evidence from execution evidence (clean tree paths)
    # ------------------------------------------------------------------

    def test_file_analyze_plus_implement_evidence_reaches_push_phase(self) -> None:
        """File-based analyze + IMPLEMENTED_COMMITTED in execution evidence
        → READY_FOR_PUSH_OR_PR on a clean tree."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")
        self._write_execution_evidence(target, {
            "branch": "001-feature",
            "status": nfr.EVIDENCE_IMPLEMENTED_COMMITTED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_PUSH_OR_PR, report["phase"])

    def test_file_analyze_plus_wrong_branch_implement_evidence_stays_at_implement(self) -> None:
        """File-based analyze passes, but IMPLEMENTED_COMMITTED for a different
        branch is stale; must fall through to READY_FOR_IMPLEMENT."""
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")
        self._write_execution_evidence(target, {
            "branch": "002-other",
            "status": nfr.EVIDENCE_IMPLEMENTED_COMMITTED,
        })

        report = nfr.build_next_feature_readiness_report(
            target, run=_RunStub(git_root=target, branch="001-feature")
        )

        self.assertIn(nfr.PHASE_ANALYZE_READY, report["completed_phases"])
        self.assertEqual(nfr.PHASE_READY_FOR_IMPLEMENT, report["phase"])

    # ------------------------------------------------------------------
    # Branch/spec binding conflicts
    # ------------------------------------------------------------------

    def test_branch_spec_dir_mismatch_is_reported_as_binding_blocked(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="002-other"))

        self.assertEqual(nfr.PHASE_BRANCH_BINDING_BLOCKED, report["phase"])
        self.assertEqual(nfr.SAFETY_BLOCKED, report["safety_status"])
        self.assertFalse(report["merge_allowed"])

    # ------------------------------------------------------------------
    # No state may claim merge allowed
    # ------------------------------------------------------------------

    def test_no_phase_ever_allows_merge(self) -> None:
        scenarios: list[dict[str, Any]] = []

        target = self._target("base")
        scenarios.append({"target": target, "run": _RunStub(git_root=None)})

        target = self._target("init")
        self._init_speckit(target, constitution=False)
        scenarios.append({"target": target, "run": _RunStub(git_root=target, branch="main")})

        target = self._target("ready")
        self._init_speckit(target)
        scenarios.append({"target": target, "run": _RunStub(git_root=target, branch="main")})

        target = self._target("implement")
        self._init_speckit(target)
        self._hook(target)
        self._write_spec(target, "001-feature", plan="plan body", tasks="tasks body", analyze="analyze body")
        scenarios.append({"target": target, "run": _RunStub(git_root=target, branch="001-feature")})

        for scenario in scenarios:
            report = nfr.write_next_feature_readiness_report(scenario["target"], run=scenario["run"])
            self.assertFalse(report["merge_allowed"], report["phase"])

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------

    def test_report_is_idempotent_except_for_report_artifacts(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature", plan="plan body")

        first = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))
        second = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="001-feature"))

        for key in (
            "phase",
            "safety_status",
            "completed_phases",
            "verified_evidence",
            "missing_evidence",
            "blockers",
            "speckit_next_action",
            "git_next_action",
            "next_safe_action",
            "merge_allowed",
            "branch_gate",
            "constitution_exists",
        ):
            self.assertEqual(first[key], second[key], key)

    # ------------------------------------------------------------------
    # Agent / model guidance (advisory)
    # ------------------------------------------------------------------

    # 1 + 7. JSON includes agent_model_guidance; recommended_model unchanged.
    def test_agent_model_guidance_present_and_recommended_model_unchanged(self) -> None:
        target = self._target()
        self._init_speckit(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        guidance = report["agent_model_guidance"]
        self.assertIsInstance(guidance, dict)
        for key in (
            "recommended_actor",
            "model_tier",
            "concrete_model",
            "thinking_effort",
            "simple_model_allowed",
            "human_decision_required",
            "why",
        ):
            self.assertIn(key, guidance)
        # recommended_model field itself is preserved (READY_FOR_SPECKIT_SPECIFY -> MODEL_DEFAULT).
        self.assertEqual(mr.MODEL_DEFAULT, report["recommended_model"])

    # 2. Markdown includes the section.
    def test_agent_model_guidance_rendered_section(self) -> None:
        target = self._target()
        self._init_speckit(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))
        rendered = nfr.render_next_feature_readiness_report(report)

        self.assertIn("## Agent / model guidance", rendered)
        self.assertIn("Recommended actor", rendered)
        self.assertIn("Thinking effort", rendered)
        self.assertIn("Human decision required", rendered)

    # 3. MODEL_DEFAULT -> standard / lower-cost compatible.
    def test_guidance_default_is_standard_and_simple_allowed(self) -> None:
        guidance = nfr._agent_model_guidance(
            phase=nfr.PHASE_READY_FOR_SPECKIT_SPECIFY,
            safety_status=nfr.SAFETY_PASS,
            recommended_model=mr.MODEL_DEFAULT,
            blockers=[],
        )
        self.assertEqual(mr.MODEL_DEFAULT, guidance["model_tier"])
        self.assertEqual("standard", guidance["thinking_effort"])
        self.assertTrue(guidance["simple_model_allowed"])
        self.assertFalse(guidance["human_decision_required"])

    # 4. MODEL_STRONG -> strong / high, simple not allowed.
    def test_guidance_strong_is_high_no_simple(self) -> None:
        guidance = nfr._agent_model_guidance(
            phase=nfr.PHASE_READY_FOR_PLAN,
            safety_status=nfr.SAFETY_PASS,
            recommended_model=mr.MODEL_STRONG,
            blockers=[],
        )
        self.assertEqual(mr.MODEL_STRONG, guidance["model_tier"])
        self.assertEqual("high", guidance["thinking_effort"])
        self.assertFalse(guidance["simple_model_allowed"])
        self.assertIn("Sonnet", guidance["concrete_model"])

    # 5. MODEL_CRITICAL -> reviewer / deep / human decision.
    def test_guidance_critical_is_reviewer_deep_human(self) -> None:
        guidance = nfr._agent_model_guidance(
            phase=nfr.PHASE_IMPLEMENTATION_REVIEW_REQUIRED,
            safety_status=nfr.SAFETY_ACTION,
            recommended_model=mr.MODEL_CRITICAL,
            blockers=["needs review"],
        )
        self.assertEqual(mr.MODEL_CRITICAL, guidance["model_tier"])
        self.assertEqual("deep", guidance["thinking_effort"])
        self.assertFalse(guidance["simple_model_allowed"])
        self.assertTrue(guidance["human_decision_required"])
        self.assertIn("reviewer", guidance["recommended_actor"])

    # 6. branch/spec blocked maps to critical guidance.
    def test_branch_binding_blocked_gets_critical_guidance(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._write_spec(target, "001-feature")

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="002-other"))

        self.assertEqual(nfr.PHASE_BRANCH_BINDING_BLOCKED, report["phase"])
        guidance = report["agent_model_guidance"]
        self.assertEqual(mr.MODEL_CRITICAL, guidance["model_tier"])
        self.assertTrue(guidance["human_decision_required"])

    # 8. Guidance is advisory only -- no execution, single next safe action preserved.
    def test_guidance_adds_no_execution_and_keeps_single_next_action(self) -> None:
        target = self._target()
        self._init_speckit(target)

        run = _RunStub(git_root=target, branch="main")
        report = nfr.build_next_feature_readiness_report(target, run=run)

        # Only read-only git plumbing issued; guidance did not trigger any command.
        for argv in run.calls:
            self.assertEqual("git", argv[0])
            self.assertTrue({"commit", "push", "checkout", "init", "merge"}.isdisjoint(argv), argv)
        self.assertIsInstance(report["next_safe_action"], str)
        self.assertNotIsInstance(report["next_safe_action"], (list, tuple))


if __name__ == "__main__":
    unittest.main()
