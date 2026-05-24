from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


enrich_mod = load_module("enrich_spec_build_plan_with_answer_context", "scripts/enrich_spec_build_plan_with_answer_context.py")
prework_mod = load_module("build_speckit_prework_plan", "scripts/build_speckit_prework_plan.py")


class SpecBuildPlanContextEnrichmentTest(unittest.TestCase):
    def make_workspace(self) -> tuple[Path, Path, tempfile.TemporaryDirectory[str]]:
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name)
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True)

        plan = {
            "schema_version": 1,
            "recommended_order": ["009", "010"],
            "planned_specs": [
                {
                    "planned_spec_id": "010",
                    "title": "Internal Database API",
                    "source_hld_sections": ["HLD-010"],
                    "depends_on_specs": ["009"],
                },
                {
                    "planned_spec_id": "009",
                    "title": "User Workflow",
                    "source_hld_sections": ["HLD-009"],
                    "depends_on_specs": [],
                },
            ],
        }
        plan_path = sync / "spec_build_plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")

        (sync / "hld_usecase_api_map.json").write_text(
            json.dumps(
                {
                    "system_use_cases": [
                        {
                            "id": "UC-001",
                            "name": "Run HLDspec workflow",
                            "source_hld_sections": ["HLD-009"],
                            "summary": "User runs a workflow.",
                        }
                    ],
                    "user_journeys": [
                        {
                            "id": "J-001",
                            "name": "First run",
                            "source_hld_sections": ["HLD-009"],
                            "summary": "Start and approve checkpoints.",
                        }
                    ],
                    "feature_candidates": [
                        {
                            "hld_id": "HLD-009",
                            "title": "User Workflow",
                            "source_hld_sections": ["HLD-009"],
                            "buildability_signals": ["ui_interaction"],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        (sync / "speckit_product_manager_pack.json").write_text(
            json.dumps(
                {
                    "user_stories": [
                        {
                            "story_id": "US-001",
                            "title": "Run workflow",
                            "story": "As a user, I want to run HLDspec.",
                            "acceptance_criteria": ["Workflow can start."],
                            "source_hld_sections": ["HLD-009"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (sync / "interface_contract_map.json").write_text(
            json.dumps(
                {
                    "contracts": [
                        {
                            "contract_id": "DATABASE_API_CONTRACT",
                            "contract_name": "Database API Contract",
                            "provider": "Database API",
                            "consumer": "CLI",
                            "source_hld_sections": ["HLD-010"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        (sync / "data_ownership_map.json").write_text(
            json.dumps(
                {
                    "data_objects": [
                        {
                            "data_object": "tasks",
                            "owner": "Database API",
                            "source_of_truth": "SQLite",
                            "update_timing": "transactional",
                            "source_hld_sections": ["HLD-010"],
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        return workspace, plan_path, tmp

    def test_enriches_product_and_architecture_context(self) -> None:
        workspace, plan_path, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        plan = enrich_mod.enrich_plan(plan_path, workspace)
        specs = {spec["planned_spec_id"]: spec for spec in plan["planned_specs"]}

        self.assertEqual(len(specs["009"]["product_context"]["user_stories"]), 1)
        self.assertFalse(specs["009"]["product_context"]["no_direct_user_story"])
        self.assertEqual(len(specs["010"]["architecture_context"]["contracts"]), 1)
        self.assertTrue(specs["010"]["product_context"]["no_direct_user_story"])
        self.assertEqual(specs["010"]["product_context"]["feeds_user_facing_specs"], [])

    def test_recommended_order_drives_graph_and_queue(self) -> None:
        workspace, plan_path, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        plan = enrich_mod.enrich_plan(plan_path, workspace)
        artifacts = prework_mod.build_artifacts(plan, plan_path)

        graph_order = artifacts["feature_dependency_graph"]["bottom_up_order"]
        queue_order = [item["feature_id"] for item in artifacts["speckit_invocation_queue"]["items"]]

        self.assertEqual(graph_order, ["009", "010"])
        self.assertEqual(queue_order, ["009", "010"])
        self.assertEqual(graph_order, queue_order)
        feature = artifacts["speckit_input_manifest"]["features"][0]
        self.assertEqual(len(feature["user_stories"]), 1)


if __name__ == "__main__":
    unittest.main()
