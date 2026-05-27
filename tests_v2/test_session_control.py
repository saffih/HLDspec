import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec import gate_validator as gv
from hldspec import model_routing as mr
from hldspec import session_control as sc
from hldspec.workspace_adapter import TargetWorkspaceAdapter

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hldspec_agent_session as facade  # noqa: E402
import hldspec_session_control as cli  # noqa: E402


class SessionPlanTests(unittest.TestCase):
    def test_plan_generation_keys(self):
        plan = sc.build_session_plan("/tmp/target", "/repo")
        for key in (
            "schema_version",
            "session_name",
            "backend",
            "target_repo_path",
            "hldspec_repo_path",
            "current_gate",
            "roles",
        ):
            self.assertIn(key, plan)

    def test_plan_has_four_roles(self):
        plan = sc.build_session_plan("/tmp/target", "/repo")
        self.assertEqual(
            set(plan["roles"].keys()),
            {sc.MAIN_CONTROLLER, sc.BASEPACK, sc.RUNNER, sc.CONSULTANT},
        )

    def test_dry_run_is_default(self):
        self.assertEqual(sc.DEFAULT_BACKEND, "dry-run")
        plan = sc.build_session_plan("/tmp/target", "/repo")
        self.assertEqual(plan["backend"], "dry-run")

    def test_command_only_backend(self):
        plan = sc.build_session_plan("/tmp/target", "/repo", backend="command-only")
        commands = sc.render_role_commands(plan)
        self.assertEqual(set(commands.keys()), set(sc.ROLES))
        self.assertTrue(all(isinstance(c, str) and c for c in commands.values()))

    def test_tmux_commands_use_target_path(self):
        plan = sc.build_session_plan("/tmp/my-target", "/repo", backend="tmux")
        cmds = sc.render_tmux_commands(plan)
        self.assertTrue(any("/tmp/my-target" in c for c in cmds))
        self.assertTrue(any(sc.MAIN_CONTROLLER in c for c in cmds))

    def test_tmux_default_session_name_is_target_and_gate_specific(self):
        plan = sc.build_session_plan(
            "/tmp/My Target",
            "/repo",
            backend="tmux",
            current_gate="SPECKIT_READY",
        )
        self.assertEqual(plan["session_name"], "hldspec-my-target-speckit_ready")

    def test_tmux_commands_capture_logs_and_attach(self):
        plan = sc.build_session_plan("/tmp/my-target", "/repo", backend="tmux")
        cmds = sc.render_tmux_commands(plan)
        text = "\n".join(cmds)
        self.assertIn("mkdir -p", text)
        self.assertIn("tmux pipe-pane -o", text)
        self.assertIn("tmux capture-pane -p -S -", text)
        self.assertIn("tmux attach-session -t", text)
        self.assertIn(".hldspec/tmux/", text)

    def test_main_controller_owns_gates(self):
        plan = sc.build_session_plan("/tmp/target", "/repo")
        for role, entry in plan["roles"].items():
            self.assertEqual(entry["next_gate_owner"], sc.MAIN_CONTROLLER)

    def test_unknown_backend_rejected(self):
        with self.assertRaises(ValueError):
            sc.build_session_plan("/tmp/target", "/repo", backend="nope")


class ExecuteFlagTests(unittest.TestCase):
    def test_execute_required_for_launch(self):
        emit, _ = cli.resolve_execution("tmux", execute=False)
        self.assertFalse(emit)

    def test_execute_flag_emits(self):
        emit, _ = cli.resolve_execution("tmux", execute=True)
        self.assertTrue(emit)

    def test_dry_run_never_emits(self):
        emit, _ = cli.resolve_execution("dry-run", execute=True)
        self.assertFalse(emit)


