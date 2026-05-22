from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TodoV2PlanTests(unittest.TestCase):
    def test_todo_v2_plan_exists_and_tracks_big_rewrite(self) -> None:
        text = (ROOT / "docs" / "TODO_V2.md").read_text(encoding="utf-8")

        required = [
            "HLDspec V2 TODO",
            "made by AI",
            "ProjectMachine",
            "RawHldConversionMachine",
            "ApplyHldConversionMachine",
            "SpecBuildPlanMachine",
            "SpeckitPreworkMachine",
            "ApprovalGateMachine",
            "SourceUpdateMachine",
            "RunSkepticReviewMachine",
            "ConstitutionQualityMachine",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_todo_v2_declares_next_leaps_and_stop_conditions(self) -> None:
        text = (ROOT / "docs" / "TODO_V2.md").read_text(encoding="utf-8")

        for item in [
            "Leap 1: ApplyHldConversionMachine",
            "Leap 2: SpecBuildPlanMachine",
            "Leap 3: SpeckitPreworkMachine",
            "Leap 4: V2 runner migration",
            "Stop conditions",
            "conversion decision is TBD",
            "source-HLD update is proposed",
            "SpecKit invocation is requested",
        ]:
            self.assertIn(item, text)

    def test_todo_v2_preserves_legacy_test_policy(self) -> None:
        text = (ROOT / "docs" / "TODO_V2.md").read_text(encoding="utf-8")

        self.assertIn("tests_legacy/ = old tests, kept for reference", text)
        self.assertIn("tests_v2/     = active V2 contract and machine tests", text)
        self.assertIn("Do not delete legacy tests blindly.", text)


if __name__ == "__main__":
    unittest.main()
