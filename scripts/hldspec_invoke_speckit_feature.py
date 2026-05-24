#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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
        if (candidate / "speckit_prework_approval.json").exists():
            return candidate
    return direct


def first_active_feature(queue: dict[str, Any]) -> dict[str, Any]:
    for item in as_list(queue.get("items")):
        if not isinstance(item, dict):
            continue
        if str(item.get("status", "")).upper() in {
            "PENDING_HUMAN_PLAN_REVIEW",
            "READY_FOR_SPECKIT_SPECIFY",
        }:
            return item
    items = [i for i in as_list(queue.get("items")) if isinstance(i, dict)]
    return items[0] if items else {}


def feature_dossier_entry(dossier: dict[str, Any], feature_id: str) -> dict[str, Any]:
    for spec in as_list(dossier.get("specs")):
        if isinstance(spec, dict) and str(spec.get("planned_spec_id")) == feature_id:
            return spec
    return {}


def render_prompt(
    feature: dict[str, Any],
    entry: dict[str, Any],
    constitution_rules: list[dict[str, Any]],
) -> str:
    fid = str(feature.get("feature_id", "unknown"))
    fname = str(feature.get("feature_name", fid))
    specify_input = str(feature.get("speckit_specify_input", "")).strip()
    depends = ", ".join(str(x) for x in as_list(feature.get("depends_on_features"))) or "none"
    source_sections = ", ".join(str(x) for x in as_list(feature.get("source_hld_sections"))) or "TBD"

    provides = ", ".join(str(x) for x in as_list(entry.get("provides"))) or "TBD"
    owns = ", ".join(str(x) for x in as_list(entry.get("owns"))) or "TBD"
    sot = str(entry.get("source_of_truth_or_TBD", "TBD"))
    pm_value = str(entry.get("pm_value", "TBD"))
    failure_fallbacks = as_list(entry.get("failure_fallbacks"))

    interfaces = as_list(entry.get("interfaces"))
    integration_paths = as_list(entry.get("integration_paths"))

    lines = [
        "# SpecKit Proxy Agent Prompt",
        "",
        "",
        "",
        f"Feature: `{fid}` — {fname}",
        f"Source HLD sections: {source_sections}",
        f"Depends on: {depends}",
        "",
        "## Constitution rules you must enforce",
        "",
        "The following rules govern ALL SpecKit artifacts you create.",
        "Specs, plans, and tasks must not contradict these rules.",
        "",
    ]
    for rule in constitution_rules:
        if isinstance(rule, dict):
            lines.append(f"- **{rule.get('rule_id', '?')} {rule.get('name', '')}**: {rule.get('rule', '')}")
    lines += [
        "",
        "## Step 1 — Run /speckit.specify",
        "",
        "Use the input below verbatim:",
        "",
        "```text",
        specify_input,
        "```",
        "",
        "## Step 2 — Run /speckit.clarify if markers remain",
        "",
        "After specify, check for unresolved markers or clarification requests.",
        "For each clarification question:",
        "",
        "1. Look up the answer in the evidence sources listed below.",
        "2. If found with non-TBD values → answer from evidence (record source).",
        "3. If found but values are TBD → ESCALATE_TO_HUMAN, do not guess.",
        "4. If not found → ESCALATE_TO_HUMAN.",
        "",
        "You may run:",
        "```bash",
        f"python3 scripts/lookup_speckit_clarify_answer.py <workspace> \"<question>\"",
        "```",
        "",
        "## Evidence sources for this feature",
        "",
        f"- PM value: {pm_value}",
        f"- Provides: {provides}",
        f"- Owns: {owns}",
        f"- Source of truth: {sot}",
    ]

    if interfaces:
        lines += ["", "Interface contracts:"]
        for iface in interfaces[:5]:
            if isinstance(iface, dict):
                lines.append(f"  - {iface.get('contract_name', '?')}: provider={iface.get('provider', 'TBD')}, consumer={iface.get('consumer', 'TBD')}")

    if integration_paths:
        lines += ["", "Integration paths:"]
        for path_item in integration_paths[:3]:
            if isinstance(path_item, dict):
                lines.append(f"  - {path_item.get('name', '?')}: {', '.join(as_list(path_item.get('path_or_flow', [])))[:120]}")

    if failure_fallbacks and failure_fallbacks != ["TBD"]:
        lines += ["", "Failure/fallback notes:"]
        for fb in failure_fallbacks[:4]:
            lines.append(f"  - {fb}")

    lines += [
        "",
        "## Stop boundary",
        "",
        "- Do NOT run /speckit.tasks without explicit judge approval.",
        "- Do NOT run /speckit.implement under any circumstances.",
        "- Do NOT modify the source HLD.",
        "- Do NOT create specs for other features.",
        "",
        "## Report format",
        "",
        "After completing specify + clarify:",
        "",
        "```",
        "files_created: [list]",
        "files_changed: [list]",
        "questions_answered_from_evidence: [list with source]",
        "questions_escalated: [list with reason]",
        "ready_for_plan: yes/no",
        "blockers: [list or none]",
        "```",
        "",
    ]
    return "\n".join(lines)


def build_prompt(workspace: Path) -> dict[str, Any]:
    sync = find_sync(workspace)

    approval = load_json(sync / "speckit_prework_approval.json")
    if str(approval.get("status", "")).upper() != "APPROVED":
        raise ValueError(
            "SpecKit prework is not approved. Run approve_hldspec_prework.py with APPROVE_PLAN first."
        )

    quality = load_json(sync / "speckit_prework_quality_review.json")
    blockers = [
        f for f in as_list(quality.get("findings"))
        if isinstance(f, dict) and str(f.get("severity", "")).upper() == "BLOCKER"
    ]
    if blockers:
        ids = [str(b.get("id", "?")) for b in blockers]
        raise ValueError(
            f"Cannot generate invoke prompt: {len(blockers)} BLOCKER finding(s) unresolved: {', '.join(ids)}"
        )

    queue = load_json(sync / "speckit_invocation_queue.json")
    feature = first_active_feature(queue)
    if not feature:
        raise ValueError("No active feature found in speckit_invocation_queue.json.")

    feature_id = str(feature.get("feature_id", ""))
    dossier = load_json(sync / "speckit_answer_dossier.json")
    entry = feature_dossier_entry(dossier, feature_id)

    constitution = load_json(sync / "constitution_update_plan.json")
    rules = [r for r in as_list(constitution.get("required_rules")) if isinstance(r, dict)]

    prompt_text = render_prompt(feature, entry, rules)
    out_path = sync / f"speckit_invoke_prompt_{feature_id}.md"
    out_path.write_text(prompt_text, encoding="utf-8")

    return {
        "workspace": str(workspace),
        "feature_id": feature_id,
        "feature_name": str(feature.get("feature_name", "")),
        "prompt_path": str(out_path),
        "constitution_rules": len(rules),
        "status": "PROMPT_READY",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a bounded SpecKit proxy agent prompt for the active feature."
    )
    parser.add_argument("workspace")
    args = parser.parse_args()

    try:
        result = build_prompt(Path(args.workspace).resolve())
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print("SpecKit invoke prompt generated:")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
