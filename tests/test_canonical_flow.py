from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CanonicalFlowTest(unittest.TestCase):
    def test_agents_points_to_canonical_flow(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        canonical = (ROOT / "docs" / "CANONICAL_FLOW.md").read_text(encoding="utf-8")

        self.assertIn("docs/CANONICAL_FLOW.md", agents)
        self.assertIn("SpecKit prework approval gate", canonical)
        self.assertIn("speckit_proxy_dossier.md/json", canonical)


if __name__ == "__main__":
    unittest.main()
