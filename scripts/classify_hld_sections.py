#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hld_map


CONTEXT_TITLE_TERMS = (
    "lesson learned",
    "lessons learned",
    "success metric",
    "success criteria",
    "next step",
    "future work",
    "appendix",
    "archive",
    "deprecated",
    "glossary",
    "reference",
    "references",
    "milestone",
    "timeline",
    "changelog",
    "history",
    "stakeholder",
    "stakeholder analysis",
    "persona",
    "personas",
    "user persona",
    "user personas",
    "business case",
    "business case foundation",
    "executive summary",
    "assumption",
    "assumptions",
)


GOVERNANCE_TITLE_TERMS = (
    "decision log",
    "open conflict",
    "open conflicts",
)
SPEC_TITLE_TERMS = (
    "api",
    "interface",
    "database",
    "storage",
    "config",
    "session",
    "sync",
    "operation",
    "workflow",
    "pipeline",
    "wip",
    "web ui",
    "ui",
    "core",
    "integration",
    "service",
    "engine",
    "controller",
    "architecture",
)


def explicit_spec_ids(section: hld_map.HldSection) -> list[str]:
    values = hld_map.split_metadata_list(section.metadata_value("HLD-SPECS"))
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized or normalized.upper() == "TBD" or normalized.lower() == "constitution":
            continue
        result.append(normalized)
    return result


def classify_section(section: hld_map.HldSection, previous_spec_candidate: str | None) -> dict[str, object]:
    title = section.title.strip()
    lower_title = title.lower()
    lower_text = section.text.lower()
    role = section.metadata_value("HLD-ROLE", "").strip().lower()
    specs = explicit_spec_ids(section)

    if specs:
        return {
            "hld_id": section.id,
            "title": title,
            "section_kind": "SPEC_CANDIDATE",
            "spec_candidate": True,
            "recommended_action": "USE_EXPLICIT_HLD_SPECS",
            "merge_with": None,
            "reason": "Section has explicit HLD-SPECS metadata.",
            "explicit_hld_specs": specs,
        }

    if (
        role == "governance"
        or "source of truth" in lower_text
        or "constitution" in lower_title
        or any(term in lower_title for term in GOVERNANCE_TITLE_TERMS)
    ):
        return {
            "hld_id": section.id,
            "title": title,
            "section_kind": "GOVERNANCE",
            "spec_candidate": False,
            "recommended_action": "KEEP_AS_GOVERNANCE_CONTEXT",
            "merge_with": None,
            "reason": "Governance/source-of-truth material should inform constitution or planning, not become a feature spec by default.",
            "explicit_hld_specs": [],
        }

    if any(term in lower_title for term in CONTEXT_TITLE_TERMS):
        return {
            "hld_id": section.id,
            "title": title,
            "section_kind": "HLD_CONTEXT_ONLY",
            "spec_candidate": False,
            "recommended_action": "KEEP_AS_CONTEXT",
            "merge_with": previous_spec_candidate,
            "reason": "Title indicates context, stakeholder/persona/business-case material, status, history, appendix, milestone, or verification material rather than an independently implementable capability.",
            "explicit_hld_specs": [],
        }

    if lower_title in {"overview", "summary", "introduction"} or lower_title.startswith("overview"):
        return {
            "hld_id": section.id,
            "title": title,
            "section_kind": "MERGE_WITH_SIBLING",
            "spec_candidate": False,
            "recommended_action": "MERGE_WITH_NEAREST_SPEC_CONTEXT",
            "merge_with": previous_spec_candidate,
            "reason": "Overview/summary sections usually provide context for nearby capability sections.",
            "explicit_hld_specs": [],
        }

    if any(term in lower_title for term in SPEC_TITLE_TERMS):
        return {
            "hld_id": section.id,
            "title": title,
            "section_kind": "SPEC_CANDIDATE",
            "spec_candidate": True,
            "recommended_action": "PLAN_AS_SPEC_CANDIDATE",
            "merge_with": None,
            "reason": "Title indicates an implementable architecture/capability/API/interface area.",
            "explicit_hld_specs": [],
        }

    if role in {"api", "data", "processing", "operations", "testing", "architecture"}:
        return {
            "hld_id": section.id,
            "title": title,
            "section_kind": "SPEC_CANDIDATE",
            "spec_candidate": True,
            "recommended_action": "PLAN_AS_SPEC_CANDIDATE",
            "merge_with": None,
            "reason": f"HLD-ROLE `{role}` is usually spec-plannable unless a context-only title overrides it.",
            "explicit_hld_specs": [],
        }

    return {
        "hld_id": section.id,
        "title": title,
        "section_kind": "SPEC_CANDIDATE",
        "spec_candidate": True,
        "recommended_action": "PLAN_AS_SPEC_CANDIDATE",
        "merge_with": None,
        "reason": "Default to spec candidate to avoid losing coverage; plan-quality gate may still require merge/split review.",
        "explicit_hld_specs": [],
    }


