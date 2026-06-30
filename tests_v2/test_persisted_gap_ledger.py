"""Tests for persisted gap ledger validator.

Pins the schema contract defined in docs/PERSISTED_GAP_LEDGER_SCHEMA.md.
"""
from __future__ import annotations

import copy
import unittest

from hldspec.persisted_gap_ledger import (
    ALLOWED_GAP_CATEGORIES,
    ALLOWED_GAP_STATES,
    GapLedgerValidation,
    validate_gap_ledger,
)


def _valid_gap(**overrides) -> dict:
    base = {
        "gap_id": "CTX-001",
        "category": "context_safety_and_gap_continuity",
        "state": "OPEN",
        "summary": "test gap",
        "why_it_matters": "because",
        "source_refs": ["docs/foo.md"],
        "created_at": "2026-06-30T12:00:00Z",
        "updated_at": "2026-06-30T12:00:00Z",
    }
    base.update(overrides)
    return base


def _valid_ledger(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "created_at": "2026-06-30T12:00:00Z",
        "updated_at": "2026-06-30T12:00:00Z",
        "source_refs": ["docs/foo.md"],
        "gaps": [_valid_gap()],
    }
    base.update(overrides)
    return base


class TestValidMinimalLedger(unittest.TestCase):
    def test_valid_minimal_ledger_passes(self):
        result = validate_gap_ledger(_valid_ledger())
        self.assertTrue(result.ok, result.errors)

    def test_empty_gaps_list_passes(self):
        result = validate_gap_ledger(_valid_ledger(gaps=[]))
        self.assertTrue(result.ok, result.errors)


class TestTopLevelShape(unittest.TestCase):
    def test_top_level_list_fails(self):
        result = validate_gap_ledger([])
        self.assertFalse(result.ok)
        self.assertIn("top-level must be object", result.errors)

    def test_top_level_string_fails(self):
        result = validate_gap_ledger("not a dict")
        self.assertFalse(result.ok)

    def test_missing_top_level_field(self):
        for field in ("schema_version", "created_at", "updated_at", "source_refs", "gaps"):
            data = _valid_ledger()
            del data[field]
            result = validate_gap_ledger(data)
            self.assertFalse(result.ok, f"should fail for missing {field}")
            self.assertTrue(
                any(f"missing top-level field: {field}" in e for e in result.errors),
                f"error should mention {field}: {result.errors}",
            )

    def test_schema_version_not_integer_fails(self):
        result = validate_gap_ledger(_valid_ledger(schema_version="1"))
        self.assertFalse(result.ok)
        self.assertTrue(any("schema_version must be integer" in e for e in result.errors))

    def test_created_at_not_string_fails(self):
        result = validate_gap_ledger(_valid_ledger(created_at=123))
        self.assertFalse(result.ok)
        self.assertTrue(any("created_at must be string" in e for e in result.errors))

    def test_updated_at_not_string_fails(self):
        result = validate_gap_ledger(_valid_ledger(updated_at=123))
        self.assertFalse(result.ok)
        self.assertTrue(any("updated_at must be string" in e for e in result.errors))

    def test_source_refs_not_list_fails(self):
        result = validate_gap_ledger(_valid_ledger(source_refs="not a list"))
        self.assertFalse(result.ok)
        self.assertTrue(any("source_refs must be list of strings" in e for e in result.errors))

    def test_source_refs_with_non_string_fails(self):
        result = validate_gap_ledger(_valid_ledger(source_refs=[123]))
        self.assertFalse(result.ok)
        self.assertTrue(any("source_refs must be list of strings" in e for e in result.errors))

    def test_gaps_not_list_fails(self):
        result = validate_gap_ledger(_valid_ledger(gaps="not a list"))
        self.assertFalse(result.ok)
        self.assertTrue(any("gaps must be list" in e for e in result.errors))


