#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


VALID_DECISIONS = {
    "SPLIT_AS_PROPOSED",
    "MODIFY_SPLIT",
    "KEEP_AS_ONE",
    "SPLIT",
}


def parse_pairs(values: list[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"Expected KEY=VALUE, got: {value}")
        key, val = value.split("=", 1)
        key = key.strip()
        val = val.strip()
        if not key or not val:
            raise ValueError(f"Expected non-empty KEY=VALUE, got: {value}")
        result[key] = val
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Safely answer an HLD conversion decision queue.")
    parser.add_argument("queue_json", help="Path to hld_conversion_decision_queue.json")
    parser.add_argument(
        "--answer",
        action="append",
        default=[],
        help="Answer in QUESTION_ID=DECISION format, for example Q-003=KEEP_AS_ONE",
    )
    parser.add_argument(
        "--keep-reason",
        action="append",
        default=[],
        help="Keep reason in QUESTION_ID=REASON format. Required for KEEP_AS_ONE.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    try:
        answers = parse_pairs(args.answer)
        keep_reasons = parse_pairs(args.keep_reason)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    queue_path = Path(args.queue_json)
    data = json.loads(queue_path.read_text(encoding="utf-8"))
    questions = data.get("questions", [])
    if not isinstance(questions, list):
        print("ERROR: queue JSON has no questions list")
        return 2

    seen: set[str] = set()
    errors: list[str] = []

    for question in questions:
        if not isinstance(question, dict):
            continue
        qid = str(question.get("question_id", "")).strip()
        if qid not in answers:
            continue

        decision = answers[qid]
        seen.add(qid)

        if decision not in VALID_DECISIONS:
            errors.append(f"{qid}: unsupported decision {decision!r}")
            continue

        question["human_decision"] = decision

        if decision == "KEEP_AS_ONE":
            reason = keep_reasons.get(qid) or str(question.get("approved_keep_reason", "")).strip()
            if not reason:
                errors.append(f"{qid}: KEEP_AS_ONE requires --keep-reason {qid}=...")
            else:
                question["approved_keep_reason"] = reason

    missing = sorted(set(answers) - seen)
    for qid in missing:
        errors.append(f"{qid}: question_id not found in queue")

    if errors:
        print("Refusing to update conversion queue:")
        for error in errors:
            print(f"- {error}")
        return 2

    if args.dry_run:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0

    queue_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Updated conversion queue: {queue_path}")
    for qid, decision in answers.items():
        print(f"- {qid}: {decision}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
