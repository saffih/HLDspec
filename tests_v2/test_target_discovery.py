from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec import hld_source_package as hsp
from hldspec import target_discovery as td


ROOT = Path(__file__).resolve().parents[1]
FACADE = ROOT / "scripts" / "hldspec_agent_session.py"


def _write_package(
    package_dir: Path,
    *,
    bound_to: Path | None,
    source_ref: str = "/src/HLD.md",
    source_sha256: str | None = None,
    extra: dict | None = None,
) -> None:
    """Manifest + anchor map; bound to a target unless bound_to is None (legacy)."""
    package_dir.mkdir(parents=True, exist_ok=True)
    metadata: dict = {"schema_version": 1}
    if bound_to is not None:
        metadata.update(hsp.build_binding_fields(bound_to, source_ref=source_ref, source_sha256=source_sha256))
    if extra:
        metadata.update(extra)
    (package_dir / "source_package.json").write_text(json.dumps(metadata), encoding="utf-8")
    (package_dir / "hld_reference_map.json").write_text(json.dumps({"anchors": {"HLD-001": {}}}), encoding="utf-8")


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
        _write_package(target / ".hldspec" / "source_package", bound_to=target)

    def _run_facade(self, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        import os

        return subprocess.run(
            [sys.executable, str(FACADE), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, **env} if env else None,
        )

    def test_missing_target_is_new_greenfield_and_creates_nothing(self) -> None:
        target = self.root / "target"

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_NEW_GREENFIELD, report["classification"])
        self.assertFalse(report["reports_written"])
        self.assertFalse(target.exists(), "checking a missing target must not create it")

    def test_empty_existing_target_is_new_greenfield_and_writes_reports(self) -> None:
        target = self.root / "target"
        target.mkdir()

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_NEW_GREENFIELD, report["classification"])
        self.assertTrue(report["reports_written"])
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

    def test_empty_source_package_dir_with_existing_code_is_unknown_brownfield(self) -> None:
        target = self.root / "target"
        (target / ".hldspec" / "source_package").mkdir(parents=True)
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertFalse(report["trusted_hldspec_lineage"])

    def test_empty_source_package_dir_without_code_is_not_prepared(self) -> None:
        target = self.root / "target"
        (target / ".hldspec" / "source_package").mkdir(parents=True)

        report = td.write_discovery_reports(target)

        self.assertNotEqual(td.CLASS_PREPARED_GREENFIELD, report["classification"])
        self.assertFalse(report["trusted_hldspec_lineage"])

    def test_specify_dir_alone_is_not_trusted(self) -> None:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertFalse(report["trusted_hldspec_lineage"])

    def test_specs_dir_alone_is_not_trusted(self) -> None:
        target = self.root / "target"
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertFalse(report["trusted_hldspec_lineage"])

    def test_copied_agent_session_from_other_target_is_not_trusted(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")
        (target / ".hldspec").mkdir()
        (target / ".hldspec" / "agent_session.json").write_text(
            json.dumps({"source": {"path": "/elsewhere/HLD.md"}, "target": "/some/other/target"}),
            encoding="utf-8",
        )

        report = td.write_discovery_reports(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])

    def test_agent_session_with_bare_string_source_is_not_trusted(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")
        (target / ".hldspec").mkdir()
        (target / ".hldspec" / "agent_session.json").write_text(
            json.dumps({"source": "x", "target": "y"}), encoding="utf-8"
        )

        report = td.write_discovery_reports(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])

    def test_agent_session_belonging_to_this_target_is_trusted(self) -> None:
        target = self.root / "target"
        target.mkdir()
        (target / ".hldspec").mkdir()
        (target / ".hldspec" / "agent_session.json").write_text(
            json.dumps({"source": {"path": str(self.root / "HLD.md")}, "target": str(target)}),
            encoding="utf-8",
        )

        report = td.write_discovery_reports(target)

        self.assertTrue(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_PREPARED_GREENFIELD, report["classification"])

    def test_external_implementation_lineage_classifies_evolving(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        _write_package(controller / ".hldspec" / "source_package", bound_to=target)
        (controller / ".hldspec" / "sync").mkdir(parents=True)
        (controller / ".hldspec" / "sync" / "implementation_lineage.json").write_text("{}", encoding="utf-8")
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_EVOLVING_GREENFIELD, report["classification"])

    def test_markdown_only_validation_evidence_is_unverified(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (spec_dir / "specify_validation.md").write_text("looks good\n", encoding="utf-8")

        report = td.write_discovery_reports(target)
        ledger = report["phase_ledger"]

        self.assertTrue(any(e["phase"] == "specify" and e["status"] == td.PHASE_UNVERIFIED for e in ledger["entries"]))
        self.assertEqual(td.SAFETY_ACTION, ledger["safety_status"])

    def test_empty_and_malformed_json_evidence_is_unverified(self) -> None:
        for payload in ("{}", "{not json"):
            with self.subTest(payload=payload):
                target = self.root / f"target-{abs(hash(payload))}"
                self._lineage(target)
                spec_dir = target / "specs" / "001-demo"
                spec_dir.mkdir(parents=True)
                (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
                (spec_dir / "specify_validation.json").write_text(payload, encoding="utf-8")

                report = td.write_discovery_reports(target)
                ledger = report["phase_ledger"]

                self.assertTrue(
                    any(e["phase"] == "specify" and e["status"] == td.PHASE_UNVERIFIED for e in ledger["entries"])
                )
                self.assertEqual(td.SAFETY_ACTION, ledger["safety_status"])

    def test_manifest_without_anchor_map_is_not_trusted(self) -> None:
        target = self.root / "target"
        source_package = target / ".hldspec" / "source_package"
        source_package.mkdir(parents=True)
        (source_package / "source_package.json").write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])

    def test_pointer_to_controller_with_valid_source_package_is_trusted(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        _write_package(controller / ".hldspec" / "source_package", bound_to=target)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )

        report = td.write_discovery_reports(target)

        self.assertTrue(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_PREPARED_GREENFIELD, report["classification"])
        self.assertTrue(any(item["kind"] == "hldspec_run_pointer" for item in report["lineage_evidence"]))

    def test_pointer_to_controller_without_valid_state_is_not_trusted(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        (controller / ".hldspec" / "source_package").mkdir(parents=True)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])

    def test_external_mode_writes_reports_to_controller_sync(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        _write_package(controller / ".hldspec" / "source_package", bound_to=target)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )

        report = td.write_discovery_reports(target)

        controller_sync = controller / ".hldspec" / "sync"
        self.assertTrue((controller_sync / td.DISCOVERY_JSON).is_file())
        self.assertTrue((controller_sync / td.LEDGER_JSON).is_file())
        self.assertFalse((target / ".hldspec" / "sync").exists())
        self.assertEqual(str(controller_sync / td.DISCOVERY_JSON), report["report_paths"]["discovery_json"])

    def test_external_mode_status_prints_controller_report_path(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        _write_package(controller / ".hldspec" / "source_package", bound_to=target)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )

        status = self._run_facade("status", "--target", str(target))

        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn(str(controller / ".hldspec" / "sync" / td.DISCOVERY_JSON), status.stdout)
        self.assertNotIn(str(target / ".hldspec" / "sync"), status.stdout)

    def test_external_start_prints_controller_paths_not_deleted_target_paths(self) -> None:
        source = self._source()
        target = self.root / "target"
        runs = self.root / "runs"

        result = self._run_facade(
            "start",
            "--source",
            str(source),
            "--target",
            str(target),
            "--state-location",
            "external",
            env={"HLDSPEC_RUNS_DIR": str(runs)},
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        match = re.search(r"Discovery report: (.+)", result.stdout)
        self.assertIsNotNone(match, result.stdout)
        printed = Path(match.group(1).strip()).resolve()
        self.assertTrue(printed.is_file(), printed)
        self.assertIn(str(runs.resolve()), str(printed))
        self.assertNotIn(str(target / ".hldspec" / "sync"), result.stdout)
        self.assertFalse((target / ".hldspec" / "sync").exists())

    def test_unverified_artifact_sets_safety_action_with_active_lifecycle(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        report = td.write_discovery_reports(target)
        ledger = report["phase_ledger"]

        self.assertEqual(td.PHASE_ACTIVE, ledger["overall_status"])
        self.assertEqual(td.SAFETY_ACTION, ledger["safety_status"])
        self.assertEqual(td.SAFETY_ACTION, report["phase_ledger_safety"])
        self.assertTrue(any("safety blocks continuation" in item for item in report["blockers"]))

    def test_stale_artifact_sets_safety_blocked(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        (target / ".hldspec" / "source_freshness.json").write_text(json.dumps({"blocking": True}), encoding="utf-8")
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertEqual(td.SAFETY_BLOCKED, report["phase_ledger"]["safety_status"])

    def test_verified_artifacts_have_safety_pass(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (spec_dir / "specify_validation.json").write_text(json.dumps({"status": "PASS"}), encoding="utf-8")

        report = td.write_discovery_reports(target)

        self.assertEqual(td.SAFETY_PASS, report["phase_ledger"]["safety_status"])
        self.assertEqual(td.PHASE_DONE, report["phase_ledger"]["overall_status"])

    def test_failing_validation_evidence_blocks_instead_of_done(self) -> None:
        target = self.root / "target"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (spec_dir / "specify_validation.json").write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")

        report = td.write_discovery_reports(target)
        ledger = report["phase_ledger"]

        self.assertEqual(td.SAFETY_BLOCKED, ledger["safety_status"])
        self.assertTrue(any(entry["phase"] == "specify" and entry["status"] == td.PHASE_BLOCKED for entry in ledger["entries"]))
        self.assertFalse(any(entry["phase"] == "specify" and entry["status"] == td.PHASE_DONE for entry in ledger["entries"]))
        self.assertTrue(any("failing status" in item for item in ledger["blockers"]))

    def test_continue_blocks_on_unverified_phase_artifact(self) -> None:
        target = self.root / "unverified"
        self._lineage(target)
        spec_dir = target / "specs" / "001-demo"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")

        result = self._run_facade("continue", "--target", str(target))

        self.assertEqual(3, result.returncode, result.stderr + result.stdout)
        self.assertIn("BLOCKED by target discovery", result.stdout)
        self.assertIn("UNVERIFIED", result.stdout + result.stderr)

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


class SourcePackageBindingTests(unittest.TestCase):
    """Invariant B: a copied .hldspec/source_package must not transfer trust."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-binding-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _payload(self, target: Path) -> None:
        target.mkdir(parents=True, exist_ok=True)
        (target / "app.py").write_text("print('existing')\n", encoding="utf-8")

    def test_in_place_bound_package_is_trusted_with_bound_match(self) -> None:
        target = self.root / "target"
        _write_package(target / ".hldspec" / "source_package", bound_to=target)

        report = td.build_target_discovery(target)

        self.assertTrue(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_PREPARED_GREENFIELD, report["classification"])
        self.assertEqual(td.BINDING_BOUND_MATCH, report["source_package_binding"]["state"])
        self.assertTrue(any(item.get("kind") == "source_package_binding" for item in report["lineage_evidence"]))

    def test_package_copied_to_another_target_is_not_trusted(self) -> None:
        import shutil

        original = self.root / "original"
        _write_package(original / ".hldspec" / "source_package", bound_to=original)
        victim = self.root / "victim"
        self._payload(victim)
        shutil.copytree(original / ".hldspec", victim / ".hldspec")

        report = td.build_target_discovery(victim)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertEqual(td.BINDING_BOUND_MISMATCH, report["source_package_binding"]["state"])
        self.assertTrue(any("must not transfer trust" in item for item in report["blockers"]))

    def test_target_path_mismatch_blocks_trust(self) -> None:
        target = self.root / "target"
        self._payload(target)
        _write_package(target / ".hldspec" / "source_package", bound_to=self.root / "elsewhere")

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertEqual(td.BINDING_BOUND_MISMATCH, report["source_package_binding"]["state"])
        self.assertIn("different target", report["source_package_binding"]["mismatch_reason"])

    def test_source_hash_mismatch_with_pointer_evidence_blocks_trust(self) -> None:
        target = self.root / "target"
        self._payload(target)
        controller = self.root / "controller"
        _write_package(controller / ".hldspec" / "source_package", bound_to=target, source_sha256="a" * 64)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller), "source_sha256": "b" * 64}),
            encoding="utf-8",
        )

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertEqual(td.BINDING_BOUND_MISMATCH, report["source_package_binding"]["state"])
        self.assertIn("source_sha256", report["source_package_binding"]["mismatch_reason"])

    def test_matching_source_hash_with_pointer_evidence_stays_trusted(self) -> None:
        target = self.root / "target"
        target.mkdir()
        controller = self.root / "controller"
        _write_package(controller / ".hldspec" / "source_package", bound_to=target, source_sha256="a" * 64)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller), "source_sha256": "a" * 64}),
            encoding="utf-8",
        )

        report = td.build_target_discovery(target)

        self.assertTrue(report["trusted_hldspec_lineage"])
        self.assertEqual(td.BINDING_BOUND_MATCH, report["source_package_binding"]["state"])

    def test_malformed_binding_is_invalid_and_untrusted(self) -> None:
        target = self.root / "target"
        self._payload(target)
        _write_package(
            target / ".hldspec" / "source_package",
            bound_to=target,
            extra={"target_path_sha256": "deadbeef"},
        )

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertEqual(td.BINDING_INVALID, report["source_package_binding"]["state"])

    def test_partial_binding_is_invalid_and_untrusted(self) -> None:
        target = self.root / "target"
        self._payload(target)
        _write_package(
            target / ".hldspec" / "source_package",
            bound_to=None,
            extra={"target_path": str(target)},
        )

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.BINDING_INVALID, report["source_package_binding"]["state"])

    def test_legacy_unbound_package_warns_and_is_not_fully_trusted(self) -> None:
        target = self.root / "target"
        _write_package(target / ".hldspec" / "source_package", bound_to=None)

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertNotEqual(td.CLASS_PREPARED_GREENFIELD, report["classification"])
        self.assertEqual(td.BINDING_UNBOUND_LEGACY, report["source_package_binding"]["state"])
        self.assertTrue(any("legacy/unbound" in item for item in report["warnings"]))
        self.assertIn("bind it to this target", report["next_safe_action"])

    def test_legacy_unbound_package_with_product_files_is_unknown_brownfield(self) -> None:
        target = self.root / "target"
        self._payload(target)
        _write_package(target / ".hldspec" / "source_package", bound_to=None)

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])
        self.assertEqual(td.BINDING_UNBOUND_LEGACY, report["source_package_binding"]["state"])

    def test_mismatched_package_overrides_valid_agent_session(self) -> None:
        target = self.root / "target"
        self._payload(target)
        _write_package(target / ".hldspec" / "source_package", bound_to=self.root / "elsewhere")
        (target / ".hldspec" / "agent_session.json").write_text(
            json.dumps({"source": {"path": str(self.root / "HLD.md")}, "target": str(target)}),
            encoding="utf-8",
        )

        report = td.build_target_discovery(target)

        self.assertFalse(report["trusted_hldspec_lineage"])
        self.assertEqual(td.CLASS_UNKNOWN_BROWNFIELD, report["classification"])


if __name__ == "__main__":
    unittest.main()
