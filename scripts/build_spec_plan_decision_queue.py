#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BLOCKING_DECISIONS = {"DECOMPOSE", "CONFLICT"}
BLOCKING_RECOMMENDATIONS = {"SPLIT_PLANNED_SPEC", "RESOLVE_CONFLICT", "REVIEW_PLAN"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def spec_title(spec: dict[str, Any]) -> str:
    return str(spec.get("title") or spec.get("name") or spec.get("planned_spec_id") or "Untitled planned spec")


def build_spec_question(spec: dict[str, Any], idx: int) -> dict[str, Any]:
    spec_id = str(spec.get("planned_spec_id", f"spec-{idx:03d}"))
    flags = [str(flag) for flag in spec.get("quality_flags", [])]
    boundary_risk = str(spec.get("boundary_risk", "unknown"))
    source_ids = [str(item) for item in spec.get("source_hld_sections", [])]
    responsibilities = [str(item) for item in spec.get("responsibility_mix", [])]
    role_mix = [str(item) for item in spec.get("role_mix", [])]

    default = "SPLIT_PLANNED_SPEC" if boundary_risk == "high" else "REVIEW_OR_MODIFY_MAPPING"

    return {
        "question_id": f"SPQ-{idx:03d}",
        "planned_spec_id": spec_id,
        "title": spec_title(spec),
        "source_hld_sections": source_ids,
        "quality_flags": flags,
        "boundary_risk": boundary_risk,
        "responsibility_mix": responsibilities,
        "role_mix": role_mix,
        "blocking": True,
        "human_decision": "TBD",
        "human_notes": "",
        "default_recommendation": default,
        "question": (
            f"How should planned spec {spec_id} - {spec_title(spec)} be resolved before target-spec generation?"
        ),
        "options": [
            "SPLIT_PLANNED_SPEC",
            "MODIFY_HLD_SPECS_MAPPING",
            "KEEP_AS_ONE_WITH_REASON",
            "DEFER",
        ],
        "approved_resolution": {},
    }


def build_plan_level_question(plan_quality: dict[str, Any], idx: int) -> dict[str, Any]:
    decision = str(plan_quality.get("decision", "UNKNOWN"))
    recommendation = str(plan_quality.get("recommendation", "UNKNOWN"))
    findings = [str(item) for item in plan_quality.get("findings", [])]
    conflicts = [str(item) for item in plan_quality.get("conflicts", [])]

    return {
        "question_id": f"SPQ-{idx:03d}",
        "planned_spec_id": "__PLAN_QUALITY__",
        "title": "Plan Quality Gate",
        "source_hld_sections": [],
        "quality_flags": findings,
        "conflicts": conflicts,
        "boundary_risk": "high" if decision in BLOCKING_DECISIONS else "medium",
        "blocking": True,
        "human_decision": "TBD",
        "human_notes": "",
        "default_recommendation": recommendation,
        "question": (
            f"Plan quality is {decision} / {recommendation}. What should the judge/orchestrator do before target-spec generation?"
        ),
        "options": [
            "RESOLVE_CONFLICT",
            "SPLIT_PLANNED_SPEC",
            "MODIFY_HLD_SPECS_MAPPING",
            "KEEP_PLAN_WITH_REASON",
            "DEFER",
        ],
        "approved_resolution": {},
    }


def build_queue(plan: dict[str, Any], plan_path: Path) -> dict[str, Any]:
    plan_quality = plan.get("plan_quality", {})
    if not isinstance(plan_quality, dict):
        plan_quality = {}

    planned_specs = plan.get("planned_specs", [])
    if not isinstance(planned_specs, list):
        planned_specs = []

    questions: list[dict[str, Any]] = []
    for spec in planned_specs:
        if not isinstance(spec, dict):
            continue
        flags = spec.get("quality_flags", [])
        requires_review = bool(spec.get("requires_user_review"))
        boundary_risk = str(spec.get("boundary_risk", ""))
        if requires_review or flags or boundary_risk == "high":
            questions.append(build_spec_question(spec, len(questions) + 1))

    decision = str(plan_quality.get("decision", ""))
    recommendation = str(plan_quality.get("recommendation", ""))
    conflicts = plan_quality.get("conflicts", [])
    if not questions and (
        decision in BLOCKING_DECISIONS
        or recommendation in BLOCKING_RECOMMENDATIONS
        or bool(conflicts)
    ):
        questions.append(build_plan_level_question(plan_quality, len(questions) + 1))

    return {
        "schema_version": 1,
        "status": "HUMAN_CHECKPOINT_REQUIRED" if questions else "NO_SPEC_PLAN_DECISIONS_REQUIRED",
        "checkpoint": {
            "checkpoint_id": "SPEC_BUILD_PLAN_DECISIONS",
            "open_question_count": len(questions),
            "allowed_to_generate_target_specs": not bool(questions),
        },
        "plan_path": str(plan_path),
        "plan_quality": {
            "decision": decision,
            "recommendation": recommendation,
            "conflict_count": len(conflicts) if isinstance(conflicts, list) else 0,
            "finding_count": len(plan_quality.get("findings", [])) if isinstance(plan_quality.get("findings", []), list) else 0,
        },
        "questions": questions,
        "manager_instruction": (
            "The judge/orchestrator may provide evidence and a recommendation, but must not answer spec-plan checkpoint questions. "
            "The human answers the listed options; the judge updates this JSON and reruns the same HLDspec command."
        ),
    }


def render_md(queue: dict[str, Any]) -> str:
    lines = [
        "# Spec Build Plan Decision Queue",
        "",
        "",
        "",
        f"Status: `{queue['status']}`",
        "Checkpoint: `SPEC_BUILD_PLAN_DECISIONS`",
        f"Open questions: {queue['checkpoint']['open_question_count']}",
        f"Allowed to generate target specs: `{str(queue['checkpoint']['allowed_to_generate_target_specs']).lower()}`",
        "",
        "## Manager instruction",
        "",
        queue["manager_instruction"],
        "",
        "Do not create target specs while any blocking question has `human_decision: TBD`.",
        "",
        "## Questions",
        "",
    ]

    questions = queue.get("questions", [])
    if not questions:
        lines += ["No spec-plan checkpoint questions were generated.", ""]
    for question in questions:
        lines += [
            f"### {question.get('question_id')} - {question.get('planned_spec_id')} {question.get('title')}",
            "",
            f"- boundary risk: `{question.get('boundary_risk')}`",
            f"- quality flags: {', '.join(question.get('quality_flags', [])) or 'none'}",
            f"- source HLD sections: {', '.join(question.get('source_hld_sections', [])) or 'none'}",
            f"- default recommendation: `{question.get('default_recommendation')}`",
            f"- question: {question.get('question')}",
            f"- options: {', '.join(question.get('options', []))}",
            f"- human decision: `{question.get('human_decision')}`",
            "",
        ]

    lines += [
        "## After the human answers",
        "",
        "The judge/orchestrator must:",
        "",
        "1. update `spec_build_plan_decision_queue.json` with the human answers",
        "2. apply the approved mapping/split decision to the working HLD or plan inputs",
        "3. rerun the same HLDspec command",
        "4. continue only to the next safe checkpoint",
        "",
        "The human should not need to provide the continuation command again.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build human decision queue for blocked Spec Build Plan reviews.")
    parser.add_argument("spec_build_plan_json")
    parser.add_argument("workspace", nargs="?")
    args = parser.parse_args()

    plan_path = Path(args.spec_build_plan_json)
    workspace = Path(args.workspace) if args.workspace else plan_path.parents[2]
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = load_json(plan_path)
    queue = build_queue(plan, plan_path)

    json_path = out_dir / "spec_build_plan_decision_queue.json"
    md_path = out_dir / "spec_build_plan_decision_queue.md"
    json_path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(queue), encoding="utf-8")

    print("Spec Build Plan decision queue generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {queue['status']}")
    print(f"- open questions: {queue['checkpoint']['open_question_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
