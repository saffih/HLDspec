"""Session artifacts must resolve through the pointer-aware source-package resolver.

Closes the documented control-plane leak: `write_session_artifacts` (the writer)
built a non-pointer-aware adapter, so in external mode it wrote `session_plan.json`
+ subagent packets into `target/.hldspec/source_package/` — a control-plane leak
(Option C) AND a write/read split: the continuation gate reader
(`session_continue_preflight`) already resolves the controller root, so the gate was
silently bypassed (no plan found → `gated=False`). After this slice both resolve
through `hld_source_package.source_package_paths()`.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import control_paths, hld_source_package, run_state
from hldspec import session_control as sc


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


class SessionArtifactsResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-session-")
        self.root = Path(self._tmp.name).resolve()  # immune to /var -> /private/var
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()
        self.plan = sc.build_session_plan(self.target, self.root / "hldspec")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # 1. Legacy no-pointer: artifacts still write to the in-target source package.
    def test_legacy_no_pointer_writes_in_target(self) -> None:
        written = sc.write_session_artifacts(self.target, self.plan)
        in_target = self.target / ".hldspec" / "source_package"
        self.assertTrue((in_target / sc.SESSION_PLAN_FILE).is_file())
        self.assertTrue((in_target / "subagent_packets" / "basepack_packet.md").is_file())
        self.assertEqual(written[sc.SESSION_PLAN_FILE], in_target / sc.SESSION_PLAN_FILE)

    # 2. External mode: artifacts write to the controller, NOT the target.
    def test_external_writes_to_controller_not_target(self) -> None:
        _write_pointer(self.target, self.controller)
        written = sc.write_session_artifacts(self.target, self.plan)
        ctrl_pkg = self.controller / ".hldspec" / "source_package"
        self.assertTrue((ctrl_pkg / sc.SESSION_PLAN_FILE).is_file())
        self.assertTrue((ctrl_pkg / "subagent_packets" / "runner_packet.md").is_file())
        self.assertEqual(written[sc.SESSION_PLAN_FILE], ctrl_pkg / sc.SESSION_PLAN_FILE)
        self.assertFalse(
            (self.target / ".hldspec" / "source_package").exists(),
            "external write must not leak the control plane into the target",
        )

    # 3. HEADLINE round-trip: in external mode the writer and the continuation gate
    #    agree on location, so the gate is no longer silently bypassed.
    def test_external_round_trip_preflight_gates(self) -> None:
        _write_pointer(self.target, self.controller)
        sc.write_session_artifacts(self.target, self.plan)
        preflight = sc.session_continue_preflight(self.target, check_dirty=False)
        self.assertTrue(
            preflight.gated,
            "external write must land where preflight reads, so the gate engages "
            "(pre-fix the plan was in-target while preflight read the controller)",
        )

    # 4. Write and read resolve to the SAME dir (the pointer-aware resolver).
    def test_write_read_agree_on_controller_dir(self) -> None:
        _write_pointer(self.target, self.controller)
        written = sc.write_session_artifacts(self.target, self.plan)
        resolved, _mirror = hld_source_package.source_package_paths(self.target)
        self.assertEqual(written[sc.SESSION_PLAN_FILE].parent, resolved)
        self.assertEqual(resolved, control_paths.resolve_hldspec_dir(self.target) / "source_package")

    # 7. No .specify/ mutation — session artifacts are control plane, not the mirror.
    def test_no_specify_mutation(self) -> None:
        _write_pointer(self.target, self.controller)
        sc.write_session_artifacts(self.target, self.plan)
        self.assertFalse((self.target / ".specify").exists())
        self.assertFalse((self.controller / ".specify").exists())

    # EQG-13: re-running overwrites in place; no duplication, same file set.
    def test_idempotent_rewrite(self) -> None:
        _write_pointer(self.target, self.controller)
        first = sc.write_session_artifacts(self.target, self.plan)
        second = sc.write_session_artifacts(self.target, self.plan)
        self.assertEqual(set(first), set(second))
        self.assertEqual(
            {k: str(v) for k, v in first.items()}, {k: str(v) for k, v in second.items()}
        )


if __name__ == "__main__":
    unittest.main()
