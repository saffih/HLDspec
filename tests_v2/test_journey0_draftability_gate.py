"""Tests for the pure Journey 0 draftability gate."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_draftability_gate as gate


def _evidence_pack(*labels: str) -> dict:
    return {
        "kind": j0.ARTIFACT_BROWNFIELD_EVIDENCE_PACK,
        "evidence": [
            {"label": label, "statement": f"evidence #{idx} ({label})"}
            for idx, label in enumerate(labels)
        ],
    }


def _input(**overrides: object) -> gate.DraftabilityInput:
    values = {
        "evidence_pack": _evidence_pack(j0.EVIDENCE_OBSERVED),
        "gap_report": {"kind": j0.ARTIFACT_HLD_GAP_REPORT},
        "product_decision_register": (),
    }
    values.update(overrides)
    return gate.DraftabilityInput(**values)


class Journey0DraftabilityGateTests(unittest.TestCase):
    def test_ready_to_draft_hld_for_sufficient_observed_evidence(self) -> None:
        result = gate.evaluate_hld_draftability(_input())

        self.assertEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertTrue(result.draftable)
        self.assertEqual(result.accepted_fact_count, 1)
        self.assertFalse(result.blockers)

    def test_ready_with_open_questions_when_no_blocking_decision_exists(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(
                evidence_pack=_evidence_pack(
                    j0.EVIDENCE_OBSERVED, j0.EVIDENCE_UNKNOWN
                ),
                open_questions=("Which billing mode is canonical?",),
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_READY_WITH_OPEN_QUESTIONS)
        self.assertTrue(result.draftable)
        self.assertGreaterEqual(len(result.open_questions), 2)

    def test_blocked_product_decisions_required_for_blocking_decisions(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(product_decision_register=({"id": "PD-1", "status": "OPEN"},))
        )

        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertFalse(result.draftable)
        self.assertIn("PD-1 remains OPEN", result.blockers)

    def test_blocked_repo_state_conflict_for_unresolved_conflicts(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(
                gap_report={
                    "kind": j0.ARTIFACT_HLD_GAP_REPORT,
                    "repo_state_conflict": True,
                }
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)
        self.assertFalse(result.draftable)
        self.assertIn("gap report declares repo_state_conflict", result.blockers)

    def test_insufficient_evidence_when_evidence_is_too_weak(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(evidence_pack=_evidence_pack(j0.EVIDENCE_INFERRED))
        )

        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.draftable)
        self.assertEqual(result.accepted_fact_count, 0)

    def test_conflict_is_never_treated_as_accepted_observed_fact(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(evidence_pack=_evidence_pack(j0.EVIDENCE_CONFLICT))
        )

        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)
        self.assertFalse(result.draftable)
        self.assertEqual(result.accepted_fact_count, 0)
        self.assertTrue(any("CONFLICT evidence" in b for b in result.blockers))

    def test_unknown_cannot_become_a_requirement(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(
                candidate_requirements=(
                    {"id": "REQ-1", "evidence_label": j0.EVIDENCE_UNKNOWN},
                )
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.draftable)
        self.assertIn(
            "REQ-1 cannot become a requirement from UNKNOWN evidence",
            result.blockers,
        )

    def test_safety_authority_gaps_block_implementation_planning(self) -> None:
        result = gate.evaluate_hld_draftability(
            _input(safety_authority_gaps=("missing deploy owner",))
        )

        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertFalse(result.draftable)
        self.assertIn(
            "safety/authority gap blocks handoff: missing deploy owner",
            result.blockers,
        )
        self.assertFalse(result.authorizes_implementation)

    def test_journey1_handoff_remains_evidence_gap_input_only(self) -> None:
        result = gate.evaluate_hld_draftability(_input())

        self.assertEqual(result.handoff_kind, j0.HANDOFF_EVIDENCE_AND_GAP_INPUT)
        self.assertTrue(result.journey1_input_only)
        as_dict = result.to_dict()
        self.assertEqual(as_dict["handoff_kind"], j0.HANDOFF_EVIDENCE_AND_GAP_INPUT)
        self.assertTrue(as_dict["journey1_input_only"])

    def test_gate_result_grants_no_approval_authority(self) -> None:
        result = gate.evaluate_hld_draftability(_input())

        self.assertFalse(result.grants_approval_authority)
        self.assertFalse(result.to_dict()["grants_approval_authority"])

    def test_gate_result_grants_no_implementation_authority(self) -> None:
        result = gate.evaluate_hld_draftability(_input())

        self.assertFalse(result.authorizes_implementation)
        self.assertFalse(result.authorizes_work_orders)
        as_dict = result.to_dict()
        self.assertFalse(as_dict["authorizes_implementation"])
        self.assertFalse(as_dict["authorizes_work_orders"])

    def test_module_purity_has_no_runtime_or_target_mechanisms(self) -> None:
        source = inspect.getsource(gate)
        forbidden = (
            "open" + "(",
            "write" + "_text",
            "read" + "_text",
            "sub" + "process",
            "os" + ".system",
            "request" + "s",
            "url" + "lib",
            "Spec" + "Kit",
            "cli" + "ck",
            "arg" + "parse",
            "Typ" + "er",
            "Path" + "(",
        )

        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
