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


def augmented_rule_counts(constitution: dict) -> dict[str, int]:
    """Return counts of augmented rule types present in constitution."""
    counts: dict[str, int] = {"CONTRACT": 0, "DATA": 0}
    for rule in constitution.get("required_rules", []):
        rule_id = rule.get("rule_id", "") if isinstance(rule, dict) else ""
        if str(rule_id).startswith("CONTRACT-"):
            counts["CONTRACT"] += 1
        elif str(rule_id).startswith("DATA-"):
            counts["DATA"] += 1
    return counts


def augmentation_intact(constitution: dict, expected_counts: dict[str, int]) -> list[str]:
    """Check that augmented rules have not been wiped. Returns blocker strings."""
    actual = augmented_rule_counts(constitution)
    blockers: list[str] = []
    for prefix, expected in expected_counts.items():
        got = actual.get(prefix, 0)
        if got < expected:
            blockers.append(f"{prefix} rules decreased: expected {expected}, got {got}")
    return blockers


def constitution_augmentation_blockers(constitution: dict) -> list[str]:
    """Block if augmentation_applied=True but no CONTRACT-* or DATA-* rules exist."""
    if constitution.get("augmentation_applied") is True:
        counts = augmented_rule_counts(constitution)
        if counts["CONTRACT"] == 0 and counts["DATA"] == 0:
            return ["constitution has augmentation_applied=True but no CONTRACT-* or DATA-* rules found"]
    return []


REQUIRED_PM_PACK_KEYS = [
    "users",
    "jobs_to_be_done",
    "user_journeys",
    "use_cases",
    "user_stories",
    "acceptance_criteria",
]

REQUIRED_ARCHITECT_PACK_KEYS = [
    "constitution_rules",
    "component_boundaries",
    "interface_contracts",
    "dependency_order",
    "technical_risks",
]

REQUIRED_DOSSIER_FIELDS = [
    "named_capabilities",
    "interface_contracts",
    "data_ownership",
    "integration_paths",
    "dependency_reasons",
    "acceptance_criteria",
]


def missing_pm_pack_keys(pm_pack: dict[str, Any]) -> list[str]:
    """Returns list of missing required keys in the PM pack."""
    missing: list[str] = []
    for key in REQUIRED_PM_PACK_KEYS:
        if not pm_pack.get(key):
            missing.append(key)
    return missing


def missing_architect_pack_keys(arch_pack: dict[str, Any]) -> list[str]:
    """Returns list of missing required keys in the Architect pack."""
    missing: list[str] = []
    for key in REQUIRED_ARCHITECT_PACK_KEYS:
        if not arch_pack.get(key):
            missing.append(key)
    return missing


def shallow_dossier_fields(dossier: dict[str, Any]) -> list[str]:
    """Returns list of missing or empty required fields in the Answer Dossier."""
    missing: list[str] = []
    for key in REQUIRED_DOSSIER_FIELDS:
        if not dossier.get(key):
            missing.append(key)
    return missing


def specs_missing_test_plans(planned_specs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return one entry per spec that is missing required test plan fields.

    Rules:
      - Every spec must have a non-empty `ut_coverage_plan` (unit tests).
      - Specs without `no_direct_user_story: true` must also have a non-empty
        `ui_ux_test_plan` (end-to-end / user-journey tests).

    Returns a list of dicts with keys: spec_id, missing_fields.
    """
    result: list[dict[str, Any]] = []
    for spec in planned_specs:
        if not isinstance(spec, dict):
            continue
        spec_id = str(spec.get("planned_spec_id", "?"))
        missing: list[str] = []

        if not spec.get("ut_coverage_plan"):
            missing.append("ut_coverage_plan")

        is_technical_foundation = bool(spec.get("no_direct_user_story"))
        if not is_technical_foundation and not spec.get("ui_ux_test_plan"):
            missing.append("ui_ux_test_plan")

        if missing:
            result.append({"spec_id": spec_id, "missing_fields": missing})
    return result


def stale_prework_artifacts(sync: Path) -> list[str]:
    """Return blockers if prework artifacts are stale relative to spec_build_plan.json."""
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
