from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecReadyGateContractTests(unittest.TestCase):
    def test_ready_gate_script_exists_and_has_no_paid_agent_invocation(self) -> None:
        path = ROOT / "scripts" / "hldspec_ready_gate.py"
        self.assertTrue(path.exists())
        text = path.read_text(encoding="utf-8")

        self.assertIn("READY_FOR_PAID_AGENT_TEST", text)
        self.assertIn("full_unittest_discovery", text)
        self.assertIn("test_raw_hld_marking_plan", text)
        self.assertIn("test_spec_build_plan_quality_gate_fixtures", text)

        forbidden_direct_commands = [
            " codex ",
            " devin ",
            " claude ",
            "specify run",
            "specify implement",
        ]
        lowered = text.lower()
        for term in forbidden_direct_commands:
            self.assertNotIn(term, lowered)

    def test_ready_gate_can_report_missing_files_without_running_paid_agents(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "hldspec_ready_gate.py"),
                    "--repo",
                    str(ROOT),
                    "--output-dir",
                    str(out),
                    "--structure-only",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertIn(result.returncode, {0, 2})
            report = out / "hldspec_ready_gate.json"
            self.assertTrue(report.exists())

            data = json.loads(report.read_text(encoding="utf-8"))
            self.assertIn(data["status"], {"READY_FOR_PAID_AGENT_TEST", "NOT_READY"})
            self.assertIn("checks", data)
            self.assertTrue(any(item["name"] == "required_files" for item in data["checks"]))

    def test_ready_gate_doc_exists(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_READY_GATE.md").read_text(encoding="utf-8")
        self.assertIn("READY_FOR_PAID_AGENT_TEST", text)
        self.assertIn("Do not spend paid agent/SpecKit credits", text)


if __name__ == "__main__":
    unittest.main()
