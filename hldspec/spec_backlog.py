"""Spec Backlog validator — pure validation of already-loaded data.

Validates Python objects against the schema contract defined in
docs/MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md.

Pure functions only: no filesystem, no child processes, no network, no CLI.
"""
from __future__ import annotations

from dataclasses import dataclass, field


ALLOWED_SPEC_STATUSES: frozenset[str] = frozenset({
    "PLANNED",
    "READY_FOR_SELECTION",
    "SELECTED",
    "MATERIALIZED_TO_TARGET",
    "IN_IMPLEMENTATION",
    "VALIDATED",
    "DONE",
    "BLOCKED",
    "SUPERSEDED",
})

ALLOWED_SPEC_SIZE_CLASSES: frozenset[str] = frozenset({
    "ATOMIC_TASK",
    "BOUNDED_DELIVERABLE",
    "SPRINT_SIZED",
    "TOO_LARGE",
})

ALLOWED_TARGET_MATERIALIZATION_STATES: frozenset[str] = frozenset({
    "NOT_MATERIALIZED",
    "MATERIALIZED_TO_SINGLE_SPEC_INPUT",
    "SUPERSEDED_IN_TARGET",
})

_REQUIRED_TOP_LEVEL_FIELDS = (
    "schema_version",
    "created_at",
    "updated_at",
    "source_refs",
    "active_spec_id",
    "specs",
)

_REQUIRED_SPEC_FIELDS = (
    "spec_id",
    "title",
    "hld_anchor_ids",
    "capability",
    "status",
    "size_class",
    "dependencies",
    "validation_strategy",
    "target_materialization",
)

_STRING_SPEC_FIELDS = (
    "spec_id",
    "title",
    "capability",
    "status",
    "size_class",
    "target_materialization",
)

_LIST_OF_STRINGS_SPEC_FIELDS = (
    "hld_anchor_ids",
    "dependencies",
    "validation_strategy",
)

_OPTIONAL_STRING_FIELDS = (
    "owner_or_scope",
    "reason",
    "notes",
)

_ACTIVE_STATUSES = frozenset({"SELECTED", "MATERIALIZED_TO_TARGET"})

_SELECTION_STATUSES = frozenset({"READY_FOR_SELECTION", "SELECTED", "MATERIALIZED_TO_TARGET"})


@dataclass
class SpecBacklogValidation:
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_spec_backlog(data: object) -> SpecBacklogValidation:
    result = SpecBacklogValidation()

    if not isinstance(data, dict):
        result.errors.append("top-level must be object")
        return result

    for f in _REQUIRED_TOP_LEVEL_FIELDS:
        if f not in data:
            result.errors.append(f"missing top-level field: {f}")

    if result.errors:
        return result

    if not isinstance(data["schema_version"], int) or isinstance(data["schema_version"], bool):
        result.errors.append("schema_version must be integer")

    if not isinstance(data["created_at"], str):
        result.errors.append("created_at must be string")

    if not isinstance(data["updated_at"], str):
        result.errors.append("updated_at must be string")

    if not isinstance(data["source_refs"], list):
        result.errors.append("source_refs must be list of strings")
    elif not all(isinstance(s, str) for s in data["source_refs"]):
        result.errors.append("source_refs must be list of strings")

    active_spec_id = data["active_spec_id"]
    if active_spec_id is not None and not isinstance(active_spec_id, str):
        result.errors.append("active_spec_id must be null or string")

    if not isinstance(data["specs"], list):
        result.errors.append("specs must be list")
        return result

    seen_ids: set[str] = set()
    spec_map: dict[str, dict] = {}

    for i, spec in enumerate(data["specs"]):
        prefix = f"specs[{i}]"

        if not isinstance(spec, dict):
            result.errors.append(f"{prefix} must be object")
            continue

        for f in _REQUIRED_SPEC_FIELDS:
            if f not in spec:
                result.errors.append(f"{prefix}.missing required field: {f}")

        for f in _STRING_SPEC_FIELDS:
            if f in spec and not isinstance(spec[f], str):
                result.errors.append(f"{prefix}.{f} must be string")

        for f in _LIST_OF_STRINGS_SPEC_FIELDS:
            if f in spec:
                if not isinstance(spec[f], list):
                    result.errors.append(f"{prefix}.{f} must be list of strings")
                elif not all(isinstance(s, str) for s in spec[f]):
                    result.errors.append(f"{prefix}.{f} must be list of strings")

        for f in _OPTIONAL_STRING_FIELDS:
            if f in spec and not isinstance(spec[f], str):
                result.errors.append(f"{prefix}.{f} must be string")

        if "source_refs" in spec:
            if not isinstance(spec["source_refs"], list):
                result.errors.append(f"{prefix}.source_refs must be list of strings")
            elif not all(isinstance(s, str) for s in spec["source_refs"]):
                result.errors.append(f"{prefix}.source_refs must be list of strings")

        status = spec.get("status")
        if isinstance(status, str) and status not in ALLOWED_SPEC_STATUSES:
            result.errors.append(f"{prefix}.invalid status: {status}")

        size_class = spec.get("size_class")
        if isinstance(size_class, str) and size_class not in ALLOWED_SPEC_SIZE_CLASSES:
            result.errors.append(f"{prefix}.invalid size_class: {size_class}")

        target_mat = spec.get("target_materialization")
        if isinstance(target_mat, str) and target_mat not in ALLOWED_TARGET_MATERIALIZATION_STATES:
            result.errors.append(f"{prefix}.invalid target_materialization: {target_mat}")

        spec_id = spec.get("spec_id")
        if isinstance(spec_id, str):
            if spec_id in seen_ids:
                result.errors.append(f"duplicate spec_id: {spec_id}")
            seen_ids.add(spec_id)
            spec_map[spec_id] = spec

    _validate_relationships(result, data, seen_ids, spec_map)

    return result


