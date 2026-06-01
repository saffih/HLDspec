#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.hld_canonical_line import EXCLUDED_SCOPES, parse_canonical_line
from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict

LAYER_ORDER = [
    "governance",
    "foundation_data_tool",
    "use_logic_orchestration",
    "api_contract",
    "ui_workflow",
    "operations_validation",
    "unknown",
]

LAYER_RANK = {name: idx for idx, name in enumerate(LAYER_ORDER)}

LOW_LEVEL_WORDS = {
    "db", "database", "storage", "persistence", "state", "source-of-truth",
    "source of truth", "data model", "data-model", "repository", "sqlite",
}
TOOL_WORDS = {"tool", "programmatic", "primitive", "adapter", "driver", "connector"}
LOGIC_WORDS = {"logic", "orchestration", "processing", "processor", "workflow", "lifecycle", "policy", "core"}
API_WORDS = {"api", "http", "endpoint", "contract", "request", "response", "interface"}
UI_WORDS = {"ui", "web", "screen", "view", "frontend", "workflow"}
OPS_WORDS = {"reliability", "operation", "ops", "monitor", "test", "validation", "deployment", "observability"}


def as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def sync_dir(workspace: Path) -> Path:
    return select_sync_dir(workspace, ("hldspec_state.json",))


def find_hld(workspace: Path, explicit_hld: str = "") -> Path:
    if explicit_hld:
        return Path(explicit_hld).expanduser().resolve()
    candidates = [
        workspace / "HLD.md",
        workspace / "firstrun" / "HLD.md",
        workspace / "HLD.raw.md",
    ]
    for path in candidates:
        if path.exists():
            return path.resolve()
    return (workspace / "HLD.md").resolve()


def parse_metadata(lines: list[str]) -> dict[str, str]:
    meta: dict[str, str] = {}
    for line in lines:
        m = re.match(r"^\s*(HLD-[A-Z0-9_-]+)\s*:\s*(.*)\s*$", line)
        if m:
            meta[m.group(1).upper()] = m.group(2).strip()
    return meta


def parse_sections(hld_path: Path) -> list[dict[str, Any]]:
    if not hld_path.exists():
        return []
    text = hld_path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    starts: list[tuple[int, str, str]] = []
    for idx, line in enumerate(lines):
        m = re.match(r"^##\s+(HLD-[0-9A-Za-z_-]+)\s*-\s*(.+?)\s*$", line)
        if m:
            starts.append((idx, m.group(1).strip(), m.group(2).strip()))

    sections: list[dict[str, Any]] = []
    for i, (start, hld_id, title) in enumerate(starts):
        end = starts[i + 1][0] if i + 1 < len(starts) else len(lines)
        body_lines = lines[start + 1:end]
        body = "\n".join(body_lines).strip()
        metadata = parse_metadata(body_lines[:40])
        sections.append(
            {
                "hld_id": hld_id,
                "title": title,
                "line_start": start + 1,
                "line_end": end,
                "metadata": metadata,
                "body_excerpt": body[:1200],
            }
        )
    return sections


def contains_any(text: str, words: set[str]) -> bool:
    lower = text.lower()
    return any(word in lower for word in words)


def classify_layer(section: dict[str, Any]) -> str:
    text = " ".join(
        [
            as_text(section.get("title")),
            as_text(section.get("metadata")),
            as_text(section.get("body_excerpt")),
        ]
    ).lower()

    if "constitution" in text or "governance" in text or "approval" in text:
        return "governance"
    if contains_any(text, UI_WORDS):
        return "ui_workflow"
    if contains_any(text, OPS_WORDS):
        return "operations_validation"

    low = contains_any(text, LOW_LEVEL_WORDS) or contains_any(text, TOOL_WORDS)
    logic = contains_any(text, LOGIC_WORDS)
    api = contains_any(text, API_WORDS)

    if low and not api and not logic:
        return "foundation_data_tool"
    if logic and not api:
        return "use_logic_orchestration"
    if api and not low:
        return "api_contract"
    if low and api:
        return "boundary_mixed"
    return "unknown"


def boundary_findings(section: dict[str, Any], layer: str) -> list[dict[str, Any]]:
    text = " ".join([as_text(section.get("title")), as_text(section.get("body_excerpt"))]).lower()
    findings: list[dict[str, Any]] = []
    low = contains_any(text, LOW_LEVEL_WORDS) or contains_any(text, TOOL_WORDS)
    logic = contains_any(text, LOGIC_WORDS)
    api = contains_any(text, API_WORDS)

    if layer == "boundary_mixed" or (low and api):
        findings.append(
            {
                "finding_id": f"{section['hld_id']}-BOUNDARY-MIXED",
                "severity": "ACTION",
                "issue": "section mixes low-level tool/data/state ownership with API/interface contract",
                "recommended_action": "split into low-level tool/interface, use-logic/orchestration, and API/contract specs when independently evolvable",
                "evidence_level": "INFERRED_RISK",
            }
        )
    if low and logic and api:
        findings.append(
            {
                "finding_id": f"{section['hld_id']}-THREE-LAYER-MIX",
                "severity": "ACTION",
                "issue": "section appears to mix all three layers: tool/state, logic, and API",
                "recommended_action": "decompose into layered specs before SpecKit",
                "evidence_level": "INFERRED_RISK",
            }
        )
    return findings


