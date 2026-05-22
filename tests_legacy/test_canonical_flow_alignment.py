from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CanonicalFlowAlignmentTests(unittest.TestCase):
    def test_project_continue_uses_speckit_prework_gate(self) -> None:
        text = (ROOT / "scripts" / "project_continue.sh").read_text(encoding="utf-8")

        self.assertIn("SpecKit prework approval gate", text)
        self.assertIn("speckit_prework_quality_review.md", text)
        self.assertIn("speckit_proxy_dossier.md", text)
        self.assertIn("Do not write specs manually from HLDspec", text)
        self.assertNotIn("Next safe checkpoint: target-spec generation is allowed", text)
        self.assertNotIn("Write target specs only under the first-run workspace", text)

    def test_canonical_flow_doc_exists(self) -> None:
        text = (ROOT / "docs" / "CANONICAL_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("SpecKit prework approval gate", text)
        self.assertIn("SpecKit owns", text)
        self.assertIn("HLDspec owns", text)
        self.assertIn("target-spec generation is allowed", text)
        self.assertIn("Deprecated wording", text)

    def test_agents_references_canonical_flow(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("docs/CANONICAL_FLOW.md", text)


if __name__ == "__main__":
    unittest.main()
