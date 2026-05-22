from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hldspec_v2_answer_conversion_queue.py"


class AnswerConversionQueueTests(unittest.TestCase):
    def make_queue(self) -> Path:
        path = Path(tempfile.mkdtemp()) / "hld_conversion_decision_queue.json"
        path.write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "Q-001",
                            "human_decision": "TBD",
                            "blocking": True,
                        },
                        {
                            "question_id": "Q-003",
                            "human_decision": "TBD",
                            "blocking": True,
                        },
                    ]
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_updates_answers_and_keep_reason(self) -> None:
        queue = self.make_queue()
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(queue),
                "--answer",
                "Q-001=SPLIT_AS_PROPOSED",
                "--answer",
                "Q-003=KEEP_AS_ONE",
                "--keep-reason",
                "Q-003=Milestones are planning context.",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr + result.stdout)
        data = json.loads(queue.read_text(encoding="utf-8"))
        by_id = {q["question_id"]: q for q in data["questions"]}
        self.assertEqual("SPLIT_AS_PROPOSED", by_id["Q-001"]["human_decision"])
        self.assertEqual("KEEP_AS_ONE", by_id["Q-003"]["human_decision"])
        self.assertEqual("Milestones are planning context.", by_id["Q-003"]["approved_keep_reason"])

    def test_keep_as_one_requires_reason(self) -> None:
        queue = self.make_queue()
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                str(queue),
                "--answer",
                "Q-003=KEEP_AS_ONE",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(2, result.returncode)
        self.assertIn("KEEP_AS_ONE requires", result.stdout)


if __name__ == "__main__":
    unittest.main()
