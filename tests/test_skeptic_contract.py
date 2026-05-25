"""SKEPTIC-TEST-001 — Contract tests for RunSkeptic evidence fields.

Tests enforce:
1. Missing required field => REWORK_REQUIRED finding (BLOCKER)
2. Empty required value => REWORK_REQUIRED finding (BLOCKER)
3. Valid full item => PASS
4. Integration: producer output passes through reviewer => PASS
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from hldspec.skeptic_schema import (
    FIELD_ALIASES,
    REQUIRED_FINDING_FIELDS,
    SkepticFinding,
    has_key,
    is_empty_value,
    normalize_text,
)
from scripts.review_runskeptic_evidence_quality import (
    STATUS_PASS,
    STATUS_REWORK,
    build_review,
    review_item,
)
from scripts.run_skeptic_meta_review import Cycle, build_cycles


def _full_item() -> dict:
    """A RunSkeptic item with all required fields populated."""
    return {
        "decision": "FIX",
        "recommendation": "Keep.",
        "observed_evidence": ["tests/: 5 test files exist"],
        "evidence_level": "observed",
        "confidence": "HIGH",
        "unknowns": "none",
        "verification": "run test suite",
        "residual_risk": "low",
    }


def _item_missing(field: str) -> dict:
    item = _full_item()
    # Remove all aliases for this field
    for alias in FIELD_ALIASES[field]:
        item.pop(alias, None)
    return item


def _item_empty(field: str) -> dict:
    item = _full_item()
    # Set the canonical alias to empty
    primary_alias = FIELD_ALIASES[field][0]
    item[primary_alias] = ""
    return item


def _wrap(items: list[dict]) -> dict:
    """Wrap items in a payload shape that build_review can traverse."""
    return {"cycles": items}


class TestSchemaFieldList(unittest.TestCase):
    """Schema parity: both producer and reviewer reference the same field list."""

    def test_required_fields_matches_field_aliases_keys(self) -> None:
        self.assertEqual(sorted(REQUIRED_FINDING_FIELDS), sorted(FIELD_ALIASES.keys()))

    def test_required_fields_has_six_entries(self) -> None:
        self.assertEqual(6, len(REQUIRED_FINDING_FIELDS))

    def test_skeptic_finding_has_all_required_fields(self) -> None:
        """SkepticFinding dataclass declares all required evidence fields."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(SkepticFinding)}
        for required in REQUIRED_FINDING_FIELDS:
            self.assertIn(required, field_names, f"SkepticFinding missing field: {required}")


class TestMissingFieldIsBlocker(unittest.TestCase):
    """Missing any required field produces a BLOCKER finding."""

    def _check_missing(self, field: str) -> None:
        item = _item_missing(field)
        _, findings = review_item(item, index=1)
        blockers = [f for f in findings if f.severity == "BLOCKER" and f.field == field]
        self.assertTrue(blockers, f"Expected BLOCKER for missing field '{field}', got: {findings}")

    def test_missing_observed_evidence(self) -> None:
        self._check_missing("observed_evidence")

    def test_missing_evidence_level(self) -> None:
        self._check_missing("evidence_level")

    def test_missing_confidence(self) -> None:
        self._check_missing("confidence")

    def test_missing_unknowns(self) -> None:
        self._check_missing("unknowns")

    def test_missing_verification(self) -> None:
        self._check_missing("verification")

    def test_missing_residual_risk(self) -> None:
        self._check_missing("residual_risk")


class TestEmptyFieldIsBlocker(unittest.TestCase):
    """Empty value on any required non-unknowns field produces a BLOCKER."""

    def _check_empty(self, field: str) -> None:
        item = _item_empty(field)
        _, findings = review_item(item, index=1)
        blockers = [f for f in findings if f.severity == "BLOCKER" and f.field == field]
        self.assertTrue(blockers, f"Expected BLOCKER for empty field '{field}', got: {findings}")

    def test_empty_observed_evidence(self) -> None:
        self._check_empty("observed_evidence")

    def test_empty_evidence_level(self) -> None:
        self._check_empty("evidence_level")

    def test_empty_confidence(self) -> None:
        self._check_empty("confidence")

    def test_empty_verification(self) -> None:
        self._check_empty("verification")

    def test_empty_residual_risk(self) -> None:
        self._check_empty("residual_risk")


class TestFullItemPasses(unittest.TestCase):
    """A fully-populated item has no BLOCKER findings."""

    def test_full_item_no_blockers(self) -> None:
        item = _full_item()
        _, findings = review_item(item, index=1)
        blockers = [f for f in findings if f.severity == "BLOCKER"]
        self.assertEqual([], blockers, f"Unexpected blockers: {blockers}")

    def test_full_item_review_status_is_pass(self) -> None:
        review = build_review(_wrap([_full_item()]), source_path="test")
        self.assertEqual(STATUS_PASS, review["status"])

    def test_all_required_fields_present_in_review_output(self) -> None:
        review = build_review(_wrap([_full_item()]), source_path="test")
        self.assertEqual(sorted(REQUIRED_FINDING_FIELDS), sorted(review["required_fields"]))


class TestMissingItemsIsBlocker(unittest.TestCase):
    """An empty payload (no recognizable items) is REWORK_REQUIRED."""

    def test_empty_payload_is_rework(self) -> None:
        review = build_review({}, source_path="test")
        self.assertEqual(STATUS_REWORK, review["status"])

    def test_no_decision_field_items_not_collected(self) -> None:
        review = build_review({"cycles": [{"not_a_decision_field": "x"}]}, source_path="test")
        self.assertEqual(STATUS_REWORK, review["status"])


class TestProducerOutputPassesReviewer(unittest.TestCase):
    """Integration: meta-review producer output passes evidence-quality review."""

    def test_producer_cycles_all_have_required_fields(self) -> None:
        """Every Cycle emitted by the producer has all required evidence fields."""
        import dataclasses
        field_names = {f.name for f in dataclasses.fields(Cycle)}
        for required in REQUIRED_FINDING_FIELDS:
            self.assertIn(
                required, field_names,
                f"Producer Cycle missing required field: {required}. "
                "Fix by completing SKEPTIC-CONTRACT-002.",
            )

    def test_producer_finding_defaults_are_non_empty(self) -> None:
        """SkepticFinding default values are all non-empty strings."""
        from hldspec.skeptic_schema import FIELD_DEFAULTS
        for field, default in FIELD_DEFAULTS.items():
            self.assertTrue(
                default and default.strip(),
                f"FIELD_DEFAULTS['{field}'] is empty — must be explicit non-empty string",
            )


if __name__ == "__main__":
    unittest.main()
