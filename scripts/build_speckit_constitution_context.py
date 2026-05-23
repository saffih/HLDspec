#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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
    if (direct / "hldspec_architecture_analysis.json").exists() or (direct / "hldspec_state.json").exists():
        return direct
    if (nested / "hldspec_architecture_analysis.json").exists() or (nested / "hldspec_state.json").exists():
        return nested
    direct.mkdir(parents=True, exist_ok=True)
    return direct


def build_context(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    analysis = load_json(sync / "hldspec_architecture_analysis.json")

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "status": "CONSTITUTION_CONTEXT_READY_FOR_REVIEW",
        "constitution_role": "compact shared SpecKit context plus governance; not a full HLD duplicate",
        "source_of_truth_hierarchy": [
            "HLD is the canonical architecture, intent, ordering, and scope source.",
            "Constitution provides reusable architecture context, governance rules, and validation gates for SpecKit.",
            "Feature specs are derived capability contracts and must not contradict HLD or constitution.",
            "Implementation is derived from approved specs only.",
        ],
        "architecture_layer_model": [
            {
                "layer": "foundation_data_tool",
                "meaning": "low-level DB/storage/tool/programmatic interfaces and state ownership",
                "must_not_own": "product logic or external API semantics",
            },
            {
                "layer": "use_logic_orchestration",
                "meaning": "domain behavior, lifecycle, orchestration, and policy over tools",
                "must_not_own": "low-level persistence mechanics or UI presentation",
            },
            {
                "layer": "api_contract",
                "meaning": "caller-facing contract: endpoints, commands, inputs, outputs, errors, behavior",
                "must_not_own": "internal state mechanics",
            },
            {
                "layer": "ui_workflow",
                "meaning": "screens, flows, user interactions, and presentation-level scenarios",
                "must_not_own": "core data/state rules",
            },
            {
                "layer": "operations_validation",
                "meaning": "reliability, deployment, observability, validation, and testing",
                "must_not_own": "feature architecture decisions",
            },
        ],
        "interface_taxonomy": [
            "DB tool interface",
            "storage tool interface",
            "programmatic internal interface",
            "use-logic/orchestration interface",
            "external API contract",
            "UI/workflow surface",
        ],
        "split_rules": [
            "If one planned spec mixes low-level tool/state ownership with use-logic/orchestration and API contract, split it.",
            "If layers can evolve independently, split them into separate specs.",
            "Shared/common capabilities must be specified before dependent features.",
        ],
        "no_invention_rules": [
            "If source-of-truth ownership is not explicit in HLD evidence, mark TBD/defer.",
            "If update timing is not explicit in HLD evidence, mark TBD/defer.",
            "If product metadata is not explicit in HLD evidence, mark TBD/defer.",
            "Do not invent architecture in constitution, specs, or SpecKit prompts.",
        ],
        "checkpoint_triage_rules": [
            "If a checkpoint contains more than 5 open questions, group by root cause before asking the human.",
            "Apply existing human decisions when the mapping is clear.",
            "Ask only unresolved group-level questions.",
        ],
        "speckit_boundaries": [
            "HLDspec prepares inputs and governance context.",
            "SpecKit owns generated spec, plan, research, data-model, contract, and task artifacts.",
            "This readiness step does not invoke real SpecKit.",
            "This readiness step does not implement.",
        ],
        "validation_gates": [
            "Spec has HLD anchors or explicit TBD/defer.",
            "Spec has one stable capability.",
            "Spec dependencies and blockers are explicit.",
            "Spec acceptance criteria are testable.",
            "Spec does not contradict HLD, architecture context, or constitution.",
        ],
        "architecture_analysis_status": analysis.get("status", "MISSING"),
        "architecture_findings": analysis.get("findings", []),
    }


def render_md(data: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Constitution Context Pack",
        "",
        "made by AI",
        "",
        f"Status: `{data.get('status')}`",
        "",
        "## Role",
        "",
        data["constitution_role"],
        "",
        "## Source-of-truth hierarchy",
        "",
    ]
    for item in data["source_of_truth_hierarchy"]:
        lines.append(f"- {item}")

    lines += ["", "## Architecture layer model", ""]
    for layer in data["architecture_layer_model"]:
        lines += [
            f"### {layer['layer']}",
            "",
            f"- meaning: {layer['meaning']}",
            f"- must not own: {layer['must_not_own']}",
            "",
        ]

    for title, key in [
        ("Interface taxonomy", "interface_taxonomy"),
        ("Split rules", "split_rules"),
        ("No-invention/defer rules", "no_invention_rules"),
        ("Checkpoint triage rules", "checkpoint_triage_rules"),
        ("SpecKit boundaries", "speckit_boundaries"),
        ("Validation gates", "validation_gates"),
    ]:
        lines += [f"## {title}", ""]
        for item in data[key]:
            lines.append(f"- {item}")
        lines.append("")

    lines += [
        "## Architecture analysis status",
        "",
        f"- status: `{data.get('architecture_analysis_status')}`",
        f"- findings: {len(data.get('architecture_findings') or [])}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact constitution context for SpecKit readiness.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sync = sync_dir(workspace)
    data = build_context(workspace)
    json_path = sync / "speckit_constitution_context.json"
    md_path = sync / "speckit_constitution_context.md"
    write_json(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("SpecKit constitution context generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
