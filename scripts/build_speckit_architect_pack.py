#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def sync_dir(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    if (direct / "hld_usecase_api_map.json").exists() or (direct / "feature_dependency_graph.json").exists():
        return direct
    if (nested / "hld_usecase_api_map.json").exists() or (nested / "feature_dependency_graph.json").exists():
        return nested
    return direct


def hlds(item: dict[str, Any]) -> list[str]:
    values = item.get("source_hld_sections", [])
    if isinstance(values, list):
        return [str(v) for v in values]
    if item.get("hld_id"):
        return [str(item["hld_id"])]
    return []


def build_arch_open_questions(usecase: dict[str, Any], constitution: dict[str, Any], graph: dict[str, Any]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    counter = 1

    for api in as_list(usecase.get("api_interface_surfaces")):
        if isinstance(api, dict) and api.get("contract_risk") == "review_api_processing_split":
            questions.append(
                {
                    "question_id": f"ARQ-{counter:03d}",
                    "owner_role": "Architect",
                    "phase": "specify",
                    "classification": "ESCALATE_TO_HUMAN",
                    "question": f"Confirm API/interface boundary versus processing responsibility for {api.get('name', 'API surface')}.",
                    "why_evidence_is_insufficient": "The HLD text appears to mix API/interface and processing terms.",
                    "source_hld_sections": hlds(api),
                    "affected_artifacts": ["spec.md", "plan.md", "contracts/"],
                    "human_decision": "TBD",
                    "human_notes": "",
                }
            )
            counter += 1

    for data in as_list(usecase.get("data_source_of_truth_objects")):
        if isinstance(data, dict) and data.get("source_of_truth_risk"):
            questions.append(
                {
                    "question_id": f"ARQ-{counter:03d}",
                    "owner_role": "Architect",
                    "phase": "clarify",
                    "classification": "ESCALATE_TO_HUMAN",
                    "question": f"Confirm source-of-truth ownership and update timing for {data.get('name', 'data object')}.",
                    "why_evidence_is_insufficient": "The map detected state/source-of-truth/data terms that may affect architecture.",
                    "source_hld_sections": hlds(data),
                    "affected_artifacts": ["data-model.md", "plan.md"],
                    "human_decision": "TBD",
                    "human_notes": "",
                }
            )
            counter += 1

    checkpoint = constitution.get("human_checkpoint", {})
    if isinstance(checkpoint, dict) and str(checkpoint.get("human_decision", "TBD")) == "TBD":
        questions.append(
            {
                "question_id": f"ARQ-{counter:03d}",
                "owner_role": "Architect",
                "phase": "constitution",
                "classification": "ESCALATE_TO_HUMAN",
                "question": "Approve or modify the constitution update plan before SpecKit constitution/specify.",
                "why_evidence_is_insufficient": "Constitution rules affect all later SpecKit outputs and require explicit approval.",
                "source_hld_sections": [],
                "affected_artifacts": ["constitution.md", "spec.md", "plan.md"],
                "human_decision": "TBD",
                "human_notes": "",
            }
        )
        counter += 1

    if not as_list(graph.get("bottom_up_order")) and as_list(usecase.get("feature_candidates")):
        questions.append(
            {
                "question_id": f"ARQ-{counter:03d}",
                "owner_role": "Architect",
                "phase": "plan",
                "classification": "ESCALATE_TO_HUMAN",
                "question": "Confirm feature dependency order before SpecKit planning.",
                "why_evidence_is_insufficient": "Feature candidates exist but no bottom-up dependency order was available.",
                "source_hld_sections": [],
                "affected_artifacts": ["plan.md", "tasks.md"],
                "human_decision": "TBD",
                "human_notes": "",
            }
        )
    return questions


def build_pack(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    usecase = load_json(sync / "hld_usecase_api_map.json")
    constitution = load_json(sync / "constitution_update_plan.json")
    graph = load_json(sync / "feature_dependency_graph.json")
    dossier = load_json(sync / "speckit_proxy_dossier.json")

    api = as_list(usecase.get("api_interface_surfaces"))
    data = as_list(usecase.get("data_source_of_truth_objects"))
    deps = as_list(usecase.get("dependencies"))
    risks = as_list(usecase.get("risks"))
    questions = build_arch_open_questions(usecase, constitution, graph)

    pack = {
        "schema_version": 1,
        "status": "ARCHITECTURE_QUESTIONS_BLOCKING" if questions else "READY",
        "workspace": str(workspace),
        "role": "Architect",
        "purpose": "Define architecture evidence, boundaries, and open technical questions before SpecKit execution.",
        "selected_feature": dossier.get("selected_feature", {}),
        "api_interface_boundaries": api,
        "data_source_of_truth_objects": data,
        "dependencies": deps,
        "dependency_order": graph.get("bottom_up_order", []),
        "constitution_rules": constitution.get("required_rules", []),
        "risks": risks,
        "architecture_open_questions": questions,
    }
    return pack


def render_md(pack: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Architect Pack",
        "",
        "",
        "",
        f"Status: `{pack.get('status')}`",
        "",
        "## Architecture summary",
        "",
        f"- API/interface surfaces: {len(as_list(pack.get('api_interface_boundaries')))}",
        f"- data/source-of-truth objects: {len(as_list(pack.get('data_source_of_truth_objects')))}",
        f"- dependency edges: {len(as_list(pack.get('dependencies')))}",
        f"- risks: {len(as_list(pack.get('risks')))}",
        "",
        "## Architecture open questions",
        "",
    ]
    questions = as_list(pack.get("architecture_open_questions"))
    if not questions:
        lines.append("- none")
    for q in questions:
        if isinstance(q, dict):
            lines += [
                f"### {q.get('question_id')}",
                "",
                f"- phase: `{q.get('phase')}`",
                f"- classification: `{q.get('classification')}`",
                f"- question: {q.get('question')}",
                f"- why insufficient: {q.get('why_evidence_is_insufficient')}",
                f"- affected artifacts: {', '.join(q.get('affected_artifacts', []))}",
                "",
            ]
    lines += ["", "## Dependency order", ""]
    order = as_list(pack.get("dependency_order"))
    lines.append(", ".join(str(x) for x in order) if order else "TBD")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Architect pack for SpecKit answer preparation.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    sync = sync_dir(workspace)
    sync.mkdir(parents=True, exist_ok=True)
    pack = build_pack(workspace)
    (sync / "speckit_architect_pack.json").write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / "speckit_architect_pack.md").write_text(render_md(pack), encoding="utf-8")
    print("SpecKit Architect pack generated:")
    print(f"- json: {sync / 'speckit_architect_pack.json'}")
    print(f"- report: {sync / 'speckit_architect_pack.md'}")
    print(f"- status: {pack['status']}")
    print(f"- open questions: {len(pack['architecture_open_questions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
