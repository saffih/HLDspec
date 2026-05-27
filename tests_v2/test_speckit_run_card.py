from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.speckit_run_card import (
    REQUIRED_JSON_FIELDS,
    REQUIRED_MD_SECTIONS,
    build_run_card_payload,
    render_run_card_md,
    validate_run_card_payload,
    write_run_cards,
)


class SpecKitRunCardTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        root = Path(tempfile.mkdtemp(prefix="hldspec-run-card-"))
        sync = root / ".hldspec" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_prework_approval.json").write_text(
            json.dumps({"status": "APPROVED", "approved_by": "test"}),
            encoding="utf-8",
        )
        (sync / "feature_dependency_graph.json").write_text(json.dumps({"nodes": ["G01"]}), encoding="utf-8")
        (sync / "speckit_invocation_queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (sync / "speckit_bundle_queue.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "bundles": [
                        {
                            "bundle_id": "G01",
                            "bundle_name": "API Bundle 01",
                            "bundle_slug": "g01-api-bundle-01",
                            "dependency_position": 1,
                            "dependencies": [],
                            "included_specs": [
                                {
                                    "feature_id": "F1",
                                    "feature_name": "API foundation",
                                    "speckit_specify_input": "Build API foundation.",
                                }
                            ],
                            "allowed_evidence": [
                                ".hldspec/sync/speckit_invocation_queue.json",
                                ".hldspec/sync/feature_dependency_graph.json",
                            ],
                            "runskeptic_checkpoints": ["before SpecKit starts", "after specify", "after plan"],
                            "expected_outputs": ["SpecKit specify/plan/tasks outputs", "RunSkeptic status"],
                            "tests_required": ["Run affected tests", "git diff --check"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_payload_has_required_contract_fields(self) -> None:
        payload = build_run_card_payload(
            {
                "bundle_id": "G01",
                "bundle_name": "API Bundle 01",
                "bundle_slug": "g01-api-bundle-01",
                "dependency_position": 1,
                "allowed_evidence": [".hldspec/sync/speckit_invocation_queue.json"],
            },
            workspace=Path("/tmp/target"),
            sync=Path("/tmp/target/.hldspec/sync"),
            approved=True,
        )
        missing = [field for field in REQUIRED_JSON_FIELDS if field not in payload]
        self.assertEqual([], missing)
        self.assertEqual([], validate_run_card_payload(payload))
        self.assertEqual("APPROVED", payload["status"])
        self.assertIn("RunSkeptic", " ".join(payload["runskeptic_checkpoints"]))

    def test_render_markdown_has_required_sections(self) -> None:
        payload = build_run_card_payload(
            {
                "bundle_id": "G01",
                "bundle_name": "API Bundle 01",
                "bundle_slug": "g01-api-bundle-01",
                "dependency_position": 1,
                "allowed_evidence": [".hldspec/sync/speckit_invocation_queue.json"],
            },
            workspace=Path("/tmp/target"),
            sync=Path("/tmp/target/.hldspec/sync"),
            approved=True,
        )
        text = render_run_card_md(payload)
        for section in REQUIRED_MD_SECTIONS:
            self.assertIn(section, text)
        self.assertIn("ANSWER_FROM_APPROVED_DEFAULT", text)
        self.assertIn("PASS", text)
        self.assertIn("ACTION", text)
        self.assertIn("CONFLICT", text)
        self.assertIn("## Clarification Policy", text)
        self.assertIn("Resolve clarification questions from approved evidence first", text)
        self.assertIn("approved evidence is missing", text)
        self.assertIn("approved evidence is contradictory", text)
        self.assertIn("human-owned", text)
        self.assertIn("## How to run RunSkeptic", text)
        self.assertIn("~/code/skeptic/skeptic.md", text)
        self.assertIn("GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN", text)
        self.assertIn("OBSERVED", text)
        self.assertIn("REPRODUCED", text)
        self.assertIn("HISTORICAL", text)
        self.assertIn("INFERRED RISK", text)
        self.assertIn("RunSkeptic status:", text)
        self.assertIn("Next safe action:", text)
        # One-go / answer-finding / gap-map self-sufficiency contract
        self.assertIn("## One-Go Execution Policy", text)
        self.assertIn("## Answer-Finding Protocol", text)
        self.assertIn("## HLD Section Gap Map", text)
        self.assertIn("Do as much as safely possible in one run", text)
        self.assertIn("Do not stop just because SpecKit asks a question", text)
        self.assertIn("Resolve clarification questions from approved evidence first", text)
        self.assertIn("resolve them from approved evidence first", text)
        self.assertIn("active HLD sections", text)
        self.assertIn("Feature purpose", text)
        self.assertIn("Architecture boundary", text)
        self.assertIn("Source of truth", text)
        self.assertIn("Dependency order", text)
        self.assertIn("human-owned decision", text)
        self.assertIn("## Reassessment Request", text)
        self.assertIn("GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN", text)
        self.assertIn("OBSERVED", text)
        self.assertIn("REPRODUCED", text)
        self.assertIn("HISTORICAL", text)
        self.assertIn("INFERRED RISK", text)
        self.assertIn("RunSkeptic status:", text)
        self.assertIn("Next safe action:", text)
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

    def test_write_run_cards_requires_approval_by_default(self) -> None:
        root = self.make_workspace()
        (root / ".hldspec" / "sync" / "speckit_prework_approval.json").write_text(
            json.dumps({"status": "PENDING"}),
            encoding="utf-8",
        )
        result = write_run_cards(root)
        self.assertEqual("ACTION", result["status"])
        self.assertIn("APPROVED", result["reason"])
        self.assertFalse((root / "prompts" / "speckit" / "g01-api-bundle-01" / "RUN_CARD.json").exists())

    def test_write_run_cards_allows_explicit_preview(self) -> None:
        root = self.make_workspace()
        (root / ".hldspec" / "sync" / "speckit_prework_approval.json").write_text(
            json.dumps({"status": "PENDING"}),
            encoding="utf-8",
        )
        result = write_run_cards(root, allow_unapproved_preview=True)
        self.assertEqual("PREVIEW", result["status"])
        card = json.loads((root / "prompts" / "speckit" / "g01-api-bundle-01" / "RUN_CARD.json").read_text(encoding="utf-8"))
        self.assertEqual("PREVIEW", card["status"])
        self.assertTrue(card["preview"])

    def test_write_run_cards_outputs_index_current_and_package_cards(self) -> None:
        root = self.make_workspace()
        result = write_run_cards(root)
        self.assertEqual("READY_FOR_EXECUTION_HANDOFF", result["status"])
        self.assertEqual(1, result["run_card_count"])
        package_dir = root / "prompts" / "speckit" / "g01-api-bundle-01"
        self.assertTrue((package_dir / "RUN_CARD.json").is_file())
        self.assertTrue((package_dir / "RUN_CARD.md").is_file())
        self.assertTrue((root / "prompts" / "speckit" / "RUN_CARDS.json").is_file())
        self.assertTrue((root / "prompts" / "speckit" / "RUN_CARDS.md").is_file())
        self.assertTrue((root / "prompts" / "speckit" / "current_RUN_CARD.json").is_file())
        self.assertTrue((root / "prompts" / "speckit" / "current_RUN_CARD.md").is_file())
        text = (package_dir / "RUN_CARD.md").read_text(encoding="utf-8")
        self.assertIn("## Requires", text)
        self.assertIn("## Ensures", text)
        self.assertIn("## Reassessment Triggers", text)

    def test_run_card_explains_clarification_policy(self) -> None:
        payload = build_run_card_payload(
            {
                "bundle_id": "G01",
                "bundle_name": "API Bundle 01",
                "bundle_slug": "g01-api-bundle-01",
                "dependency_position": 1,
                "allowed_evidence": [".hldspec/sync/speckit_invocation_queue.json"],
            },
            workspace=Path("/tmp/target"),
            sync=Path("/tmp/target/.hldspec/sync"),
            approved=True,
        )
        text = render_run_card_md(payload)
        self.assertIn("## Clarification Policy", text)
        self.assertIn("Clarification questions are not blockers by default.", text)
        self.assertIn("approved HLDspec evidence", text)
        self.assertIn("missing, contradictory, or the answer is human-owned", text)
        self.assertIn("Stop on RunSkeptic ACTION or CONFLICT", text)


if __name__ == "__main__":
    unittest.main()
