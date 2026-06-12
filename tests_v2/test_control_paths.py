"""Canonical pointer-aware control-path resolver (invariant C).

External controller mode must never split state between the controller root
and target-local `.hldspec/sync` / `.specify/sync`.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec import control_paths as cp


def _pointer(target: Path, controller: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / ".hldspec-run.json").write_text(
        json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
    )


class ControlPathsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-control-paths-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_normal_target_resolves_target_local_sync(self) -> None:
        target = self.root / "target"
        self.assertEqual(target / ".hldspec", cp.resolve_hldspec_dir(target))
        self.assertEqual(target / ".hldspec" / "sync", cp.resolve_control_sync_dir(target))

    def test_external_pointer_resolves_controller_sync(self) -> None:
        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        self.assertEqual(controller, cp.resolve_controller_root(target))
        self.assertEqual(controller / ".hldspec", cp.resolve_hldspec_dir(target))
        self.assertEqual(controller / ".hldspec" / "sync", cp.resolve_control_sync_dir(target))

    def test_create_false_creates_nothing(self) -> None:
        target = self.root / "target"
        target.mkdir()
        sync = cp.resolve_control_sync_dir(target, create=False)
        self.assertFalse(sync.exists())
        self.assertFalse((target / ".hldspec").exists())

    def test_create_true_in_external_mode_creates_only_controller_sync(self) -> None:
        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        sync = cp.resolve_control_sync_dir(target, create=True)
        self.assertEqual(controller / ".hldspec" / "sync", sync)
        self.assertTrue(sync.is_dir())
        self.assertFalse((target / ".hldspec").exists())
        self.assertFalse((target / ".specify").exists())

    def test_legacy_specify_sync_requires_explicit_flag(self) -> None:
        target = self.root / "target"
        legacy = target / ".specify" / "sync"
        legacy.mkdir(parents=True)
        (legacy / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")
        markers = ("speckit_bundle_queue.json",)

        without_flag = cp.resolve_control_sync_dir(target, markers=markers)
        with_flag = cp.resolve_control_sync_dir(target, legacy_fallback=True, markers=markers)

        self.assertEqual(target / ".hldspec" / "sync", without_flag)
        self.assertEqual(legacy, with_flag)

    def test_legacy_fallback_without_marker_hit_stays_canonical(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "sync").mkdir(parents=True)  # exists, but no marker
        sync = cp.resolve_control_sync_dir(target, legacy_fallback=True, markers=("absent.json",))
        self.assertEqual(target / ".hldspec" / "sync", sync)

    def test_marker_in_canonical_wins_over_legacy(self) -> None:
        target = self.root / "target"
        canonical = target / ".hldspec" / "sync"
        legacy = target / ".specify" / "sync"
        for sync in (canonical, legacy):
            sync.mkdir(parents=True)
            (sync / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")
        resolved = cp.resolve_control_sync_dir(
            target, legacy_fallback=True, markers=("speckit_bundle_queue.json",)
        )
        self.assertEqual(canonical, resolved)

    def test_invalid_pointer_falls_back_to_target_local(self) -> None:
        # Documented fallback: a malformed pointer resolves target-local, where
        # discovery fails closed on missing/foreign control state.
        target = self.root / "target"
        target.mkdir()
        (target / ".hldspec-run.json").write_text("{not json", encoding="utf-8")
        self.assertIsNone(cp.resolve_controller_root(target))
        self.assertEqual(target / ".hldspec" / "sync", cp.resolve_control_sync_dir(target))

    def test_candidate_dirs_order_and_legacy_gate(self) -> None:
        target = self.root / "target"
        self.assertEqual(
            (target / ".hldspec" / "sync",),
            cp.candidate_control_sync_dirs(target),
        )
        self.assertEqual(
            (
                target / ".hldspec" / "sync",
                target / ".specify" / "sync",
                target / "firstrun" / ".specify" / "sync",
            ),
            cp.candidate_control_sync_dirs(target, legacy_fallback=True),
        )

    def test_external_mode_ignores_legacy_fallback_entirely(self) -> None:
        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        self.assertEqual(
            (controller / ".hldspec" / "sync",),
            cp.candidate_control_sync_dirs(target, legacy_fallback=True),
        )

    def test_external_mode_stale_legacy_marker_cannot_win(self) -> None:
        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        stale = target / ".specify" / "sync"
        stale.mkdir(parents=True)
        (stale / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")

        resolved = cp.resolve_control_sync_dir(
            target, legacy_fallback=True, markers=("speckit_bundle_queue.json",)
        )

        self.assertEqual(controller / ".hldspec" / "sync", resolved)


class MigratedHelperTests(unittest.TestCase):
    """script_io / execution-state helpers must route through the resolver."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-migrated-helpers-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_select_sync_dir_resolves_controller_in_external_mode(self) -> None:
        from hldspec.script_io import select_sync_dir

        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        sync = select_sync_dir(target, ("speckit_bundle_queue.json",))
        self.assertEqual(controller / ".hldspec" / "sync", sync)
        self.assertFalse((target / ".hldspec").exists())
        self.assertFalse((target / ".specify").exists())

    def test_select_sync_dir_keeps_existing_legacy_marker_state(self) -> None:
        from hldspec.script_io import select_sync_dir

        target = self.root / "target"
        legacy = target / ".specify" / "sync"
        legacy.mkdir(parents=True)
        (legacy / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")
        self.assertEqual(legacy, select_sync_dir(target, ("speckit_bundle_queue.json",)))

    def test_select_execution_sync_dir_resolves_controller_in_external_mode(self) -> None:
        from hldspec.speckit_execution_state import select_execution_sync_dir

        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        controller_sync = controller / ".hldspec" / "sync"
        controller_sync.mkdir(parents=True)
        (controller_sync / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")

        self.assertEqual(controller_sync, select_execution_sync_dir(target))
        created = select_execution_sync_dir(target, create=True)
        self.assertEqual(controller_sync, created)
        self.assertFalse((target / ".hldspec").exists())

    def test_select_execution_sync_dir_create_false_creates_nothing(self) -> None:
        from hldspec.speckit_execution_state import select_execution_sync_dir

        target = self.root / "target"
        target.mkdir()
        sync = select_execution_sync_dir(target)
        self.assertEqual(target / ".hldspec" / "sync", sync)
        self.assertFalse(sync.exists())

    def test_select_execution_sync_dir_ignores_stale_legacy_in_external_mode(self) -> None:
        from hldspec.speckit_execution_state import select_execution_sync_dir

        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        stale = target / ".specify" / "sync"
        stale.mkdir(parents=True)
        (stale / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")

        self.assertEqual(controller / ".hldspec" / "sync", select_execution_sync_dir(target))

    def test_select_sync_dir_ignores_stale_legacy_in_external_mode(self) -> None:
        from hldspec.script_io import select_sync_dir

        target = self.root / "target"
        controller = self.root / "controller"
        _pointer(target, controller)
        stale = target / ".specify" / "sync"
        stale.mkdir(parents=True)
        (stale / "speckit_bundle_queue.json").write_text("{}", encoding="utf-8")

        self.assertEqual(
            controller / ".hldspec" / "sync",
            select_sync_dir(target, ("speckit_bundle_queue.json",)),
        )


if __name__ == "__main__":
    unittest.main()
