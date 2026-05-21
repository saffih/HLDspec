#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def build_package(workspace: Path) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    state = load_json(sync / "hldspec_state.json")
    constitution = load_json(sync / "constitution_update_plan.json")
    graph = load_json(sync / "feature_dependency_graph.json")
    quality = load_json(sync / "speckit_prework_quality_review.json")
    dossier = load_json(sync / "speckit_proxy_dossier.json")

    findings = as_list(quality.get("findings"))
    blockers = [f for f in findings if isinstance(f, dict) and str(f.get("severity", "")).upper() == "BLOCKER"]
    active = dossier.get("selected_feature", {}) if isinstance(dossier.get("selected_feature"), dict) else {}
    first = quality.get("case_to_present", {}).get("first_feature_case", {}) if isinstance(quality.get("case_to_present"), dict) else {}

    return {
        "schema_version": 1,
        "status": "REWORK_REQUIRED" if blockers else "PENDING_HUMAN_REVIEW",
        "purpose": "single human-facing package for reviewing SpecKit prework before SpecKit invocation",
        "state": {
            "current_stage": state.get("current_stage", ""),
            "current_checkpoint": state.get("current_checkpoint", ""),
        },
        "constitution_case": {
            "claim": "The constitution must protect HLD architecture before SpecKit creates feature artifacts.",
            "rules": as_list(constitution.get("required_rules")),
        },
        "dependency_case": {
            "claim": "Features should be invoked bottom-up from independent foundations to dependents.",
            "bottom_up_order": as_list(graph.get("bottom_up_order")),
            "edges": as_list(graph.get("edges")),
        },
        "first_feature_case": first or active,
        "active_proxy_feature": active,
        "beskeptic_findings": findings,
        "feedback_impact_rules": quality.get("affected_artifact_policy", {}),
        "controlling_artifacts": [
            ".specify/sync/hldspec_state.md",
            ".specify/sync/speckit_prework_package.md",
            ".specify/sync/speckit_prework_quality_review.md",
            ".specify/sync/speckit_proxy_dossier.md",
            ".specify/sync/speckit_invocation_queue.md",
            ".specify/sync/constitution_update_plan.md",
            ".specify/sync/feature_dependency_graph.md",
        ],
        "supporting_artifacts": [
            ".specify/sync/speckit_input_manifest.md",
            ".specify/sync/spec_build_plan.md",
            ".specify/sync/spec_build_plan_review.md",
        ],
        "legacy_supporting_artifacts": [
            ".specify/sync/target_spec_work_order.md",
            ".specify/sync/spec_branch_queue.md",
        ],
        "human_checkpoint": {
            "question": "Do you approve the constitution, dependency order, first feature, and SpecKit proxy handoff?",
            "options": ["APPROVE_PLAN", "MODIFY_PLAN", "DECOMPOSE_MORE", "FIX_CONSTITUTION", "REBUILD_DEPENDENCY_GRAPH"],
            "human_decision": "TBD",
        },
    }


