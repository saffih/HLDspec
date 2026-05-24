#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def sync_dirs(workspace: Path) -> list[Path]:
    return [
        workspace / ".specify" / "sync",
        workspace / "firstrun" / ".specify" / "sync",
    ]


def primary_sync(workspace: Path) -> Path:
    for sync in sync_dirs(workspace):
        if (sync / "hldspec_state.json").exists():
            return sync
    return workspace / ".specify" / "sync"


def question_is_open(question: dict[str, Any]) -> bool:
    return bool(question.get("blocking", True)) and str(question.get("human_decision", "TBD")) == "TBD"


def queue_open_count(queue: dict[str, Any]) -> int:
    return sum(1 for q in as_list(queue.get("questions")) if isinstance(q, dict) and question_is_open(q))


def queue_candidates(workspace: Path, explicit_queue: str = "") -> list[Path]:
    if explicit_queue:
        return [Path(explicit_queue).expanduser().resolve()]

    sync = primary_sync(workspace)
    state = load_json(sync / "hldspec_state.json")
    candidates: list[Path] = []

    for artifact in as_list(state.get("controlling_artifacts")):
        if not isinstance(artifact, str):
            continue
        path = Path(artifact)
        if not path.is_absolute():
            path = workspace / path
        if path.name in KNOWN_QUEUE_NAMES:
            candidates.append(path)

    for base in sync_dirs(workspace):
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


def active_queue(workspace: Path, explicit_queue: str = "") -> Path | None:
    candidates = [p for p in queue_candidates(workspace, explicit_queue) if p.exists()]
    open_queues: list[Path] = []
    for path in candidates:
        queue = load_json(path)
        if queue_open_count(queue) > 0:
            open_queues.append(path)
    if open_queues:
        return open_queues[0]
    if explicit_queue and candidates:
        return candidates[0]
    return None


def queue_kind(queue_path: Path) -> str:
    if queue_path.name == "hld_conversion_decision_queue.json":
        return "hld_conversion_decisions"
    if queue_path.name == "spec_build_plan_decision_queue.json":
        return "spec_build_plan_decisions"
    if queue_path.name == "speckit_question_escalation_queue.json":
        return "speckit_question_escalation"
    return "unknown"


def question_title(q: dict[str, Any]) -> str:
    for key in ("title", "question", "question_id"):
        value = q.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text[:160]
    return "Untitled question"


