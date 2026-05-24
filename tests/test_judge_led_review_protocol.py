from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class JudgeLedReviewProtocolTest(unittest.TestCase):
    def test_protocol_documents_human_decision_rebuild_loop(self) -> None:
        text = (ROOT / "docs" / "JUDGE_LED_REVIEW_PROTOCOL.md").read_text(encoding="utf-8")

        for phrase in [
            "Feedback Impact Map",
            "Affected Artifact",
            "Rebuild Loop",
            "What I will do after you answer",
            "Human Decision Owner",
        ]:
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
