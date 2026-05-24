#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def has_tbd_questions(path: Path) -> bool:
    data = load_json(path)
    for q in data.get("questions", []):
        if isinstance(q, dict) and q.get("blocking", True) and str(q.get("human_decision", "TBD")) == "TBD":
            return True
    checkpoint = data.get("human_checkpoint")
    return isinstance(checkpoint, dict) and str(checkpoint.get("human_decision", "TBD")) == "TBD"


def count_tbd(path: Path) -> int:
    data = load_json(path)
    questions = data.get("questions", [])
    if isinstance(questions, list):
        return sum(
            1
            for q in questions
            if isinstance(q, dict) and q.get("blocking", True) and str(q.get("human_decision", "TBD")) == "TBD"
        )
    checkpoint = data.get("human_checkpoint")
    return 1 if isinstance(checkpoint, dict) and str(checkpoint.get("human_decision", "TBD")) == "TBD" else 0


def hld_is_converted(path: Path) -> bool:
    if not path.exists():
        return False
    return bool(re.search(r"^## HLD-\d{3}[A-Z]? - ", path.read_text(encoding="utf-8", errors="replace"), re.M))


def has_first_run_artifacts(workspace: Path) -> bool:
    sync = workspace / ".specify" / "sync"
    required = [
        "spec_build_plan.json",
        "spec_build_plan_review.md",
        "speckit_prework_quality_review.json",
        "speckit_prework_package.md",
    ]
    return any((sync / name).exists() for name in required)


def plan_green(review_path: Path, plan_path: Path) -> tuple[bool, dict[str, Any]]:
    plan = load_json(plan_path)
    pq = plan.get("plan_quality", {}) if isinstance(plan, dict) else {}
    if not isinstance(pq, dict):
        pq = {}

    specs = plan.get("planned_specs", []) if isinstance(plan, dict) else []
    flagged = [
        s.get("planned_spec_id")
        for s in specs
        if isinstance(s, dict) and (s.get("quality_flags") or s.get("requires_user_review"))
    ] if isinstance(specs, list) else []
    conflicts = pq.get("conflicts", [])

    text = review_path.read_text(encoding="utf-8", errors="replace") if review_path.exists() else ""
    allowed = bool(re.search(r"Continue to target-spec generation:\s*`?true`?", text, re.I))
    blocked = bool(re.search(r"Continue to target-spec generation:\s*`?false`?", text, re.I))

    green = (
        allowed
        and not blocked
        and pq.get("decision") in {"PASS", "FIX", "HANDLED"}
        and pq.get("recommendation") == "KEEP_PLAN"
        and not conflicts
        and not flagged
    )
    return green, {
        "decision": pq.get("decision", ""),
        "recommendation": pq.get("recommendation", ""),
        "planned_specs": len(specs) if isinstance(specs, list) else 0,
        "conflicts": len(conflicts) if isinstance(conflicts, list) else 0,
        "flagged_specs": len(flagged),
    }


