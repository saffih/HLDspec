from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TodoV2OperatingModelTests(unittest.TestCase):
    def test_todo_includes_roles_subagents_and_context_tailoring(self) -> None:
        text = (ROOT / "docs" / "TODO_V2.md").read_text(encoding="utf-8")

        required = [
            "Operating model: roles, subagents, and context",
            "Judge / orchestrator",
            "Product reviewer",
            "Architecture reviewer",
            "Governance reviewer",
            "Interface contract reviewer",
            "Data/state reviewer",
            "Processing behavior reviewer",
            "Security reviewer",
            "Operations reviewer",
            "RunSkeptic reviewer",
            "Uncle Bob / SOLID reviewer",
            "Context tailoring",
            "Bloat guard",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_todo_includes_safety_and_checkpoint_rules(self) -> None:
        text = (ROOT / "docs" / "TODO_V2.md").read_text(encoding="utf-8")

        required = [
            "Checkpoint communication standard",
            "Answered questions must be separated from active blocking questions.",
            "Source-HLD safety",
            "SpecKit safety",
            "do not invoke SpecKit",
            "do not write final specs manually",
            "do not implement app code",
        ]

        for item in required:
            self.assertIn(item, text)

    def test_todo_includes_product_correctness_guard(self) -> None:
        text = (ROOT / "docs" / "TODO_V2.md").read_text(encoding="utf-8")

        required = [
            "Product correctness guard",
            "HLDspec must not produce fake specs.",
            "unknown / neutral section",
            "primary_role = TBD",
            "evidence_level = unknown",
            "no architecture default",
        ]

        for item in required:
            self.assertIn(item, text)


if __name__ == "__main__":
    unittest.main()
