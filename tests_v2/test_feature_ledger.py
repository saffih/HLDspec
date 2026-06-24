"""Tests for the Product QA feature ledger (Slice 1).

Covers: schema fields, allowed statuses, stable feature IDs, deterministic
CSV/JSON output, idempotent regeneration, evidence-required behavior, default
values, no .specify/ writes, resolved target QA path, artifact contract
registration, and audit vocabulary reuse.
"""
from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class FeatureLedgerSchemaTests(unittest.TestCase):
    """Schema field and validation tests — written before implementation."""

    def test_ledger_row_has_all_required_fields(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-test-abc12345",
            stable_key="area::component",
            area="area",
            screen_or_component="component",
        )
        required = [
            "feature_id", "stable_key", "area", "screen_or_component",
            "user_story", "preconditions", "inputs", "outputs",
            "expected_observable_behavior", "actual_observed_behavior",
            "actual_behavior_from_code", "test_steps",
            "status", "test_status", "retest_status",
            "defect_category", "severity", "evidence_level", "evidence",
            "fix_status", "approval_needed", "notes",
        ]
        d = row.to_dict()
        for field_name in required:
            self.assertIn(field_name, d, f"missing field: {field_name}")

    def test_default_status_is_untested(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
        )
        self.assertEqual(row.status, "untested")

    def test_default_test_status_is_not_tested(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
        )
        self.assertIn(row.test_status, ("NOT_TESTED", "NOT_EXAMINED"))

    def test_default_retest_status_is_not_tested(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
        )
        self.assertIn(row.retest_status, ("NOT_TESTED", "NOT_APPLICABLE"))

    def test_default_actual_observed_behavior_is_not_examined(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
        )
        self.assertEqual(row.actual_observed_behavior, "NOT_EXAMINED")

    def test_default_evidence_level_is_inferred(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
        )
        self.assertEqual(row.evidence_level, "INFERRED")


class FeatureLedgerStatusValidationTests(unittest.TestCase):

    def test_allowed_statuses(self) -> None:
        from hldspec.feature_ledger import VALID_STATUSES

        expected = {"untested", "fail", "blocked", "unclear", "approval_needed"}
        self.assertEqual(VALID_STATUSES, expected)

    def test_pass_not_in_allowed_statuses(self) -> None:
        from hldspec.feature_ledger import VALID_STATUSES

        self.assertNotIn("pass", VALID_STATUSES)

    def test_allowed_test_statuses(self) -> None:
        from hldspec.feature_ledger import VALID_TEST_STATUSES

        expected = {"NOT_TESTED", "PASS", "FAIL", "BLOCKED", "NOT_EXAMINED"}
        self.assertEqual(VALID_TEST_STATUSES, expected)

    def test_allowed_retest_statuses(self) -> None:
        from hldspec.feature_ledger import VALID_RETEST_STATUSES

        expected = {"NOT_TESTED", "NOT_APPLICABLE", "RETEST_REQUIRED", "PASS", "FAIL", "BLOCKED"}
        self.assertEqual(VALID_RETEST_STATUSES, expected)

    def test_allowed_evidence_levels(self) -> None:
        from hldspec.feature_ledger import VALID_EVIDENCE_LEVELS

        expected = {"OBSERVED", "REPRODUCED", "HISTORICAL", "INFERRED"}
        self.assertEqual(VALID_EVIDENCE_LEVELS, expected)

    def test_evidence_levels_match_audit_vocabulary(self) -> None:
        from hldspec.feature_ledger import VALID_EVIDENCE_LEVELS

        audit_terms = {"OBSERVED", "REPRODUCED", "HISTORICAL", "INFERRED"}
        self.assertEqual(VALID_EVIDENCE_LEVELS, audit_terms)

    def test_invalid_status_fails_validation(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
            status="pass",
        )
        errors = row.validate()
        self.assertTrue(any("status" in e for e in errors))

    def test_invalid_evidence_level_fails_validation(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
            evidence_level="VERIFIED",
        )
        errors = row.validate()
        self.assertTrue(any("evidence_level" in e for e in errors))

    def test_valid_row_passes_validation(self) -> None:
        from hldspec.feature_ledger import make_row

        row = make_row("auth", "login-form", evidence_level="OBSERVED", evidence="seen in auth/views.py:30")
        self.assertEqual(row.validate(), [])


