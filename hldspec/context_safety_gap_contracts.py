"""Brownfield Context Safety and Gap Ledger contracts -- pure validation.

For large-evidence, repo-archaeology, HLD/SDD, product-recovery, state-model
recovery, persistence-safety recovery, or implementation-planning workflows,
these contracts enforce mandatory worker decomposition, compact receipts,
evidence mapping, gap ledger completeness, and RunSkeptic reconciliation.

Load-bearing rules:

- No gap may disappear: every worker gap must appear in the final ledger.
- Lost gaps and missing coverage are correctness failures.
- Gaps must be classified by type before build planning.
- BLOCKING gaps make the plan unsafe.
- CONFLICT gaps must be surfaced in the verdict.
- ASSUMED_FOR_NOW requires explicit assumption text.
- NEEDS_OWNER requires blocking=True or explicit owner_decision_scope.
- Worker receipts must be compact (bounded byte limit).
- Lead synthesis must not ingest unbounded raw context.
- Evidence not inspected must be recorded, not omitted.
- RunSkeptic reconciliation of worker gaps to final ledger is required.
- This module grants no approval, implementation, work-order, speckit
  execution, product-decision, or target-mutation authority.

Pure functions only: no filesystem, no child processes, no network, no CLI.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Gap classification
# ---------------------------------------------------------------------------

class GapType(str, Enum):
    PRODUCT_GAP = "PRODUCT_GAP"
    STATE_MODEL_GAP = "STATE_MODEL_GAP"
    PERSISTENCE_GAP = "PERSISTENCE_GAP"
    MIGRATION_GAP = "MIGRATION_GAP"
    DATA_SAFETY_GAP = "DATA_SAFETY_GAP"
    UI_FLOW_GAP = "UI_FLOW_GAP"
    TEST_GAP = "TEST_GAP"
    ARCHITECTURE_GAP = "ARCHITECTURE_GAP"
    CONTRADICTION = "CONTRADICTION"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class GapStatus(str, Enum):
    RESOLVED_BY_EVIDENCE = "RESOLVED_BY_EVIDENCE"
    NEEDS_OWNER = "NEEDS_OWNER"
    SAFE_TO_DEFER = "SAFE_TO_DEFER"
    ASSUMED_FOR_NOW = "ASSUMED_FOR_NOW"
    BLOCKING = "BLOCKING"
    CONFLICT = "CONFLICT"


VALID_GAP_TYPES: frozenset[str] = frozenset(t.value for t in GapType)
VALID_GAP_STATUSES: frozenset[str] = frozenset(s.value for s in GapStatus)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GapItem:
    gap_id: str
    gap_type: GapType
    status: GapStatus
    description: str
    source_worker: str
    blocking: bool = False
    assumption_text: str = ""
    owner_decision_scope: str = ""


@dataclass(frozen=True)
class WorkerReceipt:
    worker_id: str
    evidence_inspected: tuple[str, ...]
    findings: tuple[str, ...]
    gaps: tuple[str, ...]
    confidence: str
    evidence_not_inspected: tuple[str, ...] | None = None
    raw_size_bytes: int = 0


@dataclass(frozen=True)
class EvidenceMap:
    inspected: tuple[str, ...]
    not_inspected: tuple[str, ...] | None = None
    owner_declared_not_required: tuple[str, ...] = ()


@dataclass(frozen=True)
class GapLedger:
    gaps: tuple[GapItem, ...]


@dataclass(frozen=True)
class RunSkepticGapReconciliation:
    reconciled: bool
    notes: str = ""


@dataclass(frozen=True)
class ContextSafetyRules:
    max_worker_receipt_bytes: int = 50_000
    max_lead_context_bytes: int = 200_000
    min_worker_count: int = 2
    require_worker_decomposition: bool = True
    require_evidence_map: bool = True
    require_gap_ledger: bool = True
    require_skeptic_reconciliation: bool = True
    grants_approval_authority: bool = False
    grants_implementation_authority: bool = False
    grants_work_order_authority: bool = False
    grants_speckit_execution_authority: bool = False
    grants_product_decision_authority: bool = False
    grants_target_mutation_authority: bool = False


@dataclass(frozen=True)
class ContextSafetyVerdict:
    safe: bool
    blockers: tuple[str, ...]
    conflicts: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Validation — Idiom A: blocker functions returning list[str]
# ---------------------------------------------------------------------------

def gap_item_blockers(item: GapItem) -> list[str]:
    """Validate a single gap item. Returns blocker strings."""
    blockers: list[str] = []
    if item.status == GapStatus.ASSUMED_FOR_NOW and not item.assumption_text:
        blockers.append(
            f"Gap {item.gap_id}: ASSUMED_FOR_NOW requires assumption_text"
        )
    if item.status == GapStatus.NEEDS_OWNER:
        if not item.blocking and not item.owner_decision_scope:
            blockers.append(
                f"Gap {item.gap_id}: NEEDS_OWNER requires "
                f"blocking=True or owner_decision_scope"
            )
    return blockers


def authority_grants(rules: ContextSafetyRules) -> list[str]:
    """Returns any authority grants that are set. Must be empty for safe contracts."""
    grants: list[str] = []
    if rules.grants_approval_authority:
        grants.append("approval")
    if rules.grants_implementation_authority:
        grants.append("implementation")
    if rules.grants_work_order_authority:
        grants.append("work_order")
    if rules.grants_speckit_execution_authority:
        grants.append("speckit_execution")
    if rules.grants_product_decision_authority:
        grants.append("product_decision")
    if rules.grants_target_mutation_authority:
        grants.append("target_mutation")
    return grants


def gap_ledger_blockers(
    ledger: GapLedger,
    worker_receipts: tuple[WorkerReceipt, ...],
    reconciliation: RunSkepticGapReconciliation | None,
    evidence_map: EvidenceMap | None,
    rules: ContextSafetyRules,
) -> list[str]:
    """Validate the full gap ledger. Returns blocker strings.

    Recomputes worker-gap coverage from receipts — never trusts stored fields.
    """
    blockers: list[str] = []

    # Per-item validation
    for gap in ledger.gaps:
        blockers.extend(gap_item_blockers(gap))

    # No gap may remain unclassified
    for gap in ledger.gaps:
        if gap.gap_type == GapType.UNKNOWN:
            blockers.append(
                f"Gap {gap.gap_id}: remains unclassified (type UNKNOWN)"
            )

    # BLOCKING gaps make plan unsafe
    for gap in ledger.gaps:
        if gap.status == GapStatus.BLOCKING:
            blockers.append(
                f"Gap {gap.gap_id}: BLOCKING gap makes plan unsafe"
            )

    # CONFLICT gaps must be surfaced
    for gap in ledger.gaps:
        if gap.status == GapStatus.CONFLICT:
            blockers.append(
                f"Gap {gap.gap_id}: CONFLICT gap must be resolved"
            )

    # Recompute: every worker gap must appear in final ledger
    all_worker_gaps: set[str] = set()
    for receipt in worker_receipts:
        all_worker_gaps.update(receipt.gaps)
    ledger_gap_ids = {gap.gap_id for gap in ledger.gaps}
    for gap_id in sorted(all_worker_gaps - ledger_gap_ids):
        blockers.append(f"Worker gap {gap_id} missing from final ledger")

    # Worker decomposition requires multiple bounded workers
    if rules.require_worker_decomposition:
        if len(worker_receipts) < rules.min_worker_count:
            blockers.append(
                f"Worker decomposition requires at least {rules.min_worker_count} "
                f"workers but got {len(worker_receipts)}"
            )

    # Gap ledger must not be empty
    if rules.require_gap_ledger and not ledger.gaps:
        blockers.append("Gap ledger is required but empty")

    # RunSkeptic reconciliation required and must have passed
    if rules.require_skeptic_reconciliation:
        if reconciliation is None:
            blockers.append(
                "RunSkeptic reconciliation is required before final verdict"
            )
        elif not reconciliation.reconciled:
            blockers.append(
                "RunSkeptic reconciliation failed"
            )

    # Evidence map required
    if rules.require_evidence_map and evidence_map is None:
        blockers.append("Evidence map is required")

    # Evidence not inspected must be recorded (None = not recorded)
    if evidence_map is not None and evidence_map.not_inspected is None:
        blockers.append(
            "Evidence not inspected must be recorded in evidence map"
        )

    # Owner-declared non-required evidence must be traceable
    if evidence_map is not None and evidence_map.owner_declared_not_required:
        recon_notes = reconciliation.notes if reconciliation is not None else ""
        for item in evidence_map.owner_declared_not_required:
            in_ledger = any(
                item in g.description for g in ledger.gaps
            )
            in_recon = item in recon_notes
            if not in_ledger and not in_recon:
                blockers.append(
                    f"Owner-declared non-required evidence '{item}' is not "
                    f"traceable in gap ledger or reconciliation notes"
                )

    # Worker receipt compactness
    for receipt in worker_receipts:
        if receipt.raw_size_bytes > rules.max_worker_receipt_bytes:
            blockers.append(
                f"Worker {receipt.worker_id} receipt exceeds compactness limit: "
                f"{receipt.raw_size_bytes} > {rules.max_worker_receipt_bytes}"
            )

    # Worker evidence_not_inspected must be recorded
    for receipt in worker_receipts:
        if receipt.evidence_not_inspected is None:
            blockers.append(
                f"Worker {receipt.worker_id}: evidence_not_inspected not recorded"
            )

    # Lead context limit
    total_receipt_bytes = sum(r.raw_size_bytes for r in worker_receipts)
    if total_receipt_bytes > rules.max_lead_context_bytes:
        blockers.append(
            f"Total worker receipt size exceeds lead context limit: "
            f"{total_receipt_bytes} > {rules.max_lead_context_bytes}"
        )

    return blockers


def context_safety_verdict(
    ledger: GapLedger,
    worker_receipts: tuple[WorkerReceipt, ...],
    reconciliation: RunSkepticGapReconciliation | None,
    evidence_map: EvidenceMap | None,
    rules: ContextSafetyRules | None = None,
) -> ContextSafetyVerdict:
    """Compute the final context safety verdict."""
    if rules is None:
        rules = ContextSafetyRules()

    all_blockers = gap_ledger_blockers(
        ledger, worker_receipts, reconciliation, evidence_map, rules,
    )

    auth = authority_grants(rules)
    if auth:
        all_blockers.append(
            f"Authority grants must be empty: {', '.join(auth)}"
        )

    conflicts = tuple(
        gap.gap_id for gap in ledger.gaps
        if gap.status == GapStatus.CONFLICT
    )

    return ContextSafetyVerdict(
        safe=len(all_blockers) == 0,
        blockers=tuple(all_blockers),
        conflicts=conflicts,
    )
