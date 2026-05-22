from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RAW_HLD = """# Demo Raw HLD

## Product Goals

Users need a dashboard journey with acceptance criteria and stakeholder goals.

## API and Processing

The HTTP API endpoint accepts a request and response contract.
The workflow processes validation steps and runtime decisions.
DEPENDS REF HLD-003

## Data State

The database schema stores user state.
This is the source of truth for persistence.

## Governance

Architecture constraints and assumptions belong in the constitution.

## Security Controls

Security requires auth token permission checks.

## Operations Runbook

Deployment rollback, observability, alerts, and recovery are required.

## Neutral Notes

Miscellaneous notes.
CONFLICTS_WITH REF HLD-004
"""


def build_plan_for(raw_hld: str = RAW_HLD) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        source = work / "raw.md"
        source.write_text(raw_hld, encoding="utf-8")

        conversion_plan = {
            "candidates": [
                {"proposed_hld_id": "HLD-001", "title": "Product Goals", "source_line_start": 3, "source_line_end": 5, "recommended_action": "PROCEED_METADATA_ONLY"},
                {"proposed_hld_id": "HLD-002", "title": "API and Processing", "source_line_start": 7, "source_line_end": 11, "recommended_action": "PROCEED_METADATA_ONLY"},
                {"proposed_hld_id": "HLD-003", "title": "Data State", "source_line_start": 13, "source_line_end": 16, "recommended_action": "PROCEED_METADATA_ONLY"},
                {"proposed_hld_id": "HLD-004", "title": "Governance", "source_line_start": 18, "source_line_end": 20, "recommended_action": "PROCEED_METADATA_ONLY"},
                {"proposed_hld_id": "HLD-005", "title": "Security Controls", "source_line_start": 22, "source_line_end": 24, "recommended_action": "PROCEED_METADATA_ONLY"},
                {"proposed_hld_id": "HLD-006", "title": "Operations Runbook", "source_line_start": 26, "source_line_end": 28, "recommended_action": "PROCEED_METADATA_ONLY"},
                {"proposed_hld_id": "HLD-007", "title": "Neutral Notes", "source_line_start": 30, "source_line_end": 33, "recommended_action": "PROCEED_METADATA_ONLY"},
            ]
        }
        plan_path = work / "conversion_plan.json"
        plan_path.write_text(json.dumps(conversion_plan), encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "build_raw_hld_marking_plan.py"),
                str(plan_path),
                str(work),
                "--source-hld",
                str(source),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if result.returncode != 0:
            raise AssertionError(result.stderr + result.stdout)

        data = json.loads((work / ".specify" / "sync" / "raw_hld_marking_plan.json").read_text(encoding="utf-8"))
        self_report = work / ".specify" / "sync" / "raw_hld_marking_plan.md"
        self_prompt = work / "RAW_HLD_MARKING_PROMPT.md"
        assert self_report.exists()
        assert self_prompt.exists()
        return data


class RawHldMarkingPlanTests(unittest.TestCase):
    def test_builds_raw_hld_marking_plan_with_bounded_perspectives(self) -> None:
        data = build_plan_for()

        self.assertEqual("RAW_HLD_MARKING_REQUIRED", data["status"])
        self.assertEqual(7, len(data["items"]))

        by_id = {item["candidate_id"]: item for item in data["items"]}
        self.assertEqual("product_context", by_id["HLD-001"]["primary_role"])
        self.assertIn("interface_contract", by_id["HLD-002"]["suggested_roles"])
        self.assertIn("processing_behavior", by_id["HLD-002"]["suggested_roles"])
        self.assertEqual("SPLIT", by_id["HLD-002"]["split_keep_recommendation"])
        self.assertIn("data_model", by_id["HLD-003"]["suggested_roles"])
        self.assertIn("governance_context", by_id["HLD-004"]["suggested_roles"])

        self.assertIn("product_reviewer", by_id["HLD-001"]["subagents"])
        self.assertIn("architecture_reviewer", data["subagent_contract"]["bounded_subagents"])

    def test_security_and_operations_roles_get_correct_subagents(self) -> None:
        data = build_plan_for()
        by_id = {item["candidate_id"]: item for item in data["items"]}

        self.assertIn("security", by_id["HLD-005"]["suggested_roles"])
        self.assertIn("security_reviewer", by_id["HLD-005"]["subagents"])
        self.assertIn("operations", by_id["HLD-006"]["suggested_roles"])
        self.assertIn("operations_reviewer", by_id["HLD-006"]["subagents"])

    def test_unknown_neutral_section_stays_tbd_not_architecture(self) -> None:
        data = build_plan_for()
        item = {item["candidate_id"]: item for item in data["items"]}["HLD-007"]

        self.assertEqual([], item["suggested_roles"])
        self.assertEqual("TBD", item["primary_role"])
        self.assertEqual("unknown", item["evidence_level"])
        self.assertEqual("TBD", item["split_keep_recommendation"])
        self.assertIn("Insufficient evidence", " ".join(item["judge_notes"]))
        self.assertEqual("TBD", item["candidate_hld_metadata"]["HLD-ROLE"])

    def test_refs_are_extracted_into_metadata(self) -> None:
        data = build_plan_for()
        by_id = {item["candidate_id"]: item for item in data["items"]}

        self.assertEqual(["HLD-003"], by_id["HLD-002"]["depends_ref"])
        self.assertEqual(["HLD-003"], by_id["HLD-002"]["candidate_hld_metadata"]["DEPENDS_REF"])
        self.assertEqual(["HLD-004"], by_id["HLD-007"]["conflicts_with_ref"])
        self.assertEqual(["HLD-004"], by_id["HLD-007"]["candidate_hld_metadata"]["CONFLICTS_WITH_REF"])

    def test_metadata_object_exists_for_every_marking_item(self) -> None:
        data = build_plan_for()
        required = {
            "HLD-ID",
            "HLD-ROLE",
            "HLD-STATUS",
            "HLD-RISK",
            "HLD-SPECS",
            "HLD-RESOURCES",
            "HLD-VERIFY",
            "REF",
            "DEPENDS_REF",
            "CONFLICTS_WITH_REF",
        }

        for item in data["items"]:
            metadata = item["candidate_hld_metadata"]
            self.assertTrue(required.issubset(metadata.keys()))
            self.assertIn(item["evidence_level"], {"observed", "inferred_risk", "unknown"})
            self.assertIn(item["split_keep_recommendation"], {"KEEP", "SPLIT", "TBD"})


if __name__ == "__main__":
    unittest.main()
