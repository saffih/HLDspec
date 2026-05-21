#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def first_active_item(queue: dict[str, Any]) -> dict[str, Any]:
    items = [item for item in as_list(queue.get("items")) if isinstance(item, dict)]
    for item in items:
        if str(item.get("status", "")).upper() in {
            "PENDING_HUMAN_PLAN_REVIEW",
            "READY_FOR_SPECKIT_SPECIFY",
            "PENDING",
            "NOT_STARTED",
        }:
            return item
    return items[0] if items else {}


def feature_from_manifest(manifest: dict[str, Any], feature_id: str) -> dict[str, Any]:
    for feature in as_list(manifest.get("features")):
        if isinstance(feature, dict) and str(feature.get("feature_id")) == feature_id:
            return feature
    return {}


def build_dossier(workspace: Path) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    manifest = load_json(sync / "speckit_input_manifest.json")
    queue = load_json(sync / "speckit_invocation_queue.json")
    constitution = load_json(sync / "constitution_update_plan.json")
    graph = load_json(sync / "feature_dependency_graph.json")
    quality = load_json(sync / "speckit_prework_quality_review.json")

    active = first_active_item(queue)
    feature_id = str(active.get("feature_id", ""))
    feature = feature_from_manifest(manifest, feature_id) if feature_id else {}

    return {
        "schema_version": 1,
        "status": "READY_FOR_PROXY_AFTER_HUMAN_APPROVAL",
        "protocol": "docs/SPECKIT_PROXY_PROTOCOL.md",
        "selected_feature": {
            "feature_id": feature_id,
            "feature_name": active.get("feature_name") or feature.get("feature_name", ""),
            "short_name": active.get("short_name") or feature.get("short_name", ""),
            "queue_order": active.get("order"),
            "why_this_feature": (
                "Selected from the active next item in the approved bottom-up SpecKit invocation queue."
                if active else "No active feature found; do not invoke SpecKit."
            ),
            "depends_on_features": active.get("depends_on_features") or feature.get("depends_on_features", []),
            "source_hld_sections": active.get("source_hld_sections") or feature.get("source_hld_sections", []),
        },
        "speckit_sequence": [
            "constitution if missing or update required",
            "specify",
            "clarify when SpecKit asks questions or markers remain",
            "plan",
            "tasks",
            "analyze when consistency review is needed",
            "implement only after explicit approval",
        ],
        "speckit_specify_input": active.get("speckit_specify_input") or feature.get("speckit_specify_input", ""),
        "constitution_context": {
            "target_path": constitution.get("target_constitution_path", ".specify/memory/constitution.md"),
            "required_rules": constitution.get("required_rules", []),
            "human_checkpoint": constitution.get("human_checkpoint", {}),
        },
        "architecture_context": {
            "bottom_up_order": graph.get("bottom_up_order", []),
            "dependency_edges": graph.get("edges", []),
            "decomposition_flags": feature.get("decomposition_flags", []),
            "api_interface_contract_notes": feature.get("api_interface_contract_notes", ""),
            "processing_functionality_notes": feature.get("processing_functionality_notes", ""),
            "shared_common_dependencies": feature.get("shared_common_dependencies", []),
        },
        "quality_context": {
            "quality_status": quality.get("status", ""),
            "beskeptic_findings": quality.get("findings", []),
            "first_feature_case": quality.get("case_to_present", {}).get("first_feature_case", {}),
        },
        "allowed_evidence_sources": [
            "HLD.raw.md",
            "HLD.md",
            ".specify/sync/hld_index.md",
            ".specify/sync/hld_sections/",
            ".specify/sync/spec_build_plan.json",
            ".specify/sync/spec_build_plan_review.md",
            ".specify/sync/speckit_input_manifest.json",
            ".specify/sync/speckit_invocation_queue.json",
            ".specify/sync/constitution_update_plan.json",
            ".specify/sync/feature_dependency_graph.json",
            ".specify/sync/speckit_prework_quality_review.json",
            ".specify/memory/constitution.md if present",
        ],
        "local_tools_allowed": ["rg", "grep", "find", "sed -n", "awk", "cat small files"],
        "question_answering_policy": {
            "ANSWER_FROM_EVIDENCE": "Use for answers directly supported by HLD/prework/approved constitution.",
            "ANSWER_FROM_REASONABLE_DEFAULT": "Use only when safe and not architecture/scope/security/data/dependency affecting.",
            "ESCALATE_TO_HUMAN": "Use for architecture, source-of-truth, constitution, API, security, data, UX, dependency, split/merge, or implementation approval questions.",
        },
        "phase_completion_report_required": True,
    }


