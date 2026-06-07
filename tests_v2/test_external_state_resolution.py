"""Guard tests: in external state-location mode, control-state reads must resolve
the controller root (via the .hldspec-run.json pointer), not target/.hldspec.

These cover the external-mode resolution regressions: a runner in external mode
keeps only the pointer in the target, so any code reading target/.hldspec directly
silently misses the real state.
"""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hldspec_agent_session as facade  # noqa: E402
from hldspec import run_state  # noqa: E402
from hldspec import session_control as sc  # noqa: E402
from hldspec import source_freshness as sf  # noqa: E402
from hldspec import speckit_readiness as sr  # noqa: E402


def _make_external(tmp: str) -> tuple[Path, Path]:
    """A target with only the pointer; real .hldspec lives under the controller root."""
    target = Path(tmp) / "target"
    controller = Path(tmp) / "controller"
    target.mkdir()
    (controller / ".hldspec").mkdir(parents=True)
    source = target / "HLD.md"
    source.write_text("# HLD\n", encoding="utf-8")
    run_state.write_pointer(
        target,
        controller_root=controller,
        source=source,
        source_hash="deadbeef",
        mode="update",
        agent="test",
        workflow_trigger="build_loop_ready",
        created_or_updated_at="2026-06-07T00:00:00+00:00",
    )
    return target, controller


class ExternalStateResolutionTests(unittest.TestCase):
    def test_resolver_points_at_controller_in_external_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            self.assertEqual(
                facade._resolve_hldspec_dir(target).resolve(),
                (controller / ".hldspec").resolve(),
            )

    def test_open_questions_resolved_from_controller(self):
        # P1b: unresolved checkpoints stored in the controller must not be hidden.
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            (controller / ".hldspec" / "interview_answers.json").write_text(
                json.dumps({"open_questions": ["Q-EXT: confirm scope"]}),
                encoding="utf-8",
            )
            qs = facade.collect_open_questions(target)
            # Pre-fix this read target/.hldspec (absent) and returned [].
            self.assertIn("Q-EXT: confirm scope", qs)

    def test_non_external_mode_unchanged(self):
        # No pointer -> resolver and open-questions behave exactly as before.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "t"
            (target / ".hldspec").mkdir(parents=True)
            self.assertEqual(facade._resolve_hldspec_dir(target), target / ".hldspec")
            (target / ".hldspec" / "interview_answers.json").write_text(
                json.dumps({"open_questions": ["Q-LOCAL"]}), encoding="utf-8"
            )
            self.assertIn("Q-LOCAL", facade.collect_open_questions(target))


class PreflightGateExternalTests(unittest.TestCase):
    def test_preflight_is_gated_from_controller_plan(self):
        # P0: in external mode the continuation gate must NOT be bypassed — the
        # session plan lives under the controller root, and preflight must find it.
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            pkg = controller / ".hldspec" / "source_package"
            pkg.mkdir(parents=True)
            (pkg / sc.SESSION_PLAN_FILE).write_text(
                json.dumps({"current_gate": "PREWORK"}), encoding="utf-8"
            )
            preflight = sc.session_continue_preflight(target, check_dirty=False)
            # Pre-fix: adapter used target/.hldspec, no plan found -> gated=False (BYPASS).
            self.assertTrue(preflight.gated, "external-mode continuation gate was bypassed")

    def test_preflight_off_without_any_plan(self):
        # Backward compatible: no plan anywhere -> gating OFF (allowed).
        with tempfile.TemporaryDirectory() as tmp:
            target, _controller = _make_external(tmp)
            preflight = sc.session_continue_preflight(target, check_dirty=False)
            self.assertFalse(preflight.gated)
            self.assertTrue(preflight.allowed)


