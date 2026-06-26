"""Anti-drift tests for the Driver KISS/TDD triage contract."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "DRIVER_KISS_TDD_TRIAGE.md"


class DriverKissTddTriageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DOC.read_text(encoding="utf-8")

    def test_poc_defaults_to_kiss_required(self) -> None:
        self.assertIn("Proof of concept (POC) | `KISS_REQUIRED`", self.text)

    def test_simulator_defaults_to_kiss_required(self) -> None:
        self.assertIn("Simulator | `KISS_REQUIRED`", self.text)

    def test_docs_only_uses_doc_check_not_code_test(self) -> None:
        self.assertIn("`DOC_CHECK_REQUIRED`", self.text)
        self.assertIn("not a fake code test", self.text)

    def test_complexity_requires_current_risk(self) -> None:
        self.assertIn("`CURRENT_EVIDENCED_RISK`", self.text)
        self.assertIn("A hypothetical future need is not evidence.", self.text)

    def test_future_proofing_without_evidence_is_blocked(self) -> None:
        self.assertIn("future-proofing, speculation, or agent preference | `BLOCKED`", self.text)

    def test_authority_boundary_escalates_skeptic_level(self) -> None:
        self.assertIn("`SKEPTIC_ESCALATION_REQUIRED`", self.text)
        self.assertIn("human owner review", self.text)

    def test_speckit_helper_requires_phase_bypass_tests(self) -> None:
        helper_contract = (ROOT / "docs" / "SPECKIT_HELPER_EXECUTION_CONTRACT.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("negative tests for every attempted phase bypass", helper_contract)

    def test_driver_output_includes_kiss_tdd_skeptic_decision(self) -> None:
        for field in (
            "`kiss_tdd_decision`",
            "`current_evidence`",
            "`required_check`",
            "`skeptic_level`",
            "`next_safe_action`",
        ):
            with self.subTest(field=field):
                self.assertIn(field, self.text)

    def test_docs_index_registers_the_triage_contract(self) -> None:
        index = (ROOT / "docs" / "DOCS_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("DRIVER_KISS_TDD_TRIAGE.md", index)


if __name__ == "__main__":
    unittest.main()