class StableFeatureIdTests(unittest.TestCase):

    def test_id_is_deterministic(self) -> None:
        from hldspec.feature_ledger import make_row

        r1 = make_row("auth", "login-form")
        r2 = make_row("auth", "login-form")
        self.assertEqual(r1.feature_id, r2.feature_id)
        self.assertEqual(r1.stable_key, r2.stable_key)

    def test_id_starts_with_fl_prefix(self) -> None:
        from hldspec.feature_ledger import make_row

        row = make_row("auth", "login-form")
        self.assertTrue(row.feature_id.startswith("FL-"))

    def test_id_contains_hash_suffix(self) -> None:
        from hldspec.feature_ledger import make_row

        row = make_row("auth", "login-form")
        parts = row.feature_id.rsplit("-", 1)
        self.assertEqual(len(parts), 2)
        self.assertEqual(len(parts[1]), 8)

    def test_different_areas_produce_different_ids(self) -> None:
        from hldspec.feature_ledger import make_row

        r1 = make_row("auth", "login-form")
        r2 = make_row("dashboard", "login-form")
        self.assertNotEqual(r1.feature_id, r2.feature_id)

    def test_different_components_produce_different_ids(self) -> None:
        from hldspec.feature_ledger import make_row

        r1 = make_row("auth", "login-form")
        r2 = make_row("auth", "signup-form")
        self.assertNotEqual(r1.feature_id, r2.feature_id)

    def test_id_not_enumeration_order(self) -> None:
        from hldspec.feature_ledger import make_row

        row = make_row("auth", "login-form")
        self.assertNotRegex(row.feature_id, r"^F-\d+$")
        self.assertNotRegex(row.feature_id, r"^FL-\d+$")

    def test_stable_key_preserved_in_row(self) -> None:
        from hldspec.feature_ledger import make_row

        row = make_row("Auth Module", "Login Form")
        self.assertEqual(row.stable_key, "auth module::login form")

    def test_adding_row_does_not_change_existing_ids(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        r1 = make_row("auth", "login")
        r2 = make_row("dashboard", "main")
        ledger.add_row(r1)
        id_before = r1.feature_id

        ledger.add_row(r2)
        self.assertEqual(r1.feature_id, id_before)


class HashInputTests(unittest.TestCase):

    def test_hash_derives_from_normalized_key_only(self) -> None:
        import hashlib
        from hldspec.feature_ledger import make_row

        row = make_row("Auth", "Login Form")
        expected_key = "auth::login form"
        expected_hash = hashlib.sha256(expected_key.encode()).hexdigest()[:8]
        self.assertTrue(row.feature_id.endswith(expected_hash))

    def test_case_insensitive_key(self) -> None:
        from hldspec.feature_ledger import make_row

        r1 = make_row("Auth", "Login")
        r2 = make_row("AUTH", "login")
        self.assertEqual(r1.feature_id, r2.feature_id)

    def test_id_independent_of_other_row_content(self) -> None:
        from hldspec.feature_ledger import make_row

        r1 = make_row("auth", "login", evidence_level="OBSERVED", evidence="x", notes="aaa")
        r2 = make_row("auth", "login", evidence_level="INFERRED", evidence="y", notes="bbb")
        self.assertEqual(r1.feature_id, r2.feature_id)


class DuplicateMergeTests(unittest.TestCase):

    def test_same_key_merges_evidence_not_duplicates(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.upsert_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="views.py:10"))
        ledger.upsert_row(make_row("auth", "login", evidence_level="HISTORICAL", evidence="README mentions login"))

        self.assertEqual(len(ledger.rows), 1)
        self.assertIn("views.py:10", ledger.rows[0].evidence)
        self.assertIn("README mentions login", ledger.rows[0].evidence)

    def test_upsert_distinct_keys_keeps_separate_rows(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.upsert_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="a"))
        ledger.upsert_row(make_row("auth", "signup", evidence_level="OBSERVED", evidence="b"))
        self.assertEqual(len(ledger.rows), 2)


