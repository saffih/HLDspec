#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any


SPLITTABLE_RESPONSIBILITIES = {
    "data_state": {
        "suffix": "Data and State Ownership",
        "layer": "data",
        "depends_on_extra": [],
    },
    "processing": {
        "suffix": "Use Logic and Orchestration",
        "layer": "processing",
        "depends_on_extra": ["data_state"],
    },
    "api_contract": {
        "suffix": "API Contract",
        "layer": "api",
        "depends_on_extra": ["data_state", "processing"],
    },
    "operations": {
        "suffix": "Operations and Failure Handling",
        "layer": "operations",
        "depends_on_extra": ["processing", "api_contract"],
    },
    "testing": {
        "suffix": "Validation and Testing",
        "layer": "testing",
        "depends_on_extra": ["api_contract", "processing"],
    },
}

RESPONSIBILITY_ORDER = [
    "data_state",
    "processing",
    "api_contract",
    "operations",
    "testing",
]


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object JSON: {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def clean_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "planned-spec"


def queue_hash(queue: dict[str, Any]) -> str:
    relevant = {
        "questions": [
            {
                "question_id": q.get("question_id"),
                "planned_spec_id": q.get("planned_spec_id"),
                "title": q.get("title"),
                "human_decision": q.get("human_decision"),
                "human_notes": q.get("human_notes", ""),
            }
            for q in as_list(queue.get("questions"))
            if isinstance(q, dict)
        ]
    }
    payload = json.dumps(relevant, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def open_questions(queue: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        q for q in as_list(queue.get("questions"))
        if isinstance(q, dict)
        and bool(q.get("blocking", True))
        and str(q.get("human_decision", "TBD")) == "TBD"
    ]


def answered_split_questions(queue: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        q for q in as_list(queue.get("questions"))
        if isinstance(q, dict)
        and str(q.get("human_decision", "TBD")) == "SPLIT_PLANNED_SPEC"
        and q.get("planned_spec_id")
        and str(q.get("planned_spec_id")) != "__PLAN_QUALITY__"
    ]


def responsibility_ids(spec: dict[str, Any]) -> list[str]:
    responsibilities = [str(item) for item in as_list(spec.get("responsibility_mix"))]
    selected = [item for item in RESPONSIBILITY_ORDER if item in responsibilities]

    flags = set(str(flag) for flag in as_list(spec.get("quality_flags")))
    if "data_api_boundary_needs_review" in flags:
        for item in ("data_state", "api_contract"):
            if item not in selected:
                selected.append(item)
    if "api_processing_boundary_needs_review" in flags:
        for item in ("processing", "api_contract"):
            if item not in selected:
                selected.append(item)
    if "operations_processing_boundary_needs_review" in flags:
        for item in ("processing", "operations"):
            if item not in selected:
                selected.append(item)

    selected = [item for item in RESPONSIBILITY_ORDER if item in selected and item in SPLITTABLE_RESPONSIBILITIES]
    if len(selected) < 2:
        selected = ["data_state", "api_contract"]
    return selected


def child_spec_id(parent_id: str, responsibility: str, index: int) -> str:
    short = {
        "data_state": "data",
        "processing": "logic",
        "api_contract": "api",
        "operations": "ops",
        "testing": "test",
    }.get(responsibility, f"part{index}")
    return f"{parent_id}-{short}"


def make_child(parent: dict[str, Any], responsibility: str, parent_id: str, index: int) -> dict[str, Any]:
    meta = SPLITTABLE_RESPONSIBILITIES[responsibility]
    title = f"{parent.get('title', parent_id)} - {meta['suffix']}"
    cid = child_spec_id(parent_id, responsibility, index)

    child = copy.deepcopy(parent)
    child.update(
        {
            "planned_spec_id": cid,
            "slug": f"{cid}-{clean_slug(title)}",
            "title": title,
            "layer": meta["layer"],
            "quality_flags": [],
            "boundary_risk": "low",
            "requires_user_review": False,
            "responsibility_mix": [responsibility],
            "role_mix": as_list(parent.get("role_mix")),
            "layer_mix": [meta["layer"]],
            "decision": "FIX",
            "recommendation": "KEEP_SPEC",
            "user_decision_needed": "",
            "split_from_planned_spec_id": parent_id,
            "split_responsibility": responsibility,
            "decision_applied": "SPLIT_PLANNED_SPEC",
            "decision_application_reason": "Human accepted split checkpoint for a high-risk mixed-boundary planned spec.",
        }
    )

    child["coverage_expectations"] = [
        f"{source_id} HLD anchors and related refs for {meta['suffix']} are represented in this split spec."
        for source_id in as_list(parent.get("source_hld_sections"))
    ]

    if responsibility == "api_contract":
        child["api_contract_expectations"] = [
            "Caller-facing API/interface contract is defined without owning internal data/state mechanics."
        ]
        child["integration_expectations"] = [
            "Producer/consumer dependencies on lower-level data/state or logic specs are explicit."
        ]
    elif responsibility == "data_state":
        child["api_contract_expectations"] = []
        child["integration_expectations"] = [
            "Data/state ownership is specified as a lower-level dependency for API or logic specs."
        ]
    elif responsibility == "processing":
        child["api_contract_expectations"] = []
        child["integration_expectations"] = [
            "Use-logic/orchestration dependencies on data/state and API contracts are explicit."
        ]

    child["RunSkeptic_cycles"] = [
        {
            "framework": {
                "name": "RunSkeptic / Skeptic",
                "phase_flow_text": "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
            },
            "step": "spec_build_plan_decision_application",
            "key_aspects": [
                "spec_boundary",
                "spec_decomposition",
                "bottom_up_order",
                "api_contract",
                "data_state_ownership",
                "dependency_order",
            ],
            "spotlight": f"Apply human SPLIT_PLANNED_SPEC decision from {parent_id} into {cid}.",
            "decision": "FIX",
            "recommendation": "KEEP_SPEC",
            "evidence_levels": ["OBSERVED"],
            "verification": "Review spec_build_plan_review.md after applying decisions.",
            "outcome": "HANDLED",
        }
    ]
    return child


def split_parent_spec(parent: dict[str, Any]) -> list[dict[str, Any]]:
    parent_id = str(parent.get("planned_spec_id"))
    responsibilities = responsibility_ids(parent)

    children = [
        make_child(parent, responsibility, parent_id, index)
        for index, responsibility in enumerate(responsibilities, start=1)
    ]
    child_by_responsibility = {str(child["split_responsibility"]): child for child in children}

    original_deps = [str(dep) for dep in as_list(parent.get("depends_on_specs"))]
    for child in children:
        responsibility = str(child.get("split_responsibility"))
        deps = set(original_deps)
        for dep_responsibility in SPLITTABLE_RESPONSIBILITIES.get(responsibility, {}).get("depends_on_extra", []):
            dep_child = child_by_responsibility.get(dep_responsibility)
            if dep_child:
                deps.add(str(dep_child["planned_spec_id"]))
        deps.discard(str(child["planned_spec_id"]))
        child["depends_on_specs"] = sorted(deps)
        child["blocks_specs"] = []

    return children


def recompute_blocks(plan: dict[str, Any]) -> None:
    planned = [spec for spec in as_list(plan.get("planned_specs")) if isinstance(spec, dict)]
    by_id = {str(spec.get("planned_spec_id")): spec for spec in planned}
    for spec in planned:
        spec["blocks_specs"] = []
    for spec in planned:
        spec_id = str(spec.get("planned_spec_id"))
        for dep in [str(item) for item in as_list(spec.get("depends_on_specs"))]:
            if dep in by_id and spec_id not in as_list(by_id[dep].get("blocks_specs")):
                by_id[dep].setdefault("blocks_specs", []).append(spec_id)


def recompute_plan_quality(plan: dict[str, Any]) -> None:
    planned = [spec for spec in as_list(plan.get("planned_specs")) if isinstance(spec, dict)]
    findings: list[str] = []
    conflicts: list[str] = []
    cycles: list[dict[str, Any]] = []

    for spec in planned:
        spec_id = str(spec.get("planned_spec_id", "unknown"))
        flags = [str(item) for item in as_list(spec.get("quality_flags"))]
        boundary_risk = str(spec.get("boundary_risk", "low"))
        if flags:
            findings.append(f"{spec_id}: {', '.join(flags)}")
        if boundary_risk == "high":
            cycles.append(
                {
                    "step": "plan_quality_gate",
                    "spotlight": f"Is planned spec {spec_id} safe to use as a target-spec boundary?",
                    "decision": "DECOMPOSE",
                    "recommendation": "SPLIT_PLANNED_SPEC",
                    "evidence_levels": ["OBSERVED", "INFERRED_RISK"],
                    "outcome": "CONFLICT",
                }
            )

    if conflicts:
        decision = "CONFLICT"
        recommendation = "RESOLVE_CONFLICT"
    elif any(str(spec.get("boundary_risk", "low")) == "high" for spec in planned):
        decision = "DECOMPOSE"
        recommendation = "SPLIT_PLANNED_SPEC"
    elif findings:
        decision = "FIX"
        recommendation = "REVIEW_PLAN"
    else:
        decision = "PASS"
        recommendation = "KEEP_PLAN"

    plan["plan_quality"] = {
        "decision": decision,
        "recommendation": recommendation,
        "findings": findings,
        "conflicts": conflicts,
        "RunSkeptic_cycles": cycles,
        "decision_application": "spec_build_plan_decisions_applied",
    }


def render_plan_md(plan: dict[str, Any], plan_path: Path) -> str:
    planned = [spec for spec in as_list(plan.get("planned_specs")) if isinstance(spec, dict)]
    quality = plan.get("plan_quality", {}) if isinstance(plan.get("plan_quality"), dict) else {}

    lines: list[str] = [
        "# Spec Build Plan",
        "",
        "",
        "",
        f"Source HLD: `{plan.get('source_hld', '')}`",
        f"Plan JSON: `{plan_path}`",
        f"Constitution action: `{plan.get('constitution_action', '')}`",
        "",
        "## Status",
        "",
        "Read-only plan artifact. Spec build plan decisions may be applied to this workspace plan, but no target specs are created.",
        "",
        "## Plan Quality Gate",
        "",
        f"- Decision: `{quality.get('decision', '')}`",
        f"- Recommendation: `{quality.get('recommendation', '')}`",
        "",
    ]

    findings = [str(item) for item in as_list(quality.get("findings"))]
    if findings:
        lines += ["Findings:", ""]
        lines += [f"- {item}" for item in findings]
        lines.append("")

    lines += ["## Recommended order", ""]
    for spec_id in as_list(plan.get("recommended_order")):
        spec = next((item for item in planned if str(item.get("planned_spec_id")) == str(spec_id)), None)
        if spec:
            lines.append(f"- `{spec_id}` {spec.get('title')} ({spec.get('layer')})")
    lines.append("")

    lines += ["## Planned specs", ""]
    for spec in planned:
        flags = [str(item) for item in as_list(spec.get("quality_flags"))]
        lines += [
            f"### {spec.get('planned_spec_id')} - {spec.get('title')}",
            "",
            f"- Slug: `{spec.get('slug', '')}`",
            f"- Layer: `{spec.get('layer', '')}`",
            f"- Source HLD Sections: {', '.join(str(x) for x in as_list(spec.get('source_hld_sections'))) or 'none'}",
            f"- Depends on specs: {', '.join(str(x) for x in as_list(spec.get('depends_on_specs'))) or 'none'}",
            f"- Blocks specs: {', '.join(str(x) for x in as_list(spec.get('blocks_specs'))) or 'none'}",
            f"- Skeptic decision: `{spec.get('decision', '')}`",
            f"- Spec recommendation: `{spec.get('recommendation', '')}`",
            f"- Quality flags: {', '.join(flags) or 'none'}",
            f"- Boundary risk: `{spec.get('boundary_risk', 'low')}`",
            f"- Requires user review: `{str(bool(spec.get('requires_user_review'))).lower()}`",
            f"- Responsibility mix: {', '.join(str(x) for x in as_list(spec.get('responsibility_mix'))) or 'none'}",
            "",
        ]
        if spec.get("split_from_planned_spec_id"):
            lines += [
                f"- Split from planned spec: `{spec.get('split_from_planned_spec_id')}`",
                f"- Split responsibility: `{spec.get('split_responsibility')}`",
                "",
            ]
        lines += ["Coverage expectations:"]
        for expectation in as_list(spec.get("coverage_expectations")):
            lines.append(f"- {expectation}")
        lines.append("")

    lines += [
        "## Next safe steps",
        "",
        "1. Review `spec_build_plan_review.md` and confirm the decision queue is fully resolved.",
        "2. If the plan is not green, fix the plan inputs and rerun this decision step before anything else.",
        "3. If the plan is green, run `scripts/build_speckit_bundle_prompts.py <workspace>`.",
        "4. Immediately after bundle prompts, run `scripts/write_agent_context_handoff.py <workspace>` so the runtime root files stay in sync.",
        "5. Continue only to SpecKit prework human approval when the plan gate is green and the handoff file exists.",
        "",
    ]
    return "\n".join(lines)


def apply_decisions(workspace: Path) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    queue_path = sync / "spec_build_plan_decision_queue.json"
    plan_path = sync / "spec_build_plan.json"
    md_path = sync / "spec_build_plan.md"
    applied_path = sync / "spec_build_plan_decisions_applied.json"

    if not queue_path.exists():
        raise SystemExit(f"Missing decision queue: {queue_path}")
    if not plan_path.exists():
        raise SystemExit(f"Missing spec build plan: {plan_path}")

    queue = load_json(queue_path)
    unanswered = open_questions(queue)
    if unanswered:
        ids = ", ".join(str(q.get("question_id")) for q in unanswered)
        raise SystemExit(f"Cannot apply spec build plan decisions while questions are still TBD: {ids}")

    split_questions = answered_split_questions(queue)
    if not split_questions:
        result = {
            "status": "NO_APPLICABLE_SPEC_PLAN_DECISIONS",
            "workspace": str(workspace),
            "queue_path": str(queue_path),
            "plan_path": str(plan_path),
            "split_applied_count": 0,
        }
        write_json(applied_path, result)
        return result

    current_hash = queue_hash(queue)
    if applied_path.exists():
        previous = load_json(applied_path)
        if previous.get("queue_hash") == current_hash and previous.get("status") == "SPEC_PLAN_DECISIONS_APPLIED":
            return previous

    plan = load_json(plan_path)
    planned = [spec for spec in as_list(plan.get("planned_specs")) if isinstance(spec, dict)]
    split_by_id = {str(q.get("planned_spec_id")): q for q in split_questions}

    new_planned: list[dict[str, Any]] = []
    split_map: dict[str, list[str]] = {}

    for spec in planned:
        spec_id = str(spec.get("planned_spec_id"))
        if spec_id in split_by_id:
            children = split_parent_spec(spec)
            split_map[spec_id] = [str(child["planned_spec_id"]) for child in children]
            new_planned.extend(children)
        else:
            new_planned.append(spec)

    for spec in new_planned:
        deps = []
        for dep in [str(item) for item in as_list(spec.get("depends_on_specs"))]:
            if dep in split_map:
                deps.extend(split_map[dep])
            else:
                deps.append(dep)
        spec_id = str(spec.get("planned_spec_id"))
        spec["depends_on_specs"] = sorted({dep for dep in deps if dep != spec_id})

    plan["planned_specs"] = new_planned

    old_order = [str(item) for item in as_list(plan.get("recommended_order"))]
    new_order: list[str] = []
    for spec_id in old_order:
        if spec_id in split_map:
            new_order.extend(split_map[spec_id])
        else:
            new_order.append(spec_id)
    existing_ids = {str(spec.get("planned_spec_id")) for spec in new_planned}
    for spec in new_planned:
        spec_id = str(spec.get("planned_spec_id"))
        if spec_id not in new_order:
            new_order.append(spec_id)
    plan["recommended_order"] = [spec_id for spec_id in new_order if spec_id in existing_ids]

    recompute_blocks(plan)
    recompute_plan_quality(plan)

    write_json(plan_path, plan)
    md_path.write_text(render_plan_md(plan, plan_path), encoding="utf-8")

    result = {
        "status": "SPEC_PLAN_DECISIONS_APPLIED",
        "workspace": str(workspace),
        "queue_path": str(queue_path),
        "queue_hash": current_hash,
        "plan_path": str(plan_path),
        "plan_md_path": str(md_path),
        "split_applied_count": len(split_map),
        "split_map": split_map,
        "plan_quality": plan.get("plan_quality", {}),
    }
    write_json(applied_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply answered spec build plan decisions to workspace plan artifacts.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    result = apply_decisions(workspace)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
