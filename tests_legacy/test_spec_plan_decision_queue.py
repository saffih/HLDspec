from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class SpecBuildPlanDecisionQueueTests(unittest.TestCase):
    def test_generates_question_for_flagged_planned_spec(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            plan = {
                "plan_quality": {
                    "decision": "DECOMPOSE",
                    "recommendation": "SPLIT_PLANNED_SPEC",
                    "findings": ["018: api_processing_boundary_needs_review"],
                    "conflicts": [],
                },
                "planned_specs": [
                    {
                        "planned_spec_id": "018",
                        "title": "HTTP API Design and Endpoint Surface",
                        "source_hld_sections": ["HLD-020", "HLD-021"],
                        "quality_flags": ["api_processing_boundary_needs_review"],
                        "boundary_risk": "high",
                        "requires_user_review": True,
                        "responsibility_mix": ["api_contract", "processing"],
                    }
                ],
            }
            plan_path = sync / "spec_build_plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_spec_plan_decision_queue.py"),
                    str(plan_path),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            queue = json.loads((sync / "spec_build_plan_decision_queue.json").read_text(encoding="utf-8"))
            self.assertEqual("HUMAN_CHECKPOINT_REQUIRED", queue["status"])
            self.assertFalse(queue["checkpoint"]["allowed_to_generate_target_specs"])
            self.assertEqual(1, len(queue["questions"]))
            q = queue["questions"][0]
            self.assertEqual("018", q["planned_spec_id"])
            self.assertIn("SPLIT_PLANNED_SPEC", q["options"])
            self.assertEqual("TBD", q["human_decision"])
            report = (sync / "spec_build_plan_decision_queue.md").read_text(encoding="utf-8")
            self.assertIn("The judge/orchestrator may provide evidence", report)
            self.assertIn("must not answer", report)


if __name__ == "__main__":
    unittest.main()
