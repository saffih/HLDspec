"""Legacy Journey 0 draftability gate.

This module belongs to the frozen dict/contracts stack. It is NOT_CANONICAL /
DO_NOT_WIRE for new Journey 0 work; use `journey0_draftability` for the typed
Journey 0 draftability verdict path.

This module evaluates already-collected Journey 0 artifact summaries and
decides whether they are safe to hand to Journey 1 as evidence/gap input. It
does not discover repos, read files, write files, launch tools, or approve any
protected transition.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from hldspec import journey0_artifact_contracts as j0

LEGACY_JOURNEY0_STACK_STATUS = j0.LEGACY_JOURNEY0_STACK_STATUS
LEGACY_JOURNEY0_STACK_WIRING_STATUS = j0.LEGACY_JOURNEY0_STACK_WIRING_STATUS
LEGACY_JOURNEY0_STACK_DISPOSITION = j0.LEGACY_JOURNEY0_STACK_DISPOSITION


@dataclass(frozen=True)
class DraftabilityInput:
    """Minimal input surface for the Journey 0 draftability gate.

    The gate consumes artifact summaries that another Journey 0 producer has
    already assembled. `candidate_requirements` is intentionally shallow: each
    entry may declare an `evidence_label`, and only OBSERVED backing can pass as
    requirement-ready evidence.
    """

    evidence_pack: Mapping[str, Any]
    gap_report: Mapping[str, Any] = field(
        default_factory=lambda: {"kind": j0.ARTIFACT_HLD_GAP_REPORT}
    )
    product_decision_register: Sequence[Mapping[str, Any]] | None = None
    open_questions: Sequence[str] = ()
    candidate_requirements: Sequence[Mapping[str, Any]] = ()
    safety_authority_gaps: Sequence[str] = ()


@dataclass(frozen=True)
class DraftabilityResult:
    """Draftability verdict plus explicit non-authority boundary fields."""

    verdict: str
    draftable: bool
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]
    open_questions: tuple[str, ...]
    accepted_fact_count: int
    handoff_kind: str = j0.HANDOFF_EVIDENCE_AND_GAP_INPUT
    journey1_input_only: bool = True
    grants_approval_authority: bool = False
    authorizes_implementation: bool = False
    authorizes_work_orders: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": j0.ARTIFACT_HLD_DRAFTABILITY_VERDICT,
            "verdict": self.verdict,
            "draftable": self.draftable,
            "reasons": list(self.reasons),
            "blockers": list(self.blockers),
            "open_questions": list(self.open_questions),
            "accepted_fact_count": self.accepted_fact_count,
            "handoff_kind": self.handoff_kind,
            "journey1_input_only": self.journey1_input_only,
            "grants_approval_authority": self.grants_approval_authority,
            "authorizes_implementation": self.authorizes_implementation,
            "authorizes_work_orders": self.authorizes_work_orders,
        }


def evaluate_hld_draftability(draftability_input: DraftabilityInput) -> DraftabilityResult:
    """Return the Journey 0 HLD draftability verdict.

    Priority order is intentionally small and explicit:

    1. blocking product decisions or authority gaps
    2. repo-state conflicts or CONFLICT evidence
    3. no OBSERVED evidence, or candidate requirements without OBSERVED backing
    4. non-blocking open questions
    5. ready to draft
    """

    items = j0.evidence_items(dict(draftability_input.evidence_pack))
    accepted = j0.accepted_facts(dict(draftability_input.evidence_pack))
    gap_report = _validate_gap_report(draftability_input.gap_report)
    open_decisions = j0.open_product_decisions(
        list(draftability_input.product_decision_register or ())
    )
    product_decision_evidence = [
        item for item in items if item.get("label") == j0.EVIDENCE_PRODUCT_DECISION_REQUIRED
    ]
    conflict_evidence = [item for item in items if item.get("label") == j0.EVIDENCE_CONFLICT]
    unknown_evidence = [item for item in items if item.get("label") == j0.EVIDENCE_UNKNOWN]

    requirement_blockers = _requirement_blockers(
        draftability_input.candidate_requirements
    )
    blocker_reasons: list[str] = []
    open_question_reasons = [
        *_strings_from_items(unknown_evidence, "UNKNOWN evidence"),
        *draftability_input.open_questions,
    ]

    if open_decisions or product_decision_evidence or draftability_input.safety_authority_gaps:
        blocker_reasons.extend(_decision_reasons(open_decisions))
        blocker_reasons.extend(
            _strings_from_items(product_decision_evidence, "PRODUCT_DECISION_REQUIRED evidence")
        )
        blocker_reasons.extend(
            f"safety/authority gap blocks handoff: {gap}"
            for gap in draftability_input.safety_authority_gaps
        )
        return _result(
            j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED,
            accepted,
            reasons=("product decision or authority resolution is required",),
            blockers=blocker_reasons,
            open_questions=open_question_reasons,
        )

    if bool(gap_report.get("repo_state_conflict")) or conflict_evidence:
        blocker_reasons.extend(_strings_from_items(conflict_evidence, "CONFLICT evidence"))
        if gap_report.get("repo_state_conflict"):
            blocker_reasons.append("gap report declares repo_state_conflict")
        return _result(
            j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT,
            accepted,
            reasons=("unresolved repo-state conflict blocks HLD draftability",),
            blockers=blocker_reasons,
            open_questions=open_question_reasons,
        )

    if not accepted or requirement_blockers:
        blocker_reasons.extend(requirement_blockers)
        if not accepted:
            blocker_reasons.append("no OBSERVED evidence is available")
        return _result(
            j0.VERDICT_INSUFFICIENT_EVIDENCE,
            accepted,
            reasons=("observed evidence is insufficient for HLD drafting",),
            blockers=blocker_reasons,
            open_questions=open_question_reasons,
        )

    if open_question_reasons:
        return _result(
            j0.VERDICT_READY_WITH_OPEN_QUESTIONS,
            accepted,
            reasons=("observed evidence exists, with explicit open questions",),
            blockers=(),
            open_questions=open_question_reasons,
        )

    return _result(
        j0.VERDICT_READY_TO_DRAFT_HLD,
        accepted,
        reasons=("observed evidence is sufficient and no blockers remain",),
        blockers=(),
        open_questions=(),
    )


def _validate_gap_report(gap_report: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(gap_report, Mapping):
        raise j0.InvalidJourney0ArtifactError("gap report is not an object")
    report = dict(gap_report)
    if "kind" in report:
        j0.validate_artifact(report)
        if report["kind"] != j0.ARTIFACT_HLD_GAP_REPORT:
            raise j0.InvalidJourney0ArtifactError("gap report kind is not HLDGapReport")
    return report


def _requirement_blockers(requirements: Sequence[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for idx, requirement in enumerate(requirements):
        if not isinstance(requirement, Mapping):
            raise j0.InvalidJourney0ArtifactError("candidate requirement is not an object")
        label = j0.validate_evidence_label(requirement.get("evidence_label"))
        if label != j0.EVIDENCE_OBSERVED:
            name = requirement.get("id") or requirement.get("name") or f"requirement[{idx}]"
            blockers.append(
                f"{name} cannot become a requirement from {label} evidence"
            )
    return blockers


def _decision_reasons(decisions: Sequence[Mapping[str, Any]]) -> list[str]:
    reasons: list[str] = []
    for idx, decision in enumerate(decisions):
        decision_id = decision.get("id") or f"decision[{idx}]"
        status = decision.get("status", "OPEN")
        reasons.append(f"{decision_id} remains {status}")
    return reasons


def _strings_from_items(items: Sequence[Mapping[str, Any]], prefix: str) -> list[str]:
    reasons: list[str] = []
    for idx, item in enumerate(items):
        statement = item.get("statement") or item.get("id") or f"item[{idx}]"
        reasons.append(f"{prefix}: {statement}")
    return reasons


def _result(
    verdict: str,
    accepted_facts: Sequence[Mapping[str, Any]],
    *,
    reasons: Sequence[str],
    blockers: Sequence[str],
    open_questions: Sequence[str],
) -> DraftabilityResult:
    return DraftabilityResult(
        verdict=verdict,
        draftable=j0.is_draftable(verdict),
        reasons=tuple(reasons),
        blockers=tuple(blockers),
        open_questions=tuple(open_questions),
        accepted_fact_count=len(accepted_facts),
    )
