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


pm = load_module("build_speckit_product_manager_pack", "scripts/build_speckit_product_manager_pack.py")
arch = load_module("build_speckit_architect_pack", "scripts/build_speckit_architect_pack.py")
answer = load_module("build_speckit_answer_pack", "scripts/build_speckit_answer_pack.py")


class SpeckitPmArchAnswerPackTest(unittest.TestCase):
    def make_workspace(self) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        workspace = Path(tmp.name)
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "hld_usecase_api_map.json").write_text(
            json.dumps(
                {
                    "source_hld": "HLD.md",
                    "first_buildable_feature": {"hld_id": "HLD-001", "title": "Session API Interface"},
                    "system_use_cases": [
                        {
                            "id": "UC-001",
                            "name": "Session API Interface",
                            "source_hld_sections": ["HLD-001"],
                            "buildability_signals": ["api_interface"],
                            "summary": "User calls a session API.",
                        }
                    ],
                    "feature_candidates": [{"hld_id": "HLD-001", "title": "Session API Interface"}],
                    "api_interface_surfaces": [
                        {
                            "name": "Session API Interface",
                            "source_hld_sections": ["HLD-001"],
                            "contract_risk": "review_api_processing_split",
                        }
                    ],
                    "data_source_of_truth_objects": [
                        {
                            "name": "Session State",
                            "source_hld_sections": ["HLD-001"],
                            "source_of_truth_risk": True,
                        }
                    ],
                    "open_questions": [
                        {"question": "Which actor owns the session?", "source_hld_sections": ["HLD-001"]}
                    ],
                }
            ),
            encoding="utf-8",
        )
        (sync / "spec_build_plan.json").write_text(json.dumps({"planned_specs": [], "plan_quality": {}}), encoding="utf-8")
        (sync / "constitution_update_plan.json").write_text(
            json.dumps({"human_checkpoint": {"human_decision": "TBD"}, "required_rules": []}),
            encoding="utf-8",
        )
        (sync / "feature_dependency_graph.json").write_text(json.dumps({"bottom_up_order": ["001"]}), encoding="utf-8")
        (sync / "speckit_proxy_dossier.json").write_text(
            json.dumps({"selected_feature": {"feature_id": "001", "feature_name": "Session API Interface"}}),
            encoding="utf-8",
        )
        return workspace

    def test_product_manager_pack_creates_user_story_and_open_question(self) -> None:
        pack = pm.build_pack(self.make_workspace())
        self.assertEqual(len(pack["user_stories"]), 1)
        self.assertEqual(pack["user_stories"][0]["story_id"], "US-001")
        self.assertTrue(pack["product_open_questions"])
        self.assertEqual(pack["status"], "PRODUCT_QUESTIONS_BLOCKING")

    def test_architect_pack_creates_boundary_questions(self) -> None:
        pack = arch.build_pack(self.make_workspace())
        questions = pack["architecture_open_questions"]
        self.assertGreaterEqual(len(questions), 2)
        self.assertTrue(any(q["phase"] == "constitution" for q in questions))
        self.assertEqual(pack["status"], "ARCHITECTURE_QUESTIONS_BLOCKING")

    def test_answer_pack_blocks_on_open_questions(self) -> None:
        workspace = self.make_workspace()
        sync = workspace / ".specify" / "sync"
        pm_pack = pm.build_pack(workspace)
        arch_pack = arch.build_pack(workspace)
        (sync / "speckit_product_manager_pack.json").write_text(json.dumps(pm_pack), encoding="utf-8")
        (sync / "speckit_architect_pack.json").write_text(json.dumps(arch_pack), encoding="utf-8")
        pack = answer.build_pack(workspace)
        self.assertEqual(pack["status"], "BLOCKED_OPEN_QUESTIONS")
        self.assertGreater(len(pack["blocking_open_questions"]), 0)
        self.assertEqual(pack["counts"]["user_stories"], 1)

    def test_answer_pack_ready_when_questions_are_answered(self) -> None:
        workspace = self.make_workspace()
        sync = workspace / ".specify" / "sync"
        pm_pack = pm.build_pack(workspace)
        arch_pack = arch.build_pack(workspace)
        for q in pm_pack["product_open_questions"]:
            q["human_decision"] = "ANSWERED"
        for q in arch_pack["architecture_open_questions"]:
            q["human_decision"] = "ANSWERED"
        (sync / "speckit_product_manager_pack.json").write_text(json.dumps(pm_pack), encoding="utf-8")
        (sync / "speckit_architect_pack.json").write_text(json.dumps(arch_pack), encoding="utf-8")
        pack = answer.build_pack(workspace)
        self.assertEqual(pack["status"], "READY")
        self.assertEqual(pack["blocking_open_questions"], [])


if __name__ == "__main__":
    unittest.main()
