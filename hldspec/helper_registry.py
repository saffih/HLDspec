"""Canonical helper registry (Helper Bootstrap Slice A).

JSON is canonical: the serialized registry dict is the single source of truth for
which helpers HLDspec knows about and what each may do. Any future Markdown
`HELPER.md` is a *generated, explanatory* view and must be stamped GENERATED — it
is never authoritative. See `docs/HELPER_BOOTSTRAP_CONTRACT.md` (lifecycle states,
authority caps) and `docs/JOURNEY3_HELPER_CONTRACT.md` (operational HelperContract).

This slice adds the registry schema, validation, and the first operational helper
(`speckit`). It deliberately does NOT: write into a target repo, emit
`helper_recommendations.json` (Journey 2 advisory output), store a selected helper
(`.hldspec/helper_selection.json`, Journey 3 state), touch runtime
`MANIFEST.json` (provenance only), or generate a NextActionPacket.

`speckit` is the first *operational* helper by prior implementation
(`next_feature_readiness` + the vendored run-card runtime); it predates the
Bootstrap and is recorded here as a retrofit, with no behavior change.
"""
from __future__ import annotations

import json

SCHEMA_VERSION = 1

# --- Lifecycle states (mirror docs/HELPER_BOOTSTRAP_CONTRACT.md §3) -----------
LIFECYCLE_UNKNOWN_TOOL = "UNKNOWN_TOOL"
LIFECYCLE_INSPECTED_TOOL = "INSPECTED_TOOL"
LIFECYCLE_PROPOSED_HELPER = "PROPOSED_HELPER"
LIFECYCLE_REVIEWED_HELPER = "REVIEWED_HELPER"
LIFECYCLE_APPROVED_HELPER = "APPROVED_HELPER"
LIFECYCLE_REJECTED_HELPER = "REJECTED_HELPER"
LIFECYCLE_OPERATIONAL_HELPER = "OPERATIONAL_HELPER"

LIFECYCLE_STATES: tuple[str, ...] = (
    LIFECYCLE_UNKNOWN_TOOL,
    LIFECYCLE_INSPECTED_TOOL,
    LIFECYCLE_PROPOSED_HELPER,
    LIFECYCLE_REVIEWED_HELPER,
    LIFECYCLE_APPROVED_HELPER,
    LIFECYCLE_REJECTED_HELPER,
    LIFECYCLE_OPERATIONAL_HELPER,
)

# Only this state may drive the helper loop.
OPERATIONAL_LIFECYCLE_STATE = LIFECYCLE_OPERATIONAL_HELPER

# --- Authority levels (mirror docs/JOURNEY3_HELPER_CONTRACT.md §7) ------------
AUTHORITY_GUIDE_ONLY = "GUIDE_ONLY"
AUTHORITY_PROPOSE_COMMAND = "PROPOSE_COMMAND"
AUTHORITY_EXECUTE_WITH_APPROVAL = "EXECUTE_WITH_APPROVAL"
AUTHORITY_AUTONOMOUS_WITH_GUARDS = "AUTONOMOUS_WITH_GUARDS"

VALID_AUTHORITY_LEVELS: frozenset[str] = frozenset({
    AUTHORITY_GUIDE_ONLY,
    AUTHORITY_PROPOSE_COMMAND,
    AUTHORITY_EXECUTE_WITH_APPROVAL,
    AUTHORITY_AUTONOMOUS_WITH_GUARDS,
})

# AUTONOMOUS_WITH_GUARDS is future-only and never allowed on a registered helper.
FORBIDDEN_AUTHORITY_LEVELS: frozenset[str] = frozenset({AUTHORITY_AUTONOMOUS_WITH_GUARDS})

# Known helper IDs that are contracted (docs/JOURNEY3_HELPER_CONTRACT.md,
# docs/HELPER_BOOTSTRAP_CONTRACT.md) but have no operational implementation yet.
# Only their IDs and the not-implemented status are canonical here — they carry no
# capabilities. A future slice promotes one into `helpers` via the Bootstrap. This
# is the single source of truth for "known but not-implemented" helper IDs so that
# advisory consumers (e.g. Journey 2 helper_recommendations) never invent the list.
PLANNED_HELPER_IDS: tuple[str, ...] = ("claude-code", "codex", "devin", "manual")

# --- Schema fields -----------------------------------------------------------
# Negative-capability fields. These must be concrete and non-empty for every
# helper (see _is_vague). Concrete negative capability is the load-bearing safety
# property: a helper that cannot say what it will NOT do cannot be trusted.
NEGATIVE_CAPABILITY_FIELDS: tuple[str, ...] = (
    "cannot_do",
    "forbidden_actions",
    "stop_rules",
    "known_limits",
)

