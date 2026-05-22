from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContextTailoringProtocolTests(unittest.TestCase):
    def test_context_tailoring_protocol_exists(self) -> None:
        text = (ROOT / "docs" / "CONTEXT_TAILORING_PROTOCOL.md").read_text(encoding="utf-8")

        self.assertIn("Context Tailoring Protocol", text)
        self.assertIn("weakest sufficient agent", text)
        self.assertIn("smallest sufficient context", text)
        self.assertIn("strictest sufficient prompt", text)
        self.assertIn("Cost-fit delegation", text)
        self.assertIn("Nested delegation", text)
        self.assertIn("Level 0 - deterministic tool/script", text)
        self.assertIn("Level 4 - extra-high reasoning agent", text)
        self.assertIn("Only the judge/orchestrator may", text)

    def test_protocol_is_referenced_from_agents(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")

        self.assertIn("docs/CONTEXT_TAILORING_PROTOCOL.md", text)
        self.assertIn("weakest sufficient agent", text)
        self.assertIn("smallest sufficient context", text)
        self.assertIn("strictest sufficient prompt", text)

    def test_protocol_is_referenced_from_existing_protocol_docs(self) -> None:
        expected = [
            ROOT / "docs" / "JUDGE_LED_REVIEW_PROTOCOL.md",
            ROOT / "docs" / "SPECKIT_PROXY_PROTOCOL.md",
        ]
        for path in expected:
            if path.exists():
                text = path.read_text(encoding="utf-8")
                self.assertIn("docs/CONTEXT_TAILORING_PROTOCOL.md", text, msg=str(path))

    def test_terminology_contains_context_tailoring_terms(self) -> None:
        text = (ROOT / "TERMINOLOGY.md").read_text(encoding="utf-8")

        self.assertIn("Context Tailoring", text)
        self.assertIn("Bloat Guard", text)
        self.assertIn("Cost-Fit Delegation", text)
        self.assertIn("Weakest Sufficient Agent", text)
        self.assertIn("Strictest Sufficient Prompt", text)


if __name__ == "__main__":
    unittest.main()