def render_md(pkg: dict[str, Any]) -> str:
    first = pkg.get("first_feature_case", {}) if isinstance(pkg.get("first_feature_case"), dict) else {}
    active = pkg.get("active_proxy_feature", {}) if isinstance(pkg.get("active_proxy_feature"), dict) else {}

    lines = [
        "# SpecKit Prework Package",
        "",
        "made by AI",
        "",
        f"Status: `{pkg['status']}`",
        f"Purpose: {pkg['purpose']}",
        "",
        "## Where we are",
        "",
        f"- current stage: `{pkg['state'].get('current_stage', '')}`",
        f"- checkpoint: `{pkg['state'].get('current_checkpoint', '')}`",
        "- HLDspec has prepared SpecKit inputs but must not invoke SpecKit until this package is approved.",
        "",
        "## Constitution case",
        "",
        pkg["constitution_case"]["claim"],
        "",
        "Proposed rules:",
    ]

    rules = pkg["constitution_case"].get("rules", [])
    if not rules:
        lines.append("- No constitution rules found. This requires rework.")
    for rule in rules:
        if isinstance(rule, dict):
            lines.append(f"- `{rule.get('rule_id', '')}` {rule.get('name', '')}: {rule.get('rule', '')}")

    lines += [
        "",
        "## Architecture and dependency case",
        "",
        pkg["dependency_case"]["claim"],
        "",
        "Bottom-up order:",
    ]
    order = pkg["dependency_case"].get("bottom_up_order", [])
    if not order:
        lines.append("- No bottom-up order found. This requires review.")
    for idx, item in enumerate(order, start=1):
        lines.append(f"{idx}. `{item}`")

    lines += [
        "",
        "## First feature case",
        "",
        f"- feature: `{first.get('feature_id') or active.get('feature_id', '')}` - {first.get('feature_name') or active.get('feature_name', '')}",
        f"- why first: {first.get('why_first') or active.get('why_this_feature', '')}",
        f"- depends on: {', '.join(first.get('depends_on') or active.get('depends_on_features') or []) or 'none'}",
        "",
        "## SpecKit proxy handoff",
        "",
        f"- active feature: `{active.get('feature_id', '')}` - {active.get('feature_name', '')}",
        f"- short name: `{active.get('short_name', '')}`",
        "- proxy must use SpecKit in sequence: constitution if needed -> specify -> clarify -> plan -> tasks -> implement only after approval.",
        "",
        "## Beskeptic findings",
        "",
    ]

    findings = pkg.get("beskeptic_findings", [])
    if not findings:
        lines.append("No Beskeptic findings recorded.")
    for finding in findings:
        if not isinstance(finding, dict):
            continue
        lines += [
            f"### {finding.get('id', '')} - {finding.get('area', '')}",
            "",
            f"- severity: `{finding.get('severity', '')}`",
            f"- decision: `{finding.get('beskeptic_decision', '')}`",
            f"- finding: {finding.get('finding', '')}",
            f"- recommendation: {finding.get('recommendation', '')}",
            "",
        ]

    lines += [
        "## Feedback impact rules",
        "",
        "If you give feedback, the judge/orchestrator must rebuild affected artifacts instead of patching only this markdown file.",
        "",
    ]
    impact = pkg.get("feedback_impact_rules", {})
    if isinstance(impact, dict) and impact:
        for key, actions in impact.items():
            lines.append(f"### {key}")
            for action in as_list(actions):
                lines.append(f"- {action}")
            lines.append("")
    else:
        lines.append("- No feedback impact map found. Use Judge-Led Review Protocol defaults.")

    for title, key in [
        ("Controlling artifacts", "controlling_artifacts"),
        ("Supporting artifacts", "supporting_artifacts"),
        ("Legacy/supporting artifacts", "legacy_supporting_artifacts"),
    ]:
        lines += ["", f"## {title}", ""]
        if title == "Legacy/supporting artifacts":
            lines.append("These may exist for compatibility, but they are not the controlling handoff when SpecKit is available.")
        for artifact in pkg.get(key, []):
            lines.append(f"- `{artifact}`")

    checkpoint = pkg["human_checkpoint"]
    lines += [
        "",
        "## Human checkpoint",
        "",
        checkpoint["question"],
        "",
        "Options:",
    ]
    for option in checkpoint["options"]:
        lines.append(f"- {option}")
    lines += ["", "Human decision: `TBD`", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one human-facing SpecKit prework package.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    out = workspace / ".specify" / "sync"
    out.mkdir(parents=True, exist_ok=True)

    pkg = build_package(workspace)
    (out / "speckit_prework_package.json").write_text(json.dumps(pkg, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "speckit_prework_package.md").write_text(render_md(pkg), encoding="utf-8")

    print("SpecKit prework package generated:")
    print(f"- json: {out / 'speckit_prework_package.json'}")
    print(f"- report: {out / 'speckit_prework_package.md'}")
    print(f"- status: {pkg['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
