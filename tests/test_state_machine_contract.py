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


class StateMachineContractTests(unittest.TestCase):
    def test_human_checkpoint_maps_to_exit_code_2(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="Milestones",
                    question="Keep or split?",
                    options=("KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"),
                ),
            ),
            controlling_artifacts=(
                ArtifactRef(
                    path=".hldspec-first-run/.specify/sync/hld_conversion_decision_queue.json",
                    role="decision_queue",
                ),
            ),
            next_action="Update the decision queue and rerun HLDspec.",
            forbidden_actions=(
                "Do not modify the source HLD.",
                "Do not invoke SpecKit.",
            ),
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual(ExitCode.HUMAN_CHECKPOINT_REQUIRED, result.exit_code())
        self.assertTrue(result.requires_human())
        self.assertIsNotNone(result.checkpoint)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())
        self.assertEqual(CheckpointKind.HLD_CONVERSION_DECISIONS, result.checkpoint.kind)

    def test_blocked_result_maps_to_gate_blocked(self) -> None:
        result = blocked_result(
            machine="SpecBuildPlanMachine",
            state="SPEC_BUILD_PLAN_CHECKPOINT",
            blocking_reason="Spec build plan is not green.",
            controlling_artifacts=(
                ArtifactRef(path="spec_build_plan_review.md", role="review"),
            ),
            forbidden_actions=("Do not invoke SpecKit.",),
        )

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual(ExitCode.GATE_BLOCKED, result.exit_code())
        self.assertFalse(result.requires_human())

    def test_done_result_maps_to_ok(self) -> None:
        result = done_result(
            machine="SpeckitPreworkMachine",
            state="SPECKIT_PREWORK_APPROVAL_GATE",
            actions_run=("quality_review",),
        )

        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual(ExitCode.OK, result.exit_code())
        self.assertFalse(result.requires_human())

    def test_checkpoint_distinguishes_answered_and_open_questions(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="Answered",
                    question="Already answered?",
                    options=("KEEP_AS_ONE", "SPLIT"),
                    current_decision="KEEP_AS_ONE",
                ),
                HumanQuestion(
                    question_id="Q-002",
                    title="Open",
                    question="Needs answer?",
                    options=("KEEP_AS_ONE", "SPLIT"),
                ),
            ),
            controlling_artifacts=(),
            next_action="Rerun HLDspec.",
            forbidden_actions=(),
        )

        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())


if __name__ == "__main__":
    unittest.main()
