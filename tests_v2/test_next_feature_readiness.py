from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

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

    def test_missing_specify_dir_recommends_init_not_refresh_target_or_specify(self) -> None:
        target = self._target()

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        setup = report["setup_readiness"]
        self.assertFalse(setup["specify_dir_exists"])
        self.assertFalse(setup["memory_dir_exists"])
        self.assertNotIn("refresh_target", report["next_safe_action"])
        self.assertNotIn("refresh-target", report["next_safe_action"])
        self.assertNotIn("/speckit.specify", report["next_safe_action"])
        if setup["recommended_init_command"]:
            self.assertIn(setup["recommended_init_command"], report["next_safe_action"])
        else:
            self.assertIn("does not invent a command", report["next_safe_action"])

    def test_missing_memory_dir_recommends_init_completion(self) -> None:
        target = self._target()
        (target / ".specify").mkdir(parents=True, exist_ok=True)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.PHASE_NEEDS_SPECKIT_INIT, report["phase"])
        setup = report["setup_readiness"]
        self.assertTrue(setup["specify_dir_exists"])
        self.assertFalse(setup["memory_dir_exists"])
        self.assertIn(".specify/memory/", report["blockers"][0])

    def test_hooks_unknown_when_specify_dir_missing(self) -> None:
        target = self._target()

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_UNKNOWN, report["setup_readiness"]["hooks_status"])
        self.assertEqual([], report["advisory_actions"])

    def test_hooks_missing_is_advisory_only_once_initialized(self) -> None:
        target = self._target()
        self._init_speckit(target)  # constitution present, no hook file

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_MISSING, report["setup_readiness"]["hooks_status"])
        self.assertTrue(any("HOOKS_MISSING" in item for item in report["advisory_actions"]))
        # Advisory only -- does not block the normal next SpecKit action.
        self.assertEqual(nfr.PHASE_READY_FOR_SPECKIT_SPECIFY, report["phase"])
        self.assertEqual("/speckit.specify", report["speckit_next_action"])

    def test_hooks_ready_when_branch_policy_file_present(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))

        self.assertEqual(nfr.HOOKS_READY, report["setup_readiness"]["hooks_status"])
        self.assertFalse(any("HOOKS_MISSING" in item for item in report["advisory_actions"]))

    def test_setup_readiness_rendered_in_run_card(self) -> None:
        target = self._target()
        self._init_speckit(target)
        self._hook(target)

        report = nfr.write_next_feature_readiness_report(target, run=_RunStub(git_root=target, branch="main"))
        rendered = nfr.render_next_feature_readiness_report(report)

        self.assertIn("## Setup readiness", rendered)
        self.assertIn("HOOKS_READY", rendered)
        self.assertIn(".specify/ exists: `true`", rendered)
        self.assertIn(".specify/memory/ exists: `true`", rendered)

    def test_setup_readiness_does_not_run_speckit_install_hooks_or_mutate_git(self) -> None:
        target = self._target()
        self._init_speckit(target)

        run = _RunStub(git_root=target, branch="main")
        nfr.build_next_feature_readiness_report(target, run=run)

        # Only read-only git plumbing commands are issued -- no commit/push/checkout/init.
        mutating = {"commit", "push", "checkout", "init", "merge", "reset"}
        for argv in run.calls:
            self.assertEqual("git", argv[0])
            self.assertTrue(mutating.isdisjoint(argv), argv)
        self.assertFalse((target / ".specify" / "extensions.yml").exists())
        self.assertFalse((target / ".specify" / "hooks.yml").exists())

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


if __name__ == "__main__":
    unittest.main()
