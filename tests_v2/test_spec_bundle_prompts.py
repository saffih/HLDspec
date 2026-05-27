from __future__ import annotations

import unittest
from pathlib import Path

from hldspec.spec_bundle_prompts import RUNTIMES, render_bundle_prompt, validate_prompt_text


class SpecBundlePromptTests(unittest.TestCase):
    def make_bundle(self) -> dict:
        return {
            "bundle_id": "G01",
            "bundle_name": "API Bundle 01",
            "bundle_slug": "g01-api-bundle-01",
            "included_specs": [
                {
                    "feature_id": "F1",
                    "feature_name": "API foundation",
                    "layer": "api",
                    "theme": "api",
                    "depends_on_features": [],
                    "speckit_specify_input": "Build API foundation.",
                }
            ],
            "why_grouped": "Single spec bundle.",
            "dependency_position": 1,
            "dependencies": [],
            "allowed_evidence": [".specify/sync/speckit_invocation_queue.json"],
            "forbidden_reads": ["Do not read outside allowed evidence."],
            "model_runtime_recommendation": {
                "orchestrator": "MODEL_CRITICAL",
                "default_subagent": "MODEL_STRONG",
                "clarification": "MODEL_DEFAULT",
            },
            "expected_outputs": ["outputs"],
            "tests_required": ["tests"],
            "runskeptic_checkpoints": ["post-specify", "post-plan", "post-tasks"],
            "human_checkpoint_rules": ["stop on unresolved ACTION or CONFLICT"],
            "stop_condition": "Stop at checkpoint.",
            "implementation_allowed": False,
            "prompt_paths": {},
        }

    def test_all_runtime_prompts_have_required_sections(self) -> None:
        bundle = self.make_bundle()
        for runtime in RUNTIMES:
            with self.subTest(runtime=runtime):
                text = render_bundle_prompt(bundle, workspace=Path("/tmp/work"), sync=Path("/tmp/work/.specify/sync"), runtime=runtime)
                self.assertEqual([], validate_prompt_text(text))
                self.assertIn("Specify", text)
                self.assertIn("Clarify", text)
                self.assertIn("Plan", text)
                self.assertIn("Research/data/contracts", text)
                self.assertIn("Tasks", text)
                self.assertIn("Implementation", text)
                self.assertIn("Verification", text)
                self.assertIn("RunSkeptic", text)
                self.assertIn("## Clarification Policy", text)
                self.assertIn("resolve them from approved evidence first", text)
                self.assertIn("approved evidence is missing", text)
                self.assertIn("approved evidence is contradictory", text)
                self.assertIn("human-owned", text)
                self.assertIn("PASS", text)
                self.assertIn("ACTION", text)
                self.assertIn("CONFLICT", text)
                self.assertIn("## How to run RunSkeptic", text)
                self.assertIn("~/code/skeptic/skeptic.md", text)
                self.assertIn("GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN", text)
                self.assertIn("OBSERVED", text)
                self.assertIn("REPRODUCED", text)
                self.assertIn("HISTORICAL", text)
                self.assertIn("INFERRED RISK", text)
                self.assertIn("RunSkeptic status:", text)
                self.assertIn("Next safe action:", text)
                self.assertNotIn("BLOCKER", text)
                # One-go / answer-finding / gap-map self-sufficiency contract
                self.assertIn("## One-Go Execution Policy", text)
                self.assertIn("## Answer-Finding Protocol", text)
                self.assertIn("## HLD Section Gap Map", text)
                self.assertIn("Do as much as safely possible in one run", text)
                self.assertIn("Do not stop just because SpecKit asks a question", text)
                self.assertIn("Resolve clarification questions from approved evidence first", text)
                self.assertIn("active HLD sections", text)
                self.assertIn("Feature purpose", text)
                self.assertIn("Architecture boundary", text)
                self.assertIn("Source of truth", text)
                self.assertIn("Dependency order", text)
                self.assertIn("human-owned decision", text)
                self.assertIn("## Reassessment Request", text)
                # Each major policy section must appear exactly once (no drift/dupes).
                for section in (
                    "## One-Go Execution Policy",
                    "## Answer-Finding Protocol",
                    "## HLD Section Gap Map",
                    "## Clarification Policy",
                    "## How to run RunSkeptic",
                    "## Reassessment Request",
                ):
                    self.assertEqual(1, text.count(section), f"{section} must appear exactly once")

    def test_unknown_runtime_fails(self) -> None:
        with self.assertRaises(ValueError):
            render_bundle_prompt(self.make_bundle(), workspace=Path("/tmp/work"), sync=Path("/tmp/work/.specify/sync"), runtime="unknown")

    def test_prompt_explains_clarification_policy(self) -> None:
        text = render_bundle_prompt(
            self.make_bundle(),
            workspace=Path("/tmp/work"),
            sync=Path("/tmp/work/.hldspec/sync"),
            runtime="claude",
        )
        self.assertEqual([], validate_prompt_text(text))
        self.assertIn("## Clarification Policy", text)
        self.assertIn("Clarification questions are not blockers by default.", text)
        self.assertIn("approved HLDspec evidence", text)
        self.assertIn("missing, contradictory, or the answer is human-owned", text)
        self.assertIn("Stop on RunSkeptic ACTION or CONFLICT", text)


if __name__ == "__main__":
    unittest.main()
