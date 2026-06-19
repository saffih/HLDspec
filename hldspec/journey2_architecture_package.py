"""Journey 2 Architecture Package Contract v0 -- pure validation helpers.

Journey 2 (`docs/THREE_JOURNEYS.md`) turns an SDD-ready HLD into the architecture
wisdom and slice design that Journey 3 realizes. This module is the deterministic,
machine-checkable shape of that *architecture package*: a design-reasoning view
that organizes HLD-grounded constraints, contracts/seams, expert-lens findings,
and a reviewable slice roadmap. See docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md.

This module is intentionally minimal and side-effect free:

- It only *validates* a package dict; it never generates one, reads the
  filesystem, mutates anything, runs a helper, or changes helper selection.
- It is not wired into any gate or pipeline -- it is a contract slice, a shape a
  package author (human or upstream tool) can check against.

`helper_recommendation` is treated as an opaque required field: validation checks
only that it is present and non-empty. It does not import or call
`helper_selection`, and the recommendation's *value* never affects the verdict --
selection semantics live elsewhere and are unchanged here.
"""
from __future__ import annotations

from typing import Any

STATUS_PASS = "PASS"
STATUS_ACTION = "ACTION"

# The 14 required top-level sections of a Journey 2 architecture package.
REQUIRED_ARCHITECTURE_PACKAGE_FIELDS: tuple[str, ...] = (
    "product_goal_summary",
    "architecture_intent",
    "source_of_truth_map",
    "ownership_boundaries",
    "contracts_and_seams",
    "brownfield_constraints",
    "expert_lenses_applied",
    "domain_assumptions",
    "slice_roadmap",
    "next_slice_packet",
    "test_strategy",
    "forbidden_shortcuts",
    "growth_and_change_notes",
    "helper_recommendation",
)

# Every slice in `slice_roadmap` must carry these 12 fields. A slice that cannot
# state its tests, its rollback story, or what it may not change is not a
# reviewable, architecture-preserving slice.
REQUIRED_SLICE_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "purpose",
    "layer",
    "allowed_changes",
    "forbidden_changes",
    "expected_files_or_areas",
    "required_tests",
    "dependency_ids",
    "risk_level",
    "rollback_story",
    "architecture_value",
)

# Fields that must be *present* but may legitimately be empty. A root slice has no
# dependencies, so an empty `dependency_ids` is valid -- forcing it non-empty
# would make authors invent fake dependencies. The key must still be present, so
# the author has explicitly considered dependencies.
SLICE_FIELDS_ALLOW_EMPTY: frozenset[str] = frozenset({"dependency_ids"})

# Built-in v0 expert lenses. Names only -- the lens *findings* live in the
# package's `expert_lenses_applied` section; this is the canonical vocabulary.
BUILTIN_EXPERT_LENSES: tuple[str, ...] = (
    "software_architecture",
    "brownfield_integration",
    "contracts_and_seams",
    "ai_agent_toolchain_safety",
    "test_and_evidence",
    "git_worktree_pr_lifecycle",
    "slice_quality",
)

# Substrings that mark a slice as too broad to be reviewable/testable in one
# pass. Matched case-insensitively against a slice's name + purpose. This catches
# the obvious mega-slice phrasing; it cannot catch every vague wording, and it
# does not prove a slice is *well* scoped -- only that it is not blatantly broad.
MEGA_SLICE_PHRASES: tuple[str, ...] = (
    "implement the whole",
    "the whole feature",
    "implement everything",
    "refactor everything",
    "rewrite everything",
    "add automation",
    "fix architecture",
    "big bang",
)


def _is_empty(value: Any) -> bool:
    """A required field is satisfied only if present and non-empty. None, empty
    string/list/dict all count as missing -- so "no expert lenses", "empty slice
    roadmap", and "no contracts/seams" are all the same ACTION condition."""
    if value is None:
        return True
    if isinstance(value, (str, list, tuple, dict, set)):
        return len(value) == 0
    return False


def _slice_label(slice_obj: dict[str, Any], index: int) -> str:
    raw_id = slice_obj.get("id") if isinstance(slice_obj, dict) else None
    return str(raw_id) if raw_id else f"#{index}"


def _validate_slice(slice_obj: Any, index: int) -> list[str]:
    """Return findings for one slice. Empty == the slice is well-formed."""
    if not isinstance(slice_obj, dict):
        return [f"slice {index}: not an object"]

    findings: list[str] = []
    label = _slice_label(slice_obj, index)

    for field_name in REQUIRED_SLICE_FIELDS:
        if field_name not in slice_obj:
            findings.append(f"slice {label}: missing required field '{field_name}'")
        elif _is_empty(slice_obj.get(field_name)) and field_name not in SLICE_FIELDS_ALLOW_EMPTY:
            findings.append(f"slice {label}: missing required field '{field_name}'")

    name = str(slice_obj.get("name") or "")
    purpose = str(slice_obj.get("purpose") or "")
    haystack = f"{name} {purpose}".lower()
    for phrase in MEGA_SLICE_PHRASES:
        if phrase in haystack:
            findings.append(
                f"slice {label}: too broad -- phrase {phrase!r} signals a "
                f"mega-slice; split into reviewable, testable slices"
            )

    return findings


def validate_architecture_package(package: Any) -> dict[str, Any]:
    """Validate a Journey 2 architecture package dict. Pure and deterministic.

    Returns:
        {
            "status": "PASS" | "ACTION",
            "missing_fields": [...],   # absent or empty required top-level fields
            "slice_findings": [...],   # per-slice issues (missing field / too broad)
            "notes": [...],            # human-readable summary lines
        }

    ACTION when any required top-level field is missing/empty or any slice has a
    finding; PASS only when the package is structurally complete. There is no
    BLOCKED state -- structural completeness is repairable, so this gate is
    PASS/ACTION only (deeper human/RunSkeptic review owns BLOCKED-class calls).
    """
    missing_fields: list[str] = []
    slice_findings: list[str] = []
    notes: list[str] = []

    if not isinstance(package, dict):
        return {
            "status": STATUS_ACTION,
            "missing_fields": list(REQUIRED_ARCHITECTURE_PACKAGE_FIELDS),
            "slice_findings": [],
            "notes": ["package is not an object"],
        }

    for field_name in REQUIRED_ARCHITECTURE_PACKAGE_FIELDS:
        if field_name not in package or _is_empty(package.get(field_name)):
            missing_fields.append(field_name)

    # Per-slice checks run only when a non-empty roadmap is present; an empty or
    # missing roadmap is already reported as a missing top-level field above.
    roadmap = package.get("slice_roadmap")
    if isinstance(roadmap, list):
        for index, slice_obj in enumerate(roadmap):
            slice_findings.extend(_validate_slice(slice_obj, index))

    if missing_fields:
        notes.append(
            f"missing or empty required fields: {', '.join(missing_fields)}"
        )
    if slice_findings:
        notes.append(f"{len(slice_findings)} slice finding(s) require attention")

    status = STATUS_ACTION if (missing_fields or slice_findings) else STATUS_PASS
    if status == STATUS_PASS:
        notes.append("architecture package is structurally complete")

    return {
        "status": status,
        "missing_fields": missing_fields,
        "slice_findings": slice_findings,
        "notes": notes,
    }
