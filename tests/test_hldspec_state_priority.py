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


state_mod = load_module("build_hldspec_state", "scripts/build_hldspec_state.py")

# ---------------------------------------------------------------------------
# Helpers shared across tests
# ---------------------------------------------------------------------------

_CONVERTED_HLD = (
    "## HLD-001 - Foundation\n\n"
    "HLD-ID: HLD-001\n"
    "HLD-ROLE: api\n"
    "HLD-STATUS: active\n"
    "HLD-RISK: LOW\n"
    "HLD-SPECS: 001\n"
    "HLD-RESOURCES: TBD\n"
    "HLD-VERIFY: covered\n"
)

_GREEN_PLAN_REVIEW = "Continue to target-spec generation: `true`\n"

_GREEN_PLAN_JSON = {
    "plan_quality": {
        "decision": "PASS",
        "recommendation": "KEEP_PLAN",
        "conflicts": [],
    },
    "planned_specs": [{"planned_spec_id": "001"}],
}


def _make_workspace(tmp: str) -> tuple[Path, Path]:
    workspace = Path(tmp)
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True)
    (workspace / "HLD.md").write_text(_CONVERTED_HLD, encoding="utf-8")
    return workspace, sync


class HldspecStatePriorityTest(unittest.TestCase):
    def test_converted_hld_ignores_stale_conversion_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            converted_hld = (
                "# Converted HLD\n\n"
                "## HLD-001 - Foundation\n\n"
                "HLD-ID: HLD-001\n"
                "HLD-ROLE: API\n"
                "HLD-STATUS: Accepted\n"
                "HLD-RISK: Low\n"
                "HLD-SPECS: 001\n"
                "HLD-RESOURCES: TBD\n"
            )
            (workspace / "HLD.md").write_text(converted_hld, encoding="utf-8")
            (sync / "hld_conversion_decision_queue.json").write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "Q-001",
                                "blocking": True,
                                "human_decision": "TBD",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "hld_conversion_decision_queue.md").write_text("# stale\n", encoding="utf-8")

            state = state_mod.build_state(workspace, "/source/HLD.md")

            self.assertNotEqual(state["current_stage"], "CONVERSION_CHECKPOINT")
            self.assertNotEqual(state["current_checkpoint"], "hld_conversion_decisions")
            self.assertIn(
                "Ignored stale conversion queue because the working HLD is already in HLDspec format.",
                state["notes"],
            )

    def test_raw_hld_still_blocks_on_conversion_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            (workspace / "HLD.md").write_text("# Raw HLD\n\nNo HLDspec section markers yet.\n", encoding="utf-8")
            (sync / "hld_conversion_decision_queue.json").write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "Q-001",
                                "blocking": True,
                                "human_decision": "TBD",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "hld_conversion_decision_queue.md").write_text("# queue\n", encoding="utf-8")

            state = state_mod.build_state(workspace, "/source/HLD.md")

            self.assertEqual(state["current_stage"], "CONVERSION_CHECKPOINT")
            self.assertEqual(state["current_checkpoint"], "hld_conversion_decisions")
            self.assertEqual(state["blocking_questions"][0]["open_question_count"], 1)


