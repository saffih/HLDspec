from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StateAndPreworkPackageTests(unittest.TestCase):
    def test_state_detects_conversion_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            (workspace / "HLD.md").write_text("# Raw HLD\n", encoding="utf-8")
            (sync / "hld_conversion_decision_queue.json").write_text(
                json.dumps({"questions": [{"question_id": "Q-001", "human_decision": "TBD", "blocking": True}]}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_hldspec_state.py"), str(workspace), "--source-hld", "Flow-System-HLD.md"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            state = json.loads((sync / "hldspec_state.json").read_text(encoding="utf-8"))
            self.assertEqual("CONVERSION_CHECKPOINT", state["current_stage"])
            self.assertEqual("hld_conversion_decisions", state["current_checkpoint"])

    def test_state_handles_direct_first_run_workspace_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            (workspace / "HLD.md").write_text(
                """# HLD

## HLD-001 - API

HLD-ID: HLD-001
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 001
HLD-RESOURCES: TBD
HLD-VERIFY: covered
""",
                encoding="utf-8",
            )
            (sync / "spec_build_plan_review.md").write_text("Continue to target-spec generation: `false`\n", encoding="utf-8")
            (sync / "spec_build_plan.json").write_text(
                json.dumps(
                    {
                        "plan_quality": {"decision": "DECOMPOSE", "recommendation": "SPLIT_PLANNED_SPEC", "conflicts": []},
                        "planned_specs": [],
                    }
                ),
                encoding="utf-8",
            )
            (sync / "spec_build_plan_decision_queue.json").write_text(
                json.dumps({"questions": [{"question_id": "SPQ-001", "human_decision": "TBD", "blocking": True}]}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_hldspec_state.py"), str(workspace), "--source-hld", "Flow-System-HLD.md"],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            state = json.loads((sync / "hldspec_state.json").read_text(encoding="utf-8"))
            self.assertEqual("SPEC_BUILD_PLAN_CHECKPOINT", state["current_stage"])
            self.assertEqual("spec_build_plan_decisions", state["current_checkpoint"])

    def test_prework_package_combines_review_case(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            (sync / "hldspec_state.json").write_text(
                json.dumps({"current_stage": "SPECKIT_PREWORK_APPROVAL_GATE", "current_checkpoint": "human_approves_speckit_prework"}),
                encoding="utf-8",
            )
            (sync / "constitution_update_plan.json").write_text(
                json.dumps({"required_rules": [{"rule_id": "ARCH-001", "name": "HLD Source of Truth", "rule": "Do not contradict HLD."}]}),
                encoding="utf-8",
            )
            (sync / "feature_dependency_graph.json").write_text(json.dumps({"bottom_up_order": ["001"], "edges": []}), encoding="utf-8")
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps(
                    {
                        "status": "APPROVAL_READY",
                        "findings": [],
                        "case_to_present": {
                            "first_feature_case": {
                                "feature_id": "001",
                                "feature_name": "Rock Foundation",
                                "why_first": "This feature has no dependencies.",
                                "depends_on": [],
                            }
                        },
                        "affected_artifact_policy": {"if_human_changes_constitution": ["rebuild constitution_update_plan"]},
                    }
                ),
                encoding="utf-8",
            )
            (sync / "speckit_proxy_dossier.json").write_text(
                json.dumps({"selected_feature": {"feature_id": "001", "feature_name": "Rock Foundation", "short_name": "001-rock-foundation", "depends_on_features": []}}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_speckit_prework_package.py"), str(workspace)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            package = json.loads((sync / "speckit_prework_package.json").read_text(encoding="utf-8"))
            self.assertEqual("PENDING_HUMAN_REVIEW", package["status"])
            self.assertEqual("TBD", package["human_checkpoint"]["human_decision"])

            report = (sync / "speckit_prework_package.md").read_text(encoding="utf-8")
            self.assertIn("Constitution case", report)
            self.assertIn("Architecture and dependency case", report)
            self.assertIn("First feature case", report)
            self.assertIn("Legacy/supporting artifacts", report)

    def test_prework_package_blocks_before_approval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            (sync / "hldspec_state.json").write_text(
                json.dumps(
                    {
                        "current_stage": "SPEC_BUILD_PLAN_CHECKPOINT",
                        "current_checkpoint": "spec_build_plan_decisions",
                        "next_allowed_actions": ["judge presents spec_build_plan_decision_queue.md"],
                        "controlling_artifacts": ["/tmp/work/.specify/sync/spec_build_plan_decision_queue.md"],
                    }
                ),
                encoding="utf-8",
            )
            (sync / "constitution_update_plan.json").write_text(
                json.dumps({"required_rules": [{"rule_id": "ARCH-001", "name": "HLD Source of Truth", "rule": "Do not contradict HLD."}]}),
                encoding="utf-8",
            )
            (sync / "feature_dependency_graph.json").write_text(json.dumps({"bottom_up_order": ["001"], "edges": []}), encoding="utf-8")
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps({"status": "APPROVAL_READY", "findings": [], "affected_artifact_policy": {}}),
                encoding="utf-8",
            )
            (sync / "speckit_proxy_dossier.json").write_text(
                json.dumps({"selected_feature": {"feature_id": "001", "feature_name": "Rock Foundation", "short_name": "001-rock-foundation"}}),
                encoding="utf-8",
            )

            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_speckit_prework_package.py"), str(workspace)],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            package = json.loads((sync / "speckit_prework_package.json").read_text(encoding="utf-8"))
            self.assertEqual("BLOCKED_BY_CURRENT_CHECKPOINT", package["status"])
            self.assertEqual("NOT_APPLICABLE", package["human_checkpoint"]["human_decision"])
            self.assertIn("spec_build_plan_decision_queue.md", package["controlling_artifacts"][0])

            report = (sync / "speckit_prework_package.md").read_text(encoding="utf-8")
            self.assertIn("Blocking checkpoint", report)
            self.assertIn("not approval-ready", report)
            self.assertIn("spec_build_plan_decision_queue.md", report)


if __name__ == "__main__":
    unittest.main()
