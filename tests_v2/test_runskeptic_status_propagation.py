from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from hldspec.machines.project import ProjectMachine
from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import (
    CheckpointKind,
    MachineContext,
    MachineStatus,
    RunSkepticStatus,
    blocked_result,
)


def write_prework_workspace(root: Path, review: dict[str, object]) -> None:
    sync = root / "firstrun" / ".specify" / "sync"
    sync.mkdir(parents=True)
    (sync / "speckit_prework_package.md").write_text("prework package\n", encoding="utf-8")
    (sync / "speckit_prework_quality_review.md").write_text("review report\n", encoding="utf-8")
    (sync / "speckit_prework_quality_review.json").write_text(
        json.dumps(review, indent=2) + "\n",
        encoding="utf-8",
    )


class RunSkepticStatusPropagationTests(unittest.TestCase):
    def test_machine_result_carries_runskeptic_status(self) -> None:
        result = blocked_result(
            machine="TestMachine",
            state="BLOCKED_ON_RUNSKEPTIC",
            kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
            blocking_reason="blocked",
            runskeptic=RunSkepticStatus(status="ACTION", next_safe_action="fix findings"),
        )

        self.assertEqual(result.runskeptic.status, "ACTION")
        self.assertEqual(result.runskeptic.next_safe_action, "fix findings")

    def test_project_machine_wrap_preserves_runskeptic_status(self) -> None:
        result = blocked_result(
            machine="SpeckitPreworkMachine",
            state="SPECKIT_PREWORK_RUNSKEPTIC_REWORK",
            kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
            blocking_reason="blocked",
            runskeptic=RunSkepticStatus(status="CONFLICT", next_safe_action="escalate"),
        )

        wrapped = ProjectMachine()._wrap(result)

        self.assertEqual(wrapped.runskeptic.status, "CONFLICT")
        self.assertEqual(wrapped.runskeptic.next_safe_action, "escalate")

    def test_prework_blocks_explicit_runskeptic_conflict_before_speckit(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write_prework_workspace(
                workspace,
                {
                    "status": "PASS",
                    "runskeptic_status": "CONFLICT",
                    "findings": [],
                },
            )

            result = SpeckitPreworkMachine().run(
                MachineContext(repo_root=str(workspace), workspace=str(workspace))
            )

        self.assertEqual(result.status, MachineStatus.BLOCKED)
        self.assertEqual(result.state, "SPECKIT_PREWORK_RUNSKEPTIC_REWORK")
        self.assertEqual(result.runskeptic.status, "CONFLICT")
        self.assertIsNotNone(result.checkpoint)
        assert result.checkpoint is not None
        self.assertIn("RunSkeptic status is CONFLICT", result.checkpoint.blocking_reason)
        self.assertIn("Do not invoke SpecKit.", result.checkpoint.forbidden_actions)

    def test_prework_propagates_explicit_runskeptic_pass_on_continue(self) -> None:
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            write_prework_workspace(
                workspace,
                {
                    "status": "PASS",
                    "runskeptic_status": "PASS",
                    "findings": [],
                },
            )

            result = SpeckitPreworkMachine().run(
                MachineContext(repo_root=str(workspace), workspace=str(workspace))
            )

        self.assertEqual(result.status, MachineStatus.CONTINUE)
        self.assertEqual(result.runskeptic.status, "PASS")
        self.assertTrue(result.runskeptic.evidence)


if __name__ == "__main__":
    unittest.main()
