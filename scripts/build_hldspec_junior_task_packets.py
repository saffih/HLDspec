#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def sync_dir(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    if direct.exists():
        return direct
    if nested.exists():
        return nested
    return direct


def task(task_id: str, assigned_role: str, goal: str, allowed_inputs: list[str], output_schema: dict[str, Any], senior_reviewer: str) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "assigned_role": assigned_role,
        "cost_tier": "LOW",
        "context_budget": "SMALL_RELEVANT_ARTIFACTS_ONLY",
        "goal": goal,
        "allowed_inputs": allowed_inputs,
        "forbidden_actions": [
            "do not approve artifacts",
            "do not promote artifacts",
            "do not decide human-owned questions",
            "do not edit the source HLD",
            "do not trigger SpecKit",
            "do not perform implementation",
            "do not inspect unrelated repository context",
        ],
        "output_schema": output_schema,
        "senior_reviewer": senior_reviewer,
        "stop_condition": "Return the requested JSON-shaped proposal only. Escalate missing evidence as open questions.",
        "promotion_status": "PROPOSED",
        "requires_senior_review": True,
        "requires_judge_promotion": True,
    }


def build_packets(workspace: Path) -> dict[str, Any]:
    packets = [
        task("JPM-001", "Junior Product Use-Case Extractor", "Extract use cases and user-visible flows from the provided HLD evidence.", [".specify/sync/hld_usecase_api_map.json", ".specify/sync/hld_sections/ relevant sections only"], {"use_cases": [], "evidence_sources": [], "product_open_questions": [], "unsupported_claims": []}, "Product Lead"),
        task("JPM-002", "Junior Product Story Drafter", "Draft user stories and acceptance criteria from extracted use cases.", [".specify/sync/hld_usecase_api_map.json", ".specify/sync/speckit_product_manager_pack.json if present"], {"user_stories": [], "acceptance_criteria": [], "evidence_sources": [], "open_questions": []}, "Product Lead"),
        task("JAR-001", "Junior Architect Boundary Extractor", "Extract API/interface, data/source-of-truth, and responsibility boundaries.", [".specify/sync/hld_usecase_api_map.json", ".specify/sync/feature_dependency_graph.json"], {"api_boundaries": [], "data_boundaries": [], "evidence_sources": [], "architecture_open_questions": []}, "Architect Lead"),
        task("JAR-002", "Junior Architect Dependency Mapper", "Map dependency order and architecture risks from approved HLD evidence.", [".specify/sync/hld_usecase_api_map.json", ".specify/sync/feature_dependency_graph.json"], {"dependency_findings": [], "risks": [], "evidence_sources": [], "open_questions": []}, "Architect Lead"),
    ]
    return {"schema_version": 1, "status": "PROPOSED", "workspace": str(workspace), "source_rule": "Junior task packets are instructions for cheap bounded subagents. They are not decisions.", "task_packets": packets, "counts": {"task_packets": len(packets)}}


def render_md(data: dict[str, Any]) -> str:
    lines = ["# HLDspec Junior Task Packets", "", "made by AI", "", f"Status: `{data.get('status')}`", "", "Junior agents do cheap bounded extraction/drafting. Senior roles synthesize. Judge promotes.", ""]
    for item in data.get("task_packets", []):
        if not isinstance(item, dict):
            continue
        lines += [f"## {item.get('task_id')} - {item.get('assigned_role')}", "", f"- cost tier: `{item.get('cost_tier')}`", f"- context budget: `{item.get('context_budget')}`", f"- senior reviewer: `{item.get('senior_reviewer')}`", f"- goal: {item.get('goal')}", "", "Forbidden actions:"]
        for action in item.get("forbidden_actions", []):
            lines.append(f"- {action}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build bounded junior subagent task packets for Product/Architect work.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    sync = sync_dir(workspace)
    sync.mkdir(parents=True, exist_ok=True)
    data = build_packets(workspace)
    (sync / "hldspec_junior_task_packets.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / "hldspec_junior_task_packets.md").write_text(render_md(data), encoding="utf-8")
    print("HLDspec junior task packets generated:")
    print(f"- json: {sync / 'hldspec_junior_task_packets.json'}")
    print(f"- report: {sync / 'hldspec_junior_task_packets.md'}")
    print(f"- task packets: {len(data['task_packets'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
