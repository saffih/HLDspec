#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SOURCE_DECISIONS = {"SPLIT_AS_PROPOSED", "MODIFY_SPLIT", "SPLIT", "KEEP_AS_ONE"}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_decisions(workspace: Path) -> list[dict[str, Any]]:
    sync = workspace / ".specify" / "sync"
    log_path = sync / "hld_decision_log.json"
    queue_path = sync / "hld_conversion_decision_queue.json"

    if log_path.exists():
        log = load_json(log_path)
        decisions = log.get("decisions", [])
        return [item for item in decisions if isinstance(item, dict)]

    if queue_path.exists():
        queue = load_json(queue_path)
        questions = queue.get("questions", [])
        return [item for item in questions if isinstance(item, dict)]

    return []


def classify_update(item: dict[str, Any]) -> dict[str, Any] | None:
    decision = str(item.get("human_decision", "TBD"))
    if decision == "TBD":
        return None

    notes = str(item.get("human_notes", "")).strip()
    source_candidate_id = str(item.get("source_candidate_id", "")).strip()
    title = str(item.get("title", "")).strip()
    question = str(item.get("question", "")).strip()
    approved_keep_reason = str(item.get("approved_keep_reason", "")).strip()
    approved_split_plan = item.get("approved_split_plan") or []

    if decision not in SOURCE_DECISIONS and not notes:
        return None

    impact = "MAY_AFFECT_SOURCE_HLD" if decision in SOURCE_DECISIONS else "UNKNOWN_REVIEW_REQUIRED"
    reason = (
        "Human checkpoint answer changes/confirms HLD section boundaries or meaning."
        if decision in SOURCE_DECISIONS
        else "Human notes may affect the source HLD and require review."
    )

    proposed_lines = [
        f"Question: {question}",
        f"Decision: {decision}",
    ]
    if notes:
        proposed_lines.append(f"Human notes: {notes}")
    if approved_keep_reason:
        proposed_lines.append(f"Keep reason: {approved_keep_reason}")
    if isinstance(approved_split_plan, list) and approved_split_plan:
        proposed_lines.append("Approved split plan:")
        for split in approved_split_plan:
            if isinstance(split, dict):
                sid = split.get("proposed_hld_id") or split.get("id") or ""
                stitle = split.get("title") or ""
                start = split.get("source_line_start") or split.get("start") or ""
                end = split.get("source_line_end") or split.get("end") or ""
                proposed_lines.append(f"- {sid} - {stitle} (source lines {start}-{end})")

    return {
        "question_id": item.get("question_id", ""),
        "source_candidate_id": source_candidate_id,
        "title": title,
        "source_hld_impact": impact,
        "impact_reason": reason,
        "human_decision": decision,
        "human_notes": notes,
        "proposed_source_update": "\n".join(proposed_lines),
        "apply_to_source_hld": "PENDING_HUMAN_APPROVAL",
    }


def build_queue(workspace: Path, source_hld: str = "") -> dict[str, Any]:
    decisions = load_decisions(workspace)
    updates = []
    for item in decisions:
        update = classify_update(item)
        if update:
            updates.append(update)

    return {
        "schema_version": 1,
        "status": "SOURCE_HLD_REVIEW_REQUIRED" if updates else "NO_SOURCE_HLD_UPDATE_REQUIRED",
        "source_hld": source_hld,
        "workspace": str(workspace),
        "source_of_truth_rule": "These updates may affect source HLD content or structure. Do not apply automatically.",
        "updates": updates,
    }


def render_md(queue: dict[str, Any]) -> str:
    lines = [
        "# HLD Source Update Queue",
        "",
        "",
        "",
        f"Status: `{queue['status']}`",
        f"Source HLD: `{queue.get('source_hld', '')}`",
        "",
        "Some checkpoint feedback may affect the source HLD, not only HLDspec process state.",
        "",
        "The judge/orchestrator must review these items and ask for explicit approval before modifying the source HLD.",
        "",
    ]

    updates = queue.get("updates", [])
    if not updates:
        lines += ["No source-HLD-affecting updates were detected.", ""]
        return "\n".join(lines)

    lines += ["## Proposed source-HLD updates", ""]
    for update in updates:
        lines += [
            f"### {update.get('question_id')} - {update.get('source_candidate_id')} {update.get('title')}",
            "",
            f"- impact: `{update.get('source_hld_impact')}`",
            f"- decision: `{update.get('human_decision')}`",
            f"- approval: `{update.get('apply_to_source_hld')}`",
            f"- reason: {update.get('impact_reason')}",
            "",
            "Proposed source update:",
            "",
            "```text",
            str(update.get("proposed_source_update", "")),
            "```",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a queue of checkpoint feedback that may affect the source HLD.")
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)

    queue = build_queue(workspace, args.source_hld)
    json_path = sync / "hld_source_update_queue.json"
    md_path = sync / "hld_source_update_queue.md"

    json_path.write_text(json.dumps(queue, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(queue), encoding="utf-8")

    print("HLD source update queue written:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {queue['status']}")
    print(f"- source-HLD-affecting updates: {len(queue['updates'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
