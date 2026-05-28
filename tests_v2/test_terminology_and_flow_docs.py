from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CANONICAL = DOCS / "HLDSPEC_TERMINOLOGY_AND_FLOW.md"

CANONICAL_NAME = "HLDSPEC_TERMINOLOGY_AND_FLOW.md"

REQUIRED_TERMS = (
    "Judge Agent",
    "Agent Mediator",
    "HLDspec Operator",
    "SpecKit Doctor",
    "Devin Mediator",
    "Operator Facts",
    "Planned Operator State",
    "Planned Next Safe Action",
    "Implementation Agent",
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

    def test_canonical_flow_mentions_run_card_and_reassessment(self) -> None:
        text = _read(DOCS / "CANONICAL_FLOW.md")
        self.assertIn("SpecKit Run Card", text)
        self.assertIn("Execution Handoff", text)
        self.assertIn("Reassessment Point", text)

    def test_canonical_flow_states_greenfield_first_mvp_scope(self) -> None:
        text = _read(CANONICAL).lower()
        for phrase in (
            "greenfield-first MVP",
            "hld -> hldspec source package -> speckit preparation -> implementation slicing -> mediator guidance",
            "existing-product change mode is future scope",
            "Product Truth Set",
            "Feature Derivation Package",
            "overlap classification",
        ):
            self.assertIn(phrase.lower(), text)

    def test_canonical_doc_protects_operator_doctor_devin_boundary(self) -> None:
        text = _read(CANONICAL)
        self.assertIn("HLDspec Operator", text)
        self.assertIn("SpecKit Doctor", text)
        self.assertIn("Devin Mediator", text)
        self.assertIn("Operator / Doctor / Devin Mediator", text)
        self.assertIn("planned next layer is lifecycle state and next-safe-action guidance", text)
        self.assertIn("HLDspec does not mediate Devin directly", text)
        self.assertIn("Devin Mediator consumes those facts and related artifacts", text)
        self.assertIn("not interchangeable names for the", text)
        self.assertNotIn("next_safe_action.json", text)
        self.assertNotIn("speckit_operator_state.json", text)

    def test_speckit_proxy_protocol_uses_canonical_control_plane_paths(self) -> None:
        text = _read(DOCS / "SPECKIT_PROXY_PROTOCOL.md")
        self.assertIn("target/.hldspec/sync/speckit_proxy_dossier.json", text)
        self.assertIn("target/prompts/speckit/<package-id>/RUN_CARD.json", text)
        self.assertIn("Legacy `.specify/sync/speckit_proxy_dossier.*` paths", text)

    def test_speckit_proxy_protocol_uses_approved_default_policy(self) -> None:
        text = _read(DOCS / "SPECKIT_PROXY_PROTOCOL.md")
        self.assertIn("ANSWER_FROM_APPROVED_DEFAULT", text)
        self.assertNotIn("ANSWER_FROM_REASONABLE_DEFAULT", text)

    def test_deprecated_phrase_not_used_as_current_wording(self) -> None:
        # The canonical doc may list "target-spec generation" under deprecated
        # terms, but must never present it as the allowed current flow.
        text = _read(CANONICAL)
        self.assertNotIn("target-spec generation is allowed", text)


if __name__ == "__main__":
    unittest.main()
