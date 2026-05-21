from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SpeckitPlanningConstitutionContractTests(unittest.TestCase):
    def test_speckit_planning_constitution_contract_is_documented(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        catchup = (ROOT / "docs" / "HLD_AGENT_CATCHUP.md").read_text(encoding="utf-8")

        self.assertIn("SpecKit planning and constitution contract", agents)
        self.assertIn("user stories", agents)
        self.assertIn("use cases", agents)
        self.assertIn("user journeys", agents)
        self.assertIn("Split API/interface contracts from processing behavior", agents)
        self.assertIn("constitution_plan.md", agents)
        self.assertIn("bottom_up_implementation_plan.md", agents)
        self.assertIn("Do not start implementation before the plan and constitution are reviewed", agents)

        self.assertIn("SpecKit planning and constitution checkpoint", catchup)
        self.assertIn("API versus functionality split", catchup)
        self.assertIn("bottom-up implementation order", catchup)


if __name__ == "__main__":
    unittest.main()
