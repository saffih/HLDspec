#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


KNOWN_QUEUE_NAMES = (
    "hld_conversion_decision_queue.json",
    "spec_build_plan_decision_queue.json",
    "speckit_question_escalation_queue.json",
)


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object JSON in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def question_is_open(question: dict[str, Any]) -> bool:
    return bool(question.get("blocking", True)) and str(question.get("human_decision", "TBD")) == "TBD"


def open_question_count(queue: dict[str, Any]) -> int:
    return sum(1 for q in as_list(queue.get("questions")) if isinstance(q, dict) and question_is_open(q))


def parse_key_value(value: str, *, arg_name: str) -> tuple[str, str]:
    if "=" not in value:
        raise SystemExit(f"{arg_name} must use QUESTION_ID=value, got: {value}")
    key, val = value.split("=", 1)
    key = key.strip()
    val = val.strip()
    if not key or not val:
        raise SystemExit(f"{arg_name} must use non-empty QUESTION_ID=value, got: {value}")
    return key, val


def queue_candidates(workspace: Path) -> list[Path]:
    sync = workspace / ".specify" / "sync"
    firstrun_sync = workspace / "firstrun" / ".specify" / "sync"
    candidates: list[Path] = []

    state_path = sync / "hldspec_state.json"
    if state_path.exists():
        state = load_json(state_path)
        for artifact in as_list(state.get("controlling_artifacts")):
            if not isinstance(artifact, str):
                continue
            path = Path(artifact)
            if not path.is_absolute():
                path = workspace / path
            if path.name in KNOWN_QUEUE_NAMES and path.exists():
                candidates.append(path)

    for base in (sync, firstrun_sync):
        for name in KNOWN_QUEUE_NAMES:
            path = base / name
            if path.exists():
                candidates.append(path)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        resolved = path.resolve()
        if resolved not in seen:
            deduped.append(path)
            seen.add(resolved)
    return deduped


def discover_queue(workspace: Path) -> Path:
    candidates = queue_candidates(workspace)
    open_candidates: list[Path] = []
    for path in candidates:
        data = load_json(path)
        if open_question_count(data) > 0:
            open_candidates.append(path)
    if len(open_candidates) == 1:
        return open_candidates[0]
    if len(open_candidates) > 1:
        rendered = "\n".join(f"- {p}" for p in open_candidates)
        raise SystemExit("Multiple open queues found; pass --queue explicitly:\n" + rendered)
    if len(candidates) == 1:
        return candidates[0]
    if candidates:
        rendered = "\n".join(f"- {p}" for p in candidates)
        raise SystemExit("No open queue found; pass --queue explicitly if updating a closed queue:\n" + rendered)
    raise SystemExit(f"No HLDspec decision queue found under {workspace}")


