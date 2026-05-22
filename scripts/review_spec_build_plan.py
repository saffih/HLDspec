#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BLOCKING_DECISIONS = {"CONFLICT", "DECOMPOSE"}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def markdown_list(items: list[Any], *, empty: str = "none") -> list[str]:
    if not items:
        return [f"- {empty}"]
    return [f"- {item}" for item in items]


def spec_action(spec: dict[str, Any]) -> str:
    flags = set(str(flag) for flag in as_list(spec.get("quality_flags")))
    risk = str(spec.get("boundary_risk", "low"))

    if not flags:
        return "Keep as planned for now. Recheck after target-spec support exists."

    if risk == "high":
        return (
            "Do not generate this as one target spec yet. Review whether to split by "
            "capability, layer, API contract, data/state ownership, processing, or operations."
        )

    return "Review before target-spec. The plan may be usable after the flagged concern is resolved."


def decision_questions(spec: dict[str, Any]) -> list[str]:
    spec_id = str(spec.get("planned_spec_id", "?"))
    flags = set(str(flag) for flag in as_list(spec.get("quality_flags")))
    questions: list[str] = []

    if "mixed_layers" in flags:
        questions.append(
            f"Should planned spec {spec_id} be split because it combines multiple bottom-up layers?"
        )
    if "mixed_hld_roles" in flags:
        questions.append(
            f"Should planned spec {spec_id} be split because it combines multiple HLD roles?"
        )
    if "mixed_responsibilities" in flags:
        questions.append(
            f"Should planned spec {spec_id} be split because it combines multiple responsibility groups?"
        )
    if "api_processing_boundary_needs_review" in flags:
        questions.append(
            f"Should planned spec {spec_id} separate the API/interface contract from processing behavior?"
        )
    if "data_api_boundary_needs_review" in flags:
        questions.append(
            f"Should planned spec {spec_id} separate data/state ownership from the API contract?"
        )
    if "operations_processing_boundary_needs_review" in flags:
        questions.append(
            f"Should planned spec {spec_id} separate failure/recovery operations from core processing?"
        )
    if "explicit_hld_specs_needs_review" in flags:
        questions.append(
            f"Should the HLD-SPECS mapping for planned spec {spec_id} be revised before generating specs?"
        )
    if "performance_expectation_missing" in flags:
        questions.append(
            f"What performance/scalability expectation must planned spec {spec_id} preserve?"
        )
    if "memory_expectation_missing" in flags:
        questions.append(
            f"What memory/context-size expectation must planned spec {spec_id} preserve?"
        )
    if "high_risk_missing_verify" in flags:
        questions.append(
            f"What HLD-VERIFY evidence is required before planned spec {spec_id} can proceed?"
        )
    if "conflict_refs_present" in flags:
        questions.append(
            f"Which side of the HLD conflict should planned spec {spec_id} follow?"
        )

    return questions