class HldspecStateCheckpointCoverageTest(unittest.TestCase):
    """One test per state-machine stage not already covered above.

    Every test builds the minimal artifact set that puts build_state into that
    stage and no further — confirming stage-aware detection rather than just
    happy-path completion.
    """

    def test_first_run_pending(self) -> None:
        # Converted HLD present, no plan review anywhere → FIRST_RUN_PENDING.
        with tempfile.TemporaryDirectory() as tmp:
            workspace, _sync = _make_workspace(tmp)
            state = state_mod.build_state(workspace, "HLD.md")
            self.assertEqual(state["current_stage"], "FIRST_RUN_PENDING")
            self.assertEqual(state["current_checkpoint"], "run_first_readonly")

    def test_spec_build_plan_checkpoint(self) -> None:
        # Plan review exists, spec decision queue has a TBD blocking question.
        with tempfile.TemporaryDirectory() as tmp:
            workspace, sync = _make_workspace(tmp)
            (sync / "spec_build_plan_review.md").write_text(_GREEN_PLAN_REVIEW, encoding="utf-8")
            (sync / "spec_build_plan.json").write_text(json.dumps(_GREEN_PLAN_JSON), encoding="utf-8")
            (sync / "spec_build_plan_decision_queue.json").write_text(
                json.dumps({"questions": [{"question_id": "SPQ-001", "blocking": True, "human_decision": "TBD"}]}),
                encoding="utf-8",
            )
            state = state_mod.build_state(workspace, "HLD.md")
            self.assertEqual(state["current_stage"], "SPEC_BUILD_PLAN_CHECKPOINT")
            self.assertEqual(state["current_checkpoint"], "spec_build_plan_decisions")
            self.assertEqual(state["blocking_questions"][0]["open_question_count"], 1)

    def test_spec_build_plan_blocked(self) -> None:
        # Plan review explicitly gates false; no spec queue → SPEC_BUILD_PLAN_BLOCKED.
        with tempfile.TemporaryDirectory() as tmp:
            workspace, sync = _make_workspace(tmp)
            (sync / "spec_build_plan_review.md").write_text(
                "Continue to target-spec generation: `false`\n", encoding="utf-8"
            )
            (sync / "spec_build_plan.json").write_text(
                json.dumps({
                    "plan_quality": {"decision": "DECOMPOSE", "recommendation": "SPLIT_PLANNED_SPEC", "conflicts": []},
                    "planned_specs": [],
                }),
                encoding="utf-8",
            )
            state = state_mod.build_state(workspace, "HLD.md")
            self.assertEqual(state["current_stage"], "SPEC_BUILD_PLAN_BLOCKED")
            self.assertEqual(state["current_checkpoint"], "fix_or_decompose_spec_build_plan")

    def test_speckit_prework_missing(self) -> None:
        # Green plan, no prework quality review → SPECKIT_PREWORK_MISSING.
        with tempfile.TemporaryDirectory() as tmp:
            workspace, sync = _make_workspace(tmp)
            (sync / "spec_build_plan_review.md").write_text(_GREEN_PLAN_REVIEW, encoding="utf-8")
            (sync / "spec_build_plan.json").write_text(json.dumps(_GREEN_PLAN_JSON), encoding="utf-8")
            state = state_mod.build_state(workspace, "HLD.md")
            self.assertEqual(state["current_stage"], "SPECKIT_PREWORK_MISSING")
            self.assertEqual(state["current_checkpoint"], "generate_speckit_prework")

    def test_speckit_prework_rework_required(self) -> None:
        # Green plan, prework quality review has a BLOCKER → SPECKIT_PREWORK_REWORK_REQUIRED.
        with tempfile.TemporaryDirectory() as tmp:
            workspace, sync = _make_workspace(tmp)
            (sync / "spec_build_plan_review.md").write_text(_GREEN_PLAN_REVIEW, encoding="utf-8")
            (sync / "spec_build_plan.json").write_text(json.dumps(_GREEN_PLAN_JSON), encoding="utf-8")
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps({
                    "status": "REWORK_REQUIRED",
                    "findings": [{"id": "QG-006", "severity": "BLOCKER", "finding": "No constitution rules."}],
                }),
                encoding="utf-8",
            )
            state = state_mod.build_state(workspace, "HLD.md")
            self.assertEqual(state["current_stage"], "SPECKIT_PREWORK_REWORK_REQUIRED")
            self.assertEqual(state["current_checkpoint"], "rebuild_speckit_prework")

    def test_speckit_prework_approval_gate(self) -> None:
        # Green plan, prework quality review clean → SPECKIT_PREWORK_APPROVAL_GATE.
        with tempfile.TemporaryDirectory() as tmp:
            workspace, sync = _make_workspace(tmp)
            (sync / "spec_build_plan_review.md").write_text(_GREEN_PLAN_REVIEW, encoding="utf-8")
            (sync / "spec_build_plan.json").write_text(json.dumps(_GREEN_PLAN_JSON), encoding="utf-8")
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps({"status": "APPROVAL_READY", "findings": []}),
                encoding="utf-8",
            )
            state = state_mod.build_state(workspace, "HLD.md")
            self.assertEqual(state["current_stage"], "SPECKIT_PREWORK_APPROVAL_GATE")
            self.assertEqual(state["current_checkpoint"], "human_approves_speckit_prework")


if __name__ == "__main__":
    unittest.main()
