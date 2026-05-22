from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec.machines.approval_gate import ApprovalGateMachine
from hldspec.state_machine import MachineContext, MachineStatus


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


if __name__ == "__main__":
    unittest.main()
