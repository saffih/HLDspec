"""General Toolchain Driver v0 -- read-only navigation/reporting layer.

Two concepts this module keeps distinct:

- Helper: toolchain-specific map/rules/evidence (`helper_registry.py`,
  `helper_selection.py`). Only `speckit` is operational today.
- Driver: the process navigator -- human or system -- that watches state,
  checks the selected helper's sequence/rules/evidence, performs reality
  checks against durable repo evidence (the installed vendored runtime's
  identity), and proposes the next safe step. It never silently runs a
  toolchain step itself.

v0 is read-only: it composes `helper_selection.build_toolchain_status` (which
helper) with the installed runtime's `MANIFEST.json` identity (which
implementation is actually installed), and surfaces any mismatch or missing
evidence as ACTION/BLOCKED rather than a silent PASS. It performs no writes,
no SpecKit invocation, and no autonomous execution. See
docs/TOOLCHAIN_DRIVER_CONTRACT.md.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import control_paths, helper_registry
from . import helper_selection as hsel

SCHEMA_VERSION = 1

DRIVER_STATUS_PASS = "PASS"
DRIVER_STATUS_ACTION = "ACTION"
DRIVER_STATUS_BLOCKED = "BLOCKED"

ACTOR_HUMAN = "human"
ACTOR_SYSTEM = "system"
VALID_DRIVER_ACTORS: frozenset[str] = frozenset({ACTOR_HUMAN, ACTOR_SYSTEM})

DEFAULT_ACTOR = ACTOR_HUMAN
DEFAULT_AUTHORITY = helper_registry.AUTHORITY_GUIDE_ONLY

# Driver authority shares its vocabulary with helper authority levels
# (`helper_registry.VALID_AUTHORITY_LEVELS`): both describe "how far may it
# act", just applied to who/what is driving rather than what a helper
# supports. AUTONOMOUS_WITH_GUARDS stays future-only for the driver too.
VALID_DRIVER_AUTHORITIES = helper_registry.VALID_AUTHORITY_LEVELS
FORBIDDEN_DRIVER_AUTHORITIES = helper_registry.FORBIDDEN_AUTHORITY_LEVELS

FORBIDDEN_ACTIONS: tuple[str, ...] = (
    "Do not edit SpecKit-owned artifacts (spec.md, plan.md, tasks.md, constitution.md) directly.",
    "Do not run SpecKit commands silently or without explicit human approval.",
    "Do not commit, push, or merge without explicit approval.",
    "Do not mutate product/application files.",
    "Do not repair or regenerate files under the hood as a side effect of reporting status.",
)

# --- Driver Authority Contract v0 (docs/DRIVER_AUTHORITY_CONTRACT.md) ----------
# Core product rule encoded here:
#   An automatic (system) driver MAY replace the human *operator*.
#   It MUST NOT automatically replace the human *approver/owner*.
# So approver_replacement_allowed is False for every v0 (actor, authority) mode,
# unconditionally, and the owner-only boundaries below are always reported and
# never granted. "Watch broadly. Touch narrowly."

# Owner/approver-only transitions. The driver never self-approves any of these at
# any authority level; they belong to the human approver/owner. Always reported,
# never granted -- distinct from FORBIDDEN_WITHOUT_APPROVAL (operator-gated).
PROTECTED_APPROVAL_BOUNDARIES: tuple[str, ...] = (
    "approve a new helper",
    "mark a helper OPERATIONAL",
    "change SourceBinding",
    "change ISG Governance",
    "change NextActionPacket / READY policy",
    "mutate product / application code",
    "mutate toolchain-owned or generated artifacts",
    "commit",
    "push",
    "merge",
    "delete a branch",
    "accept unresolved risk",
    "override a BLOCKED or ACTION gate",
)

# Reality-check observation categories. The driver may inspect all of these to
# decide whether reality matches the intended journey state, even outside the
# selected toolchain. Observation never implies mutation.
ALLOWED_OBSERVATIONS: tuple[str, ...] = (
    "git status",
    "worktree ownership",
    "branch / PR / merge state",
    "test result evidence (when available)",
    "helper recommendation",
    "helper selection",
    "installed runtime manifest / helper identity",
    "generated / owned artifact boundary checks",
    "journey phase evidence",
)

# Operator-gated actions: forbidden unless explicitly approved for that action
# and scope. Unlike PROTECTED_APPROVAL_BOUNDARIES these are within the operator
# role once approved -- but v0 performs none of them ("Touch narrowly").
FORBIDDEN_WITHOUT_APPROVAL: tuple[str, ...] = (
    "execute a command or toolchain step (only after explicit per-action "
    "approval; v0 executes nothing)",
    "write to an approved write seam",
)

# Posture for state-changing actions (execution / mutation). v0 never executes,
# so this is the *contracted gate*, not current capability: EXECUTE_WITH_APPROVAL
# reports approval_gated; every other authority reports not_allowed.
POSTURE_NOT_ALLOWED = "not_allowed"
POSTURE_APPROVAL_GATED = "approval_gated"


class InvalidDriverInputError(ValueError):
    pass


def build_authority_profile(actor: str, authority: str) -> dict[str, Any]:
    """Pure Driver Authority Contract v0 view for an (actor, authority) pair.

    Encodes the product rule: a *system* driver may replace the human operator
    (`operator_replacement_allowed`), but no v0 mode may replace the human
    approver/owner (`approver_replacement_allowed` is always False). v0 is
    read-only -- `mutation_allowed`/`execution_allowed` are always False; for
    EXECUTE_WITH_APPROVAL the posture is `approval_gated` to record the
    *contracted* gate, while the booleans stay False because v0 executes
    nothing. Owner-only boundaries are always listed and never granted.

    Validates inputs and raises InvalidDriverInputError on an unknown actor or
    authority, so there is no silent fall-back to unsafe behavior.
    """
    if actor not in VALID_DRIVER_ACTORS:
        raise InvalidDriverInputError(
            f"unknown driver actor: {actor!r} (valid: {sorted(VALID_DRIVER_ACTORS)})"
        )
    if authority not in VALID_DRIVER_AUTHORITIES:
        raise InvalidDriverInputError(
            f"unknown driver authority: {authority!r} (valid: {sorted(VALID_DRIVER_AUTHORITIES)})"
        )

    action_posture = (
        POSTURE_APPROVAL_GATED
        if authority == helper_registry.AUTHORITY_EXECUTE_WITH_APPROVAL
        else POSTURE_NOT_ALLOWED
    )
    return {
        # A system driver may stand in for the human operator; a human driver is
        # one, so there is nothing to "replace".
        "operator_replacement_allowed": actor == ACTOR_SYSTEM,
        # The load-bearing invariant: never, in any v0 mode.
        "approver_replacement_allowed": False,
        # Floor capability: the driver may always watch broadly.
        "observation_allowed": True,
        # v0 touches nothing, regardless of declared authority.
        "mutation_allowed": False,
        "execution_allowed": False,
        # Contracted gate (not v0 capability): see docstring.
        "mutation_posture": action_posture,
        "protected_approval_boundaries": list(PROTECTED_APPROVAL_BOUNDARIES),
        "allowed_observations": list(ALLOWED_OBSERVATIONS),
        "forbidden_without_approval": list(FORBIDDEN_WITHOUT_APPROVAL),
    }


def _installed_runtime_manifest(target: Path) -> dict[str, Any] | None:
    """Read the installed vendored runtime's MANIFEST.json, controller-aware.

    Resolves through `control_paths.resolve_hldspec_dir` -- the same
    pointer-aware resolution `helper_selection`/`refresh_target` use -- so
    external-state mode reads the controller's runtime, never a target-local
    one. Missing or unparsable manifests return None rather than raising;
    callers turn that into an ACTION, not a crash.
    """
    manifest_path = control_paths.resolve_hldspec_dir(target) / "runtime" / "MANIFEST.json"
    if not manifest_path.is_file():
        return None
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data if isinstance(data, dict) else None


def build_driver_report(
    target: Path,
    *,
    actor: str = DEFAULT_ACTOR,
    authority: str = DEFAULT_AUTHORITY,
) -> dict[str, Any]:
    """Read-only General Toolchain Driver v0 report for `target`.

    Composes the existing helper recommendation/selection status with the
    installed runtime's identity evidence and the requested actor/authority.
    Never executes anything; an identity mismatch or missing runtime evidence
    surfaces as ACTION/BLOCKED rather than PASS.
    """
    # Validates actor/authority and raises early, before any filesystem work.
    authority_profile = build_authority_profile(actor, authority)

    toolchain_status = hsel.build_toolchain_status(target)
    effective_helper_id = toolchain_status["effective_helper_id"]

    manifest = _installed_runtime_manifest(target)
    installed_runtime_helper_id = manifest.get("helper_id") if manifest else None
    installed_runtime_toolchain = manifest.get("toolchain") if manifest else None

    notes: list[str] = list(toolchain_status["notes"])
    status = toolchain_status["status"]
    identity_match = False

    if manifest is None:
        status = DRIVER_STATUS_ACTION
        notes.append(
            "No installed runtime manifest (.hldspec/runtime/MANIFEST.json); "
            "run refresh-target --apply after reviewing the refresh plan."
        )
        next_safe_action = "Run refresh-target --apply after reviewing the refresh plan."
    elif installed_runtime_helper_id is None:
        status = DRIVER_STATUS_ACTION
        notes.append(
            "Installed runtime manifest predates helper identity fields; "
            "run refresh-target --apply to refresh it."
        )
        next_safe_action = "Run refresh-target --apply to refresh the installed runtime manifest."
    elif installed_runtime_helper_id != effective_helper_id:
        status = DRIVER_STATUS_ACTION
        notes.append(
            f"Installed runtime helper identity mismatch: manifest says "
            f"{installed_runtime_helper_id!r}, effective helper is {effective_helper_id!r}; "
            "run refresh-target --apply."
        )
        next_safe_action = "Run refresh-target --apply to reinstall the runtime for the effective helper."
    else:
        identity_match = True
        next_safe_action = f"Proceed using the {effective_helper_id} helper's recommended next command."

    authority_allowed = authority not in FORBIDDEN_DRIVER_AUTHORITIES
    if not authority_allowed:
        status = DRIVER_STATUS_BLOCKED
        notes.append(f"Driver authority {authority!r} is future-only and not allowed yet.")
        next_safe_action = "Use an allowed driver authority (GUIDE_ONLY, PROPOSE_COMMAND, or EXECUTE_WITH_APPROVAL)."

    return {
        "schema_version": SCHEMA_VERSION,
        "driver_status": status,
        "driver_actor": actor,
        "driver_authority": authority,
        "recommended_helper_id": toolchain_status["recommended_helper_id"],
        "selected_helper_id": toolchain_status["selected_helper_id"],
        "effective_helper_id": effective_helper_id,
        "installed_runtime_helper_id": installed_runtime_helper_id,
        "installed_runtime_toolchain": installed_runtime_toolchain,
        "identity_match": identity_match,
        "authority_allowed": authority_allowed,
        "next_safe_action": next_safe_action,
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "reality_check_notes": notes,
        **authority_profile,
    }
