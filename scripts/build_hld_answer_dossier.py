#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ARCHITECT_KEYWORDS = [
    "must", "never", "forbidden", "critical", "interface", "contract",
    "protocol", "api", "cli", "http", "sse", "socket", "database",
    "source of truth", "wip", "sync", "projection", "provider",
    "consumer", "integration", "data flow", "retry", "fallback",
    "failure", "error", "security", "permission", "environment",
    "session", "wal", "transaction", "logging",
]

PM_KEYWORDS = [
    "stakeholder", "persona", "pain point", "business outcome",
    "job-to-be-done", "job to be done", "user story",
    "acceptance criteria", "success metric", "workflow", "journey",
    "priority", "v1 scope", "mvp", "non-goal", "business value",
    "adoption", "quality metric", "as a user", "goal",
]

CONTRACT_NAME_RULES = [
    ("core.md", "Brain-to-Flow CLI Contract"),
    ("brain", "Brain-to-Flow CLI Contract"),
    ("cli", "CLI Protocol Contract"),
    ("database", "Database API Contract"),
    ("wip", "WIP Source-of-Truth Contract"),
    ("socket", "Task Delivery Handshake Contract"),
    ("task_offer", "Task Delivery Handshake Contract"),
    ("task_ack", "Task Delivery Handshake Contract"),
    ("http", "HTTP/UI API Contract"),
    ("sse", "HTTP/UI API Contract"),
    ("storage", "Storage Projection Contract"),
    ("markdown", "Storage Projection Contract"),
    ("spawn", "Session Spawn Contract"),
    ("devin-bg", "Session Spawn Contract"),
    ("flow_env", "Environment Isolation Contract"),
    ("environment", "Environment Isolation Contract"),
    ("log", "Logging Contract"),
    ("reply", "Reply Handling Contract"),
]


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


def parse_hld_sections(hld_text: str) -> list[dict[str, Any]]:
    lines = hld_text.splitlines()
    starts: list[tuple[int, str, str, int]] = []
    hld_re = re.compile(r"^(#{2,6})\s+(HLD-\d{3})\s*-\s*(.+?)\s*$")
    heading_re = re.compile(r"^(#{2,6})\s+(.+?)\s*$")

    for idx, line in enumerate(lines, start=1):
        m = hld_re.match(line)
        if m:
            starts.append((idx, m.group(2), norm(m.group(3)), len(m.group(1))))
            continue
        if not starts:
            m2 = heading_re.match(line)
            if m2:
                synthetic = f"SEC-{len(starts) + 1:03d}"
                starts.append((idx, synthetic, norm(m2.group(2)), len(m2.group(1))))

    if not starts:
        return [{"hld_id": "DOCUMENT", "title": "Document", "line_start": 1, "line_end": len(lines), "text": hld_text}]

    sections: list[dict[str, Any]] = []
    for pos, (start, sid, title, level) in enumerate(starts):
        end = starts[pos + 1][0] - 1 if pos + 1 < len(starts) else len(lines)
        chunk = "\n".join(lines[start - 1:end])
        sections.append(
            {
                "hld_id": sid,
                "title": title,
                "heading_level": level,
                "line_start": start,
                "line_end": end,
                "text": chunk,
            }
        )
    return sections


def keyword_hits(text: str, keywords: list[str]) -> list[str]:
    lower = text.lower()
    return sorted({kw for kw in keywords if kw.lower() in lower})


def find_line_hotspots(lines: list[str], keywords: list[str], area: str, context: int = 2) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    lower_keywords = [(kw, kw.lower()) for kw in keywords if len(kw) >= 2]
    seen: set[tuple[int, str]] = set()
    for idx, line in enumerate(lines, start=1):
        lower = line.lower()
        matched = [kw for kw, low in lower_keywords if low in lower]
        if not matched:
            continue
        start = max(1, idx - context)
        end = min(len(lines), idx + context)
        key = (idx, area)
        if key in seen:
            continue
        seen.add(key)
        hits.append(
            {
                "area": area,
                "line": idx,
                "matched_terms": sorted(set(matched)),
                "context_start": start,
                "context_end": end,
                "context": "\n".join(lines[start - 1:end]),
            }
        )
    return hits


