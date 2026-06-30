"""Tests for coverage-scope validator.

Pins the schema contract defined in docs/ACTIVE_SPEC_COVERAGE_SCOPE_SCHEMA.md.
"""
from __future__ import annotations

import copy
import unittest

from hldspec.hld_coverage_scope import (
    ALLOWED_COVERAGE_SCOPES,
    HLD_COVERAGE_SCOPE_SCHEMA_VERSION,
    HldCoverageScopeValidation,
    validate_hld_coverage_scope,
)


def _valid_full_hld(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "coverage_scope": "FULL_HLD",
        "active_spec_id": None,
        "selected_hld_anchor_ids": [],
        "source_refs": [],
        "notes": [],
    }
    base.update(overrides)
    return base


def _valid_active_spec(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "coverage_scope": "ACTIVE_SPEC",
        "active_spec_id": "SPEC-001",
        "selected_hld_anchor_ids": ["HLD-010"],
        "source_refs": [],
        "notes": [],
    }
    base.update(overrides)
    return base


class TestConstants(unittest.TestCase):
    def test_allowed_coverage_scopes(self):
        self.assertEqual(ALLOWED_COVERAGE_SCOPES, {"FULL_HLD", "ACTIVE_SPEC"})

    def test_schema_version(self):
        self.assertEqual(HLD_COVERAGE_SCOPE_SCHEMA_VERSION, 1)


class TestValidFullHld(unittest.TestCase):
    def test_valid_full_hld_empty_anchors(self):
        result = validate_hld_coverage_scope(_valid_full_hld())
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])

    def test_valid_full_hld_with_anchors(self):
        data = _valid_full_hld(selected_hld_anchor_ids=["HLD-001", "HLD-002"])
        result = validate_hld_coverage_scope(data)
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])

    def test_valid_full_hld_with_source_refs_and_notes(self):
        data = _valid_full_hld(source_refs=["ref1"], notes=["note1"])
        result = validate_hld_coverage_scope(data)
        self.assertTrue(result.ok)


class TestValidActiveSpec(unittest.TestCase):
    def test_valid_active_spec(self):
        result = validate_hld_coverage_scope(_valid_active_spec())
        self.assertTrue(result.ok)
        self.assertEqual(result.errors, [])

    def test_valid_active_spec_multiple_anchors(self):
        data = _valid_active_spec(
            selected_hld_anchor_ids=["HLD-010", "HLD-020", "HLD-030"]
        )
        result = validate_hld_coverage_scope(data)
        self.assertTrue(result.ok)


class TestInvalidObject(unittest.TestCase):
    def test_non_dict_fails(self):
        result = validate_hld_coverage_scope("not a dict")
        self.assertFalse(result.ok)
        self.assertIn("scope must be object", result.errors)

    def test_none_fails(self):
        result = validate_hld_coverage_scope(None)
        self.assertFalse(result.ok)

    def test_list_fails(self):
        result = validate_hld_coverage_scope([])
        self.assertFalse(result.ok)


class TestMissingFields(unittest.TestCase):
    def test_missing_schema_version(self):
        data = _valid_full_hld()
        del data["schema_version"]
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("missing required field: schema_version", result.errors)

    def test_missing_coverage_scope(self):
        data = _valid_full_hld()
        del data["coverage_scope"]
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("missing required field: coverage_scope", result.errors)

    def test_missing_active_spec_id(self):
        data = _valid_full_hld()
        del data["active_spec_id"]
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("missing required field: active_spec_id", result.errors)

    def test_missing_selected_hld_anchor_ids(self):
        data = _valid_full_hld()
        del data["selected_hld_anchor_ids"]
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("missing required field: selected_hld_anchor_ids", result.errors)

    def test_missing_source_refs(self):
        data = _valid_full_hld()
        del data["source_refs"]
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("missing required field: source_refs", result.errors)

    def test_missing_notes(self):
        data = _valid_full_hld()
        del data["notes"]
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("missing required field: notes", result.errors)


