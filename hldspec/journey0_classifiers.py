"""Conservative Journey 0 evidence classification.

Slice C only: transform a BrownfieldEvidencePack into typed Journey 0
inventory, gap, and human-decision artifacts. This module is pure and works
only from the provided typed evidence pack.
"""
from __future__ import annotations

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    DecisionStatus,
    EvidenceItem,
    EvidenceLabel,
    GapItem,
    GapType,
    HldCodeSpecGapReport,
    ProductDecision,
    ProductDecisionRegister,
    SpecInventory,
    SpecInventoryItem,
    SpecStatus,
)


def build_journey0_conservative_artifacts(
    evidence_pack: BrownfieldEvidencePack,
) -> tuple[SpecInventory, HldCodeSpecGapReport, ProductDecisionRegister]:
    """Build conservative typed artifacts from collected Journey 0 evidence.

    The safe default is preservation, not interpretation. Old spec resources are
    inventoried with UNKNOWN status. Explicit conflict or human-decision labels
    are surfaced as gap/decision artifacts without resolving them.
    """

    return (
        SpecInventory(specs=_spec_inventory_items(evidence_pack.evidence)),
        HldCodeSpecGapReport(gaps=_gap_items(evidence_pack.evidence)),
        ProductDecisionRegister(decisions=_product_decisions(evidence_pack.evidence)),
    )


def _spec_inventory_items(
    evidence: tuple[EvidenceItem, ...],
) -> tuple[SpecInventoryItem, ...]:
    items: list[SpecInventoryItem] = []
    for index, item in enumerate(
        (entry for entry in evidence if entry.source_type == "old_spec_state"),
        start=1,
    ):
        items.append(
            SpecInventoryItem(
                spec_id=f"SPEC-INVENTORY-{index:03d}",
                location=item.source_ref,
                status=SpecStatus.UNKNOWN,
                summary=item.summary,
                source_refs=(item.evidence_id,),
            )
        )
    return tuple(items)


def _gap_items(evidence: tuple[EvidenceItem, ...]) -> tuple[GapItem, ...]:
    gaps: list[GapItem] = []
    for index, item in enumerate(
        (entry for entry in evidence if entry.label == EvidenceLabel.CONFLICT),
        start=1,
    ):
        gaps.append(
            GapItem(
                gap_id=f"GAP-{index:03d}",
                gap_type=GapType.HLD_CODE_CONFLICT,
                description=f"Explicit conflict evidence requires human review: {item.summary}",
                evidence_refs=(item.evidence_id,),
                disposition="human_review_required",
                required_decision_or_next_action="Resolve the explicit conflict before relying on it.",
            )
        )
    return tuple(gaps)


def _product_decisions(evidence: tuple[EvidenceItem, ...]) -> tuple[ProductDecision, ...]:
    decisions: list[ProductDecision] = []
    for index, item in enumerate(
        (
            entry
            for entry in evidence
            if entry.label == EvidenceLabel.PRODUCT_DECISION_REQUIRED
        ),
        start=1,
    ):
        decisions.append(
            ProductDecision(
                decision_id=f"PRODUCT-DECISION-{index:03d}",
                question=f"Human decision required for {item.source_ref}",
                why_human_owned=(
                    "The evidence explicitly marks this as PRODUCT_DECISION_REQUIRED."
                ),
                options=(),
                evidence_refs=(item.evidence_id,),
                recommended_default_if_any=None,
                decision_status=DecisionStatus.OPEN,
                owner="human",
            )
        )
    return tuple(decisions)
