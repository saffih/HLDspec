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


def scan_existing_specs(source_project: Path) -> dict[str, Any]:
    """Scan target project's specs/ directory for existing spec IDs and highest number."""
    specs_dir = source_project / "specs"
    if not specs_dir.is_dir():
        return {"found": False, "specs_dir": str(specs_dir), "existing_ids": [], "highest_number": 0, "conflicts": []}

    existing: list[dict[str, Any]] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        # Match NNN-slug format
        m = re.match(r"^(\d+)-(.+)$", name)
        if m:
            existing.append({"spec_id": name, "number": int(m.group(1)), "slug": m.group(2)})

    highest = max((s["number"] for s in existing), default=0)
    return {
        "found": True,
        "specs_dir": str(specs_dir),
        "existing_ids": [s["spec_id"] for s in existing],
        "existing_count": len(existing),
        "highest_number": highest,
        "conflicts": [],  # filled in after numbering
    }


def build_list(workspace: Path, source_project: Path | None = None) -> dict[str, Any]:
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

    # Scan existing project specs to avoid ID conflicts
    existing_scan: dict[str, Any] = {"found": False, "existing_ids": [], "highest_number": 0, "conflicts": []}
    if source_project:
        existing_scan = scan_existing_specs(source_project)

    start_idx = existing_scan["highest_number"] + 1 if existing_scan.get("highest_number", 0) > 0 else 1
    existing_ids_set = set(existing_scan.get("existing_ids", []))

    numbered: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for offset, spec in enumerate(specs):
        idx = start_idx + offset
        layer = str(spec.get("layer", "unknown"))
        spec_id = f"{idx:03d}-{slugify(str(spec.get('title')))}"
        # Check for numeric collision even if slug differs
        conflict_ids = [eid for eid in existing_ids_set if eid.startswith(f"{idx:03d}-")]
        if conflict_ids:
            conflicts.append({"planned_id": spec_id, "conflicts_with": conflict_ids})
        numbered.append(
            {
                "spec_id": spec_id,
                "title": spec.get("title"),
                "layer": layer,
                "source_hld_ids": spec.get("source_hld_ids", []),
                "depends_on_layers": [name for name, rank in ORDER.items() if rank < ORDER.get(layer, 9) and name not in {"boundary_mixed", "unknown"}],
                "reason": spec.get("reason", ""),
                "status": "PLANNED_REVIEW",
            }
        )

    existing_scan["conflicts"] = conflicts
    has_conflicts = bool(conflicts)

    status = "NO_SPEC_CANDIDATES" if not numbered else ("ID_CONFLICT_REQUIRES_REVIEW" if has_conflicts else "SPEC_LIST_READY_FOR_REVIEW")

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "source_project": str(source_project) if source_project else None,
        "status": status,
        "ordering_rule": "bottom-up: governance, foundation/data/tool, logic/orchestration, API, UI, operations/testing",
        "spec_count": len(numbered),
        "existing_specs_scan": existing_scan,
        "specs": numbered,
    }


def render_md(data: dict[str, Any]) -> str:
    scan = data.get("existing_specs_scan") or {}
    lines = [
        "# HLDspec SpecKit Spec List",
        "",
        "made by AI",
        "",
        f"Status: `{data.get('status')}`",
        f"Spec count: {data.get('spec_count')}",
        "",
    ]
    if data.get("source_project"):
        lines += [f"Source project: `{data['source_project']}`", ""]
    if scan.get("found"):
        lines += [
            "## Existing specs scan",
            "",
            f"- scanned: `{scan.get('specs_dir')}`",
            f"- existing count: {scan.get('existing_count', 0)}",
            f"- highest existing number: {scan.get('highest_number', 0)}",
            f"- new specs start at: `{scan.get('highest_number', 0) + 1:03d}-...`",
            "",
        ]
        if scan.get("conflicts"):
            lines += ["### ⚠ ID conflicts — RESOLVE before approval", ""]
            for c in scan["conflicts"]:
                lines.append(f"- planned `{c['planned_id']}` conflicts with existing: {', '.join(c['conflicts_with'])}")
            lines.append("")
    elif data.get("source_project"):
        lines += [f"- No existing specs found at `{scan.get('specs_dir')}` — numbering starts at 001", ""]

    lines += [
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
    parser.add_argument("--source-project", help="Path to target project root (scans its specs/ for existing IDs to avoid conflicts)")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    source_project = Path(args.source_project).expanduser().resolve() if args.source_project else None
    sync = sync_dir(workspace)
    data = build_list(workspace, source_project)
    json_path = sync / "hldspec_speckit_spec_list.json"
    md_path = sync / "hldspec_speckit_spec_list.md"
    write_json(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLDspec SpecKit spec list generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    print(f"- spec count: {data['spec_count']}")
    conflicts = (data.get("existing_specs_scan") or {}).get("conflicts", [])
    if conflicts:
        print(f"- WARNING: {len(conflicts)} ID conflict(s) with existing project specs — resolve before approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
