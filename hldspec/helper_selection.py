"""Journey 3 selected-helper state — `.hldspec/helper_selection.json`.

Separate from (and never copied from) two other artifacts:

- `source_package/helper_recommendations.json` — Journey 2's advisory output:
  which helper it recommends for *this package*, and why. Written by
  `hld_source_package.build_helper_recommendations`.
- `hldspec/helper_registry.py` — the canonical helper-capability registry.

This module records which helper the human/agent actually *selected*, and reads
it back together with the recommendation to report Journey 3's effective
toolchain status. It writes only under the HLDspec-owned control dir resolved by
`control_paths.resolve_hldspec_dir` (pointer-aware: external-state mode relocates
`.hldspec` to a controller root), never into a toolchain's own files.

See `docs/TOOLCHAIN_DRIVER_BOUNDARY.md` and `docs/JOURNEY3_HELPER_CONTRACT.md` §8.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import control_paths, helper_registry
from .workspace_adapter import TargetWorkspaceAdapter

SCHEMA_VERSION = 1
SELECTION_FILENAME = "helper_selection.json"

SOURCE_EXPLICIT = "explicit"
SOURCE_DEFAULT = "default"

VALID_SOURCES: frozenset[str] = frozenset({SOURCE_EXPLICIT, SOURCE_DEFAULT})


class InvalidHelperSelectionError(ValueError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def selection_path(target: Path) -> Path:
    return control_paths.resolve_hldspec_dir(target) / SELECTION_FILENAME


def recommendations_path(target: Path) -> Path:
    return (
        TargetWorkspaceAdapter(
            target_root=target,
            layout="new",
            controller_root=control_paths.resolve_controller_root(target),
        ).source_package_dir
        / "helper_recommendations.json"
    )


def read_helper_selection(target: Path) -> dict[str, Any] | None:
    path = selection_path(target)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_helper_recommendations(target: Path) -> dict[str, Any] | None:
    path = recommendations_path(target)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def recommendations_current(recommendations: dict[str, Any] | None, registry: dict | None = None) -> bool:
    """True if `recommendations` was derived from the registry as it is now."""
    if not isinstance(recommendations, dict):
        return False
    provenance = recommendations.get("registry_provenance")
    if not isinstance(provenance, dict):
        return False
    return provenance.get("registry_sha256") == helper_registry.registry_sha256(registry)


def write_helper_selection(
    target: Path,
    helper_id: str,
    *,
    selected_by: str,
    source: str = SOURCE_EXPLICIT,
    registry: dict | None = None,
) -> Path:
    """Write `.hldspec/helper_selection.json`. Validates `helper_id` against the
    canonical registry's *operational* helpers — a planned-but-not-implemented
    helper id (e.g. `claude-code`, `codex`, `devin`, `manual`) is rejected, the
    same way an unknown `tool:<helper_id>` lens provenance is rejected.
    """
    if source not in VALID_SOURCES:
        raise InvalidHelperSelectionError(f"unknown selection source: {source!r}")

    reg = helper_registry.build_registry() if registry is None else registry
    operational_ids = {helper["helper_id"] for helper in helper_registry.operational_helpers(reg)}
    if helper_id not in operational_ids:
        raise InvalidHelperSelectionError(
            f"helper_id {helper_id!r} is not an operational helper "
            f"(operational: {sorted(operational_ids) or 'none'}); "
            "planned helper ids are not selectable until they reach OPERATIONAL_HELPER."
        )

    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "selected_helper_id": helper_id,
        "selected_at": _utc_now(),
        "selected_by": selected_by,
        "source": source,
        "registry_provenance": {
            "schema_version": reg.get("schema_version"),
            "registry_sha256": helper_registry.registry_sha256(reg),
        },
    }
    path = selection_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def build_toolchain_status(target: Path, *, registry: dict | None = None) -> dict[str, Any]:
    """Composite Journey 3 toolchain/helper status for a target.

    Never BLOCKED on a missing selection or a missing/stale recommendation — a
    missing recommendation is an ACTION-class, defaultable condition
    (docs/JOURNEY3_HELPER_CONTRACT.md §8), not a license to refuse guidance.
    """
    reg = helper_registry.build_registry() if registry is None else registry
    default_id = helper_registry.default_helper_id(reg)

    recommendations = read_helper_recommendations(target)
    recommendations_present = recommendations is not None
    recommendations_is_current = recommendations_current(recommendations, reg) if recommendations_present else False
    recommended_helper_id = (
        recommendations.get("default_helper") if isinstance(recommendations, dict) else None
    ) or default_id

    selection = read_helper_selection(target)
    selected_helper_id = selection.get("selected_helper_id") if isinstance(selection, dict) else None

    effective_helper_id = selected_helper_id or recommended_helper_id
    status = "PASS" if selected_helper_id else "ACTION"
    notes: list[str] = []
    if not selected_helper_id:
        notes.append(
            f"No helper_selection.json; defaulting to recommended helper {recommended_helper_id!r}."
        )
    if recommendations_present and not recommendations_is_current:
        notes.append("helper_recommendations.json is stale relative to the current helper registry.")
    if not recommendations_present:
        notes.append("helper_recommendations.json not present; defaulting to the registry default helper.")

    return {
        "schema_version": SCHEMA_VERSION,
        "toolchain": "SpecKit",
        "status": status,
        "recommended_helper_id": recommended_helper_id,
        "recommendations_present": recommendations_present,
        "recommendations_current": recommendations_is_current,
        "selected_helper_id": selected_helper_id,
        "effective_helper_id": effective_helper_id,
        "notes": notes,
    }