def build_review(plan: dict[str, Any], plan_path: Path) -> str:
    quality = plan.get("plan_quality")
    if not isinstance(quality, dict):
        quality = {
            "decision": "CONFLICT",
            "recommendation": "RESOLVE_CONFLICT",
            "findings": ["Plan has no plan_quality object."],
            "conflicts": ["Plan Quality Gate did not run."],
            "RunSkeptic_cycles": [],
        }

    planned_specs = [spec for spec in as_list(plan.get("planned_specs")) if isinstance(spec, dict)]
    flagged_specs = [spec for spec in planned_specs if as_list(spec.get("quality_flags"))]
    conflicts = as_list(quality.get("conflicts"))
    findings = as_list(quality.get("findings"))
    decision = str(quality.get("decision", "CONFLICT"))
    recommendation = str(quality.get("recommendation", "RESOLVE_CONFLICT"))

    can_continue_readonly = True
    can_continue_target_spec = decision not in BLOCKING_DECISIONS and not flagged_specs and not conflicts

    lines: list[str] = [
        "# Spec Build Plan Review",
        "",
        "made by AI",
        "",
        f"Plan: `{plan_path}`",
        "",
        "## Summary",
        "",
        f"- Plan Quality decision: `{decision}`",
        f"- Recommendation: `{recommendation}`",
        f"- Planned specs: `{len(planned_specs)}`",
        f"- Flagged specs: `{len(flagged_specs)}`",
        f"- Conflicts: `{len(conflicts)}`",
        "",
        "## Can continue?",
        "",
        f"- Continue read-only review cycle: `{str(can_continue_readonly).lower()}`",
        f"- Continue to target-spec generation: `{str(can_continue_target_spec).lower()}`",
        "",
    ]

    if not can_continue_target_spec:
        lines.extend(
            [
                "Target-spec generation should remain blocked until the flagged plan issues are resolved.",
                "",
            ]
        )

    lines.extend(["## Plan Quality findings", ""])
    lines.extend(markdown_list([str(item) for item in findings]))
    lines.append("")

    lines.extend(["## Plan Quality conflicts", ""])
    lines.extend(markdown_list([str(item) for item in conflicts]))
    lines.append("")

    lines.extend(["## Planned spec review", ""])
    for spec in planned_specs:
        spec_id = str(spec.get("planned_spec_id", "?"))
        title = str(spec.get("title", "Untitled"))
        flags = [str(flag) for flag in as_list(spec.get("quality_flags"))]
        questions = decision_questions(spec)

        lines.extend(
            [
                f"### {spec_id} - {title}",
                "",
                f"- Layer: `{spec.get('layer', '')}`",
                f"- Boundary risk: `{spec.get('boundary_risk', 'low')}`",
                f"- Requires user review: `{str(bool(spec.get('requires_user_review'))).lower()}`",
                f"- Source HLD Sections: `{', '.join(str(x) for x in as_list(spec.get('source_hld_sections'))) or 'none'}`",
                f"- Depends on specs: `{', '.join(str(x) for x in as_list(spec.get('depends_on_specs'))) or 'none'}`",
                f"- Quality flags: `{', '.join(flags) or 'none'}`",
                "",
                "Action:",
                "",
                f"- {spec_action(spec)}",
                "",
                "Decision questions:",
                "",
            ]
        )
        lines.extend(markdown_list(questions))
        lines.append("")

    lines.extend(
        [
            "## Recommended first-run loop",
            "",
            "1. Read this review.",
            "2. Open `spec_build_plan.md` for context.",
            "3. For each flagged spec, decide whether the HLD-SPECS mapping is valid or should split.",
            "4. Edit the working HLD if needed.",
            "5. Re-run `scripts/first_run_readonly.sh`.",
            "6. Do not use target-spec generation until Plan Quality is clean or explicitly accepted.",
            "",
            "## Important",
            "",
            "- This review is read-only.",
            "- It does not create specs.",
            "- It does not create the target Spec Kit Constitution.",
            "- It does not call an agent.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review HLDspec spec_build_plan.json and write an actionable markdown report.")
    parser.add_argument("plan_json", nargs="?", default=".specify/sync/spec_build_plan.json")
    parser.add_argument("--output", default=None, help="Output markdown path. Defaults to spec_build_plan_review.md next to the plan JSON.")
    parser.add_argument("--strict", action="store_true", help="Exit 2 when the plan has CONFLICT/DECOMPOSE or flagged specs.")
    args = parser.parse_args()

    plan_path = Path(args.plan_json).resolve()
    plan = json.loads(plan_path.read_text(encoding="utf-8"))

    output_path = Path(args.output).resolve() if args.output else plan_path.with_name("spec_build_plan_review.md")
    output_path.write_text(build_review(plan, plan_path), encoding="utf-8")

    quality = plan.get("plan_quality", {})
    decision = str(quality.get("decision", "CONFLICT")) if isinstance(quality, dict) else "CONFLICT"
    planned_specs = [spec for spec in as_list(plan.get("planned_specs")) if isinstance(spec, dict)]
    flagged_specs = [spec for spec in planned_specs if as_list(spec.get("quality_flags"))]

    print(f"Review written: {output_path}")
    print(f"Plan quality: {decision}")
    print(f"Planned specs: {len(planned_specs)}")
    print(f"Flagged specs: {len(flagged_specs)}")

    if args.strict and (decision in BLOCKING_DECISIONS or flagged_specs):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
