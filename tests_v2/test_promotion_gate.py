from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecPromotionGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def make_target(self) -> Path:
        target = self.tmp_path / "target"
        (target / "targetHLD").mkdir(parents=True)
        (target / "targetHLD" / "HLD.md").write_text("# HLD\n\n## HLD-001 - API\n\nBody.\n", encoding="utf-8")
        (target / ".hldspec").mkdir(parents=True)
        (target / ".hldspec" / "agent_session.json").write_text(
            json.dumps({"schema_version": "1.0", "target": str(target)}, indent=2) + "\n",
            encoding="utf-8",
        )
        (target / ".hldspec" / "spec_packages.json").write_text(
            json.dumps(
                {
                    "packages": [
                        {
                            "package_id": "001-api-foundation",
                            "package_name": "API foundation",
                            "description": "First bounded package.",
                        }
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return target

    def build_prompts(self, target: Path) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)

    def validate_context(self, target: Path) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_hldspec_target.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)

    def run_gate(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "check_hldspec_promotion_gate.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def read_gate_report(self, target: Path) -> dict:
        return json.loads((target / ".hldspec" / "validation" / "promotion_gate.json").read_text(encoding="utf-8"))

    def test_gate_passes_on_clean_generated_validation_reports(self) -> None:
        target = self.make_target()
        source = target / "targetHLD" / "HLD.md"
        before = source.read_text(encoding="utf-8")
        self.build_prompts(target)
        self.validate_context(target)

        result = self.run_gate(target)
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)

        report = self.read_gate_report(target)
        self.assertEqual("PASS", report["status"])
        self.assertEqual([], report["findings"])
        self.assertEqual(before, source.read_text(encoding="utf-8"))

    def test_gate_actions_when_context_validation_report_has_action(self) -> None:
        target = self.make_target()
        self.build_prompts(target)
        report_path = target / ".hldspec" / "validation" / "context_prompt_validation.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "status": "ACTION",
                    "findings": [{"severity": "ACTION", "check": "example", "message": "fix required"}],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        result = self.run_gate(target)
        self.assertEqual(2, result.returncode)

        report = self.read_gate_report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any(item["check"] == "validator_report" for item in report["findings"]))

    def test_gate_actions_when_prompts_exist_without_context_validation_report(self) -> None:
        target = self.make_target()
        self.build_prompts(target)

        result = self.run_gate(target)
        self.assertEqual(2, result.returncode)

        report = self.read_gate_report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any(item["check"] == "context_prompt_validation" for item in report["findings"]))

    def test_gate_conflicts_when_unresolved_human_checkpoint_exists(self) -> None:
        target = self.make_target()
        self.build_prompts(target)
        self.validate_context(target)
        checkpoint_path = target / ".hldspec" / "sync" / "speckit_prework_package.json"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps({"human_checkpoint": {"human_decision": "TBD", "question": "Approve prework?"}}, indent=2) + "\n",
            encoding="utf-8",
        )

        result = self.run_gate(target)
        self.assertEqual(2, result.returncode)

        report = self.read_gate_report(target)
        self.assertEqual("CONFLICT", report["status"])
        self.assertTrue(any(item["check"] == "unresolved_human_checkpoint" for item in report["findings"]))

    def test_gate_blocks_readiness_mark_above_seven_without_evidence(self) -> None:
        target = self.make_target()
        self.build_prompts(target)
        self.validate_context(target)
        scorecard = target / ".hldspec" / "readiness_scorecard.json"
        scorecard.write_text(json.dumps({"readiness_mark": 8}, indent=2) + "\n", encoding="utf-8")

        result = self.run_gate(target)
        self.assertEqual(2, result.returncode)

        report = self.read_gate_report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any(item["check"] == "readiness_evidence" for item in report["findings"]))

    def test_reports_are_written_as_json_and_markdown(self) -> None:
        target = self.make_target()
        self.build_prompts(target)
        self.validate_context(target)

        result = self.run_gate(target)
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)

        json_report = target / ".hldspec" / "validation" / "promotion_gate.json"
        md_report = target / ".hldspec" / "validation" / "promotion_gate.md"
        self.assertTrue(json_report.exists())
        self.assertTrue(md_report.exists())
        self.assertIn("Status: `PASS`", md_report.read_text(encoding="utf-8"))

    def test_doctor_reports_promotion_gate_status_when_target_is_provided(self) -> None:
        source = self.tmp_path / "source.md"
        target = self.tmp_path / "doctor-target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--source",
                str(source),
                "--target",
                str(target),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        gate_path = target / ".hldspec" / "validation" / "promotion_gate.json"
        gate_path.parent.mkdir(parents=True, exist_ok=True)
        gate_path.write_text(json.dumps({"status": "PASS"}, indent=2) + "\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_agent_session.py"),
                "doctor",
                "--target",
                str(target),
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Promotion gate: PASS", result.stdout)
        self.assertIn("Summary: ACTION", result.stdout)


if __name__ == "__main__":
    unittest.main()