def render_md(dossier: dict[str, Any]) -> str:
    selected = dossier["selected_feature"]
    lines = [
        "# SpecKit Proxy Dossier",
        "",
        "made by AI",
        "",
        f"Status: `{dossier['status']}`",
        f"Protocol: `{dossier['protocol']}`",
        "",
        "## Selected feature",
        "",
        f"- feature: `{selected.get('feature_id')}` - {selected.get('feature_name')}",
        f"- short name: `{selected.get('short_name')}`",
        f"- queue order: {selected.get('queue_order')}",
        f"- why this feature: {selected.get('why_this_feature')}",
        f"- depends on: {', '.join(selected.get('depends_on_features') or []) or 'none'}",
        f"- source HLD sections: {', '.join(selected.get('source_hld_sections') or []) or 'TBD'}",
        "",
        "## SpecKit sequence",
        "",
    ]
    for idx, phase in enumerate(dossier["speckit_sequence"], start=1):
        lines.append(f"{idx}. {phase}")
    lines += [
        "",
        "## Input for /speckit.specify",
        "",
        "```text",
        dossier.get("speckit_specify_input", ""),
        "```",
        "",
        "## Constitution context",
        "",
        f"- target path: `{dossier['constitution_context']['target_path']}`",
        "",
        "Required rules:",
    ]
    for rule in dossier["constitution_context"].get("required_rules", []):
        if isinstance(rule, dict):
            lines.append(f"- `{rule.get('rule_id', '')}` {rule.get('name', '')}: {rule.get('rule', '')}")
    lines += [
        "",
        "## Architecture context",
        "",
        f"- bottom-up order: {', '.join(str(x) for x in dossier['architecture_context'].get('bottom_up_order', [])) or 'TBD'}",
        f"- decomposition flags: {', '.join(dossier['architecture_context'].get('decomposition_flags', [])) or 'none'}",
        f"- API/interface notes: {dossier['architecture_context'].get('api_interface_contract_notes') or 'none'}",
        f"- processing/functionality notes: {dossier['architecture_context'].get('processing_functionality_notes') or 'none'}",
        "",
        "## Question handling",
        "",
        "- Answer from evidence when the answer is directly supported.",
        "- Use reasonable defaults only for non-architecture/non-scope/non-security choices.",
        "- Escalate to the judge/human for architecture, constitution, API, data ownership, dependency, split/merge, or implementation decisions.",
        "",
        "## Evidence sources",
        "",
    ]
    for source in dossier["allowed_evidence_sources"]:
        lines.append(f"- `{source}`")
    lines += [
        "",
        "## Local tools allowed",
        "",
    ]
    for tool in dossier["local_tools_allowed"]:
        lines.append(f"- `{tool}`")
    lines += [
        "",
        "## Phase completion report required",
        "",
        "After each SpecKit phase, report files changed, questions asked, questions answered from evidence, questions escalated, affected artifacts, and next-phase readiness.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a bounded dossier for a SpecKit proxy subagent.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    out = workspace / ".specify" / "sync"
    out.mkdir(parents=True, exist_ok=True)

    dossier = build_dossier(workspace)
    json_path = out / "speckit_proxy_dossier.json"
    md_path = out / "speckit_proxy_dossier.md"

    json_path.write_text(json.dumps(dossier, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(dossier), encoding="utf-8")

    print("SpecKit proxy dossier generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {dossier['status']}")
    print(f"- selected feature: {dossier['selected_feature'].get('feature_id', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
