from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FirstRunReviewTests(unittest.TestCase):
    def test_review_spec_build_plan_writes_actionable_report(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            plan_path = workspace / "spec_build_plan.json"
            plan_path.write_text(
                json.dumps(
                    {
                        "plan_quality": {
                            "decision": "DECOMPOSE",
                            "recommendation": "SPLIT_PLANNED_SPEC",
                            "findings": ["002: mixed_layers"],
                            "conflicts": [],
                            "beskeptic_cycles": [],
                        },
                        "planned_specs": [
                            {
                                "planned_spec_id": "002",
                                "title": "API and Processing",
                                "layer": "api",
                                "source_hld_sections": ["HLD-002", "HLD-003"],
                                "depends_on_specs": ["001"],
                                "quality_flags": [
                                    "mixed_layers",
                                    "api_processing_boundary_needs_review",
                                ],
                                "boundary_risk": "high",
                                "requires_user_review": True,
                            }
                        ],
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "review_spec_build_plan.py"),
                    str(plan_path),
                ],
                cwd=workspace,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            review_path = workspace / "spec_build_plan_review.md"
            self.assertTrue(review_path.exists())
            review = review_path.read_text(encoding="utf-8")
            self.assertIn("Spec Build Plan Review", review)
            self.assertIn("Continue to target-spec generation: `false`", review)
            self.assertIn("Should planned spec 002 be split", review)

    def test_first_run_detects_raw_hld_and_writes_conversion_prompt(self) -> None:
        raw_hld = """# Raw HLD

## Architecture

The system has a producer and a consumer.

## Data Model

The system stores state.
"""
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
            self.assertTrue((workspace / "hld_readiness.json").exists())
            self.assertTrue((workspace / "HLD_CONVERSION_PROMPT.md").exists())
            self.assertFalse((workspace / ".specify" / "sync" / "spec_build_plan.json").exists())

            readiness = json.loads((workspace / "hld_readiness.json").read_text(encoding="utf-8"))
            self.assertEqual("needs_conversion", readiness["status"])
            self.assertEqual(0, readiness["existing_hldspec_section_count"])
            self.assertGreaterEqual(readiness["candidate_major_section_count"], 2)


if __name__ == "__main__":
    unittest.main()
