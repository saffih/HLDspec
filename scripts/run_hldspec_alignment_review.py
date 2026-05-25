#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import tempfile
from pathlib import Path
from typing import Any


REQUIRED_DOCS = [
    "docs/HLDSPEC_USE_CASES_AND_API.md",
    "docs/HLDSPEC_USER_STORIES.md",
    # Removed: HLDSPEC_IMPLEMENTATION_TODO.md superseded by TASKS.md
    # Removed: HLDSPEC_RUNSKEPTIC_*.md are point-in-time records, now in docs/archive/
]

REQUIRED_SCRIPTS = [
    "scripts/hldspec_run.sh",
    "scripts/hldspec_status.sh",
    "scripts/hldspec_prework.sh",
    "scripts/first_run_readonly.sh",
    "scripts/build_hld_usecase_api_map.py",
    "scripts/build_hldspec_state.py",
    "scripts/build_speckit_prework_quality_review.py",
    "scripts/build_speckit_prework_package.py",
]

REQUIRED_TESTS = [
    "tests/test_hld_section_classification_context.py",
    "tests/test_hld_spec_build_plan_context_gate.py",
    "tests/test_hld_usecase_api_map.py",
    "tests/test_hldspec_status_and_alignment.py",
]


def read_text(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def load_module(root: Path, name: str, rel: str):
    path = root / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check_first_run_order(root: Path) -> tuple[bool, dict[str, int]]:
    text = read_text(root, "scripts/first_run_readonly.sh")
    markers = {
        "classify": text.find("scripts/classify_hld_sections.py"),
        "usecase_map": text.find("scripts/build_hld_usecase_api_map.py"),
        "plan_specs": text.find("--plan-specs"),
        "prework_quality": text.find("scripts/build_speckit_prework_quality_review.py"),
        "prework_package": text.find("scripts/build_speckit_prework_package.py"),
        "state": text.find("scripts/build_hldspec_state.py"),
    }

    # Evidence order only. State can be regenerated before or after package.
    ordered = all(value >= 0 for value in markers.values()) and (
        markers["classify"]
        < markers["usecase_map"]
        < markers["plan_specs"]
        < markers["prework_quality"]
        < markers["prework_package"]
    )
    return ordered, markers


def check_pass_keep_plan_by_behavior(root: Path) -> tuple[bool, str]:
    # Behavioral check, not brittle source-string matching.
    try:
        build_state_mod = load_module(root, "build_hldspec_state_for_alignment", "scripts/build_hldspec_state.py")
    except Exception as exc:
        return False, f"could not import build_hldspec_state.py: {exc}"

    with tempfile.TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        sync = workspace / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)

        hld_text = "\n".join(
            [
                "## HLD-001 - Session API Interface",
                "",
                "HLD-ID: HLD-001",
                "HLD-ROLE: api",
                "HLD-STATUS: active",
                "HLD-RISK: LOW",
                "HLD-SPECS: TBD",
                "HLD-RESOURCES: TBD",
                "",
            ]
        )
        (workspace / "HLD.md").write_text(hld_text, encoding="utf-8")
        (sync / "spec_build_plan_review.md").write_text(
            "Continue to target-spec generation: `true`\n",
            encoding="utf-8",
        )
        (sync / "spec_build_plan.json").write_text(
            json.dumps(
                {
                    "planned_specs": [
                        {
                            "planned_spec_id": "001",
                            "title": "Session API Interface",
                            "quality_flags": [],
                            "requires_user_review": False,
                        }
                    ],
                    "plan_quality": {
                        "decision": "PASS",
                        "recommendation": "KEEP_PLAN",
                        "conflicts": [],
                        "findings": [],
                    },
                }
            ),
            encoding="utf-8",
        )
        (sync / "spec_build_plan_decision_queue.json").write_text(
            json.dumps({"questions": []}),
            encoding="utf-8",
        )
        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "APPROVAL_READY", "findings": []}),
            encoding="utf-8",
        )

        state = build_state_mod.build_state(workspace, "source.md")
        evidence = {
            "current_stage": state.get("current_stage"),
            "current_checkpoint": state.get("current_checkpoint"),
            "plan_summary": state.get("plan_summary", {}),
        }
        ok = state.get("current_stage") == "SPECKIT_PREWORK_APPROVAL_GATE"
        return ok, json.dumps(evidence, sort_keys=True)