class TestInvalidFieldValues(unittest.TestCase):
    def test_wrong_schema_version_value(self):
        data = _valid_full_hld(schema_version=2)
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("schema_version must be 1", result.errors)

    def test_schema_version_string(self):
        data = _valid_full_hld(schema_version="1")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("schema_version must be 1", result.errors)

    def test_schema_version_bool(self):
        data = _valid_full_hld(schema_version=True)
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("schema_version must be 1", result.errors)

    def test_non_string_coverage_scope(self):
        data = _valid_full_hld(coverage_scope=1)
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("coverage_scope must be FULL_HLD or ACTIVE_SPEC", result.errors)

    def test_unknown_coverage_scope(self):
        data = _valid_full_hld(coverage_scope="PARTIAL")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("coverage_scope must be FULL_HLD or ACTIVE_SPEC", result.errors)

    def test_anchor_ids_not_list(self):
        data = _valid_full_hld(selected_hld_anchor_ids="HLD-001")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("selected_hld_anchor_ids must be list of strings", result.errors)

    def test_anchor_ids_non_string_item(self):
        data = _valid_full_hld(selected_hld_anchor_ids=["HLD-001", 42])
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("selected_hld_anchor_ids must be list of strings", result.errors)

    def test_duplicate_anchor_ids(self):
        data = _valid_full_hld(
            selected_hld_anchor_ids=["HLD-001", "HLD-001"]
        )
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("selected_hld_anchor_ids must contain unique strings", result.errors)

    def test_source_refs_not_list(self):
        data = _valid_full_hld(source_refs="ref")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("source_refs must be list of strings", result.errors)

    def test_source_refs_non_string_item(self):
        data = _valid_full_hld(source_refs=[1])
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("source_refs must be list of strings", result.errors)

    def test_notes_not_list(self):
        data = _valid_full_hld(notes="note")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("notes must be list of strings", result.errors)

    def test_notes_non_string_item(self):
        data = _valid_full_hld(notes=[True])
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("notes must be list of strings", result.errors)


class TestFullHldRules(unittest.TestCase):
    def test_active_spec_id_non_null_fails(self):
        data = _valid_full_hld(active_spec_id="SPEC-001")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("active_spec_id must be null for FULL_HLD", result.errors)


class TestActiveSpecRules(unittest.TestCase):
    def test_active_spec_id_none_fails(self):
        data = _valid_active_spec(active_spec_id=None)
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("active_spec_id must be non-empty string for ACTIVE_SPEC", result.errors)

    def test_active_spec_id_empty_string_fails(self):
        data = _valid_active_spec(active_spec_id="")
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("active_spec_id must be non-empty string for ACTIVE_SPEC", result.errors)

    def test_active_spec_id_non_string_fails(self):
        data = _valid_active_spec(active_spec_id=42)
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("active_spec_id must be non-empty string for ACTIVE_SPEC", result.errors)

    def test_empty_anchor_ids_fails(self):
        data = _valid_active_spec(selected_hld_anchor_ids=[])
        result = validate_hld_coverage_scope(data)
        self.assertFalse(result.ok)
        self.assertIn("selected_hld_anchor_ids must be non-empty for ACTIVE_SPEC", result.errors)


class TestPurity(unittest.TestCase):
    def test_validator_does_not_mutate_input(self):
        data = _valid_full_hld(
            selected_hld_anchor_ids=["HLD-001"],
            source_refs=["ref1"],
            notes=["note1"],
        )
        original = copy.deepcopy(data)
        validate_hld_coverage_scope(data)
        self.assertEqual(data, original)

    def test_module_does_not_import_forbidden_modules(self):
        import hldspec.hld_coverage_scope as mod
        import inspect
        source = inspect.getsource(mod)
        for forbidden in ("subprocess", "os.path", "pathlib", "socket", "urllib", "requests"):
            self.assertNotIn(f"import {forbidden}", source)

    def test_no_source_package_files_created(self):
        import os
        scope_path = os.path.join(
            ".hldspec", "source_package", "hld_coverage_scope.json"
        )
        validate_hld_coverage_scope(_valid_full_hld())
        self.assertFalse(os.path.exists(scope_path))


if __name__ == "__main__":
    unittest.main()
