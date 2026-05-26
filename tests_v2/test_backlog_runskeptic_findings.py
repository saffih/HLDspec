from __future__ import annotations

import unittest
from pathlib import Path


class BacklogRunSkepticFindingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]

    def test_backlog_records_readiness_mark_and_current_p0_items(self) -> None:
        text = (self.repo / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("Overall current mark: 6/10", text)
        self.assertNotIn("Overall current mark: 5/10", text)

        for phrase in (
            "P0-001 External IO enforcement across all write paths",
            "P0-002 Guarded product-flow integration",
            "P0-003 End-to-end journey tests",
            "P0-004 Stale artifact and diff handling",
            "P0-005 Domain validators before product-stable promotion",
            "P0-006 RunSkeptic status propagation",
            "Mostly addressed former P0 items",
        ):
            self.assertIn(phrase, text)

        for phrase in (
            "Context economy",
            "SpecKit prompts",
            "Validators",
            "RunSkeptic enforcement",
            "Promotion gate",
            "Self-dogfood",
            "Promoted capability RunSkeptic evidence",
        ):
            self.assertIn(phrase, text)

    def test_backlog_records_path_and_command_conflicts(self) -> None:
        text = (self.repo / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("CONFLICT-003 First-run and sync path ownership", text)
        self.assertIn("CONFLICT-004 Use-case API doc vs current facade", text)
        self.assertIn("target/.hldspec/sync", text)
        self.assertIn("target/.hldspec/events.jsonl", text)
        self.assertIn("target/.specify/", text)

    def test_usecase_doc_has_complete_catalog_and_command_status(self) -> None:
        text = (self.repo / "docs" / "HLDSPEC_USE_CASES_AND_API.md").read_text(encoding="utf-8")
        self.assertIn("Current command surface status - 2026-05-26", text)
        self.assertIn("UC-001 start with no source yet", text)
        self.assertIn("UC-023 completed history / merged-work audit", text)
        self.assertIn("current", text)
        self.assertIn("future", text)
        self.assertIn("legacy/debug", text)

    def test_product_scorecard_has_current_mark(self) -> None:
        text = (self.repo / "docs" / "HLDSPEC_PRODUCT_SCORECARD.md").read_text(encoding="utf-8")
        self.assertIn("Current readiness mark - 2026-05-26", text)
        self.assertIn("Overall current mark: 6/10", text)
        self.assertNotIn("Overall current mark: 5/10", text)
        self.assertIn("Promotion rule", text)
        self.assertIn("not product-ready", text)


if __name__ == "__main__":
    unittest.main()
