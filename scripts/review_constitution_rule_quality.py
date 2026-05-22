#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


STATUS_PASS = "PASS"
STATUS_PENDING = "PENDING_HUMAN_REVIEW"
STATUS_REWORK = "REWORK_REQUIRED"


FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "rule": ("rule", "text", "statement", "title"),
    "rationale": ("rationale", "why"),
    "hld_evidence": ("hld_evidence", "evidence", "source_hld_sections", "source_hld_refs", "hld_refs"),
    "violation_example": ("violation_example", "counterexample", "example_violation"),
    "speckit_phase_enforced": ("speckit_phase_enforced", "phase_enforced", "enforced_in", "speckit_phase"),
    "affected_artifacts": ("affected_artifacts", "artifacts", "outputs"),
    "open_question": ("open_question", "open_questions", "human_decision", "question"),
}


RULE_LIST_KEYS = (
    "constitution_rules",
    "proposed_constitution_rules",
    "required_constitution_rules",
    "rules",
    "updates",
)


@dataclass
class Finding:
    severity: str
    decision: str
    rule_index: int
    field: str
    message: str


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, list | tuple | set | dict):
        return len(value) == 0
    return False


def normalize_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True)
    return str(value).strip()


def value_for(rule: dict[str, Any], canonical: str) -> Any:
    for key in FIELD_ALIASES[canonical]:
        if key in rule:
            return rule[key]
    return None


def open_question_is_resolved(value: Any) -> bool:
    text = normalize_text(value).lower()
    return text in {"", "none", "n/a", "na", "no", "not applicable", "resolved"}


def evidence_is_specific(value: Any) -> bool:
    if is_empty(value):
        return False
    text = normalize_text(value)
    return "HLD-" in text or "source" in text.lower() or len(text) >= 12


def rule_text_is_generic(value: Any) -> bool:
    text = normalize_text(value).lower()
    generic_exact = {
        "hld.md is the design source of truth.",
        "hld sections are design source units, not specs.",
        "specs are capability units.",
        "specs are built bottom-up.",
        "api contracts are first-class when specs interact.",
    }
    return text in generic_exact


def extract_rules_from_value(value: Any, source_key: str = "root") -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []

    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                rule = dict(item)
                rule.setdefault("_source_key", source_key)
                rule.setdefault("_raw_type", "dict")
                rules.append(rule)
            elif isinstance(item, str):
                rules.append({"rule": item, "_source_key": source_key, "_raw_type": "string"})
        return rules

    if isinstance(value, dict):
        for key in RULE_LIST_KEYS:
            if isinstance(value.get(key), list):
                rules.extend(extract_rules_from_value(value[key], key))

        nested = value.get("constitution_update_plan")
        if isinstance(nested, dict):
            rules.extend(extract_rules_from_value(nested, "constitution_update_plan"))
        return rules

    return rules


def review_rule(rule: dict[str, Any], index: int) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    normalized: dict[str, Any] = {
        "index": index,
        "source_key": rule.get("_source_key", "unknown"),
        "raw_type": rule.get("_raw_type", "dict"),
    }

    for field in FIELD_ALIASES:
        value = value_for(rule, field)
        normalized[field] = value
        if is_empty(value):
            findings.append(
                Finding(
                    severity="BLOCKER",
                    decision="FIX",
                    rule_index=index,
                    field=field,
                    message=f"Constitution rule is missing required field `{field}`.",
                )
            )

    if normalized.get("rule") and rule_text_is_generic(normalized["rule"]) and is_empty(normalized.get("hld_evidence")):
        findings.append(
            Finding(
                severity="BLOCKER",
                decision="FIX",
                rule_index=index,
                field="hld_evidence",
                message="Generic constitution rule must include concrete HLD evidence before approval.",
            )
        )

    if not evidence_is_specific(normalized.get("hld_evidence")):
        findings.append(
            Finding(
                severity="BLOCKER",
                decision="FIX",
                rule_index=index,
                field="hld_evidence",
                message="Constitution rule evidence is missing or not specific enough.",
            )
        )

    open_question = normalized.get("open_question")
    if not is_empty(open_question) and not open_question_is_resolved(open_question):
        findings.append(
            Finding(
                severity="ACTION",
                decision="CONFLICT",
                rule_index=index,
                field="open_question",
                message="Constitution rule has an unresolved open question requiring human review.",
            )
        )

    normalized["complete"] = not any(f.severity == "BLOCKER" for f in findings)
    normalized["pending_human_review"] = any(f.field == "open_question" for f in findings)
    return normalized, findings


