"""Anti-drift checks for the bounded first live E2E proof record."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF_DOC = ROOT / "docs" / "FIRST_LIVE_E2E_PROOF.md"
JOURNEY3_DOC = ROOT / "docs" / "JOURNEY3_HELPER_CONTRACT.md"
REGISTRY = ROOT / "hldspec" / "helper_registry.py"


class FirstLiveE2EProofDocTests(unittest.TestCase):
    def test_proof_record_keeps_evidence_and_scope_limits_visible(self) -> None:
        self.assertTrue(PROOF_DOC.is_file(), f"missing {PROOF_DOC}")
        text = PROOF_DOC.read_text(encoding="utf-8")

        for phrase in (
            "Opus",
            "/tmp/proof-target",
            "calc/core.py",
            "calc/__init__.py",
            "tests/test_core.py",
            "## Proven",
            "## Not Proven",
            "not autonomous execution",
            "not a production execution channel",
            "/speckit-*",
            "not guaranteed side-effect-free",
            "weak models",
            "Haiku",
            "safer readiness/smoke probe is a follow-up",
            "Driver",
            "Helper",
            "RunSkeptic",
            "Human owner",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_concrete_command_identity_rejects_dot_style_in_contract_and_registry(self) -> None:
        journey3 = JOURNEY3_DOC.read_text(encoding="utf-8")
        registry = REGISTRY.read_text(encoding="utf-8")
        for text, source in ((journey3, JOURNEY3_DOC), (registry, REGISTRY)):
            with self.subTest(source=source):
                self.assertNotIn("/speckit.specify", text)
                self.assertNotIn("/speckit.plan", text)
                self.assertIn("/speckit-*", text)

    def test_docs_index_registers_the_supporting_evidence_record(self) -> None:
        index = (ROOT / "docs" / "DOCS_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("FIRST_LIVE_E2E_PROOF.md", index)


if __name__ == "__main__":
    unittest.main()
