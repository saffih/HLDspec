#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "spec"


def branch_name_for_item(item: dict[str, Any]) -> str:
    spec_id = str(item.get("planned_spec_id", "")).strip()
    slug = str(item.get("slug", "")).strip()
    title = str(item.get("title", "")).strip()

    if slug:
        normalized = slugify(slug)
        if normalized.startswith(f"{spec_id}-"):
            return normalized
        return f"{spec_id}-{normalized}" if spec_id else normalized

    title_slug = slugify(title)
    return f"{spec_id}-{title_slug}" if spec_id else title_slug


def build_branch_queue(work_order: dict[str, Any], work_order_path: Path) -> dict[str, Any]:
    allowed = bool(work_order.get("allowed_to_write_workspace_specs"))
    items = [item for item in work_order.get("items", []) if isinstance(item, dict)]

    branches: list[dict[str, Any]] = []
    for item in items:
        branch = branch_name_for_item(item)
        branches.append(
            {
                "order": item.get("order"),
                "planned_spec_id": item.get("planned_spec_id"),
                "title": item.get("title", ""),
                "branch_name": branch,
                "spec_workspace_path": item.get("target_workspace_path", f"specs/{branch}/spec.md"),
                "source_hld_sections": item.get("source_hld_sections", []),
                "depends_on_specs": item.get("depends_on_specs", []),
                "status": "PENDING",
                "branch_status": "NOT_CREATED",
                "write_status": "NOT_STARTED",
                "review_status": "NOT_REVIEWED",
                "allowed_actions": [
                    "CREATE_BRANCH_AFTER_HUMAN_APPROVAL",
                    "WRITE_WORKSPACE_SPEC",
                    "REVIEW_SPEC",
                    "MARK_DONE",
                ],
                "requires_human_approval_before_branch_create": True,
                "requires_human_approval_before_project_write": True,
            }
        )

    active = branches[0] if allowed and branches else None
    return {
        "schema_version": 1,
        "status": "READY" if allowed and branches else ("EMPTY" if allowed else "BLOCKED_BY_WORK_ORDER"),
        "execution_mode": "ONE_SPEC_BRANCH_AT_A_TIME",
        "source_work_order": str(work_order_path),
        "ordering_rule": work_order.get("ordering_rule", "bottom-up work order"),
        "branch_policy": {
            "branch_oriented": True,
            "create_branches_automatically": False,
            "one_branch_at_a_time": True,
            "cache_branch_plan_before_writing": True,
            "project_specs_write_requires_explicit_approval": True,
            "default_branch_name_rule": "<planned_spec_id>-<slug>",
        },
        "active_branch": active,
        "branches": branches,
    }


def render_md(queue: dict[str, Any]) -> str:
    lines = [
        "# Spec Branch Queue",
        "",
        "made by AI",
        "",
        f"Status: `{queue['status']}`",
        f"Execution mode: `{queue['execution_mode']}`",
        f"Source work order: `{queue.get('source_work_order', '')}`",
        "",
        "## Branch policy",
        "",
        "- Spec Kit work is branch-oriented.",
        "- HLDspec must cache the branch plan before writing specs.",
        "- Work one planned spec branch at a time.",
        "- Do not create Git branches automatically.",
        "- Do not write project `specs/` without explicit approval.",
        "- Workspace draft writes remain under the first-run workspace unless separately approved.",
        "",
    ]

    active = queue.get("active_branch")
    if isinstance(active, dict):
        lines += [
            "## Active next branch",
            "",
            f"- order: {active.get('order')}",
            f"- planned spec: `{active.get('planned_spec_id')}`",
            f"- title: {active.get('title')}",
            f"- branch name: `{active.get('branch_name')}`",
            f"- workspace spec path: `{active.get('spec_workspace_path')}`",
            f"- source HLD sections: {', '.join(active.get('source_hld_sections', [])) or 'none'}",
            "",
        ]

    lines += ["## Branch queue", ""]
    for item in queue.get("branches", []):
        if not isinstance(item, dict):
            continue
        lines += [
            f"### {item.get('order')}. {item.get('planned_spec_id')} - {item.get('title')}",
            "",
            f"- branch: `{item.get('branch_name')}`",
            f"- workspace spec path: `{item.get('spec_workspace_path')}`",
            f"- branch status: `{item.get('branch_status')}`",
            f"- write status: `{item.get('write_status')}`",
            f"- review status: `{item.get('review_status')}`",
            f"- depends on specs: {', '.join(item.get('depends_on_specs', [])) or 'none'}",
            "",
        ]

    lines += [
        "## Continuation rule",
        "",
        "The judge/orchestrator must process only the active next branch unless the human explicitly changes the order.",
        "",
        "After a branch/spec is completed and reviewed, update this queue and advance to the next item.",
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
    parser = argparse.ArgumentParser(description="Build one-at-a-time Spec Kit branch queue from target spec work order.")
    parser.add_argument("target_spec_work_order_json")
    parser.add_argument("workspace", nargs="?")
    args = parser.parse_args()

    work_order_path = Path(args.target_spec_work_order_json)
    workspace = Path(args.workspace) if args.workspace else work_order_path.parents[2]
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    queue = build_branch_queue(load_json(work_order_path), work_order_path)

    json_path = out_dir / "spec_branch_queue.json"
    md_path = out_dir / "spec_branch_queue.md"
    json_path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(add_legacy_supporting_notice(render_md(queue), 'Spec Branch Queue'), encoding="utf-8")

    print("Spec branch queue generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {queue['status']}")
    print(f"- execution mode: {queue['execution_mode']}")
    print(f"- branches: {len(queue['branches'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
