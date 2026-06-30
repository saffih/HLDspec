"""Tests for coverage-scope ledger interpretation.

Pins the interpretation contract: FULL_HLD vs ACTIVE_SPEC blocking semantics,
out-of-scope classification, deterministic ordering, input immutability, and
purity (no IO, no forbidden imports).
"""
from __future__ import annotations

import copy
import unittest

from hldspec.hld_coverage_scope_interpretation import (
    CoverageScopeLedgerInterpretation,
    interpret_coverage_ledger_for_scope,
)


def _valid_full_hld_scope(**overrides) -> dict:
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


def _valid_active_spec_scope(**overrides) -> dict:
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


def _ledger_item(hld_item_id: str, status: str, **overrides) -> dict:
    base = {
        "hld_item_id": hld_item_id,
        "source_section": "section-1",
        "item_type": "REQUIREMENT",
        "status": status,
    }
    base.update(overrides)
    return base


# -- FULL_HLD interpretation -------------------------------------------------


class TestFullHldInterpretation(unittest.TestCase):
    def test_not_covered_is_blocking(self):
        ledger = [_ledger_item("HLD-001", "NOT_COVERED")]
        scope = _valid_full_hld_scope()
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(len(result.blocking_items), 1)
        self.assertEqual(result.blocking_items[0]["hld_item_id"], "HLD-001")

    def test_covered_is_not_blocking(self):
        ledger = [_ledger_item("HLD-001", "COVERED_IN_SDD")]
        scope = _valid_full_hld_scope()
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.blocking_items, [])

    def test_out_of_scope_items_empty(self):
        ledger = [_ledger_item("HLD-001", "NOT_COVERED")]
        scope = _valid_full_hld_scope()
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertEqual(result.out_of_scope_items, [])

    def test_ordering_follows_ledger(self):
        ledger = [
            _ledger_item("HLD-003", "NOT_COVERED"),
            _ledger_item("HLD-001", "COVERED_IN_SDD"),
            _ledger_item("HLD-002", "NOT_COVERED"),
        ]
        scope = _valid_full_hld_scope()
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        ids = [item["hld_item_id"] for item in result.blocking_items]
        self.assertEqual(ids, ["HLD-003", "HLD-002"])

    def test_empty_ledger(self):
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=[], coverage_scope=_valid_full_hld_scope(),
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.blocking_items, [])
        self.assertEqual(result.out_of_scope_items, [])


# -- ACTIVE_SPEC interpretation -----------------------------------------------


