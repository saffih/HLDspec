from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldSourceUpdateQueueTests(unittest.TestCase):
    def test_source_update_queue_detects_hld_affecting_answer(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "work"
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            queue = {
                "questions": [
                    {
                        "question_id": "Q-001",
                        "source_candidate_id": "HLD-009",
                        "title": "Component Deep-Dive",
                        "question": "Split or keep?",
                        "human_decision": "MODIFY_SPLIT",
                        "human_notes": "Merge Overview into the first interface section.",
                        "approved_split_plan": [
                            {
                                "proposed_hld_id": "HLD-010A",
                                "title": "Database API Interface",
                                "source_line_start": 2431,
                                "source_line_end": 2558,
                            }
                        ],
                    }
                ]
            }
            (sync / "hld_conversion_decision_queue.json").write_text(json.dumps(queue), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "write_hld_source_update_queue.py"),
                    str(workspace),
                    "--source-hld",
                    "Flow-System-HLD.md",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((sync / "hld_source_update_queue.json").read_text(encoding="utf-8"))
            self.assertEqual("SOURCE_HLD_REVIEW_REQUIRED", data["status"])
            self.assertEqual(1, len(data["updates"]))
            self.assertEqual("MAY_AFFECT_SOURCE_HLD", data["updates"][0]["source_hld_impact"])
            self.assertIn("Merge Overview", data["updates"][0]["proposed_source_update"])
            report = (sync / "hld_source_update_queue.md").read_text(encoding="utf-8")
            self.assertIn("explicit approval", report)


if __name__ == "__main__":
    unittest.main()
