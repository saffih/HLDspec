#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


OPEN_DECISION_STATUSES = {
    "STOP_SPLIT_DECISION_REQUIRED",
    "PROCEED_SINGLE_SECTION_REVIEW",
}


def decision_options_for(candidate: dict[str, Any]) -> list[str]:
    action = str(candidate.get("recommended_action", ""))
    if action == "STOP_SPLIT_DECISION_REQUIRED":
        return ["SPLIT_AS_PROPOSED", "MODIFY_SPLIT", "KEEP_AS_ONE"]
    if action == "PROCEED_SINGLE_SECTION_REVIEW":
        return ["KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"]
    return ["ACCEPT"]


def question_for(candidate: dict[str, Any]) -> str:
    action = str(candidate.get("recommended_action", ""))
    candidate_id = str(candidate.get("proposed_hld_id", "UNKNOWN"))
    title = str(candidate.get("title", "")).strip()
    if action == "STOP_SPLIT_DECISION_REQUIRED":
        return (
            f"Should {candidate_id} - {title} be split using the proposed split plan, "
            "modified, or kept as one section?"
        )
    if action == "PROCEED_SINGLE_SECTION_REVIEW":
        return (
            f"Should {candidate_id} - {title} be kept as one large section, "
            "or should a split be defined manually?"
        )
    return f"Should {candidate_id} - {title} be accepted as proposed?"


def build_queue(plan: dict[str, Any], *, plan_path: str) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []

    for candidate in plan.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        action = str(candidate.get("recommended_action", ""))
        if action not in OPEN_DECISION_STATUSES:
            continue

        candidate_id = str(candidate.get("proposed_hld_id", "UNKNOWN"))
        split_plan = candidate.get("proposed_split_plan", [])
        if not isinstance(split_plan, list):
            split_plan = []

        question = {
            "question_id": f"Q-{len(questions) + 1:03d}",
            "source_candidate_id": candidate_id,
            "title": str(candidate.get("title", "")).strip(),
            "source_line_start": candidate.get("source_line_start"),
            "source_line_end": candidate.get("source_line_end"),
            "source_line_count": candidate.get("source_line_count"),
            "recommended_action": action,
            "question": question_for(candidate),
            "options": decision_options_for(candidate),
            "human_decision": "TBD",
            "human_notes": "",
            "default_proposal": {
                "decision": "SPLIT_AS_PROPOSED" if action == "STOP_SPLIT_DECISION_REQUIRED" else "KEEP_AS_ONE",
                "reason": candidate.get("reason", ""),
                "proposed_split_plan": split_plan,
            },
            "blocking": True,
        }
        questions.append(question)

    status = "HUMAN_CHECKPOINT_REQUIRED" if questions else "NO_HUMAN_DECISIONS_REQUIRED"

    return {
        "status": status,
        "plan_path": plan_path,
        "checkpoint": {
            "checkpoint_id": "HLD_CONVERSION_DECISIONS",
            "purpose": "Resolve split/keep decisions before metadata-only conversion.",
            "manager_role": "judge/orchestrator",
            "human_role": "owner of unresolved architecture/process decisions",
            "allowed_to_convert": not questions,
            "open_question_count": len(questions),
        },
        "questions": questions,
        "instructions": [
            "The judge/orchestrator must not decide these questions silently.",
            "The judge/orchestrator may continue read-only inspection and may accumulate questions.",
            "Conversion must not run while any blocking question has human_decision=TBD.",
            "When enough questions are accumulated, stop at this checkpoint and ask the human to answer the queue.",
            "After answers are recorded, rerun validation before applying metadata-only conversion.",
        ],
    }


def render_md(queue: dict[str, Any]) -> str:
    lines = [
        "# HLD Conversion Decision Queue",
        "",
        "",
        "",
        f"Status: `{queue['status']}`",
        f"Checkpoint: `{queue['checkpoint']['checkpoint_id']}`",
        f"Open questions: {queue['checkpoint']['open_question_count']}",
        f"Allowed to convert: `{str(queue['checkpoint']['allowed_to_convert']).lower()}`",
        "",
        "## Manager instruction",
        "",
        "The judge/orchestrator owns this checkpoint.",
        "",
        "The judge/orchestrator may continue read-only inspection and may accumulate questions, but must not silently decide split/keep questions.",
        "",
        "Conversion is blocked while any blocking question has `human_decision: TBD`.",
        "",
        "## Questions",
        "",
    ]

    questions = queue.get("questions", [])
    if not questions:
        lines.append("No human conversion decisions are required.")
        lines.append("")
        return "\n".join(lines)

    for question in questions:
        lines += [
            f"### {question['question_id']} - {question['source_candidate_id']} {question['title']}",
            "",
            f"- lines: {question['source_line_start']}-{question['source_line_end']}",
            f"- line count: {question['source_line_count']}",
            f"- recommended action: `{question['recommended_action']}`",
            f"- question: {question['question']}",
            f"- options: {', '.join(question['options'])}",
            "- human decision: `TBD`",
            "",
        ]

        proposal = question.get("default_proposal", {})
        split_plan = proposal.get("proposed_split_plan", []) if isinstance(proposal, dict) else []
        if split_plan:
            lines += ["Default proposed split:"]
            for split in split_plan:
                lines.append(
                    f"- {split['proposed_hld_id']} - {split['title']} "
                    f"(lines {split['source_line_start']}-{split['source_line_end']})"
                )
            lines.append("")
        elif isinstance(proposal, dict):
            lines += [
                f"Default proposal: `{proposal.get('decision', 'TBD')}`",
                f"Reason: {proposal.get('reason', '')}",
                "",
            ]

    lines += [
        "## How to answer",
        "",
        "The human only answers the listed questions.",
        "",
        "The judge/orchestrator must edit the matching JSON file and replace `human_decision: TBD` with one of the listed options.",
        "",
        "Do not use free-text answers as the only record. Human notes may be added in `human_notes`.",
        "",
        "## After the human answers",
        "",
        "The judge/orchestrator must rerun the same HLDspec command and continue to the next safe checkpoint.",
        "",
        "The human should not need to provide the continuation command again.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a human decision queue from an HLD conversion plan.")
    parser.add_argument("conversion_plan_json")
    parser.add_argument("workspace")
    args = parser.parse_args()

    plan_path = Path(args.conversion_plan_json)
    workspace = Path(args.workspace)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    queue = build_queue(plan, plan_path=str(plan_path))
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "hld_conversion_decision_queue.json"
    md_path = out_dir / "hld_conversion_decision_queue.md"
    json_path.write_text(json.dumps(queue, indent=2, sort_keys=True), encoding="utf-8")
    md_path.write_text(render_md(queue), encoding="utf-8")

    print("HLD conversion decision queue generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {queue['status']}")
    print(f"- open questions: {queue['checkpoint']['open_question_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
