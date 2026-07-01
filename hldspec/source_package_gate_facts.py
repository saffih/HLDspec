"""Scope-aware source-package gate facts — pure read-only facts layer.

Reads the source-package directory and surfaces structured facts for
downstream gate consumers. Never approves, rejects, or gates anything.
Never writes files, mutates backlogs, or changes materialization state.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import hld_source_package as sp
from .hld_coverage_scope_interpretation import interpret_coverage_ledger_for_scope


@dataclass(frozen=True)
class SourcePackageGateFacts:
    validation_ok: bool
    validation_missing: tuple[str, ...]
    validation_hash_mismatches: tuple[str, ...]
    semantic_errors: tuple[str, ...]

    coverage_scope: str | None
    active_spec_id: str | None

    interpretation_ok: bool | None
    interpretation_errors: tuple[str, ...]

    blocking_items: tuple[dict, ...]
    advisory_items: tuple[dict, ...]
    out_of_scope_items: tuple[dict, ...]

    selected_anchor_blocker_count: int
    out_of_scope_advisory_count: int

    receipt_present: bool
    receipt_type: str | None
    target_materialization: str | None
    read_errors: tuple[str, ...]


def _load_json_file(path: Path) -> tuple[dict | None, str | None]:
    if not path.is_file():
        return None, None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return None, f"{path.name} is malformed: {exc}"
    if not isinstance(data, dict):
        return None, f"{path.name} is not a JSON object"
    return data, None


def build_source_package_gate_facts(source_dir: Path) -> SourcePackageGateFacts:
    validation = sp.validate_source_package(source_dir)

    read_errors: list[str] = []

    scope_path = source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
    scope, scope_err = _load_json_file(scope_path)
    if scope_err:
        read_errors.append(scope_err)

    coverage_scope: str | None = None
    active_spec_id: str | None = None
    if scope is not None:
        coverage_scope = scope.get("coverage_scope")
        active_spec_id = scope.get("active_spec_id")

    ledger_path = source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]
    ledger_data: list | None = None
    if ledger_path.is_file():
        try:
            raw = json.loads(ledger_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            read_errors.append(f"{ledger_path.name} is malformed: {exc}")
            raw = None
        else:
            if isinstance(raw, list):
                ledger_data = raw
            else:
                read_errors.append(f"{ledger_path.name} is not a JSON array")

    interpretation_ok: bool | None = None
    interpretation_errors: list[str] = []
    blocking_items: list[dict] = []
    advisory_items: list[dict] = []
    out_of_scope_items: list[dict] = []

    if scope is not None and ledger_data is not None:
        interp = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger_data,
            coverage_scope=scope,
        )
        interpretation_ok = interp.ok
        interpretation_errors = list(interp.errors)
        blocking_items = list(interp.blocking_items)
        advisory_items = list(interp.advisory_items)
        out_of_scope_items = list(interp.out_of_scope_items)

    receipt_path = source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
    receipt, receipt_err = _load_json_file(receipt_path)
    if receipt_err:
        read_errors.append(receipt_err)

    receipt_present = receipt_path.is_file()
    receipt_type: str | None = None
    target_materialization: str | None = None
    if receipt is not None:
        receipt_type = receipt.get("receipt_type")
        target_materialization = receipt.get("target_materialization")

    return SourcePackageGateFacts(
        validation_ok=validation.ok,
        validation_missing=tuple(validation.missing),
        validation_hash_mismatches=tuple(validation.hash_mismatches),
        semantic_errors=tuple(validation.semantic_errors),
        coverage_scope=coverage_scope,
        active_spec_id=active_spec_id,
        interpretation_ok=interpretation_ok,
        interpretation_errors=tuple(interpretation_errors),
        blocking_items=tuple(blocking_items),
        advisory_items=tuple(advisory_items),
        out_of_scope_items=tuple(out_of_scope_items),
        selected_anchor_blocker_count=len(blocking_items),
        out_of_scope_advisory_count=len(out_of_scope_items),
        receipt_present=receipt_present,
        receipt_type=receipt_type,
        target_materialization=target_materialization,
        read_errors=tuple(read_errors),
    )


def build_source_package_gate_facts_report(source_dir: Path) -> dict:
    """Advisory-only compact report of source-package gate facts.

    Returns a dict with counts instead of raw ledger rows.
    Never writes files, never changes gate/driver/readiness behavior.
    """
    facts = build_source_package_gate_facts(source_dir)
    return {
        "validation_ok": facts.validation_ok,
        "semantic_errors": list(facts.semantic_errors),
        "coverage_scope": facts.coverage_scope,
        "active_spec_id": facts.active_spec_id,
        "interpretation_ok": facts.interpretation_ok,
        "interpretation_errors": list(facts.interpretation_errors),
        "selected_anchor_blocker_count": facts.selected_anchor_blocker_count,
        "out_of_scope_advisory_count": facts.out_of_scope_advisory_count,
        "receipt_present": facts.receipt_present,
        "receipt_type": facts.receipt_type,
        "target_materialization": facts.target_materialization,
        "read_errors": list(facts.read_errors),
    }