def extract_project_vocabulary(hld_text: str, sections: list[dict[str, Any]]) -> dict[str, Any]:
    counter: Counter[str] = Counter()
    patterns = [
        r"`([^`]{2,100})`",
        r"\b[A-Z][A-Z0-9_]{2,}\b",
        r"\bTASK_[A-Z0-9_]+\b",
        r"\bFLOW_[A-Z0-9_]+\b",
        r"\b[a-zA-Z_][\w/-]+\.(?:py|md|json|db|sh|yaml|yml)\b",
        r"\bflow\s+[a-z][\w-]*(?:\s+[a-z][\w-]*)?\b",
        r"\b[a-z][a-z0-9_]*_[a-z0-9_]+\b",
    ]
    for pattern in patterns:
        for match in re.findall(pattern, hld_text):
            term = norm(match if isinstance(match, str) else match[0])
            if 2 <= len(term) <= 100:
                counter[term] += 1

    for section in sections:
        title = str(section.get("title", ""))
        for word in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{2,}\b", title):
            if word.lower() not in {"the", "and", "for", "with", "this", "that"}:
                counter[word] += 2
        for phrase in re.findall(r"\b[A-Z][A-Za-z0-9_-]+(?:\s+[A-Z][A-Za-z0-9_-]+)+\b", title):
            counter[norm(phrase)] += 3

    for table in re.findall(r"CREATE\s+TABLE\s+([a-zA-Z_][\w]*)", hld_text, flags=re.I):
        counter[table] += 5

    stop_terms = {"HLD", "Status", "Purpose", "Overview", "Implementation", "Section"}
    terms = [
        {"term": term, "count": count}
        for term, count in counter.most_common(200)
        if term not in stop_terms and len(term.strip()) > 1
    ]
    return {"schema_version": 1, "term_count": len(terms), "terms": terms}


def classify_sections(sections: list[dict[str, Any]], vocabulary_terms: list[str]) -> dict[str, Any]:
    section_rows: list[dict[str, Any]] = []
    learned_terms_lower = [term.lower() for term in vocabulary_terms[:150] if len(term) >= 3]

    for section in sections:
        text = str(section.get("text", ""))
        lower = text.lower()
        arch_hits = keyword_hits(text, ARCHITECT_KEYWORDS)
        pm_hits = keyword_hits(text, PM_KEYWORDS)
        learned_hits = sorted({term for term in learned_terms_lower if term in lower})[:30]
        arch_score = len(arch_hits) + sum(1 for t in learned_hits if any(k in t for k in ["api", "cli", "db", "socket", "wip", "session", "flow"]))
        pm_score = len(pm_hits)

        def level(score: int) -> str:
            if score >= 5:
                return "high"
            if score >= 2:
                return "medium"
            if score >= 1:
                return "low"
            return "none"

        section_rows.append(
            {
                "hld_id": section.get("hld_id"),
                "title": section.get("title"),
                "line_start": section.get("line_start"),
                "line_end": section.get("line_end"),
                "architect_signal": level(arch_score),
                "pm_signal": level(pm_score),
                "architect_terms": arch_hits,
                "pm_terms": pm_hits,
                "learned_terms": learned_hits,
                "reason": "classified from generic keyword hits plus learned project vocabulary",
            }
        )

    return {
        "schema_version": 1,
        "sections": section_rows,
        "summary": {
            "section_count": len(section_rows),
            "architect_high_or_medium": sum(1 for s in section_rows if s["architect_signal"] in {"high", "medium"}),
            "pm_high_or_medium": sum(1 for s in section_rows if s["pm_signal"] in {"high", "medium"}),
        },
    }


def guess_contract_name(text: str, title: str) -> str:
    lower = f"{title}\n{text}".lower()
    for token, name in CONTRACT_NAME_RULES:
        if token.lower() in lower:
            return name
    return f"{title} Contract"


def extract_first_matching_lines(text: str, terms: list[str], limit: int = 5) -> list[str]:
    result: list[str] = []
    for line in text.splitlines():
        stripped = norm(line.strip("-* "))
        if not stripped:
            continue
        lower = stripped.lower()
        if any(term in lower for term in terms):
            result.append(stripped[:300])
        if len(result) >= limit:
            break
    return result


