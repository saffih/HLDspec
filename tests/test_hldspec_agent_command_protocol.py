from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecAgentCommandProtocolTests(unittest.TestCase):
    def test_agent_command_protocol_document_exists(self) -> None:
        path = ROOT / "docs" / "HLDSPEC_AGENT_COMMAND.md"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")

        required = [
            "HLDspec <path-to-HLD>",
            "hldspec_run.sh = local tool runner",
            "READY_FOR_PAID_AGENT_TEST",
            "Agent-led raw HLD marking",
            "Product Reviewer",
            "Architecture Reviewer",
            "Interface/API Reviewer",
            "Data/State Reviewer",
            "Processing Behavior Reviewer",
            "Governance/Constitution Reviewer",
            "Security Reviewer",
            "Operations Reviewer",
            ".hldspec-first-run/HLD.md",
            "HLDspec prepares. SpecKit creates.",
            "Do not invoke SpecKit until the human explicitly approves the prework gate.",
            "clean separated HLD -> FIX / KEEP_PLAN / 0 flagged specs",
            "mixed API/data/processing HLD -> DECOMPOSE / SPLIT_PLANNED_SPEC",
            "explicit CONFLICTS_WITH HLD -> CONFLICT / RESOLVE_CONFLICT",
            "RunSkeptic",
        ]

        for needle in required:
            self.assertIn(needle, text)

    def test_agents_references_agent_command_protocol(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("## HLDspec agent command", text)
        self.assertIn("docs/HLDSPEC_AGENT_COMMAND.md", text)
        self.assertIn("HLDspec <path-to-HLD>", text)
        self.assertIn("hldspec_run.sh = local tool runner", text)
        self.assertIn("agent-led protocol", text)

    def test_ready_gate_doc_references_agent_command_when_present(self) -> None:
        path = ROOT / "docs" / "HLDSPEC_READY_GATE.md"
        if not path.exists():
            self.skipTest("ready gate doc is not present in this checkout")
        text = path.read_text(encoding="utf-8")

        self.assertIn("Agent command integration", text)
        self.assertIn("HLDspec <path-to-HLD>", text)
        self.assertIn("READY_FOR_PAID_AGENT_TEST", text)


if __name__ == "__main__":
    unittest.main()
