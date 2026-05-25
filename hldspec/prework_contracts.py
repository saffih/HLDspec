from __future__ import annotations

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
    """Return counts of augmented rule types present in constitution.

    Returns a dict like {"CONTRACT": 3, "DATA": 2} based on rule_id prefixes
    of rules in constitution["required_rules"].
    """
    counts: dict[str, int] = {"CONTRACT": 0, "DATA": 0}
    for rule in constitution.get("required_rules", []):
        rule_id = rule.get("rule_id", "") if isinstance(rule, dict) else ""
        if str(rule_id).startswith("CONTRACT-"):
            counts["CONTRACT"] += 1
        elif str(rule_id).startswith("DATA-"):
            counts["DATA"] += 1
    return counts


def augmentation_intact(constitution: dict, expected_counts: dict[str, int]) -> list[str]:
    """Check that augmented rules have not been wiped.

    Returns a list of blocker strings (empty = intact).
    Checks that actual count of each prefix >= expected count.
    """
    actual = augmented_rule_counts(constitution)
    blockers: list[str] = []
    for prefix, expected in expected_counts.items():
        got = actual.get(prefix, 0)
        if got < expected:
            blockers.append(f"{prefix} rules decreased: expected {expected}, got {got}")
    return blockers


def constitution_augmentation_blockers(constitution: dict) -> list[str]:
    """Block if constitution has no CONTRACT-* or DATA-* rules at all
    when required_rules is non-empty.

    Returns blocker strings. An empty constitution (no required_rules) is
    not blocked — augmentation may not have run yet.
    A non-empty constitution with zero CONTRACT-* and zero DATA-* rules
    is a warning, not a hard blocker, so return an empty list unless
    the constitution explicitly claims augmentation was run
    (field: augmentation_applied == True) but rules are missing.
    """
    if constitution.get("augmentation_applied") is True:
        counts = augmented_rule_counts(constitution)
        if counts["CONTRACT"] == 0 and counts["DATA"] == 0:
            return ["constitution has augmentation_applied=True but no CONTRACT-* or DATA-* rules found"]
    return []
