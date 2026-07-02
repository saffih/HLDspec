"""Journey 3 Driver v0 — read-only "where are we?" status aggregator.

The **driver is not the helper.** It answers the journey-level question — package
state, binding, selected/effective helper, phase, blockers, the next *safe human*
action, and the approval boundaries it must never cross — by **composing existing
read-only inspectors**. It never executes a toolchain step, never runs the helper,
never mutates the target, and never auto-selects or approves a helper.

Pure and subprocess-free: this module only reads files (via `target_discovery`,
`helper_selection`, `hld_source_package`, `helper_registry`) and reuses the
boundary constants from `toolchain_driver` (single source of truth — never
re-declared here).

The canonical Journey-3 **phase** (`next_feature_readiness`'s `PHASE_*` enum;
`docs/JOURNEY3_HELPER_CONTRACT.md` §9) is produced by an engine that runs read-only
git, so it is **injected**, not computed here: pass a precomputed
`next_feature_report` to populate `journey3_phase`/evidence/blockers. Absent it, the
phase is reported as `UNKNOWN_REQUIRES_READINESS_RUN` with a next action — never a
lifecycle-ledger proxy wearing the phase name.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import (
    helper_registry,
    helper_selection,
    hld_source_package,
    next_feature_readiness,
    target_discovery,
    toolchain_driver,
)
from .active_spec_completion_facts import build_active_spec_completion_facts
from .source_package_gate_facts import build_source_package_gate_facts_report

SCHEMA_VERSION = 1

# Reuse the driver verdict + boundary vocabulary; do not fork it.
STATUS_PASS = toolchain_driver.DRIVER_STATUS_PASS
STATUS_ACTION = toolchain_driver.DRIVER_STATUS_ACTION
STATUS_BLOCKED = toolchain_driver.DRIVER_STATUS_BLOCKED

# Sentinel for the phase field when no readiness report is injected. Never the
# discovery lifecycle ledger (that is lifecycle, not phase).
PHASE_UNKNOWN_REQUIRES_READINESS_RUN = "UNKNOWN_REQUIRES_READINESS_RUN"


def _effective_helper_mode(effective_helper_id: str | None, registry: dict) -> dict[str, Any]:
    """The effective helper's authority posture, derived from the registry. An
    unknown/non-operational helper falls back to GUIDE_ONLY and is flagged — the
    driver never grants more than the registry records, and v0 executes nothing."""
    record = helper_registry.get_helper(registry, effective_helper_id) if effective_helper_id else None
    operational_ids = {h["helper_id"] for h in helper_registry.operational_helpers(registry)}
    operational = effective_helper_id in operational_ids if effective_helper_id else False
    authority_levels = list(record["authority_levels"]) if record else [helper_registry.AUTHORITY_GUIDE_ONLY]
    return {
        "effective_helper_id": effective_helper_id,
        "operational": operational,
        "authority_levels": authority_levels,
        # v0 has no execution channel regardless of authority.
        "execution": "propose_only_no_execution",
    }


def build_journey3_status(
    target: str | Path,
    *,
    next_feature_report: dict[str, Any] | None = None,
    transition_validation: dict[str, Any] | None = None,
    registry: dict | None = None,
) -> dict[str, Any]:
    """Read-only Journey 3 driver status for `target`. Pure & subprocess-free.

    `next_feature_report` (optional): a precomputed
    `next_feature_readiness.build_next_feature_readiness_report` dict. When given,
    `journey3_phase`/`evidence_found`/`missing_evidence` and phase blockers come
    from it (one source of truth, no divergence). When omitted, phase is reported
    as `UNKNOWN_REQUIRES_READINESS_RUN`.
    """
    target = Path(target).expanduser().resolve()
    reg = helper_registry.build_registry() if registry is None else registry

    # --- Package + binding (subprocess-free, never throws on an absent package) ---
    source_dir, _mirror = hld_source_package.source_package_paths(target, layout="new")
    source_package_present = (source_dir / hld_source_package.SOURCE_PACKAGE_FILE).is_file()
    if source_package_present:
        validation = hld_source_package.validate_source_package(source_dir)
        source_package_validation = {
            "ok": validation.ok,
            "missing": list(validation.missing),
            "hash_mismatches": list(validation.hash_mismatches),
        }
    else:
        source_package_validation = {
            "ok": False,
            "missing": ["source_package.json (package not present)"],
            "hash_mismatches": [],
        }

    discovery = target_discovery.build_target_discovery(target)
    binding = discovery.get("source_package_binding") or {}
    binding_status = binding.get("state") or target_discovery.BINDING_MISSING

    # --- Helper recommendation / selection / effective mode (subprocess-free) ---
    toolchain = helper_selection.build_toolchain_status(target, registry=reg)
    helper_recommendations_present = bool(toolchain["recommendations_present"])
    selected_helper = toolchain["selected_helper_id"]
    helper_selection_present = selected_helper is not None
    effective_helper_id = toolchain["effective_helper_id"]
    effective_helper_mode = _effective_helper_mode(effective_helper_id, reg)

    # --- Phase (injected only; never computed here) ---
    if next_feature_report is not None:
        journey3_phase = next_feature_report.get("phase") or PHASE_UNKNOWN_REQUIRES_READINESS_RUN
        evidence_found = sorted((next_feature_report.get("verified_evidence") or {}).keys())
        phase_missing = list(next_feature_report.get("missing_evidence") or [])
        phase_blockers = list(next_feature_report.get("blockers") or [])
        phase_safety = next_feature_report.get("safety_status")
        phase_next = next_feature_report.get("next_safe_action")
    else:
        journey3_phase = PHASE_UNKNOWN_REQUIRES_READINESS_RUN
        evidence_found = []
        phase_missing = []
        phase_blockers = []
        phase_safety = None
        phase_next = None

    # --- Aggregate: blockers (BLOCKED), actions (ACTION), evidence, next action ---
    blockers: list[str] = []
    actions: list[str] = []
    evidence: list[str] = []
    missing_evidence: list[str] = []

    # Split-brain fails closed before anything else: an authoritative package in
    # both the controller and the target is ambiguous ownership; never auto-pick.
    split_brain_dir = hld_source_package.source_package_split_brain(target)
    if split_brain_dir is not None:
        blockers.append(
            "Source-package split-brain: an authoritative source package exists BOTH at the "
            f"external controller and in-target ({split_brain_dir}). External mode must own "
            "exactly one — this is not auto-repaired. Resolve which is authoritative "
            "(re-externalize, or remove the stale in-target package) before Journey 3."
        )

    if source_package_present:
        evidence.append("source_package present")
    else:
        missing_evidence.append("source package")
        blockers.append(
            f"Source package missing — return to Journey 2 to generate/import {source_dir}/ "
            "before Journey 3."
        )

    if source_package_present and not source_package_validation["ok"]:
        blockers.append(
            "Source package invalid (validate_source_package not ok): "
            f"missing={source_package_validation['missing']} "
            f"hash_mismatches={source_package_validation['hash_mismatches']} — return to Journey 2."
        )
    elif source_package_present:
        evidence.append("source_package validation ok")

    if binding_status in target_discovery.SUSPECT_BINDING_STATES:
        blockers.append(
            f"Source-package binding is {binding_status} — the package does not trust this "
            "target; return to Journey 2 (do not patch around it)."
        )
    elif binding_status == target_discovery.BINDING_BOUND_MATCH:
        evidence.append("binding BOUND_MATCH")
    elif source_package_present:
        actions.append(f"Binding is {binding_status}; re-generate the bound package in Journey 2.")

    if helper_recommendations_present:
        evidence.append("helper_recommendations present")
    else:
        missing_evidence.append("helper_recommendations.json (defaultable)")

    if helper_selection_present:
        evidence.append(f"helper selected: {selected_helper}")
        if not effective_helper_mode["operational"]:
            actions.append(
                f"Selected helper {selected_helper!r} is not operational in the registry; "
                "select an operational helper (the driver does not approve helpers)."
            )
    else:
        missing_evidence.append("helper_selection.json")
        actions.append(
            f"No helper selected. Propose: select a helper (default {effective_helper_id!r}). "
            "The driver never auto-selects — a human must choose."
        )

    # Injected phase signals fold in conservatively.
    missing_evidence.extend(phase_missing)
    # Reference the engine's constant rather than a guessed literal, so a BLOCKED
    # phase can never silently fold into ACTION. (Importing the engine does not run
    # a subprocess; the aggregator still calls none.)
    if phase_safety == next_feature_readiness.SAFETY_BLOCKED:
        blockers.extend(phase_blockers)
    else:
        actions.extend(phase_blockers)

    # --- Transition validation (injected, never computed here) ---
    if transition_validation is not None:
        tv_status = transition_validation.get("status")
        tv_reason = transition_validation.get("reason", "")
        if tv_status and tv_status != "PASS":
            actions.append(f"Transition validation: {tv_status} — {tv_reason}")
        elif tv_status == "PASS":
            evidence.append("transition validation PASS")
    else:
        tv_status = None
        tv_reason = None

    # --- Verdict + single next safe action (BLOCKED > ACTION > PASS) ---
    if blockers:
        driver_status = STATUS_BLOCKED
        next_safe_action = blockers[0]
    elif actions:
        driver_status = STATUS_ACTION
        next_safe_action = actions[0]
    else:
        driver_status = STATUS_PASS
        next_safe_action = phase_next or (
            f"All driver evidence present. Proceed using the {effective_helper_id} helper's "
            "recommended next command — run it yourself; the driver does not execute it."
        )

    source_package_gate_facts_advisory = (
        build_source_package_gate_facts_report(source_dir)
        if source_package_present
        else None
    )

    active_spec_completion_facts_advisory = None
    if source_package_present:
        cfacts = build_active_spec_completion_facts(source_dir)
        active_spec_completion_facts_advisory = {
            "completion_applicable": cfacts.completion_applicable,
            "completion_status": cfacts.completion_status,
            "coverage_scope": cfacts.coverage_scope,
            "active_spec_id": cfacts.active_spec_id,
            "selected_anchor_blocker_count": cfacts.selected_anchor_blocker_count,
            "out_of_scope_advisory_count": cfacts.out_of_scope_advisory_count,
            "receipt_present": cfacts.receipt_present,
            "receipt_type": cfacts.receipt_type,
            "semantic_error_count": cfacts.semantic_error_count,
            "read_error_count": cfacts.read_error_count,
            "reasons": list(cfacts.reasons),
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "driver_status": driver_status,
        "target_root": str(target),
        "source_package_present": source_package_present,
        "source_package_validation": source_package_validation,
        "source_package_gate_facts_advisory": source_package_gate_facts_advisory,
        "active_spec_completion_facts_advisory": active_spec_completion_facts_advisory,
        "binding_status": binding_status,
        "helper_recommendations_present": helper_recommendations_present,
        "helper_selection_present": helper_selection_present,
        "selected_helper": selected_helper,
        "effective_helper_mode": effective_helper_mode,
        "journey3_phase": journey3_phase,
        "phase_source": "injected" if next_feature_report is not None else "not_provided",
        "evidence_found": evidence + evidence_found,
        "missing_evidence": missing_evidence,
        "blockers": blockers,
        "next_safe_action": next_safe_action,
        "forbidden_without_approval": list(toolchain_driver.FORBIDDEN_ACTIONS)
        + list(toolchain_driver.FORBIDDEN_WITHOUT_APPROVAL),
        "protected_approvals_required": list(toolchain_driver.PROTECTED_APPROVAL_BOUNDARIES),
        "transition_validation_status": tv_status,
        "transition_validation_reason": tv_reason,
        # The driver never mutates or executes; surfaced so callers can assert it.
        "mutated_target": False,
        "executed_anything": False,
    }


def _bullets(items: list[str]) -> list[str]:
    return [f"  - {x}" for x in items] if items else ["  (none)"]


def _render_advisory(advisory: dict[str, Any] | None) -> str:
    if advisory is None:
        return "unavailable (no source package)"
    scope = advisory.get("coverage_scope", "?")
    spec_id = advisory.get("active_spec_id", "—")
    blockers = advisory.get("selected_anchor_blocker_count", 0)
    oosa = advisory.get("out_of_scope_advisory_count", 0)
    errors = len(advisory.get("semantic_errors", []))
    return f"scope={scope} spec={spec_id} blockers={blockers} oos_advisory={oosa} errors={errors}"


def _render_completion_advisory(advisory: dict[str, Any] | None) -> str:
    if advisory is None:
        return "unavailable (no source package)"
    status = advisory.get("completion_status", "?")
    spec_id = advisory.get("active_spec_id", "—")
    blockers = advisory.get("selected_anchor_blocker_count", 0)
    sem_err = advisory.get("semantic_error_count", 0)
    read_err = advisory.get("read_error_count", 0)
    return f"status={status} spec={spec_id} blockers={blockers} semantic_errors={sem_err} read_errors={read_err}"


def render_status_text(report: dict[str, Any]) -> str:
    """Human-readable rendering of a driver status report."""
    mode = report["effective_helper_mode"]
    lines = [
        f"# Journey 3 Driver — {report['driver_status']}",
        "",
        f"target_root:                {report['target_root']}",
        f"source_package_present:     {report['source_package_present']}",
        f"source_package_validation:  ok={report['source_package_validation']['ok']}",
        f"source_package_gate_facts:  {_render_advisory(report.get('source_package_gate_facts_advisory'))}",
        f"active_spec_completion:     {_render_completion_advisory(report.get('active_spec_completion_facts_advisory'))}",
        f"binding_status:             {report['binding_status']}",
        f"helper_recommendations:     present={report['helper_recommendations_present']}",
        f"helper_selection:           present={report['helper_selection_present']} "
        f"selected={report['selected_helper']}",
        f"effective_helper_mode:      {mode['effective_helper_id']} "
        f"(operational={mode['operational']}, authority={mode['authority_levels']}, {mode['execution']})",
        f"journey3_phase:             {report['journey3_phase']} (source={report['phase_source']})",
        f"transition_validation:      {report['transition_validation_status'] or 'not_performed'}"
        f"{' — ' + report['transition_validation_reason'] if report.get('transition_validation_reason') else ''}",
        "",
        "evidence_found:",
        *_bullets(report["evidence_found"]),
        "missing_evidence:",
        *_bullets(report["missing_evidence"]),
        "blockers:",
        *_bullets(report["blockers"]),
        "",
        f"NEXT SAFE ACTION (propose-only, not executed):\n  {report['next_safe_action']}",
        "",
        "forbidden without approval:",
        *_bullets(report["forbidden_without_approval"]),
        "protected approvals (owner-only; driver never grants):",
        *_bullets(report["protected_approvals_required"]),
        "",
    ]
    return "\n".join(lines)
