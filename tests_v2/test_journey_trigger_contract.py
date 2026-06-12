from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TERMINOLOGY = ROOT / "docs" / "HLDSPEC_TERMINOLOGY_AND_FLOW.md"
USE_CASES = ROOT / "docs" / "HLDSPEC_USE_CASES_AND_API.md"


class JourneyTriggerContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.terminology = TERMINOLOGY.read_text(encoding="utf-8")
        self.use_cases = USE_CASES.read_text(encoding="utf-8")

    def test_canonical_journey_names_are_defined(self) -> None:
        for text in (self.terminology, self.use_cases):
            self.assertIn("HLD Shaping", text)
            self.assertIn("SpecKit Groundwork", text)
            self.assertIn("SpecKit Build Loop Supervision", text)
            self.assertIn("formerly Implementation Guidance", text)

    def test_trigger_table_contains_requested_public_phrases(self) -> None:
        required = [
            "HLDspec inspect HLD: <path>",
            "HLDspec shape HLD: <path>",
            "HLDspec repair HLD: <path>",
            "HLDspec clarify HLD: <path>",
            "HLDspec normalize HLD: <path> target: <path>",
            "HLDspec review-hld HLD: <path> target: <path>",
            "HLDspec prepare HLD: <path> target: <path>",
            "HLDspec source-package HLD: <path> target: <path>",
            "HLDspec constitution HLD: <path> target: <path>",
            "HLDspec run-card target: <path>",
            "HLDspec prework-review target: <path>",
            "HLDspec approve-prework target: <path>",
            "HLDspec doctor target: <path>",
            "HLDspec build-loop target: <path>",
            "HLDspec watch target: <path>",
            "HLDspec build-status target: <path>",
            "HLDspec reassess target: <path>",
            "HLDspec runskeptic target: <path>",
            "HLDspec git-lifecycle target: <path>",
            "HLDspec branch-gate target: <path>",
            "HLDspec commit-gate target: <path>",
            "HLDspec merge-gate target: <path>",
            "HLDspec approve-slice target: <path> slice: <slice-id>",
            "HLDspec use HLD: <path> target: <path>",
        ]
        for phrase in required:
            self.assertIn(phrase, self.use_cases)

    def test_planned_triggers_are_not_implied_as_implemented_cli(self) -> None:
        normalized = " ".join(self.use_cases.split())
        self.assertIn("planned", self.use_cases)
        self.assertIn("not necessarily same-named CLI subcommands", normalized)
        self.assertIn("must not be documented as complete behavior", normalized)

    def test_boundary_table_names_no_fake_git_automation(self) -> None:
        self.assertIn("SpecKit owns specs/plans/tasks", self.use_cases)
        self.assertIn("no auto-merge", self.use_cases)
        self.assertIn("must not", self.use_cases)


if __name__ == "__main__":
    unittest.main()
