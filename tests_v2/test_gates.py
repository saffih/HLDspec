"""Tests for hldspec/gates.py — single source of truth for gate semantics.

Critical invariant: plan_gate_status() green requires decision == "PASS" only.
"FIX", "HANDLED", "CONFLICT", "DECOMPOSE" must never produce green=True.
"""
from __future__ import annotations

import unittest

from hldspec.gates import PlanGateStatus, PreworkGateStatus, plan_gate_status, prework_gate_status

# Review text that contains the continue: true marker.
_CONTINUE_TRUE = "Continue to SpecKit prework: `true`"
_CONTINUE_FALSE = "Continue to SpecKit prework: `false`"


def _base_plan(*, decision: str = "PASS", recommendation: str = "KEEP_PLAN") -> dict:
    return {
        "plan_quality": {
            "decision": decision,
            "recommendation": recommendation,
            "conflicts": [],
        },
        "planned_specs": [],
    }


def _full_review() -> str:
    return _CONTINUE_TRUE


# ---------------------------------------------------------------------------
# plan_gate_status — green conditions
# ---------------------------------------------------------------------------

class TestPlanGateGreenRequirements(unittest.TestCase):

    def test_all_conditions_met_is_green(self):
        gate = plan_gate_status(_base_plan(), _full_review())
        self.assertTrue(gate.green)

    def test_pass_decision_with_keep_plan_is_green(self):
        gate = plan_gate_status(_base_plan(decision="PASS", recommendation="KEEP_PLAN"), _full_review())
        self.assertTrue(gate.green)

    # --- THE CRITICAL BUG FIX: these must NOT be green ---

    def test_fix_decision_is_not_green(self):
        """decision=FIX must never produce green=True (was bug in build_hldspec_state.py)."""
        gate = plan_gate_status(_base_plan(decision="FIX"), _full_review())
        self.assertFalse(gate.green)

    def test_handled_decision_is_not_green(self):
        """decision=HANDLED must never produce green=True."""
        gate = plan_gate_status(_base_plan(decision="HANDLED"), _full_review())
        self.assertFalse(gate.green)

    def test_conflict_decision_is_not_green(self):
        gate = plan_gate_status(_base_plan(decision="CONFLICT"), _full_review())
        self.assertFalse(gate.green)

    def test_decompose_decision_is_not_green(self):
        gate = plan_gate_status(_base_plan(decision="DECOMPOSE"), _full_review())
        self.assertFalse(gate.green)

    def test_empty_decision_is_not_green(self):
        gate = plan_gate_status(_base_plan(decision=""), _full_review())
        self.assertFalse(gate.green)

    def test_missing_continue_marker_is_not_green(self):
        gate = plan_gate_status(_base_plan(), "No marker here.")
        self.assertFalse(gate.green)
        self.assertFalse(gate.continue_true)

    def test_continue_false_blocks_green(self):
        review = _CONTINUE_TRUE + "\n" + _CONTINUE_FALSE
        gate = plan_gate_status(_base_plan(), review)
        self.assertFalse(gate.green)
        self.assertTrue(gate.continue_false)

    def test_wrong_recommendation_is_not_green(self):
        gate = plan_gate_status(_base_plan(recommendation="REWORK"), _full_review())
        self.assertFalse(gate.green)

    def test_conflicts_block_green(self):
        plan = _base_plan()
        plan["plan_quality"]["conflicts"] = [{"id": "C-1", "description": "Conflict"}]
        gate = plan_gate_status(plan, _full_review())
        self.assertFalse(gate.green)
        self.assertEqual(1, gate.conflict_count)

    def test_flagged_specs_block_green(self):
        plan = _base_plan()
        plan["planned_specs"] = [
            {"planned_spec_id": "spec-001", "title": "Flagged", "quality_flags": ["missing_context"]},
        ]
        gate = plan_gate_status(plan, _full_review())
        self.assertFalse(gate.green)
        self.assertEqual(1, gate.flagged_count)

    def test_requires_user_review_spec_blocks_green(self):
        plan = _base_plan()
        plan["planned_specs"] = [
            {"planned_spec_id": "spec-002", "title": "Needs review", "requires_user_review": True},
        ]
        gate = plan_gate_status(plan, _full_review())
        self.assertFalse(gate.green)
        self.assertEqual(1, gate.flagged_count)