def check_todo_intro(root: Path) -> bool:
    # HLDSPEC_IMPLEMENTATION_TODO.md was superseded by TASKS.md.
    # Check TASKS.md exists and has P0/P1 structure instead.
    text = read_text(root, "TASKS.md")
    return "P0" in text and "P1" in text


def check_usecase_map_contract(root: Path) -> bool:
    text = read_text(root, "scripts/build_hld_usecase_api_map.py")
    required_terms = [
        "actors",
        "user_journeys",
        "system_use_cases",
        "api_interface_surfaces",
        "data_source_of_truth_objects",
        "feature_candidates",
        "context_only_sections",
        "first_buildable_feature",
        "open_questions",
    ]
    return all(term in text for term in required_terms)


def run_alignment_review(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def add(fid: str, severity: str, area: str, finding: str, recommendation: str, evidence: str) -> None:
        findings.append(
            {
                "id": fid,
                "severity": severity,
                "area": area,
                "finding": finding,
                "recommendation": recommendation,
                "evidence": evidence,
                "RunSkeptic_decision": "FIX" if severity == "BLOCKER" else "HANDLED",
            }
        )

    for rel in REQUIRED_DOCS:
        if not exists(root, rel):
            add("ALIGN-DOC", "BLOCKER", "documentation", f"Missing required doc: {rel}", "Add or restore the required product-context document.", rel)

    for rel in REQUIRED_SCRIPTS:
        if not exists(root, rel):
            add("ALIGN-SCRIPT", "BLOCKER", "script/API", f"Missing required script: {rel}", "Add or restore the required product API script.", rel)

    for rel in REQUIRED_TESTS:
        if not exists(root, rel):
            add("ALIGN-TEST", "ACTION", "tests", f"Missing expected regression test: {rel}", "Add regression coverage for this product layer.", rel)

    ordered, markers = check_first_run_order(root)
    if not ordered:
        add(
            "ALIGN-FLOW-ORDER",
            "BLOCKER",
            "first-run flow",
            "first_run_readonly.sh does not run classify -> use-case/API map -> plan -> prework quality/package in the expected evidence order.",
            "Reorder first-run steps so downstream artifacts consume the correct upstream evidence.",
            json.dumps(markers, sort_keys=True),
        )

    pass_ok, pass_evidence = check_pass_keep_plan_by_behavior(root)
    if not pass_ok:
        add(
            "ALIGN-PASS-PLAN",
            "BLOCKER",
            "state/checkpoint",
            "State flow does not behaviorally accept PASS / KEEP_PLAN as a green plan.",
            "Accept PASS / KEEP_PLAN as the clean stabilized state, while preserving compatibility with FIX/HANDLED.",
            pass_evidence,
        )

    if not check_todo_intro(root):
        add(
            "ALIGN-TODO",
            "ACTION",
            "context preservation",
            "TASKS.md is missing or does not have P0/P1 task structure.",
            "Keep TASKS.md as the living session recovery anchor (supersedes HLDSPEC_IMPLEMENTATION_TODO.md).",
            "TASKS.md",
        )

    if exists(root, "scripts/build_hld_usecase_api_map.py") and not check_usecase_map_contract(root):
        add(
            "ALIGN-USECASE-CONTRACT",
            "BLOCKER",
            "use-case/API map",
            "Use-case/API map builder does not expose the expected product contract fields.",
            "Restore actors, journeys, use cases, API surfaces, data objects, candidates, context-only sections, first buildable feature, and open questions.",
            "scripts/build_hld_usecase_api_map.py",
        )

    status = "PASS_WITH_DEFERRED_ITEMS" if not any(f["severity"] == "BLOCKER" for f in findings) else "REWORK_REQUIRED"

    return {
        "schema_version": 1,
        "status": status,
        "review_type": "HLDSPEC_PRODUCT_ALIGNMENT_RUNSKEPTIC",
        "RunSkeptic_method": {
            "source": "saffih/skeptic/skeptic.md",
            "flow": "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
            "cycles": [
                "product_goal_and_source_of_truth",
                "use_cases_and_command_api",
                "first_run_artifact_flow",
                "state_and_checkpoint_flow",
                "prework_and_speckit_handoff",
                "tests_and_context_preservation",
            ],
        },
        "goal": {
            "summary": "HLDspec should be a judge-led product that converts/inspects HLDs, classifies sections, extracts use-case/API evidence, builds safe SpecKit prework, stops at human checkpoints, and never invokes implementation without approval.",
            "source_docs": REQUIRED_DOCS[:2],
        },
        "findings": findings,
        "deferred_items": [
            "interactive hldspec_interview wrapper",
            "source-HLD-affecting feedback queue",
            "one-phase-at-a-time SpecKit proxy execution",
            "changing unknown section default from SPEC_CANDIDATE to REVIEW_NEEDED",
        ],
    }


def render_md(review: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Product Alignment RunSkeptic Review",
        "",
        "",
        "",
        f"Status: `{review['status']}`",
        f"Review type: `{review['review_type']}`",
        "",
        "## Goal",
        "",
        review["goal"]["summary"],
        "",
        "Source docs:",
    ]
    for doc in review["goal"]["source_docs"]:
        lines.append(f"- `{doc}`")

    lines += [
        "",
        "## RunSkeptic cycles",
        "",
        f"Flow: `{review['RunSkeptic_method']['flow']}`",
        "",
    ]
    for idx, cycle in enumerate(review["RunSkeptic_method"]["cycles"], start=1):
        lines.append(f"{idx}. `{cycle}`")

    lines += ["", "## Findings", ""]
    findings = review.get("findings", [])
    if not findings:
        lines.append("No blocking alignment findings.")
    for finding in findings:
        lines += [
            f"### {finding['id']} - {finding['area']}",
            "",
            f"- severity: `{finding['severity']}`",
            f"- decision: `{finding['RunSkeptic_decision']}`",
            f"- finding: {finding['finding']}",
            f"- recommendation: {finding['recommendation']}",
            f"- evidence: `{finding['evidence']}`",
            "",
        ]

    lines += ["", "## Deferred items", ""]
    for item in review.get("deferred_items", []):
        lines.append(f"- {item}")

    lines += [
        "",
        "## Decision",
        "",
        "HANDLED when status is `PASS_WITH_DEFERRED_ITEMS`: the currently implemented product foundation is aligned enough to continue to the next bounded patch.",
        "",
        "CONFLICT remains for deferred items until their source-of-truth and checkpoint contracts are implemented and tested.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run HLDspec product alignment review.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--out-dir", default="")
    parser.add_argument("--print-findings", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    out_dir = Path(args.out_dir) if args.out_dir else root / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)

    review = run_alignment_review(root)
    json_path = out_dir / "HLDSPEC_RUNSKEPTIC_PRODUCT_ALIGNMENT.json"
    md_path = out_dir / "HLDSPEC_RUNSKEPTIC_PRODUCT_ALIGNMENT.md"

    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(review), encoding="utf-8")

    print("HLDspec product alignment review generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {review['status']}")
    print(f"- findings: {len(review['findings'])}")

    if args.print_findings and review["findings"]:
        print(json.dumps(review["findings"], indent=2, sort_keys=True))

    return 1 if review["status"] == "REWORK_REQUIRED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
