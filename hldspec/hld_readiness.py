from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import hld_map


REASON_KIND_VALUES = (
    "explicit_hld",
    "inferred_from_context",
    "human_choice",
    "temporary_poc_choice",
    "external_constraint",
)

ITEM_STATUS_VALUES = ("baked", "provisional", "unresolved", "superseded")

POLITE_CLARIFICATION_PROMPT = (
    "I found a few questions that may affect whether this HLD is SDD-ready. "
    "Some can be resolved from the HLD, some may need external information, "
    "and going forward with the current assumptions is also an option if you "
    "accept the risk."
)


def _compact(text: str, limit: int = 220) -> str:
    value = " ".join(text.split())
    if len(value) <= limit:
        return value
    return value[: limit - 3].rstrip() + "..."


def _item_type(section: hld_map.HldSection) -> str:
    role = section.metadata_value("HLD-ROLE", "").strip().lower()
    if role in {"api", "ui", "data", "processing", "architecture", "operations", "testing", "risk", "governance"}:
        return role
    title = section.title.lower()
    if "non-goal" in title or "out of scope" in section.text.lower():
        return "non_goal"
    if "requirement" in title:
        return "requirement"
    if "constraint" in title:
        return "constraint"
    return "feature_candidate"


def _reason(section: hld_map.HldSection) -> tuple[str, str, str]:
    desc = section.metadata_value("HLD-DESC", "").strip()
    verify = section.metadata_value("HLD-VERIFY", "").strip()
    lower = section.text.lower()
    if desc:
        kind = "temporary_poc_choice" if any(term in lower for term in ("poc", "temporary", "prototype")) else "explicit_hld"
        return desc, kind, "high"
    if verify and verify.upper() != "TBD":
        return f"Verification evidence is declared: {verify}", "explicit_hld", "medium"
    body = "\n".join(line for line in section.text.splitlines() if not line.startswith("HLD-")).strip()
    if body:
        return _compact(body), "inferred_from_context", "medium"
    return "No reason is explicit in the HLD.", "human_choice", "low"


def _status(section: hld_map.HldSection, reason_kind: str, confidence: str) -> str:
    text = section.text.lower()
    risk = section.metadata_value("HLD-RISK", "").strip().upper()
    verify = section.metadata_value("HLD-VERIFY", "").strip().upper()
    has_tbd = any(section.metadata_value(key, "").strip().upper() == "TBD" for key in ("HLD-SPECS", "HLD-RESOURCES", "HLD-OWNER"))
    if reason_kind == "human_choice" or confidence == "low":
        return "unresolved"
    if risk == "HIGH" and (verify in {"", "TBD"} or has_tbd):
        return "unresolved"
    if reason_kind == "temporary_poc_choice" or has_tbd or any(term in text for term in ("assumption", "assume", "poc", "temporary", "prototype")):
        return "provisional"
    return "baked"


def _group_questions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for item in items:
        status = str(item["status"])
        if status == "baked":
            continue
        if status == "unresolved":
            group_id = "missing_or_conflicting_reason"
            question = "Which unresolved HLD points need clarification, external evidence, or accepted-risk continuation?"
        else:
            group_id = "provisional_poc_or_assumption"
            question = "Which provisional POC assumptions should remain for now, and which must be changed before SDD readiness?"
        group = groups.setdefault(
            group_id,
            {
                "question_id": f"HLDRQ-{len(groups) + 1:03d}",
                "group_id": group_id,
                "question": question,
                "affected_item_ids": [],
                "options": ["PROVIDE_CLARIFICATION", "PROVIDE_EXTERNAL_INFO", "ACCEPT_CURRENT_ASSUMPTIONS"],
                "human_decision": "TBD",
            },
        )
        group["affected_item_ids"].append(item["item_id"])
    return list(groups.values())


def build_hld_cross_examination(hld_path: Path) -> dict[str, Any]:
    parsed = hld_map.parse_hld_file(hld_path)
    items: list[dict[str, Any]] = []
    for idx, section in enumerate(parsed.sections, start=1):
        reason, reason_kind, confidence = _reason(section)
        status = _status(section, reason_kind, confidence)
        items.append(
            {
                "item_id": f"HLDEX-{idx:03d}",
                "hld_id": section.id,
                "item_type": _item_type(section),
                "statement": section.title,
                "reason": reason,
                "reason_kind": reason_kind,
                "confidence": confidence,
                "owner": section.metadata_value("HLD-OWNER", "TBD") or "TBD",
                "phase_target": "POC" if reason_kind == "temporary_poc_choice" else "MVP",
                "revisit_trigger": "before MVP promotion" if status == "provisional" else "",
                "conflicts_with": section.refs_by_kind("CONFLICTS_WITH"),
                "status": status,
                "source_hld_sections": [section.id],
            }
        )
    questions = _group_questions(items)
    summary = {
        "examined_items": len(items),
        "baked": sum(1 for item in items if item["status"] == "baked"),
        "provisional": sum(1 for item in items if item["status"] == "provisional"),
        "unresolved": sum(1 for item in items if item["status"] == "unresolved"),
        "grouped_questions": len(questions),
    }
    status = "NEEDS_HUMAN_REVIEW" if questions else "READY"
    return {
        "schema_version": 1,
        "status": status,
        "source_hld": str(hld_path),
        "reason_kind_values": list(REASON_KIND_VALUES),
        "item_status_values": list(ITEM_STATUS_VALUES),
        "polite_clarification_prompt": POLITE_CLARIFICATION_PROMPT,
        "summary": summary,
        "examined_items": items,
        "grouped_questions": questions,
    }


