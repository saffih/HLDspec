from __future__ import annotations

import unittest

from hldspec.state_machine import ArtifactRef, CheckpointKind, ExitCode, HumanQuestion, MachineStatus, blocked_result, done_result, human_checkpoint


class StateMachineContractV2Tests(unittest.TestCase):
    def test_human_checkpoint_maps_to_exit_code_2(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(HumanQuestion(question_id="Q-001", title="HLD-019 - Milestones", question="Keep or split?", options=("KEEP_AS_ONE", "SPLIT")),),
            controlling_artifacts=(ArtifactRef(path="queue.json", role="decision_queue"),),
            next_action="Update the decision queue and rerun HLDspec.",
            forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit."),
        )
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual(ExitCode.HUMAN_CHECKPOINT_REQUIRED, result.exit_code())
        self.assertTrue(result.requires_human())
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_blocked_and_done_exit_codes(self) -> None:
        self.assertEqual(ExitCode.GATE_BLOCKED, blocked_result(machine="M", state="S", kind=CheckpointKind.SPEC_BUILD_PLAN_CHECKPOINT, blocking_reason="blocked").exit_code())
        self.assertEqual(ExitCode.OK, done_result(machine="M", state="S").exit_code())


if __name__ == "__main__":
    unittest.main()
