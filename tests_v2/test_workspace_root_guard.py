"""Regression tests for the workspace-root nesting guard (P0).

context.workspace must always be the authoritative target root. Paths that
HLDspec only ever produces as outputs (firstrun/, .hldspec/tool-runs/firstrun/,
.specify/sync/, .hldspec/sync/) must never be accepted as a workspace root,
otherwise re-deriving the adapter from such a path would nest a generated path
inside itself.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec.machines.project import ProjectMachine
from hldspec.state_machine import MachineContext, MachineStatus
from hldspec.workspace_adapter import TargetWorkspaceAdapter, reserved_workspace_root_suffix


class ReservedWorkspaceRootSuffixTests(unittest.TestCase):
    def test_legacy_firstrun_dir_is_reserved(self) -> None:
        self.assertEqual(
            reserved_workspace_root_suffix(Path("/projects/myapp/firstrun")),
            ("firstrun",),
        )

    def test_new_layout_tool_run_dir_is_reserved(self) -> None:
        self.assertEqual(
            reserved_workspace_root_suffix(Path("/projects/myapp/.hldspec/tool-runs/firstrun")),
            (".hldspec", "tool-runs", "firstrun"),
        )

    def test_specify_sync_dir_is_reserved(self) -> None:
        self.assertEqual(
            reserved_workspace_root_suffix(Path("/projects/myapp/.specify/sync")),
            (".specify", "sync"),
        )

    def test_hldspec_sync_dir_is_reserved(self) -> None:
        self.assertEqual(
            reserved_workspace_root_suffix(Path("/projects/myapp/.hldspec/sync")),
            (".hldspec", "sync"),
        )

    def test_ordinary_target_root_is_not_reserved(self) -> None:
        self.assertIsNone(reserved_workspace_root_suffix(Path("/projects/myapp/target")))


class ProjectMachineWorkspaceRootGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(tempfile.mkdtemp())
        self.source = self.repo / "HLD.md"
        self.source.write_text("# HLD\n\nBody.\n", encoding="utf-8")

    def _run(self, workspace: Path, *, layout: str = "legacy") -> tuple[MachineStatus, str]:
        context = MachineContext(
            repo_root=str(self.repo),
            source_hld=str(self.source),
            workspace=str(workspace),
            metadata={"workspace_layout": layout},
        )
        result = ProjectMachine().run(context)
        return result.status, result.state

    def test_legacy_firstrun_workspace_is_rejected_without_nesting(self) -> None:
        target = self.repo / "target"
        workspace = target / "firstrun"

        status, state = self._run(workspace, layout="legacy")

        self.assertEqual(MachineStatus.ERROR, status)
        self.assertEqual("WORKSPACE_ROOT_INVALID", state)
        # No nested firstrun/firstrun was created from the rejected root.
        self.assertFalse((workspace / "firstrun").exists())

    def test_new_layout_tool_run_workspace_is_rejected(self) -> None:
        target = self.repo / "target"
        workspace = TargetWorkspaceAdapter(target_root=target, layout="new").firstrun_dir

        status, state = self._run(workspace, layout="new")

        self.assertEqual(MachineStatus.ERROR, status)
        self.assertEqual("WORKSPACE_ROOT_INVALID", state)
        # The tool-run dir was never (re)used as a target root that derives its
        # own nested tool-runs/firstrun underneath itself.
        self.assertFalse((workspace / ".hldspec" / "tool-runs" / "firstrun").exists())

    def test_sync_dir_workspace_is_rejected(self) -> None:
        target = self.repo / "target"
        workspace = TargetWorkspaceAdapter(target_root=target, layout="new").sync_dir

        status, state = self._run(workspace, layout="new")

        self.assertEqual(MachineStatus.ERROR, status)
        self.assertEqual("WORKSPACE_ROOT_INVALID", state)

    def test_context_workspace_unchanged_by_rejected_run(self) -> None:
        target = self.repo / "target"
        workspace = target / "firstrun"
        context = MachineContext(
            repo_root=str(self.repo),
            source_hld=str(self.source),
            workspace=str(workspace),
        )

        ProjectMachine().run(context)

        self.assertEqual(str(workspace), context.workspace)


if __name__ == "__main__":
    unittest.main()
