from __future__ import annotations

import unittest

from hldspec.result_renderer import machine_result_to_dict, render_machine_result
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    MachineStatus,
    blocked_result,
    done_result,
    human_checkpoint,
)


class MachineResultRendererTests(unittest.TestCase):
    def test_renderer_outputs_standard_checkpoint_sections(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="Milestones",
                    question="Should milestones be kept or split?",
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

        text = render_machine_result(result)

        self.assertIn("Machine: RawHldConversionMachine", text)
        self.assertIn("State: HLD_CONVERSION_DECISIONS", text)
        self.assertIn("Status: STOP_CHECKPOINT", text)
        self.assertIn("Exit code: 2", text)
        self.assertIn("Current checkpoint: HLD_CONVERSION_DECISIONS", text)
        self.assertIn("Blocking reason:", text)
        self.assertIn("Human decision needed:", text)
        self.assertIn("Q-001 - Milestones", text)
        self.assertIn("Options: KEEP_AS_ONE, SPLIT, MODIFY_SPLIT", text)
        self.assertIn("Controlling artifacts:", text)
        self.assertIn("Continuation protocol:", text)
        self.assertIn("What is not modified / not invoked:", text)
        self.assertIn("Do not answer generic OK/continue.", text)

    def test_renderer_separates_answered_questions_from_open_questions(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="Component Deep-Dive",
                    question="Split?",
                    options=("KEEP_AS_ONE", "SPLIT_AS_PROPOSED"),
                    current_decision="SPLIT_AS_PROPOSED",
                ),
                HumanQuestion(
                    question_id="Q-002",
                    title="Milestones",
                    question="Split?",
                    options=("KEEP_AS_ONE", "SPLIT"),
                ),
            ),
            controlling_artifacts=(),
            next_action="Rerun HLDspec.",
            forbidden_actions=(),
        )

        text = render_machine_result(result)

        self.assertIn("Q-002 - Milestones", text)
        self.assertIn("Already answered decisions:", text)
        self.assertIn("- Q-001 - Component Deep-Dive -> SPLIT_AS_PROPOSED", text)

    def test_renderer_handles_blocked_result_without_human_question(self) -> None:
        result = blocked_result(
            machine="SpecBuildPlanMachine",
            state="SPEC_BUILD_PLAN_CHECKPOINT",
            blocking_reason="Spec build plan is not green.",
            controlling_artifacts=(
                ArtifactRef(path="spec_build_plan_review.md", role="review"),
            ),
            forbidden_actions=("Do not invoke SpecKit.",),
        )

        text = render_machine_result(result)

        self.assertIn("Status: BLOCKED", text)
        self.assertIn("Exit code: 3", text)
        self.assertIn("Human decision needed:", text)
        self.assertIn("- none", text)
        self.assertIn("Spec build plan is not green.", text)

    def test_machine_result_to_dict_is_json_compatible(self) -> None:
        result = done_result(
            machine="ReadyGateMachine",
            state="READY_FOR_PAID_AGENT_TEST",
            actions_run=("full_unittest_discovery",),
        )

        data = machine_result_to_dict(result)

        self.assertEqual("DONE", data["status"])
        self.assertEqual(0, data["exit_code"])
        self.assertEqual(False, data["requires_human"])
        self.assertEqual("ReadyGateMachine", data["machine"])


if __name__ == "__main__":
    unittest.main()
