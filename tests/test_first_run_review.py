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
            prompt = (workspace / "HLD_CONVERSION_PROMPT.md").read_text(encoding="utf-8")
            self.assertIn("Do not paste the whole HLD into agent context", prompt)
            self.assertIn("Convert in bounded batches of 3-5 major sections", prompt)
            self.assertIn("grep", prompt)
            self.assertFalse((workspace / ".specify" / "sync" / "spec_build_plan.json").exists())

            readiness = json.loads((workspace / "hld_readiness.json").read_text(encoding="utf-8"))
            self.assertEqual("needs_conversion", readiness["status"])
            self.assertEqual(0, readiness["existing_hldspec_section_count"])
            self.assertGreaterEqual(readiness["candidate_major_section_count"], 2)

    def test_limited_agent_run_card_contains_required_stop_points(self) -> None:
        card = (ROOT / "docs" / "LIMITED_AGENT_RUN_CARD.md").read_text(encoding="utf-8")
        self.assertIn("Do not load or paste the whole HLD", card)
        self.assertIn("first_run_readonly.sh", card)
        self.assertIn("3-5 major sections", card)
        self.assertIn("Stop for human decision", card)
        self.assertIn("DECOMPOSE", card)
        self.assertIn("CONFLICT", card)

    def test_chunked_agent_protocol_contains_judge_subagent_rules(self) -> None:
        protocol = (ROOT / "docs" / "CHUNKED_AGENT_PROTOCOL.md").read_text(encoding="utf-8")
        card = (ROOT / "docs" / "LIMITED_AGENT_RUN_CARD.md").read_text(encoding="utf-8")
        self.assertIn("judge/orchestrator", protocol)
        self.assertIn("bounded workers", protocol)
        self.assertIn("Human", protocol)
        self.assertIn("Normal chunk: 1 major HLD section", card)
        self.assertIn("Subagent brief template", card)
        self.assertIn("Subagent output template", card)
        self.assertIn("human owns unresolved decisions", protocol.lower())

    def test_agents_raw_hld_flow_uses_first_run_not_default_target_hld(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        raw_section = agents.split("## Existing huge HLD or raw HLD not in HLDspec format", 1)[1]
        raw_section = raw_section.split("## HLDspec operating rules vs target Spec Kit Constitution", 1)[0]
        self.assertIn("Rerun the current primary first-run workflow", raw_section)
        self.assertIn("spec_build_plan_review.md", raw_section)
        self.assertIn("Use legacy `--target-hld` only when explicitly requested", raw_section)
        self.assertIn("Do not create downstream artifacts from raw-HLD assumptions", raw_section)
        self.assertNotIn("Sync one target section at a time", raw_section)
        self.assertNotIn("Continue downstream only after the related spec exists", raw_section)

    def test_downstream_analysis_boundary_is_documented(self) -> None:
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        card = (ROOT / "docs" / "LIMITED_AGENT_RUN_CARD.md").read_text(encoding="utf-8")
        protocol = (ROOT / "docs" / "CHUNKED_AGENT_PROTOCOL.md").read_text(encoding="utf-8")

        for text in (agents, readme, card, protocol):
            self.assertIn("downstream_analysis.md", text)
            self.assertRegex(text, r"not (a first-run artifact|part of the first-run workflow)")
            self.assertIn("raw-HLD assumptions", text)

        self.assertIn("Safe default for limited agents and large/raw HLDs", readme)
        self.assertIn("Do **not** start with full sync", readme)
        self.assertLess(readme.index("Safe default for limited agents and large/raw HLDs"), readme.index("## Sync script"))
        self.assertIn("Downstream-analysis subagent", agents)
        self.assertIn("--use-hld-map --target-hld", card)


if __name__ == "__main__":
    unittest.main()
