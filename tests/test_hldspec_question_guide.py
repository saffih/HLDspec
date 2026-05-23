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


guide_mod = load_module("build_hldspec_question_guide", "scripts/build_hldspec_question_guide.py")
answers_mod = load_module("apply_hldspec_queue_answers", "scripts/apply_hldspec_queue_answers.py")


class HldspecQuestionGuideTest(unittest.TestCase):
    def test_conversion_queue_guide_explains_open_question(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            queue = sync / "hld_conversion_decision_queue.json"
            queue.write_text(
                json.dumps(
                    {
                        "status": "HUMAN_CHECKPOINT_REQUIRED",
                        "checkpoint": {"checkpoint_id": "hld_conversion_decisions", "open_question_count": 1},
                        "questions": [
                            {
                                "question_id": "Q-001",
                                "title": "Split large context section",
                                "question": "Split or keep?",
                                "options": ["SPLIT_AS_PROPOSED", "KEEP_AS_ONE"],
                                "human_decision": "TBD",
                                "blocking": True,
                                "section_title": "Large Architecture Section",
                                "default_proposal": {
                                    "proposed_split_plan": [
                                        {"title": "Part A"},
                                        {"title": "Part B"},
                                    ]
                                },
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (sync / "hldspec_state.json").write_text(
                json.dumps(
                    {
                        "current_stage": "CONVERSION_CHECKPOINT",
                        "current_checkpoint": "hld_conversion_decisions",
                        "controlling_artifacts": [str(queue)],
                    }
                ),
                encoding="utf-8",
            )
            guide = guide_mod.build_guide(workspace)
            self.assertEqual(guide["status"], "HUMAN_GUIDANCE_REQUIRED")
            self.assertEqual(guide["open_question_count"], 1)
            self.assertEqual(guide["questions"][0]["recommended_option"], "SPLIT_AS_PROPOSED")
            self.assertIn("--answer Q-001=", guide["questions"][0]["answer_command_template"])

    def test_no_active_questions_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            (sync / "hldspec_state.json").write_text(
                json.dumps({"current_stage": "SPECKIT_PREWORK_APPROVAL_GATE"}),
                encoding="utf-8",
            )
            guide = guide_mod.build_guide(workspace)
            self.assertEqual(guide["status"], "NO_ACTIVE_QUESTIONS")
            self.assertEqual(guide["questions"], [])

    def test_speckit_escalation_queue_is_guided_and_answerable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            queue = sync / "speckit_question_escalation_queue.json"
            queue.write_text(
                json.dumps(
                    {
                        "status": "HUMAN_QUESTIONS_REQUIRED",
                        "questions": [
                            {
                                "question_id": "PMQ-001",
                                "owner_role": "Product Manager",
                                "phase": "specify",
                                "classification": "ESCALATE_TO_HUMAN",
                                "question": "Who owns the user-visible scope?",
                                "human_decision": "TBD",
                                "blocking": True,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (sync / "hldspec_state.json").write_text(
                json.dumps(
                    {
                        "current_stage": "ANSWER_PACK_REVIEW",
                        "current_checkpoint": "speckit_question_escalation",
                        "controlling_artifacts": [str(queue)],
                    }
                ),
                encoding="utf-8",
            )
            guide = guide_mod.build_guide(workspace)
            self.assertEqual(guide["queue_kind"], "speckit_question_escalation")
            self.assertEqual(guide["questions"][0]["options"], ["ANSWERED", "NEEDS_REWORK", "DEFER"])

            discovered = answers_mod.discover_queue(workspace)
            self.assertEqual(discovered.resolve(), queue.resolve())


if __name__ == "__main__":
    unittest.main()
