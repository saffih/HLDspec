from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ArchitectureV2ContractTests(unittest.TestCase):
    def test_architecture_v2_doc_exists_and_defines_state_machine_target(self) -> None:
        text = (ROOT / "docs" / "ARCHITECTURE_V2.md").read_text(encoding="utf-8")

        required = [
            "HLDspec must be rebuilt around explicit state-machine contracts.",
            "MachineResult contract",
            "Checkpoint contract",
            "ProjectMachine",
            "RawHldConversionMachine",
            "SpecBuildPlanMachine",
            "SpeckitPreworkMachine",
            "ApprovalGateMachine",
            "SourceUpdateMachine",
            "SRP",
            "OCP",
            "DIP",
            "RunSkeptic",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_test_strategy_v2_doc_exists_and_blocks_blind_test_deletion(self) -> None:
        text = (ROOT / "docs" / "TEST_STRATEGY_V2.md").read_text(encoding="utf-8")

        required = [
            "Do not delete all tests.",
            "Contract tests",
            "Machine transition tests",
            "Renderer tests",
            "CLI adapter tests",
            "Legacy compatibility tests",
            "Delete a legacy test only in the same patch that adds a stronger V2 behavior test.",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_architecture_v2_declares_checkpoint_output_shape(self) -> None:
        text = (ROOT / "docs" / "ARCHITECTURE_V2.md").read_text(encoding="utf-8")

        for section in [
            "Current checkpoint:",
            "Blocking reason:",
            "Human decision needed:",
            "Controlling artifacts:",
            "Continuation protocol:",
            "What is not modified / not invoked:",
        ]:
            self.assertIn(section, text)


if __name__ == "__main__":
    unittest.main()
