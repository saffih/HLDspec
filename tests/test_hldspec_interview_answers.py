from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


answers = load_module("apply_hldspec_queue_answers", "scripts/apply_hldspec_queue_answers.py")


class HldspecInterviewAnswersTest(unittest.TestCase):
    def conversion_queue(self) -> dict:
        return {
            "status": "HUMAN_CHECKPOINT_REQUIRED",
            "checkpoint": {
                "checkpoint_id": "HLD_CONVERSION_DECISIONS",
                "open_question_count": 1,
                "allowed_to_convert": False,
            },
            "questions": [
                {
                    "question_id": "Q-001",
                    "source_candidate_id": "HLD-001",
                    "title": "Large Architecture Section",
                    "question": "Split or keep?",
                    "options": ["SPLIT_AS_PROPOSED", "MODIFY_SPLIT", "KEEP_AS_ONE"],
                    "human_decision": "TBD",
                    "human_notes": "",
                    "blocking": True,
                    "default_proposal": {
                        "proposed_split_plan": [
                            {"proposed_hld_id": "HLD-001A", "title": "API"},
                            {"proposed_hld_id": "HLD-001B", "title": "Processing"},
                        ]
                    },
                }
            ],
        }

    def test_valid_answer_updates_queue(self) -> None:
        queue = self.conversion_queue()
        updated = answers.apply_answers_to_queue(
            queue,
            {"Q-001": "SPLIT_AS_PROPOSED"},
            {"Q-001": "Use proposed split."},
        )
        question = updated["questions"][0]
        self.assertEqual(question["human_decision"], "SPLIT_AS_PROPOSED")
        self.assertEqual(question["decision_status"], "ANSWERED")
        self.assertEqual(question["human_notes"], "Use proposed split.")
        self.assertEqual(updated["checkpoint"]["open_question_count"], 0)
        self.assertTrue(updated["checkpoint"]["allowed_to_convert"])
        self.assertEqual(updated["status"], "DECISIONS_RECORDED")
        self.assertEqual(len(question["approved_split_plan"]), 2)

    def test_invalid_question_id_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            answers.apply_answers_to_queue(self.conversion_queue(), {"Q-999": "KEEP_AS_ONE"})

    def test_invalid_option_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            answers.apply_answers_to_queue(self.conversion_queue(), {"Q-001": "BAD_OPTION"})

    def test_cli_writes_source_update_queue_for_conversion_answers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            queue_path = sync / "hld_conversion_decision_queue.json"
            queue_path.write_text(json.dumps(self.conversion_queue()), encoding="utf-8")

            rc = answers.main_args_for_test if False else None
            # Exercise the same public helpers used by the CLI, without spawning a subprocess.
            queue = answers.load_json(queue_path)
            updated = answers.apply_answers_to_queue(queue, {"Q-001": "KEEP_AS_ONE"}, {"Q-001": "Keep as one for now."})
            answers.write_json(queue_path, updated)
            answers.maybe_run_supporting_writers(queue_path, workspace, "source-HLD.md")

            source_queue = sync / "hld_source_update_queue.json"
            self.assertTrue(source_queue.exists())
            data = json.loads(source_queue.read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "SOURCE_HLD_REVIEW_REQUIRED")
            self.assertEqual(len(data["updates"]), 1)


if __name__ == "__main__":
    unittest.main()