class DeterministicOutputTests(unittest.TestCase):

    def _make_ledger(self) -> "FeatureLedger":
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="auth/views.py"))
        ledger.add_row(make_row("dashboard", "overview", evidence_level="INFERRED", evidence="structure"))
        return ledger

    def test_json_output_is_deterministic(self) -> None:
        l1 = self._make_ledger()
        l2 = self._make_ledger()
        self.assertEqual(l1.to_json(), l2.to_json())

    def test_csv_output_is_deterministic(self) -> None:
        l1 = self._make_ledger()
        l2 = self._make_ledger()
        self.assertEqual(l1.to_csv(), l2.to_csv())

    def test_json_roundtrip(self) -> None:
        from hldspec.feature_ledger import FeatureLedger

        original = self._make_ledger()
        j = original.to_json()
        restored = FeatureLedger.from_dict(json.loads(j))
        self.assertEqual(original.to_json(), restored.to_json())

    def test_csv_has_all_columns(self) -> None:
        from hldspec.feature_ledger import CSV_COLUMNS

        ledger = self._make_ledger()
        reader = csv.DictReader(io.StringIO(ledger.to_csv()))
        self.assertEqual(list(reader.fieldnames or []), CSV_COLUMNS)

    def test_no_volatile_content_in_rows(self) -> None:
        ledger = self._make_ledger()
        j = ledger.to_json()
        for keyword in ("timestamp", "generated_at", "scanned_at", "run_id"):
            for row in json.loads(j)["rows"]:
                self.assertNotIn(keyword, row, f"volatile key {keyword} in row")


class IdempotentWriteTests(unittest.TestCase):

    def test_write_then_load_roundtrip(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="seen"))

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            ledger.write(qa)
            loaded = FeatureLedger.load(qa)
            self.assertEqual(ledger.to_json(), loaded.to_json())

    def test_write_twice_produces_identical_files(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="seen"))

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            ledger.write(qa)
            json1 = (qa / "feature-ledger.json").read_text()
            csv1 = (qa / "feature-ledger.csv").read_text()

            ledger.write(qa)
            json2 = (qa / "feature-ledger.json").read_text()
            csv2 = (qa / "feature-ledger.csv").read_text()

            self.assertEqual(json1, json2)
            self.assertEqual(csv1, csv2)

    def test_no_specify_dir_written(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="seen"))

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            ledger.write(qa)
            specify = Path(tmp) / ".specify"
            self.assertFalse(specify.exists(), ".specify/ must not be created")


class EvidenceRequiredTests(unittest.TestCase):

    def test_empty_evidence_with_observed_level_fails(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
            evidence_level="OBSERVED",
            evidence="",
        )
        errors = row.validate()
        self.assertTrue(any("evidence" in e.lower() for e in errors))

    def test_inferred_without_evidence_fails(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::b",
            area="a",
            screen_or_component="b",
            evidence_level="INFERRED",
            evidence="",
        )
        errors = row.validate()
        self.assertTrue(any("evidence" in e.lower() for e in errors))