def build_review(plan: dict[str, Any], *, source_path: str) -> dict[str, Any]:
    raw_rules = extract_rules_from_value(plan)
    reviewed_rules: list[dict[str, Any]] = []
    findings: list[Finding] = []

    for index, raw_rule in enumerate(raw_rules, start=1):
        reviewed, rule_findings = review_rule(raw_rule, index)
        reviewed_rules.append(reviewed)
        findings.extend(rule_findings)

    if not raw_rules:
        findings.append(
            Finding(
                severity="BLOCKER",
                decision="FIX",
                rule_index=0,
                field="rules",
                message="No constitution rules were found to review.",
            )
        )

    if any(f.severity == "BLOCKER" for f in findings):
        status = STATUS_REWORK
    elif any(f.severity == "ACTION" for f in findings):
        status = STATUS_PENDING
    else:
        status = STATUS_PASS

    return {
        "schema_version": 1,
        "status": status,
        "source_path": source_path,
        "rules_reviewed": len(raw_rules),
        "required_fields": list(FIELD_ALIASES.keys()),
        "rules": reviewed_rules,
        "findings": [asdict(finding) for finding in findings],
    }


def render_md(review: dict[str, Any]) -> str:
    lines = [
        "# Constitution Rule Quality Review",
        "",
        "made by AI",
        "",
        f"Status: `{review['status']}`",
        f"Source: `{review['source_path']}`",
        f"Rules reviewed: `{review['rules_reviewed']}`",
        "",
        "## Required rule fields",
        "",
    ]

    for field in review["required_fields"]:
        lines.append(f"- `{field}`")

    lines += ["", "## Findings", ""]
    findings = as_list(review.get("findings"))
    if not findings:
        lines.append("- none")
    else:
        for finding in findings:
            if not isinstance(finding, dict):
                continue
            lines.append(
                f"- `{finding.get('severity')}` rule {finding.get('rule_index')} "
                f"`{finding.get('field')}`: {finding.get('message')}"
            )

    lines += ["", "## Rule review", ""]
    for rule in as_list(review.get("rules")):
        if not isinstance(rule, dict):
            continue
        lines += [
            f"### Rule {rule.get('index')}",
            "",
            f"- complete: `{str(rule.get('complete')).lower()}`",
            f"- pending human review: `{str(rule.get('pending_human_review')).lower()}`",
            f"- source key: `{rule.get('source_key')}`",
            f"- rule: {normalize_text(rule.get('rule')) or 'missing'}",
            f"- HLD evidence: {normalize_text(rule.get('hld_evidence')) or 'missing'}",
            f"- SpecKit phase enforced: {normalize_text(rule.get('speckit_phase_enforced')) or 'missing'}",
            "",
        ]

    lines += [
        "## Gate meaning",
        "",
        "- `PASS`: all constitution rules have enforceable fields and no unresolved open questions.",
        "- `PENDING_HUMAN_REVIEW`: rules are structurally complete but require a human decision.",
        "- `REWORK_REQUIRED`: at least one rule is missing required evidence or enforceability fields.",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review constitution/prework rules for enforceability.")
    parser.add_argument("plan_json", help="JSON file containing constitution rules or a spec/prework plan.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--fail-on-rework", action="store_true")
    args = parser.parse_args()

    source = Path(args.plan_json).resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("plan_json must contain a JSON object")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    review = build_review(data, source_path=str(source))
    json_path = output_dir / "constitution_rule_quality_review.json"
    md_path = output_dir / "constitution_rule_quality_review.md"

    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(review), encoding="utf-8")

    print(f"Constitution rule quality: {review['status']}")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")

    if args.fail_on_rework and review["status"] == STATUS_REWORK:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
