#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def natural_key(value: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", value)
    if match:
        return (int(match.group(1)), value)
    return (10**9, value)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def plan_gate_allows_generation(plan: dict[str, Any]) -> bool:
    quality = plan.get("plan_quality", {})
    if not isinstance(quality, dict):
        return False

    decision = str(quality.get("decision", ""))
    recommendation = str(quality.get("recommendation", ""))
    conflicts = quality.get("conflicts", [])
    if decision != "FIX" or recommendation != "KEEP_PLAN" or conflicts:
        return False

    for spec in plan.get("planned_specs", []):
        if not isinstance(spec, dict):
            continue
        if spec.get("quality_flags") or spec.get("requires_user_review"):
            return False
    return True


def topological_work_order(planned_specs: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    by_id: dict[str, dict[str, Any]] = {}
    original_index: dict[str, int] = {}

    for idx, spec in enumerate(planned_specs):
        if not isinstance(spec, dict):
            continue
        spec_id = str(spec.get("planned_spec_id", "")).strip()
        if not spec_id:
            continue
        by_id[spec_id] = spec
        original_index[spec_id] = idx

    missing_dependencies: list[str] = []
    deps: dict[str, set[str]] = {}
    dependents: dict[str, set[str]] = {spec_id: set() for spec_id in by_id}

    for spec_id, spec in by_id.items():
        raw_deps = spec.get("depends_on_specs", [])
        spec_deps: set[str] = set()
        if isinstance(raw_deps, list):
            for dep in raw_deps:
                dep_id = str(dep).strip()
                if not dep_id or dep_id == spec_id:
                    continue
                if dep_id not in by_id:
                    missing_dependencies.append(f"{spec_id} depends on missing {dep_id}")
                    continue
                spec_deps.add(dep_id)
                dependents.setdefault(dep_id, set()).add(spec_id)
        deps[spec_id] = spec_deps

    ready = sorted(
        [spec_id for spec_id, spec_deps in deps.items() if not spec_deps],
        key=lambda sid: (natural_key(sid), original_index.get(sid, 10**9)),
    )
    ordered_ids: list[str] = []

    while ready:
        current = ready.pop(0)
        ordered_ids.append(current)
        for child in sorted(dependents.get(current, set()), key=lambda sid: (natural_key(sid), original_index.get(sid, 10**9))):
            deps[child].discard(current)
            if not deps[child] and child not in ordered_ids and child not in ready:
                ready.append(child)
        ready.sort(key=lambda sid: (natural_key(sid), original_index.get(sid, 10**9)))

    unresolved = [spec_id for spec_id, spec_deps in deps.items() if spec_deps]
    if unresolved:
        # Preserve deterministic output even if dependency graph has a cycle.
        for spec_id in sorted(unresolved, key=lambda sid: (natural_key(sid), original_index.get(sid, 10**9))):
            if spec_id not in ordered_ids:
                ordered_ids.append(spec_id)

    ordered_specs = [by_id[spec_id] for spec_id in ordered_ids]
    warnings = missing_dependencies
    if unresolved:
        warnings.append("Dependency cycle or unresolved dependency chain detected: " + ", ".join(unresolved))
    return ordered_specs, warnings


def build_work_order(plan: dict[str, Any], plan_path: Path) -> dict[str, Any]:
    planned_specs = [item for item in plan.get("planned_specs", []) if isinstance(item, dict)]
    ordered_specs, warnings = topological_work_order(planned_specs)
    allowed = plan_gate_allows_generation(plan)

    items: list[dict[str, Any]] = []
    for idx, spec in enumerate(ordered_specs, start=1):
        spec_id = str(spec.get("planned_spec_id", "")).strip()
        slug = str(spec.get("slug", "")).strip() or spec_id
        items.append(
            {
                "order": idx,
                "planned_spec_id": spec_id,
                "slug": slug,
                "title": spec.get("title", ""),
                "source_hld_sections": spec.get("source_hld_sections", []),
                "depends_on_specs": spec.get("depends_on_specs", []),
                "target_workspace_path": f"specs/{slug}/spec.md",
                "write_scope": "first-run workspace only",
                "status": "PENDING",
            }
        )

    return {
        "schema_version": 1,
        "status": "READY" if allowed else "BLOCKED_BY_PLAN_GATE",
        "plan_path": str(plan_path),
        "ordering_rule": "bottom-up topological order by depends_on_specs; dependencies before dependents; numeric spec ID tie-breaker",
        "allowed_to_write_workspace_specs": allowed,
        "requires_human_write_approval": True,
        "write_root": "firstrun/specs/",
        "warnings": warnings,
        "items": items,
    }


def render_md(work_order: dict[str, Any]) -> str:
    lines = [
        "# Target Spec Work Order",
        "",
        "made by AI",
        "",
        f"Status: `{work_order['status']}`",
        f"Allowed to write workspace specs: `{str(work_order['allowed_to_write_workspace_specs']).lower()}`",
        f"Requires human write approval: `{str(work_order['requires_human_write_approval']).lower()}`",
        f"Write root: `{work_order['write_root']}`",
        "",
        "## Ordering rule",
        "",
        work_order["ordering_rule"],
        "",
        "The judge/orchestrator must follow this order. Do not jump to a nearby feature cluster unless the human explicitly changes the order.",
        "",
    ]

    warnings = work_order.get("warnings", [])
    if warnings:
        lines += ["## Warnings", ""]
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    lines += ["## Work order", ""]
    for item in work_order.get("items", []):
        lines += [
            f"### {item['order']}. {item['planned_spec_id']} - {item.get('title', '')}",
            "",
            f"- target workspace path: `{item['target_workspace_path']}`",
            f"- source HLD sections: {', '.join(item.get('source_hld_sections', [])) or 'none'}",
            f"- depends on specs: {', '.join(item.get('depends_on_specs', [])) or 'none'}",
            f"- status: `{item.get('status', 'PENDING')}`",
            "",
        ]

    lines += [
        "## Write rule",
        "",
        "Before writing specs, show this file list and get human approval.",
        "",
        "Write only under the first-run workspace unless separately approved.",
        "",
    ]
    return "\n".join(lines)


LEGACY_SUPPORTING_NOTICE = '**Legacy/supporting when SpecKit is available.** This artifact preserves bottom-up planning context, but it is not the controlling handoff. Use `hldspec_state.md`, `speckit_prework_package.md`, `speckit_invocation_queue.md`, and `speckit_proxy_dossier.md` for the current SpecKit flow.'

def add_legacy_supporting_notice(markdown: str, title: str) -> str:
    if "Legacy/supporting when SpecKit is available" in markdown:
        return markdown
    marker = f"# {title}\\n\\n"
    if marker in markdown:
        return markdown.replace(marker, marker + f"> {LEGACY_SUPPORTING_NOTICE}\\n\\n", 1)
    return f"> {LEGACY_SUPPORTING_NOTICE}\\n\\n" + markdown


def main() -> int:
    parser = argparse.ArgumentParser(description="Build bottom-up work order for target Spec Kit draft generation.")
    parser.add_argument("spec_build_plan_json")
    parser.add_argument("workspace", nargs="?")
    args = parser.parse_args()

    plan_path = Path(args.spec_build_plan_json)
    workspace = Path(args.workspace) if args.workspace else plan_path.parents[2]
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    work_order = build_work_order(load_json(plan_path), plan_path)
    json_path = out_dir / "target_spec_work_order.json"
    md_path = out_dir / "target_spec_work_order.md"

    json_path.write_text(json.dumps(work_order, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(add_legacy_supporting_notice(render_md(work_order), 'Target Spec Work Order'), encoding="utf-8")

    print("Target spec work order generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {work_order['status']}")
    print(f"- items: {len(work_order['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
