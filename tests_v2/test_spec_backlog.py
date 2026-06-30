"""Tests for spec backlog validator.

Pins the schema contract defined in docs/MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md.
"""
from __future__ import annotations

import copy
import unittest

from hldspec.spec_backlog import (
    ALLOWED_SPEC_STATUSES,
    ALLOWED_SPEC_SIZE_CLASSES,
    ALLOWED_TARGET_MATERIALIZATION_STATES,
    SpecBacklogValidation,
    build_advisory_spec_backlog,
    select_active_spec,
    validate_spec_backlog,
)


def _valid_spec(**overrides) -> dict:
    base = {
        "spec_id": "SPEC-001",
        "title": "Test spec",
        "hld_anchor_ids": ["HLD-010"],
        "capability": "Test capability",
        "status": "PLANNED",
        "size_class": "BOUNDED_DELIVERABLE",
        "dependencies": [],
        "validation_strategy": ["unit_tests"],
        "target_materialization": "NOT_MATERIALIZED",
    }
    base.update(overrides)
    return base


def _valid_backlog(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "created_at": "2026-06-30T12:00:00Z",
        "updated_at": "2026-06-30T12:00:00Z",
        "source_refs": ["docs/example-hld.md"],
        "active_spec_id": None,
        "specs": [_valid_spec()],
    }
    base.update(overrides)
    return base


# --- Valid cases ---

