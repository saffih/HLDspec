"""
Negative-path tests for SpecBuildPlanMachine._quality() green condition.

The gate goes green only when ALL of:
  - review text contains "Continue to SpecKit prework: true"
  - review text does NOT contain "Continue to SpecKit prework: false"
  - plan_quality.decision == "PASS"
  - plan_quality.recommendation == "KEEP_PLAN"
  - no conflicts
  - no flagged specs

apply_spec_build_plan_decisions.py produces:
  - clean plan  -> decision="PASS",     recommendation="KEEP_PLAN"
  - has findings -> decision="FIX",      recommendation="REVIEW_PLAN"
  - conflicts   -> decision="CONFLICT",  recommendation="RESOLVE_CONFLICT"
  - needs split -> decision="DECOMPOSE", recommendation="SPLIT_PLANNED_SPEC"

The old condition (decision=="FIX" and recommendation=="KEEP_PLAN") was
unreachable — "FIX" is never paired with "KEEP_PLAN" by the generator.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.spec_build_plan import SpecBuildPlanMachine
from hldspec.state_machine import MachineContext, MachineStatus


CONTINUE_TRUE = "Continue to SpecKit prework: `true`\n"
CONTINUE_FALSE = "Continue to SpecKit prework: `false`\n"


def make_workspace(plan_quality: dict, planned_specs: list | None = None, review_text: str = CONTINUE_TRUE) -> Path:
    work = Path(tempfile.mkdtemp())
    sync = work / "firstrun" / ".specify" / "sync"
    sync.mkdir(parents=True)
    (sync / "spec_build_plan_review.md").write_text(review_text, encoding="utf-8")
    (sync / "spec_build_plan.json").write_text(
        json.dumps({"plan_quality": plan_quality, "planned_specs": planned_specs or []}),
        encoding="utf-8",
    )
    return work


def run(work: Path) -> "MachineResult":  # noqa: F821
    return SpecBuildPlanMachine().run(
        MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
    )


class TestGreenPath(unittest.TestCase):
    """The one combination that must go green."""

    def test_pass_keep_plan_no_issues_is_green(self) -> None:
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
        )
        result = run(work)
        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_GREEN", result.state)


class TestOldBrokenComboIsNotGreen(unittest.TestCase):
    """FIX+KEEP_PLAN was the old (wrong) green condition. It must NOT pass."""

    def test_fix_keep_plan_is_not_green(self) -> None:
        # This combination is never produced by apply_spec_build_plan_decisions.py
        # but if somehow present it should not go green.
        work = make_workspace(
            {"decision": "FIX", "recommendation": "KEEP_PLAN", "conflicts": []},
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)

    def test_fix_review_plan_is_not_green(self) -> None:
        # Normal "has findings" output from the generator — should checkpoint.
        work = make_workspace(
            {"decision": "FIX", "recommendation": "REVIEW_PLAN", "conflicts": []},
        )
        result = run(work)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)


class TestBlockingDecisions(unittest.TestCase):
    """CONFLICT and DECOMPOSE decisions must block."""

    def test_conflict_decision_is_not_green(self) -> None:
        work = make_workspace(
            {"decision": "CONFLICT", "recommendation": "RESOLVE_CONFLICT", "conflicts": ["spec boundary unclear"]},
        )
        result = run(work)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)

    def test_decompose_decision_is_not_green(self) -> None:
        work = make_workspace(
            {"decision": "DECOMPOSE", "recommendation": "SPLIT_PLANNED_SPEC", "conflicts": []},
        )
        result = run(work)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)


class TestReviewTextMarkers(unittest.TestCase):
    """continue_true/continue_false markers are required conditions."""

    def test_missing_continue_marker_is_not_green(self) -> None:
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
            review_text="No marker here.\n",
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)

    def test_continue_false_blocks_even_with_pass_decision(self) -> None:
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
            review_text=CONTINUE_FALSE,
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)

    def test_both_true_and_false_markers_is_not_green(self) -> None:
        # Contradictory markers — should not go green.
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
            review_text=CONTINUE_TRUE + CONTINUE_FALSE,
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)


class TestConflictsAndFlaggedSpecs(unittest.TestCase):
    """Conflicts or flagged specs block green even with PASS decision."""

    def test_pass_with_conflicts_is_not_green(self) -> None:
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": ["scope overlap"]},
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)

    def test_pass_with_flagged_spec_is_not_green(self) -> None:
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
            planned_specs=[
                {
                    "planned_spec_id": "PS-001",
                    "title": "Mixed concerns",
                    "quality_flags": ["mixed_responsibilities"],
                    "requires_user_review": True,
                }
            ],
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)

    def test_pass_with_requires_review_only_is_not_green(self) -> None:
        # requires_user_review=True without quality_flags still blocks.
        work = make_workspace(
            {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
            planned_specs=[
                {
                    "planned_spec_id": "PS-002",
                    "title": "Ambiguous boundary",
                    "quality_flags": [],
                    "requires_user_review": True,
                }
            ],
        )
        result = run(work)
        self.assertNotEqual("SPEC_BUILD_PLAN_GREEN", result.state)


class TestMissingArtifacts(unittest.TestCase):
    """Missing artifacts must checkpoint, not error silently."""

    def test_missing_plan_json_checkpoints(self) -> None:
        work = Path(tempfile.mkdtemp())
        sync = work / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "spec_build_plan_review.md").write_text(CONTINUE_TRUE, encoding="utf-8")
        # no spec_build_plan.json

        result = run(work)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_MISSING", result.state)

    def test_missing_review_md_checkpoints(self) -> None:
        work = Path(tempfile.mkdtemp())
        sync = work / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "spec_build_plan.json").write_text(
            json.dumps({"plan_quality": {"decision": "PASS", "recommendation": "KEEP_PLAN"}, "planned_specs": []}),
            encoding="utf-8",
        )
        # no spec_build_plan_review.md

        result = run(work)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_MISSING", result.state)


if __name__ == "__main__":
    unittest.main()
