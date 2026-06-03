from __future__ import annotations

import importlib.util
import json
import subprocess
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


apply_mod = load_module("apply_spec_build_plan_decisions", "scripts/apply_spec_build_plan_decisions.py")


class ApplySpecBuildPlanDecisionsTest(unittest.TestCase):
    def make_workspace(self) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name) / "firstrun"
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True)

        plan = {
            "schema_version": 1,
            "source_hld": "HLD.md",
            "constitution_action": "create",
            "planned_specs": [
                {
                    "planned_spec_id": "010",
                    "slug": "010-flow-core-database-api",
                    "title": "2. Flow Core Database API (Critical Safety Layer)",
                    "layer": "processing",
                    "source_hld_sections": ["HLD-010"],
                    "depends_on_specs": [],
                    "blocks_specs": ["011"],
                    "api_contract_expectations": ["Explicit API contract."],
                    "coverage_expectations": ["HLD-010 anchors represented."],
                    "integration_expectations": [],
                    "performance_expectations": [],
                    "memory_expectations": [],
                    "RunSkeptic_cycles": [],
                    "decision": "DECOMPOSE",
                    "recommendation": "SPLIT_SPEC",
                    "quality_flags": ["data_api_boundary_needs_review"],
                    "boundary_risk": "high",
                    "requires_user_review": True,
                    "layer_mix": ["processing"],
                    "role_mix": ["architecture"],
                    "responsibility_mix": ["api_contract", "data_state"],
                    "user_decision_needed": "",
                },
                {
                    "planned_spec_id": "011",
                    "slug": "011-dependent",
                    "title": "Dependent Feature",
                    "layer": "processing",
                    "source_hld_sections": ["HLD-011"],
                    "depends_on_specs": ["010"],
                    "blocks_specs": [],
                    "api_contract_expectations": [],
                    "coverage_expectations": ["HLD-011 anchors represented."],
                    "integration_expectations": [],
                    "performance_expectations": [],
                    "memory_expectations": [],
                    "RunSkeptic_cycles": [],
                    "decision": "FIX",
                    "recommendation": "KEEP_SPEC",
                    "quality_flags": [],
                    "boundary_risk": "low",
                    "requires_user_review": False,
                    "layer_mix": ["processing"],
                    "role_mix": ["architecture"],
                    "responsibility_mix": ["processing"],
                    "user_decision_needed": "",
                },
            ],
            "recommended_order": ["010", "011"],
            "context_hld_sections": [],
            "conflicts": [],
            "deferred": [],
            "plan_quality": {
                "decision": "DECOMPOSE",
                "recommendation": "SPLIT_PLANNED_SPEC",
                "findings": ["010: data_api_boundary_needs_review"],
                "conflicts": [],
                "RunSkeptic_cycles": [],
            },
        }
        queue = {
            "schema_version": 1,
            "status": "DECISIONS_RECORDED",
            "checkpoint": {
                "checkpoint_id": "SPEC_BUILD_PLAN_DECISIONS",
                "open_question_count": 0,
                "allowed_to_generate_target_specs": True,
            },
            "questions": [
                {
                    "question_id": "SPQ-001",
                    "planned_spec_id": "010",
                    "title": "2. Flow Core Database API (Critical Safety Layer)",
                    "quality_flags": ["data_api_boundary_needs_review"],
                    "boundary_risk": "high",
                    "blocking": True,
                    "human_decision": "SPLIT_PLANNED_SPEC",
                    "options": [
                        "SPLIT_PLANNED_SPEC",
                        "MODIFY_HLD_SPECS_MAPPING",
                        "KEEP_AS_ONE_WITH_REASON",
                        "DEFER",
                    ],
                }
            ],
        }
        (sync / "spec_build_plan.json").write_text(json.dumps(plan), encoding="utf-8")
        (sync / "spec_build_plan_decision_queue.json").write_text(json.dumps(queue), encoding="utf-8")
        return workspace, tmp

    def test_split_decision_rewrites_plan_and_clears_gate(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        result = apply_mod.apply_decisions(workspace)

        self.assertEqual(result["status"], "SPEC_PLAN_DECISIONS_APPLIED")
        plan = json.loads((workspace / ".specify" / "sync" / "spec_build_plan.json").read_text())
        ids = [spec["planned_spec_id"] for spec in plan["planned_specs"]]

        self.assertIn("010-data", ids)
        self.assertIn("010-api", ids)
        self.assertNotIn("010", ids)

        by_id = {spec["planned_spec_id"]: spec for spec in plan["planned_specs"]}
        self.assertEqual(by_id["010-data"]["quality_flags"], [])
        self.assertEqual(by_id["010-api"]["quality_flags"], [])
        self.assertIn("010-data", by_id["010-api"]["depends_on_specs"])
        self.assertIn("010-data", by_id["011"]["depends_on_specs"])
        self.assertIn("010-api", by_id["011"]["depends_on_specs"])
        self.assertEqual(plan["plan_quality"]["decision"], "PASS")
        self.assertEqual(plan["plan_quality"]["recommendation"], "KEEP_PLAN")

    def test_review_after_apply_allows_speckit_prework(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        apply_mod.apply_decisions(workspace)
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "review_spec_build_plan.py"),
                str(workspace / ".specify" / "sync" / "spec_build_plan.json"),
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        review = (workspace / ".specify" / "sync" / "spec_build_plan_review.md").read_text()
        self.assertIn("Continue to SpecKit prework: `true`", review)
        self.assertIn("Flagged specs: `0`", review)


if __name__ == "__main__":
    unittest.main()
