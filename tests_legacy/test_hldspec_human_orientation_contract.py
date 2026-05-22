from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecHumanOrientationContractTests(unittest.TestCase):
    def test_orientation_contract_is_documented(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        catchup = (ROOT / "docs" / "HLD_AGENT_CATCHUP.md").read_text(encoding="utf-8")

        self.assertIn("Human orientation contract", agents)
        self.assertIn("Where we are", agents)
        self.assertIn("What HLDspec already did", agents)
        self.assertIn("Why we stopped", agents)
        self.assertIn("What I need from you", agents)
        self.assertIn("What I will do after you answer", agents)
        self.assertIn("Do not ask for a generic", agents)
        self.assertIn("If an artifact is missing", catchup)


if __name__ == "__main__":
    unittest.main()