def _validate_relationships(
    result: SpecBacklogValidation,
    data: dict,
    seen_ids: set[str],
    spec_map: dict[str, dict],
) -> None:
    active_spec_id = data["active_spec_id"]

    if isinstance(active_spec_id, str) and active_spec_id not in seen_ids:
        result.errors.append(f"active_spec_id does not match any spec_id: {active_spec_id}")

    active_status_specs = [
        (sid, s) for sid, s in spec_map.items()
        if s.get("status") in _ACTIVE_STATUSES
    ]

    if len(active_status_specs) > 1:
        result.errors.append("multiple active specs")

    if active_spec_id is None:
        if active_status_specs:
            result.errors.append("multiple active specs")
    elif isinstance(active_spec_id, str) and active_spec_id in seen_ids:
        if len(active_status_specs) == 1:
            actual_id, _ = active_status_specs[0]
            if actual_id != active_spec_id:
                result.errors.append("multiple active specs")

    materialized_specs = [
        sid for sid, s in spec_map.items()
        if s.get("target_materialization") == "MATERIALIZED_TO_SINGLE_SPEC_INPUT"
    ]

    if len(materialized_specs) > 1:
        result.errors.append("multiple materialized-to-single-input specs")

    for i, spec in enumerate(data["specs"]):
        if not isinstance(spec, dict):
            continue
        prefix = f"specs[{i}]"
        status = spec.get("status")
        size_class = spec.get("size_class")
        spec_id = spec.get("spec_id")
        target_mat = spec.get("target_materialization")
        validation_strategy = spec.get("validation_strategy")

        if size_class == "TOO_LARGE" and status in _SELECTION_STATUSES:
            result.errors.append(f"{prefix}.TOO_LARGE cannot be {status}")

        if status in _SELECTION_STATUSES:
            if isinstance(validation_strategy, list) and len(validation_strategy) == 0:
                result.errors.append(f"{prefix}.selected spec requires non-empty validation_strategy")

        if target_mat == "MATERIALIZED_TO_SINGLE_SPEC_INPUT":
            if not isinstance(active_spec_id, str) or spec_id != active_spec_id:
                result.errors.append(f"{prefix}.MATERIALIZED_TO_SINGLE_SPEC_INPUT must be active spec")

        if status == "MATERIALIZED_TO_TARGET" and target_mat != "MATERIALIZED_TO_SINGLE_SPEC_INPUT":
            result.errors.append(f"{prefix}.MATERIALIZED_TO_TARGET requires MATERIALIZED_TO_SINGLE_SPEC_INPUT")

        if target_mat == "MATERIALIZED_TO_SINGLE_SPEC_INPUT" and status != "MATERIALIZED_TO_TARGET":
            result.errors.append(f"{prefix}.MATERIALIZED_TO_SINGLE_SPEC_INPUT requires status MATERIALIZED_TO_TARGET")

        if isinstance(spec.get("dependencies"), list):
            for dep in spec["dependencies"]:
                if not isinstance(dep, str):
                    continue
                if dep == spec_id:
                    result.errors.append(f"{prefix}.must not depend on itself")
                elif dep not in seen_ids:
                    result.errors.append(f"{prefix}.dependency not found: {dep}")
                elif status in _ACTIVE_STATUSES and dep in spec_map:
                    dep_status = spec_map[dep].get("status")
                    if dep_status not in ("DONE", "VALIDATED"):
                        result.errors.append(f"{prefix}.selected dependency not done or validated: {dep}")
