from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec import product_runability as pr
from hldspec import target_discovery as td

ROOT = Path(__file__).resolve().parents[1]


def _lineage(base: Path) -> None:
    source_package = base / ".hldspec" / "source_package"
    source_package.mkdir(parents=True, exist_ok=True)
    (source_package / "source_package.json").write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
    (source_package / "hld_reference_map.json").write_text(json.dumps({"anchors": {"HLD-001": {}}}), encoding="utf-8")


def _snapshot(target: Path) -> set[str]:
    return {str(p.relative_to(target)) for p in target.rglob("*")}


class ProductRunabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-product-runability-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_documented_cli_target_is_pass_with_discovered_commands(self) -> None:
        target = self.root / "target"
        _lineage(target)
        (target / "app.py").write_text("print('cli')\n", encoding="utf-8")
        (target / "requirements.txt").write_text("rich\n", encoding="utf-8")
        (target / "README.md").write_text(
            "# App\n\n```\npip install -r requirements.txt\npython3 app.py --help\n```\n\nRun the tests with `pytest`.\n",
            encoding="utf-8",
        )

        report = pr.write_product_runability_report(target)

        self.assertEqual("PASS", report["runability_status"])
        self.assertIn("pip install -r requirements.txt", report["likely_install_commands"])
        self.assertIn("python3 app.py --help", report["likely_start_commands"])
        self.assertEqual(["pytest"], report["likely_test_commands"])
        self.assertEqual("cli", report["detected_product_type"])
        self.assertIn("not executed", report["next_safe_action"])

    def test_wrapped_start_command_is_extracted(self) -> None:
        target = self.root / "target"
        _lineage(target)
        (target / "app.py").write_text("print('cli')\n", encoding="utf-8")
        (target / "README.md").write_text(
            '# App\n\n```\napp() { python3 app.py "$@"; }\n```\n\nRun the tests with `pytest`.\n',
            encoding="utf-8",
        )

        report = pr.write_product_runability_report(target)

        self.assertEqual(["python3 app.py"], report["likely_start_commands"])
        self.assertEqual("PASS", report["runability_status"])

    def test_product_files_without_docs_is_action(self) -> None:
        target = self.root / "target"
        _lineage(target)
        (target / "app.py").write_text("print('x')\n", encoding="utf-8")

        report = pr.write_product_runability_report(target)

        self.assertEqual("ACTION", report["runability_status"])
        self.assertTrue(any("lacks" in w for w in report["warnings"]))
        self.assertIn("rerun the runability gate", report["next_safe_action"])

    def test_no_product_code_is_unknown_with_safe_action(self) -> None:
        target = self.root / "target"
        _lineage(target)

        report = pr.write_product_runability_report(target)

        self.assertEqual("UNKNOWN", report["runability_status"])
        self.assertIn("nothing to run yet", report["next_safe_action"])

    def test_read_only_writes_only_control_reports(self) -> None:
        target = self.root / "target"
        _lineage(target)
        (target / "app.py").write_text("print('x')\n", encoding="utf-8")
        before = _snapshot(target)

        pr.write_product_runability_report(target)

        created = _snapshot(target) - before
        self.assertTrue(created, "control reports should be written")
        for path in created:
            self.assertTrue(path.startswith(".hldspec/sync") or path == ".hldspec/sync", path)

    def test_missing_target_is_not_created(self) -> None:
        target = self.root / "missing"

        report = pr.write_product_runability_report(target)

        self.assertFalse(report["reports_written"])
        self.assertFalse(target.exists())

    def test_external_controller_mode_writes_report_to_controller_sync(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        _lineage(controller)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (target / "app.py").write_text("print('x')\n", encoding="utf-8")

        report = pr.write_product_runability_report(target)

        controller_sync = controller / ".hldspec" / "sync"
        self.assertTrue((controller_sync / pr.REPORT_JSON).is_file())
        self.assertFalse((target / ".hldspec" / "sync").exists())
        self.assertEqual(str(controller_sync / pr.REPORT_JSON), report["report_paths"]["report_json"])

    def test_unknown_brownfield_never_gets_runnable_pass(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / "app.py").write_text("print('x')\n", encoding="utf-8")
        (target / "README.md").write_text(
            "```\npip install -r requirements.txt\npython3 app.py\n```\nRun tests with `pytest`.\n",
            encoding="utf-8",
        )

        report = pr.write_product_runability_report(target)

        self.assertEqual("BLOCKED", report["runability_status"])
        self.assertTrue(any("UNKNOWN_BROWNFIELD" in b for b in report["blockers"]))

    def test_blocked_phase_ledger_blocks_runability(self) -> None:
        target = self.root / "target"
        _lineage(target)
        spec_dir = target / "specs" / "001-x"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# s\n", encoding="utf-8")
        (spec_dir / "specify_validation.json").write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
        (target / "app.py").write_text("print('x')\n", encoding="utf-8")

        report = pr.write_product_runability_report(target)

        self.assertEqual("BLOCKED", report["runability_status"])

    def test_report_and_docs_do_not_overclaim_execution(self) -> None:
        target = self.root / "target"
        _lineage(target)
        (target / "app.py").write_text("print('x')\n", encoding="utf-8")
        report = pr.write_product_runability_report(target)
        md = pr.render_product_runability_md(report)
        self.assertIn("No command was executed", md)
        self.assertIn("not that the product was run", md)

        doc = (ROOT / "docs" / "HLDSPEC_TERMINOLOGY_AND_FLOW.md").read_text(encoding="utf-8")
        self.assertIn("`HLDspec product-report`", doc)
        self.assertIn("never runs commands", doc)
        self.assertIn("never that the", doc)
        self.assertIn("`HLDspec help product-report`", doc)


if __name__ == "__main__":
    unittest.main()