def build_analysis(workspace: Path, explicit_hld: str = "") -> dict[str, Any]:
    hld_path = find_hld(workspace, explicit_hld)
    sections = parse_sections(hld_path)
    analyzed: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []

    for section in sections:
        hld_desc = section.get("metadata", {}).get("HLD-DESC", "")
        canonical = parse_canonical_line(hld_desc) if hld_desc else None
        if canonical and canonical.get("scope") in EXCLUDED_SCOPES:
            analyzed.append(
                {
                    "hld_id": section["hld_id"],
                    "title": section["title"],
                    "line_start": section["line_start"],
                    "line_end": section["line_end"],
                    "metadata": section["metadata"],
                    "layer": "governance",
                    "spec_candidate": False,
                    "requires_layered_split": False,
                    "findings": [],
                }
            )
            continue
        layer = classify_layer(section)
        section_findings = boundary_findings(section, layer)
        findings.extend([{**f, "hld_id": section["hld_id"], "title": section["title"]} for f in section_findings])
        analyzed.append(
            {
                "hld_id": section["hld_id"],
                "title": section["title"],
                "line_start": section["line_start"],
                "line_end": section["line_end"],
                "metadata": section["metadata"],
                "layer": layer,
                "spec_candidate": layer not in {"governance", "unknown"},
                "requires_layered_split": layer == "boundary_mixed" or any(f["severity"] == "ACTION" for f in section_findings),
                "findings": section_findings,
            }
        )

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "hld_path": str(hld_path),
        "section_count": len(sections),
        "status": "NO_HLD_SECTIONS" if not sections else "ARCHITECTURE_REVIEW_REQUIRED" if findings else "PASS_WITH_REVIEW",
        "architecture_model": {
            "layers": [
                "governance",
                "foundation_data_tool",
                "use_logic_orchestration",
                "api_contract",
                "ui_workflow",
                "operations_validation",
            ],
            "layer_rule": "low-level DB/storage/tool interfaces, use-logic/orchestration, and API/contract layers must be separate when independently evolvable",
        },
        "sections": analyzed,
        "findings": findings,
    }


def render_md(data: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Architecture Analysis",
        "",
        "",
        "",
        f"Status: `{data.get('status')}`",
        f"Workspace: `{data.get('workspace')}`",
        f"HLD: `{data.get('hld_path')}`",
        f"Sections: {data.get('section_count')}",
        "",
        "## Architecture model",
        "",
        "- governance",
        "- foundation/data/tool",
        "- use-logic/orchestration",
        "- API/contract",
        "- UI/workflow",
        "- operations/validation",
        "",
        "## Layer rule",
        "",
        "Low-level DB/storage/tool interfaces, use-logic/orchestration, and API/contract layers must be separated when they can evolve independently.",
        "",
        "## Findings",
        "",
    ]
    findings = data.get("findings") or []
    if not findings:
        lines.append("- none")
    else:
        for finding in findings:
            lines += [
                f"### {finding.get('finding_id')}",
                "",
                f"- HLD: `{finding.get('hld_id')}` - {finding.get('title')}",
                f"- severity: `{finding.get('severity')}`",
                f"- issue: {finding.get('issue')}",
                f"- recommendation: {finding.get('recommended_action')}",
                f"- evidence level: `{finding.get('evidence_level')}`",
                "",
            ]

    lines += ["", "## Sections", ""]
    for section in data.get("sections", []):
        lines += [
            f"### {section.get('hld_id')} - {section.get('title')}",
            "",
            f"- layer: `{section.get('layer')}`",
            f"- spec candidate: `{str(section.get('spec_candidate')).lower()}`",
            f"- requires layered split: `{str(section.get('requires_layered_split')).lower()}`",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Analyze HLD architecture layers and SpecKit boundary readiness.")
    parser.add_argument("workspace")
    parser.add_argument("--hld", default="", help="Optional explicit HLD path.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sync = sync_dir(workspace)
    data = build_analysis(workspace, args.hld)
    json_path = sync / "hldspec_architecture_analysis.json"
    md_path = sync / "hldspec_architecture_analysis.md"
    write_json_dict(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLDspec architecture analysis generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    print(f"- sections: {data['section_count']}")
    print(f"- findings: {len(data['findings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
