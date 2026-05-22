from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecStateDiscoveryInvocationTests(unittest.TestCase):
    def test_minimal_invocation_is_documented(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        catchup = (ROOT / "docs" / "HLD_AGENT_CATCHUP.md").read_text(encoding="utf-8")

        self.assertIn("State-discovery invocation", agents)
        self.assertIn("HLDspec", agents)
        self.assertIn("must discover the current HLDspec state", agents)
        self.assertIn("must not ask the human what command to run", agents)
        self.assertIn("hld_conversion_decision_queue.md", agents)
        self.assertIn("spec_branch_queue.md", agents)

        self.assertIn("Minimal state-discovery invocation", catchup)
        self.assertIn("The human may write only", catchup)
        self.assertIn("Ask only actual checkpoint questions", catchup)


if __name__ == "__main__":
    unittest.main()