def build_interface_contract_map(sections: list[dict[str, Any]], chunk_map: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["hld_id"]: row for row in as_list(chunk_map.get("sections")) if isinstance(row, dict)}
    contracts: dict[str, dict[str, Any]] = {}

    for section in sections:
        sid = str(section.get("hld_id"))
        row = by_id.get(sid, {})
        if row.get("architect_signal") not in {"high", "medium"}:
            continue
        text = str(section.get("text", ""))
        title = str(section.get("title", ""))
        if not keyword_hits(text, ["interface", "contract", "protocol", "api", "cli", "socket", "http", "sse", "database", "wip", "spawn", "sync", "projection", "reply", "log"]):
            continue

        name = guess_contract_name(text, title)
        contract_id = slug(name).upper().replace("-", "_")
        existing = contracts.setdefault(
            contract_id,
            {
                "contract_id": contract_id,
                "contract_name": name,
                "provider": "TBD",
                "consumer": "TBD",
                "protocol_or_api": [],
                "source_of_truth": "TBD",
                "inputs": [],
                "outputs": [],
                "errors": [],
                "fallback": [],
                "security_rule": [],
                "data_owned": [],
                "data_read": [],
                "data_written": [],
                "update_timing": "TBD",
                "depends_on": [],
                "blocks": [],
                "source_hld_sections": [],
                "evidence": [],
                "tbd_or_questions": [],
            },
        )
        existing["source_hld_sections"].append(sid)
        existing["evidence"].extend(extract_first_matching_lines(text, ["must", "never", "interface", "contract", "protocol", "api", "cli", "source of truth"], 6))
        existing["protocol_or_api"].extend(keyword_hits(text, ["cli", "http", "sse", "unix socket", "json", "sqlite", "markdown", "rest"]))
        existing["inputs"].extend(extract_first_matching_lines(text, ["input", "request", "command", "task", "id", "path"], 4))
        existing["outputs"].extend(extract_first_matching_lines(text, ["output", "response", "returns", "ack", "report", "status"], 4))
        existing["errors"].extend(extract_first_matching_lines(text, ["error", "failure", "retry", "timeout", "conflict"], 4))
        existing["fallback"].extend(extract_first_matching_lines(text, ["fallback", "polling", "rollback", "degraded"], 4))
        existing["security_rule"].extend(extract_first_matching_lines(text, ["security", "permission", "auth", "owner", "forbidden", "never"], 4))
        existing["tbd_or_questions"].extend(extract_first_matching_lines(text, ["tbd", "question", "unknown", "to be decided"], 4))

        lower = text.lower()
        if "database" in lower and "source of truth" in lower:
            existing["source_of_truth"] = "SQLite database via Flow Core Database API"
        elif "markdown" in lower and "projection" in lower:
            existing["source_of_truth"] = "Database; markdown is projection"
        if "core.md" in lower:
            existing["consumer"] = "core.md / AI session"
        if "flow cli" in lower or " cli" in lower:
            existing["provider"] = "Flow CLI"
        if "database api" in lower:
            existing["provider"] = "Flow Core Database API"
        if "http" in lower or "sse" in lower:
            existing["provider"] = "HTTP API layer"
            existing["consumer"] = "Web UI / browser"
        if "socket" in lower:
            existing["provider"] = "Unix socket notifier/listener"
            existing["consumer"] = "AI session listener / Flow task assignment"

    for contract in contracts.values():
        for key in [
            "protocol_or_api", "inputs", "outputs", "errors", "fallback",
            "security_rule", "data_owned", "data_read", "data_written",
            "depends_on", "blocks", "source_hld_sections", "evidence",
            "tbd_or_questions",
        ]:
            values = []
            seen = set()
            for item in as_list(contract.get(key)):
                item_s = str(item)
                if item_s and item_s not in seen:
                    seen.add(item_s)
                    values.append(item_s)
            contract[key] = values[:20]
    return {"schema_version": 1, "contracts": sorted(contracts.values(), key=lambda c: c["contract_name"])}


def build_data_ownership_map(sections: list[dict[str, Any]]) -> dict[str, Any]:
    objects: dict[str, dict[str, Any]] = {}
    for section in sections:
        text = str(section.get("text", ""))
        if not keyword_hits(text, ["data", "database", "source of truth", "table", "schema", "state", "read", "write", "sync", "projection"]):
            continue
        sid = str(section.get("hld_id"))
        title = str(section.get("title"))
        table_names = re.findall(r"CREATE\s+TABLE\s+([a-zA-Z_][\w]*)", text, flags=re.I)
        if not table_names and ("database" in text.lower() or "source of truth" in text.lower()):
            table_names = [title]
        for obj in table_names:
            key = slug(obj)
            item = objects.setdefault(
                key,
                {
                    "data_object": obj,
                    "owner": "TBD",
                    "readers": [],
                    "writers": [],
                    "source_of_truth": "TBD",
                    "update_timing": "TBD",
                    "source_hld_sections": [],
                    "evidence": [],
                    "tbd_or_questions": [],
                },
            )
            item["source_hld_sections"].append(sid)
            item["evidence"].extend(extract_first_matching_lines(text, ["source of truth", "read", "write", "sync", "projection", "table", "schema"], 6))
            lower = text.lower()
            if "sqlite" in lower or "database" in lower:
                item["source_of_truth"] = "SQLite database via Database API"
            if "database api" in lower:
                item["owner"] = "Flow Core Database API"
            if "event-driven" in lower:
                item["update_timing"] = "Event-driven after database writes"
            elif "every" in lower and "seconds" in lower:
                item["update_timing"] = "Interval/timer based; verify exact value in HLD evidence"
            item["tbd_or_questions"].extend(extract_first_matching_lines(text, ["tbd", "question", "unknown"], 4))
    return {"schema_version": 1, "data_objects": list(objects.values())}


