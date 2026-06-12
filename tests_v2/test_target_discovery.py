from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec import target_discovery as td


ROOT = Path(__file__).resolve().parents[1]
FACADE = ROOT / "scripts" / "hldspec_agent_session.py"


class TargetDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-target-discovery-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _source(self) -> Path:
        source = self.root / "HLD.md"
        source.write_text("# HLD\n\n## HLD-001 - Demo\n\nHLD-ID: HLD-001\n", encoding="utf-8")
        return source

    def _lineage(self, target: Path) -> None:
        source_package = target / ".hldspec" / "source_package"
        source_package.mkdir(parents=True, exist_ok=True)
        (source_package / "source_package.json").write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        (source_package / "hld_reference_map.json").write_text(json.dumps({"anchors": {"HLD-001": {}}}), encoding="utf-8")

    def _run_facade(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(FACADE), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_empty_target_is_new_greenfield_and_writes_reports(self) -> None:
        target = self.root / "target"

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_NEW_GREENFIELD, report["classification"])
        self.assertTrue((target / ".hldspec" / "sync" / td.DISCOVERY_JSON).exists())
        self.assertTrue((target / ".hldspec" / "sync" / td.LEDGER_JSON).exists())

    def test_source_package_lineage_is_prepared_greenfield(self) -> None:
        target = self.root / "target"
        self._lineage(target)

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_PREPARED_GREENFIELD, report["classification"])
        self.assertTrue(report["trusted_hldspec_lineage"])

    def test_speckit_memory_with_lineage_is_initialized_greenfield(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        (target / ".specify" / "memory").mkdir(parents=True)

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_INITIALIZED_GREENFIELD, report["classification"])

    def test_spec_without_validation_is_unverified_active_not_done(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        report = td.write_discovery_reports(target)
        ledger = report["phase_ledger"]

        self.assertEqual(td.CLASS_PHASED_GREENFIELD, report["classification"])
        self.assertEqual(td.PHASE_ACTIVE, ledger["overall_status"])
        self.assertTrue(any(entry["phase"] == "specify" and entry["status"] == td.PHASE_UNVERIFIED for entry in ledger["entries"]))
        self.assertFalse(any(entry["phase"] == "specify" and entry["status"] == td.PHASE_DONE for entry in ledger["entries"]))

    def test_phase_artifact_with_validation_evidence_is_done(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (spec_dir / "specify_validation.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

        report = td.write_discovery_reports(target)
        ledger = report["phase_ledger"]

        self.assertEqual(td.PHASE_DONE, ledger["overall_status"])
        self.assertTrue(any(entry["phase"] == "specify" and entry["status"] == td.PHASE_DONE for entry in ledger["entries"]))

    def test_existing_code_without_lineage_is_unknown_brownfield(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertTrue(report["blockers"])

    def test_start_blocks_unknown_brownfield_without_wipe_recommendation(self) -> None:
        source = self._source()
        target = self.root / "brownfield"
        target.mkdir()
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")

        result = self._run_facade("start", "--source", str(source), "--target", str(target))

        self.assertEqual(3, result.returncode, result.stderr + result.stdout)
        self.assertIn(td.CLASS_UNKNOWN_BROWNFIELD, result.stdout)
        self.assertIn("adoption is unsupported", result.stdout)
        self.assertNotIn("wipe", result.stdout.lower())

    def test_rerun_start_status_on_known_target_does_not_recommend_wipe(self) -> None:
        source = self._source()
        target = self.root / "prepared"
        self._lineage(target)

        start = self._run_facade("start", "--source", str(source), "--target", str(target))
        status = self._run_facade("status", "--target", str(target))

        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn(td.CLASS_PREPARED_GREENFIELD, start.stdout)
        self.assertNotIn("wipe", (start.stdout + status.stdout).lower())

    def test_status_doctor_and_operator_state_agree_on_classification(self) -> None:
        target = self.root / "prepared"
        self._lineage(target)

        status = self._run_facade("status", "--target", str(target))
        doctor = self._run_facade("doctor", "--target", str(target))
        operator = self._run_facade("operator-state", "--target", str(target))

        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn(td.CLASS_PREPARED_GREENFIELD, status.stdout)
        self.assertIn(td.CLASS_PREPARED_GREENFIELD, doctor.stdout)
        self.assertIn(td.CLASS_PREPARED_GREENFIELD, operator.stdout)


if __name__ == "__main__":
    unittest.main()
