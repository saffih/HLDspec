"""Anti-drift tests for the contract-only SpecKit helper execution gate."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "SPECKIT_HELPER_EXECUTION_CONTRACT.md"
TRIAGE_DOC = ROOT / "docs" / "DRIVER_KISS_TDD_TRIAGE.md"


class SpeckitHelperExecutionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = DOC.read_text(encoding="utf-8")
        cls.flat_text = " ".join(cls.text.split())

    def test_speckit_unavailable_blocks_without_fallback(self) -> None:
        self.assertIn("`STOP / SKILL_UNAVAILABLE`", self.text)
        self.assertIn("There is no manual fallback", self.flat_text)

    def test_guide_only_cannot_execute(self) -> None:
        self.assertIn("At `GUIDE_ONLY`", self.text)
        self.assertIn("cannot execute SpecKit", self.text)

    def test_specify_required_before_analyze(self) -> None:
        self.assertIn("`/specify` to `/analyze` | `SPECIFY_RECEIPT`", self.text)

    def test_analyze_required_before_plan(self) -> None:
        self.assertIn("`/analyze` to `/plan` | `ANALYZE_RECEIPT`", self.text)

    def test_plan_required_before_tasks(self) -> None:
        self.assertIn("`/plan` to `/tasks` | `PLAN_RECEIPT`", self.text)

    def test_tasks_required_before_implementation(self) -> None:
        self.assertIn("`/tasks` to implementation/testing | `TASKS_RECEIPT` and human approval", self.text)

    def test_stale_receipt_rejected(self) -> None:
        self.assertIn("A stale receipt is rejected.", self.text)

    def test_wrong_target_receipt_rejected(self) -> None:
        self.assertIn("A receipt for a different target is rejected.", self.flat_text)

    def test_manual_fallback_language_rejected(self) -> None:
        self.assertIn(
            "Manual fallback is not a valid substitute for missing SpecKit availability or missing phase receipts.",
            self.flat_text,
        )

    def test_driver_recommends_but_does_not_approve(self) -> None:
        self.assertIn("The driver recommends but does not approve.", self.flat_text)
        self.assertIn("does not approve", TRIAGE_DOC.read_text(encoding="utf-8"))

    def test_candidate_order_cannot_override_current_runtime(self) -> None:
        self.assertIn("does not alter the existing Journey 3 lifecycle", self.flat_text)
        self.assertIn("`STOP / CANONICAL_SEQUENCE_RECONCILIATION_REQUIRED`", self.text)

    def test_docs_index_registers_the_helper_contract(self) -> None:
        index = (ROOT / "docs" / "DOCS_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("SPECKIT_HELPER_EXECUTION_CONTRACT.md", index)


if __name__ == "__main__":
    unittest.main()
