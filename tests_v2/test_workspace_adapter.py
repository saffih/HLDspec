"""Tests for TargetWorkspaceAdapter (P0-003).

Verifies:
- Legacy layout returns paths that match what ProjectMachine used to hardcode.
- New layout returns target-workspace paths (P0-003 target state).
- Invalid layout raises ValueError.
- from_workspace_str factory works.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from hldspec.workspace_adapter import TargetWorkspaceAdapter


class TestLegacyLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/workspace/run")
        self.a = TargetWorkspaceAdapter(target_root=self.root)

    def test_layout_default_is_legacy(self) -> None:
        self.assertEqual(self.a.layout, "legacy")

    def test_working_hld(self) -> None:
        self.assertEqual(self.a.working_hld, self.root / "HLD.md")

    def test_raw_hld(self) -> None:
        self.assertEqual(self.a.raw_hld, self.root / "HLD.raw.md")

    def test_hldspec_dir(self) -> None:
        self.assertEqual(self.a.hldspec_dir, self.root / ".hldspec")

    def test_specify_dir(self) -> None:
        self.assertEqual(self.a.specify_dir, self.root / ".specify")

    def test_firstrun_dir(self) -> None:
        self.assertEqual(self.a.firstrun_dir, self.root / "firstrun")

    def test_sync_dir_legacy(self) -> None:
        # Must match the path ProjectMachine used to hardcode:
        #   workspace / "firstrun" / ".specify" / "sync"
        expected = self.root / "firstrun" / ".specify" / "sync"
        self.assertEqual(self.a.sync_dir, expected)

    def test_events_path_legacy(self) -> None:
        # Must match the path ProjectMachine used to hardcode:
        #   workspace / ".specify" / "sync" / "hldspec_event_log.jsonl"
        expected = self.root / ".specify" / "sync" / "hldspec_event_log.jsonl"
        self.assertEqual(self.a.events_path, expected)


class TestNewLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/projects/myapp/target")
        self.a = TargetWorkspaceAdapter(target_root=self.root, layout="new")

    def test_working_hld(self) -> None:
        self.assertEqual(self.a.working_hld, self.root / "targetHLD" / "HLD.md")

    def test_raw_hld(self) -> None:
        self.assertEqual(self.a.raw_hld, self.root / "targetHLD" / "raw" / "HLD.raw.md")

    def test_sync_dir_new(self) -> None:
        self.assertEqual(self.a.sync_dir, self.root / ".hldspec" / "sync")

    def test_events_path_new(self) -> None:
        self.assertEqual(self.a.events_path, self.root / ".hldspec" / "events.jsonl")

    def test_hldspec_dir_same_both_layouts(self) -> None:
        legacy = TargetWorkspaceAdapter(target_root=self.root, layout="legacy")
        self.assertEqual(self.a.hldspec_dir, legacy.hldspec_dir)

    def test_firstrun_dir_new_is_tool_scratch_not_canonical_sync(self) -> None:
        self.assertEqual(self.a.firstrun_dir, self.root / ".hldspec" / "tool-runs" / "firstrun")

    def test_conversion_sync_dir_new_matches_hldspec_sync(self) -> None:
        self.assertEqual(self.a.conversion_sync_dir, self.a.sync_dir)


class TestFactory(unittest.TestCase):
    def test_from_workspace_str_legacy(self) -> None:
        a = TargetWorkspaceAdapter.from_workspace_str("/tmp/ws")
        self.assertEqual(a.target_root, Path("/tmp/ws"))
        self.assertEqual(a.layout, "legacy")

    def test_from_workspace_str_new(self) -> None:
        a = TargetWorkspaceAdapter.from_workspace_str("/tmp/ws", layout="new")
        self.assertEqual(a.layout, "new")

    def test_invalid_layout_raises(self) -> None:
        with self.assertRaises(ValueError):
            TargetWorkspaceAdapter(target_root=Path("/tmp"), layout="bogus")


class TestExternalLayout(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path("/projects/myapp/target")
        self.run_root = Path("/tmp/hldspec/runs/myapp-abc123")
        self.a = TargetWorkspaceAdapter(target_root=self.root, layout="new", controller_root=self.run_root)

    def test_hldspec_dir_uses_controller_root(self) -> None:
        self.assertEqual(self.a.hldspec_dir, self.run_root / ".hldspec")

    def test_sync_dir_uses_controller_root(self) -> None:
        self.assertEqual(self.a.sync_dir, self.run_root / ".hldspec" / "sync")

    def test_events_path_uses_controller_root(self) -> None:
        self.assertEqual(self.a.events_path, self.run_root / ".hldspec" / "events.jsonl")

    def test_source_package_uses_controller_root(self) -> None:
        self.assertEqual(self.a.source_package_dir, self.run_root / ".hldspec" / "source_package")

    def test_working_hld_stays_in_target(self) -> None:
        self.assertEqual(self.a.working_hld, self.root / "targetHLD" / "HLD.md")

    def test_specify_dir_stays_in_target(self) -> None:
        self.assertEqual(self.a.specify_dir, self.root / ".specify")


if __name__ == "__main__":
    unittest.main()
