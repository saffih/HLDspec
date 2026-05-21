from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldConversionDecisionQueueTests(unittest.TestCase):
    def test_decision_queue_blocks_stop_split_and_single_section_review(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "workspace"
            workspace.mkdir()
            sync_dir = workspace / ".specify" / "sync"
            sync_dir.mkdir(parents=True)
            plan = {
                "status": "STOP_SPLIT_DECISION_REQUIRED",
                "candidates": [
                    {
                        "proposed_hld_id": "HLD-009",
                        "title": "Component Deep-Dive",
                        "source_line_start": 749,
                        "source_line_end": 2428,
                        "source_line_count": 1680,
                        "recommended_action": "STOP_SPLIT_DECISION_REQUIRED",
                        "reason": "large section",
                        "proposed_split_plan": [
                            {"proposed_hld_id": "HLD-009A", "title": "TEA", "source_line_start": 751, "source_line_end": 781},
                            {"proposed_hld_id": "HLD-009B", "title": "API", "source_line_start": 782, "source_line_end": 799},
                        ],
                    },
                    {
                        "proposed_hld_id": "HLD-019",
                        "title": "Milestones",
                        "source_line_start": 3836,
                        "source_line_end": 4274,
                        "source_line_count": 439,
                        "recommended_action": "PROCEED_SINGLE_SECTION_REVIEW",
                        "reason": "large but cohesive",
                        "proposed_split_plan": [],
                    },
                ],
            }
            plan_path = sync_dir / "hld_conversion_plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_hld_conversion_decision_queue.py"),
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
            queue = json.loads((sync_dir / "hld_conversion_decision_queue.json").read_text(encoding="utf-8"))
            self.assertEqual("HUMAN_CHECKPOINT_REQUIRED", queue["status"])
            self.assertFalse(queue["checkpoint"]["allowed_to_convert"])
            self.assertEqual(2, queue["checkpoint"]["open_question_count"])
            self.assertEqual("TBD", queue["questions"][0]["human_decision"])
            self.assertIn("SPLIT_AS_PROPOSED", queue["questions"][0]["options"])
            self.assertIn("KEEP_AS_ONE", queue["questions"][1]["options"])
            report = (sync_dir / "hld_conversion_decision_queue.md").read_text(encoding="utf-8")
            self.assertIn("The judge/orchestrator owns this checkpoint", report)
            self.assertIn("Conversion is blocked", report)

    def test_first_run_raw_hld_writes_decision_queue(self) -> None:
        raw_hld = "# Raw HLD\n\n## Large Section\n\n" + "\n".join(f"line {i}" for i in range(450)) + "\n"
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
            self.assertTrue((workspace / ".specify" / "sync" / "hld_conversion_decision_queue.json").exists())
            self.assertTrue((workspace / ".specify" / "sync" / "hld_conversion_decision_queue.md").exists())
            prompt = (workspace / "HLD_CONVERSION_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("hld_conversion_decision_queue.md", prompt)


if __name__ == "__main__":
    unittest.main()