class PacketTests(unittest.TestCase):
    def test_packet_has_required_sections(self):
        text = sc.render_packet(sc.build_runner_packet())
        for heading in sc.PACKET_SECTIONS:
            self.assertIn(heading, text)

    def test_no_self_approval_in_rendered_packet(self):
        for packet in sc.all_packets().values():
            self.assertIn("SELF-APPROVAL: forbidden", sc.render_packet(packet))

    def test_runner_stops_after_one_phase(self):
        packet = sc.build_runner_packet()
        self.assertIn("one bounded phase", packet.stop_condition.lower())
        self.assertEqual([], sc.validate_packet(packet))

    def test_consultant_is_review_only(self):
        packet = sc.build_consultant_packet()
        self.assertFalse(packet.write_access)
        self.assertEqual([], sc.validate_packet(packet))

    def test_basepack_stops_after_validation(self):
        packet = sc.build_basepack_packet()
        self.assertIn("validation", packet.stop_condition.lower())
        self.assertEqual([], sc.validate_packet(packet))

    def test_broad_scan_and_web_forbidden_by_default(self):
        for packet in sc.all_packets().values():
            self.assertFalse(packet.broad_scan)
            self.assertFalse(packet.web)

    def test_validate_rejects_self_approval(self):
        packet = sc.build_runner_packet()
        packet.can_self_approve = True
        self.assertIn("self-approval is forbidden for every packet", sc.validate_packet(packet))

    def test_validate_rejects_broad_scan(self):
        packet = sc.build_runner_packet()
        packet.broad_scan = True
        self.assertTrue(any("broad scan" in e for e in sc.validate_packet(packet)))

    def test_validate_rejects_consultant_write(self):
        packet = sc.build_consultant_packet()
        packet.write_access = True
        self.assertTrue(any("review-only" in e for e in sc.validate_packet(packet)))

    def test_model_routing_used_in_packets(self):
        # Tiers come from model_routing per task: mechanical -> SIMPLE, meaning -> SMART.
        self.assertEqual(sc.build_basepack_packet().model_tier, mr.MODEL_SIMPLE)
        self.assertEqual(sc.build_runner_packet().model_tier, mr.MODEL_SIMPLE)
        self.assertEqual(sc.build_consultant_packet().model_tier, mr.MODEL_SMART)
        for packet in sc.all_packets().values():
            self.assertIn(packet.model_tier, mr.OPERATIONAL_TIERS)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data) + "\n", encoding="utf-8")


class PreflightTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.target, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.source_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_plan(self, gate=gv.SOURCE_PACKAGE_APPROVAL_GATE, approvals=None):
        plan = sc.build_session_plan(self.target, ROOT, current_gate=gate)
        if approvals is not None:
            plan["approvals"] = approvals
        _write_json(self.source_dir / sc.SESSION_PLAN_FILE, plan)

    def _full_pass_report(self):
        _write_json(self.source_dir / sc.PHASE_REPORT_FILE, {
            "phase": "p", "actor": sc.RUNNER,
            "validation_result": "PASS",
            "runskeptic_result": gv.RUNSKEPTIC_PASS,
            "consultant_result": gv.CONSULTANT_PASS,
            "source_anchors_used": ["a:intro"],
            "next_safe_action": "continue",
        })

    def _full_receipt(self):
        _write_json(self.source_dir / sc.CONTEXT_RECEIPT_FILE, {
            "required_files_read": sc.REQUIRED_READS,
            "current_phase": "p", "actor": sc.RUNNER, "model_tier": mr.MODEL_SIMPLE,
            "stop_condition": "stop", "validation_command": "x",
        })

    def test_no_plan_is_not_gated(self):
        # Backward compat: no session plan -> continuation proceeds (legacy path).
        result = sc.session_continue_preflight(self.target)
        self.assertTrue(result.allowed)
        self.assertFalse(result.gated)
        self.assertIsNone(result.gate)

    def test_missing_phase_report_blocks(self):
        self._write_plan(approvals={gv.SOURCE_PACKAGE_APPROVAL_GATE: True})
        self._full_receipt()
        result = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertTrue(result.gated)
        self.assertFalse(result.allowed)
        self.assertIn("missing Phase Report", result.blockers)

    def test_missing_receipt_blocks(self):
        self._write_plan(approvals={gv.SOURCE_PACKAGE_APPROVAL_GATE: True})
        self._full_pass_report()
        result = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertFalse(result.allowed)
        self.assertIn("missing Context Receipt", result.blockers)

    def test_missing_runskeptic_pass_blocks(self):
        self._write_plan(approvals={gv.SOURCE_PACKAGE_APPROVAL_GATE: True})
        self._full_receipt()
        _write_json(self.source_dir / sc.PHASE_REPORT_FILE, {
            "phase": "p", "actor": sc.RUNNER, "validation_result": "PASS",
            "runskeptic_result": gv.RUNSKEPTIC_NOT_RUN,
            "consultant_result": gv.CONSULTANT_PASS,
            "source_anchors_used": ["a:x"], "next_safe_action": "go",
        })
        result = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertIn("missing RunSkeptic PASS", result.blockers)

    def test_missing_consultant_pass_blocks(self):
        self._write_plan(gate=gv.SPECKIT_PLAN_REVIEW_GATE, approvals={})
        self._full_receipt()
        _write_json(self.source_dir / sc.PHASE_REPORT_FILE, {
            "phase": "p", "actor": sc.RUNNER, "validation_result": "PASS",
            "runskeptic_result": gv.RUNSKEPTIC_PASS,
            "consultant_result": gv.CONSULTANT_NOT_RUN,
            "source_anchors_used": ["a:x"], "next_safe_action": "go",
        })
        result = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertIn("missing Consultant PASS", result.blockers)

    def test_full_pass_allows_continuation(self):
        self._write_plan(approvals={gv.SOURCE_PACKAGE_APPROVAL_GATE: True})
        self._full_receipt()
        self._full_pass_report()
        result = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertTrue(result.allowed, msg=result.blockers)

    def test_dirty_tree_reported_before_runner_phase(self):
        # A git target with an unrelated dirty file must surface in the blockers.
        import subprocess
        subprocess.run(["git", "init", "-q", str(self.target)], check=True)
        (self.target / "unrelated.txt").write_text("dirty\n", encoding="utf-8")
        self._write_plan(approvals={gv.SOURCE_PACKAGE_APPROVAL_GATE: True})
        self._full_receipt()
        self._full_pass_report()
        result = sc.session_continue_preflight(self.target, check_dirty=True)
        self.assertFalse(result.allowed)
        self.assertTrue(any("dirty tree" in b for b in result.blockers))


class FacadeWiringTests(unittest.TestCase):
    """session_control must be wired into the public `continue`, not inert."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.target, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.source_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def test_continue_refuses_when_gate_blocks(self):
        # Session plan present but no Phase Report -> continue must refuse with
        # GATE_BLOCKED, before ProjectMachine runs.
        plan = sc.build_session_plan(self.target, ROOT)
        _write_json(self.source_dir / sc.SESSION_PLAN_FILE, plan)
        # also record a source so the only reason to block is the gate
        _write_json(self.target / ".hldspec" / "agent_session.json", {
            "source": {"path": str(self.target / "HLD.md")}
        })
        args = argparse.Namespace(target=str(self.target))
        code = facade.command_continue(args)
        self.assertEqual(code, 3)  # ExitCode.GATE_BLOCKED

    def test_continue_without_plan_takes_legacy_path(self):
        # No session plan AND no recorded source -> continue must NOT gate (exit 3);
        # it falls through to the legacy source check and errors with exit 2. This
        # proves command_continue only gates when session_plan.json exists.
        args = argparse.Namespace(target=str(self.target))
        code = facade.command_continue(args)
        self.assertEqual(code, 2)  # "no source recorded", not GATE_BLOCKED


class ExecuteCliTests(unittest.TestCase):
    """The CLI itself must honor dry-run/--execute, not just the helper."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.target = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _run_cli(self, *extra: str) -> str:
        import contextlib
        import io

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            cli.main(["--target", str(self.target), *extra])
        return buf.getvalue()

    def test_tmux_without_execute_emits_no_commands(self):
        out = self._run_cli("--backend", "tmux")
        self.assertNotIn("tmux new-session", out)

    def test_tmux_with_execute_emits_commands(self):
        out = self._run_cli("--backend", "tmux", "--execute")
        self.assertIn("tmux new-session", out)
        self.assertIn(str(self.target), out)


if __name__ == "__main__":
    unittest.main()