def build_state(workspace: Path, source_hld: str) -> dict[str, Any]:
    sync = workspace / ".specify" / "sync"
    firstrun = workspace if has_first_run_artifacts(workspace) else workspace / "firstrun"
    fsync = firstrun / ".specify" / "sync"

    working_hld = workspace / "HLD.md"
    conversion_queue = sync / "hld_conversion_decision_queue.json"
    plan_review = fsync / "spec_build_plan_review.md"
    plan_json = fsync / "spec_build_plan.json"
    spec_queue = fsync / "spec_build_plan_decision_queue.json"
    prework_quality = fsync / "speckit_prework_quality_review.json"

    base: dict[str, Any] = {
        "schema_version": 1,
        "source_hld": source_hld,
        "workspace": str(workspace),
        "source_hld_modified": False,
        "working_hld_modified": working_hld.exists(),
        "current_stage": "UNKNOWN",
        "last_completed_stage": "",
        "current_checkpoint": "",
        "blocking_questions": [],
        "next_allowed_actions": [],
        "controlling_artifacts": [],
        "supporting_artifacts": [],
        "legacy_supporting_artifacts": [],
        "notes": [],
    }

    def finish(stage: str, checkpoint: str, last: str, actions: list[str], controlling: list[Path], supporting: list[Path] | None = None, legacy: list[Path] | None = None) -> dict[str, Any]:
        base["current_stage"] = stage
        base["current_checkpoint"] = checkpoint
        base["last_completed_stage"] = last
        base["next_allowed_actions"] = actions
        base["controlling_artifacts"] = [str(p) for p in controlling if p]
        base["supporting_artifacts"] = [str(p) for p in (supporting or []) if p]
        base["legacy_supporting_artifacts"] = [str(p) for p in (legacy or []) if p]
        return base

    if not working_hld.exists():
        return finish(
            "NO_WORKSPACE",
            "run_hldspec",
            "none",
            ["run scripts/hldspec_run.sh <source-HLD.md>"],
            [],
        )

    working_hld_converted = hld_is_converted(working_hld)

    if not working_hld_converted and conversion_queue.exists() and has_tbd_questions(conversion_queue):
        base["blocking_questions"] = [{"artifact": str(conversion_queue), "open_question_count": count_tbd(conversion_queue)}]
        return finish(
            "CONVERSION_CHECKPOINT",
            "hld_conversion_decisions",
            "raw_hld_format_report",
            [
                "run scripts/hldspec_question_guide.sh <workspace>",
                "judge presents hld_conversion_decision_queue.md",
                "human answers only listed split/keep questions",
                "judge updates hld_conversion_decision_queue.json",
                "rerun scripts/hldspec_run.sh",
            ],
            [sync / "hld_conversion_decision_queue.md", conversion_queue],
        )

    if not working_hld_converted:
        return finish(
            "CONVERSION_READY_TO_APPLY",
            "apply_working_hld_conversion",
            "hld_conversion_decisions_answered",
            ["apply conversion decisions to working HLD only", "rerun first_readonly on converted working HLD"],
            [conversion_queue],
        )

    if conversion_queue.exists() and has_tbd_questions(conversion_queue):
        base["notes"].append(
            "Ignored stale conversion queue because the working HLD is already in HLDspec format."
        )

    if not plan_review.exists():
        return finish(
            "FIRST_RUN_PENDING",
            "run_first_readonly",
            "working_hld_converted",
            ["run first_run_readonly.sh on converted working HLD"],
            [working_hld],
        )

    green, summary = plan_green(plan_review, plan_json)
    base["plan_summary"] = summary

    if spec_queue.exists() and has_tbd_questions(spec_queue):
        base["blocking_questions"] = [{"artifact": str(spec_queue), "open_question_count": count_tbd(spec_queue)}]
        return finish(
            "SPEC_BUILD_PLAN_CHECKPOINT",
            "spec_build_plan_decisions",
            "spec_build_plan_review",
            [
                "run scripts/hldspec_question_guide.sh <workspace>",
                "judge presents spec_build_plan_decision_queue.md",
                "human answers listed plan questions",
                "judge reruns hldspec",
            ],
            [fsync / "spec_build_plan_decision_queue.md", spec_queue, plan_review],
        )

    if not green:
        return finish(
            "SPEC_BUILD_PLAN_BLOCKED",
            "fix_or_decompose_spec_build_plan",
            "spec_build_plan_review",
            ["review spec_build_plan_review.md", "fix working HLD/HLD-SPECS mapping or answer spec-plan queue", "rerun first_readonly"],
            [plan_review, plan_json],
        )

    if not prework_quality.exists():
        return finish(
            "SPECKIT_PREWORK_MISSING",
            "generate_speckit_prework",
            "green_spec_build_plan",
            ["rerun first_readonly to generate SpecKit prework artifacts"],
            [plan_review, plan_json],
        )

    quality = load_json(prework_quality)
    findings = quality.get("findings", [])
    blockers = [f for f in findings if isinstance(f, dict) and str(f.get("severity", "")).upper() == "BLOCKER"]
    if quality.get("status") == "REWORK_REQUIRED" or blockers:
        return finish(
            "SPECKIT_PREWORK_REWORK_REQUIRED",
            "rebuild_speckit_prework",
            "speckit_prework_quality_review",
            ["present speckit_prework_quality_review.md", "rebuild affected artifacts", "rerun quality review"],
            [fsync / "speckit_prework_quality_review.md", prework_quality],
        )

    base["notes"] = [
        "target_spec_work_order and spec_branch_queue may exist for compatibility but do not control the flow when SpecKit is available."
    ]
    return finish(
        "SPECKIT_PREWORK_APPROVAL_GATE",
        "human_approves_speckit_prework",
        "speckit_proxy_dossier_ready",
        [
            "judge presents speckit_prework_package.md",
            "judge explains constitution case, dependency case, first-feature case, Skeptic findings",
            "human approves or requests modifications",
            "after approval, SpecKit proxy subagent invokes SpecKit in sequence",
        ],
        [fsync / "speckit_prework_package.md", fsync / "speckit_prework_quality_review.md", fsync / "speckit_proxy_dossier.md"],
        [fsync / "speckit_input_manifest.md", fsync / "speckit_invocation_queue.md", fsync / "constitution_update_plan.md", fsync / "feature_dependency_graph.md"],
        [fsync / "target_spec_work_order.md", fsync / "spec_branch_queue.md"],
    )


def render_md(state: dict[str, Any]) -> str:
    lines = [
        "# HLDspec State",
        "",
        "made by AI",
        "",
        f"Current stage: `{state['current_stage']}`",
        f"Last completed stage: `{state['last_completed_stage']}`",
        f"Current checkpoint: `{state['current_checkpoint']}`",
        f"Source HLD modified: `{str(state['source_hld_modified']).lower()}`",
        f"Working HLD modified: `{str(state['working_hld_modified']).lower()}`",
        "",
        "## Next allowed actions",
        "",
    ]
    for action in state.get("next_allowed_actions", []):
        lines.append(f"- {action}")

    for title, key in [
        ("Controlling artifacts", "controlling_artifacts"),
        ("Supporting artifacts", "supporting_artifacts"),
        ("Legacy/supporting artifacts", "legacy_supporting_artifacts"),
    ]:
        lines += ["", f"## {title}", ""]
        values = state.get(key, [])
        if values:
            for value in values:
                lines.append(f"- `{value}`")
        else:
            lines.append("- none")

    if state.get("blocking_questions"):
        lines += ["", "## Blocking questions", ""]
        for q in state["blocking_questions"]:
            lines.append(f"- `{q.get('artifact')}`: {q.get('open_question_count')} open")

    if state.get("notes"):
        lines += ["", "## Notes", ""]
        for note in state["notes"]:
            lines.append(f"- {note}")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build current HLDspec state summary.")
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    out = workspace / ".specify" / "sync"
    out.mkdir(parents=True, exist_ok=True)

    state = build_state(workspace, args.source_hld)
    (out / "hldspec_state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "hldspec_state.md").write_text(render_md(state), encoding="utf-8")

    print("HLDspec state generated:")
    print(f"- json: {out / 'hldspec_state.json'}")
    print(f"- report: {out / 'hldspec_state.md'}")
    print(f"- current stage: {state['current_stage']}")
    print(f"- checkpoint: {state['current_checkpoint']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
