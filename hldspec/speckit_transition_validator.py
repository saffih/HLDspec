"""Pure validator for SpecKit phase transitions (no execution, no IO).

Validates a TransitionRequest against declared PhaseReceipts and context
flags. Returns a ValidationResult with a fail-closed status. Does not
execute SpecKit, mint receipts, write files, or mutate any state.

Implements the contract in docs/SPECKIT_HELPER_EXECUTION_CONTRACT.md.
"""
from __future__ import annotations

from dataclasses import dataclass

CANONICAL_PHASES = ("specify", "plan", "tasks", "analyze", "implementation")

RECEIPT_MAX_AGE_SECONDS = 86400


@dataclass(frozen=True)
class PhaseReceipt:
    target_id: str
    source_evidence_sha: str
    phase: str
    created_at: float


@dataclass(frozen=True)
class TransitionRequest:
    target_id: str
    from_phase: str
    to_phase: str
    manual_fallback: bool = False


@dataclass(frozen=True)
class ValidationResult:
    status: str
    reason: str


def _stop(code: str, reason: str) -> ValidationResult:
    return ValidationResult(status=f"STOP_{code}", reason=reason)


def validate_speckit_transition(
    request: TransitionRequest,
    receipts: list[PhaseReceipt],
    *,
    speckit_available: bool,
    human_approval: bool,
    now: float | None = None,
) -> ValidationResult:
    if not speckit_available:
        return _stop("SKILL_UNAVAILABLE", "SpecKit is not available")

    if request.manual_fallback:
        return _stop("MANUAL_FALLBACK_FORBIDDEN",
                      "manual fallback is not a valid substitute")

    if request.from_phase not in CANONICAL_PHASES or request.to_phase not in CANONICAL_PHASES:
        return _stop("CANONICAL_SEQUENCE_RECONCILIATION_REQUIRED",
                      f"unknown phase: {request.from_phase} or {request.to_phase}")

    from_idx = CANONICAL_PHASES.index(request.from_phase)
    to_idx = CANONICAL_PHASES.index(request.to_phase)
    if to_idx != from_idx + 1:
        return _stop("CANONICAL_SEQUENCE_RECONCILIATION_REQUIRED",
                      f"transition {request.from_phase} -> {request.to_phase} "
                      f"is not a canonical adjacent step")

    required_phase = request.from_phase
    matching = [r for r in receipts
                if r.phase == required_phase and r.target_id == request.target_id]

    if not matching:
        wrong_target = [r for r in receipts if r.phase == required_phase]
        if wrong_target:
            return _stop("WRONG_TARGET_RECEIPT",
                          f"{required_phase} receipt exists but for a different target")
        receipt_name = required_phase.upper() + "_RECEIPT"
        return _stop(f"MISSING_{receipt_name}",
                      f"no {required_phase} receipt for target {request.target_id}")

    if now is not None:
        best = max(matching, key=lambda r: r.created_at)
        age = now - best.created_at
        if age > RECEIPT_MAX_AGE_SECONDS:
            return _stop("STALE_RECEIPT",
                          f"{required_phase} receipt is {age:.0f}s old "
                          f"(max {RECEIPT_MAX_AGE_SECONDS}s)")

    if request.to_phase == "implementation" and not human_approval:
        return _stop("HUMAN_APPROVAL_REQUIRED",
                      "implementation requires explicit human owner approval")

    return ValidationResult(
        status="PASS",
        reason=f"transition {request.from_phase} -> {request.to_phase} validated",
    )
