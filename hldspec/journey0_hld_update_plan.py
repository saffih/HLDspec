"""Journey 0 HLD update plan generation.

Slice D2 only: build a typed HldUpdatePlan from existing typed Journey 0
artifacts. This module is pure and does not write an HLD or perform downstream
workflow actions.
"""
from __future__ import annotations

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    DecisionStatus,
    GapType,
    HldCodeSpecGapReport,
    HldDraftabilityVerdict,
    HldUpdatePlan,
    Journey0Verdict,
    ProductDecisionRegister,
    ProductSurfaceMap,
    SpecInventory,
    SpecStatus,
)

_SECTION_SOURCE_TYPES = (
    ("Product capabilities", "observed_capabilities", "product_capability"),
    ("Users and actors", "observed_users_or_actors", "product_actor"),
    ("Inputs and outputs", "observed_inputs_outputs", "product_input_output"),
    ("Workflows", "observed_workflows", "product_workflow"),
    ("Known limits", "known_limits", "product_limit"),
)


def build_journey0_hld_update_plan(
    *,
    draftability_verdict: HldDraftabilityVerdict,
    evidence_pack: BrownfieldEvidencePack,
    product_surface_map: ProductSurfaceMap,
    spec_inventory: SpecInventory,
    gap_report: HldCodeSpecGapReport,
    decision_register: ProductDecisionRegister,
) -> HldUpdatePlan:
    """Build a conservative HLD update plan from typed Journey 0 artifacts."""

    evidence_refs_per_section = _evidence_refs_per_section(
        draftability_verdict=draftability_verdict,
        product_surface_map=product_surface_map,
        evidence_pack=evidence_pack,
    )
    sections = tuple(evidence_refs_per_section)

    return HldUpdatePlan(
        hld_sections_to_create_or_update=sections,
        evidence_refs_per_section=evidence_refs_per_section,
        decisions_required_before_writing=_decisions_required_before_writing(
            draftability_verdict,
            gap_report,
            decision_register,
        ),
        known_stale_material_to_exclude=_known_stale_material(spec_inventory),
        open_questions_to_carry_forward=_open_questions(
            draftability_verdict,
            product_surface_map,
            spec_inventory,
            gap_report,
            decision_register,
            evidence_pack,
        ),
    )


def _evidence_refs_per_section(
    *,
    draftability_verdict: HldDraftabilityVerdict,
    product_surface_map: ProductSurfaceMap,
    evidence_pack: BrownfieldEvidencePack,
) -> dict[str, tuple[str, ...]]:
    if draftability_verdict.verdict == Journey0Verdict.BLOCKED:
        return {}

    refs_per_section: dict[str, tuple[str, ...]] = {}
    for section, field_name, source_type in _SECTION_SOURCE_TYPES:
        if not getattr(product_surface_map, field_name):
            continue
        section_refs = _section_evidence_refs(
            section_source_type=source_type,
            draftability_verdict=draftability_verdict,
            product_surface_map=product_surface_map,
            evidence_pack=evidence_pack,
        )
        if section_refs:
            refs_per_section[section] = section_refs
    return refs_per_section


def _section_evidence_refs(
    *,
    section_source_type: str,
    draftability_verdict: HldDraftabilityVerdict,
    product_surface_map: ProductSurfaceMap,
    evidence_pack: BrownfieldEvidencePack,
) -> tuple[str, ...]:
    accepted = set(draftability_verdict.accepted_evidence_refs)
    map_refs = set(product_surface_map.source_refs)
    return tuple(
        item.evidence_id
        for item in evidence_pack.evidence
        if item.evidence_id in accepted
        and item.evidence_id in map_refs
        and item.source_type == section_source_type
    )


def _decisions_required_before_writing(
    draftability_verdict: HldDraftabilityVerdict,
    gap_report: HldCodeSpecGapReport,
    decision_register: ProductDecisionRegister,
) -> tuple[str, ...]:
    required: list[str] = []
    for decision_id in draftability_verdict.required_human_decisions:
        _append_unique(required, decision_id)
    for decision in decision_register.decisions:
        if decision.decision_status in {DecisionStatus.OPEN, DecisionStatus.DEFERRED}:
            _append_unique(required, decision.decision_id)
    for gap in gap_report.gaps:
        if _blocking_gap(gap.gap_type, gap.disposition, gap.required_decision_or_next_action):
            _append_unique(required, gap.gap_id)
    return tuple(required)


def _known_stale_material(spec_inventory: SpecInventory) -> tuple[str, ...]:
    stale_statuses = {
        SpecStatus.STALE,
        SpecStatus.SUPERSEDED,
        SpecStatus.CONFLICTING,
    }
    return tuple(
        item.spec_id
        for item in spec_inventory.specs
        if item.status in stale_statuses
    )


def _open_questions(
    draftability_verdict: HldDraftabilityVerdict,
    product_surface_map: ProductSurfaceMap,
    spec_inventory: SpecInventory,
    gap_report: HldCodeSpecGapReport,
    decision_register: ProductDecisionRegister,
    evidence_pack: BrownfieldEvidencePack,
) -> tuple[str, ...]:
    questions: list[str] = []
    for unknown in product_surface_map.unknowns:
        _append_unique(questions, unknown)
    for item in spec_inventory.specs:
        if item.status in {SpecStatus.UNKNOWN, SpecStatus.PARTIAL}:
            _append_unique(questions, item.spec_id)
    for gap in gap_report.gaps:
        if _blocking_gap(gap.gap_type, gap.disposition, gap.required_decision_or_next_action):
            _append_unique(
                questions,
                gap.required_decision_or_next_action or gap.description or gap.gap_id,
            )
        else:
            _append_unique(questions, gap.gap_id)
    if draftability_verdict.verdict in {Journey0Verdict.ACTION, Journey0Verdict.BLOCKED}:
        for item in draftability_verdict.blocking_items:
            _append_unique(questions, item)
    if not evidence_pack.evidence and draftability_verdict.verdict != Journey0Verdict.PASS:
        _append_unique(questions, "No accepted Journey 0 evidence is available.")
    return tuple(questions)


def _blocking_gap(
    gap_type: GapType,
    disposition: str,
    next_action: str,
) -> bool:
    if gap_type in {GapType.HLD_CODE_CONFLICT, GapType.SAFETY_AUTHORITY_GAP}:
        return True
    text = f"{disposition} {next_action}".lower()
    has_owner_word = any(token in text for token in ("human", "product", "authority"))
    has_decision_word = "decision" in text or "required" in text
    return has_owner_word and has_decision_word


def _append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)
