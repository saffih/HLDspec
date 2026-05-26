from __future__ import annotations

import unittest
from pathlib import Path


class BacklogScorecardTruthTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.backlog = (self.repo / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md").read_text(
            encoding="utf-8"
        )
        self.scorecard = (self.repo / "docs" / "HLDSPEC_PRODUCT_SCORECARD.md").read_text(
            encoding="utf-8"
        )

    def test_backlog_mentions_self_dogfood_and_promoted_capability_evidence(self) -> None:
        self.assertIn("Self-dogfood", self.backlog)
        self.assertIn("tests_v2/test_self_dogfood_flow.py", self.backlog)
        self.assertIn("Promoted capability RunSkeptic evidence", self.backlog)
        self.assertIn("tests_v2/test_promoted_capability_runskeptic_gate.py", self.backlog)
        self.assertIn("RunSkeptic PASS evidence", self.backlog)

    def test_scorecard_mentions_self_dogfood_and_promoted_capability_evidence(self) -> None:
        self.assertIn("Self-dogfood", self.scorecard)
        self.assertIn("promoted capability RunSkeptic evidence", self.scorecard)
        self.assertIn("RunSkeptic PASS evidence", self.scorecard)

    def test_backlog_no_longer_contains_stale_absent_claims(self) -> None:
        stale_claims = [
            "generated templates are not complete/enforced",
            "path-contract, command-surface, use-case, and promotion tests are missing",
            "prompt-level validator exists, but gate-machine enforcement remains",
            "Desired structure is documented; generated templates are not complete/enforced",
            "Some tests exist; path-contract, command-surface, use-case, and promotion tests are missing",
        ]
        for claim in stale_claims:
            self.assertNotIn(claim, self.backlog)

    def test_backlog_records_generated_speckit_prompts_and_validators_as_existing(self) -> None:
        self.assertIn("Seven bounded SpecKit phase prompts are generated", self.backlog)
        self.assertIn("hldspec/validators.py", self.backlog)
        self.assertIn("scripts/validate_hldspec_target.py", self.backlog)
        self.assertIn("context_prompt_validation.json", self.backlog)

    def test_scorecard_still_blocks_product_ready_claim(self) -> None:
        self.assertRegex(self.scorecard, r"HLDspec is not fully product-ready\.?")
        self.assertIn("Overall current mark: 6/10", self.scorecard)
        self.assertIn("## Remaining blockers", self.scorecard)
        self.assertIn("Do not raise the overall mark above 7", self.scorecard)


if __name__ == "__main__":
    unittest.main()