class TestPlanGateStatusFields(unittest.TestCase):

    def test_decision_propagated(self):
        gate = plan_gate_status(_base_plan(decision="FIX"), _full_review())
        self.assertEqual("FIX", gate.decision)

    def test_recommendation_propagated(self):
        gate = plan_gate_status(_base_plan(recommendation="REWORK"), _full_review())
        self.assertEqual("REWORK", gate.recommendation)

    def test_continue_true_detected(self):
        gate = plan_gate_status(_base_plan(), _CONTINUE_TRUE)
        self.assertTrue(gate.continue_true)

    def test_continue_false_detected(self):
        gate = plan_gate_status(_base_plan(), _CONTINUE_FALSE)
        self.assertTrue(gate.continue_false)

    def test_empty_plan_not_green(self):
        gate = plan_gate_status({}, _full_review())
        self.assertFalse(gate.green)

    def test_returns_plan_gate_status_type(self):
        gate = plan_gate_status(_base_plan(), _full_review())
        self.assertIsInstance(gate, PlanGateStatus)

    def test_legacy_marker_is_not_accepted(self):
        """Deprecated target-spec wording must not drive the live gate."""
        legacy_text = "Continue to target-spec generation: `true`"
        gate = plan_gate_status(_base_plan(), legacy_text)
        self.assertFalse(gate.continue_true)
        self.assertFalse(gate.green)


# ---------------------------------------------------------------------------
# prework_gate_status
# ---------------------------------------------------------------------------

class TestPreworkGateStatus(unittest.TestCase):

    def test_pass_status_no_blockers_is_ready(self):
        gate = prework_gate_status({"status": "PASS", "findings": []})
        self.assertTrue(gate.ready)
        self.assertEqual(0, gate.blocker_count)

    def test_rework_required_is_not_ready(self):
        gate = prework_gate_status({"status": "REWORK_REQUIRED", "findings": []})
        self.assertFalse(gate.ready)
        self.assertEqual("REWORK_REQUIRED", gate.status)

    def test_missing_status_is_not_ready(self):
        gate = prework_gate_status({})
        self.assertFalse(gate.ready)
        self.assertEqual("MISSING", gate.status)

    def test_blocker_finding_blocks_even_on_pass_status(self):
        gate = prework_gate_status({
            "status": "PASS",
            "findings": [{"severity": "BLOCKER", "field": "observed_evidence", "message": "missing"}],
        })
        self.assertFalse(gate.ready)
        self.assertEqual(1, gate.blocker_count)

    def test_action_finding_does_not_block(self):
        gate = prework_gate_status({
            "status": "PASS",
            "findings": [{"severity": "ACTION", "field": "evidence_level", "message": "note"}],
        })
        self.assertTrue(gate.ready)
        self.assertEqual(0, gate.blocker_count)

    def test_pending_human_review_status_is_ready(self):
        """PENDING_HUMAN_REVIEW is not REWORK — gate should pass."""
        gate = prework_gate_status({"status": "PENDING_HUMAN_REVIEW", "findings": []})
        self.assertTrue(gate.ready)

    def test_returns_prework_gate_status_type(self):
        gate = prework_gate_status({"status": "PASS", "findings": []})
        self.assertIsInstance(gate, PreworkGateStatus)

    def test_non_dict_review_is_not_ready(self):
        gate = prework_gate_status(None)  # type: ignore[arg-type]
        self.assertFalse(gate.ready)


if __name__ == "__main__":
    unittest.main()
