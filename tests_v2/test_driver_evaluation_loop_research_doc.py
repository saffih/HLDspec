"""Anti-drift checks for Driver Evaluation Loop research boundaries."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "DRIVER_EVALUATION_LOOP_RESEARCH.md"


class DriverEvaluationLoopResearchDocTests(unittest.TestCase):
    def test_research_record_keeps_driver_and_authority_boundaries_explicit(self) -> None:
        self.assertTrue(DOC.is_file(), f"missing {DOC}")
        text = DOC.read_text(encoding="utf-8")

        for phrase in (
            "Driver owns route integrity",
            "Helper owns toolchain-specific commands/actions",
            "RunSkeptic is a checkpoint",
            "Human owner owns protected approvals",
            "system driver may replace the human operator",
            "not the human approver/owner",
            "no execution channel",
            "controlled brownfield fixture",
            "recognition/model-obedience probe",
            "/speckit-*",
            "/speckit.*` is abstract shorthand only",
            "Driver Evaluation Loop",
            "PASS` / `ACTION` / `BLOCKED` / `CONFLICT",
            "safer non-stateful readiness/smoke probe",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

    def test_docs_index_registers_research_record(self) -> None:
        index = (ROOT / "docs" / "DOCS_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("DRIVER_EVALUATION_LOOP_RESEARCH.md", index)


if __name__ == "__main__":
    unittest.main()
