#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


def load_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def print_section(title: str) -> None:
    print(title)


def render_conversion_decisions(args: argparse.Namespace) -> int:
    queue = load_json(args.queue)
    checkpoint = queue.get("checkpoint", {}) if isinstance(queue.get("checkpoint"), dict) else {}
    questions = [q for q in as_list(queue.get("questions")) if isinstance(q, dict)]

    open_questions = [
        q for q in questions
        if q.get("blocking", True) and str(q.get("human_decision", "TBD")) == "TBD"
    ]
    answered_questions = [
        q for q in questions
        if str(q.get("human_decision", "TBD")) != "TBD"
    ]

    print(f"Current checkpoint: {checkpoint.get('checkpoint_id', 'HLD_CONVERSION_DECISIONS')}")
    print(f"Allowed to convert: {checkpoint.get('allowed_to_convert', False)}")
    print(f"Open blocking questions: {len(open_questions)}")
    print()

    print_section("Blocking reason:")
    if open_questions:
        print(f"- {len(open_questions)} conversion decision(s) still require a human answer.")
        print("- Conversion decisions are still TBD.")
    else:
        print("- No open blocking conversion questions.")
    print()

    print_section("Human decision needed:")
    if open_questions:
        print()
        for q in open_questions:
            options = ", ".join(str(option) for option in as_list(q.get("options")))
            print(f"{q.get('question_id')} {q.get('source_candidate_id')} - {q.get('title')}")
            print(f"Question: {q.get('question')}")
            print(f"Options: {options}")
            print("Current human decision: TBD")
            print()
        print_section("Answer format:")
        print("- Pick one listed option for each open question.")
        print("- Do not answer generic OK/continue.")
    else:
        print("- none")
    print()

    if answered_questions:
        print_section("Already answered decisions:")
        for q in answered_questions:
            print(f"- {q.get('question_id')} {q.get('source_candidate_id')} -> {q.get('human_decision')}")
        print()

    print_section("Controlling artifacts:")
    queue_path = args.queue or "<queue not provided>"
    print(f"- {queue_path}")
    if args.workspace:
        print(f"- {Path(args.workspace) / '.specify' / 'sync' / 'hld_conversion_decision_queue.md'}")
    print()

    print_section("Continuation protocol:")
    print("- Human answers only the currently open checkpoint questions.")
    print(f"- Judge/orchestrator updates: {queue_path}")
    if args.runner and args.source_hld:
        print(f"- Then reruns the same command: {args.runner} {args.source_hld}")
    else:
        print("- Then reruns the same HLDspec command.")
    print()

    print_section("What is not modified / not invoked:")
    print("- The source HLD is not modified by this checkpoint.")
    print("- SpecKit is not invoked at this checkpoint.")
    print("- App code is not implemented.")

    return 2 if open_questions else 0


def plan_quality(plan: dict[str, Any], review_text: str) -> dict[str, Any]:
    pq = plan.get("plan_quality", {}) if isinstance(plan.get("plan_quality"), dict) else {}
    planned = as_list(plan.get("planned_specs"))
    conflicts = as_list(pq.get("conflicts"))
    bad = []
    for spec in planned:
        if isinstance(spec, dict) and (spec.get("quality_flags") or spec.get("requires_user_review")):
            bad.append(spec.get("planned_spec_id"))

    continue_true = bool(re.search(r"Continue to target-spec generation:\s*`?true`?", review_text, re.I))
    continue_false = bool(re.search(r"Continue to target-spec generation:\s*`?false`?", review_text, re.I))
    decision = pq.get("decision", "")
    recommendation = pq.get("recommendation", "")
    plan_green = continue_true and not continue_false and decision == "FIX" and recommendation == "KEEP_PLAN" and not conflicts and not bad

    return {
        "decision": decision,
        "recommendation": recommendation,
        "planned_count": len(planned),
        "conflict_count": len(conflicts),
        "flagged": bad,
        "plan_green": plan_green,
    }


def render_spec_build_plan(args: argparse.Namespace) -> int:
    plan = load_json(args.plan)
    review_text = Path(args.review).read_text(encoding="utf-8", errors="replace") if args.review and Path(args.review).exists() else ""
    quality = plan_quality(plan, review_text)

    print("Current checkpoint: SPEC_BUILD_PLAN_CHECKPOINT")
    print()
    print_section("Blocking reason:")
    print("- Spec build plan is not green.")
    print(f"- Plan quality decision: {quality['decision']}")
    print(f"- Recommendation: {quality['recommendation']}")
    print(f"- Planned specs: {quality['planned_count']}")
    print(f"- Conflicts: {quality['conflict_count']}")
    print(f"- Flagged specs: {len(quality['flagged'])}")
    if quality["flagged"]:
        print("- Flagged spec IDs: " + ", ".join(str(item) for item in quality["flagged"]))
    print()

    print_section("Human decision needed:")
    print("- Decide whether to fix HLD metadata, split/merge planned specs, resolve conflicts, or keep the plan with explicit rationale.")
    print("- Do not answer generic OK/continue.")
    print()

    print_section("Controlling artifacts:")
    if args.review:
        print(f"- {args.review}")
    if args.plan:
        print(f"- {args.plan}")
    if args.workspace:
        print(f"- {Path(args.workspace) / '.specify' / 'sync' / 'spec_build_plan_decision_queue.md'}")
    print()

    print_section("Continuation protocol:")
    print("- Judge/orchestrator applies the decision to the working HLD/artifacts.")
    print("- Then reruns the same HLDspec command.")
    print()

    print_section("What is not modified / not invoked:")
    print("- SpecKit is not invoked at this checkpoint.")
    print("- App code is not implemented.")
    return 2


