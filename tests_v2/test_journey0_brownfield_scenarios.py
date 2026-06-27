"""Synthetic Journey 0 brownfield scenarios for the draftability gate.

These are structured inputs only. They approximate messy brownfield discovery
signals without inspecting any real repository or producing scanner behavior.
"""
from __future__ import annotations

import unittest

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_draftability_gate as gate


def _evidence_pack(*items: dict) -> dict:
    return {"kind": j0.ARTIFACT_BROWNFIELD_EVIDENCE_PACK, "evidence": list(items)}


def _observed(statement: str) -> dict:
    return {"label": j0.EVIDENCE_OBSERVED, "statement": statement}


def _inferred(statement: str) -> dict:
    return {"label": j0.EVIDENCE_INFERRED, "statement": statement}


def _unknown(statement: str) -> dict:
    return {"label": j0.EVIDENCE_UNKNOWN, "statement": statement}


def _conflict(statement: str) -> dict:
    return {"label": j0.EVIDENCE_CONFLICT, "statement": statement}


def _product_decision(statement: str) -> dict:
    return {"label": j0.EVIDENCE_PRODUCT_DECISION_REQUIRED, "statement": statement}


def _result(
    *,
    evidence: tuple[dict, ...],
    decisions: tuple[dict, ...] = (),
    gap_report: dict | None = None,
    questions: tuple[str, ...] = (),
    requirements: tuple[dict, ...] = (),
    safety_gaps: tuple[str, ...] = (),
) -> gate.DraftabilityResult:
    return gate.evaluate_hld_draftability(
        gate.DraftabilityInput(
            evidence_pack=_evidence_pack(*evidence),
            product_decision_register=decisions,
            gap_report=gap_report or {"kind": j0.ARTIFACT_HLD_GAP_REPORT},
            open_questions=questions,
            candidate_requirements=requirements,
            safety_authority_gaps=safety_gaps,
        )
    )


class Journey0BrownfieldScenarioTests(unittest.TestCase):
    def test_clean_enough_to_draft_from_observed_product_code_spec_evidence(self) -> None:
        result = _result(
            evidence=(
                _observed("product exposes a run dashboard"),
                _observed("code has a resumable job model"),
                _observed("spec fragment describes operator review"),
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertTrue(result.draftable)
        self.assertEqual(result.accepted_fact_count, 3)

    def test_open_questions_are_draftable_when_non_blocking(self) -> None:
        result = _result(
            evidence=(
                _observed("product has job history"),
                _observed("tests cover run restart display"),
                _unknown("exact retention period is not documented"),
            ),
            questions=("confirm retention wording during Journey 1",),
        )

        self.assertEqual(result.verdict, j0.VERDICT_READY_WITH_OPEN_QUESTIONS)
        self.assertTrue(result.draftable)
        self.assertIn("confirm retention wording during Journey 1", result.open_questions)

    def test_product_decisions_block_hld_draftability(self) -> None:
        result = _result(
            evidence=(
                _observed("library entrypoints and terminal commands both exist"),
                _product_decision("source-of-truth owner is unresolved"),
            ),
            decisions=(
                {"id": "PD-source-owner", "status": "OPEN"},
                {"id": "PD-product-identity", "status": "OPEN"},
                {"id": "PD-resume-model", "status": "PRODUCT_DECISION_REQUIRED"},
            ),
        )

        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertFalse(result.draftable)
        self.assertIn("PD-source-owner remains OPEN", result.blockers)
        self.assertTrue(
            any("source-of-truth owner is unresolved" in b for b in result.blockers)
        )

    def test_code_spec_hld_conflict_blocks_hld_draftability(self) -> None:
        result = _result(
            evidence=(
                _observed("HLD fragment says external controller owns run state"),
                _observed("code records lifecycle in local session state"),
                _conflict("state ownership disagrees across HLD and code evidence"),
            ),
            gap_report={
                "kind": j0.ARTIFACT_HLD_GAP_REPORT,
                "repo_state_conflict": True,
            },
        )

        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)
        self.assertFalse(result.draftable)
        self.assertIn("gap report declares repo_state_conflict", result.blockers)

    def test_insufficient_evidence_when_only_unknowns_and_inferences_exist(self) -> None:
        result = _result(
            evidence=(
                _unknown("product owner is not visible in available notes"),
                _inferred("resume may exist because run IDs appear in logs"),
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertFalse(result.draftable)
        self.assertEqual(result.accepted_fact_count, 0)

    def test_safety_authority_gap_blocks_unsafe_handoff(self) -> None:
        result = _result(
            evidence=(_observed("blocked run records exist"),),
            safety_gaps=(
                "unclear whether an agent may resume blocked runs",
                "transition approver is not named",
            ),
        )

        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertFalse(result.draftable)
        self.assertTrue(
            any("transition approver is not named" in b for b in result.blockers)
        )

    def test_positive_evidence_cannot_launder_unresolved_conflict(self) -> None:
        result = _result(
            evidence=(
                _observed("dashboard routes are implemented"),
                _observed("test suite describes a resumable flow"),
                _conflict("two product docs disagree on who owns run recovery"),
            )
        )

        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)
        self.assertFalse(result.draftable)
        self.assertEqual(result.accepted_fact_count, 2)

    def test_unknown_backed_requirement_is_not_accepted(self) -> None:
        result = _result(
            evidence=(_observed("run records exist"),),
            requirements=(
                {
                    "id": "REQ-owner-can-resume",
                    "evidence_label": j0.EVIDENCE_UNKNOWN,
                },
            ),
        )

        self.assertNotEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertIn(
            "REQ-owner-can-resume cannot become a requirement from UNKNOWN evidence",
            result.blockers,
        )

    def test_journey1_handoff_remains_evidence_gap_input_only(self) -> None:
        result = _result(evidence=(_observed("product has run history"),))
        payload = result.to_dict()

        self.assertEqual(payload["handoff_kind"], j0.HANDOFF_EVIDENCE_AND_GAP_INPUT)
        self.assertTrue(payload["journey1_input_only"])
        self.assertFalse(payload["grants_approval_authority"])
        self.assertFalse(payload["authorizes_implementation"])
        self.assertFalse(payload["authorizes_work_orders"])
        self.assertNotIn("approval", payload)
        self.assertNotIn("work_orders", payload)


if __name__ == "__main__":
    unittest.main()
