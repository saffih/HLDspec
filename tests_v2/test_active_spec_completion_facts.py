"""Focused tests for ActiveSpecCompletionFacts — pure advisory layer."""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hldspec.active_spec_completion_facts import (
    COMPLETION_COMPLETE_ADVISORY,
    COMPLETION_INCOMPLETE_ADVISORY,
    COMPLETION_NOT_APPLICABLE,
    COMPLETION_UNKNOWN_ADVISORY,
    ActiveSpecCompletionFacts,
    build_active_spec_completion_facts,
)
from hldspec.source_package_gate_facts import SourcePackageGateFacts

_PATCH_TARGET = "hldspec.active_spec_completion_facts.build_source_package_gate_facts"


def _base_facts(**overrides) -> SourcePackageGateFacts:
    defaults = dict(
        validation_ok=True,
        validation_missing=(),
        validation_hash_mismatches=(),
        semantic_errors=(),
        coverage_scope="ACTIVE_SPEC",
        active_spec_id="SPEC-001",
        interpretation_ok=True,
        interpretation_errors=(),
        blocking_items=(),
        advisory_items=(),
        out_of_scope_items=(),
        selected_anchor_blocker_count=0,
        out_of_scope_advisory_count=0,
        receipt_present=True,
        receipt_type="ACTIVE_SPEC_SOURCE_PACKAGE_RENDER",
        target_materialization="NOT_MATERIALIZED",
        read_errors=(),
    )
    defaults.update(overrides)
    return SourcePackageGateFacts(**defaults)


class FullHldNotApplicableTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts(
        coverage_scope="FULL_HLD", active_spec_id=None,
    ))
    def test_full_hld_returns_not_applicable(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertFalse(result.completion_applicable)
        self.assertEqual(result.completion_status, COMPLETION_NOT_APPLICABLE)
        self.assertIn("coverage_scope_not_active_spec", result.reasons)


class ActiveSpecCompleteTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts())
    def test_complete_advisory(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertTrue(result.completion_applicable)
        self.assertEqual(result.completion_status, COMPLETION_COMPLETE_ADVISORY)
        self.assertEqual(result.reasons, ())
        self.assertEqual(result.selected_anchor_blocker_count, 0)
        self.assertTrue(result.receipt_present)
        self.assertEqual(result.semantic_error_count, 0)
        self.assertEqual(result.read_error_count, 0)


class SelectedBlockerIncompleteTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts(
        blocking_items=({"hld_item_id": "HLD-001", "status": "NOT_COVERED"},),
        selected_anchor_blocker_count=1,
    ))
    def test_selected_blockers_incomplete(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertEqual(result.completion_status, COMPLETION_INCOMPLETE_ADVISORY)
        self.assertIn("selected_anchor_blockers_present", result.reasons)


class MissingReceiptTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts(
        receipt_present=False, receipt_type=None,
    ))
    def test_missing_receipt_incomplete(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertEqual(result.completion_status, COMPLETION_INCOMPLETE_ADVISORY)
        self.assertIn("missing_active_spec_receipt", result.reasons)


class UnexpectedReceiptTypeTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts(
        receipt_type="SOMETHING_ELSE",
    ))
    def test_unexpected_receipt_type_incomplete(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertEqual(result.completion_status, COMPLETION_INCOMPLETE_ADVISORY)
        self.assertIn("unexpected_receipt_type", result.reasons)


class SemanticErrorsTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts(
        semantic_errors=("bad_anchor_ref",),
    ))
    def test_semantic_errors_incomplete(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertEqual(result.completion_status, COMPLETION_INCOMPLETE_ADVISORY)
        self.assertIn("semantic_errors_present", result.reasons)
        self.assertEqual(result.semantic_error_count, 1)


class ReadErrorsTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts(
        read_errors=("scope.json is malformed: ...",),
    ))
    def test_read_errors_incomplete(self, _mock):
        result = build_active_spec_completion_facts(Path("/unused"))
        self.assertEqual(result.completion_status, COMPLETION_INCOMPLETE_ADVISORY)
        self.assertIn("read_errors_present", result.reasons)
        self.assertEqual(result.read_error_count, 1)


class MissingSourcePackageTests(unittest.TestCase):
    def test_missing_source_package_does_not_crash(self):
        result = build_active_spec_completion_facts(Path("/nonexistent/path"))
        self.assertIsInstance(result, ActiveSpecCompletionFacts)
        self.assertIn(result.completion_status, (
            COMPLETION_UNKNOWN_ADVISORY,
            COMPLETION_NOT_APPLICABLE,
            COMPLETION_INCOMPLETE_ADVISORY,
        ))


class NoWriteTests(unittest.TestCase):
    @patch(_PATCH_TARGET, return_value=_base_facts())
    def test_builder_does_not_write_files(self, _mock):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            before = set(tmp_path.rglob("*"))
            build_active_spec_completion_facts(tmp_path)
            after = set(tmp_path.rglob("*"))
            self.assertEqual(before, after)


class NoForbiddenImportsTests(unittest.TestCase):
    def test_no_gate_driver_readiness_imports(self):
        import hldspec.active_spec_completion_facts as mod
        source = inspect.getsource(mod)
        for forbidden in (
            "journey3_driver",
            "speckit_readiness",
            "approval_gate",
            "spec_build_plan",
            "speckit_prework",
        ):
            self.assertNotIn(
                forbidden, source,
                f"Module must not import {forbidden}",
            )


class NoMutationTests(unittest.TestCase):
    def test_result_is_frozen(self):
        result = ActiveSpecCompletionFacts(
            completion_applicable=True,
            completion_status=COMPLETION_COMPLETE_ADVISORY,
            coverage_scope="ACTIVE_SPEC",
            active_spec_id="SPEC-001",
            selected_anchor_blocker_count=0,
            out_of_scope_advisory_count=0,
            receipt_present=True,
            receipt_type="ACTIVE_SPEC_SOURCE_PACKAGE_RENDER",
            semantic_error_count=0,
            read_error_count=0,
            reasons=(),
        )
        with self.assertRaises(AttributeError):
            result.completion_status = "HACKED"


if __name__ == "__main__":
    unittest.main()
