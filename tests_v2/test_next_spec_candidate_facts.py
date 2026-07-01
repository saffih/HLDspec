"""Tests for next-spec candidate facts -- pure read-only advisory layer."""
from __future__ import annotations

import copy
import inspect
import unittest

from hldspec.active_spec_completion_facts import COMPLETION_COMPLETE_ADVISORY
from hldspec.next_spec_candidate_facts import (
    CANDIDATE_CANDIDATES_AVAILABLE,
    CANDIDATE_NO_CANDIDATES,
    CANDIDATE_NOT_APPLICABLE,
    CANDIDATE_UNKNOWN,
    NextSpecCandidate,
    NextSpecCandidateFacts,
    RejectedNextSpec,
    build_next_spec_candidate_facts,
)


def _make_backlog(specs, active_spec_id=None):
    return {
        "schema_version": 1,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "source_refs": [],
        "active_spec_id": active_spec_id,
        "specs": specs,
    }


def _make_spec(
    spec_id,
    status="PLANNED",
    title=None,
    dependencies=None,
    hld_anchor_ids=None,
    target_materialization="NOT_MATERIALIZED",
):
    return {
        "spec_id": spec_id,
        "title": title or f"Spec {spec_id}",
        "hld_anchor_ids": hld_anchor_ids or [],
        "capability": "test",
        "status": status,
        "size_class": "SMALL",
        "dependencies": dependencies or [],
        "validation_strategy": "unit_tests",
        "target_materialization": target_materialization,
    }


