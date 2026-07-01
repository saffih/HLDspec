"""Spec Backlog validator and advisory builder — pure functions on already-loaded data.

Validates and builds Python objects against the schema contract defined in
docs/MULTI_SPEC_BACKLOG_AND_ACTIVE_SELECTION.md.

Pure functions only: no filesystem, no child processes, no network, no CLI.
"""
from __future__ import annotations

import copy
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

_SELECTABLE_STATUSES = frozenset({"PLANNED", "READY_FOR_SELECTION"})


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
        if len(active_status_specs) == 0:
            result.errors.append("active_spec_id set but no spec has active status")
        elif len(active_status_specs) == 1:
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


def _anchor_source_refs(meta: dict, fallback: list[str]) -> list[str]:
    raw = meta.get("source_refs")
    if isinstance(raw, list) and all(isinstance(s, str) for s in raw):
        return list(raw)

    raw = meta.get("source_ref")
    if isinstance(raw, str):
        return [raw]

    return list(fallback)


def build_advisory_spec_backlog(
    hld_references: object,
    *,
    created_at: str,
    updated_at: str,
    source_refs: list[str] | None = None,
) -> dict:
    """Build an advisory spec backlog from an already-loaded HLD reference map.

    Accepted input shape (as produced by ``hld_marking.build_reference_map``):

        {"schema_version": <int>, "anchors": {<anchor_id>: {"title": ..., ...}, ...}}

    Each anchor becomes one advisory candidate spec with status ``PLANNED``.
    No spec is selected, materialized, or marked ready.

    If *hld_references* is not a dict or has no ``anchors`` dict, an empty
    valid backlog is returned.

    Raises ``ValueError`` if the generated backlog fails validation (should
    not happen by construction).
    """
    resolved_source_refs = list(source_refs) if source_refs is not None else []

    anchors: dict = {}
    if isinstance(hld_references, dict):
        raw = hld_references.get("anchors")
        if isinstance(raw, dict):
            anchors = raw

    specs: list[dict] = []
    for i, (anchor_id, meta) in enumerate(anchors.items(), start=1):
        meta = meta if isinstance(meta, dict) else {}
        title_raw = meta.get("title")
        if isinstance(title_raw, str) and title_raw:
            title = title_raw
            capability = title_raw
        else:
            title = f"Candidate spec for {anchor_id}"
            capability = f"Address {anchor_id}"

        specs.append({
            "spec_id": f"SPEC-{i:03d}",
            "title": title,
            "hld_anchor_ids": [anchor_id],
            "capability": capability,
            "status": "PLANNED",
            "size_class": "BOUNDED_DELIVERABLE",
            "dependencies": [],
            "validation_strategy": ["focused_tests", "contract_validation"],
            "target_materialization": "NOT_MATERIALIZED",
            "source_refs": _anchor_source_refs(meta, resolved_source_refs),
            "reason": "Advisory candidate derived from HLD reference map.",
        })

    backlog: dict = {
        "schema_version": 1,
        "created_at": created_at,
        "updated_at": updated_at,
        "source_refs": resolved_source_refs,
        "active_spec_id": None,
        "specs": specs,
    }

    validation = validate_spec_backlog(backlog)
    if not validation.ok:
        raise ValueError(
            "generated spec backlog is invalid: " + "; ".join(validation.errors)
        )

    return backlog


def _markdown_scalar(value: str) -> str:
    sanitized = value.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    return " ".join(sanitized.split())


def _format_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- {_markdown_scalar(item)}" for item in items)


def _format_hld_anchor_list(items: list[str]) -> str:
    if not items:
        return "- None"
    return "\n".join(f"- ({_markdown_scalar(item)})" for item in items)