def build_classification(parsed: hld_map.HldMap) -> dict[str, object]:
    sections: list[dict[str, object]] = []
    previous_spec_candidate: str | None = None

    for section in parsed.sections:
        item = classify_section(section, previous_spec_candidate)
        sections.append(item)
        if item.get("spec_candidate"):
            previous_spec_candidate = section.id

    summary: dict[str, int] = {}
    for item in sections:
        kind = str(item.get("section_kind", "UNKNOWN"))
        summary[kind] = summary.get(kind, 0) + 1

    return {
        "schema_version": 1,
        "source_hld": parsed.source_path,
        "status": "classification_ready",
        "rule": "HLD sections are anchors; only spec_candidate sections become planned specs by default.",
        "summary": summary,
        "sections": sections,
    }


def render_md(classification: dict[str, object]) -> str:
    sections = classification.get("sections", [])
    if not isinstance(sections, list):
        sections = []

    lines = [
        "# HLD Section Classification",
        "",
        "made by AI",
        "",
        f"Status: `{classification.get('status')}`",
        "",
        "Rule: HLD sections are anchors. Do not assume one HLD section equals one target spec.",
        "",
        "## Summary",
        "",
    ]

    summary = classification.get("summary", {})
    if isinstance(summary, dict):
        for kind, count in sorted(summary.items()):
            lines.append(f"- {kind}: {count}")
    lines.append("")

    lines += ["## Sections", ""]
    for item in sections:
        if not isinstance(item, dict):
            continue
        lines += [
            f"### {item.get('hld_id')} - {item.get('title')}",
            "",
            f"- kind: `{item.get('section_kind')}`",
            f"- spec candidate: `{str(item.get('spec_candidate')).lower()}`",
            f"- action: `{item.get('recommended_action')}`",
            f"- merge with: `{item.get('merge_with') or ''}`",
            f"- reason: {item.get('reason')}",
            "",
        ]

    lines += [
        "## Planning rule",
        "",
        "- `SPEC_CANDIDATE` sections may become planned specs.",
        "- `HLD_CONTEXT_ONLY`, `GOVERNANCE`, `APPENDIX`, `RUNBOOK`, `REFERENCE`, `VERIFICATION_CONTEXT`, and merge sections should not become planned specs by default.",
        "- Explicit `HLD-SPECS` metadata overrides the default classification.",
        "- If plan quality worsens after conversion, stop and consolidate HLD-SPECS mapping instead of splitting more.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify HLD sections before spec build planning.")
    parser.add_argument("hld")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    hld_path = Path(args.hld)
    if not hld_path.is_absolute():
        hld_path = (workspace / hld_path).resolve()

    parsed = hld_map.parse_hld_file(hld_path)
    if parsed.validation_errors:
        print("Invalid HLD map; cannot classify sections.")
        for error in parsed.validation_errors:
            print(f"- {error}")
        return 1

    classification = build_classification(parsed)
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "hld_section_classification.json"
    md_path = out_dir / "hld_section_classification.md"
    json_path.write_text(json.dumps(classification, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_md(classification), encoding="utf-8")

    print("HLD section classification generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