class TestGapEntryValidation(unittest.TestCase):
    def test_gap_entry_not_object_fails(self):
        result = validate_gap_ledger(_valid_ledger(gaps=["not a dict"]))
        self.assertFalse(result.ok)
        self.assertTrue(any("must be object" in e for e in result.errors))

    def test_missing_required_gap_field(self):
        for field in ("gap_id", "category", "state", "summary", "why_it_matters",
                       "source_refs", "created_at", "updated_at"):
            gap = _valid_gap()
            del gap[field]
            result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
            self.assertFalse(result.ok, f"should fail for missing {field}")
            self.assertTrue(
                any(f"missing required field: {field}" in e for e in result.errors),
                f"error should mention {field}: {result.errors}",
            )

    def test_invalid_category_fails(self):
        gap = _valid_gap(category="nonexistent_category")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid category: nonexistent_category" in e for e in result.errors))

    def test_invalid_state_fails(self):
        gap = _valid_gap(state="INVENTED")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid state: INVENTED" in e for e in result.errors))

    def test_unknown_state_fails(self):
        gap = _valid_gap(state="UNKNOWN")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid state: UNKNOWN" in e for e in result.errors))

    def test_duplicate_gap_id_fails(self):
        gaps = [_valid_gap(gap_id="DUP-1"), _valid_gap(gap_id="DUP-1")]
        result = validate_gap_ledger(_valid_ledger(gaps=gaps))
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate gap_id: DUP-1" in e for e in result.errors))

    def test_all_valid_states_accepted(self):
        for state in ALLOWED_GAP_STATES:
            gap = _valid_gap(state=state)
            if state == "SAFE_TO_DEFER":
                gap["reason"] = "ok"
                gap["owner_or_scope"] = "team"
            elif state == "ASSUMED_FOR_NOW":
                gap["assumption_text"] = "assume X"
            elif state == "RESOLVED_BY_EVIDENCE":
                gap["evidence_ref"] = "commit abc"
            elif state == "RESOLVED_BY_DECISION":
                gap["decision_ref"] = "PR #1"
            elif state == "CONFLICT":
                gap["notes"] = "conflicting sources"
            result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
            self.assertTrue(result.ok, f"state {state} should be valid: {result.errors}")

    def test_all_valid_categories_accepted(self):
        for cat in ALLOWED_GAP_CATEGORIES:
            gap = _valid_gap(category=cat)
            result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
            self.assertTrue(result.ok, f"category {cat} should be valid: {result.errors}")


class TestConditionalStateRules(unittest.TestCase):
    def test_safe_to_defer_without_reason_fails(self):
        gap = _valid_gap(state="SAFE_TO_DEFER", owner_or_scope="team")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("SAFE_TO_DEFER requires reason" in e for e in result.errors))

    def test_safe_to_defer_without_owner_or_scope_fails(self):
        gap = _valid_gap(state="SAFE_TO_DEFER", reason="safe because X")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("SAFE_TO_DEFER requires owner_or_scope" in e for e in result.errors))

    def test_safe_to_defer_with_both_passes(self):
        gap = _valid_gap(state="SAFE_TO_DEFER", reason="safe", owner_or_scope="team")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertTrue(result.ok, result.errors)

    def test_assumed_for_now_without_assumption_text_fails(self):
        gap = _valid_gap(state="ASSUMED_FOR_NOW")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("ASSUMED_FOR_NOW requires assumption_text" in e for e in result.errors))

    def test_assumed_for_now_with_assumption_text_passes(self):
        gap = _valid_gap(state="ASSUMED_FOR_NOW", assumption_text="assume X")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertTrue(result.ok, result.errors)

    def test_resolved_by_evidence_without_evidence_ref_fails(self):
        gap = _valid_gap(state="RESOLVED_BY_EVIDENCE")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("RESOLVED_BY_EVIDENCE requires evidence_ref" in e for e in result.errors))

    def test_resolved_by_evidence_with_evidence_ref_passes(self):
        gap = _valid_gap(state="RESOLVED_BY_EVIDENCE", evidence_ref="commit abc")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertTrue(result.ok, result.errors)

    def test_resolved_by_decision_without_decision_ref_fails(self):
        gap = _valid_gap(state="RESOLVED_BY_DECISION")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("RESOLVED_BY_DECISION requires decision_ref" in e for e in result.errors))

    def test_resolved_by_decision_with_decision_ref_passes(self):
        gap = _valid_gap(state="RESOLVED_BY_DECISION", decision_ref="PR #5")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertTrue(result.ok, result.errors)

    def test_conflict_without_related_or_notes_fails(self):
        gap = _valid_gap(state="CONFLICT")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertFalse(result.ok)
        self.assertTrue(any("CONFLICT requires related_gap_ids or notes" in e for e in result.errors))

    def test_conflict_with_notes_passes(self):
        gap = _valid_gap(state="CONFLICT", notes="conflicting sources")
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertTrue(result.ok, result.errors)

    def test_conflict_with_related_gap_ids_passes(self):
        gap = _valid_gap(state="CONFLICT", related_gap_ids=["CTX-002"])
        result = validate_gap_ledger(_valid_ledger(gaps=[gap]))
        self.assertTrue(result.ok, result.errors)


class TestNoInputMutation(unittest.TestCase):
    def test_validator_does_not_mutate_input(self):
        data = _valid_ledger()
        original = copy.deepcopy(data)
        validate_gap_ledger(data)
        self.assertEqual(data, original)

    def test_validator_does_not_mutate_invalid_input(self):
        data = _valid_ledger(gaps=[_valid_gap(state="UNKNOWN")])
        original = copy.deepcopy(data)
        validate_gap_ledger(data)
        self.assertEqual(data, original)


if __name__ == "__main__":
    unittest.main()
