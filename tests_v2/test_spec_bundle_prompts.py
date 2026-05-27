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

    def test_unknown_runtime_fails(self) -> None:
        with self.assertRaises(ValueError):
            render_bundle_prompt(self.make_bundle(), workspace=Path("/tmp/work"), sync=Path("/tmp/work/.specify/sync"), runtime="unknown")


if __name__ == "__main__":
    unittest.main()
