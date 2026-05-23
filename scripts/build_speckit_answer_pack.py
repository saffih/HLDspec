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
    if (direct / "speckit_product_manager_pack.json").exists() or (direct / "speckit_architect_pack.json").exists():
        return direct
    if (nested / "speckit_product_manager_pack.json").exists() or (nested / "speckit_architect_pack.json").exists():
        return nested
    return direct


def answered(question: dict[str, Any]) -> bool:
    return str(question.get("human_decision", "TBD")) != "TBD"


def normalize_question(item: dict[str, Any], default_owner: str) -> dict[str, Any]:
    return {
        "question_id": item.get("question_id", ""),
        "owner_role": item.get("owner_role", default_owner),
        "phase": item.get("phase", "clarify"),
        "classification": item.get("classification", "ESCALATE_TO_HUMAN"),
        "question": item.get("question", ""),
        "why_evidence_is_insufficient": item.get("why_evidence_is_insufficient", ""),
        "source_hld_sections": item.get("source_hld_sections", []),
        "affected_artifacts": item.get("affected_artifacts", []),
        "human_decision": item.get("human_decision", "TBD"),
        "human_notes": item.get("human_notes", ""),
    }


def build_pack(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    pm = load_json(sync / "speckit_product_manager_pack.json")
    architect = load_json(sync / "speckit_architect_pack.json")
    dossier = load_json(sync / "speckit_proxy_dossier.json")
    constitution = load_json(sync / "constitution_update_plan.json")

    product_questions = [
        normalize_question(q, "Product Manager")
        for q in as_list(pm.get("product_open_questions"))
        if isinstance(q, dict)
    ]
    architecture_questions = [
        normalize_question(q, "Architect")
        for q in as_list(architect.get("architecture_open_questions"))
        if isinstance(q, dict)
    ]
    escalation_queue = product_questions + architecture_questions
    blocking = [q for q in escalation_queue if not answered(q)]

    user_stories = as_list(pm.get("user_stories"))
    selected = dossier.get("selected_feature", {}) if isinstance(dossier.get("selected_feature"), dict) else {}
    if not selected:
        selected = pm.get("selected_first_feature", {}) if isinstance(pm.get("selected_first_feature"), dict) else {}

    constitution_answers = {
        "phase": "constitution",
        "answer_policy": "ANSWER_FROM_EVIDENCE_OR_ESCALATE",
        "rules": constitution.get("required_rules", []),
        "open_questions": [q for q in architecture_questions if q.get("phase") == "constitution"],
    }
    specify_answers = {
        "phase": "specify",
        "selected_feature": selected,
        "user_stories": user_stories,
        "acceptance_criteria": [
            {"story_id": s.get("story_id"), "criteria": s.get("acceptance_criteria", [])}
            for s in user_stories
            if isinstance(s, dict)
        ],
        "non_goals": pm.get("non_goals", []),
        "open_questions": [q for q in escalation_queue if q.get("phase") == "specify"],
    }
    clarify_policy = {
        "phase": "clarify",
        "rules": [
            {"area": "API contract", "policy": "ESCALATE unless explicit in HLD/architect pack"},
            {"area": "source of truth", "policy": "ESCALATE unless explicit in architect pack"},
            {"area": "UX/user-visible scope", "policy": "ESCALATE unless explicit in product manager pack"},
            {"area": "naming/reversible phrasing", "policy": "ANSWER_FROM_REASONABLE_DEFAULT if low risk"},
            {"area": "security/privacy/data ownership", "policy": "ESCALATE"},
            {"area": "dependency order", "policy": "ANSWER_FROM_EVIDENCE only"},
        ],
        "open_questions": [q for q in escalation_queue if q.get("phase") == "clarify"],
    }

    status = "READY" if not blocking else "BLOCKED_OPEN_QUESTIONS"
    return {
        "schema_version": 1,
        "status": status,
        "workspace": str(workspace),
        "role_inputs": {
            "product_manager_pack": str(sync / "speckit_product_manager_pack.json"),
            "architect_pack": str(sync / "speckit_architect_pack.json"),
        },
        "constitution_answers": constitution_answers,
        "specify_answers": specify_answers,
        "clarify_answer_policy": clarify_policy,
        "question_escalation_queue": escalation_queue,
        "blocking_open_questions": blocking,
        "counts": {
            "user_stories": len(user_stories),
            "product_open_questions": len(product_questions),
            "architecture_open_questions": len(architecture_questions),
            "blocking_open_questions": len(blocking),
        },
    }


def render_questions_md(title: str, questions: list[dict[str, Any]]) -> str:
    lines = [f"# {title}", "", "made by AI", ""]
    if not questions:
        lines.append("No open questions.")
        return "\n".join(lines) + "\n"
    for q in questions:
        lines += [
            f"## {q.get('question_id')} - {q.get('owner_role')}",
            "",
            f"- phase: `{q.get('phase')}`",
            f"- classification: `{q.get('classification')}`",
            f"- question: {q.get('question')}",
            f"- human decision: `{q.get('human_decision')}`",
            f"- affected artifacts: {', '.join(q.get('affected_artifacts', []))}",
            "",
        ]
    return "\n".join(lines) + "\n"


def render_md(pack: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Answer Pack",
        "",
        "made by AI",
        "",
        f"Status: `{pack.get('status')}`",
        "",
        "## Counts",
        "",
    ]
    for key, value in (pack.get("counts") or {}).items():
        lines.append(f"- {key}: {value}")
    lines += [
        "",
        "## Constitution answers",
        "",
        f"- policy: `{pack['constitution_answers']['answer_policy']}`",
        f"- open questions: {len(pack['constitution_answers']['open_questions'])}",
        "",
        "## Specify answers",
        "",
        f"- selected feature: `{pack['specify_answers']['selected_feature'].get('feature_id', '')}` {pack['specify_answers']['selected_feature'].get('feature_name', '')}",
        f"- user stories: {len(pack['specify_answers']['user_stories'])}",
        f"- open questions: {len(pack['specify_answers']['open_questions'])}",
        "",
        "## Clarify answer policy",
        "",
    ]
    for rule in pack["clarify_answer_policy"]["rules"]:
        lines.append(f"- {rule['area']}: {rule['policy']}")
    lines += ["", "## Blocking open questions", ""]
    if not pack.get("blocking_open_questions"):
        lines.append("- none")
    for q in pack.get("blocking_open_questions", []):
        lines.append(f"- `{q.get('question_id')}` {q.get('question')}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SpecKit answer pack from Product Manager and Architect packs.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    sync = sync_dir(workspace)
    sync.mkdir(parents=True, exist_ok=True)
    pack = build_pack(workspace)

    (sync / "speckit_answer_pack.json").write_text(json.dumps(pack, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / "speckit_answer_pack.md").write_text(render_md(pack), encoding="utf-8")
    (sync / "speckit_constitution_answers.md").write_text(render_questions_md("SpecKit Constitution Answers", pack["constitution_answers"]["open_questions"]), encoding="utf-8")
    (sync / "speckit_specify_answers.md").write_text(render_questions_md("SpecKit Specify Answers", pack["specify_answers"]["open_questions"]), encoding="utf-8")
    (sync / "speckit_clarify_answer_policy.md").write_text(render_questions_md("SpecKit Clarify Answer Policy", pack["clarify_answer_policy"]["open_questions"]), encoding="utf-8")
    escalation = {
        "schema_version": 1,
        "status": "HUMAN_QUESTIONS_REQUIRED" if pack["blocking_open_questions"] else "NO_BLOCKING_QUESTIONS",
        "questions": pack["question_escalation_queue"],
    }
    (sync / "speckit_question_escalation_queue.json").write_text(json.dumps(escalation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / "speckit_question_escalation_queue.md").write_text(render_questions_md("SpecKit Question Escalation Queue", pack["question_escalation_queue"]), encoding="utf-8")

    print("SpecKit answer pack generated:")
    print(f"- json: {sync / 'speckit_answer_pack.json'}")
    print(f"- report: {sync / 'speckit_answer_pack.md'}")
    print(f"- status: {pack['status']}")
    print(f"- blocking questions: {len(pack['blocking_open_questions'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
