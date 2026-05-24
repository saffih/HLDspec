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
    if (direct / "hld_usecase_api_map.json").exists() or (direct / "spec_build_plan.json").exists():
        return direct
    if (nested / "hld_usecase_api_map.json").exists() or (nested / "spec_build_plan.json").exists():
        return nested
    return direct


def source_sections(item: dict[str, Any]) -> list[str]:
    values = item.get("source_hld_sections", [])
    if isinstance(values, list):
        return [str(v) for v in values]
    hld_id = item.get("hld_id")
    return [str(hld_id)] if hld_id else []


def build_user_story(index: int, use_case: dict[str, Any]) -> dict[str, Any]:
    name = str(use_case.get("name") or use_case.get("title") or f"Use case {index}")
    actors = use_case.get("actors", [])
    actor = str(actors[0]) if isinstance(actors, list) and actors else "user"
    signals = [str(x) for x in as_list(use_case.get("buildability_signals"))]
    sections = source_sections(use_case)
    acceptance = [
        f"The workflow for {name} is represented in an approved SpecKit specification.",
        "The specification cites the relevant HLD source sections.",
        "Open product questions are answered or explicitly escalated before implementation.",
    ]
    if "api_interface" in signals:
        acceptance.append("The user-facing/API behavior is separated from processing details.")
    if "ui_interaction" in signals:
        acceptance.append("The user-visible status, prompt, or checkpoint behavior is explicit.")
    return {
        "story_id": f"US-{index:03d}",
        "title": name,
        "source_hld_sections": sections,
        "story": f"As a {actor}, I want {name}, so that the product behavior is explicit and testable.",
        "acceptance_criteria": acceptance,
        "signals": signals,
        "evidence": use_case.get("summary", ""),
    }


def build_product_open_questions(data: dict[str, Any], stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions: list[dict[str, Any]] = []
    counter = 1

    for q in as_list(data.get("open_questions")):
        if not isinstance(q, dict):
            continue
        questions.append(
            {
                "question_id": f"PMQ-{counter:03d}",
                "owner_role": "Product Manager",
                "phase": "specify",
                "classification": "ESCALATE_TO_HUMAN",
                "question": str(q.get("question", "Resolve product requirement question.")),
                "why_evidence_is_insufficient": "HLDspec detected this as an unresolved HLD/product question.",
                "source_hld_sections": source_sections(q),
                "affected_artifacts": ["speckit_specify_answers", "spec.md"],
                "human_decision": "TBD",
                "human_notes": "",
            }
        )
        counter += 1

    if not stories:
        questions.append(
            {
                "question_id": f"PMQ-{counter:03d}",
                "owner_role": "Product Manager",
                "phase": "specify",
                "classification": "ESCALATE_TO_HUMAN",
                "question": "What is the first user-visible/use-case story SpecKit should specify?",
                "why_evidence_is_insufficient": "No system use cases were extracted from the HLD use-case/API map.",
                "source_hld_sections": [],
                "affected_artifacts": ["hld_usecase_api_map", "speckit_specify_answers"],
                "human_decision": "TBD",
                "human_notes": "",
            }
        )
        counter += 1

    for story in stories:
        if not story.get("source_hld_sections"):
            questions.append(
                {
                    "question_id": f"PMQ-{counter:03d}",
                    "owner_role": "Product Manager",
                    "phase": "specify",
                    "classification": "ESCALATE_TO_HUMAN",
                    "question": f"Which HLD section is the evidence source for user story {story['story_id']}?",
                    "why_evidence_is_insufficient": "The extracted user story has no source HLD section link.",
                    "source_hld_sections": [],
                    "affected_artifacts": ["speckit_specify_answers"],
                    "human_decision": "TBD",
                    "human_notes": "",
                }
            )
            counter += 1

    return questions


def build_pack(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    usecase = load_json(sync / "hld_usecase_api_map.json")
    plan = load_json(sync / "spec_build_plan.json")

    use_cases = [x for x in as_list(usecase.get("system_use_cases")) if isinstance(x, dict)]
    feature_candidates = [x for x in as_list(usecase.get("feature_candidates")) if isinstance(x, dict)]
    stories = [build_user_story(i, uc) for i, uc in enumerate(use_cases, start=1)]

    first = usecase.get("first_buildable_feature", {})
    if not isinstance(first, dict):
        first = {}

    pack = {
        "schema_version": 1,
        "status": "READY" if stories else "PRODUCT_QUESTIONS_BLOCKING",
        "workspace": str(workspace),
        "source_hld": usecase.get("source_hld", ""),
        "role": "Product Manager",
        "purpose": "Define the user/use-case story evidence SpecKit may use for constitution/specify/clarify.",
        "selected_first_feature": first,
        "user_stories": stories,
        "use_cases": use_cases,
        "feature_candidates": feature_candidates,
        "non_goals": as_list(usecase.get("non_goals")),
        "product_open_questions": build_product_open_questions(usecase, stories),
        "spec_plan_summary": {
            "planned_specs": len(as_list(plan.get("planned_specs"))),
            "plan_quality": plan.get("plan_quality", {}),
        },
    }

    if pack["product_open_questions"]:
        pack["status"] = "PRODUCT_QUESTIONS_BLOCKING"
    return pack


def render_md(pack: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Product Manager Pack",
        "",
        "",
        "",
        f"Status: `{pack.get('status')}`",
        "",
        "## Selected first feature",
        "",
    ]
    first = pack.get("selected_first_feature", {}) if isinstance(pack.get("selected_first_feature"), dict) else {}
    lines += [
        f"- HLD: `{first.get('hld_id', '')}`",
        f"- title: {first.get('title', '')}",
        f"- why first: {first.get('why_first', '')}",
        "",
        "## User stories",
        "",
    ]
    for story in as_list(pack.get("user_stories")):
        if isinstance(story, dict):
            lines += [
                f"### {story.get('story_id')} - {story.get('title')}",
                "",
                story.get("story", ""),
                "",
                "Acceptance criteria:",
            ]
            for item in as_list(story.get("acceptance_criteria")):
                lines.append(f"- {item}")
            lines.append(f"- source HLD sections: {', '.join(story.get('source_hld_sections', [])) or 'TBD'}")
            lines.append("")
    if not pack.get("user_stories"):
        lines.append("- none")
    lines += ["", "## Product open questions", ""]
    questions = as_list(pack.get("product_open_questions"))
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
                f"- source HLD sections: {', '.join(q.get('source_hld_sections', [])) or 'TBD'}",
                "",
            ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Product Manager pack for SpecKit answer preparation.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    sync = sync_dir(workspace)
    sync.mkdir(parents=True, exist_ok=True)
    pack = build_pack(workspace)
    (sync / "speckit_product_manager_pack.json").write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / "speckit_product_manager_pack.md").write_text(render_md(pack), encoding="utf-8")
    print("SpecKit Product Manager pack generated:")
    print(f"- json: {sync / 'speckit_product_manager_pack.json'}")
    print(f"- report: {sync / 'speckit_product_manager_pack.md'}")
    print(f"- status: {pack['status']}")
    print(f"- user stories: {len(pack['user_stories'])}")
    print(f"- open questions: {len(pack['product_open_questions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
