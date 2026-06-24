"""Tests for the Product QA ledger row classifier (Slice 2A).

Covers: every decision table rule, total classification coverage,
deterministic output, source hash, markdown grouping/sorting,
invalid ledger handling, no target modification, no .specify/ writes,
artifact contract registration, HARNESS_FIX_CANDIDATE reservation,
and no-execution boundary.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _row(**overrides):
    """Build a LedgerRow with sane defaults for classifier testing."""
    from hldspec.feature_ledger import LedgerRow

    defaults = dict(
        feature_id="FL-test-00000000",
        stable_key="area::component",
        area="area",
        screen_or_component="component",
        evidence_level="OBSERVED",
        evidence="some/file.tsx",
    )
    defaults.update(overrides)
    return LedgerRow(**defaults)


def _classify(row):
    from hldspec.ledger_classifier import classify_row
    return classify_row(row)


# ─── Decision table: one test per rule ─────────────────────────────────────────

class Rule01Tests(unittest.TestCase):
    def test_empty_evidence_blocked(self):
        self.assertEqual(_classify(_row(evidence="")).classification, "BLOCKED_NO_EVIDENCE")

    def test_blank_evidence_blocked(self):
        self.assertEqual(_classify(_row(evidence="   ")).classification, "BLOCKED_NO_EVIDENCE")


class Rule02Tests(unittest.TestCase):
    def test_status_test_status_contradiction_fail_pass(self):
        r = _row(status="fail", test_status="PASS")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")

    def test_status_test_status_contradiction_untested_pass(self):
        r = _row(status="untested", test_status="PASS")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")

    def test_status_test_status_contradiction_untested_fail(self):
        r = _row(status="untested", test_status="FAIL")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule03Tests(unittest.TestCase):
    def test_approval_needed_bool(self):
        r = _row(approval_needed=True)
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule04Tests(unittest.TestCase):
    def test_status_approval_needed(self):
        r = _row(status="approval_needed")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")

    def test_status_unclear(self):
        r = _row(status="unclear")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule05Tests(unittest.TestCase):
    def test_unclear_requirement(self):
        r = _row(defect_category="unclear_requirement")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule06Tests(unittest.TestCase):
    def test_fail_blank_expected_behavior(self):
        r = _row(status="fail", expected_observable_behavior="")
        self.assertEqual(_classify(r).classification, "NEEDS_EXPECTED_BEHAVIOR")

    def test_fail_whitespace_expected_behavior(self):
        r = _row(status="fail", expected_observable_behavior="   ")
        self.assertEqual(_classify(r).classification, "NEEDS_EXPECTED_BEHAVIOR")


class Rule07Tests(unittest.TestCase):
    def test_fail_inferred_evidence(self):
        r = _row(
            status="fail",
            evidence_level="INFERRED",
            expected_observable_behavior="should do X",
        )
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule08Tests(unittest.TestCase):
    def test_fail_not_examined_actual(self):
        r = _row(
            status="fail",
            expected_observable_behavior="should do X",
            actual_observed_behavior="NOT_EXAMINED",
        )
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule09Tests(unittest.TestCase):
    def test_fail_ux_defect(self):
        r = _row(
            status="fail",
            defect_category="ux_defect",
            expected_observable_behavior="button visible",
            actual_observed_behavior="button hidden",
        )
        self.assertEqual(_classify(r).classification, "UX_FIX_CANDIDATE")


class Rule10Tests(unittest.TestCase):
    def test_fail_functional_bug(self):
        r = _row(
            status="fail",
            defect_category="functional_bug",
            expected_observable_behavior="saves data",
            actual_observed_behavior="error thrown",
        )
        self.assertEqual(_classify(r).classification, "BUGFIX_CANDIDATE")

    def test_fail_data_integrity(self):
        r = _row(
            status="fail",
            defect_category="data_integrity",
            expected_observable_behavior="consistent",
            actual_observed_behavior="corrupted",
            evidence_level="REPRODUCED",
        )
        self.assertEqual(_classify(r).classification, "BUGFIX_CANDIDATE")

    def test_fail_security(self):
        r = _row(
            status="fail",
            defect_category="security",
            expected_observable_behavior="auth required",
            actual_observed_behavior="no auth check",
        )
        self.assertEqual(_classify(r).classification, "BUGFIX_CANDIDATE")

    def test_fail_performance(self):
        r = _row(
            status="fail",
            defect_category="performance",
            expected_observable_behavior="<200ms",
            actual_observed_behavior="5s response",
        )
        self.assertEqual(_classify(r).classification, "BUGFIX_CANDIDATE")

    def test_fail_integration(self):
        r = _row(
            status="fail",
            defect_category="integration",
            expected_observable_behavior="API returns 200",
            actual_observed_behavior="API returns 500",
            evidence_level="REPRODUCED",
        )
        self.assertEqual(_classify(r).classification, "BUGFIX_CANDIDATE")


class Rule11Tests(unittest.TestCase):
    def test_fail_missing_feature(self):
        r = _row(
            status="fail",
            defect_category="missing_feature",
            expected_observable_behavior="export button",
            actual_observed_behavior="no export found",
        )
        self.assertEqual(_classify(r).classification, "SPEC_GAP_CANDIDATE")


class Rule12Tests(unittest.TestCase):
    def test_fail_none_category(self):
        r = _row(
            status="fail",
            defect_category="none",
            expected_observable_behavior="works",
            actual_observed_behavior="broken",
        )
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule13Tests(unittest.TestCase):
    def test_blocked_status(self):
        r = _row(status="blocked")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")

    def test_blocked_status_is_not_harness_fix_candidate(self):
        r = _row(status="blocked")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")
        self.assertNotEqual(_classify(r).classification, "HARNESS_FIX_CANDIDATE")


class Rule14Tests(unittest.TestCase):
    def test_missing_feature_not_fail_observed(self):
        r = _row(
            status="untested",
            defect_category="missing_feature",
            evidence_level="OBSERVED",
        )
        self.assertEqual(_classify(r).classification, "SPEC_GAP_CANDIDATE")


class Rule15Tests(unittest.TestCase):
    def test_missing_feature_not_fail_inferred(self):
        r = _row(
            status="untested",
            defect_category="missing_feature",
            evidence_level="INFERRED",
            evidence="inferred from requirements",
        )
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class Rule16Tests(unittest.TestCase):
    def test_untested_no_signals(self):
        r = _row(status="untested")
        self.assertEqual(_classify(r).classification, "NO_ACTION")


class Rule17Tests(unittest.TestCase):
    def test_catchall_escalates(self):
        r = _row(status="untested", severity="major")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")

    def test_catchall_nondefault_fix_status(self):
        r = _row(status="untested", fix_status="in_progress")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")

    def test_catchall_nondefault_actual_observed(self):
        r = _row(status="untested", actual_observed_behavior="something happened")
        self.assertEqual(_classify(r).classification, "PRODUCT_DECISION_REQUIRED")


class HistoricalEvidenceTests(unittest.TestCase):
    def test_historical_evidence_reaches_candidate(self):
        r = _row(
            status="fail",
            defect_category="functional_bug",
            evidence_level="HISTORICAL",
            expected_observable_behavior="should work",
            actual_observed_behavior="does not work",
        )
        self.assertEqual(_classify(r).classification, "BUGFIX_CANDIDATE")


# ─── Negative / boundary tests ────────────────────────────────────────────────

class NegativeBoundaryTests(unittest.TestCase):

    def test_blank_expected_never_becomes_bugfix(self):
        for cat in ("functional_bug", "ux_defect", "data_integrity", "security", "performance", "integration"):
            r = _row(
                status="fail",
                defect_category=cat,
                expected_observable_behavior="",
                actual_observed_behavior="broken",
            )
            c = _classify(r).classification
            self.assertNotIn(c, ("BUGFIX_CANDIDATE", "UX_FIX_CANDIDATE"),
                             f"blank expected became {c} for {cat}")

    def test_inferred_never_becomes_candidate(self):
        for cat in ("functional_bug", "ux_defect", "data_integrity"):
            r = _row(
                status="fail",
                defect_category=cat,
                evidence_level="INFERRED",
                expected_observable_behavior="should work",
                actual_observed_behavior="broken",
            )
            c = _classify(r).classification
            self.assertNotIn(c, ("BUGFIX_CANDIDATE", "UX_FIX_CANDIDATE"),
                             f"INFERRED became {c} for {cat}")

    def test_code_only_never_confirms_failure(self):
        for cat in ("functional_bug", "ux_defect"):
            r = _row(
                status="fail",
                defect_category=cat,
                expected_observable_behavior="should work",
                actual_observed_behavior="NOT_EXAMINED",
            )
            c = _classify(r).classification
            self.assertNotIn(c, ("BUGFIX_CANDIDATE", "UX_FIX_CANDIDATE"),
                             f"NOT_EXAMINED became {c} for {cat}")

    def test_no_speckit_invocation(self):
        import hldspec.ledger_classifier as mod
        source = inspect.getsource(mod)
        for term in ("import speckit", "from speckit", "speckit_invoker", "SpecKitInvoker"):
            self.assertNotIn(term, source, f"classifier source contains '{term}'")
        self.assertFalse(
            any(name.startswith("speckit") for name in dir(mod)),
            "classifier module exposes speckit-related names",
        )

    def test_no_ledger_modification(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import classify_ledger

        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="file.tsx"))
        original_json = ledger.to_json()
        classify_ledger(ledger)
        self.assertEqual(ledger.to_json(), original_json)

    def test_no_specify_writes(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import build_result, write_classification

        with tempfile.TemporaryDirectory() as tmp:
            ledger = FeatureLedger()
            ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
            result = build_result(ledger, "fakehash")
            control = Path(tmp) / "control"
            write_classification(result, control)
            self.assertFalse((Path(tmp) / ".specify").exists())

    def test_classification_not_work_order(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import build_result, result_to_dict

        ledger = FeatureLedger()
        ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
        result = build_result(ledger, "fakehash")
        d = result_to_dict(result)
        text = json.dumps(d)
        for term in ("work_order", "task_id", "implementation", "speckit"):
            self.assertNotIn(term, text.lower())

    def test_stable_feature_id_preserved(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import classify_ledger

        ledger = FeatureLedger()
        r1 = make_row("auth", "login", evidence_level="OBSERVED", evidence="x")
        r2 = make_row("dash", "main", evidence_level="OBSERVED", evidence="y")
        ledger.add_row(r1)
        ledger.add_row(r2)
        classified = classify_ledger(ledger)
        self.assertEqual(classified[0].feature_id, r1.feature_id)
        self.assertEqual(classified[1].feature_id, r2.feature_id)


# ─── HARNESS_FIX_CANDIDATE reservation tests ──────────────────────────────────

class HarnessFixReservationTests(unittest.TestCase):

    def test_harness_fix_is_valid_value(self):
        from hldspec.ledger_classifier import VALID_CLASSIFICATIONS
        self.assertIn("HARNESS_FIX_CANDIDATE", VALID_CLASSIFICATIONS)

    def test_harness_fix_never_assigned(self):
        from hldspec.feature_ledger import VALID_STATUSES, VALID_DEFECT_CATEGORIES
        from hldspec.ledger_classifier import VALID_CLASSIFICATIONS

        rows = []
        for status in VALID_STATUSES:
            for cat in VALID_DEFECT_CATEGORIES:
                rows.append(_row(
                    status=status,
                    defect_category=cat,
                    expected_observable_behavior="expected",
                    actual_observed_behavior="actual",
                    evidence_level="OBSERVED",
                    evidence="file.tsx",
                ))
        for r in rows:
            c = _classify(r)
            self.assertNotEqual(c.classification, "HARNESS_FIX_CANDIDATE",
                                f"HARNESS_FIX_CANDIDATE assigned for status={r.status}, "
                                f"defect_category={r.defect_category}")
            self.assertIn(c.classification, VALID_CLASSIFICATIONS,
                          f"invalid classification '{c.classification}' for status={r.status}, "
                          f"defect_category={r.defect_category}")


# ─── Output format tests ──────────────────────────────────────────────────────

class OutputFormatTests(unittest.TestCase):

    def _make_ledger(self):
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="x"))
        ledger.add_row(make_row("dash", "overview",
                                status="fail",
                                defect_category="functional_bug",
                                expected_observable_behavior="works",
                                actual_observed_behavior="broken",
                                evidence_level="REPRODUCED",
                                evidence="test log"))
        ledger.add_row(make_row("settings", "profile",
                                status="fail",
                                expected_observable_behavior="",
                                evidence="code scan"))
        return ledger

    def test_deterministic_output(self):
        from hldspec.ledger_classifier import build_result, result_to_dict

        ledger = self._make_ledger()
        r1 = build_result(ledger, "hash1")
        r2 = build_result(ledger, "hash1")
        self.assertEqual(r1.classifications, r2.classifications)
        d1 = result_to_dict(r1)
        d2 = result_to_dict(r2)
        d1.pop("classified_at")
        d2.pop("classified_at")
        self.assertEqual(d1, d2)

    def test_json_roundtrip(self):
        from hldspec.ledger_classifier import build_result, result_to_json

        ledger = self._make_ledger()
        result = build_result(ledger, "hash1")
        j = result_to_json(result)
        parsed = json.loads(j)
        self.assertEqual(parsed["schema_version"], 1)
        self.assertEqual(len(parsed["classifications"]), 3)

    def test_summary_counts_match(self):
        from hldspec.ledger_classifier import build_result

        ledger = self._make_ledger()
        result = build_result(ledger, "hash1")
        actual_counts = {}
        for c in result.classifications:
            actual_counts[c["classification"]] = actual_counts.get(c["classification"], 0) + 1
        self.assertEqual(result.summary, actual_counts)

    def test_total_rows_matches(self):
        from hldspec.ledger_classifier import build_result

        ledger = self._make_ledger()
        result = build_result(ledger, "hash1")
        self.assertEqual(result.total_rows, len(ledger.rows))
        self.assertEqual(result.total_rows, len(result.classifications))

    def test_source_hash_matches(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import load_and_classify

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            control = Path(tmp) / "control"
            ledger = FeatureLedger()
            ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
            ledger.write(qa)

            result, _ = load_and_classify(qa, control)
            expected_hash = hashlib.sha256(
                (qa / "feature-ledger.json").read_bytes()
            ).hexdigest()
            self.assertEqual(result.source_ledger_sha256, expected_hash)

    def test_md_output_generated(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import build_result, write_classification

        with tempfile.TemporaryDirectory() as tmp:
            ledger = FeatureLedger()
            ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
            result = build_result(ledger, "hash")
            paths = write_classification(result, Path(tmp))
            self.assertTrue(paths.md_path.exists())
            self.assertTrue(paths.json_path.exists())

    def test_output_under_control_plane(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import build_result, write_classification

        with tempfile.TemporaryDirectory() as tmp:
            ledger = FeatureLedger()
            ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
            result = build_result(ledger, "hash")
            control = Path(tmp) / "control_sync"
            paths = write_classification(result, control)
            self.assertIn("product_qa_loop", str(paths.json_path))
            self.assertIn("product_qa_loop", str(paths.md_path))

    def test_plain_overwrite(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import build_result, write_classification, result_to_json

        with tempfile.TemporaryDirectory() as tmp:
            control = Path(tmp) / "control"
            ledger = FeatureLedger()
            ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
            r1 = build_result(ledger, "hash1")
            write_classification(r1, control)

            ledger.add_row(make_row("c", "d", evidence_level="OBSERVED", evidence="y"))
            r2 = build_result(ledger, "hash2")
            paths = write_classification(r2, control)

            data = json.loads(paths.json_path.read_text())
            self.assertEqual(data["total_rows"], 2)
            self.assertEqual(data["source_ledger_sha256"], "hash2")


class MarkdownGroupingTests(unittest.TestCase):

    def test_md_grouped_by_classification(self):
        from hldspec.ledger_classifier import result_to_md, ClassificationResult

        result = ClassificationResult(
            schema_version=1,
            source_ledger_sha256="abc",
            classified_at="2026-01-01T00:00:00Z",
            total_rows=3,
            summary={"NO_ACTION": 2, "BUGFIX_CANDIDATE": 1},
            classifications=[
                {"feature_id": "FL-z", "classification": "NO_ACTION", "reason": "inert"},
                {"feature_id": "FL-a", "classification": "BUGFIX_CANDIDATE", "reason": "bug"},
                {"feature_id": "FL-m", "classification": "NO_ACTION", "reason": "inert"},
            ],
        )
        md = result_to_md(result)
        bug_pos = md.index("## BUGFIX_CANDIDATE")
        no_action_pos = md.index("## NO_ACTION")
        self.assertLess(bug_pos, no_action_pos)

    def test_md_sorted_by_feature_id_within_group(self):
        from hldspec.ledger_classifier import result_to_md, ClassificationResult

        result = ClassificationResult(
            schema_version=1,
            source_ledger_sha256="abc",
            classified_at="2026-01-01T00:00:00Z",
            total_rows=2,
            summary={"NO_ACTION": 2},
            classifications=[
                {"feature_id": "FL-z", "classification": "NO_ACTION", "reason": "inert"},
                {"feature_id": "FL-a", "classification": "NO_ACTION", "reason": "inert"},
            ],
        )
        md = result_to_md(result)
        a_pos = md.index("FL-a")
        z_pos = md.index("FL-z")
        self.assertLess(a_pos, z_pos)


# ─── Input validation tests ───────────────────────────────────────────────────

class InputValidationTests(unittest.TestCase):

    def test_empty_ledger_produces_empty_classification(self):
        from hldspec.feature_ledger import FeatureLedger
        from hldspec.ledger_classifier import build_result

        result = build_result(FeatureLedger(), "empty_hash")
        self.assertEqual(result.total_rows, 0)
        self.assertEqual(result.classifications, [])
        self.assertEqual(result.summary, {})

    def test_invalid_ledger_errors_cleanly(self):
        from hldspec.ledger_classifier import load_and_classify

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            qa.mkdir()
            (qa / "feature-ledger.json").write_text("not json", encoding="utf-8")
            with self.assertRaises(Exception):
                load_and_classify(qa, Path(tmp) / "ctrl")

    def test_missing_ledger_errors_cleanly(self):
        from hldspec.ledger_classifier import load_and_classify

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            with self.assertRaises(FileNotFoundError):
                load_and_classify(qa, Path(tmp) / "ctrl")

    def test_schema_invalid_rows_error(self):
        from hldspec.ledger_classifier import load_and_classify

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            qa.mkdir()
            (qa / "feature-ledger.json").write_text(json.dumps({
                "schema_version": 1,
                "rows": [{
                    "feature_id": "FL-x",
                    "stable_key": "a::b",
                    "area": "a",
                    "screen_or_component": "b",
                    "evidence_level": "BOGUS",
                    "evidence": "something",
                }],
            }), encoding="utf-8")
            control = Path(tmp) / "ctrl"
            with self.assertRaises(ValueError):
                load_and_classify(qa, control)
            self.assertFalse(control.exists(), "invalid ledger must not create output")

    def test_malformed_ledger_errors_without_output(self):
        from hldspec.ledger_classifier import load_and_classify

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            qa.mkdir()
            (qa / "feature-ledger.json").write_text("not json", encoding="utf-8")
            control = Path(tmp) / "ctrl"
            with self.assertRaises(json.JSONDecodeError):
                load_and_classify(qa, control)
            self.assertFalse(control.exists(), "malformed ledger must not create output")


# ─── Determinism invariants ───────────────────────────────────────────────────

class DeterminismInvariantTests(unittest.TestCase):

    def test_reason_strings_are_static(self):
        from hldspec.ledger_classifier import classify_ledger
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.add_row(make_row("a", "b", evidence_level="OBSERVED", evidence="x"))
        ledger.add_row(make_row("c", "d",
                                status="fail",
                                defect_category="functional_bug",
                                expected_observable_behavior="works",
                                actual_observed_behavior="broken",
                                evidence_level="OBSERVED",
                                evidence="y"))

        c1 = classify_ledger(ledger)
        c2 = classify_ledger(ledger)
        for a, b in zip(c1, c2):
            self.assertEqual(a.reason, b.reason)
            self.assertFalse(any(char.isdigit() and len(char) > 8 for char in a.reason.split()),
                             f"reason may contain volatile content: {a.reason}")

    def test_no_action_only_from_inert_rows(self):
        from hldspec.feature_ledger import VALID_STATUSES, VALID_DEFECT_CATEGORIES, VALID_SEVERITIES

        non_default_severities = VALID_SEVERITIES - {"none"}
        non_default_categories = VALID_DEFECT_CATEGORIES - {"none"}

        for sev in non_default_severities:
            r = _row(status="untested", severity=sev)
            c = _classify(r)
            self.assertNotEqual(c.classification, "NO_ACTION",
                                f"NO_ACTION assigned with severity={sev}")

        for cat in non_default_categories:
            r = _row(status="untested", defect_category=cat)
            c = _classify(r)
            if cat == "unclear_requirement":
                self.assertEqual(c.classification, "PRODUCT_DECISION_REQUIRED")
            elif cat == "missing_feature":
                self.assertIn(c.classification, ("SPEC_GAP_CANDIDATE", "PRODUCT_DECISION_REQUIRED"))
            else:
                self.assertNotEqual(c.classification, "NO_ACTION",
                                    f"NO_ACTION assigned with defect_category={cat}")

    def test_all_valid_rows_receive_one_known_classification(self):
        from hldspec.feature_ledger import (
            VALID_DEFECT_CATEGORIES,
            VALID_EVIDENCE_LEVELS,
            VALID_STATUSES,
        )
        from hldspec.ledger_classifier import VALID_CLASSIFICATIONS

        for status in VALID_STATUSES:
            for category in VALID_DEFECT_CATEGORIES:
                for evidence_level in VALID_EVIDENCE_LEVELS:
                    row = _row(
                        status=status,
                        defect_category=category,
                        evidence_level=evidence_level,
                        expected_observable_behavior="expected",
                        actual_observed_behavior="observed",
                    )
                    classification = _classify(row).classification
                    self.assertIn(classification, VALID_CLASSIFICATIONS)


# ─── Artifact contract tests ──────────────────────────────────────────────────

class ArtifactContractTests(unittest.TestCase):

    def test_classification_registered_in_contracts(self):
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS
        self.assertIn("product-ledger-classification", ARTIFACT_CONTRACTS)

    def test_contract_producer(self):
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS
        contract = ARTIFACT_CONTRACTS["product-ledger-classification"]
        self.assertIn("Slice 2A", contract.producer)

    def test_contract_output_not_under_specify(self):
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS
        contract = ARTIFACT_CONTRACTS["product-ledger-classification"]
        for f in contract.output_artifacts:
            self.assertNotIn(".specify", f)

    def test_contract_notes_not_work_order(self):
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS
        contract = ARTIFACT_CONTRACTS["product-ledger-classification"]
        self.assertIn("NOT a work order", contract.notes)

    def test_feature_ledger_has_classifier_consumer(self):
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS
        contract = ARTIFACT_CONTRACTS["feature-ledger"]
        self.assertIn("ledger_classifier", contract.consumers)


# ─── CLI tests ─────────────────────────────────────────────────────────────────

class CliTests(unittest.TestCase):

    def _fake_target_with_ledger(self, tmp: str) -> Path:
        from hldspec.feature_ledger import FeatureLedger, make_row

        target = Path(tmp) / "app"
        target.mkdir(parents=True)
        qa = target / "qa"
        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="file.tsx"))
        ledger.write(qa)
        return target

    def test_cli_writes_classification(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target_with_ledger(tmp)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "classify_ledger.py"), "--target", str(target)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            ctrl_dir = target / ".hldspec" / "sync" / "product_qa_loop"
            self.assertTrue((ctrl_dir / "product-ledger-classification.json").is_file(), proc.stdout)
            self.assertTrue((ctrl_dir / "product-ledger-classification.md").is_file(), proc.stdout)

    def test_cli_missing_target_exits_nonzero(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "classify_ledger.py"),
             "--target", "/nonexistent/path"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(proc.returncode, 0)

    def test_cli_missing_ledger_exits_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "app"
            target.mkdir()
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "classify_ledger.py"),
                 "--target", str(target)],
                capture_output=True, text=True,
            )
            self.assertNotEqual(proc.returncode, 0)
            self.assertFalse(
                (target / ".hldspec").exists(),
                "missing ledger must not create control-plane output",
            )

    def test_disk_run_preserves_target_owned_files(self):
        from hldspec.feature_ledger import FeatureLedger, make_row
        from hldspec.ledger_classifier import load_and_classify

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "app"
            qa = target / "qa"
            product_file = target / "src" / "app.py"
            specify_file = target / ".specify" / "memory" / "constitution.md"
            product_file.parent.mkdir(parents=True)
            specify_file.parent.mkdir(parents=True)
            product_file.write_bytes(b"print('product')\n")
            specify_file.write_bytes(b"# product-owned SpecKit memory\n")

            ledger = FeatureLedger()
            ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="file.tsx"))
            ledger.write(qa)
            ledger_bytes = (qa / "feature-ledger.json").read_bytes()
            product_bytes = product_file.read_bytes()
            specify_bytes = specify_file.read_bytes()

            control = Path(tmp) / "controller" / ".hldspec" / "sync"
            _, paths = load_and_classify(qa, control)

            self.assertEqual((qa / "feature-ledger.json").read_bytes(), ledger_bytes)
            self.assertEqual(product_file.read_bytes(), product_bytes)
            self.assertEqual(specify_file.read_bytes(), specify_bytes)
            self.assertTrue(paths.json_path.is_file())
            self.assertTrue(paths.md_path.is_file())


if __name__ == "__main__":
    unittest.main()