class SourceFreshnessExternalTests(unittest.TestCase):
    def test_targethld_resolved_from_target_in_external_mode(self):
        # P1a: targetHLD is a product artifact and stays in the target even in
        # external mode; freshness must not look for it under the controller root.
        with tempfile.TemporaryDirectory() as tmp:
            target, _controller = _make_external(tmp)
            body = "# Working HLD\n\nbody\n"
            (target / "targetHLD" / "raw").mkdir(parents=True)
            (target / "targetHLD" / "HLD.md").write_text(body, encoding="utf-8")
            (target / "targetHLD" / "raw" / "HLD.raw.md").write_text(body, encoding="utf-8")
            source = Path(tmp) / "source_HLD.md"
            source.write_text(body, encoding="utf-8")
            result = sf.build_source_freshness(target, source)
            # Pre-fix: looked under controller/targetHLD (absent) -> "missing" -> stale.
            self.assertEqual(result["state"], "fresh", result.get("warnings"))


class RemainingExternalReadSweepTests(unittest.TestCase):
    def test_current_state_resolves_hldspec_state_from_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            sync = controller / ".hldspec" / "sync"
            sync.mkdir(parents=True)
            (sync / "hldspec_state.json").write_text(
                json.dumps({"current_stage": "READY_FOR_SPECIFY", "current_checkpoint": "BUILD_LOOP_READY"}),
                encoding="utf-8",
            )

            state = facade.current_state(target, {"schema_version": 1})

            self.assertEqual(state, "READY_FOR_SPECIFY / BUILD_LOOP_READY")

    def test_active_workflow_report_resolves_from_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            sync = controller / ".hldspec" / "sync"
            sync.mkdir(parents=True)
            (sync / "build_loop_prereqs_report.json").write_text(
                json.dumps(
                    {
                        "status": "ACTION",
                        "state": "NEEDS_INIT",
                        "blockers": ["controller blocker"],
                        "next_safe_action": "fix controller blocker",
                    }
                ),
                encoding="utf-8",
            )

            blockers, next_action = facade.active_workflow_blockers(
                target, {"workflow_trigger": "build_loop_prereqs"}
            )

            self.assertIn("Workflow report: ACTION (NEEDS_INIT)", blockers)
            self.assertIn("controller blocker", blockers)
            self.assertEqual(next_action, "fix controller blocker")

    def test_doctor_validation_reports_resolve_from_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            (target / "targetHLD" / "raw").mkdir(parents=True)
            (target / "targetHLD" / "HLD.md").write_text("# HLD\n", encoding="utf-8")
            (target / "targetHLD" / "raw" / "HLD.raw.md").write_text("# HLD\n", encoding="utf-8")
            (controller / "prompts" / "agent").mkdir(parents=True)
            (controller / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").write_text("start\n", encoding="utf-8")
            validation = controller / ".hldspec" / "validation"
            validation.mkdir(parents=True)
            (validation / "context_prompt_validation.json").write_text(
                json.dumps({"status": "ACTION"}), encoding="utf-8"
            )
            (validation / "promotion_gate.json").write_text(
                json.dumps({"status": "PASS"}), encoding="utf-8"
            )
            (controller / ".hldspec" / "agent_session.json").write_text(
                json.dumps({"speckit_workspace_init": {}}), encoding="utf-8"
            )

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                facade.command_doctor(SimpleNamespace(target=str(target)))

            text = out.getvalue()
            self.assertIn(str(validation / "context_prompt_validation.json"), text)
            self.assertIn(str(validation / "promotion_gate.json"), text)

    def test_start_prompt_and_tool_manifest_use_controller_paths_when_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            controller = Path(tmp) / "controller"
            target.mkdir()
            session = {
                "source": {"path": str(Path(tmp) / "HLD.md")},
                "mode": "create",
                "agent": "codex",
                "comment": "",
                "workflow_trigger": "default",
                "speckit_workspace_init": {"selected_command": ["specify", "init", ".", "--force"]},
            }

            prompt = facade.write_start_prompt(target, session, controller_root=controller)
            manifest = facade.write_tool_manifest(target, controller_root=controller)

            self.assertIn(str(controller / ".hldspec" / "source_package" / "session_plan.json"), prompt.read_text(encoding="utf-8"))
            self.assertIn(str(controller / ".hldspec" / "sync"), manifest.read_text(encoding="utf-8"))

    def test_speckit_readiness_source_package_check_resolves_from_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            (controller / ".hldspec" / "source_package").mkdir(parents=True)

            report = sr.build_speckit_readiness_report(target, which=lambda _: None)

            checks = {item["name"]: item for item in report["checks"]}
            self.assertEqual("PASS", checks[".hldspec/source_package/ exists"]["status"])


class ExternalizationCrashSafetyTests(unittest.TestCase):
    def test_copy_happens_before_pointer_and_target_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            controller = Path(tmp) / "controller"
            (target / ".hldspec").mkdir(parents=True)
            (target / ".hldspec" / "agent_session.json").write_text("{}\n", encoding="utf-8")
            (target / "prompts" / "agent").mkdir(parents=True)
            (target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").write_text("start\n", encoding="utf-8")

            copied = run_state.copy_target_control_artifacts(target, controller_root=controller)

            self.assertFalse((target / run_state.POINTER_FILE).exists())
            self.assertTrue((target / ".hldspec" / "agent_session.json").is_file())
            self.assertTrue((target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").is_file())
            self.assertTrue((controller / ".hldspec" / "agent_session.json").is_file())
            self.assertTrue((controller / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").is_file())
            self.assertEqual({".hldspec", "prompts"}, {item["rel"] for item in copied})

    def test_copy_removes_stale_controller_files_without_deleting_target_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            controller = Path(tmp) / "controller"
            (target / ".hldspec").mkdir(parents=True)
            (target / ".hldspec" / "agent_session.json").write_text("{}\n", encoding="utf-8")
            (controller / ".hldspec").mkdir(parents=True)
            (controller / ".hldspec" / "stale_checkpoint.json").write_text(
                json.dumps({"human_checkpoint": {"decision": "TBD"}}),
                encoding="utf-8",
            )

            run_state.copy_target_control_artifacts(target, controller_root=controller)

            self.assertTrue((target / ".hldspec" / "agent_session.json").is_file())
            self.assertTrue((controller / ".hldspec" / "agent_session.json").is_file())
            self.assertFalse((controller / ".hldspec" / "stale_checkpoint.json").exists())

    def test_target_deletion_happens_only_after_pointer_resolves_to_complete_controller(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target"
            controller = Path(tmp) / "controller"
            source = Path(tmp) / "HLD.md"
            source.write_text("# HLD\n", encoding="utf-8")
            (target / ".hldspec").mkdir(parents=True)
            (target / ".hldspec" / "agent_session.json").write_text("{}\n", encoding="utf-8")
            (target / "prompts" / "agent").mkdir(parents=True)
            (target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").write_text("start\n", encoding="utf-8")

            copied = run_state.copy_target_control_artifacts(target, controller_root=controller)
            run_state.write_pointer(
                target,
                controller_root=controller,
                source=source,
                source_hash="beadfeed",
                mode="create",
                agent="test",
                workflow_trigger="default",
                created_or_updated_at="2026-06-07T00:00:00+00:00",
            )
            removed = run_state.delete_target_control_artifacts(target, copied)

            self.assertTrue((target / run_state.POINTER_FILE).is_file())
            self.assertEqual(facade._resolve_hldspec_dir(target).resolve(), (controller / ".hldspec").resolve())
            self.assertTrue((controller / ".hldspec" / "agent_session.json").is_file())
            self.assertTrue((controller / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").is_file())
            self.assertFalse((target / ".hldspec").exists())
            self.assertFalse((target / "prompts").exists())
            self.assertEqual({".hldspec", "prompts"}, {item["rel"] for item in removed})


if __name__ == "__main__":
    unittest.main()