class LedgerValidationTests(unittest.TestCase):

    def test_duplicate_feature_id_detected(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row

        ledger = FeatureLedger()
        r1 = make_row("auth", "login", evidence_level="OBSERVED", evidence="seen")
        r2 = make_row("auth", "login", evidence_level="OBSERVED", evidence="seen")
        ledger.add_row(r1)
        ledger.add_row(r2)
        errors = ledger.validate()
        self.assertTrue(any("duplicate" in e for e in errors))

    def test_missing_area_fails(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="::b",
            area="",
            screen_or_component="b",
        )
        errors = row.validate()
        self.assertTrue(any("area" in e for e in errors))

    def test_missing_screen_or_component_fails(self) -> None:
        from hldspec.feature_ledger import LedgerRow

        row = LedgerRow(
            feature_id="FL-x-00000000",
            stable_key="a::",
            area="a",
            screen_or_component="",
        )
        errors = row.validate()
        self.assertTrue(any("screen_or_component" in e for e in errors))


class ResolvedTargetQaPathTests(unittest.TestCase):

    def test_resolve_product_qa_dir_returns_target_qa(self) -> None:
        from hldspec.feature_ledger import resolve_product_qa_dir

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            qa = resolve_product_qa_dir(target)
            self.assertEqual(qa, target / "qa")

    def test_resolve_does_not_hardcode_string(self) -> None:
        import inspect
        from hldspec import feature_ledger

        source = inspect.getsource(feature_ledger.resolve_product_qa_dir)
        self.assertNotIn('"target/qa"', source)
        self.assertNotIn("'target/qa'", source)


class ConflictOnOverwriteTests(unittest.TestCase):

    def test_incompatible_schema_version_is_not_overwritten(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row, safe_write

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            qa.mkdir(parents=True)
            (qa / "feature-ledger.json").write_text(
                json.dumps({"schema_version": 999, "rows": []}), encoding="utf-8"
            )
            original = (qa / "feature-ledger.json").read_text()

            ledger = FeatureLedger()
            ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="x"))
            result = safe_write(ledger, qa)

            self.assertFalse(result.written)
            self.assertTrue(result.conflict)
            self.assertEqual((qa / "feature-ledger.json").read_text(), original)

    def test_malformed_existing_ledger_is_not_overwritten(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row, safe_write

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            qa.mkdir(parents=True)
            (qa / "feature-ledger.json").write_text("{ not valid json", encoding="utf-8")
            original = (qa / "feature-ledger.json").read_text()

            ledger = FeatureLedger()
            ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="x"))
            result = safe_write(ledger, qa)

            self.assertFalse(result.written)
            self.assertTrue(result.conflict)
            self.assertEqual((qa / "feature-ledger.json").read_text(), original)

    def test_compatible_existing_ledger_is_overwritten(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row, safe_write

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            ledger0 = FeatureLedger()
            ledger0.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="x"))
            ledger0.write(qa)

            ledger1 = FeatureLedger()
            ledger1.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="y"))
            result = safe_write(ledger1, qa)
            self.assertTrue(result.written)
            self.assertFalse(result.conflict)

    def test_fresh_dir_writes_cleanly(self) -> None:
        from hldspec.feature_ledger import FeatureLedger, make_row, safe_write

        with tempfile.TemporaryDirectory() as tmp:
            qa = Path(tmp) / "qa"
            ledger = FeatureLedger()
            ledger.add_row(make_row("auth", "login", evidence_level="OBSERVED", evidence="x"))
            result = safe_write(ledger, qa)
            self.assertTrue(result.written)
            self.assertFalse(result.conflict)