def build_integration_map(sections: list[dict[str, Any]]) -> dict[str, Any]:
    integrations: list[dict[str, Any]] = []
    for section in sections:
        text = str(section.get("text", ""))
        if not keyword_hits(text, ["flow", "integration", "->", "calls", "sync", "spawns", "api", "cli", "socket", "database"]):
            continue
        lines = []
        for line in text.splitlines():
            if "->" in line or "calls" in line.lower() or "sync" in line.lower() or "spawns" in line.lower():
                lines.append(norm(line.strip(" -*`")))
            if len(lines) >= 8:
                break
        if not lines:
            continue
        integrations.append(
            {
                "integration_id": f"INT-{len(integrations) + 1:03d}",
                "name": str(section.get("title")),
                "source_hld_sections": [section.get("hld_id")],
                "producer": "TBD",
                "consumer": "TBD",
                "path_or_flow": lines,
                "dependency_reason": "Integration flow found in HLD section; provider/consumer should be verified by Architect pass.",
                "failure_or_fallback": extract_first_matching_lines(text, ["failure", "fallback", "retry", "timeout", "conflict"], 4),
                "tbd_or_questions": extract_first_matching_lines(text, ["tbd", "question", "unknown"], 3),
            }
        )
    return {"schema_version": 1, "integrations": integrations}


def build_product_answer_pack(sections: list[dict[str, Any]], chunk_map: dict[str, Any]) -> dict[str, Any]:
    by_id = {row["hld_id"]: row for row in as_list(chunk_map.get("sections")) if isinstance(row, dict)}
    items: list[dict[str, Any]] = []
    for section in sections:
        sid = str(section.get("hld_id"))
        row = by_id.get(sid, {})
        if row.get("pm_signal") not in {"high", "medium"}:
            continue
        text = str(section.get("text", ""))
        items.append(
            {
                "capability_id": sid,
                "capability_name": str(section.get("title")),
                "persona": "TBD",
                "job_to_be_done": "; ".join(extract_first_matching_lines(text, ["job-to-be-done", "job to be done", "so that"], 2)) or "TBD",
                "user_goal": "; ".join(extract_first_matching_lines(text, ["goal", "want", "need", "so that"], 3)) or "TBD",
                "pain_point": "; ".join(extract_first_matching_lines(text, ["pain point", "problem", "struggle", "difficulty"], 3)) or "TBD",
                "user_story": "; ".join(extract_first_matching_lines(text, ["as a user", "as a system", "as an ai"], 4)) or "TBD",
                "acceptance_criteria": extract_first_matching_lines(text, ["acceptance criteria", "must", "can", "should"], 8),
                "success_metrics": extract_first_matching_lines(text, ["target", "metric", "success", "%", "rate"], 8),
                "priority": "TBD",
                "scope_status": "TBD",
                "non_goals": extract_first_matching_lines(text, ["non-goal", "out of scope", "do not"], 4),
                "source_hld_sections": [sid],
                "evidence": extract_first_matching_lines(text, ["business", "user", "acceptance", "success", "workflow", "goal"], 8),
                "tbd_or_questions": extract_first_matching_lines(text, ["tbd", "question", "unknown"], 4),
            }
        )
    return {"schema_version": 1, "product_items": items}


def build_architecture_answer_pack(interface_map: dict[str, Any], data_map: dict[str, Any], integration_map: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "summary": {
            "contract_count": len(as_list(interface_map.get("contracts"))),
            "data_object_count": len(as_list(data_map.get("data_objects"))),
            "integration_count": len(as_list(integration_map.get("integrations"))),
        },
        "contracts": as_list(interface_map.get("contracts")),
        "data_objects": as_list(data_map.get("data_objects")),
        "integrations": as_list(integration_map.get("integrations")),
    }