class TestValidBacklog(unittest.TestCase):
    def test_valid_backlog_no_active_spec(self):
        result = validate_spec_backlog(_valid_backlog())
        self.assertTrue(result.ok, result.errors)

    def test_valid_backlog_with_selected_active_spec(self):
        spec = _valid_spec(status="SELECTED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertTrue(result.ok, result.errors)

    def test_valid_backlog_with_materialized_active_spec(self):
        spec = _valid_spec(
            status="MATERIALIZED_TO_TARGET",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertTrue(result.ok, result.errors)

    def test_empty_specs_list_passes(self):
        result = validate_spec_backlog(_valid_backlog(specs=[]))
        self.assertTrue(result.ok, result.errors)


# --- Top-level failures ---

class TestTopLevelShape(unittest.TestCase):
    def test_top_level_list_fails(self):
        result = validate_spec_backlog([])
        self.assertFalse(result.ok)
        self.assertIn("top-level must be object", result.errors)

    def test_missing_each_top_level_field(self):
        for fld in ("schema_version", "created_at", "updated_at",
                     "source_refs", "active_spec_id", "specs"):
            data = _valid_backlog()
            del data[fld]
            result = validate_spec_backlog(data)
            self.assertFalse(result.ok, f"should fail for missing {fld}")
            self.assertTrue(
                any(f"missing top-level field: {fld}" in e for e in result.errors),
                f"error should mention {fld}: {result.errors}",
            )

    def test_schema_version_not_integer_fails(self):
        result = validate_spec_backlog(_valid_backlog(schema_version="1"))
        self.assertFalse(result.ok)
        self.assertTrue(any("schema_version must be integer" in e for e in result.errors))

    def test_schema_version_bool_fails(self):
        result = validate_spec_backlog(_valid_backlog(schema_version=True))
        self.assertFalse(result.ok)
        self.assertTrue(any("schema_version must be integer" in e for e in result.errors))

    def test_created_at_not_string_fails(self):
        result = validate_spec_backlog(_valid_backlog(created_at=123))
        self.assertFalse(result.ok)
        self.assertTrue(any("created_at must be string" in e for e in result.errors))

    def test_updated_at_not_string_fails(self):
        result = validate_spec_backlog(_valid_backlog(updated_at=123))
        self.assertFalse(result.ok)
        self.assertTrue(any("updated_at must be string" in e for e in result.errors))

    def test_source_refs_not_list_fails(self):
        result = validate_spec_backlog(_valid_backlog(source_refs="not a list"))
        self.assertFalse(result.ok)
        self.assertTrue(any("source_refs must be list of strings" in e for e in result.errors))

    def test_source_refs_with_non_string_fails(self):
        result = validate_spec_backlog(_valid_backlog(source_refs=[123]))
        self.assertFalse(result.ok)
        self.assertTrue(any("source_refs must be list of strings" in e for e in result.errors))

    def test_active_spec_id_not_null_or_string_fails(self):
        result = validate_spec_backlog(_valid_backlog(active_spec_id=42))
        self.assertFalse(result.ok)
        self.assertTrue(any("active_spec_id must be null or string" in e for e in result.errors))

    def test_specs_not_list_fails(self):
        result = validate_spec_backlog(_valid_backlog(specs="not a list"))
        self.assertFalse(result.ok)
        self.assertTrue(any("specs must be list" in e for e in result.errors))

    def test_spec_entry_not_object_fails(self):
        result = validate_spec_backlog(_valid_backlog(specs=["not a dict"]))
        self.assertFalse(result.ok)
        self.assertTrue(any("must be object" in e for e in result.errors))


# --- Spec field failures ---

class TestSpecFieldValidation(unittest.TestCase):
    def test_missing_each_required_spec_field(self):
        for fld in ("spec_id", "title", "hld_anchor_ids", "capability",
                     "status", "size_class", "dependencies",
                     "validation_strategy", "target_materialization"):
            spec = _valid_spec()
            del spec[fld]
            result = validate_spec_backlog(_valid_backlog(specs=[spec]))
            self.assertFalse(result.ok, f"should fail for missing {fld}")
            self.assertTrue(
                any(f"missing required field: {fld}" in e for e in result.errors),
                f"error should mention {fld}: {result.errors}",
            )

    def test_invalid_status_fails(self):
        spec = _valid_spec(status="INVENTED")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid status: INVENTED" in e for e in result.errors))

    def test_invalid_size_class_fails(self):
        spec = _valid_spec(size_class="INVENTED")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid size_class: INVENTED" in e for e in result.errors))

    def test_invalid_target_materialization_fails(self):
        spec = _valid_spec(target_materialization="INVENTED")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("invalid target_materialization: INVENTED" in e for e in result.errors))

    def test_hld_anchor_ids_not_list_of_strings_fails(self):
        spec = _valid_spec(hld_anchor_ids="not a list")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("hld_anchor_ids must be list of strings" in e for e in result.errors))

    def test_dependencies_not_list_of_strings_fails(self):
        spec = _valid_spec(dependencies="not a list")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("dependencies must be list of strings" in e for e in result.errors))

    def test_validation_strategy_not_list_of_strings_fails(self):
        spec = _valid_spec(validation_strategy="not a list")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("validation_strategy must be list of strings" in e for e in result.errors))

    def test_optional_source_refs_not_list_of_strings_fails(self):
        spec = _valid_spec(source_refs=42)
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("source_refs must be list of strings" in e for e in result.errors))

    def test_optional_string_fields_non_string_fails(self):
        for fld in ("owner_or_scope", "reason", "notes"):
            spec = _valid_spec(**{fld: 42})
            result = validate_spec_backlog(_valid_backlog(specs=[spec]))
            self.assertFalse(result.ok, f"should fail for non-string {fld}")
            self.assertTrue(
                any(f"{fld} must be string" in e for e in result.errors),
                f"error should mention {fld}: {result.errors}",
            )


# --- Relationship failures ---

