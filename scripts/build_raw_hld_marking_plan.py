#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


ROLE_KEYWORDS: dict[str, list[str]] = {
    "product_context": [
        "user", "persona", "stakeholder", "journey", "story", "business",
        "goal", "requirement", "use case", "customer", "acceptance",
    ],
    "architecture": [
        "architecture", "component", "service", "module", "flow",
        "orchestration", "integration", "system", "boundary",
    ],
    "interface_contract": [
        "api", "http", "endpoint", "contract", "cli", "command",
        "request", "response", "event", "interface",
    ],
    "data_model": [
        "data", "state", "schema", "database", "storage", "persistence",
        "entity", "model", "source of truth",
    ],
    "processing_behavior": [
        "process", "workflow", "behavior", "execute", "runtime",
        "algorithm", "decision", "validation", "step",
    ],
    "governance_context": [
        "assumption", "decision log", "conflict", "source of truth",
        "constraint", "policy", "scope", "constitution", "governance",
    ],
    "security": [
        "security", "auth", "permission", "secret", "token", "access",
    ],
    "operations": [
        "runbook", "deployment", "monitor", "observability", "logging",
        "alert", "environment", "operation",
    ],
}


PERSPECTIVE_QUESTIONS: dict[str, list[str]] = {
    "product_context": [
        "What user value, use case, or user journey does this section define?",
        "Is this context-only or does it imply a SpecKit feature?",
        "What acceptance criteria would make the feature testable?",
    ],
    "architecture": [
        "What component, boundary, or responsibility is defined here?",
        "What must remain connected, and what can be separated?",
        "Does this section impose architecture constraints for downstream specs?",
    ],
    "interface_contract": [
        "Does this define an external API, endpoint, CLI, event, request, or response contract?",
        "Can the contract be specified separately from processing behavior?",
        "What consumers depend on this interface?",
    ],
    "data_model": [
        "What is the source of truth for this state or data?",
        "Who owns mutation and lifecycle of this data?",
        "Which features depend on this model before they can be specified?",
    ],
    "processing_behavior": [
        "What runtime behavior or workflow is defined here?",
        "Is behavior mixed with API contract or data ownership?",
        "What inputs, outputs, failure modes, and verification rules are implied?",
    ],
    "governance_context": [
        "Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?",
        "Does it belong in constitution/prework rather than a feature spec?",
        "What human decision would be needed if this is unclear?",
    ],
    "security": [
        "Does this introduce access, permission, token, secret, or exposure risk?",
        "What must be validated before implementation?",
    ],
    "operations": [
        "Does this define environment, deployment, observability, or runbook behavior?",
        "Is it a feature, support concern, or constitution/operational constraint?",
    ],
}


@dataclass
class MarkingItem:
    candidate_id: str
    title: str
    source_line_start: int
    source_line_end: int
    current_conversion_action: str
    suggested_roles: list[str]
    primary_role: str
    suggested_risk: str
    suggested_specs: str
    suggested_resources: str
    marking_questions: list[str]
    subagents: list[str]
    judge_notes: list[str]


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def source_slice(lines: list[str], start: int, end: int) -> str:
    if start <= 0:
        return ""
    return "\n".join(lines[start - 1 : max(start - 1, end)])


