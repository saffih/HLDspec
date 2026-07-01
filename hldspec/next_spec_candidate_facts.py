"""Next-spec candidate facts -- pure read-only advisory layer."""
from __future__ import annotations

from dataclasses import dataclass

from .active_spec_completion_facts import COMPLETION_COMPLETE_ADVISORY

CANDIDATE_NOT_APPLICABLE = "NOT_APPLICABLE"
CANDIDATE_CANDIDATES_AVAILABLE = "CANDIDATES_AVAILABLE"
CANDIDATE_NO_CANDIDATES = "NO_CANDIDATES"
CANDIDATE_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class NextSpecCandidate:
    spec_id: str
    title: str | None
    status: str | None
    hld_anchor_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RejectedNextSpec:
    spec_id: str | None
    title: str | None
    status: str | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class NextSpecCandidateFacts:
    candidate_facts_applicable: bool
    candidate_status: str
    active_spec_id: str | None
    active_spec_completion_status: str | None
    candidate_count: int
    rejected_count: int
    candidates: tuple[NextSpecCandidate, ...]
    rejected: tuple[RejectedNextSpec, ...]
    reasons: tuple[str, ...]


def _as_str_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    return ()


def _is_complete_status(status: object) -> bool:
    return isinstance(status, str) and status in {"DONE", "VALIDATED", "COMPLETE"}


def build_next_spec_candidate_facts(
    backlog: dict,
    *,
    active_spec_completion_status: str | None = None,
) -> NextSpecCandidateFacts:
    if active_spec_completion_status != COMPLETION_COMPLETE_ADVISORY:
        active_id = backlog.get("active_spec_id") if isinstance(backlog, dict) else None
        return NextSpecCandidateFacts(
            candidate_facts_applicable=False,
            candidate_status=CANDIDATE_NOT_APPLICABLE,
            active_spec_id=active_id if isinstance(active_id, str) else None,
            active_spec_completion_status=active_spec_completion_status,
            candidate_count=0,
            rejected_count=0,
            candidates=(),
            rejected=(),
            reasons=("active_spec_not_complete",),
        )

    if not isinstance(backlog, dict):
        return NextSpecCandidateFacts(
            candidate_facts_applicable=False,
            candidate_status=CANDIDATE_UNKNOWN,
            active_spec_id=None,
            active_spec_completion_status=active_spec_completion_status,
            candidate_count=0,
            rejected_count=0,
            candidates=(),
            rejected=(),
            reasons=("backlog_unreadable",),
        )

    active_spec_id = backlog.get("active_spec_id")
    if not isinstance(active_spec_id, str):
        active_spec_id = None

    specs = backlog.get("specs")
    if not isinstance(specs, list):
        return NextSpecCandidateFacts(
            candidate_facts_applicable=False,
            candidate_status=CANDIDATE_UNKNOWN,
            active_spec_id=active_spec_id,
            active_spec_completion_status=active_spec_completion_status,
            candidate_count=0,
            rejected_count=0,
            candidates=(),
            rejected=(),
            reasons=("backlog_unreadable",),
        )

    if not specs:
        return NextSpecCandidateFacts(
            candidate_facts_applicable=True,
            candidate_status=CANDIDATE_NO_CANDIDATES,
            active_spec_id=active_spec_id,
            active_spec_completion_status=active_spec_completion_status,
            candidate_count=0,
            rejected_count=0,
            candidates=(),
            rejected=(),
            reasons=("no_specs", "no_candidates"),
        )

    candidates: list[NextSpecCandidate] = []
    rejected: list[RejectedNextSpec] = []

    for entry in specs:
        if not isinstance(entry, dict):
            rejected.append(
                RejectedNextSpec(
                    spec_id=None,
                    title=None,
                    status=None,
                    reasons=("backlog_unreadable",),
                )
            )
            continue

        spec_id = entry.get("spec_id")
        raw_title = entry.get("title")
        raw_status = entry.get("status")
        title = raw_title if isinstance(raw_title, str) else None
        status = raw_status if isinstance(raw_status, str) else None
        hld_anchor_ids = _as_str_tuple(entry.get("hld_anchor_ids"))
        dependency_ids = _as_str_tuple(entry.get("dependencies"))
        target_materialization = entry.get("target_materialization")

        if not isinstance(spec_id, str) or not spec_id:
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id if isinstance(spec_id, str) else None,
                    title=title,
                    status=status,
                    reasons=("missing_spec_id",),
                )
            )
            continue

        if spec_id == active_spec_id:
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("current_active_spec",),
                )
            )
            continue

        if dependency_ids:
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("dependency_semantics_unknown",),
                )
            )
            continue

        if status == "SELECTED":
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("already_selected",),
                )
            )
            continue

        if _is_complete_status(status):
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("already_complete",),
                )
            )
            continue

        if status == "MATERIALIZED_TO_TARGET" or target_materialization == "MATERIALIZED_TO_TARGET":
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("already_materialized",),
                )
            )
            continue

        if target_materialization != "NOT_MATERIALIZED":
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("unsupported_status",),
                )
            )
            continue

        if status == "BLOCKED":
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("blocked_status",),
                )
            )
            continue

        if status in {"SUPERSEDED", "IN_IMPLEMENTATION"}:
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("unsupported_status",),
                )
            )
            continue

        if status not in {"PLANNED", "READY_FOR_SELECTION"}:
            rejected.append(
                RejectedNextSpec(
                    spec_id=spec_id,
                    title=title,
                    status=status,
                    reasons=("unsupported_status",),
                )
            )
            continue

        candidates.append(
            NextSpecCandidate(
                spec_id=spec_id,
                title=title,
                status=status,
                hld_anchor_ids=hld_anchor_ids,
                dependency_ids=dependency_ids,
                reasons=(),
            )
        )

    candidate_tuple = tuple(candidates)
    rejected_tuple = tuple(rejected)
    if candidate_tuple:
        return NextSpecCandidateFacts(
            candidate_facts_applicable=True,
            candidate_status=CANDIDATE_CANDIDATES_AVAILABLE,
            active_spec_id=active_spec_id,
            active_spec_completion_status=active_spec_completion_status,
            candidate_count=len(candidate_tuple),
            rejected_count=len(rejected_tuple),
            candidates=candidate_tuple,
            rejected=rejected_tuple,
            reasons=(),
        )

    return NextSpecCandidateFacts(
        candidate_facts_applicable=True,
        candidate_status=CANDIDATE_NO_CANDIDATES,
        active_spec_id=active_spec_id,
        active_spec_completion_status=active_spec_completion_status,
        candidate_count=0,
        rejected_count=len(rejected_tuple),
        candidates=(),
        rejected=rejected_tuple,
        reasons=("no_candidates",),
    )
