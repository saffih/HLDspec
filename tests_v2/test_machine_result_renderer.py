from __future__ import annotations

import unittest

from hldspec.result_renderer import machine_result_to_dict, render_machine_result
from hldspec.state_machine import ArtifactRef, CheckpointKind, HumanQuestion, human_checkpoint


class MachineResultRendererV2Tests(unittest.TestCase):
    def test_renderer_outputs_standard_checkpoint_sections(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(
                HumanQuestion(
                    question_id="Q-001",
                    title="HLD-019 - Milestones",
                    question="Should milestones be kept or split?",
                    options=("KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"),
                ),
            ),
            controlling_artifacts=(ArtifactRef(path="queue.json", role="decision_queue"),),
            next_action="Update the decision queue and rerun HLDspec.",
            forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit."),
        )

        text = render_machine_result(result)

        for section in [
            "Machine: RawHldConversionMachine",
            "Current checkpoint: HLD_CONVERSION_DECISIONS",
            "Blocking reason:",
            "Human decision needed:",
            "Controlling artifacts:",
            "Continuation protocol:",
            "What is not modified / not invoked:",
        ]:
            self.assertIn(section, text)

    def test_machine_result_to_dict_is_json_compatible(self) -> None:
        result = human_checkpoint(
            machine="RawHldConversionMachine",
            state="HLD_CONVERSION_DECISIONS",
            kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
            blocking_reason="Conversion decisions are still TBD.",
            questions=(),
            controlling_artifacts=(),
            next_action="Rerun.",
            forbidden_actions=(),
        )

        data = machine_result_to_dict(result)

        self.assertEqual("STOP_CHECKPOINT", data["status"])
        self.assertEqual(2, data["exit_code"])
        self.assertEqual(True, data["requires_human"])
        self.assertEqual("HLD_CONVERSION_DECISIONS", data["checkpoint"]["kind"])


if __name__ == "__main__":
    unittest.main()
