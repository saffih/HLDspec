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


proxy = load_module("build_speckit_proxy_dry_run", "scripts/build_speckit_proxy_dry_run.py")
approve = load_module("approve_hldspec_prework", "scripts/approve_hldspec_prework.py")


class SpeckitProxyDryRunTest(unittest.TestCase):
    def make_workspace(self, *, answer_status: str = "READY", blocking: list | None = None) -> Path:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        workspace = Path(tmp.name)
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "hldspec_state.json").write_text(
            json.dumps({"current_stage": "SPECKIT_PREWORK_APPROVAL_GATE"}),
            encoding="utf-8",
        )
        (sync / "speckit_prework_package.json").write_text(
            json.dumps(
                {
                    "status": "PENDING_HUMAN_REVIEW",
                    "human_checkpoint": {
                        "question": "Approve prework?",
                        "options": ["APPROVE_PLAN", "MODIFY_PLAN", "DECOMPOSE_MORE"],
                        "human_decision": "TBD",
                    },
                }
            ),
            encoding="utf-8",
        )
        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "APPROVAL_READY", "findings": []}),
            encoding="utf-8",
        )
        (sync / "hld_answer_dossier_quality_review.json").write_text(
            json.dumps({"status": "APPROVAL_READY", "findings": []}),
            encoding="utf-8",
        )
        (sync / "speckit_proxy_dossier.json").write_text(
            json.dumps(
                {
                    "selected_feature": {
                        "feature_id": "001",
                        "feature_name": "Session API Interface",
                        "short_name": "session-api-interface",
                    },
                    "speckit_specify_input": "Build Session API Interface from approved HLD evidence.",
                }
            ),
            encoding="utf-8",
        )
        (sync / "speckit_invocation_queue.json").write_text(json.dumps({"items": []}), encoding="utf-8")
        (sync / "speckit_answer_pack.json").write_text(
            json.dumps({"status": answer_status, "blocking_open_questions": blocking or []}),
            encoding="utf-8",
        )
        (sync / "hldspec_promotion_ledger.json").write_text(
            json.dumps({"schema_version": 1, "promotions": {"speckit_answer_pack": {"promotion_status": "ACCEPTED"}}}),
            encoding="utf-8",
        )
        return workspace

    def test_refuses_without_prework_approval(self) -> None:
        workspace = self.make_workspace()
        dry_run = proxy.build_dry_run(workspace, "specify")
        self.assertEqual(dry_run["status"], "REFUSED_PREWORK_NOT_APPROVED")
        self.assertFalse(dry_run["will_invoke_speckit"])
        self.assertFalse(dry_run["implementation_allowed"])

    def test_approved_prework_allows_one_phase_dry_run_when_answer_pack_ready(self) -> None:
        workspace = self.make_workspace()
        record = approve.approve_prework(workspace, "APPROVE_PLAN", "Approved for dry-run.")
        self.assertEqual(record["status"], "APPROVED")
        dry_run = proxy.build_dry_run(workspace, "specify")
        self.assertEqual(dry_run["status"], "DRY_RUN_READY")
        self.assertEqual(dry_run["phase"], "specify")
        self.assertEqual(dry_run["model_routing"]["assigned_agent_name"], "SpecKit Specify Proxy")
        self.assertEqual(dry_run["model_routing"]["model_tier"], "MODEL_STRONG")
        self.assertEqual(len(dry_run["would_run"]), 1)
        self.assertEqual(dry_run["would_run"][0]["assigned_agent_name"], "SpecKit Specify Proxy")
        self.assertEqual(dry_run["would_run"][0]["model_tier"], "MODEL_STRONG")
        self.assertFalse(dry_run["will_invoke_speckit"])
        self.assertFalse(dry_run["implementation_allowed"])

    def test_refuses_when_answer_pack_has_blocking_questions(self) -> None:
        workspace = self.make_workspace(answer_status="BLOCKED_OPEN_QUESTIONS", blocking=[{"question_id": "PMQ-001"}])
        approve.approve_prework(workspace, "APPROVE_PLAN")
        dry_run = proxy.build_dry_run(workspace, "specify")
        self.assertEqual(dry_run["status"], "REFUSED_ANSWER_PACK_BLOCKED")
        self.assertIn("answer pack status", " ".join(dry_run["refusal_reasons"]))

    def test_implementation_phase_is_forbidden_even_after_approval(self) -> None:
        workspace = self.make_workspace()
        approve.approve_prework(workspace, "APPROVE_PLAN")
        dry_run = proxy.build_dry_run(workspace, "implement")
        self.assertEqual(dry_run["status"], "REFUSED_IMPLEMENT_FORBIDDEN")
        self.assertFalse(dry_run["implementation_allowed"])

    def test_multiple_phases_are_rejected(self) -> None:
        workspace = self.make_workspace()
        approve.approve_prework(workspace, "APPROVE_PLAN")
        dry_run = proxy.build_dry_run(workspace, "specify,plan")
        self.assertEqual(dry_run["status"], "REFUSED_INVALID_PHASE")
        self.assertIn("one phase only", " ".join(dry_run["refusal_reasons"]))


if __name__ == "__main__":
    unittest.main()
