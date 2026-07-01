import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hldspec import hld_source_package as sp
from hldspec import journey2_hld_coverage_contracts as cov
from hldspec.source_package_gate_facts import (
    SourcePackageGateFacts,
    build_source_package_gate_facts,
)
from hldspec.workspace_adapter import TargetWorkspaceAdapter


def _seed_min_package(source_dir: Path) -> None:
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / sp.AUTHORITATIVE_FILES["hld"]).write_text("# HLD\n", encoding="utf-8")
    (source_dir / sp.AUTHORITATIVE_FILES["marked_hld"]).write_text(
        "# HLD\n<!-- a:intro -->\n", encoding="utf-8"
    )
    (source_dir / sp.AUTHORITATIVE_FILES["reference_map"]).write_text(
        '{"a:intro": {}}\n', encoding="utf-8"
    )
    (source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).write_text(
        "# Single spec input\n", encoding="utf-8"
    )
    (source_dir / sp.AUTHORITATIVE_FILES["engineering_guidelines"]).write_text(
        "# Engineering Guidelines\n", encoding="utf-8"
    )


def _selected_backlog(**overrides) -> dict:
    base = {
        "schema_version": 1,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
        "source_refs": ["docs/hld.md"],
        "active_spec_id": "SPEC-001",
        "specs": [
            {
                "spec_id": "SPEC-001",
                "title": "Auth Module",
                "hld_anchor_ids": ["HLD-001"],
                "capability": "Authentication",
                "status": "SELECTED",
                "size_class": "BOUNDED_DELIVERABLE",
                "dependencies": [],
                "validation_strategy": ["integration_tests"],
                "target_materialization": "NOT_MATERIALIZED",
                "source_refs": ["docs/hld.md"],
            },
            {
                "spec_id": "SPEC-002",
                "title": "Logging Module",
                "hld_anchor_ids": ["HLD-002"],
                "capability": "Observability",
                "status": "PLANNED",
                "size_class": "BOUNDED_DELIVERABLE",
                "dependencies": [],
                "validation_strategy": ["unit_tests"],
                "target_materialization": "NOT_MATERIALIZED",
            },
        ],
    }
    base.update(overrides)
    return base


_MULTI_ANCHOR_HLD = (
    "# HLD\n\n"
    "## HLD-001 - Auth\n\nHLD-ID: HLD-001\n\nAuth module.\n\n"
    "## HLD-002 - Logging\n\nHLD-ID: HLD-002\n\nLogging module.\n"
)


class LegacyPackageWithoutScopeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source_dir = self.root / ".hldspec" / "source_package"
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_coverage_scope_is_none(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.coverage_scope)

    def test_active_spec_id_is_none(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.active_spec_id)

    def test_interpretation_ok_is_none(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.interpretation_ok)

    def test_receipt_present_false(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertFalse(facts.receipt_present)

    def test_validation_ok_true(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(facts.validation_ok)

    def test_no_read_errors(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.read_errors, ())

    def test_no_semantic_errors(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.semantic_errors, ())


class FullHldFactsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_coverage_scope_full_hld(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.coverage_scope, "FULL_HLD")

    def test_active_spec_id_none(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.active_spec_id)

    def test_interpretation_ok_true(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(facts.interpretation_ok)

    def test_receipt_not_present(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertFalse(facts.receipt_present)

    def test_validation_ok(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(facts.validation_ok)


class ActiveSpecFactsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_coverage_scope_active_spec(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.coverage_scope, "ACTIVE_SPEC")

    def test_active_spec_id(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.active_spec_id, "SPEC-001")

    def test_receipt_present(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(facts.receipt_present)

    def test_receipt_type(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.receipt_type, "ACTIVE_SPEC_SOURCE_PACKAGE_RENDER")

    def test_target_materialization(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.target_materialization, "NOT_MATERIALIZED")

    def test_selected_covered_no_blockers(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.selected_anchor_blocker_count, 0)
        self.assertEqual(facts.blocking_items, ())

    def test_non_selected_not_covered_in_out_of_scope(self):
        facts = build_source_package_gate_facts(self.source_dir)
        out_ids = [item["hld_item_id"] for item in facts.out_of_scope_items]
        self.assertIn("HLD-002", out_ids)

    def test_out_of_scope_advisory_count(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertEqual(facts.out_of_scope_advisory_count, len(facts.out_of_scope_items))


class ActiveSpecSelectedNotCoveredTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        ledger_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for item in ledger:
            if item["hld_item_id"] == "HLD-001":
                item["status"] = "NOT_COVERED"
                item["sdd_section"] = None
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def test_selected_not_covered_appears_in_blocking(self):
        facts = build_source_package_gate_facts(self.source_dir)
        blocked_ids = [item["hld_item_id"] for item in facts.blocking_items]
        self.assertIn("HLD-001", blocked_ids)

    def test_selected_anchor_blocker_count(self):
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertGreaterEqual(facts.selected_anchor_blocker_count, 1)


class SemanticErrorsSurfacedTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_receipt_in_full_hld_surfaces_semantic_error(self):
        scope_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
        scope["coverage_scope"] = "FULL_HLD"
        scope["active_spec_id"] = None
        scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)

        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(any("FULL_HLD" in e for e in facts.semantic_errors))

    def test_wrong_receipt_type_surfaces_semantic_error(self):
        receipt_path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["receipt_type"] = "WRONG"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)

        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(any("receipt_type" in e for e in facts.semantic_errors))


class MalformedScopeTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source_dir = self.root / ".hldspec" / "source_package"
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_malformed_scope_does_not_crash(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).write_text(
            "{bad json", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsInstance(facts, SourcePackageGateFacts)

    def test_malformed_scope_records_read_error(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).write_text(
            "{bad json", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(any("malformed" in e.lower() for e in facts.read_errors))

    def test_malformed_scope_coverage_scope_is_none(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).write_text(
            "{bad json", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.coverage_scope)


class MalformedLedgerTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )

    def tearDown(self):
        self._tmp.cleanup()

    def test_malformed_ledger_does_not_crash(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsInstance(facts, SourcePackageGateFacts)

    def test_malformed_ledger_records_read_error(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(any("malformed" in e.lower() for e in facts.read_errors))

    def test_malformed_ledger_interpretation_stays_none(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.interpretation_ok)


class MalformedReceiptTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source_dir = self.root / ".hldspec" / "source_package"
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_malformed_receipt_does_not_crash(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsInstance(facts, SourcePackageGateFacts)

    def test_malformed_receipt_records_read_error(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(any("malformed" in e.lower() for e in facts.read_errors))

    def test_malformed_receipt_still_present(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertTrue(facts.receipt_present)

    def test_malformed_receipt_type_is_none(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).write_text(
            "not json{{{", encoding="utf-8"
        )
        facts = build_source_package_gate_facts(self.source_dir)
        self.assertIsNone(facts.receipt_type)


class NoWriteTests(unittest.TestCase):
    def test_facts_function_does_not_write_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / ".hldspec" / "source_package"
            _seed_min_package(source_dir)
            sp.write_source_package(source_dir, hld_source_ref="/src/HLD.md", state="x")

            before = sorted(
                (p.relative_to(root), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()
            )
            build_source_package_gate_facts(source_dir)
            after = sorted(
                (p.relative_to(root), p.stat().st_mtime_ns) for p in root.rglob("*") if p.is_file()
            )
            self.assertEqual(before, after)


class NoGateCallTests(unittest.TestCase):
    def test_does_not_call_gate_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_dir = root / ".hldspec" / "source_package"
            _seed_min_package(source_dir)
            sp.write_source_package(source_dir, hld_source_ref="/src/HLD.md", state="x")

            with patch("hldspec.gate_validator.validate_gate") as mock_gate:
                build_source_package_gate_facts(source_dir)
                mock_gate.assert_not_called()


class NoSelectActiveSpecTests(unittest.TestCase):
    def test_does_not_call_select_active_spec(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            adapter = TargetWorkspaceAdapter(target_root=root, layout="new")
            source_dir = adapter.source_package_dir
            sp.build_source_package_content(
                root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=_selected_backlog(),
            )
            with patch("hldspec.spec_backlog.select_active_spec") as mock_select:
                build_source_package_gate_facts(source_dir)
                mock_select.assert_not_called()


class ValidationOkUnchangedTests(unittest.TestCase):
    def test_semantic_errors_do_not_affect_ok(self):
        v = sp.SourcePackageValidation(semantic_errors=["some error"])
        self.assertTrue(v.ok)

    def test_missing_does_affect_ok(self):
        v = sp.SourcePackageValidation(missing=["HLD.md"])
        self.assertFalse(v.ok)

    def test_hash_mismatches_affect_ok(self):
        v = sp.SourcePackageValidation(hash_mismatches=["HLD.md"])
        self.assertFalse(v.ok)


if __name__ == "__main__":
    unittest.main()
