from __future__ import annotations

import unittest
from pathlib import Path


class BacklogRunSkepticFindingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]

    def test_backlog_records_readiness_mark_and_new_p0_items(self) -> None:
        text = (self.repo / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md").read_text(encoding="utf-8")
        self.assertIn("Overall current mark: 4/10", text)
        for item in range(11, 18):
            self.assertIn(f"P0-{item:03d}", text)
        self.assertIn("Canonical target path contract", text)
        self.assertIn("Complete use-case catalog", text)
        self.assertIn("Promotion scorecard gate", text)

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
        self.assertIn("Overall current mark: 4/10", text)
        self.assertIn("Promotion rule", text)


if __name__ == "__main__":
    unittest.main()