REQUIRED_HELPER_FIELDS: tuple[str, ...] = (
    "helper_id",
    "display_name",
    "status",
    "lifecycle_state",
    "toolchain",
    "authority_levels",
    "can_do",
    "cannot_do",
    "required_package_files",
    "required_target_evidence",
    "allowed_actions",
    "forbidden_actions",
    "stop_rules",
    "report_back_format",
    "known_limits",
    "provenance",
)

# Heuristic concreteness check for negative-capability items. This is a guard, not
# a proof: the authoritative guarantee that speckit's negatives are concrete is the
# content-asserting test in tests_v2/test_helper_registry.py. The denylist catches
# the common vague stock phrases; it cannot catch every possible vague wording.
_VAGUE_SUBSTRINGS: tuple[str, ...] = (
    "do unsafe things",
    "unsafe things",
    "if needed",
    "some limitations",
    "be careful",
    "as appropriate",
    "when necessary",
    "stop if needed",
)
_MIN_CONCRETE_LEN = 20


def _is_vague(item: object) -> bool:
    if not isinstance(item, str):
        return True
    text = item.strip().lower()
    if len(text) < _MIN_CONCRETE_LEN:
        return True
    return any(pattern in text for pattern in _VAGUE_SUBSTRINGS)


def build_speckit_helper() -> dict:
    """The one operational helper today. Filled from the existing run-card runtime
    (next_feature_readiness + refresh_target); retrofit only, no behavior change."""
    return {
        "helper_id": "speckit",
        "display_name": "SpecKit",
        "status": "implemented",
        "lifecycle_state": LIFECYCLE_OPERATIONAL_HELPER,
        "toolchain": "SpecKit",
        "authority_levels": [AUTHORITY_GUIDE_ONLY, AUTHORITY_PROPOSE_COMMAND],
        "can_do": [
            "constitution guidance",
            "specify guidance",
            "clarify guidance",
            "plan guidance",
            "tasks guidance",
            "analyze guidance",
            "implement guidance",
        ],
        "cannot_do": [
            "must not invent HLD truth or requirements absent from the source package",
            "must not invent constitution truth not present in constitution.proposed.md",
            "must not silently repair or rewrite the source package",
            "must not invent HLD anchors missing from hld_reference_map.json",
            "must not commit, merge, or push target code",
            "must not execute commands without explicit human approval",
            "must not bypass the Journey 1 SDD-ready gate or the Journey 2 "
            "SOURCE_PACKAGE_APPROVAL_GATE",
        ],
        "required_package_files": [
            "speckit_single_spec_input.md",
            "constitution.proposed.md",
            "implementation_slices.json",
            "engineering_guidelines.md",
        ],
        "required_target_evidence": [
            "git working tree state",
            ".specify/memory/ (proof of a real SpecKit init)",
            "specs/<branch>/ phase artifacts",
        ],
        "allowed_actions": [
            "recommend the next /speckit.* command for the current phase",
            "cite source_package files and HLD anchors as evidence",
            "report phase, blockers, and the single next safe action",
        ],
        "forbidden_actions": [
            "must not run /speckit.plan before /speckit.specify output exists",
            "must not run /speckit.tasks before a /speckit.plan output exists",
            "must not start implementation before the implementation-approval gate",
            "must not commit, merge, or push target code",
            "must not initialize SpecKit or create branches on the human's behalf",
        ],
        "stop_rules": [
            "must stop if source_package validation did not PASS",
            "must stop if a human-owned architecture or source-of-truth question arises",
            "must stop if RunSkeptic returns ACTION or CONFLICT",
            "must stop if target tests fail",
            "must stop at the implementation-approval boundary",
        ],
        "report_back_format": (
            "phase / files read / files changed / questions asked / questions "
            "escalated / RunSkeptic status / tests run / failures / next safe "
            "action / should HLDspec reassess?"
        ),
        "known_limits": [
            "guides SpecKit only; does not drive Claude Code, Codex, Devin, or manual flows",
            "operates read-only at GUIDE_ONLY/PROPOSE_COMMAND; does not execute "
            "SpecKit commands itself",
            "derives phase from durable repo evidence only, never from chat history",
        ],
        "provenance": {
            "source": "pre-existing operational runtime",
            "modules": ["next_feature_readiness", "refresh_target"],
            "onboarded_via": "prior_implementation",
            "note": "predates the Helper Bootstrap; recorded as a retrofit with no behavior change",
        },
    }