def build_hld_readiness_check(cross: dict[str, Any], cross_path: Path) -> dict[str, Any]:
    summary = cross.get("summary", {}) if isinstance(cross.get("summary"), dict) else {}
    unresolved = int(summary.get("unresolved", 0) or 0)
    provisional = int(summary.get("provisional", 0) or 0)
    questions = cross.get("grouped_questions", [])
    if unresolved:
        verdict = "HLD_BLOCKED"
        next_action = "Answer grouped readiness questions or provide external evidence before full SpecKit Preparation."
    elif provisional:
        verdict = "HLD_READY_WITH_ACTIONS"
        next_action = "Either accept current assumptions with revisit triggers or clarify the provisional choices before preparation."
    else:
        verdict = "HLD_READY"
        next_action = "Proceed to Execution Preparation when the user confirms."
    return {
        "schema_version": 1,
        "verdict": verdict,
        "source_hld": cross.get("source_hld", ""),
        "cross_examination_artifact": str(cross_path),
        "blockers": questions if unresolved else [],
        "grouped_questions": questions,
        "accepted_risks": [],
        "revisit_triggers": [
            item for item in cross.get("examined_items", [])
            if isinstance(item, dict) and item.get("status") == "provisional"
        ],
        "next_safe_action": next_action,
    }


def render_cross_examination_md(cross: dict[str, Any]) -> str:
    lines = [
        "# HLD Cross-examination",
        "",
        f"Status: `{cross.get('status')}`",
        "",
        cross.get("polite_clarification_prompt", POLITE_CLARIFICATION_PROMPT),
        "",
        "## Summary",
        "",
    ]
    summary = cross.get("summary", {}) if isinstance(cross.get("summary"), dict) else {}
    for key in ("examined_items", "baked", "provisional", "unresolved", "grouped_questions"):
        lines.append(f"- {key}: {summary.get(key, 0)}")
    lines += ["", "## Grouped questions", ""]
    questions = cross.get("grouped_questions", [])
    if not questions:
        lines.append("- none")
    for question in questions:
        if isinstance(question, dict):
            lines.append(f"- `{question.get('question_id')}` {question.get('question')}")
            lines.append(f"  - affected items: {', '.join(question.get('affected_item_ids', []))}")
    lines += ["", "## Examined items", ""]
    for item in cross.get("examined_items", []):
        if isinstance(item, dict):
            lines.append(f"- `{item.get('item_id')}` `{item.get('status')}` {item.get('statement')}")
            lines.append(f"  - reason kind: `{item.get('reason_kind')}`")
            lines.append(f"  - reason: {item.get('reason')}")
    lines.append("")
    return "\n".join(lines)


def render_readiness_md(readiness: dict[str, Any]) -> str:
    lines = [
        "# HLD Readiness Check",
        "",
        f"Verdict: `{readiness.get('verdict')}`",
        f"Cross-examination: `{readiness.get('cross_examination_artifact')}`",
        "",
        "## Next safe action",
        "",
        readiness.get("next_safe_action", ""),
        "",
        "## Grouped questions",
        "",
    ]
    questions = readiness.get("grouped_questions", [])
    if not questions:
        lines.append("- none")
    for question in questions:
        if isinstance(question, dict):
            lines.append(f"- `{question.get('question_id')}` {question.get('question')}")
    lines.append("")
    return "\n".join(lines)


def write_hld_readiness_artifacts(hld_path: Path, sync_dir: Path) -> dict[str, Any]:
    sync_dir.mkdir(parents=True, exist_ok=True)
    cross = build_hld_cross_examination(hld_path)
    cross_path = sync_dir / "hld_cross_examination.json"
    cross_path.write_text(json.dumps(cross, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync_dir / "hld_cross_examination.md").write_text(render_cross_examination_md(cross), encoding="utf-8")
    readiness = build_hld_readiness_check(cross, cross_path)
    (sync_dir / "hld_readiness_check.json").write_text(json.dumps(readiness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync_dir / "hld_readiness_check.md").write_text(render_readiness_md(readiness), encoding="utf-8")
    return readiness
