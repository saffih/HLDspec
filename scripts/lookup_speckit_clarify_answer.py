#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "of",
    "is", "are", "was", "were", "be", "been", "this", "that", "it", "its",
    "by", "from", "with", "as", "do", "does", "how", "what", "which",
    "should", "would", "could", "can", "will", "when", "where", "who",
    "not", "no", "i", "we", "you", "they", "my", "our", "their",
}

# Known contract keywords for boosting matches (from CONTRACT_NAME_RULES in build_hld_answer_dossier.py)
CONTRACT_KEYWORDS = {
    "database", "cli", "wip", "socket", "task_offer", "task_ack",
    "http", "sse", "storage", "spawn", "devin-bg", "flow_env",
    "environment", "log", "reply", "core.md", "brain",
}


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


def find_sync(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    for candidate in (direct, nested):
        if (candidate / "interface_contract_map.json").exists():
            return candidate
    return direct


def extract_key_terms(question: str) -> list[str]:
    """Extract significant terms from a natural-language question."""
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_.-]*", question)
    terms: list[str] = []
    for token in tokens:
        lower = token.lower()
        if lower in STOPWORDS:
            continue
        terms.append(lower)
        if lower in CONTRACT_KEYWORDS:
            terms.insert(0, lower)  # boost contract keywords to front
    # also keep original case for things like TASK_OFFER, core.md
    for token in tokens:
        if token != token.lower() and len(token) > 2:
            terms.append(token)
    return list(dict.fromkeys(terms))  # deduplicate, preserve order


def is_tbd(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().upper() in {"TBD", "", "UNKNOWN", "N/A"}
    if isinstance(value, list):
        return all(is_tbd(v) for v in value)
    return False


def score_match(text: str, terms: list[str]) -> int:
    lower = text.lower()
    return sum(1 for t in terms if t.lower() in lower)


def lookup(workspace: Path, question: str) -> dict[str, Any]:
    sync = find_sync(workspace)
    terms = extract_key_terms(question)

    interface_map = load_json(sync / "interface_contract_map.json")
    data_map = load_json(sync / "data_ownership_map.json")
    open_map = load_json(sync / "open_questions_tbd_map.json")

    best_score = 0
    best_match: dict[str, Any] | None = None
    best_source = ""
    best_answer = ""
    best_tbd = True

    # Search interface_contract_map
    for contract in as_list(interface_map.get("contracts")):
        if not isinstance(contract, dict):
            continue
        name = str(contract.get("contract_name", ""))
        provider = str(contract.get("provider", "TBD"))
        consumer = str(contract.get("consumer", "TBD"))
        cid = str(contract.get("contract_id", ""))
        text = f"{name} {provider} {consumer} {' '.join(as_list(contract.get('evidence', [])))}"
        score = score_match(text, terms)
        if score > best_score:
            best_score = score
            best_match = contract
            best_source = f"interface_contract_map.json:{cid}"
            values_tbd = is_tbd(provider) and is_tbd(consumer)
            best_tbd = values_tbd
            if not values_tbd:
                best_answer = (
                    f"Contract: {name}. Provider: {provider}. Consumer: {consumer}."
                )
                evidence = as_list(contract.get("evidence"))
                if evidence:
                    best_answer += f" Evidence: {evidence[0]}"
            else:
                best_answer = f"Contract '{name}' found but provider/consumer are TBD."

    # Search data_ownership_map
    for obj in as_list(data_map.get("data_objects")):
        if not isinstance(obj, dict):
            continue
        obj_name = str(obj.get("data_object", ""))
        sot = str(obj.get("source_of_truth", "TBD"))
        owner = str(obj.get("owner", "TBD"))
        text = f"{obj_name} {sot} {owner}"
        score = score_match(text, terms)
        if score > best_score:
            best_score = score
            best_match = obj
            best_source = f"data_ownership_map.json:{obj_name}"
            values_tbd = is_tbd(sot) and is_tbd(owner)
            best_tbd = values_tbd
            if not values_tbd:
                best_answer = (
                    f"Data object: {obj_name}. Source of truth: {sot}. Owner: {owner}."
                )
                timing = str(obj.get("update_timing", "TBD"))
                if not is_tbd(timing):
                    best_answer += f" Update timing: {timing}."
            else:
                best_answer = f"Data object '{obj_name}' found but source_of_truth/owner are TBD."

    # Search open_questions_tbd_map
    if best_score == 0:
        for item in as_list(open_map.get("items")):
            if not isinstance(item, dict):
                continue
            text = str(item.get("question_or_tbd", ""))
            score = score_match(text, terms)
            if score > best_score:
                best_score = score
                best_match = item
                best_source = f"open_questions_tbd_map.json"
                best_tbd = True
                best_answer = f"Open question/TBD found: {text[:300]}"

    if best_score == 0 or best_match is None:
        return {
            "classification": "ESCALATE_TO_HUMAN",
            "answer": "No matching evidence found in dossier artifacts.",
            "evidence_source": "none",
            "confidence": "LOW",
            "affected_artifacts": [],
            "question": question,
            "search_terms": terms[:10],
        }

    if best_tbd:
        return {
            "classification": "ESCALATE_TO_HUMAN",
            "answer": best_answer,
            "evidence_source": best_source,
            "confidence": "LOW",
            "affected_artifacts": ["constitution_update_plan.json"],
            "question": question,
            "search_terms": terms[:10],
        }

    return {
        "classification": "ANSWER_FROM_EVIDENCE",
        "answer": best_answer,
        "evidence_source": best_source,
        "confidence": "HIGH" if best_score >= 2 else "MEDIUM",
        "affected_artifacts": [],
        "question": question,
        "search_terms": terms[:10],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Look up a SpecKit clarify question in the HLDspec Answer Dossier."
    )
    parser.add_argument("workspace")
    parser.add_argument("question")
    args = parser.parse_args()

    result = lookup(Path(args.workspace).resolve(), args.question)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["classification"] == "ANSWER_FROM_EVIDENCE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
