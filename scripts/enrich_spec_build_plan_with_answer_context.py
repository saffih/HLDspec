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


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def source_ids(item: dict[str, Any]) -> set[str]:
    values = item.get("source_hld_sections")
    if isinstance(values, list):
        return {str(v) for v in values if str(v)}
    hld_id = item.get("hld_id")
    return {str(hld_id)} if hld_id else set()


def related_by_source(source_hlds: set[str], items: list[Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        if source_hlds & source_ids(item):
            result.append(item)
    return result


def compact_items(items: list[dict[str, Any]], keys: list[str], limit: int = 8) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items[:limit]:
        row: dict[str, Any] = {}
        for key in keys:
            if key in item:
                row[key] = item[key]
        if not row:
            row = {k: v for k, v in item.items() if k in {"id", "name", "title", "summary", "source_hld_sections"}}
        out.append(row)
    return out


def downstream_specs(spec_id: str, planned_specs: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for spec in planned_specs:
        deps = {str(x) for x in as_list(spec.get("depends_on_specs"))}
        if spec_id in deps:
            value = str(spec.get("planned_spec_id") or spec.get("id") or "")
            if value:
                out.append(value)
    return out


def build_context_for_spec(
    spec: dict[str, Any],
    planned_specs: list[dict[str, Any]],
    usecase: dict[str, Any],
    pm_pack: dict[str, Any],
    architect_pack: dict[str, Any],
    answer_dossier: dict[str, Any],
    interface_map: dict[str, Any],
    data_map: dict[str, Any],
    integration_map: dict[str, Any],
    open_questions: dict[str, Any],
) -> dict[str, Any]:
    spec_id = str(spec.get("planned_spec_id") or spec.get("id") or "")
    source_hlds = {str(x) for x in as_list(spec.get("source_hld_sections"))}

    use_cases = related_by_source(source_hlds, as_list(usecase.get("system_use_cases")))
    journeys = related_by_source(source_hlds, as_list(usecase.get("user_journeys")))
    feature_candidates = related_by_source(source_hlds, as_list(usecase.get("feature_candidates")))
    pm_stories = related_by_source(source_hlds, as_list(pm_pack.get("user_stories")))
    pm_questions = related_by_source(source_hlds, as_list(pm_pack.get("product_open_questions")))

    contracts = related_by_source(source_hlds, as_list(interface_map.get("contracts")))
    data_objects = related_by_source(source_hlds, as_list(data_map.get("data_objects")))
    integrations = related_by_source(source_hlds, as_list(integration_map.get("integrations")))
    arch_questions = related_by_source(source_hlds, as_list(architect_pack.get("architecture_open_questions")))
    tbd_items = related_by_source(source_hlds, as_list(open_questions.get("items")))

    dossier_specs = []
    for item in as_list(answer_dossier.get("specs")):
        if not isinstance(item, dict):
            continue
        if str(item.get("planned_spec_id")) == spec_id or source_hlds & source_ids(item):
            dossier_specs.append(item)

    feeds = downstream_specs(spec_id, planned_specs)
    no_direct_user_story = not pm_stories and not use_cases

    product_context = {
        "use_cases": compact_items(use_cases, ["id", "name", "summary", "source_hld_sections", "buildability_signals"]),
        "user_journeys": compact_items(journeys, ["id", "name", "summary", "source_hld_sections"]),
        "feature_candidates": compact_items(feature_candidates, ["hld_id", "title", "buildability_signals", "source_hld_sections"]),
        "user_stories": compact_items(pm_stories, ["story_id", "title", "story", "acceptance_criteria", "source_hld_sections"]),
        "acceptance_criteria": [criterion for story in pm_stories for criterion in as_list(story.get("acceptance_criteria"))][:20],
        "success_metrics": [
            metric
            for item in dossier_specs
            for metric in as_list(item.get("success_metrics_or_TBD"))
            if str(metric) != "TBD"
        ][:20],
        "product_open_questions": compact_items(pm_questions, ["question_id", "question", "phase", "source_hld_sections"]),
        "no_direct_user_story": no_direct_user_story,
        "no_direct_user_story_reason": "technical foundation or internal capability; do not invent a fake user story" if no_direct_user_story else "",
        "feeds_user_facing_specs": feeds,
    }

    architecture_context = {
        "interfaces": compact_items(contracts, ["contract_id", "contract_name", "provider", "consumer", "source_hld_sections"]),
        "contracts": compact_items(contracts, ["contract_id", "contract_name", "provider", "consumer", "source_of_truth", "source_hld_sections"]),
        "data_objects": compact_items(data_objects, ["data_object", "owner", "source_of_truth", "update_timing", "source_hld_sections"]),
        "integrations": compact_items(integrations, ["integration_id", "name", "producer", "consumer", "path_or_flow", "source_hld_sections"]),
        "architecture_open_questions": compact_items(arch_questions, ["question_id", "question", "phase", "source_hld_sections"]),
    }

    speckit_context = {
        "answer_dossier_specs": compact_items(
            dossier_specs,
            ["planned_spec_id", "capability_name", "plain_english_purpose", "source_of_truth_or_TBD", "update_timing_or_TBD", "source_hld_sections"],
        ),
        "clarify_questions": compact_items(tbd_items, ["question_or_tbd", "planned_spec_id", "source_hld_sections"]),
        "research_needed": [],
        "process_requirements": [
            item.get("summary") for item in journeys[:5] if isinstance(item.get("summary"), str) and item.get("summary")
        ],
        "tbd_or_needs_clarification": compact_items(tbd_items, ["question_or_tbd", "planned_spec_id", "source_hld_sections"]),
    }

    return {
        "product_context": product_context,
        "architecture_context": architecture_context,
        "speckit_context": speckit_context,
    }


def enrich_plan(plan_path: Path, workspace: Path) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    plan = load_json(plan_path)
    planned_specs = [item for item in as_list(plan.get("planned_specs")) if isinstance(item, dict)]

    usecase = load_json(sync / "hld_usecase_api_map.json")
    pm_pack = load_json(sync / "speckit_product_manager_pack.json")
    architect_pack = load_json(sync / "speckit_architect_pack.json")
    answer_dossier = load_json(sync / "speckit_answer_dossier.json")
    interface_map = load_json(sync / "interface_contract_map.json")
    data_map = load_json(sync / "data_ownership_map.json")
    integration_map = load_json(sync / "integration_map.json")
    open_questions = load_json(sync / "open_questions_tbd_map.json")

    enriched_specs: list[dict[str, Any]] = []
    for spec in planned_specs:
        enriched = dict(spec)
        enriched.update(
            build_context_for_spec(
                enriched,
                planned_specs,
                usecase,
                pm_pack,
                architect_pack,
                answer_dossier,
                interface_map,
                data_map,
                integration_map,
                open_questions,
            )
        )
        enriched_specs.append(enriched)

    plan["planned_specs"] = enriched_specs
    plan["context_enrichment"] = {
        "schema_version": 1,
        "status": "ENRICHED",
        "join_key": "source_hld_sections",
        "sources": [
            "hld_usecase_api_map.json",
            "speckit_product_manager_pack.json",
            "speckit_architect_pack.json",
            "speckit_answer_dossier.json",
            "interface_contract_map.json",
            "data_ownership_map.json",
            "integration_map.json",
            "open_questions_tbd_map.json",
        ],
        "planned_specs_enriched": len(enriched_specs),
        "planned_specs_with_user_stories": sum(1 for spec in enriched_specs if as_list(spec.get("product_context", {}).get("user_stories"))),
        "planned_specs_marked_no_direct_user_story": sum(1 for spec in enriched_specs if spec.get("product_context", {}).get("no_direct_user_story")),
        "planned_specs_with_architecture_context": sum(
            1
            for spec in enriched_specs
            if as_list(spec.get("architecture_context", {}).get("contracts"))
            or as_list(spec.get("architecture_context", {}).get("data_objects"))
            or as_list(spec.get("architecture_context", {}).get("integrations"))
        ),
    }

    write_json(plan_path, plan)
    return plan


def render_summary(plan: dict[str, Any]) -> str:
    summary = plan.get("context_enrichment", {}) if isinstance(plan.get("context_enrichment"), dict) else {}
    lines = [
        "# Spec Build Plan Context Enrichment",
        "",
        f"Status: `{summary.get('status', 'UNKNOWN')}`",
        f"Join key: `{summary.get('join_key', '')}`",
        "",
        "## Counts",
        "",
        f"- planned specs enriched: `{summary.get('planned_specs_enriched', 0)}`",
        f"- planned specs with user stories: `{summary.get('planned_specs_with_user_stories', 0)}`",
        f"- planned specs marked no direct user story: `{summary.get('planned_specs_marked_no_direct_user_story', 0)}`",
        f"- planned specs with architecture context: `{summary.get('planned_specs_with_architecture_context', 0)}`",
        "",
        "## Per-spec context",
        "",
    ]
    for spec in as_list(plan.get("planned_specs")):
        if not isinstance(spec, dict):
            continue
        pc = spec.get("product_context", {}) if isinstance(spec.get("product_context"), dict) else {}
        ac = spec.get("architecture_context", {}) if isinstance(spec.get("architecture_context"), dict) else {}
        lines += [
            f"### {spec.get('planned_spec_id')} - {spec.get('title', '')}",
            "",
            f"- use cases: `{len(as_list(pc.get('use_cases')))}`",
            f"- user stories: `{len(as_list(pc.get('user_stories')))}`",
            f"- no direct user story: `{str(bool(pc.get('no_direct_user_story'))).lower()}`",
            f"- contracts: `{len(as_list(ac.get('contracts')))}`",
            f"- data objects: `{len(as_list(ac.get('data_objects')))}`",
            f"- integrations: `{len(as_list(ac.get('integrations')))}`",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Enrich spec_build_plan planned_specs with PM/Architect/SpecKit context.")
    parser.add_argument("spec_build_plan_json")
    parser.add_argument("workspace", nargs="?")
    args = parser.parse_args()

    plan_path = Path(args.spec_build_plan_json).resolve()
    workspace = Path(args.workspace).resolve() if args.workspace else plan_path.parents[2]
    sync = workspace / ".specify" / "sync"

    plan = enrich_plan(plan_path, workspace)
    (sync / "spec_build_plan_context_enrichment.md").write_text(render_summary(plan), encoding="utf-8")

    summary = plan.get("context_enrichment", {})
    print("Spec build plan context enrichment complete:")
    print(f"- plan: {plan_path}")
    print(f"- report: {sync / 'spec_build_plan_context_enrichment.md'}")
    print(f"- enriched specs: {summary.get('planned_specs_enriched', 0)}")
    print(f"- specs with user stories: {summary.get('planned_specs_with_user_stories', 0)}")
    print(f"- specs marked no direct user story: {summary.get('planned_specs_marked_no_direct_user_story', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
