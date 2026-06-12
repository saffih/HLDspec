from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace

from hldspec import run_state
from hldspec import speckit_operator_state as sos


ROOT = Path(__file__).resolve().parents[1]


class _RunStub:
    def __init__(self, *, git_root: Path | None = None, branch: str = "main", dirty: bool = False, dirty_paths: list[str] | None = None):
        self.git_root = git_root
        self.branch = branch
        self.dirty = dirty
        self.dirty_paths = dirty_paths
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
                if self.dirty_paths is not None:
                    return SimpleNamespace(returncode=0, stdout="".join(f"?? {path}\n" for path in self.dirty_paths), stderr="")
                return SimpleNamespace(returncode=0, stdout=(" M file.txt\n" if self.dirty else ""), stderr="")
        if argv[:3] in (["specify", "init", "--help"], ["spec-kit", "init", "--help"]):
            return SimpleNamespace(returncode=0, stdout="ok\n--force\n", stderr="")
        if argv[:2] in (["specify", "--help"], ["specify", "--version"], ["spec-kit", "--help"], ["spec-kit", "--version"]):
            return SimpleNamespace(returncode=0, stdout="ok\n--force\n", stderr="")
        if argv[:7] == ["uvx", "--from", sos.sr.sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "init", "--help"]:
            return SimpleNamespace(returncode=0, stdout="ok\n--force\n", stderr="")
        if argv[:6] == ["uvx", "--from", sos.sr.sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "--help"]:
            return SimpleNamespace(returncode=0, stdout="ok\n--force\n", stderr="")
        if argv[:6] == ["uvx", "--from", sos.sr.sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "--version"]:
            return SimpleNamespace(returncode=0, stdout="ok\n--force\n", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


def _write_lineage(base: Path) -> None:
    """Real trusted lineage: manifest plus anchor map (a bare dir is no longer trusted)."""
    source_package = base / ".hldspec" / "source_package"
    source_package.mkdir(parents=True, exist_ok=True)
    (source_package / "source_package.json").write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    (source_package / "hld_reference_map.json").write_text(json.dumps({"anchors": {"HLD-001": {}}}), encoding="utf-8")


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
        self.assertEqual("NEW_GREENFIELD", report["state"])
        self.assertIn("HLDspec start", report["next_safe_action"])
        self.assertEqual("NEW_GREENFIELD", report["target_discovery_report"]["classification"])

    def test_no_git_repo_reports_action(self) -> None:
        target = self.root / "target"
        target.mkdir()
        _write_lineage(target)
        report = self._report(target, which=_which_only("specify"), run=_RunStub())
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("TARGET_NOT_GIT", report["state"])
        self.assertIn("git workspace", report["next_safe_action"])

    def test_dirty_tree_reports_action(self) -> None:
        target = self.root / "target"
        _write_lineage(target)
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target, dirty=True))
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("TARGET_DIRTY_UNEXPECTED", report["state"])
        self.assertIn("Clean, commit, or stash the target tree", report["next_safe_action"])

    def test_hldspec_pointer_only_dirty_tree_is_classified_as_expected_control(self) -> None:
        target = self.root / "target"
        controller = self.root / "external-run"
        _write_lineage(controller)
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        run_state.write_pointer(
            target,
            controller_root=controller,
            source=self.root / "HLD.md",
            source_hash="a" * 64,
            mode="update",
            agent="codex",
            workflow_trigger="build_loop_ready",
            created_or_updated_at="2026-06-06T00:00:00+00:00",
        )

        report = self._report(
            target,
            which=_which_only("specify"),
            run=_RunStub(git_root=target, dirty=True, dirty_paths=[run_state.POINTER_FILE]),
        )

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("TARGET_DIRTY_EXPECTED_HLDSPEC_CONTROL", report["state"])
        facts = report["source_facts_used"]
        self.assertEqual("expected_hldspec_control", facts["dirty_target_classification"]["status"])
        self.assertEqual(str((controller / ".hldspec" / "source_package").resolve()), facts["source_package_dir"])

    def test_zero_anchor_external_source_package_reports_invalid_before_dirty_pointer(self) -> None:
        target = self.root / "target-invalid-source"
        controller = self.root / "external-run-invalid-source"
        source_package = controller / ".hldspec" / "source_package"
        source_package.mkdir(parents=True)
        (source_package / "hld_reference_map.json").write_text(json.dumps({"anchors": {}}), encoding="utf-8")
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        run_state.write_pointer(
            target,
            controller_root=controller,
            source=self.root / "proposal.md",
            source_hash="b" * 64,
            mode="update",
            agent="codex",
            workflow_trigger="build_loop_ready",
            created_or_updated_at="2026-06-06T00:00:00+00:00",
        )

        report = self._report(
            target,
            which=_which_only("specify"),
            run=_RunStub(git_root=target, dirty=True, dirty_paths=[run_state.POINTER_FILE]),
        )

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("SOURCE_PACKAGE_INVALID", report["state"])
        self.assertIn("0 recognized HLD anchors", " ".join(report["blockers"]))
        self.assertEqual(0, report["source_facts_used"]["source_package_anchor_count"])

    def test_source_package_missing_reports_action(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("UNKNOWN_BROWNFIELD", report["state"])
        self.assertIn("brownfield adoption is unsupported", " ".join(report["blockers"]))
        self.assertNotIn("wipe", report["next_safe_action"].lower())

    def test_specify_source_only_reports_not_initialized(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "source").mkdir(parents=True)
        _write_lineage(target)
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
        _write_lineage(target)
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        self.assertEqual("PASS", report["status"])
        self.assertEqual("READY_FOR_SPECIFY", report["state"])
        self.assertTrue(report["next_safe_action"])
        self.assertTrue(report["evidence"])
        self.assertTrue(report["source_facts_used"])
        self.assertEqual("PASS", report["readiness_report"]["status"])
        self.assertIn("readiness/preflight only", report["doctor_note"])

    def test_ready_project_checkpoint_does_not_block_operator_state(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "hldspec_state.json").write_text(
            json.dumps({"schema_version": 1, "current_stage": "READY_FOR_SPECIFY", "current_checkpoint": "BUILD_LOOP_READY"}),
            encoding="utf-8",
        )

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("PASS", report["status"])
        self.assertEqual("READY_FOR_SPECIFY", report["state"])

    def test_unknown_project_checkpoint_requires_reassessment(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "hldspec_state.json").write_text(
            json.dumps({"schema_version": 1, "current_stage": "SURPRISE_STATE", "current_checkpoint": "SURPRISE_CHECKPOINT"}),
            encoding="utf-8",
        )

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("BLOCKED", report["state"])
        self.assertTrue(any("Unrecognized Project checkpoint state" in item for item in report["blockers"]))

    def test_legacy_conversion_ready_stage_blocks_operator_state(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "hldspec_state.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "current_stage": "CONVERSION_READY_TO_APPLY",
                    "current_checkpoint": "apply_working_hld_conversion",
                    "next_allowed_actions": ["apply conversion decisions to working HLD only"],
                }
            ),
            encoding="utf-8",
        )

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("BLOCKED", report["state"])
        self.assertTrue(any("CONVERSION_READY_TO_APPLY" in item for item in report["blockers"]))

    def test_hld_ready_check_hld_state_is_not_full_speckit_readiness(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "hldspec_state.json").write_text(
            json.dumps({"schema_version": 1, "current_stage": "HLD_READY", "current_checkpoint": ""}),
            encoding="utf-8",
        )

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("BLOCKED", report["state"])
        self.assertTrue(any("not full SpecKit Preparation approval" in item for item in report["blockers"]))
        self.assertIn("SpecKit Preparation", report["next_safe_action"])

    def test_managed_workspace_with_stale_source_freshness_blocks_operator_state(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        (target / ".hldspec" / "agent_session.json").write_text("{}\n", encoding="utf-8")
        (target / ".hldspec" / "source_freshness.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "working_hld_differs_from_source": True,
                    "warnings": ["workspace HLD differs from source"],
                }
            )
            + "\n",
            encoding="utf-8",
        )

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("SOURCE_FRESHNESS_BLOCKED", report["state"])
        self.assertIn("workspace HLD differs from source", report["blockers"])

    def test_managed_workspace_missing_source_freshness_blocks_operator_state(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        (target / ".hldspec" / "agent_session.json").write_text("{}\n", encoding="utf-8")

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("SOURCE_FRESHNESS_BLOCKED", report["state"])
        self.assertTrue(any("source_freshness.json" in item for item in report["blockers"]))

    def test_operator_state_read_writes_only_discovery_sync_reports(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("PASS", report["status"])
        self.assertEqual("READY_FOR_SPECIFY", report["state"])
        sync = target / ".hldspec" / "sync"
        self.assertTrue((sync / "target_discovery_report.json").is_file())
        self.assertTrue((sync / "target_discovery_report.md").is_file())
        self.assertTrue((sync / "phase_ledger.json").is_file())
        self.assertTrue((sync / "phase_ledger.md").is_file())
        self.assertFalse((target / "specs").exists())

    def test_ready_workspace_with_partial_speckit_artifacts_reports_plan_active(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_bundle_queue.json").write_text(
            '{"bundles":[{"bundle_id":"G01","bundle_slug":"g01","included_specs":[{"feature_id":"F01","short_name":"001-flow"}]}]}',
            encoding="utf-8",
        )
        spec_dir = target / "specs" / "001-flow"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (spec_dir / "specify_validation.json").write_text('{"status":"PASS"}\n', encoding="utf-8")

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("PASS", report["status"])
        self.assertEqual("PLAN_ACTIVE", report["state"])
        self.assertEqual("PLAN_ACTIVE", report["lifecycle_state"])
        self.assertEqual("IN_PROGRESS", report["speckit_execution_state"]["status"])
        self.assertIn("phase `plan`", report["next_safe_action"])

    def test_tasks_done_reports_analyze_ready_before_implementation(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        sync = target / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_invocation_queue.json").write_text(
            '{"items":[{"feature_id":"F01","short_name":"001-flow"}]}',
            encoding="utf-8",
        )
        spec_dir = target / "specs" / "001-flow"
        spec_dir.mkdir(parents=True)
        for name in ("spec.md", "plan.md", "tasks.md"):
            (spec_dir / name).write_text("content\n", encoding="utf-8")
        for name in ("specify_validation.json", "plan_validation.json", "tasks_validation.json"):
            (spec_dir / name).write_text('{"status":"PASS"}\n', encoding="utf-8")

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("PASS", report["status"])
        self.assertEqual("ANALYZE_READY", report["state"])
        self.assertEqual("ANALYZE_READY", report["lifecycle_state"])
        self.assertIn("/speckit.analyze", report["next_safe_action"])
        self.assertIn("implementation-slice approval", report["next_safe_action"])

    def test_unmapped_speckit_artifacts_require_reassessment(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        spec_dir = target / "specs" / "001-flow"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))

        self.assertEqual("ACTION", report["status"])
        self.assertEqual("PHASED_GREENFIELD", report["state"])
        self.assertIn("UNVERIFIED", report["next_safe_action"])
        self.assertTrue(any("Unverified phase artifact" in item for item in report["blockers"]))

    def test_summary_is_boundary_safe_and_devin_free(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "source").mkdir(parents=True)
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        _write_lineage(target)
        report = self._report(target, which=_which_only("specify"), run=_RunStub(git_root=target))
        text = sos.summarize_speckit_operator_state(report)
        self.assertIn("STATUS: PASS", text)
        self.assertIn("State: READY_FOR_SPECIFY", text)
        self.assertIn("Next safe action:", text)
        self.assertIn("SpecKit Doctor is readiness/preflight only", text)
        self.assertIn("Lifecycle:", text)
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
        self.assertIn("State: NEW_GREENFIELD", result.stdout)
        self.assertIn("Next safe action:", result.stdout)


if __name__ == "__main__":
    unittest.main()
