from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CANONICAL = DOCS / "HLDSPEC_TERMINOLOGY_AND_FLOW.md"

CANONICAL_NAME = "HLDSPEC_TERMINOLOGY_AND_FLOW.md"

REQUIRED_TERMS = (
    "Judge Agent",
    "Scout Agent",
    "Architecture Reviewer",
    "Product Reviewer",
    "Governance Reviewer",
    "HLD Chunk",
    "HLD Section",
    "HLD Group",
    "Spec Package Map",
    "SpecKit Run Card",
    "Execution Handoff",
    "Reassessment Point",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class TerminologyAndFlowDocTests(unittest.TestCase):
    def test_canonical_doc_exists(self) -> None:
        self.assertTrue(CANONICAL.is_file(), f"missing {CANONICAL}")

    def test_canonical_doc_defines_all_terms(self) -> None:
        text = _read(CANONICAL)
        missing = [term for term in REQUIRED_TERMS if term not in text]
        self.assertEqual([], missing, f"canonical doc missing terms: {missing}")

    def test_docs_index_lists_it_as_authoritative(self) -> None:
        text = _read(DOCS / "DOCS_INDEX.md")
        self.assertIn(CANONICAL_NAME, text)
        self.assertIn("Authoritative", text)

    def test_architecture_v2_references_it(self) -> None:
        self.assertIn(CANONICAL_NAME, _read(DOCS / "ARCHITECTURE_V2.md"))

    def test_canonical_flow_references_it(self) -> None:
        self.assertIn(CANONICAL_NAME, _read(DOCS / "CANONICAL_FLOW.md"))

    def test_speckit_proxy_protocol_references_run_card_or_handoff(self) -> None:
        text = _read(DOCS / "SPECKIT_PROXY_PROTOCOL.md")
        self.assertTrue(
            ("SpecKit Run Card" in text) or ("Execution Handoff" in text),
            "SPECKIT_PROXY_PROTOCOL.md must reference SpecKit Run Card or Execution Handoff",
        )

    def test_deprecated_phrase_not_used_as_current_wording(self) -> None:
        # The canonical doc may list "target-spec generation" under deprecated
        # terms, but must never present it as the allowed current flow.
        text = _read(CANONICAL)
        self.assertNotIn("target-spec generation is allowed", text)


if __name__ == "__main__":
    unittest.main()
