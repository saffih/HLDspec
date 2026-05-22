from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "scripts" / "render_hldspec_checkpoint.py"


class RenderHldspecCheckpointTests(unittest.TestCase):
    def run_renderer(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(RENDERER), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

    def test_conversion_checkpoint_shows_only_open_questions_as_active(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            queue = Path(td) / "queue.json"
            queue.write_text(
                json.dumps(
                    {
                        "checkpoint": {"checkpoint_id": "HLD_CONVERSION_DECISIONS", "allowed_to_convert": False},
                        "questions": [
                            {
                                "question_id": "Q-001",
                                "source_candidate_id": "HLD-009",
                                "title": "Answered",
                                "question": "Answered question?",
                                "options": ["KEEP_AS_ONE", "SPLIT_AS_PROPOSED"],
                                "human_decision": "SPLIT_AS_PROPOSED",
                                "blocking": True,
                            },
                            {
                                "question_id": "Q-002",
                                "source_candidate_id": "HLD-019",
                                "title": "Milestones",
                                "question": "Keep or split?",
                                "options": ["KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"],
                                "human_decision": "TBD",
                                "blocking": True,
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_renderer(
                [
                    "--checkpoint",
                    "HLD_CONVERSION_DECISIONS",
                    "--queue",
                    str(queue),
                    "--workspace",
                    td,
                    "--source-hld",
                    "./Flow-System-HLD.md",
                    "--runner",
                    "~/code/HLDspec/scripts/hldspec_run.sh",
                ]
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            out = result.stdout
            self.assertIn("Current checkpoint: HLD_CONVERSION_DECISIONS", out)
            self.assertIn("Open blocking questions: 1", out)
            self.assertIn("Human decision needed:", out)
            self.assertIn("Q-002 HLD-019 - Milestones", out)
            self.assertIn("Already answered decisions:", out)
            self.assertIn("- Q-001 HLD-009 -> SPLIT_AS_PROPOSED", out)
            self.assertIn("Continuation protocol:", out)
            self.assertIn("The source HLD is not modified by this checkpoint.", out)
            self.assertIn("Do not answer generic OK/continue.", out)

    def test_speckit_approval_preserves_safety_phrases(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = self.run_renderer(
                [
                    "--checkpoint",
                    "SPECKIT_PREWORK_APPROVAL_GATE",
                    "--workspace",
                    td,
                ]
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            out = result.stdout
            self.assertIn("SpecKit prework approval gate", out)
            self.assertIn("Human decision needed:", out)
            self.assertIn("Do not write specs manually from HLDspec", out)
            self.assertIn("Do not invoke SpecKit until the human approves this gate", out)

    def test_spec_build_plan_checkpoint_has_standard_sections(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            plan = root / "plan.json"
            review = root / "review.md"
            plan.write_text(
                json.dumps(
                    {
                        "plan_quality": {
                            "decision": "DECOMPOSE",
                            "recommendation": "SPLIT_PLANNED_SPEC",
                            "conflicts": [],
                        },
                        "planned_specs": [
                            {"planned_spec_id": "spec-1", "quality_flags": ["mixed_responsibilities"]}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            review.write_text("Continue to target-spec generation: `false`", encoding="utf-8")

            result = self.run_renderer(
                [
                    "--checkpoint",
                    "SPEC_BUILD_PLAN_CHECKPOINT",
                    "--plan",
                    str(plan),
                    "--review",
                    str(review),
                    "--workspace",
                    td,
                ]
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            out = result.stdout
            self.assertIn("Current checkpoint: SPEC_BUILD_PLAN_CHECKPOINT", out)
            self.assertIn("Blocking reason:", out)
            self.assertIn("Human decision needed:", out)
            self.assertIn("Controlling artifacts:", out)
            self.assertIn("SpecKit is not invoked at this checkpoint.", out)


if __name__ == "__main__":
    unittest.main()
