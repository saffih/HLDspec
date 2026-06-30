"""Coverage-scope ledger interpretation — pure functions on already-loaded data.

Interprets an already-loaded hld_coverage_ledger.json according to an
already-loaded hld_coverage_scope.json, separating selected-anchor blockers
from out-of-scope rows (step 5 of docs/ACTIVE_SPEC_COVERAGE_SCOPE_SCHEMA.md).

Pure functions only: no filesystem, no child processes, no network, no CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from hldspec.hld_coverage_scope import validate_hld_coverage_scope
from hldspec.journey2_hld_coverage_contracts import (
    BLOCKING_STATUSES,
    InvalidCoverageItemError,
    validate_coverage_ledger,
)


@dataclass
class CoverageScopeLedgerInterpretation:
    ok: bool
    errors: list[str] = field(default_factory=list)
    blocking_items: list[dict] = field(default_factory=list)
    advisory_items: list[dict] = field(default_factory=list)
    out_of_scope_items: list[dict] = field(default_factory=list)


def interpret_coverage_ledger_for_scope(
    *,
    coverage_ledger: object,
    coverage_scope: object,
) -> CoverageScopeLedgerInterpretation:
    errors: list[str] = []

    scope_result = validate_hld_coverage_scope(coverage_scope)
    if not scope_result.ok:
        errors.append(
            f"coverage_scope invalid: {'; '.join(scope_result.errors)}"
        )

    try:
        validated_ledger = validate_coverage_ledger(coverage_ledger)
    except InvalidCoverageItemError as exc:
        errors.append(f"coverage_ledger invalid: {exc}")
        validated_ledger = None

    if errors:
        return CoverageScopeLedgerInterpretation(ok=False, errors=errors)

    assert validated_ledger is not None
    assert isinstance(coverage_scope, dict)

    scope_mode = coverage_scope["coverage_scope"]

    if scope_mode == "FULL_HLD":
        return _interpret_full_hld(validated_ledger)

    return _interpret_active_spec(validated_ledger, coverage_scope)


def _interpret_full_hld(
    ledger: list[dict],
) -> CoverageScopeLedgerInterpretation:
    blocking = [item for item in ledger if item.get("status") in BLOCKING_STATUSES]
    return CoverageScopeLedgerInterpretation(
        ok=True,
        blocking_items=blocking,
        advisory_items=[],
        out_of_scope_items=[],
    )


def _interpret_active_spec(
    ledger: list[dict],
    scope: dict,
) -> CoverageScopeLedgerInterpretation:
    selected = set(scope["selected_hld_anchor_ids"])
    blocking: list[dict] = []
    out_of_scope: list[dict] = []

    for item in ledger:
        if item.get("status") not in BLOCKING_STATUSES:
            continue
        if item.get("hld_item_id") in selected:
            blocking.append(item)
        else:
            out_of_scope.append(item)

    return CoverageScopeLedgerInterpretation(
        ok=True,
        blocking_items=blocking,
        advisory_items=[],
        out_of_scope_items=out_of_scope,
    )