def compact(value: Any, limit: int = 240) -> str:
    if value in (None, "", [], {}):
        return ""
    if isinstance(value, (list, dict)):
        text = json.dumps(value, ensure_ascii=True, sort_keys=True)
    else:
        text = str(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def evidence_from_question(q: dict[str, Any]) -> list[str]:
    evidence: list[str] = []
    keys = [
        "evidence",
        "reason",
        "why_evidence_is_insufficient",
        "summary",
        "source_excerpt",
        "section_title",
        "candidate_title",
        "source_hld_sections",
        "affected_artifacts",
        "default_proposal",
    ]
    for key in keys:
        value = q.get(key)
        text = compact(value)
        if text:
            evidence.append(f"{key}: {text}")
    return evidence[:8]


def options_for(q: dict[str, Any]) -> list[str]:
    options = [str(x) for x in as_list(q.get("options")) if str(x).strip()]
    if options:
        return options
    return ["ANSWERED", "NEEDS_REWORK", "DEFER"]


def recommended_option(q: dict[str, Any]) -> tuple[str, str, str]:
    for key in ("recommended_option", "recommendation", "suggested_decision"):
        value = q.get(key)
        if isinstance(value, str) and value.strip():
            rec = value.strip()
            return rec, "HIGH", f"Question contains explicit {key}."
    default = q.get("default_proposal")
    if isinstance(default, dict):
        for key in ("recommended_option", "decision", "human_decision"):
            value = default.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip(), "MEDIUM", f"default_proposal contains {key}."
        if isinstance(default.get("proposed_split_plan"), list) and default.get("proposed_split_plan"):
            opts = options_for(q)
            if "SPLIT_AS_PROPOSED" in opts:
                return "SPLIT_AS_PROPOSED", "MEDIUM", "A proposed split plan exists."
    return "", "NONE", "No safe recommendation from explicit evidence."


def meaning_for(kind: str, q: dict[str, Any]) -> str:
    if kind == "hld_conversion_decisions":
        return "Decide how this raw HLD candidate section should be represented before conversion: split as proposed, keep as one section, or defer/rework if unclear."
    if kind == "spec_build_plan_decisions":
        return "Decide whether the generated SpecKit build plan can continue or needs correction before target-spec/prework generation."
    if kind == "speckit_question_escalation":
        owner = q.get("owner_role", "human")
        return f"Resolve a {owner} question before the answer pack or SpecKit proxy may be promoted."
    return "Resolve this checkpoint question before the flow can continue."


def risk_for(kind: str) -> str:
    if kind == "hld_conversion_decisions":
        return "Wrong split/keep decisions can merge unrelated responsibilities or fragment one coherent design, causing bad HLD metadata and downstream specs."
    if kind == "spec_build_plan_decisions":
        return "Wrong plan decisions can send context-only or unsafe features into SpecKit prework."
    if kind == "speckit_question_escalation":
        return "Wrong answers can let the proxy invent product or architecture decisions."
    return "Wrong answers can make downstream artifacts unsafe or misleading."


def answer_command(workspace: Path, queue_path: Path, question_id: str, options: list[str]) -> str:
    option = options[0] if options else "<OPTION>"
    return (
        f"bash scripts/hldspec_interview.sh {workspace} "
        f"--queue {queue_path} "
        f"--answer {question_id}={option}"
    )


def build_guide(workspace: Path, explicit_queue: str = "") -> dict[str, Any]:
    sync = primary_sync(workspace)
    queue_path = active_queue(workspace, explicit_queue)
    state = load_json(sync / "hldspec_state.json")
    if queue_path is None:
        return {
            "schema_version": 1,
            "status": "NO_ACTIVE_QUESTIONS",
            "workspace": str(workspace),
            "current_stage": state.get("current_stage", ""),
            "current_checkpoint": state.get("current_checkpoint", ""),
            "queue_path": "",
            "questions": [],
            "next_action": "No active checkpoint question queue was found.",
        }

    queue = load_json(queue_path)
    kind = queue_kind(queue_path)
    questions: list[dict[str, Any]] = []
    for raw in as_list(queue.get("questions")):
        if not isinstance(raw, dict):
            continue
        qid = str(raw.get("question_id", "")).strip()
        if not qid:
            continue
        opts = options_for(raw)
        rec, confidence, rationale = recommended_option(raw)
        guide = {
            "question_id": qid,
            "title": question_title(raw),
            "checkpoint": kind,
            "meaning": meaning_for(kind, raw),
            "human_decision": raw.get("human_decision", "TBD"),
            "is_open": question_is_open(raw),
            "options": opts,
            "evidence": evidence_from_question(raw),
            "recommended_option": rec,
            "recommendation_confidence": confidence,
            "recommendation_rationale": rationale,
            "risk_if_wrong": risk_for(kind),
            "human_must_choose": question_is_open(raw),
            "answer_command_template": answer_command(workspace, queue_path, qid, opts),
        }
        questions.append(guide)

    open_questions = [q for q in questions if q["is_open"]]
    return {
        "schema_version": 1,
        "status": "HUMAN_GUIDANCE_REQUIRED" if open_questions else "NO_OPEN_QUESTIONS",
        "workspace": str(workspace),
        "current_stage": state.get("current_stage", ""),
        "current_checkpoint": state.get("current_checkpoint", kind),
        "queue_path": str(queue_path),
        "queue_kind": kind,
        "open_question_count": len(open_questions),
        "questions": questions,
        "next_action": "Human chooses answers; hldspec_interview records validated decisions.",
    }


def render_md(guide: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Checkpoint Question Guide",
        "",
        "",
        "",
        f"Status: `{guide.get('status')}`",
        f"Current stage: `{guide.get('current_stage', '')}`",
        f"Current checkpoint: `{guide.get('current_checkpoint', '')}`",
        f"Queue: `{guide.get('queue_path', '')}`",
        f"Open questions: {guide.get('open_question_count', 0)}",
        "",
    ]

    if not guide.get("questions"):
        lines += ["## Questions", "", "- none", ""]
        return "\n".join(lines)

    lines += ["## How to use this guide", ""]
    lines += [
        "- This guide is read-only.",
        "- It explains the checkpoint questions.",
        "- The human chooses answers.",
        "- Use `hldspec_interview.sh` to record answers.",
        "",
    ]

    for q in guide.get("questions", []):
        if not isinstance(q, dict):
            continue
        lines += [
            f"## {q.get('question_id')} - {q.get('title')}",
            "",
            f"- open: `{str(q.get('is_open')).lower()}`",
            f"- meaning: {q.get('meaning')}",
            f"- human decision: `{q.get('human_decision')}`",
            "",
            "### Options",
            "",
        ]
        for option in q.get("options", []):
            lines.append(f"- `{option}`")
        lines += [
            "",
            "### Evidence",
            "",
        ]
        evidence = q.get("evidence", [])
        if evidence:
            for item in evidence:
                lines.append(f"- {item}")
        else:
            lines.append("- no direct evidence field was found in the queue item")
        lines += [
            "",
            "### Recommendation",
            "",
            f"- recommended option: `{q.get('recommended_option') or 'NONE'}`",
            f"- confidence: `{q.get('recommendation_confidence')}`",
            f"- rationale: {q.get('recommendation_rationale')}",
            "",
            "### Risk if wrong",
            "",
            q.get("risk_if_wrong", ""),
            "",
            "### Answer command template",
            "",
            "```bash",
            str(q.get("answer_command_template", "")),
            "```",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only guide for the current HLDspec checkpoint questions.")
    parser.add_argument("workspace")
    parser.add_argument("--queue", default="", help="Optional explicit queue JSON path.")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sync = primary_sync(workspace)
    sync.mkdir(parents=True, exist_ok=True)

    guide = build_guide(workspace, args.queue)
    json_path = sync / "hldspec_question_guide.json"
    md_path = sync / "hldspec_question_guide.md"
    write_json(json_path, guide)
    md_path.write_text(render_md(guide), encoding="utf-8")

    print("HLDspec question guide generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {guide['status']}")
    print(f"- open questions: {guide.get('open_question_count', 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
