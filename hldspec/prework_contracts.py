from __future__ import annotations

from pathlib import Path
from typing import Any


REQUIRED_CONSTITUTION_KEYS = [
    "source_of_truth_hierarchy",
    "architecture_layer_model",
    "interface_taxonomy",
    "split_rules",
    "no_invention_rules",
    "checkpoint_triage_rules",
    "speckit_boundaries",
    "validation_gates",
]


def missing_constitution_keys(context: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key in REQUIRED_CONSTITUTION_KEYS:
        if not context.get(key):
            missing.append(key)
    return missing


def architecture_disposition_blockers(arch: dict[str, Any], disposition: dict[str, Any]) -> list[str]:
    if arch.get("status") != "ARCHITECTURE_REVIEW_REQUIRED":
        return []
    findings = [item for item in arch.get("findings", []) if isinstance(item, dict)]
    if not findings:
        return []
    if not disposition:
        return [f"architecture review has {len(findings)} finding(s) requiring disposition"]
    if disposition.get("status") not in {"DISPOSITIONED", "APPROVED"}:
        return [f"architecture disposition status is {disposition.get('status', 'MISSING')}"]

    finding_ids = {str(item.get("finding_id")) for item in findings if item.get("finding_id")}
    records = disposition.get("dispositions", [])
    if not isinstance(records, list):
        return ["architecture disposition records are missing or invalid"]
    covered = {str(item.get("finding_id")) for item in records if isinstance(item, dict) and item.get("finding_id")}
    missing = sorted(finding_ids - covered)
    if missing:
        return [f"architecture disposition missing {len(missing)} finding(s): {', '.join(missing[:5])}"]

    unresolved = [
        str(item.get("finding_id"))
        for item in records
        if isinstance(item, dict) and str(item.get("disposition", "")).upper() in {"", "TBD", "CONFLICT", "UNRESOLVED"}
    ]
    if unresolved:
        return [f"architecture disposition has {len(unresolved)} unresolved finding(s): {', '.join(unresolved[:5])}"]
    return []


def stale_prework_artifacts(sync: Path) -> list[str]:
    """Return list of blocker strings if prework artifacts are stale relative to spec_build_plan.json.

    Stale = spec_build_plan.json was modified more recently than the prework artifact.
    Returns [] if plan does not exist, if prework does not exist, or if prework is newer.
    Only blocks when BOTH plan and prework exist AND plan is newer.
    """
    plan = sync / "spec_build_plan.json"
    if not plan.exists():
        return []

    plan_mtime = plan.stat().st_mtime
    blockers: list[str] = []

    prework = sync / "speckit_prework_package.md"
    if prework.exists() and plan_mtime > prework.stat().st_mtime:
        blockers.append(
            "speckit_prework_package.md is stale: spec_build_plan.json was modified after prework was built"
        )

    queue = sync / "speckit_invocation_queue.json"
    if queue.exists() and plan_mtime > queue.stat().st_mtime:
        blockers.append(
            "speckit_invocation_queue.json is stale: spec_build_plan.json was modified after queue was built"
        )

    return blockers