class TestActiveSpecInterpretation(unittest.TestCase):
    def test_selected_not_covered_is_blocking(self):
        ledger = [_ledger_item("HLD-010", "NOT_COVERED")]
        scope = _valid_active_spec_scope(
            selected_hld_anchor_ids=["HLD-010"],
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(len(result.blocking_items), 1)
        self.assertEqual(result.blocking_items[0]["hld_item_id"], "HLD-010")

    def test_non_selected_not_covered_is_out_of_scope(self):
        ledger = [_ledger_item("HLD-099", "NOT_COVERED")]
        scope = _valid_active_spec_scope(
            selected_hld_anchor_ids=["HLD-010"],
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.blocking_items, [])
        self.assertEqual(len(result.out_of_scope_items), 1)
        self.assertEqual(result.out_of_scope_items[0]["hld_item_id"], "HLD-099")

    def test_selected_covered_does_not_block(self):
        ledger = [_ledger_item("HLD-010", "COVERED_IN_SDD")]
        scope = _valid_active_spec_scope(
            selected_hld_anchor_ids=["HLD-010"],
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.blocking_items, [])
        self.assertEqual(result.out_of_scope_items, [])

    def test_mixed_selected_and_non_selected(self):
        ledger = [
            _ledger_item("HLD-010", "NOT_COVERED"),
            _ledger_item("HLD-020", "NOT_COVERED"),
            _ledger_item("HLD-030", "COVERED_IN_SDD"),
            _ledger_item("HLD-040", "NOT_COVERED"),
        ]
        scope = _valid_active_spec_scope(
            selected_hld_anchor_ids=["HLD-010", "HLD-030"],
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        blocking_ids = [i["hld_item_id"] for i in result.blocking_items]
        oos_ids = [i["hld_item_id"] for i in result.out_of_scope_items]
        self.assertEqual(blocking_ids, ["HLD-010"])
        self.assertEqual(oos_ids, ["HLD-020", "HLD-040"])

    def test_ordering_follows_ledger(self):
        ledger = [
            _ledger_item("HLD-040", "NOT_COVERED"),
            _ledger_item("HLD-010", "NOT_COVERED"),
            _ledger_item("HLD-020", "NOT_COVERED"),
        ]
        scope = _valid_active_spec_scope(
            selected_hld_anchor_ids=["HLD-020", "HLD-040"],
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        blocking_ids = [i["hld_item_id"] for i in result.blocking_items]
        oos_ids = [i["hld_item_id"] for i in result.out_of_scope_items]
        self.assertEqual(blocking_ids, ["HLD-040", "HLD-020"])
        self.assertEqual(oos_ids, ["HLD-010"])


# -- Invalid input ------------------------------------------------------------


class TestInvalidInput(unittest.TestCase):
    def test_invalid_scope_returns_ok_false(self):
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=[], coverage_scope="not a dict",
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("coverage_scope invalid" in e for e in result.errors))

    def test_invalid_ledger_returns_ok_false(self):
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger="not a list",
            coverage_scope=_valid_full_hld_scope(),
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("coverage_ledger invalid" in e for e in result.errors))

    def test_invalid_ledger_item_returns_ok_false(self):
        ledger = [{"bad": "item"}]
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=_valid_full_hld_scope(),
        )
        self.assertFalse(result.ok)
        self.assertTrue(any("coverage_ledger invalid" in e for e in result.errors))

    def test_invalid_ledger_does_not_raise(self):
        try:
            result = interpret_coverage_ledger_for_scope(
                coverage_ledger=[42],
                coverage_scope=_valid_full_hld_scope(),
            )
            self.assertFalse(result.ok)
        except Exception:
            self.fail("should not raise on invalid ledger input")

    def test_both_invalid_reports_both_errors(self):
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger="bad", coverage_scope="bad",
        )
        self.assertFalse(result.ok)
        scope_errors = [e for e in result.errors if "coverage_scope invalid" in e]
        ledger_errors = [e for e in result.errors if "coverage_ledger invalid" in e]
        self.assertTrue(len(scope_errors) >= 1)
        self.assertTrue(len(ledger_errors) >= 1)

    def test_invalid_input_has_empty_classification(self):
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger="bad", coverage_scope="bad",
        )
        self.assertEqual(result.blocking_items, [])
        self.assertEqual(result.advisory_items, [])
        self.assertEqual(result.out_of_scope_items, [])


# -- Input immutability -------------------------------------------------------


class TestInputImmutability(unittest.TestCase):
    def test_does_not_mutate_ledger(self):
        ledger = [
            _ledger_item("HLD-010", "NOT_COVERED"),
            _ledger_item("HLD-020", "COVERED_IN_SDD"),
        ]
        original = copy.deepcopy(ledger)
        interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger,
            coverage_scope=_valid_active_spec_scope(
                selected_hld_anchor_ids=["HLD-010"],
            ),
        )
        self.assertEqual(ledger, original)

    def test_does_not_mutate_scope(self):
        scope = _valid_active_spec_scope(
            selected_hld_anchor_ids=["HLD-010"],
        )
        original = copy.deepcopy(scope)
        interpret_coverage_ledger_for_scope(
            coverage_ledger=[_ledger_item("HLD-010", "NOT_COVERED")],
            coverage_scope=scope,
        )
        self.assertEqual(scope, original)


# -- Purity / scope -----------------------------------------------------------


class TestPurity(unittest.TestCase):
    def test_no_forbidden_imports(self):
        import inspect
        import hldspec.hld_coverage_scope_interpretation as mod
        source = inspect.getsource(mod)
        for forbidden in (
            "subprocess", "pathlib", "socket", "urllib", "requests",
        ):
            self.assertNotIn(
                f"import {forbidden}", source,
                f"module must not import {forbidden}",
            )

    def test_no_source_package_import(self):
        import inspect
        import hldspec.hld_coverage_scope_interpretation as mod
        source = inspect.getsource(mod)
        self.assertNotIn("hld_source_package", source)

    def test_no_renderer_import(self):
        import inspect
        import hldspec.hld_coverage_scope_interpretation as mod
        source = inspect.getsource(mod)
        self.assertNotIn("render_active_spec", source)

    def test_no_selector_import(self):
        import inspect
        import hldspec.hld_coverage_scope_interpretation as mod
        source = inspect.getsource(mod)
        self.assertNotIn("select_active_spec", source)

    def test_no_gate_import(self):
        import inspect
        import hldspec.hld_coverage_scope_interpretation as mod
        source = inspect.getsource(mod)
        for forbidden in ("gate", "driver", "readiness"):
            self.assertNotIn(
                f"import {forbidden}", source,
                f"module must not import {forbidden}",
            )


if __name__ == "__main__":
    unittest.main()
