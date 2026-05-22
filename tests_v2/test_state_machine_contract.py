from __future__ import annotations

import unittest

from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    ExitCode,
    HumanQuestion,
    MachineStatus,
    blocked_result,
    done_result,
    human_checkpoint,
)


class StateMachineContractV2Tests(unittest.TestCase):
    def test_human_checkpoint_maps_to_exit_code_2(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="HLD-019 - Milestones",
                    question="Keep or split?",
                    options=("KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"),
                ),
            ),
            controlling_artifacts=(ArtifactRef(path="queue.json", role="decision_queue"),),
            next_action="Update the decision queue and rerun HLDspec.",
            forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit."),
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual(ExitCode.HUMAN_CHECKPOINT_REQUIRED, result.exit_code())
        self.assertTrue(result.requires_human())
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_blocked_result_maps_to_exit_code_3(self) -> None:
        result = blocked_result(
            machine="SpecBuildPlanMachine",
            state="SPEC_BUILD_PLAN_CHECKPOINT",
            blocking_reason="Spec build plan is not green.",
        )

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual(ExitCode.GATE_BLOCKED, result.exit_code())

    def test_done_result_maps_to_ok(self) -> None:
        result = done_result(machine="RawHldConversionMachine", state="WORKING_HLD_CONVERTED")
        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual(ExitCode.OK, result.exit_code())


if __name__ == "__main__":
    unittest.main()