def matches(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(keyword in low for keyword in keywords)


def infer_roles(text: str, title: str) -> list[str]:
    haystack = f"{title}\n{text}"
    roles = [role for role, keywords in ROLE_KEYWORDS.items() if matches(haystack, keywords)]
    if not roles:
        roles = ["architecture"]
    return roles


def choose_primary_role(roles: list[str]) -> str:
    order = [
        "governance_context",
        "product_context",
        "interface_contract",
        "data_model",
        "processing_behavior",
        "security",
        "operations",
        "architecture",
    ]
    for role in order:
        if role in roles:
            return role
    return roles[0] if roles else "architecture"


def infer_risk(roles: list[str], text: str) -> str:
    if "security" in roles or "interface_contract" in roles or "data_model" in roles:
        return "HIGH"
    if len(roles) >= 3:
        return "MEDIUM"
    if re.search(r"\b(conflict|source of truth|must|critical|failure|risk|constraint)\b", text, re.I):
        return "MEDIUM"
    return "LOW"


def subagents_for(roles: list[str]) -> list[str]:
    mapping = {
        "product_context": "product_reviewer",
        "architecture": "architecture_reviewer",
        "interface_contract": "interface_contract_reviewer",
        "data_model": "data_state_reviewer",
        "processing_behavior": "processing_behavior_reviewer",
        "governance_context": "governance_reviewer",
        "security": "security_reviewer",
        "operations": "operations_reviewer",
    }
    return [mapping[role] for role in roles if role in mapping]


def questions_for(roles: list[str]) -> list[str]:
    questions: list[str] = []
    for role in roles:
        questions.extend(PERSPECTIVE_QUESTIONS.get(role, []))
    seen: set[str] = set()
    unique: list[str] = []
    for question in questions:
        if question not in seen:
            unique.append(question)
            seen.add(question)
    return unique


def build_marking_item(candidate: dict[str, Any], source_lines: list[str]) -> MarkingItem:
    start = as_int(candidate.get("source_line_start"), as_int(candidate.get("line"), 0))
    line_count = as_int(candidate.get("source_line_count"), 1)
    end = as_int(candidate.get("source_line_end"), start + max(1, line_count) - 1)
    title = str(candidate.get("title") or "").strip()
    candidate_id = str(candidate.get("proposed_hld_id") or candidate.get("candidate_id") or "").strip()
    text = source_slice(source_lines, start, end)

    roles = infer_roles(text, title)
    primary_role = choose_primary_role(roles)
    risk = infer_risk(roles, text)
    agents = subagents_for(roles)

    notes: list[str] = []
    if "interface_contract" in roles and "processing_behavior" in roles:
        notes.append("Check whether API/interface contract should be separated from processing behavior.")
    if "data_model" in roles and "interface_contract" in roles:
        notes.append("Check whether data/source-of-truth concerns are mixed with interface contract.")
    if "product_context" in roles and primary_role != "product_context":
        notes.append("Product/use-case evidence exists but may be context for another primary role.")
    if "governance_context" in roles:
        notes.append("May belong in constitution/prework rather than a feature spec.")

    return MarkingItem(
        candidate_id=candidate_id,
        title=title,
        source_line_start=start,
        source_line_end=end,
        current_conversion_action=str(candidate.get("recommended_action") or "UNKNOWN"),
        suggested_roles=roles,
        primary_role=primary_role,
        suggested_risk=risk,
        suggested_specs="TBD",
        suggested_resources="TBD",
        marking_questions=questions_for(roles),
        subagents=agents,
        judge_notes=notes,
    )


def build_plan(conversion_plan: dict[str, Any], source_text: str, *, source_hld: str) -> dict[str, Any]:
    source_lines = source_text.splitlines()
    candidates = conversion_plan.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []

    items = [build_marking_item(item, source_lines) for item in candidates if isinstance(item, dict)]

    return {
        "schema_version": 1,
        "status": "RAW_HLD_MARKING_REQUIRED",
        "source_hld": source_hld,
        "purpose": (
            "Mark raw HLD sections with product, architecture, interface, data, processing, "
            "governance, security, and operations perspectives before conversion."
        ),
        "rules": [
            "Do not convert raw HLD mechanically when section role/boundary is unclear.",
            "Use bounded product and architecture perspectives to mark each candidate section.",
            "Ask only real checkpoint questions when interpretation affects split/role/dependency/constitution.",
            "Do not create SpecKit specs during marking.",
            "Do not modify the source HLD.",
        ],
        "subagent_contract": {
            "judge_orchestrator": "Owns final marking decisions, human questions, and source-HLD safety.",
            "bounded_subagents": [
                "product_reviewer",
                "architecture_reviewer",
                "interface_contract_reviewer",
                "data_state_reviewer",
                "processing_behavior_reviewer",
                "governance_reviewer",
                "security_reviewer",
                "operations_reviewer",
            ],
            "context_rule": (
                "Each subagent receives only the candidate section, relevant prior decisions, "
                "and its perspective questions."
            ),
        },
        "items": [asdict(item) for item in items],
    }


def render_md(plan: dict[str, Any]) -> str:
    lines = [
        "# Raw HLD Marking Plan",
        "",
        "made by AI",
        "",
        f"Status: `{plan['status']}`",
        "",
        "## Purpose",
        "",
        str(plan["purpose"]),
        "",
        "## Rules",
        "",
    ]

    for rule in plan["rules"]:
        lines.append(f"- {rule}")

    lines += [
        "",
        "## Subagent Contract",
        "",
        f"- judge/orchestrator: {plan['subagent_contract']['judge_orchestrator']}",
        f"- context rule: {plan['subagent_contract']['context_rule']}",
        "",
        "Bounded subagents:",
    ]

    for agent in plan["subagent_contract"]["bounded_subagents"]:
        lines.append(f"- `{agent}`")

    lines += ["", "## Candidate Marking Items", ""]

    for item in plan["items"]:
        lines += [
            f"### {item['candidate_id']} - {item['title']}",
            "",
            f"- source lines: {item['source_line_start']}-{item['source_line_end']}",
            f"- conversion action: `{item['current_conversion_action']}`",
            f"- primary role: `{item['primary_role']}`",
            f"- suggested roles: {', '.join(item['suggested_roles'])}",
            f"- suggested risk: `{item['suggested_risk']}`",
            f"- suggested specs: `{item['suggested_specs']}`",
            f"- suggested resources: `{item['suggested_resources']}`",
            f"- subagents: {', '.join(item['subagents'])}",
            "",
            "Questions:",
        ]
        for question in item["marking_questions"]:
            lines.append(f"- {question}")
        if item["judge_notes"]:
            lines += ["", "Judge notes:"]
            for note in item["judge_notes"]:
                lines.append(f"- {note}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_prompt(plan: dict[str, Any]) -> str:
    return (
        "# Raw HLD Marking Prompt\n\n"
        "made by AI\n\n"
        "Act as the HLDspec judge/orchestrator.\n\n"
        "Goal:\n"
        "Mark the raw HLD before conversion using bounded product and architecture perspectives.\n\n"
        "Inputs:\n"
        "- raw HLD source\n"
        "- HLD conversion plan\n"
        "- raw HLD marking plan\n\n"
        "Rules:\n"
        "- Do not modify the source HLD.\n"
        "- Do not invoke SpecKit.\n"
        "- Do not create final specs manually.\n"
        "- Use bounded subagents only for candidate sections and perspective questions.\n"
        "- Ask the human only real checkpoint questions.\n"
        "- Final output should guide HLD metadata: HLD-ROLE, HLD-RISK, HLD-SPECS, HLD-RESOURCES, HLD-VERIFY, refs, split/keep decisions.\n\n"
        "Open:\n"
        f"- {plan['source_hld']}\n"
        "- .specify/sync/hld_conversion_plan.md\n"
        "- .specify/sync/raw_hld_marking_plan.md\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a product/architecture marking plan for raw HLD conversion.")
    parser.add_argument("conversion_plan_json")
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", required=True)
    args = parser.parse_args()

    conversion_plan_path = Path(args.conversion_plan_json)
    workspace = Path(args.workspace)
    source_hld_path = Path(args.source_hld)

    conversion_plan = json.loads(conversion_plan_path.read_text(encoding="utf-8"))
    source_text = source_hld_path.read_text(encoding="utf-8", errors="replace")

    plan = build_plan(conversion_plan, source_text, source_hld=str(source_hld_path))
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "raw_hld_marking_plan.json"
    md_path = out_dir / "raw_hld_marking_plan.md"
    prompt_path = workspace / "RAW_HLD_MARKING_PROMPT.md"

    json_path.write_text(json.dumps(plan, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(plan), encoding="utf-8")
    prompt_path.write_text(render_prompt(plan), encoding="utf-8")

    print("Raw HLD marking plan written:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- prompt: {prompt_path}")
    print(f"- items: {len(plan['items'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