def question_lookup(queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in as_list(queue.get("questions")):
        if isinstance(item, dict) and item.get("question_id"):
            result[str(item["question_id"])] = item
    return result


def apply_answers_to_queue(
    queue: dict[str, Any],
    answers: dict[str, str],
    notes: dict[str, str] | None = None,
) -> dict[str, Any]:
    notes = notes or {}
    by_id = question_lookup(queue)
    changed: list[str] = []

    for qid, answer in answers.items():
        if qid not in by_id:
            raise ValueError(f"Unknown question id: {qid}")
        question = by_id[qid]
        options = [str(item) for item in as_list(question.get("options"))]
        if options and answer not in options:
            raise ValueError(f"Invalid answer for {qid}: {answer}. Allowed: {', '.join(options)}")
        question["human_decision"] = answer
        question["decision_status"] = "ANSWERED"
        if qid in notes:
            question["human_notes"] = notes[qid]
        elif "human_notes" not in question:
            question["human_notes"] = ""

        if answer == "SPLIT_AS_PROPOSED":
            default = question.get("default_proposal", {})
            if isinstance(default, dict) and isinstance(default.get("proposed_split_plan"), list):
                question["approved_split_plan"] = default["proposed_split_plan"]
        if answer == "KEEP_AS_ONE" and not question.get("approved_keep_reason"):
            question["approved_keep_reason"] = question.get("human_notes", "") or "Human chose KEEP_AS_ONE at checkpoint."
        changed.append(qid)

    remaining = open_question_count(queue)
    checkpoint = queue.get("checkpoint")
    if isinstance(checkpoint, dict):
        checkpoint["open_question_count"] = remaining
        if "allowed_to_convert" in checkpoint:
            checkpoint["allowed_to_convert"] = remaining == 0
        if "allowed_to_generate_target_specs" in checkpoint:
            checkpoint["allowed_to_generate_target_specs"] = remaining == 0

    if remaining == 0 and changed:
        queue["status"] = "DECISIONS_RECORDED"
    elif remaining > 0:
        queue["status"] = "HUMAN_CHECKPOINT_REQUIRED"

    queue["last_answered_questions"] = changed
    return queue


def render_queue_md(queue: dict[str, Any], path: Path) -> str:
    title = "HLDspec Decision Queue"
    if path.name == "hld_conversion_decision_queue.json":
        title = "HLD Conversion Decision Queue"
    elif path.name == "spec_build_plan_decision_queue.json":
        title = "Spec Build Plan Decision Queue"
    elif path.name == "speckit_question_escalation_queue.json":
        title = "SpecKit Question Escalation Queue"

    checkpoint = queue.get("checkpoint", {}) if isinstance(queue.get("checkpoint"), dict) else {}
    lines = [
        f"# {title}",
        "",
        "made by AI",
        "",
        f"Status: `{queue.get('status', '')}`",
        f"Checkpoint: `{checkpoint.get('checkpoint_id', '')}`",
        f"Open questions: {checkpoint.get('open_question_count', open_question_count(queue))}",
        "",
        "## Questions",
        "",
    ]
    questions = [q for q in as_list(queue.get("questions")) if isinstance(q, dict)]
    if not questions:
        lines.append("No questions.")
    for q in questions:
        lines.extend(
            [
                f"### {q.get('question_id', '')} - {q.get('title', '')}",
                "",
                f"- question: {q.get('question', '')}",
                f"- options: {', '.join(str(x) for x in as_list(q.get('options'))) or 'none'}",
                f"- human decision: `{q.get('human_decision', 'TBD')}`",
                f"- notes: {q.get('human_notes', '')}",
                "",
            ]
        )
    return "\n".join(lines)


def queue_md_path(queue_path: Path) -> Path:
    return queue_path.with_suffix(".md")


def maybe_run_supporting_writers(queue_path: Path, workspace: Path, source_hld: str) -> None:
    root = Path(__file__).resolve().parents[1]
    if queue_path.name != "hld_conversion_decision_queue.json":
        return
    for script in ("write_hld_decision_log.py", "write_hld_source_update_queue.py"):
        path = root / "scripts" / script
        if path.exists():
            subprocess.run(
                [sys.executable, str(path), str(workspace), "--source-hld", source_hld],
                check=True,
            )


def build_result(queue_path: Path, queue: dict[str, Any]) -> dict[str, Any]:
    return {
        "queue_path": str(queue_path),
        "status": queue.get("status", ""),
        "open_question_count": open_question_count(queue),
        "last_answered_questions": queue.get("last_answered_questions", []),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply human answers to an HLDspec decision queue.")
    parser.add_argument("workspace")
    parser.add_argument("--queue", default="", help="Explicit queue JSON path. If omitted, discovers the active queue.")
    parser.add_argument("--answer", action="append", default=[], help="QUESTION_ID=OPTION. Can be repeated.")
    parser.add_argument("--note", action="append", default=[], help="QUESTION_ID=note text. Can be repeated.")
    parser.add_argument("--source-hld", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    queue_path = Path(args.queue).resolve() if args.queue else discover_queue(workspace).resolve()
    if not queue_path.exists():
        raise SystemExit(f"Missing queue: {queue_path}")

    answers = dict(parse_key_value(item, arg_name="--answer") for item in args.answer)
    notes = dict(parse_key_value(item, arg_name="--note") for item in args.note)
    if not answers:
        raise SystemExit("At least one --answer QUESTION_ID=OPTION is required")

    queue = load_json(queue_path)
    try:
        updated = apply_answers_to_queue(queue, answers, notes)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    write_json(queue_path, updated)
    queue_md_path(queue_path).write_text(render_queue_md(updated, queue_path), encoding="utf-8")
    maybe_run_supporting_writers(queue_path, workspace, args.source_hld)

    result = build_result(queue_path, updated)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
