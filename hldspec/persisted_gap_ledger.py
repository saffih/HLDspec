"""Persisted Gap Ledger validator — pure validation of already-loaded data.

Validates Python objects against the schema contract defined in
docs/PERSISTED_GAP_LEDGER_SCHEMA.md.

Pure functions only: no filesystem, no child processes, no network, no CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_GAP_STATES: frozenset[str] = frozenset({
    "OPEN",
    "BLOCKING",
    "CONFLICT",
    "NEEDS_OWNER",
    "ASSUMED_FOR_NOW",
    "SAFE_TO_DEFER",
    "RESOLVED_BY_EVIDENCE",
    "RESOLVED_BY_DECISION",
    "PARTIAL",
    "KNOWN_LIMITATION",
})

ALLOWED_GAP_CATEGORIES: frozenset[str] = frozenset({
    "context_safety_and_gap_continuity",
    "spec_capability_decomposition",
    "control_plane_isolation",
    "journey2_sdd_completeness",
    "validation_architecture",
    "testing_discipline",
    "driver_readiness",
    "journey3_helper_execution",
    "speckit_helper_scope",
    "baton_external_workflow",
    "docs_governance",
})

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "created_at",
    "updated_at",
    "source_refs",
    "gaps",
)

_REQUIRED_GAP_FIELDS = (
    "gap_id",
    "category",
    "state",
    "summary",
    "why_it_matters",
    "source_refs",
    "created_at",
    "updated_at",
)

_STRING_GAP_FIELDS = (
    "gap_id",
    "category",
    "state",
    "summary",
    "why_it_matters",
    "created_at",
    "updated_at",
)


@dataclass
class GapLedgerValidation:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_gap_ledger(data: object) -> GapLedgerValidation:
    result = GapLedgerValidation()

    if not isinstance(data, dict):
        result.errors.append("top-level must be object")
        return result

    for f in _REQUIRED_TOP_LEVEL_FIELDS:
        if f not in data:
            result.errors.append(f"missing top-level field: {f}")

    if result.errors:
        return result

    if not isinstance(data["schema_version"], int):
        result.errors.append("schema_version must be integer")

    if not isinstance(data["created_at"], str):
        result.errors.append("created_at must be string")

    if not isinstance(data["updated_at"], str):
        result.errors.append("updated_at must be string")

    if not isinstance(data["source_refs"], list):
        result.errors.append("source_refs must be list of strings")
    elif not all(isinstance(s, str) for s in data["source_refs"]):
        result.errors.append("source_refs must be list of strings")

    if not isinstance(data["gaps"], list):
        result.errors.append("gaps must be list")
        return result

    seen_ids: set[str] = set()

    for i, gap in enumerate(data["gaps"]):
        prefix = f"gaps[{i}]"

        if not isinstance(gap, dict):
            result.errors.append(f"{prefix} must be object")
            continue

        for f in _REQUIRED_GAP_FIELDS:
            if f not in gap:
                result.errors.append(f"{prefix}.missing required field: {f}")

        for f in _STRING_GAP_FIELDS:
            if f in gap and not isinstance(gap[f], str):
                result.errors.append(f"{prefix}.{f} must be string")

        if "source_refs" in gap:
            if not isinstance(gap["source_refs"], list):
                result.errors.append(f"{prefix}.source_refs must be list of strings")
            elif not all(isinstance(s, str) for s in gap["source_refs"]):
                result.errors.append(f"{prefix}.source_refs must be list of strings")

        category = gap.get("category")
        if isinstance(category, str) and category not in ALLOWED_GAP_CATEGORIES:
            result.errors.append(f"{prefix}.invalid category: {category}")

        state = gap.get("state")
        if isinstance(state, str):
            if state == "UNKNOWN":
                result.errors.append(f"{prefix}.invalid state: UNKNOWN")
            elif state not in ALLOWED_GAP_STATES:
                result.errors.append(f"{prefix}.invalid state: {state}")

        gap_id = gap.get("gap_id")
        if isinstance(gap_id, str):
            if gap_id in seen_ids:
                result.errors.append(f"duplicate gap_id: {gap_id}")
            seen_ids.add(gap_id)

        if isinstance(state, str):
            _validate_conditional_fields(result, prefix, state, gap)

    return result


def _validate_conditional_fields(
    result: GapLedgerValidation,
    prefix: str,
    state: str,
    gap: dict,
) -> None:
    if state == "SAFE_TO_DEFER":
        if not gap.get("reason") or not isinstance(gap.get("reason"), str):
            result.errors.append(f"{prefix}.SAFE_TO_DEFER requires reason")
        if not gap.get("owner_or_scope") or not isinstance(gap.get("owner_or_scope"), str):
            result.errors.append(f"{prefix}.SAFE_TO_DEFER requires owner_or_scope")

    elif state == "ASSUMED_FOR_NOW":
        if not gap.get("assumption_text") or not isinstance(gap.get("assumption_text"), str):
            result.errors.append(f"{prefix}.ASSUMED_FOR_NOW requires assumption_text")

    elif state == "RESOLVED_BY_EVIDENCE":
        if not gap.get("evidence_ref") or not isinstance(gap.get("evidence_ref"), str):
            result.errors.append(f"{prefix}.RESOLVED_BY_EVIDENCE requires evidence_ref")

    elif state == "RESOLVED_BY_DECISION":
        if not gap.get("decision_ref") or not isinstance(gap.get("decision_ref"), str):
            result.errors.append(f"{prefix}.RESOLVED_BY_DECISION requires decision_ref")

    elif state == "CONFLICT":
        related = gap.get("related_gap_ids")
        notes = gap.get("notes")
        has_related = isinstance(related, list) and len(related) > 0 and all(isinstance(s, str) for s in related)
        has_notes = isinstance(notes, str) and len(notes) > 0
        if not has_related and not has_notes:
            result.errors.append(f"{prefix}.CONFLICT requires related_gap_ids or notes")