def build_registry() -> dict:
    """The canonical registry. JSON serialization of this dict is the source of truth."""
    return {
        "schema_version": SCHEMA_VERSION,
        "helpers": [build_speckit_helper()],
    }


def registry_json(registry: dict | None = None) -> str:
    """Deterministic JSON serialization (sorted keys, fixed indent)."""
    reg = build_registry() if registry is None else registry
    return json.dumps(reg, indent=2, sort_keys=True) + "\n"


def get_helper(registry: dict, helper_id: str) -> dict | None:
    for helper in registry.get("helpers", []):
        if isinstance(helper, dict) and helper.get("helper_id") == helper_id:
            return helper
    return None


def operational_helpers(registry: dict) -> list[dict]:
    """Helpers in the only state allowed to drive the helper loop."""
    return [
        helper
        for helper in registry.get("helpers", [])
        if isinstance(helper, dict)
        and helper.get("lifecycle_state") == OPERATIONAL_LIFECYCLE_STATE
    ]


def implemented_helpers(registry: dict) -> list[dict]:
    """Helpers with status 'implemented'. The canonical 'available helpers' set."""
    return [
        helper
        for helper in registry.get("helpers", [])
        if isinstance(helper, dict) and helper.get("status") == "implemented"
    ]


def default_helper_id(registry: dict) -> str | None:
    """The safe default helper id: the first implemented helper, or None."""
    helpers = implemented_helpers(registry)
    return helpers[0]["helper_id"] if helpers else None


def registry_sha256(registry: dict | None = None) -> str:
    """SHA256 of the canonical registry JSON. Lets advisory consumers record which
    registry version they derived from, so drift is detectable."""
    import hashlib

    return hashlib.sha256(registry_json(registry).encode("utf-8")).hexdigest()


def validate_helper(entry: dict) -> list[str]:
    """Return a list of contract violations for one helper entry. Empty == valid."""
    errors: list[str] = []
    helper_id = entry.get("helper_id", "<missing helper_id>")

    for field_name in REQUIRED_HELPER_FIELDS:
        if field_name not in entry:
            errors.append(f"{helper_id}: missing required field '{field_name}'")

    lifecycle = entry.get("lifecycle_state")
    if lifecycle is not None and lifecycle not in LIFECYCLE_STATES:
        errors.append(f"{helper_id}: invalid lifecycle_state '{lifecycle}'")

    if not entry.get("status"):
        errors.append(f"{helper_id}: status must be non-empty")

    authority = entry.get("authority_levels", [])
    if not isinstance(authority, list) or not authority:
        errors.append(f"{helper_id}: authority_levels must be a non-empty list")
    else:
        for level in authority:
            if level not in VALID_AUTHORITY_LEVELS:
                errors.append(f"{helper_id}: unknown authority level '{level}'")
            if level in FORBIDDEN_AUTHORITY_LEVELS:
                errors.append(
                    f"{helper_id}: authority level '{level}' is future-only and "
                    f"not allowed on a registered helper"
                )

    for field_name in ("can_do", "allowed_actions"):
        value = entry.get(field_name)
        if not isinstance(value, list) or not value:
            errors.append(f"{helper_id}: '{field_name}' must be a non-empty list")

    for field_name in NEGATIVE_CAPABILITY_FIELDS:
        value = entry.get(field_name)
        if not isinstance(value, list) or not value:
            errors.append(
                f"{helper_id}: negative-capability field '{field_name}' must be a "
                f"non-empty list"
            )
            continue
        for item in value:
            if _is_vague(item):
                errors.append(
                    f"{helper_id}: negative-capability item in '{field_name}' is too "
                    f"vague to be enforceable: {item!r}"
                )

    if not isinstance(entry.get("report_back_format"), str) or not entry.get("report_back_format"):
        errors.append(f"{helper_id}: report_back_format must be a non-empty string")

    return errors


def validate_registry(registry: dict) -> list[str]:
    """Return a list of violations for the whole registry. Empty == valid."""
    errors: list[str] = []
    if registry.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"registry schema_version must be {SCHEMA_VERSION}")
    helpers = registry.get("helpers")
    if not isinstance(helpers, list) or not helpers:
        errors.append("registry must have a non-empty 'helpers' list")
        return errors

    seen: set[str] = set()
    for helper in helpers:
        if not isinstance(helper, dict):
            errors.append("each helper must be an object")
            continue
        helper_id = helper.get("helper_id")
        if helper_id in seen:
            errors.append(f"duplicate helper_id '{helper_id}'")
        seen.add(helper_id)
        errors.extend(validate_helper(helper))
    return errors
