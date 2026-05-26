from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PromotedCapabilityRunSkepticGateTests(unittest.TestCase):
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
        self.run_script("build_speckit_context_prompts.py", target, expected=0)
        self.run_script("validate_hldspec_target.py", target, expected=0)
        return target

    def run_script(self, script: str, target: Path, *, expected: int | None = None) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / script), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if expected is not None:
            self.assertEqual(expected, result.returncode, result.stderr + result.stdout)
        return result

    def write_promoted_capabilities(self, target: Path, capabilities: list[dict]) -> Path:
        path = target / ".hldspec" / "promoted_capabilities.json"
        path.write_text(json.dumps({"capabilities": capabilities}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    def read_gate_report(self, target: Path) -> dict:
        return json.loads((target / ".hldspec" / "validation" / "promotion_gate.json").read_text(encoding="utf-8"))

    def test_promoted_capability_with_runskeptic_pass_evidence_passes(self) -> None:
        target = self.make_target()
        self.write_promoted_capabilities(
            target,
            [
                {
                    "name": "context economy prompt generation",
                    "runskeptic_status": "PASS",
                    "runskeptic_evidence": [
                        "RunSkeptic reviewed generated prompt validation and found no ACTION/CONFLICT findings."
                    ],
                }
            ],
        )

        result = self.run_script("check_hldspec_promotion_gate.py", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        report = self.read_gate_report(target)
        self.assertEqual("PASS", report["status"])
        self.assertIn(".hldspec/promoted_capabilities.json", report["inputs_read"])

    def test_promoted_capability_missing_runskeptic_status_blocks_promotion(self) -> None:
        target = self.make_target()
        self.write_promoted_capabilities(target, [{"name": "validator framework"}])

        result = self.run_script("check_hldspec_promotion_gate.py", target)

        self.assertEqual(2, result.returncode)
        report = self.read_gate_report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any(item["check"] == "runskeptic_status" for item in report["findings"]))

    def test_promoted_capability_runskeptic_action_blocks_promotion(self) -> None:
        target = self.make_target()
        self.write_promoted_capabilities(
            target,
            [
                {
                    "name": "validator framework",
                    "runskeptic_status": "ACTION",
                    "runskeptic_evidence": ["RunSkeptic found fixable validator gaps."],
                }
            ],
        )

        result = self.run_script("check_hldspec_promotion_gate.py", target)

        self.assertEqual(2, result.returncode)
        report = self.read_gate_report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any("unresolved RunSkeptic ACTION" in item["message"] for item in report["findings"]))

    def test_promoted_capability_runskeptic_conflict_blocks_promotion(self) -> None:
        target = self.make_target()
        self.write_promoted_capabilities(
            target,
            [
                {
                    "name": "promotion gate",
                    "runskeptic_status": "CONFLICT",
                    "runskeptic_evidence": ["RunSkeptic found unresolved ownership conflict."],
                }
            ],
        )

        result = self.run_script("check_hldspec_promotion_gate.py", target)

        self.assertEqual(2, result.returncode)
        report = self.read_gate_report(target)
        self.assertEqual("CONFLICT", report["status"])
        self.assertTrue(any(item["check"] == "runskeptic_status" for item in report["findings"]))

    def test_promoted_capability_runskeptic_pass_without_evidence_blocks_promotion(self) -> None:
        target = self.make_target()
        self.write_promoted_capabilities(
            target,
            [{"name": "promotion gate", "runskeptic_status": "PASS"}],
        )

        result = self.run_script("check_hldspec_promotion_gate.py", target)

        self.assertEqual(2, result.returncode)
        report = self.read_gate_report(target)
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any(item["check"] == "runskeptic_evidence" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
