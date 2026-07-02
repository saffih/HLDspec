"""Tests for Journey 0 draftability verdict computation."""
from __future__ import annotations

import inspect
import unittest

from hldspec import journey0_draftability as draftability
from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    DecisionStatus,
    EvidenceItem,
    EvidenceLabel,
    GapItem,
    GapType,
    HldCodeSpecGapReport,
    HldDraftabilityVerdict,
    Journey0Verdict,
    ProductDecision,
    ProductDecisionRegister,
    ProductSurfaceMap,
)


def _evidence(
    evidence_id: str,
    *,
    label: EvidenceLabel = EvidenceLabel.OBSERVED,
) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        source_type="product_capability",
        source_ref=f"{evidence_id}.md",
        source_location=f"{evidence_id}.md:1",
        summary=f"{evidence_id} observed",
        label=label,
        confidence="medium",
    )


def _verdict(
    *,
    evidence_pack: BrownfieldEvidencePack | None = None,
    product_surface_map: ProductSurfaceMap | None = None,
    gap_report: HldCodeSpecGapReport | None = None,
    decision_register: ProductDecisionRegister | None = None,
) -> HldDraftabilityVerdict:
    return draftability.compute_journey0_draftability_verdict(
        evidence_pack=evidence_pack or BrownfieldEvidencePack(),
        product_surface_map=product_surface_map or ProductSurfaceMap(),
        gap_report=gap_report or HldCodeSpecGapReport(),
        decision_register=decision_register or ProductDecisionRegister(),
    )


def _surface() -> ProductSurfaceMap:
    return ProductSurfaceMap(
        observed_capabilities=("User can claim work",),
        source_refs=("E-1",),
    )


class Journey0DraftabilityTests(unittest.TestCase):
    def test_empty_evidence_returns_action(self) -> None:
        result = _verdict()

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_observed_file_only_evidence_returns_action_not_pass(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),))
        )

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_observed_evidence_with_explicit_product_surface_passes(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
        )

        self.assertEqual(result.verdict, Journey0Verdict.PASS)

    def test_pass_is_journey1_only(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
        )

        self.assertTrue(result.journey1_only)

    def test_pass_is_not_implementation_ready(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
        )

        self.assertFalse(result.implementation_ready)

    def test_open_product_decision_blocks(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
            decision_register=ProductDecisionRegister(
                decisions=(
                    ProductDecision(
                        decision_id="PD-1",
                        question="Which source of truth wins?",
                        why_human_owned="source of truth decision",
                        options=("hld", "code"),
                        evidence_refs=("E-1",),
                        recommended_default_if_any=None,
                        decision_status=DecisionStatus.OPEN,
                        owner="human",
                    ),
                )
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("PD-1", result.blocking_items)
        self.assertIn("PD-1", result.required_human_decisions)

    def test_hld_code_conflict_gap_blocks(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
            gap_report=HldCodeSpecGapReport(
                gaps=(
                    GapItem(
                        gap_id="G-1",
                        gap_type=GapType.HLD_CODE_CONFLICT,
                        description="HLD and code disagree",
                    ),
                )
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("G-1", result.blocking_items)

    def test_safety_authority_gap_blocks(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
            gap_report=HldCodeSpecGapReport(
                gaps=(
                    GapItem(
                        gap_id="G-1",
                        gap_type=GapType.SAFETY_AUTHORITY_GAP,
                        description="Approval owner unclear",
                    ),
                )
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("G-1", result.blocking_items)

    def test_human_decision_gap_text_blocks(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
            gap_report=HldCodeSpecGapReport(
                gaps=(
                    GapItem(
                        gap_id="G-1",
                        gap_type=GapType.HLD_GAP,
                        description="needs owner",
                        disposition="human_decision_required",
                    ),
                )
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("G-1", result.blocking_items)

    def test_non_blocking_gap_returns_action(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
            gap_report=HldCodeSpecGapReport(
                gaps=(
                    GapItem(
                        gap_id="G-1",
                        gap_type=GapType.CODE_GAP,
                        description="missing test evidence",
                        disposition="continue_discovery",
                    ),
                )
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_inferred_only_evidence_returns_action(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", label=EvidenceLabel.INFERRED),)
            ),
            product_surface_map=_surface(),
        )

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_unknown_only_evidence_returns_action(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", label=EvidenceLabel.UNKNOWN),)
            ),
            product_surface_map=_surface(),
        )

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_conflict_evidence_blocks(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(
                evidence=(_evidence("E-1", label=EvidenceLabel.CONFLICT),)
            ),
            product_surface_map=_surface(),
        )

        self.assertEqual(result.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("E-1", result.blocking_items)

    def test_product_decision_required_evidence_blocks(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", label=EvidenceLabel.PRODUCT_DECISION_REQUIRED),
                )
            ),
            product_surface_map=_surface(),
        )

        self.assertEqual(result.verdict, Journey0Verdict.BLOCKED)
        self.assertIn("E-1", result.blocking_items)

    def test_accepted_evidence_refs_include_observed_evidence_only(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(
                evidence=(
                    _evidence("E-1", label=EvidenceLabel.OBSERVED),
                    _evidence("E-2", label=EvidenceLabel.INFERRED),
                    _evidence("E-3", label=EvidenceLabel.UNKNOWN),
                )
            ),
            product_surface_map=_surface(),
        )

        self.assertEqual(result.accepted_evidence_refs, ("E-1",))

    def test_product_surface_with_only_unknowns_returns_action(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=ProductSurfaceMap(unknowns=("surface unclear",)),
        )

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_explicit_observed_capability_can_support_pass(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                source_refs=("E-1",),
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.PASS)

    def test_known_limit_can_support_pass_when_linked_to_observed_evidence(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=ProductSurfaceMap(
                known_limits=("single local store",),
                source_refs=("E-1",),
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.PASS)

    def test_unlinked_product_surface_returns_action(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=ProductSurfaceMap(
                observed_capabilities=("User can claim work",),
                source_refs=("OTHER",),
            ),
        )

        self.assertEqual(result.verdict, Journey0Verdict.ACTION)

    def test_output_type_is_hld_draftability_verdict(self) -> None:
        self.assertIsInstance(_verdict(), HldDraftabilityVerdict)

    def test_no_hld_update_plan_output(self) -> None:
        result = _verdict().to_dict()

        self.assertEqual(result["artifact"], "hld_draftability_verdict")
        self.assertNotIn("hld_sections_to_create_or_update", result)
        self.assertNotIn("evidence_refs_per_section", result)

    def test_safe_next_action_avoids_later_journey_and_execution_terms(self) -> None:
        result = _verdict(
            evidence_pack=BrownfieldEvidencePack(evidence=(_evidence("E-1"),)),
            product_surface_map=_surface(),
        )

        forbidden = (
            "SpecKit",
            "Journey 2",
            "Journey 3",
            "implementation",
            "target mutation",
            "backlog",
        )
        for token in forbidden:
            self.assertNotIn(token, result.safe_next_action)

    def test_boundary_tokens_do_not_appear_in_draftability_module(self) -> None:
        source = inspect.getsource(draftability)

        forbidden_tokens = (
            "subprocess",
            "argparse",
            "click",
            "Path(",
            "open(",
            "read_text",
            "write_text",
            "SpecKit",
            "speckit",
            "git",
            "HldUpdatePlan",
            "collect_journey0",
            "build_journey0_conservative_artifacts",
            "build_journey0_product_surface_map",
            "backlog",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
