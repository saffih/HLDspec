from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.approval_gate import ApprovalGateMachine
from hldspec.state_machine import MachineContext, MachineStatus


def _pointer(target: Path, controller: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / ".hldspec-run.json").write_text(
        json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
    )


class ApprovalGateHandoffDocsTests(unittest.TestCase):
    def test_approval_gate_references_architecture_and_product_handoff(self) -> None:
        work = Path(tempfile.mkdtemp())
        result = ApprovalGateMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        assert result.checkpoint is not None
        roles = {artifact.role for artifact in result.checkpoint.controlling_artifacts}
        self.assertIn("architecture_handoff", roles)
        self.assertIn("product_handoff", roles)
        self.assertIn("architecture_handoff.md", result.checkpoint.next_action)
        self.assertIn("product_handoff.md", result.checkpoint.next_action)


class ApprovalGateControlSyncPathResolutionTests(unittest.TestCase):
    """A3.2c-family: ApprovalGateMachine must resolve its sync dir the same
    pointer-aware way SpecKitExecutionMachine does (PR #147) so external-
    controller mode can't split writer/reader state.
    """

    def test_external_controller_mode_reads_controller_sync(self) -> None:
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        controller_sync = controller / ".hldspec" / "sync"
        controller_sync.mkdir(parents=True, exist_ok=True)
        (controller_sync / "speckit_prework_approval.json").write_text(
            json.dumps({"status": "APPROVED"}), encoding="utf-8"
        )

        result = ApprovalGateMachine().run(
            MachineContext(repo_root=".", workspace=str(ws), metadata={"workspace_layout": "new"})
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECKIT_PREWORK_APPROVED", result.state)
        self.assertFalse((ws / ".hldspec").exists())

    def test_legacy_layout_default_unaffected_by_controller_pointer(self) -> None:
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        legacy_sync = ws / "firstrun" / ".specify" / "sync"
        legacy_sync.mkdir(parents=True, exist_ok=True)
        (legacy_sync / "speckit_prework_approval.json").write_text(
            json.dumps({"status": "APPROVED"}), encoding="utf-8"
        )

        result = ApprovalGateMachine().run(MachineContext(repo_root=".", workspace=str(ws)))

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECKIT_PREWORK_APPROVED", result.state)


if __name__ == "__main__":
    unittest.main()
