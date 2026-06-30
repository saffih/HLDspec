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
    build_full_hld_coverage_scope,
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


class TestBuildFullHldCoverageScope(unittest.TestCase):
    def test_returns_valid_full_hld(self):
        data = build_full_hld_coverage_scope()
        result = validate_hld_coverage_scope(data)
        self.assertTrue(result.ok, result.errors)

    def test_schema_version(self):
        self.assertEqual(build_full_hld_coverage_scope()["schema_version"], 1)

    def test_coverage_scope_is_full_hld(self):
        self.assertEqual(build_full_hld_coverage_scope()["coverage_scope"], "FULL_HLD")

    def test_active_spec_id_is_none(self):
        self.assertIsNone(build_full_hld_coverage_scope()["active_spec_id"])

    def test_defaults_lists_to_empty(self):
        data = build_full_hld_coverage_scope()
        self.assertEqual(data["selected_hld_anchor_ids"], [])
        self.assertEqual(data["source_refs"], [])
        self.assertEqual(data["notes"], [])

    def test_preserves_caller_anchor_ids(self):
        ids = ["HLD-001", "HLD-002"]
        data = build_full_hld_coverage_scope(selected_hld_anchor_ids=ids)
        self.assertEqual(data["selected_hld_anchor_ids"], ids)

    def test_preserves_caller_source_refs(self):
        refs = ["ref1", "ref2"]
        data = build_full_hld_coverage_scope(source_refs=refs)
        self.assertEqual(data["source_refs"], refs)

    def test_preserves_caller_notes(self):
        notes = ["note1"]
        data = build_full_hld_coverage_scope(notes=notes)
        self.assertEqual(data["notes"], notes)

    def test_returns_fresh_lists(self):
        a = build_full_hld_coverage_scope()
        b = build_full_hld_coverage_scope()
        self.assertIsNot(a["selected_hld_anchor_ids"], b["selected_hld_anchor_ids"])
        self.assertIsNot(a["source_refs"], b["source_refs"])
        self.assertIsNot(a["notes"], b["notes"])

    def test_does_not_alias_caller_list(self):
        ids = ["HLD-001"]
        data = build_full_hld_coverage_scope(selected_hld_anchor_ids=ids)
        data["selected_hld_anchor_ids"].append("HLD-002")
        self.assertEqual(ids, ["HLD-001"])

    def test_validates_output(self):
        data = build_full_hld_coverage_scope()
        result = validate_hld_coverage_scope(data)
        self.assertTrue(result.ok)

    def test_raises_on_duplicate_anchor_ids(self):
        with self.assertRaises(ValueError) as ctx:
            build_full_hld_coverage_scope(selected_hld_anchor_ids=["x", "x"])
        self.assertIn("generated hld coverage scope is invalid", str(ctx.exception))

    def test_raises_on_non_string_source_refs(self):
        with self.assertRaises((ValueError, TypeError)):
            build_full_hld_coverage_scope(source_refs=[1])


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
