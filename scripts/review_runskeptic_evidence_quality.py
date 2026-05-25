#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from hldspec.skeptic_schema import (  # noqa: E402
    FIELD_ALIASES,
    REQUIRED_FINDING_FIELDS,
    has_key,
    is_empty_value,
    normalize_text,
    unresolved_unknowns,
    value_for,
)

STATUS_PASS = "PASS"
STATUS_PENDING = "PENDING_HUMAN_REVIEW"
STATUS_REWORK = "REWORK_REQUIRED"


RUNSKEPTIC_KEYS = {
    "RunSkeptic_cycles",
    "decision",
    "recommendation",
    "outcome",
    "spotlight",
    "evidence_level",
    "evidence_levels",
    "observed_evidence",
    "verification",
    "confidence",
}


@dataclass
class Finding:
    severity: str
    decision: str
    item_index: int
    field: str
    message: str


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def looks_like_runskeptic_item(item: dict[str, Any]) -> bool:
    keys = set(item.keys())
    return bool(keys & RUNSKEPTIC_KEYS) and (
        "decision" in item
        or "recommendation" in item
        or "outcome" in item
        or "evidence_level" in item
        or "evidence_levels" in item
    )


def collect_items(value: Any, collected: list[dict[str, Any]]) -> None:
    if isinstance(value, dict):
        if looks_like_runskeptic_item(value):
            collected.append(value)
        for child in value.values():
            collect_items(child, collected)
    elif isinstance(value, list):
        for child in value:
            collect_items(child, collected)


def review_item(item: dict[str, Any], index: int) -> tuple[dict[str, Any], list[Finding]]:
    findings: list[Finding] = []
    normalized: dict[str, Any] = {"index": index}

    for field in FIELD_ALIASES:
        present = has_key(item, field)
        value = value_for(item, field)
        normalized[field] = value
        normalized[f"{field}_present"] = present

        if not present:
            findings.append(
                Finding(
                    severity="BLOCKER",
                    decision="FIX",
                    item_index=index,
                    field=field,
                    message=f"RunSkeptic item is missing required field `{field}`.",
                )
            )
            continue

        if field in REQUIRED_FINDING_FIELDS:
            if is_empty_value(value):
                findings.append(
                    Finding(
                        severity="BLOCKER",
                        decision="FIX",
                        item_index=index,
                        field=field,
                        message=f"RunSkeptic item field `{field}` is empty.",
                    )
                )

    evidence_text = normalize_text(normalized.get("observed_evidence"))
    evidence_level_text = normalize_text(normalized.get("evidence_level")).lower()
    if evidence_text and evidence_level_text and "observed" not in evidence_level_text and "inferred" not in evidence_level_text and "unknown" not in evidence_level_text:
        findings.append(
            Finding(
                severity="ACTION",
                decision="FIX",
                item_index=index,
                field="evidence_level",
                message="Evidence level should explicitly distinguish observed, inferred risk, or unknown.",
            )
        )

    if unresolved_unknowns(normalized.get("unknowns")):
        findings.append(
            Finding(
                severity="ACTION",
                decision="CONFLICT",
                item_index=index,
                field="unknowns",
                message="RunSkeptic item has unresolved unknowns requiring explicit handling.",
            )
        )

    normalized["complete"] = not any(f.severity == "BLOCKER" for f in findings)
    normalized["pending_human_review"] = any(f.decision == "CONFLICT" for f in findings)
    return normalized, findings


def build_review(payload: dict[str, Any], *, source_path: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    collect_items(payload, items)

    reviewed_items: list[dict[str, Any]] = []
    findings: list[Finding] = []

    for index, item in enumerate(items, start=1):
        reviewed, item_findings = review_item(item, index)
        reviewed_items.append(reviewed)
        findings.extend(item_findings)

    if not items:
        findings.append(
            Finding(
                severity="BLOCKER",
                decision="FIX",
                item_index=0,
                field="items",
                message="No RunSkeptic findings or cycles were found to review.",
            )
        )

    if any(f.severity == "BLOCKER" for f in findings):
        status = STATUS_REWORK
    elif any(f.decision == "CONFLICT" for f in findings):
        status = STATUS_PENDING
    else:
        status = STATUS_PASS

    return {
        "schema_version": 1,
        "status": status,
        "source_path": source_path,
        "items_reviewed": len(items),
        "required_fields": list(REQUIRED_FINDING_FIELDS),
        "items": reviewed_items,
        "findings": [asdict(finding) for finding in findings],
    }


def render_md(review: dict[str, Any]) -> str:
    lines = [
        "# RunSkeptic Evidence Quality Review",
        "",
        "",
        "",
        f"Status: `{review['status']}`",
        f"Source: `{review['source_path']}`",
        f"Items reviewed: `{review['items_reviewed']}`",
        "",
        "## Required fields",
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
                f"- `{finding.get('severity')}` item {finding.get('item_index')} "
                f"`{finding.get('field')}`: {finding.get('message')}"
            )

    lines += [
        "",
        "## Gate meaning",
        "",
        "- `PASS`: every RunSkeptic finding has evidence, evidence level, confidence, unknowns, verification, and residual risk.",
        "- `PENDING_HUMAN_REVIEW`: findings are structurally complete but unresolved unknowns require human decision.",
        "- `REWORK_REQUIRED`: at least one finding is missing required evidence fields.",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review RunSkeptic findings/cycles for evidence completeness.")
    parser.add_argument("report_json", help="JSON report containing RunSkeptic findings or cycles.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--fail-on-rework", action="store_true")
    args = parser.parse_args()

    source = Path(args.report_json).resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit("report_json must contain a JSON object")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else source.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    review = build_review(data, source_path=str(source))
    json_path = output_dir / "runskeptic_evidence_quality_review.json"
    md_path = output_dir / "runskeptic_evidence_quality_review.md"

    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(review), encoding="utf-8")

    print(f"RunSkeptic evidence quality: {review['status']}")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")

    if args.fail_on_rework and review["status"] == STATUS_REWORK:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
