"""Coverage-scope validator — pure functions on already-loaded data.

Validates Python objects against the schema contract defined in
docs/ACTIVE_SPEC_COVERAGE_SCOPE_SCHEMA.md.

Pure functions only: no filesystem, no child processes, no network, no CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_COVERAGE_SCOPES: frozenset[str] = frozenset({"FULL_HLD", "ACTIVE_SPEC"})

HLD_COVERAGE_SCOPE_SCHEMA_VERSION: int = 1

_REQUIRED_FIELDS = (
    "schema_version",
    "coverage_scope",
    "active_spec_id",
    "selected_hld_anchor_ids",
    "source_refs",
    "notes",
)


@dataclass
class HldCoverageScopeValidation:
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_hld_coverage_scope(data: object) -> HldCoverageScopeValidation:
    errors: list[str] = []

    if not isinstance(data, dict):
        errors.append("scope must be object")
        return HldCoverageScopeValidation(ok=False, errors=errors)

    for f in _REQUIRED_FIELDS:
        if f not in data:
            errors.append(f"missing required field: {f}")

    if errors:
        return HldCoverageScopeValidation(ok=False, errors=errors)

    if not isinstance(data["schema_version"], int) or isinstance(data["schema_version"], bool):
        errors.append("schema_version must be 1")
    elif data["schema_version"] != 1:
        errors.append("schema_version must be 1")

    coverage_scope = data["coverage_scope"]
    if not isinstance(coverage_scope, str) or coverage_scope not in ALLOWED_COVERAGE_SCOPES:
        errors.append("coverage_scope must be FULL_HLD or ACTIVE_SPEC")

    _validate_list_of_strings(errors, data, "source_refs")
    _validate_list_of_strings(errors, data, "notes")
    _validate_selected_hld_anchor_ids(errors, data)

    if isinstance(coverage_scope, str) and coverage_scope in ALLOWED_COVERAGE_SCOPES:
        if coverage_scope == "FULL_HLD":
            _validate_full_hld(errors, data)
        else:
            _validate_active_spec(errors, data)

    return HldCoverageScopeValidation(ok=not errors, errors=errors)


def _validate_list_of_strings(errors: list[str], data: dict, field_name: str) -> None:
    value = data[field_name]
    if not isinstance(value, list):
        errors.append(f"{field_name} must be list of strings")
    elif not all(isinstance(s, str) for s in value):
        errors.append(f"{field_name} must be list of strings")


def _validate_selected_hld_anchor_ids(errors: list[str], data: dict) -> None:
    value = data["selected_hld_anchor_ids"]
    if not isinstance(value, list):
        errors.append("selected_hld_anchor_ids must be list of strings")
        return
    if not all(isinstance(s, str) for s in value):
        errors.append("selected_hld_anchor_ids must be list of strings")
        return
    if len(value) != len(set(value)):
        errors.append("selected_hld_anchor_ids must contain unique strings")


def _validate_full_hld(errors: list[str], data: dict) -> None:
    if data["active_spec_id"] is not None:
        errors.append("active_spec_id must be null for FULL_HLD")


def _validate_active_spec(errors: list[str], data: dict) -> None:
    active_spec_id = data["active_spec_id"]
    if not isinstance(active_spec_id, str) or not active_spec_id:
        errors.append("active_spec_id must be non-empty string for ACTIVE_SPEC")

    anchor_ids = data["selected_hld_anchor_ids"]
    if isinstance(anchor_ids, list) and all(isinstance(s, str) for s in anchor_ids):
        if not anchor_ids:
            errors.append("selected_hld_anchor_ids must be non-empty for ACTIVE_SPEC")


def build_active_spec_coverage_scope(
    *,
    active_spec_id: str,
    selected_hld_anchor_ids: list[str],
    source_refs: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict:
    data = {
        "schema_version": HLD_COVERAGE_SCOPE_SCHEMA_VERSION,
        "coverage_scope": "ACTIVE_SPEC",
        "active_spec_id": active_spec_id,
        "selected_hld_anchor_ids": list(selected_hld_anchor_ids) if isinstance(selected_hld_anchor_ids, list) else selected_hld_anchor_ids,
        "source_refs": list(source_refs) if isinstance(source_refs, list) else ([] if source_refs is None else source_refs),
        "notes": list(notes) if isinstance(notes, list) else ([] if notes is None else notes),
    }
    result = validate_hld_coverage_scope(data)
    if not result.ok:
        raise ValueError(
            f"generated active-spec hld coverage scope is invalid: {'; '.join(result.errors)}"
        )
    return data


def build_active_spec_coverage_scope_from_selected_spec(
    *,
    active_spec_id: str,
    selected_spec: dict,
    source_refs: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict:
    return build_active_spec_coverage_scope(
        active_spec_id=active_spec_id,
        selected_hld_anchor_ids=selected_spec.get("hld_anchor_ids", []),
        source_refs=source_refs,
        notes=notes,
    )


def build_full_hld_coverage_scope(
    *,
    selected_hld_anchor_ids: list[str] | None = None,
    source_refs: list[str] | None = None,
    notes: list[str] | None = None,
) -> dict:
    data = {
        "schema_version": HLD_COVERAGE_SCOPE_SCHEMA_VERSION,
        "coverage_scope": "FULL_HLD",
        "active_spec_id": None,
        "selected_hld_anchor_ids": list(selected_hld_anchor_ids or []),
        "source_refs": list(source_refs or []),
        "notes": list(notes or []),
    }
    result = validate_hld_coverage_scope(data)
    if not result.ok:
        raise ValueError(f"generated hld coverage scope is invalid: {'; '.join(result.errors)}")
    return data
