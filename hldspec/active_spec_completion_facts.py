"""Active-spec completion facts — pure read-only advisory layer.

Consumes source-package gate facts and surfaces a single completion
verdict for the current active spec.  Never writes files, never
gates, never mutates backlogs or materialization state.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .source_package_gate_facts import build_source_package_gate_facts

COMPLETION_NOT_APPLICABLE = "NOT_APPLICABLE"
COMPLETION_COMPLETE_ADVISORY = "COMPLETE_ADVISORY"
COMPLETION_INCOMPLETE_ADVISORY = "INCOMPLETE_ADVISORY"
COMPLETION_UNKNOWN_ADVISORY = "UNKNOWN_ADVISORY"

_EXPECTED_RECEIPT_TYPE = "ACTIVE_SPEC_SOURCE_PACKAGE_RENDER"


@dataclass(frozen=True)
class ActiveSpecCompletionFacts:
    completion_applicable: bool
    completion_status: str
    coverage_scope: str | None
    active_spec_id: str | None
    selected_anchor_blocker_count: int | None
    out_of_scope_advisory_count: int | None
    receipt_present: bool
    receipt_type: str | None
    semantic_error_count: int
    read_error_count: int
    reasons: tuple[str, ...]


def build_active_spec_completion_facts(source_dir: Path) -> ActiveSpecCompletionFacts:
    try:
        facts = build_source_package_gate_facts(source_dir)
    except Exception:
        return ActiveSpecCompletionFacts(
            completion_applicable=False,
            completion_status=COMPLETION_UNKNOWN_ADVISORY,
            coverage_scope=None,
            active_spec_id=None,
            selected_anchor_blocker_count=None,
            out_of_scope_advisory_count=None,
            receipt_present=False,
            receipt_type=None,
            semantic_error_count=0,
            read_error_count=1,
            reasons=("read_errors_present",),
        )

    if facts.coverage_scope != "ACTIVE_SPEC":
        return ActiveSpecCompletionFacts(
            completion_applicable=False,
            completion_status=COMPLETION_NOT_APPLICABLE,
            coverage_scope=facts.coverage_scope,
            active_spec_id=facts.active_spec_id,
            selected_anchor_blocker_count=None,
            out_of_scope_advisory_count=None,
            receipt_present=facts.receipt_present,
            receipt_type=facts.receipt_type,
            semantic_error_count=len(facts.semantic_errors),
            read_error_count=len(facts.read_errors),
            reasons=("coverage_scope_not_active_spec",),
        )

    reasons: list[str] = []
    read_error_count = len(facts.read_errors)
    semantic_error_count = len(facts.semantic_errors)

    if not facts.active_spec_id:
        reasons.append("missing_active_spec_id")

    if facts.selected_anchor_blocker_count > 0:
        reasons.append("selected_anchor_blockers_present")

    if not facts.receipt_present:
        reasons.append("missing_active_spec_receipt")
    elif facts.receipt_type != _EXPECTED_RECEIPT_TYPE:
        reasons.append("unexpected_receipt_type")

    if semantic_error_count > 0:
        reasons.append("semantic_errors_present")

    if read_error_count > 0:
        reasons.append("read_errors_present")

    if reasons:
        status = COMPLETION_INCOMPLETE_ADVISORY
    else:
        status = COMPLETION_COMPLETE_ADVISORY

    return ActiveSpecCompletionFacts(
        completion_applicable=True,
        completion_status=status,
        coverage_scope=facts.coverage_scope,
        active_spec_id=facts.active_spec_id,
        selected_anchor_blocker_count=facts.selected_anchor_blocker_count,
        out_of_scope_advisory_count=facts.out_of_scope_advisory_count,
        receipt_present=facts.receipt_present,
        receipt_type=facts.receipt_type,
        semantic_error_count=semantic_error_count,
        read_error_count=read_error_count,
        reasons=tuple(reasons),
    )
