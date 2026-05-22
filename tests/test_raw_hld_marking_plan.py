from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RAW_HLD = """# Demo Raw HLD

## Product Goals

Users need a dashboard journey with acceptance criteria and stakeholder goals.

## API and Processing

The HTTP API endpoint accepts a request and response contract.
The workflow processes validation steps and runtime decisions.

## Data State

The database schema stores user state.
This is the source of truth for persistence.

## Governance

Architecture constraints and assumptions belong in the constitution.
"""


class RawHldMarkingPlanTests(unittest.TestCase):
    def test_builds_raw_hld_marking_plan_with_bounded_perspectives(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            source = work / "raw.md"
            source.write_text(RAW_HLD, encoding="utf-8")

            conversion_plan = {
                "candidates": [
                    {
                        "proposed_hld_id": "HLD-001",
                        "title": "Product Goals",
                        "source_line_start": 3,
                        "source_line_end": 5,
                        "recommended_action": "PROCEED_METADATA_ONLY",
                    },
                    {
                        "proposed_hld_id": "HLD-002",
                        "title": "API and Processing",
                        "source_line_start": 7,
                        "source_line_end": 10,
                        "recommended_action": "PROCEED_METADATA_ONLY",
                    },
                    {
                        "proposed_hld_id": "HLD-003",
                        "title": "Data State",
                        "source_line_start": 12,
                        "source_line_end": 15,
                        "recommended_action": "PROCEED_METADATA_ONLY",
                    },
                    {
                        "proposed_hld_id": "HLD-004",
                        "title": "Governance",
                        "source_line_start": 17,
                        "source_line_end": 18,
                        "recommended_action": "PROCEED_METADATA_ONLY",
                    },
                ]
            }
            plan_path = work / "conversion_plan.json"
            plan_path.write_text(json.dumps(conversion_plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_raw_hld_marking_plan.py"),
                    str(plan_path),
                    str(work),
                    "--source-hld",
                    str(source),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((work / ".specify" / "sync" / "raw_hld_marking_plan.json").read_text(encoding="utf-8"))

            self.assertEqual("RAW_HLD_MARKING_REQUIRED", data["status"])
            self.assertEqual(4, len(data["items"]))

            by_id = {item["candidate_id"]: item for item in data["items"]}
            self.assertEqual("product_context", by_id["HLD-001"]["primary_role"])
            self.assertIn("interface_contract", by_id["HLD-002"]["suggested_roles"])
            self.assertIn("processing_behavior", by_id["HLD-002"]["suggested_roles"])
            self.assertIn("data_model", by_id["HLD-003"]["suggested_roles"])
            self.assertIn("governance_context", by_id["HLD-004"]["suggested_roles"])

            self.assertIn("product_reviewer", by_id["HLD-001"]["subagents"])
            self.assertIn("architecture_reviewer", data["subagent_contract"]["bounded_subagents"])
            self.assertTrue((work / ".specify" / "sync" / "raw_hld_marking_plan.md").exists())
            self.assertTrue((work / "RAW_HLD_MARKING_PROMPT.md").exists())

    def test_first_run_wires_raw_hld_marking_plan_into_conversion_checkpoint(self) -> None:
        text = (ROOT / "scripts" / "first_run_readonly.sh").read_text(encoding="utf-8")

        self.assertIn("build_raw_hld_marking_plan.py", text)
        self.assertIn("raw_hld_marking_plan.md", text)
        self.assertIn("raw_hld_marking_plan.json", text)
        self.assertIn("RAW_HLD_MARKING_PROMPT.md", text)


if __name__ == "__main__":
    unittest.main()
