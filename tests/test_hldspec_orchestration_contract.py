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


junior = load_module("build_hldspec_junior_task_packets", "scripts/build_hldspec_junior_task_packets.py")
orch = load_module("build_hldspec_orchestration_state", "scripts/build_hldspec_orchestration_state.py")
promote = load_module("promote_hldspec_artifact", "scripts/promote_hldspec_artifact.py")
proxy = load_module("build_speckit_proxy_dry_run_for_orchestration", "scripts/build_speckit_proxy_dry_run.py")


class HldspecOrchestrationContractTest(unittest.TestCase):
    def make_workspace(self, *, pm_questions=None, arch_questions=None, answer_blockers=None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        workspace = Path(tmp.name)
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_product_manager_pack.json").write_text(json.dumps({"status": "READY", "product_open_questions": pm_questions or []}), encoding="utf-8")
        (sync / "speckit_architect_pack.json").write_text(json.dumps({"status": "READY", "architecture_open_questions": arch_questions or []}), encoding="utf-8")
        (sync / "speckit_answer_pack.json").write_text(json.dumps({"status": "READY", "blocking_open_questions": answer_blockers or []}), encoding="utf-8")
        (sync / "speckit_prework_package.json").write_text(json.dumps({"human_checkpoint": {"human_decision": "APPROVE_PLAN", "options": ["APPROVE_PLAN"]}}), encoding="utf-8")
        (sync / "speckit_prework_quality_review.json").write_text(json.dumps({"status": "APPROVAL_READY", "findings": []}), encoding="utf-8")
        (sync / "hldspec_state.json").write_text(json.dumps({"current_stage": "SPECKIT_PREWORK_APPROVAL_GATE"}), encoding="utf-8")
        (sync / "speckit_proxy_dossier.json").write_text(json.dumps({"selected_feature": {"feature_id": "001", "feature_name": "Session API"}, "speckit_specify_input": "Specify Session API."}), encoding="utf-8")
        (sync / "speckit_invocation_queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        return workspace

    def test_junior_task_packets_are_low_cost_and_cannot_promote(self) -> None:
        data = junior.build_packets(self.make_workspace())
        self.assertGreaterEqual(len(data["task_packets"]), 4)
        self.assertIn("model_routing_policy", data)
        self.assertEqual(
            data["model_routing_policy"]["promotion_rule"],
            "Weakest sufficient model creates; strongest necessary model promotes.",
        )
        packets = {item["task_id"]: item for item in data["task_packets"]}
        self.assertEqual(packets["JPM-001"]["assigned_agent_name"], "Junior Product Extractor")
        self.assertEqual(packets["JPM-001"]["model_tier"], "MODEL_ROUTINE")
        self.assertEqual(packets["JPM-001"]["cost_tier"], "LOW")
        self.assertEqual(packets["JPM-002"]["assigned_agent_name"], "Product Story Drafting Agent")
        self.assertEqual(packets["JPM-002"]["model_tier"], "MODEL_STRONG")
        self.assertEqual(packets["JPM-002"]["cost_tier"], "MEDIUM")
        self.assertEqual(packets["JAR-001"]["assigned_agent_name"], "Architecture Boundary Scout")
        self.assertEqual(packets["JAR-001"]["model_tier"], "MODEL_STRONG")
        self.assertEqual(packets["JAR-001"]["cost_tier"], "MEDIUM")
        self.assertEqual(packets["JAR-002"]["assigned_agent_name"], "Dependency Risk Scout")
        self.assertEqual(packets["JAR-002"]["model_tier"], "MODEL_STRONG")
        self.assertEqual(packets["JAR-002"]["cost_tier"], "MEDIUM")
        for item in data["task_packets"]:
            self.assertIn("do not promote artifacts", item["forbidden_actions"])
            self.assertTrue(item["requires_senior_review"])
            self.assertTrue(item["requires_judge_promotion"])
            self.assertIn("escalation_rule", item)

    def test_existing_artifacts_are_proposed_not_accepted(self) -> None:
        state = orch.build_state(self.make_workspace())
        outputs = {item["artifact_id"]: item for item in state["specialist_outputs"]}
        self.assertEqual(outputs["speckit_product_manager_pack"]["promotion_status"], "PROPOSED")
        self.assertEqual(outputs["speckit_product_manager_pack"]["assigned_agent_name"], "Product Lead Reviewer")
        self.assertEqual(outputs["speckit_product_manager_pack"]["model_tier"], "MODEL_STRONG")
        self.assertEqual(outputs["speckit_architect_pack"]["promotion_status"], "PROPOSED")
        self.assertEqual(outputs["speckit_architect_pack"]["assigned_agent_name"], "Architect Lead Reviewer")
        self.assertEqual(outputs["speckit_architect_pack"]["model_tier"], "MODEL_CRITICAL")
        self.assertEqual(outputs["speckit_answer_pack"]["promotion_status"], "PROPOSED")
        self.assertEqual(outputs["speckit_answer_pack"]["assigned_agent_name"], "HLDspec Judge Orchestrator")
        self.assertEqual(outputs["speckit_answer_pack"]["model_tier"], "MODEL_CRITICAL")
        self.assertIn("SpecKit proxy dry-run requires accepted answer pack and approved prework", state["blocked_actions"])

    def test_answer_pack_cannot_be_accepted_before_pm_and_arch(self) -> None:
        workspace = self.make_workspace()
        with self.assertRaises(ValueError):
            promote.promote(workspace, "speckit_answer_pack", "ACCEPTED")

    def test_answer_pack_acceptance_requires_no_open_questions(self) -> None:
        workspace = self.make_workspace(answer_blockers=[{"question_id": "PMQ-001", "human_decision": "TBD"}])
        promote.promote(workspace, "speckit_product_manager_pack", "ACCEPTED")
        promote.promote(workspace, "speckit_architect_pack", "ACCEPTED")
        with self.assertRaises(ValueError):
            promote.promote(workspace, "speckit_answer_pack", "ACCEPTED")

    def test_proxy_refuses_unpromoted_answer_pack(self) -> None:
        workspace = self.make_workspace()
        dry = proxy.build_dry_run(workspace, "specify")
        self.assertEqual(dry["status"], "REFUSED_ANSWER_PACK_NOT_PROMOTED")

    def test_proxy_allows_after_judge_promotes_answer_pack(self) -> None:
        workspace = self.make_workspace()
        promote.promote(workspace, "speckit_product_manager_pack", "ACCEPTED")
        promote.promote(workspace, "speckit_architect_pack", "ACCEPTED")
        promote.promote(workspace, "speckit_answer_pack", "ACCEPTED")
        dry = proxy.build_dry_run(workspace, "specify")
        self.assertEqual(dry["status"], "DRY_RUN_READY")
        self.assertEqual(dry["answer_pack"]["promotion_status"], "ACCEPTED")


if __name__ == "__main__":
    unittest.main()
