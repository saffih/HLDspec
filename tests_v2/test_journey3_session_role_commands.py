"""Rendered role-command strings must point at the actual packet locations.

PR #32 moved the written packets to the controller source package in external mode,
but `build_session_plan`'s rendered role *commands* still hardcoded
`{target}/.hldspec/source_package/subagent_packets/...` — a path that does not exist
in external mode. This routes the *executable* command path through the same
pointer-aware resolver (`hld_source_package.source_package_paths`) that
`write_session_artifacts` uses, so command paths and written packets agree in both
modes. (The descriptor fields `packet_file`/`prompt_file` are made pointer-aware in
`tests_v2/test_journey3_session_descriptor_fields.py` — the follow-up to this slice.)
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import run_state
from hldspec import session_control as sc

_COMMAND_BACKENDS = ("dry-run", "claude", "codex", "manual")
_ROLE_FILENAME = {
    sc.BASEPACK: "basepack_packet.md",
    sc.RUNNER: "runner_packet.md",
    sc.CONSULTANT: "consultant_packet.md",
}


def _write_pointer(target: Path, controller: Path) -> None:
    (controller / ".hldspec").mkdir(parents=True, exist_ok=True)
    source = target / "HLD.md"
    source.write_text("# HLD\n", encoding="utf-8")
    run_state.write_pointer(
        target,
        controller_root=controller,
        source=source,
        source_hash="deadbeef",
        mode="external",
        agent="test",
        workflow_trigger="build_loop_ready",
        created_or_updated_at="2026-06-21T00:00:00+00:00",
    )


class RoleCommandRenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-rolecmd-")
        self.root = Path(self._tmp.name).resolve()  # immune to /var -> /private/var
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _packet_command(self, target: Path, backend: str, role: str) -> str:
        plan = sc.build_session_plan(target, self.root / "hldspec", backend=backend)
        return plan["roles"][role]["command"]

    # 1. Legacy no-pointer: commands point at the in-target packet path.
    def test_legacy_commands_point_in_target(self) -> None:
        for backend in _COMMAND_BACKENDS:
            cmd = self._packet_command(self.target, backend, sc.RUNNER)
            want = f"{self.target}/.hldspec/source_package/subagent_packets/runner_packet.md"
            self.assertIn(want, cmd, f"backend={backend}")

    # 2. HEADLINE — external mode: commands point at the controller packet path.
    def test_external_commands_point_to_controller(self) -> None:
        _write_pointer(self.target, self.controller)
        for backend in _COMMAND_BACKENDS:
            for role, fname in _ROLE_FILENAME.items():
                cmd = self._packet_command(self.target, backend, role)
                want = f"{self.controller}/.hldspec/source_package/subagent_packets/{fname}"
                self.assertIn(want, cmd, f"backend={backend} role={role}")

    # 3. External mode: commands must NOT reference the in-target packet path.
    def test_external_commands_do_not_reference_in_target_packet(self) -> None:
        _write_pointer(self.target, self.controller)
        in_target_pkt = f"{self.target}/.hldspec/source_package/subagent_packets"
        for backend in _COMMAND_BACKENDS:
            for role in _ROLE_FILENAME:
                cmd = self._packet_command(self.target, backend, role)
                self.assertNotIn(in_target_pkt, cmd, f"backend={backend} role={role}")

    # 4. Rendered command path agrees with where write_session_artifacts writes.
    def test_command_path_matches_written_packet(self) -> None:
        _write_pointer(self.target, self.controller)
        plan = sc.build_session_plan(self.target, self.root / "hldspec", backend="manual")
        written = sc.write_session_artifacts(self.target, plan)
        runner_pkt = written["runner_packet.md"]
        self.assertIn(str(runner_pkt), plan["roles"][sc.RUNNER]["command"])

    # 6/7. build_session_plan is a pure builder — writes no files, no .specify.
    def test_build_session_plan_writes_no_files(self) -> None:
        _write_pointer(self.target, self.controller)
        before_t = sorted(p.name for p in self.target.iterdir())
        sc.build_session_plan(self.target, self.root / "hldspec", backend="codex")
        self.assertEqual(before_t, sorted(p.name for p in self.target.iterdir()))
        self.assertFalse((self.target / ".specify").exists())
        self.assertFalse((self.controller / ".specify").exists())
        self.assertFalse((self.target / ".hldspec" / "source_package").exists())

    # 9. Deterministic / idempotent rendering.
    def test_idempotent_rendering(self) -> None:
        _write_pointer(self.target, self.controller)
        a = sc.build_session_plan(self.target, self.root / "hldspec", backend="codex")
        b = sc.build_session_plan(self.target, self.root / "hldspec", backend="codex")
        cmds_a = {r: e["command"] for r, e in a["roles"].items()}
        cmds_b = {r: e["command"] for r, e in b["roles"].items()}
        self.assertEqual(cmds_a, cmds_b)


if __name__ == "__main__":
    unittest.main()
