from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldConversionPlanTests(unittest.TestCase):
    def test_conversion_plan_uses_approx_lines_for_large_section_detection(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            workspace.mkdir()
            report = {
                "headings": [
                    {"line": 1, "level": 1, "title": "Raw"},
                    {"line": 2, "level": 2, "title": "Component Deep-Dive"},
                    {"line": 20, "level": 3, "title": "Subcomponent A"},
                    {"line": 100, "level": 3, "title": "Subcomponent B"},
                    {"line": 1682, "level": 2, "title": "Next Section"},
                ],
                "suggested_hld_sections": [
                    {
                        "suggested_id": "HLD-001",
                        "line": 2,
                        "heading_level": 2,
                        "title": "Component Deep-Dive",
                        "role": "architecture",
                        "risk": "MEDIUM",
                        "approx_lines_until_next_candidate": 1680,
                        "metadata_skeleton": {
                            "HLD-ID": "HLD-001",
                            "HLD-ROLE": "architecture",
                            "HLD-STATUS": "active",
                            "HLD-RISK": "MEDIUM",
                            "HLD-SPECS": "TBD",
                            "HLD-RESOURCES": "TBD",
                            "HLD-VERIFY": "section can be processed without loading the full HLD",
                        },
                    },
                    {
                        "suggested_id": "HLD-002",
                        "line": 1682,
                        "heading_level": 2,
                        "title": "Next Section",
                        "role": "processing",
                        "risk": "MEDIUM",
                        "approx_lines_until_next_candidate": 12,
                    },
                ],
            }
            report_path = workspace / "suggested_hld_sections.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_hld_conversion_plan.py"),
                    str(report_path),
                    str(workspace),
                    "--source-hld",
                    "raw.md",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            plan_path = workspace / ".specify" / "sync" / "hld_conversion_plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            self.assertEqual("STOP_SPLIT_DECISION_REQUIRED", plan["status"])
            self.assertEqual(1, plan["large_candidate_section_count"])
            self.assertTrue(plan["candidates"][0]["large_section"])
            self.assertEqual("STOP_SPLIT_DECISION_REQUIRED", plan["candidates"][0]["recommended_action"])
            self.assertGreaterEqual(len(plan["candidates"][0]["split_candidate_headings"]), 2)

    def test_first_run_raw_hld_writes_conversion_plan(self) -> None:
        raw_hld = "# Raw HLD\n\n## Architecture\n\nBody.\n\n## Data Model\n\nBody.\n"
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            source = Path(td) / "raw.md"
            source.write_text(raw_hld, encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "first_run_readonly.sh"),
                    str(source),
                    str(workspace),
                    "--force",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertTrue((workspace / ".specify" / "sync" / "hld_conversion_plan.json").exists())
            self.assertTrue((workspace / ".specify" / "sync" / "hld_conversion_plan.md").exists())
            prompt = (workspace / "HLD_CONVERSION_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("hld_conversion_plan.md", prompt)
            readiness = json.loads((workspace / "hld_readiness.json").read_text(encoding="utf-8"))
            self.assertIn("conversion_plan_json", readiness)
            self.assertIn("conversion_plan_md", readiness)


if __name__ == "__main__":
    unittest.main()