def render_active_spec_to_single_spec_input(backlog: object) -> str:
    validation = validate_spec_backlog(backlog)
    if not validation.ok:
        raise ValueError(
            "input spec backlog is invalid: " + "; ".join(validation.errors)
        )

    active_spec_id = backlog["active_spec_id"]
    if not isinstance(active_spec_id, str) or not active_spec_id:
        raise ValueError("active_spec_id is required")

    active_spec = None
    for spec in backlog["specs"]:
        if spec["spec_id"] == active_spec_id:
            active_spec = spec
            break

    if active_spec is None:
        raise ValueError(f"active spec not found: {active_spec_id}")

    if active_spec["status"] != "SELECTED":
        raise ValueError(
            f"active spec must have status SELECTED: {active_spec_id}"
        )

    if active_spec["target_materialization"] != "NOT_MATERIALIZED":
        raise ValueError(
            f"active spec must not be materialized: {active_spec_id}"
        )

    source_refs = active_spec.get("source_refs", [])
    if not isinstance(source_refs, list):
        source_refs = []

    lines = [
        "# Active Spec Input",
        "",
        "<!-- Generated from spec_backlog.json active spec. Advisory planning artifact. -->",
        "",
        "## Selected Spec",
        "",
        f"- Spec ID: {_markdown_scalar(active_spec['spec_id'])}",
        f"- Title: {_markdown_scalar(active_spec['title'])}",
        f"- Capability: {_markdown_scalar(active_spec['capability'])}",
        f"- Status: {_markdown_scalar(active_spec['status'])}",
        f"- Target Materialization: {_markdown_scalar(active_spec['target_materialization'])}",
        "",
        "## HLD Anchors",
        "",
        _format_hld_anchor_list(active_spec["hld_anchor_ids"]),
        "",
        "## Dependencies",
        "",
        _format_list(active_spec["dependencies"]),
        "",
        "## Validation Strategy",
        "",
        _format_list(active_spec["validation_strategy"]),
        "",
        "## Source References",
        "",
        _format_list(source_refs),
        "",
        "## Boundary",
        "",
        "This input represents one selected active spec only.",
        "Do not implement unrelated backlog candidates.",
        "Do not treat this as proof of semantic completeness.",
        "",
    ]

    return "\n".join(lines)


def select_active_spec(backlog: object, spec_id: str) -> dict:
    if not isinstance(spec_id, str):
        raise ValueError("spec_id must be string")

    validation = validate_spec_backlog(backlog)
    if not validation.ok:
        raise ValueError(
            "input spec backlog is invalid: " + "; ".join(validation.errors)
        )

    if backlog["active_spec_id"] is not None:
        raise ValueError(
            "cannot select spec because another active spec already exists"
        )

    for spec in backlog["specs"]:
        if spec["status"] in _ACTIVE_STATUSES:
            raise ValueError(
                "cannot select spec because another active spec already exists"
            )

    spec_map: dict[str, dict] = {s["spec_id"]: s for s in backlog["specs"]}

    if spec_id not in spec_map:
        raise ValueError(f"spec_id not found: {spec_id}")

    candidate = spec_map[spec_id]

    if candidate["status"] not in _SELECTABLE_STATUSES:
        raise ValueError(
            f"cannot select spec with status {candidate['status']}: {spec_id}"
        )

    if candidate["size_class"] == "TOO_LARGE":
        raise ValueError(f"cannot select TOO_LARGE spec: {spec_id}")

    if not candidate["validation_strategy"]:
        raise ValueError(
            f"cannot select spec without validation_strategy: {spec_id}"
        )

    if candidate["target_materialization"] != "NOT_MATERIALIZED":
        raise ValueError(
            f"cannot select spec with target_materialization "
            f"{candidate['target_materialization']}: {spec_id}"
        )

    for dep in candidate["dependencies"]:
        dep_status = spec_map[dep]["status"]
        if dep_status not in ("DONE", "VALIDATED"):
            raise ValueError(
                f"cannot select spec with unresolved dependency: "
                f"{spec_id} -> {dep}"
            )

    selected = copy.deepcopy(backlog)
    selected["active_spec_id"] = spec_id
    for spec in selected["specs"]:
        if spec["spec_id"] == spec_id:
            spec["status"] = "SELECTED"
            break

    output_validation = validate_spec_backlog(selected)
    if not output_validation.ok:
        raise ValueError(
            "selected spec backlog is invalid: "
            + "; ".join(output_validation.errors)
        )

    return selected
