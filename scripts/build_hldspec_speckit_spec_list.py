#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ORDER = {
    "governance": 0,
    "foundation_data_tool": 1,
    "use_logic_orchestration": 2,
    "api_contract": 3,
    "ui_workflow": 4,
    "operations_validation": 5,
    "boundary_mixed": 1,
    "unknown": 9,
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_dir(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    if (direct / "hldspec_architecture_analysis.json").exists():
        return direct
    if (nested / "hldspec_architecture_analysis.json").exists():
        return nested
    direct.mkdir(parents=True, exist_ok=True)
    return direct


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text[:50] or "spec"


def split_candidates(section: dict[str, Any]) -> list[dict[str, Any]]:
    hld_id = section["hld_id"]
    title = section["title"]
    lower = title.lower()
    tool_kind = "storage" if "storage" in lower else "database" if "database" in lower or "db" in lower else "tool"

    return [
        {
            "source_hld_ids": [hld_id],
            "title": f"{title} - {tool_kind.title()} Tool Interface",
            "layer": "foundation_data_tool",
            "reason": "split low-level tool/data/state ownership from higher layers",
        },
        {
            "source_hld_ids": [hld_id],
            "title": f"{title} - Use Logic and Orchestration",
            "layer": "use_logic_orchestration",
            "reason": "split domain behavior and lifecycle rules from tool and API layers",
        },
        {
            "source_hld_ids": [hld_id],
            "title": f"{title} - API Contract",
            "layer": "api_contract",
            "reason": "split caller-facing contract from implementation and use logic",
        },
    ]


def build_list(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    analysis = load_json(sync / "hldspec_architecture_analysis.json")
    specs: list[dict[str, Any]] = []

    for section in analysis.get("sections", []):
        if not isinstance(section, dict):
            continue
        if not section.get("spec_candidate") and not section.get("requires_layered_split"):
            continue
        if section.get("requires_layered_split"):
            specs.extend(split_candidates(section))
        else:
            specs.append(
                {
                    "source_hld_ids": [section.get("hld_id")],
                    "title": section.get("title", "Untitled"),
                    "layer": section.get("layer", "unknown"),
                    "reason": "direct capability candidate from architecture analysis",
                }
            )

    specs.sort(key=lambda item: (ORDER.get(str(item.get("layer")), 9), str(item.get("title"))))
    numbered: list[dict[str, Any]] = []
    for idx, spec in enumerate(specs, start=1):
        layer = str(spec.get("layer", "unknown"))
        numbered.append(
            {
                "spec_id": f"{idx:03d}-{slugify(str(spec.get('title')))}",
                "title": spec.get("title"),
                "layer": layer,
                "source_hld_ids": spec.get("source_hld_ids", []),
                "depends_on_layers": [name for name, rank in ORDER.items() if rank < ORDER.get(layer, 9) and name not in {"boundary_mixed", "unknown"}],
                "reason": spec.get("reason", ""),
                "status": "PLANNED_REVIEW",
            }
        )

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "status": "SPEC_LIST_READY_FOR_REVIEW" if numbered else "NO_SPEC_CANDIDATES",
        "ordering_rule": "bottom-up: governance, foundation/data/tool, logic/orchestration, API, UI, operations/testing",
        "spec_count": len(numbered),
        "specs": numbered,
    }


def render_md(data: dict[str, Any]) -> str:
    lines = [
        "# HLDspec SpecKit Spec List",
        "",
        "made by AI",
        "",
        f"Status: `{data.get('status')}`",
        f"Spec count: {data.get('spec_count')}",
        "",
        "Ordering rule:",
        "",
        data.get("ordering_rule", ""),
        "",
        "## Planned specs",
        "",
    ]
    if not data.get("specs"):
        lines.append("- none")
    for spec in data.get("specs", []):
        lines += [
            f"### {spec.get('spec_id')}",
            "",
            f"- title: {spec.get('title')}",
            f"- layer: `{spec.get('layer')}`",
            f"- source HLD ids: {', '.join(spec.get('source_hld_ids', []))}",
            f"- depends on layers: {', '.join(spec.get('depends_on_layers', [])) or 'none'}",
            f"- reason: {spec.get('reason')}",
            f"- status: `{spec.get('status')}`",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dependency-aware SpecKit spec list from HLDspec architecture analysis.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sync = sync_dir(workspace)
    data = build_list(workspace)
    json_path = sync / "hldspec_speckit_spec_list.json"
    md_path = sync / "hldspec_speckit_spec_list.md"
    write_json(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLDspec SpecKit spec list generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    print(f"- spec count: {data['spec_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
