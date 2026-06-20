"""Journey 2 Architecture Package Contract v0 -- pure validation helpers.

Journey 2 (`docs/THREE_JOURNEYS.md`) turns an SDD-ready HLD into the architecture
wisdom and slice design that Journey 3 realizes. This module is the deterministic,
machine-checkable shape of that *architecture package*: a design-reasoning view
that organizes HLD-grounded constraints, contracts/seams, expert-lens findings,
and a reviewable slice roadmap. See docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md.

This module is intentionally minimal and side-effect free (pure functions only --
no filesystem reads, no mutation, no helper run, no helper-selection change):

- `validate_architecture_package` validates a package dict against the required
  shape.
- `build_architecture_package` builds the advisory typed-slot dict (the human-owned
  architecture fields left empty, only `helper_recommendation` grounded via an
  injected value). It returns a dict and writes nothing.

The package builder (`hld_source_package.build_source_package_content`) persists
that dict as the advisory `architecture_package.json` artifact -- manifest-hashed
but excluded from `REQUIRED_FILES`, the `.specify` mirror, and every gate, so it
is informational and blocks no promotion. Neither function reads the filesystem or
is wired into a gate; emission lives in the package builder, not here.

`helper_recommendation` is treated as an opaque required field: validation checks
only that it is present and non-empty. This module does not import or call
`helper_selection` (or `helper_registry`), and the recommendation's *value* never
affects the verdict -- selection semantics live elsewhere and are unchanged here.
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


ARCHITECTURE_PACKAGE_SCHEMA_VERSION = 0


def _empty_architecture_fields() -> dict[str, Any]:
    """The 14 required fields as an EMPTY typed slot.

    Human-owned architecture reasoning is intentionally left empty so
    `validate_architecture_package` returns ACTION until it is authored. The
    emitter never fabricates architecture truth the HLD/human did not decide
    (`docs/JOURNEY2_PACKAGE_CONTRACT.md` §8) -- it materializes the typed slot so
    the gap is *visible and authorable*, not absent. `helper_recommendation` is
    filled by the caller from the registry-derived recommendations (the one
    genuinely grounded field); everything else awaits authorship.
    """
    return {
        "product_goal_summary": "",
        "architecture_intent": "",
        "source_of_truth_map": {},
        "ownership_boundaries": {},
        "contracts_and_seams": [],
        "brownfield_constraints": [],
        "expert_lenses_applied": {},
        "domain_assumptions": [],
        "slice_roadmap": [],
        "next_slice_packet": {},
        "test_strategy": "",
        "forbidden_shortcuts": [],
        "growth_and_change_notes": "",
        "helper_recommendation": {},
    }


def build_architecture_package(*, helper_recommendation: Any = None) -> dict[str, Any]:
    """Emit an ADVISORY Journey 2 architecture package artifact (the typed slot).

    Pure and side-effect free: returns a dict, writes nothing. The package builder
    (`hld_source_package.build_source_package_content`) persists it as
    `architecture_package.json`, mirroring `helper_recommendations.json`.

    The 14 required fields are present, but the human-owned architecture-reasoning
    fields are left **empty** -- this emitter never invents architecture the HLD/
    human did not decide (`docs/JOURNEY2_PACKAGE_CONTRACT.md` §8). The only grounded
    field is `helper_recommendation`, injected by the caller from the
    registry-derived recommendations. This module imports neither `helper_selection`
    nor `helper_registry`, so helper-selection semantics are unchanged.

    The artifact embeds its own `validate_architecture_package` result, so it
    honestly reports **ACTION** ("fields await authorship") until authored. It is
    advisory: excluded from `REQUIRED_FILES` and the `.specify` mirror and wired
    into no gate -- an ACTION artifact promotes nothing.

    `next_slice_packet` is descriptive data, never an execution channel /
    NextActionPacket (`docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md` §3).
    """
    fields = _empty_architecture_fields()
    if helper_recommendation is not None:
        fields["helper_recommendation"] = helper_recommendation
    validation = validate_architecture_package(fields)
    return {
        "schema_version": ARCHITECTURE_PACKAGE_SCHEMA_VERSION,
        "advisory": True,
        **fields,
        "validation": validation,
        "notes": [
            "Advisory Journey 2 architecture package (typed slot). Human-owned "
            "architecture-reasoning fields are left empty until authored; this "
            "emitter never invents architecture truth (JOURNEY2_PACKAGE_CONTRACT.md §8).",
            "helper_recommendation is derived from the helper registry (advisory); "
            "its value never drives helper selection.",
            "next_slice_packet is descriptive data, not a NextActionPacket / "
            "execution channel (JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md §3).",
            "Excluded from REQUIRED_FILES and the .specify mirror; wired into no "
            "gate. status ACTION here promotes nothing.",
        ],
    }


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
