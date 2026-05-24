#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


API_WORDS = {
    "api", "endpoint", "http", "route", "request", "response", "contract",
    "interface", "schema", "cli", "command", "event", "webhook",
}
PROCESSING_WORDS = {
    "process", "processing", "workflow", "orchestration", "execute", "execution",
    "state", "transition", "persist", "database", "storage", "mutation",
    "side effect", "background", "worker", "sync",
}
COMMON_WORDS = {
    "common", "shared", "foundation", "base", "core", "model", "validation",
    "utility", "service", "library", "config", "configuration", "auth",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "feature"


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def text_of(value: Any) -> str:
    if isinstance(value, str):
        return value
    return ""


def natural_key(value: str) -> tuple[int, str]:
    match = re.search(r"(\d+)", value)
    if match:
        return (int(match.group(1)), value)
    return (10**9, value)


def infer_notes(title: str, summary: str = "") -> dict[str, Any]:
    lower = f"{title} {summary}".lower()
    has_api = any(word in lower for word in API_WORDS)
    has_processing = any(word in lower for word in PROCESSING_WORDS)
    has_common = any(word in lower for word in COMMON_WORDS)

    # API "design/surface" sections frequently mix externally visible contract
    # concerns with internal handling choices. Treat them as boundary-review
    # candidates even when the title does not explicitly say "processing".
    api_surface_boundary_risk = has_api and (
        has_processing
        or "surface" in lower
        or "design" in lower
        or "endpoint" in lower
    )

    return {
        "api_interface_contract_notes": (
            "Likely contains public interface/API/command/contract concerns; verify with HLD evidence."
            if has_api else ""
        ),
        "processing_functionality_notes": (
            "Likely contains workflow/state/processing behavior; keep separate from external contracts when independent."
            if has_processing else (
                "API surface/design section should be reviewed for hidden processing behavior before SpecKit invocation."
                if api_surface_boundary_risk else ""
            )
        ),
        "shared_common_dependencies": (
            ["shared/common foundation candidate"]
            if has_common else []
        ),
        "decomposition_flags": [
            flag
            for flag, enabled in [
                ("SPLIT_API_CONTRACT_FROM_PROCESSING", api_surface_boundary_risk),
                ("EXTRACT_COMMON_FOUNDATION", has_common),
            ]
            if enabled
        ],
    }


def build_feature_item(spec: dict[str, Any], idx: int) -> dict[str, Any]:
    spec_id = str(spec.get("planned_spec_id") or spec.get("id") or f"{idx:03d}")
    title = text_of(spec.get("title")) or f"Feature {spec_id}"
    slug = text_of(spec.get("slug")) or f"{spec_id}-{slugify(title)}"
    source_hld_sections = [str(item) for item in as_list(spec.get("source_hld_sections"))]
    depends_on = [str(item) for item in as_list(spec.get("depends_on_specs"))]
    quality_flags = [str(item) for item in as_list(spec.get("quality_flags"))]
    summary = text_of(spec.get("summary")) or text_of(spec.get("description"))
    inferred = infer_notes(title, summary)

    description_lines = [
        f"Build {title}.",
        "",
        "Context from HLDspec:",
        f"- Planned spec id: {spec_id}",
        f"- Source HLD sections: {', '.join(source_hld_sections) or 'TBD'}",
    ]
    if summary:
        description_lines += ["", "HLD summary:", summary]
    if inferred["api_interface_contract_notes"]:
        description_lines += ["", "API/interface guidance:", inferred["api_interface_contract_notes"]]
    if inferred["processing_functionality_notes"]:
        description_lines += ["", "Processing/functionality guidance:", inferred["processing_functionality_notes"]]
    if quality_flags:
        description_lines += ["", "Known plan review flags:", *[f"- {flag}" for flag in quality_flags]]
    if depends_on:
        description_lines += ["", "Dependencies that must be specified first:", *[f"- {dep}" for dep in depends_on]]

    return {
        "feature_id": spec_id,
        "feature_name": title,
        "short_name": slugify(slug),
        "source_hld_sections": source_hld_sections,
        "user_stories": as_list(spec.get("user_stories")) or as_list(spec.get("product_context", {}).get("user_stories") if isinstance(spec.get("product_context"), dict) else []),
        "use_cases": as_list(spec.get("use_cases")) or as_list(spec.get("product_context", {}).get("use_cases") if isinstance(spec.get("product_context"), dict) else []),
        "user_journeys": as_list(spec.get("user_journeys")) or as_list(spec.get("product_context", {}).get("user_journeys") if isinstance(spec.get("product_context"), dict) else []),
        "product_context": spec.get("product_context", {}) if isinstance(spec.get("product_context"), dict) else {},
        "architecture_context": spec.get("architecture_context", {}) if isinstance(spec.get("architecture_context"), dict) else {},
        "speckit_context": spec.get("speckit_context", {}) if isinstance(spec.get("speckit_context"), dict) else {},
        "api_interface_contract_notes": inferred["api_interface_contract_notes"],
        "processing_functionality_notes": inferred["processing_functionality_notes"],
        "shared_common_dependencies": inferred["shared_common_dependencies"],
        "depends_on_features": depends_on,
        "constitution_implications": [
            "Must preserve HLD architecture boundaries.",
            "Must pass SpecKit constitution checks before planning proceeds.",
        ],
        "decomposition_flags": inferred["decomposition_flags"],
        "quality_flags": quality_flags,
        "speckit_specify_input": "\n".join(description_lines).strip(),
        "recommended_speckit_phase": "READY_FOR_SPECKIT_SPECIFY",
        "status": "PENDING_HUMAN_PLAN_REVIEW",
    }


def order_features(features: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    by_id = {str(item["feature_id"]): item for item in features}
    deps: dict[str, set[str]] = {}
    dependents: dict[str, set[str]] = {fid: set() for fid in by_id}
    warnings: list[str] = []

    for fid, item in by_id.items():
        item_deps: set[str] = set()
        for dep in item.get("depends_on_features", []):
            dep_id = str(dep)
            if dep_id in by_id and dep_id != fid:
                item_deps.add(dep_id)
                dependents.setdefault(dep_id, set()).add(fid)
            elif dep_id and dep_id != fid:
                warnings.append(f"{fid} depends on missing feature {dep_id}")
        deps[fid] = item_deps

    ready = sorted([fid for fid, d in deps.items() if not d], key=natural_key)
    ordered: list[str] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for child in sorted(dependents.get(current, set()), key=natural_key):
            deps[child].discard(current)
            if not deps[child] and child not in ordered and child not in ready:
                ready.append(child)
        ready.sort(key=natural_key)

    unresolved = [fid for fid, d in deps.items() if d]
    if unresolved:
        warnings.append("Dependency cycle or unresolved chain: " + ", ".join(sorted(unresolved, key=natural_key)))
        for fid in sorted(unresolved, key=natural_key):
            if fid not in ordered:
                ordered.append(fid)

    return [by_id[fid] for fid in ordered], warnings


def ordered_features_from_plan(features: list[dict[str, Any]], plan: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    """Use spec_build_plan.recommended_order when present, with dependency validation."""
    recommended = [str(item) for item in as_list(plan.get("recommended_order")) if str(item)]
    if not recommended:
        return order_features(features)

    by_id = {str(item["feature_id"]): item for item in features}
    warnings: list[str] = []

    seen: set[str] = set()
    ordered_ids: list[str] = []
    for feature_id in recommended:
        if feature_id in seen:
            warnings.append(f"recommended_order duplicate feature id {feature_id}")
            continue
        seen.add(feature_id)
        if feature_id not in by_id:
            warnings.append(f"recommended_order references missing feature {feature_id}")
            continue
        ordered_ids.append(feature_id)

    for feature_id in sorted(by_id, key=natural_key):
        if feature_id not in seen:
            warnings.append(f"recommended_order omitted feature {feature_id}; appended after listed features")
            ordered_ids.append(feature_id)

    position = {feature_id: idx for idx, feature_id in enumerate(ordered_ids)}
    for feature_id in ordered_ids:
        feature = by_id[feature_id]
        for dep in feature.get("depends_on_features", []):
            dep_id = str(dep)
            if dep_id in position and position[dep_id] > position[feature_id]:
                warnings.append(f"recommended_order violates dependency: {feature_id} appears before dependency {dep_id}")

    return [by_id[feature_id] for feature_id in ordered_ids], warnings


def build_artifacts(plan: dict[str, Any], plan_path: Path) -> dict[str, dict[str, Any]]:
    planned_specs = [item for item in as_list(plan.get("planned_specs")) if isinstance(item, dict)]
    features = [build_feature_item(spec, idx + 1) for idx, spec in enumerate(planned_specs)]
    ordered_features, warnings = ordered_features_from_plan(features, plan)

    plan_quality = plan.get("plan_quality", {})
    if not isinstance(plan_quality, dict):
        plan_quality = {}

    graph_edges = []
    for feature in ordered_features:
        for dep in feature.get("depends_on_features", []):
            graph_edges.append({"from": str(dep), "to": feature["feature_id"], "type": "depends_on"})

    constitution_rules = [
        {
            "rule_id": "ARCH-001",
            "name": "HLD Architecture Source of Truth",
            "rule": "SpecKit specs and plans must not contradict HLD architecture facts.",
            "rationale": "HLDspec extracts architecture constraints; SpecKit uses them as governing context.",
        },
        {
            "rule_id": "ARCH-002",
            "name": "API Contract and Processing Separation",
            "rule": "API/interface contracts must be separated from processing behavior when they can change independently.",
            "rationale": "Prevents mixed feature specs and allows contracts, workflows, and implementations to evolve safely.",
        },
        {
            "rule_id": "ARCH-003",
            "name": "Common Foundation Before Dependents",
            "rule": "Shared/common capabilities must be specified before dependent user-facing features.",
            "rationale": "Supports bottom-up implementation and prevents duplicate foundations.",
        },
        {
            "rule_id": "ARCH-004",
            "name": "SpecKit Ownership Boundary",
            "rule": "HLDspec prepares SpecKit inputs; SpecKit creates spec.md, plan.md, research.md, data-model.md, contracts, quickstart.md, tasks.md, and implementation artifacts.",
            "rationale": "Avoids reimplementing SpecKit and keeps generated artifacts owned by the tool designed for them.",
        },
    ]

    manifest = {
        "schema_version": 1,
        "status": "PENDING_HUMAN_REVIEW",
        "source_plan": str(plan_path),
        "plan_quality": {
            "decision": plan_quality.get("decision", ""),
            "recommendation": plan_quality.get("recommendation", ""),
            "conflicts": as_list(plan_quality.get("conflicts")),
            "findings": as_list(plan_quality.get("findings")),
        },
        "ownership_boundary": {
            "hldspec_owns": [
                "HLD extraction",
                "feature/use-case/user-journey decomposition",
                "architecture dependency graph",
                "constitution update plan",
                "bottom-up SpecKit invocation order",
                "checkpoint orchestration",
            ],
            "speckit_owns": [
                "spec.md",
                "checklists/requirements.md",
                "plan.md",
                "research.md",
                "data-model.md",
                "contracts/",
                "quickstart.md",
                "tasks.md",
                "implementation phase",
            ],
        },
        "features": ordered_features,
        "warnings": warnings,
    }

    invocation_queue = {
        "schema_version": 1,
        "status": "PENDING_HUMAN_PLAN_APPROVAL",
        "execution_mode": "ONE_SPECKIT_FEATURE_AT_A_TIME",
        "source_manifest": "speckit_input_manifest.json",
        "rules": [
            "Do not manually create final SpecKit artifacts.",
            "Invoke SpecKit one feature at a time after human approval.",
            "Follow dependency order from feature_dependency_graph.",
            "Run constitution/update review before invoking SpecKit.",
        ],
        "items": [
            {
                "order": idx,
                "feature_id": feature["feature_id"],
                "feature_name": feature["feature_name"],
                "short_name": feature["short_name"],
                "speckit_command": "/speckit.specify",
                "speckit_specify_input": feature["speckit_specify_input"],
                "depends_on_features": feature["depends_on_features"],
                "source_hld_sections": feature["source_hld_sections"],
                "product_context": feature.get("product_context", {}),
                "architecture_context": feature.get("architecture_context", {}),
                "speckit_context": feature.get("speckit_context", {}),
                "recommended_phase": feature["recommended_speckit_phase"],
                "status": "PENDING_HUMAN_PLAN_REVIEW" if idx == 1 else "WAITING_FOR_DEPENDENCIES",
            }
            for idx, feature in enumerate(ordered_features, start=1)
        ],
    }

    constitution_plan = {
        "schema_version": 1,
        "status": "PENDING_HUMAN_REVIEW",
        "target_constitution_path": ".specify/memory/constitution.md",
        "source_plan": str(plan_path),
        "required_rules": constitution_rules,
        "template_sync_targets": [
            ".specify/templates/plan-template.md",
            ".specify/templates/spec-template.md",
            ".specify/templates/tasks-template.md",
            ".specify/templates/commands/*.md",
        ],
        "human_checkpoint": {
            "question": "Does this constitution plan correctly protect the architecture before invoking SpecKit?",
            "options": [
                "APPROVE_PLAN",
                "MODIFY_PLAN",
                "DECOMPOSE_MORE",
                "FIX_CONSTITUTION",
                "REBUILD_DEPENDENCY_GRAPH",
            ],
            "human_decision": "TBD",
        },
    }

    dependency_graph = {
        "schema_version": 1,
        "status": "PENDING_HUMAN_REVIEW",
        "nodes": [
            {
                "feature_id": feature["feature_id"],
                "feature_name": feature["feature_name"],
                "decomposition_flags": feature["decomposition_flags"],
                "source_hld_sections": feature["source_hld_sections"],
            }
            for feature in ordered_features
        ],
        "edges": graph_edges,
        "warnings": warnings,
        "bottom_up_order": [feature["feature_id"] for feature in ordered_features],
    }

    return {
        "speckit_input_manifest": manifest,
        "speckit_invocation_queue": invocation_queue,
        "constitution_update_plan": constitution_plan,
        "feature_dependency_graph": dependency_graph,
    }


def render_manifest(data: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Input Manifest",
        "",
        "",
        "",
        f"Status: `{data['status']}`",
        f"Source plan: `{data['source_plan']}`",
        "",
        "## Ownership boundary",
        "",
        "HLDspec owns extraction, architecture decomposition, dependency ordering, constitution planning, and orchestration.",
        "",
        "SpecKit owns final generated feature artifacts such as `spec.md`, `plan.md`, `tasks.md`, and implementation.",
        "",
        "## Features prepared for SpecKit",
        "",
    ]
    for feature in data["features"]:
        lines += [
            f"### {feature['feature_id']} - {feature['feature_name']}",
            "",
            f"- short name: `{feature['short_name']}`",
            f"- source HLD sections: {', '.join(feature['source_hld_sections']) or 'TBD'}",
            f"- depends on: {', '.join(feature['depends_on_features']) or 'none'}",
            f"- decomposition flags: {', '.join(feature['decomposition_flags']) or 'none'}",
            f"- use cases: {len(feature.get('use_cases', []))}",
            f"- user stories: {len(feature.get('user_stories', []))}",
            f"- no direct user story: {str(bool(feature.get('product_context', {}).get('no_direct_user_story'))).lower() if isinstance(feature.get('product_context'), dict) else 'false'}",
            "",
            "SpecKit specify input:",
            "",
            "```text",
            feature["speckit_specify_input"],
            "```",
            "",
        ]
    return "\n".join(lines)


def render_queue(data: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Invocation Queue",
        "",
        "",
        "",
        f"Status: `{data['status']}`",
        f"Execution mode: `{data['execution_mode']}`",
        "",
        "## Rules",
        "",
    ]
    for rule in data["rules"]:
        lines.append(f"- {rule}")
    lines += ["", "## Queue", ""]
    for item in data["items"]:
        lines += [
            f"### {item['order']}. {item['feature_id']} - {item['feature_name']}",
            "",
            f"- command: `{item['speckit_command']}`",
            f"- short name: `{item['short_name']}`",
            f"- status: `{item['status']}`",
            f"- depends on: {', '.join(item['depends_on_features']) or 'none'}",
            "",
        ]
    lines += [
        "## Human checkpoint",
        "",
        "Approve the manifest, constitution plan, and dependency graph before invoking SpecKit.",
        "",
    ]
    return "\n".join(lines)


def render_constitution(data: dict[str, Any]) -> str:
    lines = [
        "# Constitution Update Plan",
        "",
        "",
        "",
        f"Status: `{data['status']}`",
        f"Target constitution path: `{data['target_constitution_path']}`",
        "",
        "## Required architecture rules",
        "",
    ]
    for rule in data["required_rules"]:
        lines += [
            f"### {rule['rule_id']} - {rule['name']}",
            "",
            f"- rule: {rule['rule']}",
            f"- rationale: {rule['rationale']}",
            "",
        ]
    checkpoint = data["human_checkpoint"]
    lines += [
        "## Human checkpoint",
        "",
        checkpoint["question"],
        "",
        "Options:",
    ]
    for option in checkpoint["options"]:
        lines.append(f"- {option}")
    lines.append("")
    return "\n".join(lines)


def render_graph(data: dict[str, Any]) -> str:
    lines = [
        "# Feature Dependency Graph",
        "",
        "",
        "",
        f"Status: `{data['status']}`",
        "",
        "## Bottom-up order",
        "",
    ]
    for idx, feature_id in enumerate(data["bottom_up_order"], start=1):
        node = next((node for node in data["nodes"] if node["feature_id"] == feature_id), {})
        lines.append(f"{idx}. `{feature_id}` - {node.get('feature_name', '')}")
    lines += ["", "## Dependencies", ""]
    if not data["edges"]:
        lines.append("No explicit feature dependencies found.")
    for edge in data["edges"]:
        lines.append(f"- `{edge['from']}` -> `{edge['to']}` ({edge['type']})")
    if data["warnings"]:
        lines += ["", "## Warnings", ""]
        for warning in data["warnings"]:
            lines.append(f"- {warning}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HLDspec-to-SpecKit handoff artifacts.")
    parser.add_argument("spec_build_plan_json")
    parser.add_argument("workspace", nargs="?")
    args = parser.parse_args()

    plan_path = Path(args.spec_build_plan_json)
    workspace = Path(args.workspace) if args.workspace else plan_path.parents[2]
    out = workspace / ".specify" / "sync"
    out.mkdir(parents=True, exist_ok=True)

    artifacts = build_artifacts(load_json(plan_path), plan_path)

    writers = {
        "speckit_input_manifest": render_manifest,
        "speckit_invocation_queue": render_queue,
        "constitution_update_plan": render_constitution,
        "feature_dependency_graph": render_graph,
    }

    for name, data in artifacts.items():
        (out / f"{name}.json").write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out / f"{name}.md").write_text(writers[name](data), encoding="utf-8")

    print("SpecKit prework artifacts generated:")
    for name in artifacts:
        print(f"- {out / (name + '.json')}")
        print(f"- {out / (name + '.md')}")
    print("- status: PENDING_HUMAN_REVIEW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
