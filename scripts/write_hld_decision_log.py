#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


MARKER_BEGIN = "<!-- HLDSPEC-DECISION-LOG:BEGIN -->"
MARKER_END = "<!-- HLDSPEC-DECISION-LOG:END -->"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_question(question: dict[str, Any]) -> dict[str, Any]:
    decision = str(question.get("human_decision", "TBD"))
    status = "PENDING" if decision == "TBD" else "ANSWERED"
    return {
        "question_id": question.get("question_id", ""),
        "source_candidate_id": question.get("source_candidate_id", ""),
        "title": question.get("title", ""),
        "question": question.get("question", ""),
        "options": question.get("options", []),
        "human_decision": decision,
        "decision_status": status,
        "human_notes": question.get("human_notes", ""),
        "approved_keep_reason": question.get("approved_keep_reason", ""),
        "approved_split_plan": question.get("approved_split_plan", []),
        "default_proposal": question.get("default_proposal", {}),
    }


def build_log(workspace: Path, source_hld: str = "") -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    queue_path = sync / "hld_conversion_decision_queue.json"
    plan_path = sync / "hld_conversion_plan.json"

    if not queue_path.exists():
        raise FileNotFoundError(f"Missing decision queue: {queue_path}")

    queue = load_json(queue_path)
    questions = [normalize_question(item) for item in queue.get("questions", []) if isinstance(item, dict)]
    answered = [item for item in questions if item["decision_status"] == "ANSWERED"]
    pending = [item for item in questions if item["decision_status"] == "PENDING"]

    return {
        "schema_version": 1,
        "status": "HAS_PENDING_DECISIONS" if pending else "DECISIONS_RECORDED",
        "source_hld": source_hld,
        "workspace": str(workspace),
        "decision_queue": str(queue_path),
        "conversion_plan": str(plan_path) if plan_path.exists() else "",
        "source_of_truth_policy": {
            "current_source_of_truth": "source HLD remains authoritative until an appendix patch is explicitly applied",
            "decision_capture": "hld_decision_log.json records human checkpoint decisions",
            "source_patch": "hld_source_decision_appendix.md is the reviewable append-only patch for the source HLD",
            "apply_rule": "do not modify the source HLD without explicit human approval",
        },
        "decisions": questions,
        "answered_count": len(answered),
        "pending_count": len(pending),
    }


def render_markdown(log: dict[str, Any]) -> str:
    lines: list[str] = [
        "# HLDspec Decision Log",
        "",
        "made by AI",
        "",
        f"Status: `{log['status']}`",
        f"Source HLD: `{log.get('source_hld') or ''}`",
        f"Workspace: `{log.get('workspace')}`",
        f"Answered decisions: {log.get('answered_count', 0)}",
        f"Pending decisions: {log.get('pending_count', 0)}",
        "",
        "## Source-of-truth policy",
        "",
    ]

    policy = log.get("source_of_truth_policy", {})
    if isinstance(policy, dict):
        for key, value in policy.items():
            lines.append(f"- {key}: {value}")
    lines.append("")

    lines.append("## Decisions")
    lines.append("")
    for item in log.get("decisions", []):
        if not isinstance(item, dict):
            continue
        lines += [
            f"### {item.get('question_id')} - {item.get('source_candidate_id')} {item.get('title')}",
            "",
            f"- status: `{item.get('decision_status')}`",
            f"- decision: `{item.get('human_decision')}`",
            f"- question: {item.get('question')}",
            f"- notes: {item.get('human_notes') or ''}",
        ]
        if item.get("approved_keep_reason"):
            lines.append(f"- keep reason: {item.get('approved_keep_reason')}")
        split_plan = item.get("approved_split_plan") or []
        if split_plan:
            lines.append("- approved split plan:")
            for split in split_plan:
                if isinstance(split, dict):
                    sid = split.get("proposed_hld_id") or split.get("id") or ""
                    title = split.get("title") or ""
                    start = split.get("source_line_start") or split.get("start") or ""
                    end = split.get("source_line_end") or split.get("end") or ""
                    lines.append(f"  - {sid} - {title} (lines {start}-{end})")
        lines.append("")

    return "\n".join(lines)


def render_source_appendix(log: dict[str, Any]) -> str:
    lines: list[str] = [
        MARKER_BEGIN,
        "",
        "## HLDspec Decision Log",
        "",
        "This section records human decisions made during HLDspec processing so they are not lost outside the generated workspace.",
        "",
        f"- HLDspec workspace: `{log.get('workspace')}`",
        f"- Decision log artifact: `{Path('.hldspec-first-run/.specify/sync/hld_decision_log.md')}`",
        f"- Status: `{log.get('status')}`",
        "",
        "### Decisions",
        "",
    ]

    for item in log.get("decisions", []):
        if not isinstance(item, dict):
            continue
        lines += [
            f"#### {item.get('question_id')} - {item.get('source_candidate_id')} {item.get('title')}",
            "",
            f"- Status: `{item.get('decision_status')}`",
            f"- Decision: `{item.get('human_decision')}`",
            f"- Question: {item.get('question')}",
        ]
        if item.get("human_notes"):
            lines.append(f"- Notes: {item.get('human_notes')}")
        if item.get("approved_keep_reason"):
            lines.append(f"- Keep reason: {item.get('approved_keep_reason')}")
        split_plan = item.get("approved_split_plan") or []
        if split_plan:
            lines.append("- Approved split plan:")
            for split in split_plan:
                if isinstance(split, dict):
                    sid = split.get("proposed_hld_id") or split.get("id") or ""
                    title = split.get("title") or ""
                    start = split.get("source_line_start") or split.get("start") or ""
                    end = split.get("source_line_end") or split.get("end") or ""
                    lines.append(f"  - {sid} - {title} (lines {start}-{end})")
        lines.append("")

    lines += [
        MARKER_END,
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write durable HLDspec human decision log artifacts.")
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)

    try:
        log = build_log(workspace, args.source_hld)
    except FileNotFoundError as exc:
        print(f"No HLDspec decision log written: {exc}")
        return 0

    json_path = sync / "hld_decision_log.json"
    md_path = sync / "hld_decision_log.md"
    appendix_path = sync / "hld_source_decision_appendix.md"

    json_path.write_text(json.dumps(log, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(log), encoding="utf-8")
    appendix_path.write_text(render_source_appendix(log), encoding="utf-8")

    print("HLD decision log written:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- source appendix patch: {appendix_path}")
    print(f"- status: {log['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