def build_dependency_reason_map(plan: dict[str, Any], integrations: dict[str, Any]) -> dict[str, Any]:
    planned = [s for s in as_list(plan.get("planned_specs")) if isinstance(s, dict)]
    rows: list[dict[str, Any]] = []
    for spec in planned:
        spec_id = str(spec.get("planned_spec_id", ""))
        deps = [str(x) for x in as_list(spec.get("depends_on_specs"))]
        rows.append(
            {
                "planned_spec_id": spec_id,
                "capability_name": str(spec.get("title", "")),
                "depends_on": deps,
                "dependency_reason": (
                    "Foundation/root candidate; no upstream planned spec dependencies declared."
                    if not deps
                    else "Depends on upstream planned specs declared by spec build plan; verify exact provider/consumer link in integration map."
                ),
                "source_hld_sections": as_list(spec.get("source_hld_sections")),
                "integration_evidence": [
                    i for i in as_list(integrations.get("integrations"))
                    if set(as_list(spec.get("source_hld_sections"))) & set(as_list(i.get("source_hld_sections")))
                ][:5],
                "tbd_or_questions": ["Provider/consumer reason should be verified if not explicit in integration evidence."] if deps else [],
            }
        )
    return {"schema_version": 1, "dependency_reasons": rows}


def build_open_questions_tbd_map(sections: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    questions: list[dict[str, Any]] = []
    for section in sections:
        text = str(section.get("text", ""))
        for line in text.splitlines():
            line_n = norm(line)
            if not line_n:
                continue
            if "TBD" in line_n or "?" in line_n or "unknown" in line_n.lower() or "open question" in line_n.lower():
                questions.append({"source_hld_sections": [section.get("hld_id")], "title": section.get("title"), "question_or_tbd": line_n[:400]})
    for spec in as_list(plan.get("planned_specs")):
        if isinstance(spec, dict) and (spec.get("user_decision_needed") or spec.get("requires_user_review")):
            questions.append(
                {
                    "planned_spec_id": spec.get("planned_spec_id"),
                    "source_hld_sections": as_list(spec.get("source_hld_sections")),
                    "question_or_tbd": str(spec.get("user_decision_needed") or "Requires user review."),
                }
            )
    return {"schema_version": 1, "items": questions}


def build_speckit_answer_dossier(plan: dict[str, Any], sections: list[dict[str, Any]], interface_map: dict[str, Any], data_map: dict[str, Any], integration_map: dict[str, Any], product_pack: dict[str, Any], dependency_map: dict[str, Any]) -> dict[str, Any]:
    planned = [s for s in as_list(plan.get("planned_specs")) if isinstance(s, dict)]
    sec_by_id = {str(s.get("hld_id")): s for s in sections}
    contracts = as_list(interface_map.get("contracts"))
    data_objects = as_list(data_map.get("data_objects"))
    integrations = as_list(integration_map.get("integrations"))
    product_items = as_list(product_pack.get("product_items"))
    dep_items = {str(x.get("planned_spec_id")): x for x in as_list(dependency_map.get("dependency_reasons")) if isinstance(x, dict)}

    specs: list[dict[str, Any]] = []
    for spec in planned:
        sid_list = [str(x) for x in as_list(spec.get("source_hld_sections"))]
        matching_sections = [sec_by_id[sid] for sid in sid_list if sid in sec_by_id]
        text = "\n".join(str(s.get("text", "")) for s in matching_sections)
        title = str(spec.get("title") or (matching_sections[0].get("title") if matching_sections else spec.get("planned_spec_id")))
        matched_contracts = [c for c in contracts if set(sid_list) & set(as_list(c.get("source_hld_sections")))]
        matched_data = [d for d in data_objects if set(sid_list) & set(as_list(d.get("source_hld_sections")))]
        matched_integrations = [i for i in integrations if set(sid_list) & set(as_list(i.get("source_hld_sections")))]
        matched_product = [p for p in product_items if set(sid_list) & set(as_list(p.get("source_hld_sections")))]
        purpose_lines = extract_first_matching_lines(text, ["purpose", "goal", "objective", "as a", "must", "provides"], 2)

        specs.append(
            {
                "planned_spec_id": spec.get("planned_spec_id"),
                "capability_name": title,
                "plain_english_purpose": " ".join(purpose_lines) if purpose_lines else f"Specify capability: {title}",
                "source_hld_sections": sid_list,
                "pm_value": matched_product[0].get("user_goal", "TBD") if matched_product else "TBD",
                "user_story_or_workflow": matched_product[0].get("user_story", "TBD") if matched_product else "TBD",
                "acceptance_criteria": matched_product[0].get("acceptance_criteria", []) if matched_product else [],
                "success_metrics_or_TBD": matched_product[0].get("success_metrics", []) if matched_product else ["TBD"],
                "architecture_owner": "TBD",
                "owns": [d.get("data_object") for d in matched_data] or ["TBD"],
                "provides": [c.get("contract_name") for c in matched_contracts] or ["TBD"],
                "consumes": as_list(spec.get("depends_on_specs")) or [],
                "interfaces": matched_contracts,
                "provider_consumer_links": matched_integrations,
                "data_owns": matched_data,
                "data_reads": ["TBD"],
                "data_writes": ["TBD"],
                "source_of_truth_or_TBD": matched_data[0].get("source_of_truth", "TBD") if matched_data else "TBD",
                "update_timing_or_TBD": matched_data[0].get("update_timing", "TBD") if matched_data else "TBD",
                "integration_paths": matched_integrations,
                "dependency_reasons": dep_items.get(str(spec.get("planned_spec_id")), {}),
                "failure_fallbacks": [x for c in matched_contracts for x in as_list(c.get("errors")) + as_list(c.get("fallback"))][:10] or ["TBD"],
                "security_rules": [x for c in matched_contracts for x in as_list(c.get("security_rule"))][:10] or ["TBD"],
                "open_questions": [],
                "not_for_speckit_yet": [],
            }
        )

    return {
        "schema_version": 1,
        "status": "GENERATED",
        "purpose": "Structured answer dossier for later SpecKit/spec orchestration. This is not final specs.",
        "planned_spec_count": len(specs),
        "specs": specs,
        "summary": {
            "specs_with_contracts": sum(1 for s in specs if s.get("provides") != ["TBD"]),
            "specs_with_data": sum(1 for s in specs if s.get("owns") != ["TBD"]),
            "specs_with_pm_context": sum(1 for s in specs if s.get("pm_value") != "TBD" or s.get("user_story_or_workflow") != "TBD"),
        },
    }


def build_quality_review(dossier: dict[str, Any], interface_map: dict[str, Any], product_pack: dict[str, Any]) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    specs = [s for s in as_list(dossier.get("specs")) if isinstance(s, dict)]
    contracts = as_list(interface_map.get("contracts"))
    products = as_list(product_pack.get("product_items"))

    if not specs:
        findings.append({"id": "ADQ-001", "severity": "BLOCKER", "area": "planned spec coverage", "finding": "Answer Dossier has no planned specs.", "recommendation": "Build spec_build_plan.json before building the Answer Dossier."})
    if not contracts:
        findings.append({"id": "ADQ-002", "severity": "BLOCKER", "area": "interface contracts", "finding": "Answer Dossier found no named interface contracts.", "recommendation": "Run generic grep, learned vocabulary grep, and Architect pass before approval."})
    if not products:
        findings.append({"id": "ADQ-003", "severity": "ACTION", "area": "product context", "finding": "Answer Dossier found no PM/product items.", "recommendation": "Run Product Manager pass to capture personas, workflows, acceptance criteria, and metrics."})

    for spec in specs:
        spec_id = spec.get("planned_spec_id")
        if not as_list(spec.get("source_hld_sections")):
            findings.append({"id": "ADQ-004", "severity": "BLOCKER", "area": "traceability", "finding": f"{spec_id} has no source HLD sections.", "recommendation": "Rebuild spec build plan with HLD traceability."})
        if spec.get("provides") == ["TBD"] and spec.get("owns") == ["TBD"] and not spec.get("consumes"):
            findings.append({"id": "ADQ-005", "severity": "ACTION", "area": "shallow spec context", "finding": f"{spec_id} has no extracted provides/owns/consumes context.", "recommendation": "Review Architect extraction for this planned spec or mark explicit TBDs."})

    status = "REWORK_REQUIRED" if any(f.get("severity") == "BLOCKER" for f in findings) else ("APPROVAL_READY_WITH_ACTIONS" if findings else "APPROVAL_READY")
    return {
        "schema_version": 1,
        "review_type": "HLD_ANSWER_DOSSIER_QUALITY_GATE",
        "status": status,
        "findings": findings,
        "summary": dossier.get("summary", {}),
        "human_checkpoint": {
            "question": "Is the Answer Dossier complete enough to support later SpecKit/spec orchestration without guessing?",
            "options": ["APPROVE_DOSSIER", "MODIFY_DOSSIER", "EXTRACT_MORE", "MARK_TBDS"],
            "human_decision": "TBD",
        },
    }


def render_simple_table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return out


def render_hotspots_md(data: dict[str, Any]) -> str:
    lines = ["# HLD Grep Hotspots", "", "made by AI", ""]
    lines += render_simple_table(["area", "line", "terms"], [[h["area"], h["line"], ", ".join(h["matched_terms"])] for h in as_list(data.get("hotspots"))[:200]])
    return "\n".join(lines) + "\n"


def render_vocabulary_md(data: dict[str, Any]) -> str:
    lines = ["# HLD Project Vocabulary", "", "made by AI", ""]
    lines += render_simple_table(["term", "count"], [[t["term"], t["count"]] for t in as_list(data.get("terms"))[:200]])
    return "\n".join(lines) + "\n"


def render_chunk_map_md(data: dict[str, Any]) -> str:
    lines = ["# HLD Chunk Signal Map", "", "made by AI", ""]
    rows = [[row.get("hld_id"), row.get("title"), row.get("architect_signal"), row.get("pm_signal")] for row in as_list(data.get("sections"))]
    lines += render_simple_table(["section", "title", "architect", "pm"], rows)
    return "\n".join(lines) + "\n"


def render_contract_map_md(data: dict[str, Any]) -> str:
    lines = ["# Interface Contract Map", "", "made by AI", ""]
    rows = [[c.get("contract_name"), c.get("provider"), c.get("consumer"), ", ".join(as_list(c.get("source_hld_sections")))] for c in as_list(data.get("contracts"))]
    lines += render_simple_table(["contract", "provider", "consumer", "sources"], rows)
    return "\n".join(lines) + "\n"


def render_product_pack_md(data: dict[str, Any]) -> str:
    lines = ["# Product Answer Pack", "", "made by AI", ""]
    rows = [[item.get("capability_id"), item.get("capability_name"), item.get("user_goal"), item.get("user_story")] for item in as_list(data.get("product_items"))]
    lines += render_simple_table(["id", "capability", "goal", "story"], rows)
    return "\n".join(lines) + "\n"


def render_architecture_pack_md(data: dict[str, Any]) -> str:
    summary = data.get("summary", {})
    return "\n".join([
        "# Architecture Answer Pack",
        "",
        "made by AI",
        "",
        f"- contracts: `{summary.get('contract_count', 0)}`",
        f"- data objects: `{summary.get('data_object_count', 0)}`",
        f"- integrations: `{summary.get('integration_count', 0)}`",
        "",
        "See interface_contract_map.md, data_ownership_map.md, and integration_map.md for details.",
        "",
    ])


def render_dossier_md(data: dict[str, Any]) -> str:
    lines = ["# SpecKit Answer Dossier", "", "made by AI", "", data.get("purpose", ""), ""]
    summary = data.get("summary", {})
    lines += [
        "## Summary",
        "",
        f"- planned specs: `{data.get('planned_spec_count', 0)}`",
        f"- specs with contracts: `{summary.get('specs_with_contracts', 0)}`",
        f"- specs with data: `{summary.get('specs_with_data', 0)}`",
        f"- specs with PM context: `{summary.get('specs_with_pm_context', 0)}`",
        "",
        "## Planned spec dossier",
        "",
    ]
    for spec in as_list(data.get("specs")):
        lines += [
            f"### {spec.get('planned_spec_id')} - {spec.get('capability_name')}",
            "",
            f"- source HLD sections: {', '.join(as_list(spec.get('source_hld_sections'))) or 'none'}",
            f"- purpose: {spec.get('plain_english_purpose')}",
            f"- PM value: {spec.get('pm_value')}",
            f"- provides: {', '.join(as_list(spec.get('provides')))}",
            f"- owns: {', '.join(as_list(spec.get('owns')))}",
            f"- consumes: {', '.join(str(x) for x in as_list(spec.get('consumes'))) or 'none'}",
            f"- source of truth: {spec.get('source_of_truth_or_TBD')}",
            f"- update timing: {spec.get('update_timing_or_TBD')}",
            "",
        ]
    return "\n".join(lines) + "\n"


def render_quality_md(data: dict[str, Any]) -> str:
    lines = ["# HLD Answer Dossier Quality Review", "", "made by AI", "", f"Status: `{data.get('status')}`", ""]
    if not as_list(data.get("findings")):
        lines.append("No findings.")
    for f in as_list(data.get("findings")):
        lines += [
            f"## {f.get('id')} - {f.get('area')}",
            "",
            f"- severity: `{f.get('severity')}`",
            f"- finding: {f.get('finding')}",
            f"- recommendation: {f.get('recommendation')}",
            "",
        ]
    return "\n".join(lines) + "\n"


def write_md_json(sync: Path, name: str, data: Any, md: str) -> None:
    write_json(sync / f"{name}.json", data)
    (sync / f"{name}.md").write_text(md, encoding="utf-8")


def build(workspace: Path) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    hld_path = workspace / "HLD.md"
    if not hld_path.exists():
        raise SystemExit(f"Missing HLD.md in workspace: {hld_path}")

    hld_text = hld_path.read_text(encoding="utf-8", errors="replace")
    lines = hld_text.splitlines()
    sections = parse_hld_sections(hld_text)
    plan = load_json(sync / "spec_build_plan.json")

    generic_hotspots = find_line_hotspots(lines, ARCHITECT_KEYWORDS, "architect_generic") + find_line_hotspots(lines, PM_KEYWORDS, "pm_generic")
    vocabulary = extract_project_vocabulary(hld_text, sections)
    learned_terms = [str(t["term"]) for t in as_list(vocabulary.get("terms"))[:120]]
    learned_hotspots = find_line_hotspots(lines, learned_terms, "project_vocabulary", context=1)
    hotspots = {
        "schema_version": 1,
        "strategy": "generic grep plus learned project vocabulary grep",
        "hotspots": generic_hotspots + learned_hotspots,
        "summary": {
            "generic_hotspot_count": len(generic_hotspots),
            "learned_hotspot_count": len(learned_hotspots),
            "total_hotspot_count": len(generic_hotspots) + len(learned_hotspots),
        },
    }
    chunk_map = classify_sections(sections, learned_terms)
    interface_map = build_interface_contract_map(sections, chunk_map)
    data_map = build_data_ownership_map(sections)
    integration_map = build_integration_map(sections)
    product_pack = build_product_answer_pack(sections, chunk_map)
    architecture_pack = build_architecture_answer_pack(interface_map, data_map, integration_map)
    dependency_map = build_dependency_reason_map(plan, integration_map)
    open_questions = build_open_questions_tbd_map(sections, plan)
    dossier = build_speckit_answer_dossier(plan, sections, interface_map, data_map, integration_map, product_pack, dependency_map)
    quality = build_quality_review(dossier, interface_map, product_pack)

    sync.mkdir(parents=True, exist_ok=True)
    write_md_json(sync, "grep_hotspots", hotspots, render_hotspots_md(hotspots))
    write_md_json(sync, "project_vocabulary", vocabulary, render_vocabulary_md(vocabulary))
    write_md_json(sync, "chunk_signal_map", chunk_map, render_chunk_map_md(chunk_map))
    write_md_json(sync, "interface_contract_map", interface_map, render_contract_map_md(interface_map))
    write_md_json(sync, "data_ownership_map", data_map, "# Data Ownership Map\n\nmade by AI\n\nSee JSON for structured data ownership details.\n")
    write_md_json(sync, "integration_map", integration_map, "# Integration Map\n\nmade by AI\n\nSee JSON for structured integration details.\n")
    write_md_json(sync, "dependency_reason_map", dependency_map, "# Dependency Reason Map\n\nmade by AI\n\nSee JSON for structured dependency reasons.\n")
    write_md_json(sync, "open_questions_tbd_map", open_questions, "# Open Questions and TBD Map\n\nmade by AI\n\nSee JSON for structured open questions and TBDs.\n")
    write_md_json(sync, "architecture_answer_pack", architecture_pack, render_architecture_pack_md(architecture_pack))
    write_md_json(sync, "product_answer_pack", product_pack, render_product_pack_md(product_pack))
    write_md_json(sync, "speckit_answer_dossier", dossier, render_dossier_md(dossier))
    write_md_json(sync, "hld_answer_dossier_quality_review", quality, render_quality_md(quality))

    return {
        "workspace": str(workspace),
        "status": quality.get("status"),
        "hotspots": hotspots.get("summary", {}),
        "sections": chunk_map.get("summary", {}),
        "contracts": len(as_list(interface_map.get("contracts"))),
        "product_items": len(as_list(product_pack.get("product_items"))),
        "planned_specs": dossier.get("planned_spec_count", 0),
        "findings": len(as_list(quality.get("findings"))),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HLD Answer Dossier extraction experiment and synthesis artifacts.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    result = build(Path(args.workspace).resolve())
    print("HLD Answer Dossier generated:")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
