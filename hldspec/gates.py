"""Single source of truth for HLDspec gate semantics.

All scripts and machines must import from here rather than re-implementing
gate logic. This prevents the plan-green and prework-green conditions from
diverging across callers.

Usage:
    from hldspec.gates import plan_gate_status, prework_gate_status
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Marker used in review text to signal continue permission.
_CONTINUE_MARKER = r"Continue to SpecKit prework:\s*`?"


@dataclass(frozen=True)
class PlanGateStatus:
    """Result of evaluating the spec build plan gate."""

    green: bool
    decision: str          # "PASS" | "FIX" | "CONFLICT" | "DECOMPOSE" | ""
    recommendation: str    # "KEEP_PLAN" | "REWORK" | ""
    conflict_count: int
    flagged_count: int
    continue_true: bool    # review text says continue: true
    continue_false: bool   # review text says continue: false


@dataclass(frozen=True)
class PreworkGateStatus:
    """Result of evaluating the SpecKit prework gate."""

    ready: bool
    status: str            # "PASS" | "REWORK_REQUIRED" | "MISSING" | ...
    blocker_count: int


def plan_gate_status(plan: dict[str, Any], review_text: str) -> PlanGateStatus:
    """Canonical plan-green check.

    Green iff ALL of:
    - review text contains continue: true marker
    - review text does not contain continue: false marker
    - plan_quality.decision == "PASS"   (not "FIX", not "HANDLED")
    - plan_quality.recommendation == "KEEP_PLAN"
    - no conflicts
    - no flagged specs (quality_flags or requires_user_review)
    """
    pq = plan.get("plan_quality") if isinstance(plan, dict) else None
    if not isinstance(pq, dict):
        pq = {}

    decision = str(pq.get("decision", ""))
    recommendation = str(pq.get("recommendation", ""))
    conflicts = pq.get("conflicts", [])
    planned = plan.get("planned_specs", []) if isinstance(plan, dict) else []

    flagged = [
        s
        for s in (planned if isinstance(planned, list) else [])
        if isinstance(s, dict) and (s.get("quality_flags") or s.get("requires_user_review"))
    ]

    continue_true = bool(re.search(_CONTINUE_MARKER + r"true`?", review_text, re.I))
    continue_false = bool(re.search(_CONTINUE_MARKER + r"false`?", review_text, re.I))

    green = (
        continue_true
        and not continue_false
        and decision == "PASS"
        and recommendation == "KEEP_PLAN"
        and not conflicts
        and not flagged
    )

    return PlanGateStatus(
        green=green,
        decision=decision,
        recommendation=recommendation,
        conflict_count=len(conflicts) if isinstance(conflicts, list) else 0,
        flagged_count=len(flagged),
        continue_true=continue_true,
        continue_false=continue_false,
    )


def prework_gate_status(review: dict[str, Any]) -> PreworkGateStatus:
    """Canonical prework-green check.

    Ready iff:
    - status is not "REWORK_REQUIRED" and not "MISSING"
    - no BLOCKER findings
    """
    status = str(review.get("status", "MISSING")) if isinstance(review, dict) else "MISSING"
    findings = review.get("findings", []) if isinstance(review, dict) else []
    blockers = [
        f
        for f in (findings if isinstance(findings, list) else [])
        if isinstance(f, dict) and f.get("severity") == "BLOCKER"
    ]
    ready = status not in {"REWORK_REQUIRED", "MISSING"} and not blockers
    return PreworkGateStatus(
        ready=ready,
        status=status,
        blocker_count=len(blockers),
    )
