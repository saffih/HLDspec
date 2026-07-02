"""Journey 0 draftability verdict computation.

Slice D1 only: compute an HLD Draftability Verdict from already-built typed
Journey 0 artifacts. This module does not generate update plans, inspect
targets, call toolchains, or write artifacts.
"""
from __future__ import annotations

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    DecisionStatus,
    EvidenceLabel,
    GapType,
    HldCodeSpecGapReport,
    HldDraftabilityVerdict,
    Journey0Verdict,
    ProductDecisionRegister,
    ProductSurfaceMap,
)

_BLOCKED_NEXT_ACTION = (
    "Resolve human-owned product/source-of-truth/authority decisions before Journey 1."
)
_ACTION_NEXT_ACTION = (
    "Collect or clarify Journey 0 evidence and explicit product-surface evidence "
    "before Journey 1 HLD authoring."
)
_PASS_NEXT_ACTION = (
    "Proceed to Journey 1 HLD authoring/hardening using accepted Journey 0 "
    "evidence and explicit product-surface evidence only."
)
_PRODUCT_SURFACE_SOURCE_TYPES = frozenset(
    {
        "product_capability",
        "product_actor",
        "product_input_output",
        "product_workflow",
        "product_limit",
    }
)


def compute_journey0_draftability_verdict(
    *,
    evidence_pack: BrownfieldEvidencePack,
    product_surface_map: ProductSurfaceMap,
    gap_report: HldCodeSpecGapReport,
    decision_register: ProductDecisionRegister,
) -> HldDraftabilityVerdict:
    """Compute a conservative Journey 0 draftability verdict."""

    blocking_items = _blocking_items(evidence_pack, gap_report, decision_register)
    accepted_refs = _observed_evidence_refs(evidence_pack)
    required_decisions = tuple(
        decision.decision_id
        for decision in decision_register.decisions
        if decision.decision_status
        in {DecisionStatus.OPEN, DecisionStatus.DEFERRED}
    )

    if blocking_items:
        return HldDraftabilityVerdict(
            verdict=Journey0Verdict.BLOCKED,
            reason="Journey 0 has unresolved human-owned decisions, conflicts, or authority gaps.",
            blocking_items=blocking_items,
            accepted_evidence_refs=accepted_refs,
            required_human_decisions=required_decisions,
            safe_next_action=_BLOCKED_NEXT_ACTION,
        )

    if _requires_more_action(
        evidence_pack,
        product_surface_map,
        gap_report,
    ):
        return HldDraftabilityVerdict(
            verdict=Journey0Verdict.ACTION,
            reason="Journey 0 evidence or explicit product-surface evidence is insufficient for responsible HLD authoring.",
            accepted_evidence_refs=accepted_refs,
            safe_next_action=_ACTION_NEXT_ACTION,
        )

    return HldDraftabilityVerdict(
        verdict=Journey0Verdict.PASS,
        reason="Accepted observed evidence and explicit product-surface evidence are sufficient for Journey 1.",
        accepted_evidence_refs=accepted_refs,
        safe_next_action=_PASS_NEXT_ACTION,
    )


def _blocking_items(
    evidence_pack: BrownfieldEvidencePack,
    gap_report: HldCodeSpecGapReport,
    decision_register: ProductDecisionRegister,
) -> tuple[str, ...]:
    blockers: list[str] = []
    blockers.extend(
        decision.decision_id
        for decision in decision_register.decisions
        if decision.decision_status
        in {DecisionStatus.OPEN, DecisionStatus.DEFERRED}
    )
    blockers.extend(
        gap.gap_id
        for gap in gap_report.gaps
        if gap.gap_type
        in {GapType.HLD_CODE_CONFLICT, GapType.SAFETY_AUTHORITY_GAP}
        or _requires_human_decision(gap.disposition)
        or _requires_human_decision(gap.required_decision_or_next_action)
    )
    blockers.extend(
        item.evidence_id
        for item in evidence_pack.evidence
        if item.label
        in {EvidenceLabel.CONFLICT, EvidenceLabel.PRODUCT_DECISION_REQUIRED}
    )
    return tuple(blockers)


def _requires_human_decision(text: str) -> bool:
    normalized = text.lower()
    has_owner_word = any(
        token in normalized for token in ("human", "product", "authority")
    )
    has_decision_word = "decision" in normalized or "required" in normalized
    return has_owner_word and has_decision_word


def _requires_more_action(
    evidence_pack: BrownfieldEvidencePack,
    product_surface_map: ProductSurfaceMap,
    gap_report: HldCodeSpecGapReport,
) -> bool:
    accepted_refs = _observed_evidence_refs(evidence_pack)
    if not evidence_pack.evidence:
        return True
    if not accepted_refs:
        return True
    if not _has_explicit_product_surface(product_surface_map, evidence_pack):
        return True
    if gap_report.gaps:
        return True
    return _only_inferred_or_unknown(evidence_pack)


def _observed_evidence_refs(evidence_pack: BrownfieldEvidencePack) -> tuple[str, ...]:
    return tuple(
        item.evidence_id
        for item in evidence_pack.evidence
        if item.label == EvidenceLabel.OBSERVED
    )


def _has_explicit_product_surface(
    product_surface_map: ProductSurfaceMap,
    evidence_pack: BrownfieldEvidencePack,
) -> bool:
    if not _has_surface_field(product_surface_map):
        return False
    return any(
        item.evidence_id in product_surface_map.source_refs
        and item.label == EvidenceLabel.OBSERVED
        and item.source_type in _PRODUCT_SURFACE_SOURCE_TYPES
        for item in evidence_pack.evidence
    )


def _has_surface_field(product_surface_map: ProductSurfaceMap) -> bool:
    return any(
        (
            product_surface_map.observed_capabilities,
            product_surface_map.observed_users_or_actors,
            product_surface_map.observed_inputs_outputs,
            product_surface_map.observed_workflows,
            product_surface_map.known_limits,
        )
    )


def _only_inferred_or_unknown(evidence_pack: BrownfieldEvidencePack) -> bool:
    return all(
        item.label in {EvidenceLabel.INFERRED, EvidenceLabel.UNKNOWN}
        for item in evidence_pack.evidence
    )