def render_prework_missing(args: argparse.Namespace) -> int:
    print("Current checkpoint: SPECKIT_PREWORK_MISSING")
    print()
    print_section("Blocking reason:")
    print("- SpecKit prework artifacts are missing.")
    print()
    print_section("Human decision needed:")
    print("- none; this is a regeneration/tooling issue.")
    print()
    print_section("Controlling artifacts:")
    if args.workspace:
        print(f"- expected: {Path(args.workspace) / '.specify' / 'sync' / 'speckit_prework_package.md'}")
    print()
    print_section("Continuation protocol:")
    print("- Rerun first_readonly or the same HLDspec command to regenerate SpecKit prework artifacts.")
    print()
    print_section("What is not modified / not invoked:")
    print("- SpecKit is not invoked.")
    print("- App code is not implemented.")
    return 2


def render_prework_rework(args: argparse.Namespace) -> int:
    review = load_json(args.prework_review)
    findings = [item for item in as_list(review.get("findings")) if isinstance(item, dict)]
    blockers = [item for item in findings if item.get("severity") == "BLOCKER"]

    print("Current checkpoint: SPECKIT_PREWORK_REWORK")
    print()
    print_section("Blocking reason:")
    print("- SpecKit prework quality review requires rework.")
    print(f"- Findings: {len(findings)}")
    print(f"- Blockers: {len(blockers)}")
    for blocker in blockers[:10]:
        print(f"  - {blocker.get('field', 'unknown')}: {blocker.get('message', blocker)}")
    print()

    print_section("Human decision needed:")
    print("- Decide whether to fix constitution/prework/dependency artifacts or accept a documented conflict.")
    print("- Do not approve SpecKit invocation while blockers remain.")
    print()

    print_section("Controlling artifacts:")
    if args.prework_review:
        print(f"- {args.prework_review}")
    if args.workspace:
        sync = Path(args.workspace) / ".specify" / "sync"
        print(f"- {sync / 'speckit_prework_quality_review.md'}")
        print(f"- {sync / 'speckit_prework_package.md'}")
    print()

    print_section("Continuation protocol:")
    print("- Judge/orchestrator rebuilds affected artifacts and reruns the quality gate.")
    print()

    print_section("What is not modified / not invoked:")
    print("- SpecKit is not invoked until prework approval is green.")
    print("- App code is not implemented.")
    return 2


def render_prework_approval(args: argparse.Namespace) -> int:
    print("Current checkpoint: SPECKIT_PREWORK_APPROVAL_GATE")
    print("Checkpoint label: SpecKit prework approval gate")
    print()
    print_section("Blocking reason:")
    print("- Prework is ready for human approval before SpecKit is invoked.")
    print()
    print_section("Human decision needed:")
    print("- Approve, reject, or request changes to speckit_prework_package.md.")
    print("- Approval must cover the constitution case, architecture/dependency case, first-feature case, RunSkeptic findings, and feedback impact rules.")
    print()
    print_section("Controlling artifacts:")
    if args.workspace:
        sync = Path(args.workspace) / ".specify" / "sync"
        print(f"- {sync / 'speckit_prework_package.md'}")
        print(f"- {sync / 'speckit_prework_quality_review.md'}")
        print(f"- {sync / 'speckit_proxy_dossier.md'}")
        print(f"- {sync / 'hldspec_state.md'}")
    print()
    print_section("Continuation protocol:")
    print("- Judge/orchestrator may invoke SpecKit in the documented order after approval.")
    print("- HLDspec still must not manually write final specs.")
    print("- Implementation/code remains blocked until later approval.")
    print()
    print_section("What is not modified / not invoked:")
    print("Do not write specs manually from HLDspec.")
    print("Do not invoke SpecKit until the human approves this gate.")
    print("- App code is not implemented.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Render HLDspec checkpoint messages with a stable output contract.")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--queue")
    parser.add_argument("--workspace")
    parser.add_argument("--source-hld")
    parser.add_argument("--runner")
    parser.add_argument("--plan")
    parser.add_argument("--review")
    parser.add_argument("--prework-review")
    args = parser.parse_args()

    handlers = {
        "HLD_CONVERSION_DECISIONS": render_conversion_decisions,
        "SPEC_BUILD_PLAN_CHECKPOINT": render_spec_build_plan,
        "SPECKIT_PREWORK_MISSING": render_prework_missing,
        "SPECKIT_PREWORK_REWORK": render_prework_rework,
        "SPECKIT_PREWORK_APPROVAL_GATE": render_prework_approval,
    }
    handler = handlers.get(args.checkpoint)
    if handler is None:
        raise SystemExit(f"Unknown checkpoint: {args.checkpoint}")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