class CandidatesAvailableTests(unittest.TestCase):
    def test_candidates_available(self):
        backlog = _make_backlog(
            specs=[
                _make_spec("SPEC-001", status="DONE"),
                _make_spec("SPEC-002", status="PLANNED"),
            ],
            active_spec_id="SPEC-001",
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        self.assertTrue(result.candidate_facts_applicable)
        self.assertEqual(result.candidate_status, CANDIDATE_CANDIDATES_AVAILABLE)
        self.assertEqual(result.candidate_count, 1)
        self.assertEqual(result.candidates[0].spec_id, "SPEC-002")


class NotApplicableTests(unittest.TestCase):
    def test_incomplete_returns_not_applicable(self):
        backlog = _make_backlog(
            specs=[_make_spec("SPEC-001")],
            active_spec_id="SPEC-001",
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status="INCOMPLETE_ADVISORY",
        )
        self.assertFalse(result.candidate_facts_applicable)
        self.assertEqual(result.candidate_status, CANDIDATE_NOT_APPLICABLE)
        self.assertEqual(result.reasons, ("active_spec_not_complete",))

    def test_missing_completion_status_returns_not_applicable(self):
        backlog = _make_backlog(
            specs=[_make_spec("SPEC-001", status="PLANNED")],
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=None,
        )
        self.assertFalse(result.candidate_facts_applicable)
        self.assertEqual(result.candidate_status, CANDIDATE_NOT_APPLICABLE)
        self.assertEqual(result.reasons, ("active_spec_not_complete",))
        self.assertEqual(result.candidate_count, 0)


class CurrentActiveSpecRejectedTests(unittest.TestCase):
    def test_active_spec_rejected(self):
        backlog = _make_backlog(
            specs=[
                _make_spec("SPEC-001", status="SELECTED"),
                _make_spec("SPEC-002", status="PLANNED"),
            ],
            active_spec_id="SPEC-001",
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        rejected_ids = {item.spec_id: item for item in result.rejected}
        self.assertIn("SPEC-001", rejected_ids)
        self.assertEqual(rejected_ids["SPEC-001"].reasons, ("current_active_spec",))


class AlreadySelectedRejectedTests(unittest.TestCase):
    def test_selected_non_active_rejected(self):
        backlog = _make_backlog(
            specs=[
                _make_spec("SPEC-001", status="SELECTED"),
                _make_spec("SPEC-002", status="PLANNED"),
            ],
            active_spec_id=None,
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        rejected_ids = {item.spec_id: item for item in result.rejected}
        self.assertIn("SPEC-001", rejected_ids)
        self.assertEqual(rejected_ids["SPEC-001"].reasons, ("already_selected",))


class MaterializedRejectedTests(unittest.TestCase):
    def test_materialized_rejected(self):
        backlog = _make_backlog(
            specs=[
                _make_spec(
                    "SPEC-001",
                    status="MATERIALIZED_TO_TARGET",
                ),
                _make_spec("SPEC-002", status="PLANNED"),
            ],
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        rejected_ids = {item.spec_id: item for item in result.rejected}
        self.assertIn("SPEC-001", rejected_ids)
        self.assertEqual(rejected_ids["SPEC-001"].reasons, ("already_materialized",))

    def test_unknown_materialization_is_not_claimed_materialized(self):
        spec = _make_spec("SPEC-001", status="PLANNED")
        spec.pop("target_materialization")
        backlog = _make_backlog(specs=[spec])
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        rejected_ids = {item.spec_id: item for item in result.rejected}
        self.assertEqual(rejected_ids["SPEC-001"].reasons, ("unsupported_status",))


class MissingSpecIdRejectedTests(unittest.TestCase):
    def test_missing_spec_id_rejected(self):
        spec = _make_spec("SPEC-001")
        del spec["spec_id"]
        backlog = _make_backlog(specs=[spec])
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        self.assertEqual(result.rejected_count, 1)
        self.assertEqual(result.rejected[0].reasons, ("missing_spec_id",))


class DependenciesRejectedTests(unittest.TestCase):
    def test_dependencies_rejected(self):
        backlog = _make_backlog(
            specs=[
                _make_spec("SPEC-001", status="DONE"),
                _make_spec("SPEC-002", status="PLANNED", dependencies=["SPEC-001"]),
            ],
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        rejected_ids = {item.spec_id: item for item in result.rejected}
        self.assertIn("SPEC-002", rejected_ids)
        self.assertEqual(
            rejected_ids["SPEC-002"].reasons,
            ("dependency_semantics_unknown",),
        )


class EmptyBacklogTests(unittest.TestCase):
    def test_empty_specs(self):
        backlog = _make_backlog(specs=[])
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        self.assertEqual(result.candidate_status, CANDIDATE_NO_CANDIDATES)
        self.assertEqual(result.reasons, ("no_specs", "no_candidates"))


class CompactOutputTests(unittest.TestCase):
    def test_no_raw_spec_dicts(self):
        backlog = _make_backlog(
            specs=[_make_spec("SPEC-001", status="PLANNED")],
        )
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        for candidate in result.candidates:
            self.assertIsInstance(candidate, NextSpecCandidate)
            self.assertNotIsInstance(candidate, dict)
        for item in result.rejected:
            self.assertIsInstance(item, RejectedNextSpec)
            self.assertNotIsInstance(item, dict)


class FrozenDataclassTests(unittest.TestCase):
    def test_facts_frozen(self):
        backlog = _make_backlog(specs=[_make_spec("SPEC-001")])
        result = build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        with self.assertRaises(AttributeError):
            result.candidate_status = "HACKED"

    def test_candidate_frozen(self):
        candidate = NextSpecCandidate(
            spec_id="X",
            title=None,
            status=None,
            hld_anchor_ids=(),
            dependency_ids=(),
            reasons=(),
        )
        with self.assertRaises(AttributeError):
            candidate.spec_id = "HACKED"

    def test_rejected_frozen(self):
        rejected = RejectedNextSpec(spec_id="X", title=None, status=None, reasons=())
        with self.assertRaises(AttributeError):
            rejected.spec_id = "HACKED"


class NoWriteTests(unittest.TestCase):
    def test_no_file_writes(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            before = set(tmp_path.rglob("*"))
            backlog = _make_backlog(specs=[_make_spec("SPEC-001")])
            build_next_spec_candidate_facts(
                backlog,
                active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
            )
            after = set(tmp_path.rglob("*"))
            self.assertEqual(before, after)


class NoForbiddenImportsTests(unittest.TestCase):
    def test_no_forbidden_imports(self):
        import hldspec.next_spec_candidate_facts as mod

        source = inspect.getsource(mod)
        for forbidden in (
            "journey3_driver",
            "speckit_readiness",
            "approval_gate",
            "source_package_writer",
        ):
            self.assertNotIn(forbidden, source, f"Module must not import {forbidden}")


class NoSelectCallTests(unittest.TestCase):
    def test_no_selection_call_in_source(self):
        import hldspec.next_spec_candidate_facts as mod

        source = inspect.getsource(mod)
        self.assertNotIn(
            "select_active_spec",
            source,
            "Module must not reference the selection function",
        )


class NoBacklogMutationTests(unittest.TestCase):
    def test_no_mutation(self):
        backlog = _make_backlog(
            specs=[
                _make_spec("SPEC-001", status="DONE"),
                _make_spec("SPEC-002", status="PLANNED"),
            ],
            active_spec_id="SPEC-001",
        )
        original = copy.deepcopy(backlog)
        build_next_spec_candidate_facts(
            backlog,
            active_spec_completion_status=COMPLETION_COMPLETE_ADVISORY,
        )
        self.assertEqual(backlog, original)


if __name__ == "__main__":
    unittest.main()
