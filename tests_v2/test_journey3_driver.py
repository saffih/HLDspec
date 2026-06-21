from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from hldspec import hld_source_package as sp
from hldspec import helper_selection as hsel
from hldspec import journey3_driver as drv

REQUIRED_FIELDS = (
    "driver_status",
    "target_root",
    "source_package_present",
    "source_package_validation",
    "binding_status",
    "helper_recommendations_present",
    "helper_selection_present",
    "selected_helper",
    "effective_helper_mode",
    "journey3_phase",
    "evidence_found",
    "missing_evidence",
    "blockers",
    "next_safe_action",
    "forbidden_without_approval",
    "protected_approvals_required",
)

HLD = "# HLD\n\n## HLD-001 - Demo\n\nHLD-ID: HLD-001\n\nText.\n"


def _build_package(root: Path) -> None:
    src = root / "SourceHLD.md"
    src.write_text(HLD, encoding="utf-8")
    sp.build_source_package_content(root, HLD, hld_source_ref=str(src), layout="new")


def _tree_snapshot(root: Path) -> dict[str, float]:
    return {
        str(p.relative_to(root)): p.stat().st_mtime_ns
        for p in root.rglob("*")
        if p.is_file()
    }


class Journey3DriverTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    # 1. missing source package -> BLOCKED with a return-to-Journey-2 next action.
    def test_missing_source_package_is_blocked(self) -> None:
        report = drv.build_journey3_status(self.root)
        self.assertEqual(report["driver_status"], "BLOCKED")
        self.assertFalse(report["source_package_present"])
        self.assertIn("Journey 2", report["next_safe_action"])
        self.assertTrue(report["blockers"])

    # 2. valid source package, no helper selection -> ACTION.
    def test_valid_package_no_selection_is_action(self) -> None:
        _build_package(self.root)
        report = drv.build_journey3_status(self.root)
        self.assertEqual(report["driver_status"], "ACTION")
        self.assertTrue(report["source_package_present"])
        self.assertTrue(report["source_package_validation"]["ok"])
        self.assertFalse(report["helper_selection_present"])

    # 3. recommendation present but no selection -> driver does NOT auto-select.
    def test_recommendation_present_does_not_autoselect(self) -> None:
        _build_package(self.root)  # emits helper_recommendations.json
        report = drv.build_journey3_status(self.root)
        self.assertTrue(report["helper_recommendations_present"])
        self.assertIsNone(report["selected_helper"])  # never auto-set to the recommendation
        self.assertFalse(report["helper_selection_present"])
        self.assertEqual(report["driver_status"], "ACTION")

    # 4. selected helper present but not operational -> ACTION, no execution.
    def test_selected_non_operational_helper_is_action_not_executed(self) -> None:
        _build_package(self.root)
        # Hand-write a selection naming a planned (non-operational) helper, bypassing
        # the write API's operational guard, to simulate a tampered/forward selection.
        sel_path = hsel.selection_path(self.root)
        sel_path.parent.mkdir(parents=True, exist_ok=True)
        sel_path.write_text(json.dumps({"schema_version": 1, "selected_helper_id": "codex"}), encoding="utf-8")
        report = drv.build_journey3_status(self.root)
        self.assertEqual(report["selected_helper"], "codex")
        self.assertFalse(report["effective_helper_mode"]["operational"])
        self.assertEqual(report["driver_status"], "ACTION")
        self.assertFalse(report["executed_anything"])

    # 5. unknown helper -> GUIDE_ONLY authority fallback / ACTION.
    def test_unknown_helper_falls_back_to_guide_only(self) -> None:
        _build_package(self.root)
        sel_path = hsel.selection_path(self.root)
        sel_path.parent.mkdir(parents=True, exist_ok=True)
        sel_path.write_text(json.dumps({"schema_version": 1, "selected_helper_id": "totally-unknown"}), encoding="utf-8")
        report = drv.build_journey3_status(self.root)
        self.assertEqual(report["effective_helper_mode"]["authority_levels"], ["GUIDE_ONLY"])
        self.assertEqual(report["driver_status"], "ACTION")

    # 6. JSON output is stable and includes the required fields.
    def test_json_output_has_required_fields(self) -> None:
        _build_package(self.root)
        report = drv.build_journey3_status(self.root)
        for field in REQUIRED_FIELDS:
            self.assertIn(field, report)
        # Round-trips through JSON unchanged (stable, serializable).
        self.assertEqual(json.loads(json.dumps(report)), report)

    # 7. driver never mutates target files.
    def test_driver_does_not_mutate_target(self) -> None:
        _build_package(self.root)
        before = _tree_snapshot(self.root)
        drv.build_journey3_status(self.root)
        after = _tree_snapshot(self.root)
        self.assertEqual(before, after)

    # 8. driver runs no subprocess (helper or otherwise) in the pure aggregator.
    def test_driver_runs_no_subprocess(self) -> None:
        _build_package(self.root)

        def _tripwire(*a, **k):
            raise AssertionError(f"driver must not run a subprocess: {a!r}")

        with mock.patch("subprocess.run", _tripwire), mock.patch("subprocess.Popen", _tripwire):
            report = drv.build_journey3_status(self.root)  # no injected phase report
        self.assertEqual(report["phase_source"], "not_provided")
        self.assertEqual(report["journey3_phase"], "UNKNOWN_REQUIRES_READINESS_RUN")

    # 9 & 10. forbidden actions and protected approvals are listed.
    def test_forbidden_and_protected_listed(self) -> None:
        report = drv.build_journey3_status(self.root)
        self.assertTrue(report["forbidden_without_approval"])
        self.assertTrue(report["protected_approvals_required"])
        prot = " ".join(report["protected_approvals_required"]).lower()
        self.assertIn("approve a new helper", prot)
        self.assertIn("mark a helper operational", prot)

    # 11. source package validation result is reflected (and drives BLOCKED).
    def test_validation_result_reflected(self) -> None:
        _build_package(self.root)
        # Corrupt a hashed file so validate_source_package().ok() becomes False.
        src_dir, _ = sp.source_package_paths(self.root, layout="new")
        (src_dir / sp.AUTHORITATIVE_FILES["hld"]).write_text("# TAMPERED\n", encoding="utf-8")
        report = drv.build_journey3_status(self.root)
        self.assertFalse(report["source_package_validation"]["ok"])
        self.assertTrue(report["source_package_validation"]["hash_mismatches"])
        self.assertEqual(report["driver_status"], "BLOCKED")

    # Real seam: a genuine readiness report (not a hand-built fixture) flows through.
    def test_real_readiness_report_injection_yields_phase_enum(self) -> None:
        import subprocess

        from hldspec import next_feature_readiness as nfr

        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        _build_package(self.root)
        real_report = nfr.build_next_feature_readiness_report(self.root)
        report = drv.build_journey3_status(self.root, next_feature_report=real_report)
        self.assertEqual(report["phase_source"], "injected")
        # The phase is a real PHASE_* value from the engine, not the sentinel.
        self.assertNotEqual(report["journey3_phase"], drv.PHASE_UNKNOWN_REQUIRES_READINESS_RUN)
        self.assertEqual(report["journey3_phase"], real_report["phase"])
        # A real BLOCKED phase must fold into blockers, not actions (constant, not literal).
        if real_report.get("safety_status") == nfr.SAFETY_BLOCKED:
            for b in real_report.get("blockers", []):
                self.assertIn(b, report["blockers"])

    # Injected phase flows through to journey3_phase without the driver computing it.
    def test_injected_phase_flows_through(self) -> None:
        _build_package(self.root)
        fake_report = {
            "phase": "READY_FOR_PLAN",
            "verified_evidence": {"spec_md": "specs/x/spec.md"},
            "missing_evidence": [],
            "blockers": [],
            "safety_status": "ACTION",
            "next_safe_action": "Run /speckit-plan (human-run).",
        }
        report = drv.build_journey3_status(self.root, next_feature_report=fake_report)
        self.assertEqual(report["journey3_phase"], "READY_FOR_PLAN")
        self.assertEqual(report["phase_source"], "injected")
        self.assertIn("spec_md", report["evidence_found"])


if __name__ == "__main__":
    unittest.main()