class ScannerTests(unittest.TestCase):

    def _fake_target(self, tmp: str) -> Path:
        target = Path(tmp) / "app"
        (target / "src" / "routes").mkdir(parents=True)
        (target / "src" / "routes" / "login.tsx").write_text(
            "export default function Login() { return <form><button>Sign in</button></form>; }",
            encoding="utf-8",
        )
        (target / "src" / "routes" / "dashboard.tsx").write_text(
            "export default function Dashboard() { return <div>overview</div>; }",
            encoding="utf-8",
        )
        (target / "README.md").write_text("# App\n\nUsers can log in and view a dashboard.\n", encoding="utf-8")
        return target

    def test_scanner_produces_rows(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            ledger = scan_target(target)
            self.assertGreater(len(ledger.rows), 0)

    def test_scanner_rows_are_valid(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            ledger = scan_target(target)
            self.assertEqual(ledger.validate(), [])

    def test_scanner_never_emits_pass_status(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            ledger = scan_target(target)
            for row in ledger.rows:
                self.assertNotEqual(row.status, "pass")
                self.assertIn(row.test_status, ("NOT_TESTED", "NOT_EXAMINED"))

    def test_scanner_actual_observed_is_not_examined(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            ledger = scan_target(target)
            for row in ledger.rows:
                self.assertEqual(row.actual_observed_behavior, "NOT_EXAMINED")

    def test_scanner_idempotent(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            l1 = scan_target(target)
            l2 = scan_target(target)
            self.assertEqual(l1.to_json(), l2.to_json())

    def test_scanner_does_not_modify_target(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            before = {p: p.read_text() for p in target.rglob("*") if p.is_file()}
            scan_target(target)
            after = {p: p.read_text() for p in target.rglob("*") if p.is_file()}
            self.assertEqual(before, after)

    def test_scanner_every_row_has_evidence(self) -> None:
        from hldspec.feature_ledger import scan_target

        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            ledger = scan_target(target)
            for row in ledger.rows:
                self.assertTrue(row.evidence, f"row {row.feature_id} missing evidence")


class ArtifactContractTests(unittest.TestCase):

    def test_feature_ledger_registered_in_contracts(self) -> None:
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS

        self.assertIn("feature-ledger", ARTIFACT_CONTRACTS)

    def test_contract_producer_is_scanner(self) -> None:
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS

        contract = ARTIFACT_CONTRACTS["feature-ledger"]
        self.assertIn("product", contract.producer.lower())

    def test_contract_output_not_under_specify(self) -> None:
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS

        contract = ARTIFACT_CONTRACTS["feature-ledger"]
        for f in contract.output_artifacts:
            self.assertNotIn(".specify", f)

    def test_contract_no_current_consumers(self) -> None:
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS

        contract = ARTIFACT_CONTRACTS["feature-ledger"]
        self.assertEqual(contract.consumers, [])

    def test_contract_non_execution_boundary_documented(self) -> None:
        from hldspec.artifact_contracts import ARTIFACT_CONTRACTS

        contract = ARTIFACT_CONTRACTS["feature-ledger"]
        notes = contract.notes.lower()
        self.assertIn("not permission to invoke speckit", notes)


class AuditPromptsUnchangedTests(unittest.TestCase):
    """Audit prompts must remain contractually read-only (session-reply, no files)."""

    def test_audit_plan_prompt_still_session_reply_only(self) -> None:
        text = (ROOT / "templates" / "audit" / "AUDIT_PLAN_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("your session reply, not a file", text)
        self.assertIn("Do not modify, create, or delete any file", text)

    def test_audit_consolidate_prompt_still_read_only(self) -> None:
        text = (ROOT / "templates" / "audit" / "AUDIT_CONSOLIDATE_PROMPT.md").read_text(encoding="utf-8")
        self.assertIn("READ-ONLY", text)
        self.assertIn("add no new findings", text)


class ScanReportTests(unittest.TestCase):

    def test_scan_report_written_under_control_plane(self) -> None:
        from hldspec.feature_ledger import write_scan_report

        with tempfile.TemporaryDirectory() as tmp:
            control_sync = Path(tmp) / ".hldspec" / "sync"
            control_sync.mkdir(parents=True)
            paths = write_scan_report(
                control_sync,
                {"target": "/x", "rows_written": 3, "conflict": False},
            )
            self.assertTrue(paths.json_path.exists())
            self.assertTrue(paths.md_path.exists())
            self.assertIn("product_qa_loop", str(paths.json_path))

    def test_scan_report_not_under_specify(self) -> None:
        from hldspec.feature_ledger import write_scan_report

        with tempfile.TemporaryDirectory() as tmp:
            control_sync = Path(tmp) / ".hldspec" / "sync"
            control_sync.mkdir(parents=True)
            paths = write_scan_report(control_sync, {"target": "/x", "rows_written": 0})
            self.assertNotIn(".specify", str(paths.json_path))
            self.assertNotIn(".specify", str(paths.md_path))


class CliTests(unittest.TestCase):

    def _fake_target(self, tmp: str) -> Path:
        target = Path(tmp) / "app"
        (target / "src" / "pages").mkdir(parents=True)
        (target / "src" / "pages" / "login.tsx").write_text(
            "export default function Login() { return <form><button>Sign in</button></form>; }",
            encoding="utf-8",
        )
        return target

    def test_cli_writes_ledger_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "product_ledger.py"), "--target", str(target)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue((target / "qa" / "feature-ledger.json").is_file())
            self.assertTrue((target / "qa" / "feature-ledger.csv").is_file())

    def test_cli_does_not_write_specify(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "product_ledger.py"), "--target", str(target)],
                capture_output=True, text=True,
            )
            self.assertFalse((target / ".specify").exists())

    def test_cli_conflict_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = self._fake_target(tmp)
            qa = target / "qa"
            qa.mkdir(parents=True)
            (qa / "feature-ledger.json").write_text(
                json.dumps({"schema_version": 999, "rows": []}), encoding="utf-8"
            )
            proc = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "product_ledger.py"), "--target", str(target)],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 4, proc.stdout + proc.stderr)
            self.assertIn("CONFLICT", proc.stdout)


if __name__ == "__main__":
    unittest.main()