class TestRelationshipRules(unittest.TestCase):
    def test_duplicate_spec_id_fails(self):
        specs = [_valid_spec(spec_id="SPEC-001"), _valid_spec(spec_id="SPEC-001")]
        result = validate_spec_backlog(_valid_backlog(specs=specs))
        self.assertFalse(result.ok)
        self.assertTrue(any("duplicate spec_id: SPEC-001" in e for e in result.errors))

    def test_active_spec_id_unknown_fails(self):
        data = _valid_backlog(active_spec_id="SPEC-999")
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("active_spec_id does not match any spec_id: SPEC-999" in e for e in result.errors))

    def test_active_status_while_active_spec_id_none_fails(self):
        spec = _valid_spec(status="SELECTED")
        data = _valid_backlog(active_spec_id=None, specs=[spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("multiple active specs" in e for e in result.errors))

    def test_active_spec_id_set_but_no_active_status_fails(self):
        spec = _valid_spec(spec_id="SPEC-001", status="PLANNED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("active_spec_id set but no spec has active status" in e for e in result.errors))

    def test_active_spec_id_points_to_wrong_spec_fails(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="PLANNED")
        s2 = _valid_spec(spec_id="SPEC-002", status="SELECTED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[s1, s2])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("multiple active specs" in e for e in result.errors))

    def test_two_selected_specs_fail(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="SELECTED")
        s2 = _valid_spec(spec_id="SPEC-002", status="SELECTED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[s1, s2])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("multiple active specs" in e for e in result.errors))

    def test_too_large_ready_for_selection_fails(self):
        spec = _valid_spec(size_class="TOO_LARGE", status="READY_FOR_SELECTION")
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("TOO_LARGE cannot be READY_FOR_SELECTION" in e for e in result.errors))

    def test_too_large_selected_fails(self):
        spec = _valid_spec(size_class="TOO_LARGE", status="SELECTED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("TOO_LARGE cannot be SELECTED" in e for e in result.errors))

    def test_selected_spec_empty_validation_strategy_fails(self):
        spec = _valid_spec(status="SELECTED", validation_strategy=[])
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("selected spec requires non-empty validation_strategy" in e for e in result.errors))

    def test_materialized_on_non_active_spec_fails(self):
        spec = _valid_spec(
            spec_id="SPEC-002",
            status="MATERIALIZED_TO_TARGET",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[_valid_spec(), spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("MATERIALIZED_TO_SINGLE_SPEC_INPUT must be active spec" in e for e in result.errors))

    def test_two_materialized_to_single_input_fails(self):
        s1 = _valid_spec(
            spec_id="SPEC-001",
            status="MATERIALIZED_TO_TARGET",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        s2 = _valid_spec(
            spec_id="SPEC-002",
            status="MATERIALIZED_TO_TARGET",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[s1, s2])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("multiple" in e for e in result.errors))

    def test_status_materialized_but_target_not_materialized_fails(self):
        spec = _valid_spec(
            status="MATERIALIZED_TO_TARGET",
            target_materialization="NOT_MATERIALIZED",
        )
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("MATERIALIZED_TO_TARGET requires MATERIALIZED_TO_SINGLE_SPEC_INPUT" in e for e in result.errors))

    def test_target_materialized_but_status_not_materialized_fails(self):
        spec = _valid_spec(
            status="SELECTED",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("MATERIALIZED_TO_SINGLE_SPEC_INPUT requires status MATERIALIZED_TO_TARGET" in e for e in result.errors))

    def test_unknown_dependency_fails(self):
        spec = _valid_spec(dependencies=["SPEC-999"])
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("dependency not found: SPEC-999" in e for e in result.errors))

    def test_self_dependency_fails(self):
        spec = _valid_spec(dependencies=["SPEC-001"])
        result = validate_spec_backlog(_valid_backlog(specs=[spec]))
        self.assertFalse(result.ok)
        self.assertTrue(any("must not depend on itself" in e for e in result.errors))

    def test_selected_dependency_not_done_fails(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="PLANNED")
        s2 = _valid_spec(spec_id="SPEC-002", status="SELECTED", dependencies=["SPEC-001"])
        data = _valid_backlog(active_spec_id="SPEC-002", specs=[s1, s2])
        result = validate_spec_backlog(data)
        self.assertFalse(result.ok)
        self.assertTrue(any("selected dependency not done or validated: SPEC-001" in e for e in result.errors))

    def test_selected_dependency_done_passes(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="DONE")
        s2 = _valid_spec(spec_id="SPEC-002", status="SELECTED", dependencies=["SPEC-001"])
        data = _valid_backlog(active_spec_id="SPEC-002", specs=[s1, s2])
        result = validate_spec_backlog(data)
        self.assertTrue(result.ok, result.errors)

    def test_selected_dependency_validated_passes(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="VALIDATED")
        s2 = _valid_spec(spec_id="SPEC-002", status="SELECTED", dependencies=["SPEC-001"])
        data = _valid_backlog(active_spec_id="SPEC-002", specs=[s1, s2])
        result = validate_spec_backlog(data)
        self.assertTrue(result.ok, result.errors)


# --- Constants ---

class TestConstants(unittest.TestCase):
    def test_allowed_statuses_exact_set(self):
        expected = {
            "PLANNED", "READY_FOR_SELECTION", "SELECTED",
            "MATERIALIZED_TO_TARGET", "IN_IMPLEMENTATION",
            "VALIDATED", "DONE", "BLOCKED", "SUPERSEDED",
        }
        self.assertEqual(ALLOWED_SPEC_STATUSES, frozenset(expected))

    def test_allowed_size_classes_exact_set(self):
        expected = {
            "ATOMIC_TASK", "BOUNDED_DELIVERABLE",
            "SPRINT_SIZED", "TOO_LARGE",
        }
        self.assertEqual(ALLOWED_SPEC_SIZE_CLASSES, frozenset(expected))

    def test_allowed_target_materialization_states_exact_set(self):
        expected = {
            "NOT_MATERIALIZED",
            "MATERIALIZED_TO_SINGLE_SPEC_INPUT",
            "SUPERSEDED_IN_TARGET",
        }
        self.assertEqual(ALLOWED_TARGET_MATERIALIZATION_STATES, frozenset(expected))


# --- No input mutation ---

class TestNoInputMutation(unittest.TestCase):
    def test_validator_does_not_mutate_valid_input(self):
        data = _valid_backlog()
        original = copy.deepcopy(data)
        validate_spec_backlog(data)
        self.assertEqual(data, original)

    def test_validator_does_not_mutate_invalid_input(self):
        spec = _valid_spec(status="INVENTED")
        data = _valid_backlog(specs=[spec])
        original = copy.deepcopy(data)
        validate_spec_backlog(data)
        self.assertEqual(data, original)


# --- Advisory builder ---

def _ref_map(*anchors):
    """Build a minimal HLD reference map from (id, title) pairs."""
    d = {}
    for anchor_id, title in anchors:
        d[anchor_id] = {"title": title, "heading": f"## {anchor_id} - {title}"}
    return {"schema_version": 1, "anchors": d}


class TestAdvisoryBuilderValid(unittest.TestCase):
    def test_output_validates(self):
        refs = _ref_map(("HLD-010", "Auth module"), ("HLD-020", "Data layer"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="2026-06-30T00:00:00Z", updated_at="2026-06-30T00:00:00Z",
        )
        result = validate_spec_backlog(backlog)
        self.assertTrue(result.ok, result.errors)

    def test_active_spec_id_is_none(self):
        refs = _ref_map(("HLD-010", "Auth"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertIsNone(backlog["active_spec_id"])

    def test_all_specs_planned(self):
        refs = _ref_map(("HLD-010", "A"), ("HLD-020", "B"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        for spec in backlog["specs"]:
            self.assertEqual(spec["status"], "PLANNED")

    def test_all_specs_not_materialized(self):
        refs = _ref_map(("HLD-010", "A"), ("HLD-020", "B"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        for spec in backlog["specs"]:
            self.assertEqual(spec["target_materialization"], "NOT_MATERIALIZED")

    def test_spec_ids_deterministic_and_zero_padded(self):
        refs = _ref_map(("HLD-010", "A"), ("HLD-020", "B"), ("HLD-030", "C"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        ids = [s["spec_id"] for s in backlog["specs"]]
        self.assertEqual(ids, ["SPEC-001", "SPEC-002", "SPEC-003"])

    def test_input_order_preserved(self):
        refs = _ref_map(("HLD-030", "Third"), ("HLD-010", "First"), ("HLD-020", "Second"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        anchor_ids = [s["hld_anchor_ids"][0] for s in backlog["specs"]]
        self.assertEqual(anchor_ids, ["HLD-030", "HLD-010", "HLD-020"])

    def test_top_level_fields_preserved(self):
        refs = _ref_map(("HLD-010", "A"))
        backlog = build_advisory_spec_backlog(
            refs,
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-06-30T12:00:00Z",
            source_refs=["docs/hld.md"],
        )
        self.assertEqual(backlog["created_at"], "2026-01-01T00:00:00Z")
        self.assertEqual(backlog["updated_at"], "2026-06-30T12:00:00Z")
        self.assertEqual(backlog["source_refs"], ["docs/hld.md"])

    def test_omitted_source_refs_defaults_to_empty_list(self):
        refs = _ref_map(("HLD-010", "A"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertEqual(backlog["source_refs"], [])


class TestAdvisoryBuilderAnchorMapping(unittest.TestCase):
    def test_hld_anchor_ids_contains_anchor_id(self):
        refs = _ref_map(("HLD-010", "Auth"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertEqual(backlog["specs"][0]["hld_anchor_ids"], ["HLD-010"])

    def test_title_uses_available_title(self):
        refs = _ref_map(("HLD-010", "Auth module"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertEqual(backlog["specs"][0]["title"], "Auth module")

    def test_title_fallback_when_no_title(self):
        refs = {"schema_version": 1, "anchors": {"HLD-010": {}}}
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertEqual(backlog["specs"][0]["title"], "Candidate spec for HLD-010")

    def test_capability_equals_title_when_present(self):
        refs = _ref_map(("HLD-010", "Auth module"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertEqual(backlog["specs"][0]["capability"], "Auth module")

    def test_capability_fallback_when_no_title(self):
        refs = {"schema_version": 1, "anchors": {"HLD-010": {}}}
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        self.assertEqual(backlog["specs"][0]["capability"], "Address HLD-010")

    def test_uses_anchor_level_source_refs_when_present(self):
        refs = {
            "schema_version": 1,
            "anchors": {
                "HLD-010": {
                    "title": "Auth",
                    "source_refs": ["docs/hld.md#HLD-010"],
                }
            },
        }
        backlog = build_advisory_spec_backlog(
            refs,
            created_at="t",
            updated_at="t",
            source_refs=["docs/fallback.md"],
        )
        self.assertEqual(backlog["specs"][0]["source_refs"], ["docs/hld.md#HLD-010"])

    def test_uses_anchor_level_source_ref_string_when_present(self):
        refs = {
            "schema_version": 1,
            "anchors": {
                "HLD-010": {
                    "title": "Auth",
                    "source_ref": "docs/hld.md#HLD-010",
                }
            },
        }
        backlog = build_advisory_spec_backlog(refs, created_at="t", updated_at="t")
        self.assertEqual(backlog["specs"][0]["source_refs"], ["docs/hld.md#HLD-010"])

    def test_invalid_anchor_source_refs_falls_back_to_top_level_source_refs(self):
        refs = {
            "schema_version": 1,
            "anchors": {
                "HLD-010": {
                    "title": "Auth",
                    "source_refs": [123],
                }
            },
        }
        backlog = build_advisory_spec_backlog(
            refs,
            created_at="t",
            updated_at="t",
            source_refs=["docs/fallback.md"],
        )
        self.assertEqual(backlog["specs"][0]["source_refs"], ["docs/fallback.md"])


class TestAdvisoryBuilderPurity(unittest.TestCase):
    def test_does_not_mutate_input(self):
        refs = _ref_map(("HLD-010", "A"), ("HLD-020", "B"))
        original = copy.deepcopy(refs)
        build_advisory_spec_backlog(refs, created_at="t", updated_at="t")
        self.assertEqual(refs, original)

    def test_no_selected_status(self):
        refs = _ref_map(("HLD-010", "A"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        for spec in backlog["specs"]:
            self.assertNotEqual(spec["status"], "SELECTED")
            self.assertNotEqual(spec["status"], "READY_FOR_SELECTION")

    def test_no_materialization(self):
        refs = _ref_map(("HLD-010", "A"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        for spec in backlog["specs"]:
            self.assertNotIn(spec["target_materialization"], (
                "MATERIALIZED_TO_SINGLE_SPEC_INPUT", "SUPERSEDED_IN_TARGET",
            ))


class TestAdvisoryBuilderEdgeCases(unittest.TestCase):
    def test_empty_anchors_produces_valid_empty_backlog(self):
        refs = {"schema_version": 1, "anchors": {}}
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        result = validate_spec_backlog(backlog)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(backlog["specs"], [])

    def test_not_a_dict_input_returns_valid_empty_backlog(self):
        backlog = build_advisory_spec_backlog(
            "not a dict", created_at="t", updated_at="t",
        )
        result = validate_spec_backlog(backlog)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(backlog["specs"], [])

    def test_missing_anchors_key_returns_valid_empty_backlog(self):
        backlog = build_advisory_spec_backlog(
            {"schema_version": 1}, created_at="t", updated_at="t",
        )
        result = validate_spec_backlog(backlog)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(backlog["specs"], [])

    def test_anchor_with_none_meta_produces_fallback(self):
        refs = {"schema_version": 1, "anchors": {"HLD-010": None}}
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t",
        )
        result = validate_spec_backlog(backlog)
        self.assertTrue(result.ok, result.errors)
        self.assertEqual(backlog["specs"][0]["title"], "Candidate spec for HLD-010")

    def test_source_refs_not_shared_across_specs(self):
        refs = _ref_map(("HLD-010", "A"), ("HLD-020", "B"))
        backlog = build_advisory_spec_backlog(
            refs, created_at="t", updated_at="t", source_refs=["docs/hld.md"],
        )
        self.assertIsNot(backlog["specs"][0]["source_refs"], backlog["specs"][1]["source_refs"])
        backlog["specs"][0]["source_refs"].append("mutated")
        self.assertNotIn("mutated", backlog["specs"][1]["source_refs"])


# --- Active spec selector: valid behavior ---

class TestSelectActiveSpecValid(unittest.TestCase):
    def test_select_planned_spec(self):
        data = _valid_backlog(specs=[_valid_spec(status="PLANNED")])
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(validate_spec_backlog(result).ok, True)

    def test_select_ready_for_selection_spec(self):
        data = _valid_backlog(specs=[_valid_spec(status="READY_FOR_SELECTION")])
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(validate_spec_backlog(result).ok, True)

    def test_active_spec_id_set(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(result["active_spec_id"], "SPEC-001")

    def test_selected_spec_status_becomes_selected(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(result["specs"][0]["status"], "SELECTED")

    def test_target_materialization_remains_not_materialized(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(result["specs"][0]["target_materialization"], "NOT_MATERIALIZED")

    def test_non_selected_specs_unchanged(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="PLANNED")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED")
        data = _valid_backlog(specs=[s1, s2])
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(result["specs"][1]["status"], "PLANNED")
        self.assertEqual(result["specs"][1]["spec_id"], "SPEC-002")

    def test_input_not_mutated(self):
        data = _valid_backlog()
        original = copy.deepcopy(data)
        select_active_spec(data, "SPEC-001")
        self.assertEqual(data, original)

    def test_output_validates(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        validation = validate_spec_backlog(result)
        self.assertTrue(validation.ok, validation.errors)


# --- Active spec selector: error cases ---

class TestSelectActiveSpecErrors(unittest.TestCase):
    def test_non_string_spec_id_fails(self):
        data = _valid_backlog()
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, 42)
        self.assertIn("spec_id must be string", str(ctx.exception))

    def test_invalid_input_backlog_fails(self):
        with self.assertRaises(ValueError) as ctx:
            select_active_spec({"bad": True}, "SPEC-001")
        self.assertIn("input spec backlog is invalid", str(ctx.exception))

    def test_unknown_spec_id_fails(self):
        data = _valid_backlog()
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-999")
        self.assertIn("spec_id not found: SPEC-999", str(ctx.exception))

    def test_existing_active_spec_id_fails(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="SELECTED")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[s1, s2])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-002")
        self.assertIn("another active spec already exists", str(ctx.exception))

    def test_existing_selected_status_fails(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="SELECTED")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[s1, s2])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-002")
        self.assertIn("another active spec already exists", str(ctx.exception))

    def test_existing_materialized_to_target_status_fails(self):
        s1 = _valid_spec(
            spec_id="SPEC-001",
            status="MATERIALIZED_TO_TARGET",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED")
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[s1, s2])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-002")
        self.assertIn("another active spec already exists", str(ctx.exception))

    def test_too_large_fails(self):
        spec = _valid_spec(size_class="TOO_LARGE", status="PLANNED")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-001")
        self.assertIn("cannot select TOO_LARGE spec: SPEC-001", str(ctx.exception))

    def test_empty_validation_strategy_fails(self):
        spec = _valid_spec(validation_strategy=[])
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-001")
        self.assertIn("cannot select spec without validation_strategy: SPEC-001", str(ctx.exception))

    def test_unknown_dependency_fails(self):
        spec = _valid_spec(dependencies=["SPEC-999"])
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_self_dependency_fails(self):
        spec = _valid_spec(dependencies=["SPEC-001"])
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_dependency_not_done_or_validated_fails(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="PLANNED")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED", dependencies=["SPEC-001"])
        data = _valid_backlog(specs=[s1, s2])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-002")
        self.assertIn("unresolved dependency: SPEC-002 -> SPEC-001", str(ctx.exception))

    def test_dependency_done_passes(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="DONE")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED", dependencies=["SPEC-001"])
        data = _valid_backlog(specs=[s1, s2])
        result = select_active_spec(data, "SPEC-002")
        self.assertEqual(result["active_spec_id"], "SPEC-002")

    def test_dependency_validated_passes(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="VALIDATED")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED", dependencies=["SPEC-001"])
        data = _valid_backlog(specs=[s1, s2])
        result = select_active_spec(data, "SPEC-002")
        self.assertEqual(result["active_spec_id"], "SPEC-002")

    def test_non_not_materialized_target_fails(self):
        spec = _valid_spec(target_materialization="SUPERSEDED_IN_TARGET")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError) as ctx:
            select_active_spec(data, "SPEC-001")
        self.assertIn("target_materialization", str(ctx.exception))

    def test_status_blocked_fails(self):
        spec = _valid_spec(status="BLOCKED")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_status_superseded_fails(self):
        spec = _valid_spec(status="SUPERSEDED")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_status_in_implementation_fails(self):
        spec = _valid_spec(status="IN_IMPLEMENTATION")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_status_validated_fails(self):
        spec = _valid_spec(status="VALIDATED")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_status_done_fails(self):
        spec = _valid_spec(status="DONE")
        data = _valid_backlog(specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")

    def test_status_materialized_to_target_fails(self):
        spec = _valid_spec(
            status="MATERIALIZED_TO_TARGET",
            target_materialization="MATERIALIZED_TO_SINGLE_SPEC_INPUT",
        )
        data = _valid_backlog(active_spec_id="SPEC-001", specs=[spec])
        with self.assertRaises(ValueError):
            select_active_spec(data, "SPEC-001")


# --- Active spec selector: scope/purity safety ---

class TestSelectActiveSpecPurity(unittest.TestCase):
    def test_does_not_change_target_materialization(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(result["specs"][0]["target_materialization"], "NOT_MATERIALIZED")

    def test_does_not_produce_materialized_to_single_spec_input(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        for spec in result["specs"]:
            self.assertNotEqual(spec["target_materialization"], "MATERIALIZED_TO_SINGLE_SPEC_INPUT")

    def test_does_not_alter_source_refs(self):
        spec = _valid_spec(source_refs=["docs/hld.md#HLD-010"])
        data = _valid_backlog(specs=[spec])
        original_refs = copy.deepcopy(data["source_refs"])
        original_spec_refs = copy.deepcopy(spec["source_refs"])
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(result["source_refs"], original_refs)
        self.assertEqual(result["specs"][0]["source_refs"], original_spec_refs)

    def test_does_not_alter_dependencies(self):
        s1 = _valid_spec(spec_id="SPEC-001", status="DONE")
        s2 = _valid_spec(spec_id="SPEC-002", status="PLANNED", dependencies=["SPEC-001"])
        data = _valid_backlog(specs=[s1, s2])
        result = select_active_spec(data, "SPEC-002")
        self.assertEqual(result["specs"][1]["dependencies"], ["SPEC-001"])

    def test_does_not_call_builder(self):
        data = _valid_backlog()
        result = select_active_spec(data, "SPEC-001")
        self.assertEqual(len(result["specs"]), len(data["specs"]))
        self.assertEqual(result["schema_version"], data["schema_version"])


if __name__ == "__main__":
    unittest.main()
