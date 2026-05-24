#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


@dataclass
class Cycle:
    cycle_id: str
    area: str
    aspect: str
    spotlight: str
    decision: str
    severity: str
    finding: str
    evidence: list[str]
    recommendation: str
    affected_artifacts: list[str]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return ""


def exists(root: Path, rel: str) -> bool:
    return (root / rel).exists()


def evidence_file(root: Path, rel: str, phrase: str | None = None) -> list[str]:
    path = root / rel
    if not path.exists():
        return [f"missing: {rel}"]
    if phrase is None:
        return [f"exists: {rel}"]
    text = read(path)
    return [f"{rel}: contains {phrase!r}" if phrase in text else f"{rel}: missing {phrase!r}"]


def has(root: Path, rel: str, phrase: str) -> bool:
    return phrase in read(root / rel)


def add(cycles: list[Cycle], **kwargs: object) -> None:
    cycles.append(Cycle(**kwargs))  # type: ignore[arg-type]


def scan_required_files(root: Path, cycles: list[Cycle]) -> None:
    required = [
        "AGENTS.md",
        "TERMINOLOGY.md",
        "scripts/first_run_readonly.sh",
        "scripts/project_continue.sh",
        "scripts/hldspec_run.sh",
        "scripts/write_skeptic_cache.py",
        "scripts/build_hld_conversion_plan.py",
        "scripts/build_hld_conversion_decision_queue.py",
        "scripts/apply_hld_conversion_decisions.py",
        "scripts/classify_hld_sections.py",
        "scripts/review_spec_build_plan.py",
        "scripts/build_spec_plan_decision_queue.py",
    ]
    for idx, rel in enumerate(required, start=1):
        present = exists(root, rel)
        add(
            cycles,
            cycle_id=f"FILE-{idx:03d}",
            area="repo baseline",
            aspect="source_of_truth",
            spotlight=rel,
            decision="FIX" if not present else "FIX",
            severity="BLOCKER" if not present else "PASS",
            finding="Required HLDspec runtime file is missing." if not present else "Required HLDspec runtime file is present.",
            evidence=evidence_file(root, rel),
            recommendation="Restore or create this file before continuing." if not present else "Keep.",
            affected_artifacts=[rel],
        )


def scan_RunSkeptic(root: Path, cycles: list[Cycle]) -> None:
    agents = read(root / "AGENTS.md")
    terms = read(root / "TERMINOLOGY.md")
    cache_script = read(root / "scripts/write_skeptic_cache.py")

    checks = [
        (
            "BES-001",
            "RunSkeptic source",
            "saffih/skeptic/skeptic.md",
            "AGENTS.md",
            agents,
            "HLDspec references the real Skeptic framework source.",
        ),
        (
            "BES-002",
            "RunSkeptic phase flow",
            "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
            "AGENTS.md",
            agents,
            "HLDspec preserves the real Skeptic phase flow.",
        ),
        (
            "BES-003",
            "RunSkeptic question bank",
            "skeptic-questions.md",
            "AGENTS.md",
            agents,
            "HLDspec requires the companion question bank.",
        ),
        (
            "BES-004",
            "RunSkeptic terminology",
            "RunSkeptic review",
            "TERMINOLOGY.md",
            terms,
            "RunSkeptic terminology is defined.",
        ),
        (
            "BES-005",
            "RunSkeptic cache writer",
            "skeptic-questions",
            "scripts/write_skeptic_cache.py",
            cache_script,
            "Cache writer appears to include the question bank.",
        ),
    ]

    for cid, spotlight, phrase, rel, text, ok_finding in checks:
        ok = phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="RunSkeptic",
            aspect="verification_path",
            spotlight=spotlight,
            decision="FIX",
            severity="PASS" if ok else "ACTION",
            finding=ok_finding if ok else f"Missing expected RunSkeptic marker: {phrase}",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Update cache/docs so RunSkeptic is grounded in the real framework.",
            affected_artifacts=[rel],
        )


def scan_canonical_flow(root: Path, cycles: list[Cycle]) -> None:
    project_continue = read(root / "scripts/project_continue.sh")
    first_run = read(root / "scripts/first_run_readonly.sh")
    agents = read(root / "AGENTS.md")
    canonical = read(root / "docs/CANONICAL_FLOW.md")

    required_prework = [
        "build_speckit_prework_plan.py",
        "build_speckit_prework_quality_review.py",
        "build_speckit_proxy_dossier.py",
        "speckit_prework_quality_review.md",
        "speckit_proxy_dossier.md",
    ]

    for idx, phrase in enumerate(required_prework, start=1):
        ok = phrase in first_run or phrase in project_continue
        add(
            cycles,
            cycle_id=f"FLOW-{idx:03d}",
            area="canonical flow",
            aspect="workflow_order",
            spotlight=phrase,
            decision="FIX",
            severity="PASS" if ok else "BLOCKER",
            finding=f"Canonical flow includes {phrase}." if ok else f"Canonical flow is missing {phrase}.",
            evidence=[
                f"first_run_readonly.sh: {'contains' if phrase in first_run else 'missing'} {phrase!r}",
                f"project_continue.sh: {'contains' if phrase in project_continue else 'missing'} {phrase!r}",
            ],
            recommendation="Keep." if ok else "Wire this step/artifact into the runner before continuing.",
            affected_artifacts=["scripts/first_run_readonly.sh", "scripts/project_continue.sh"],
        )

    old_terms = [
        "Next safe checkpoint: target-spec generation is allowed",
        "Write target specs only under the first-run workspace",
    ]
    for idx, phrase in enumerate(old_terms, start=1):
        found = phrase in project_continue
        add(
            cycles,
            cycle_id=f"FLOW-LEGACY-{idx:03d}",
            area="canonical flow",
            aspect="source_of_truth",
            spotlight=phrase,
            decision="FIX",
            severity="BLOCKER" if found else "PASS",
            finding="Legacy target-spec checkpoint is still controlling the runner." if found else "Legacy target-spec checkpoint is not controlling the runner.",
            evidence=[f"project_continue.sh: {'contains' if found else 'does not contain'} {phrase!r}"],
            recommendation="Replace with SpecKit prework approval gate." if found else "Keep.",
            affected_artifacts=["scripts/project_continue.sh"],
        )

    for cid, rel, text, phrase in [
        ("FLOW-DOC-001", "docs/CANONICAL_FLOW.md", canonical, "SpecKit prework approval gate"),
        ("FLOW-DOC-002", "AGENTS.md", agents, "docs/CANONICAL_FLOW.md"),
    ]:
        ok = bool(text) and phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="canonical flow",
            aspect="human_decision",
            spotlight=rel,
            decision="FIX",
            severity="PASS" if ok else "ACTION",
            finding=f"{rel} documents canonical flow." if ok else f"{rel} does not document canonical flow.",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Add canonical flow reference.",
            affected_artifacts=[rel],
        )


def scan_speckit_boundary(root: Path, cycles: list[Cycle]) -> None:
    agents = read(root / "AGENTS.md")
    proxy_protocol = read(root / "docs/SPECKIT_PROXY_PROTOCOL.md")
    prework_script = read(root / "scripts/build_speckit_prework_plan.py")
    dossier_script = read(root / "scripts/build_speckit_proxy_dossier.py")

    checks = [
        (
            "SKB-001",
            "SpecKit ownership boundary",
            "HLDspec must use SpecKit instead of reimplementing SpecKit",
            "AGENTS.md",
            agents,
        ),
        (
            "SKB-002",
            "SpecKit owns artifacts",
            "SpecKit owns:",
            "AGENTS.md",
            agents,
        ),
        (
            "SKB-003",
            "SpecKit proxy protocol",
            "SpecKit Proxy Protocol",
            "docs/SPECKIT_PROXY_PROTOCOL.md",
            proxy_protocol,
        ),
        (
            "SKB-004",
            "SpecKit sequence",
            "constitution if missing or update required",
            "docs/SPECKIT_PROXY_PROTOCOL.md",
            proxy_protocol,
        ),
        (
            "SKB-005",
            "Question answer policy",
            "ANSWER_FROM_EVIDENCE",
            "docs/SPECKIT_PROXY_PROTOCOL.md",
            proxy_protocol,
        ),
        (
            "SKB-006",
            "Escalation policy",
            "ESCALATE_TO_HUMAN",
            "docs/SPECKIT_PROXY_PROTOCOL.md",
            proxy_protocol,
        ),
        (
            "SKB-007",
            "Prework manifest generator",
            "speckit_input_manifest",
            "scripts/build_speckit_prework_plan.py",
            prework_script,
        ),
        (
            "SKB-008",
            "Proxy dossier generator",
            "speckit_proxy_dossier",
            "scripts/build_speckit_proxy_dossier.py",
            dossier_script,
        ),
    ]

    for cid, spotlight, phrase, rel, text in checks:
        ok = phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="SpecKit boundary",
            aspect="ownership",
            spotlight=spotlight,
            decision="FIX",
            severity="PASS" if ok else "ACTION",
            finding=f"{spotlight} is present." if ok else f"{spotlight} is missing or not explicit.",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Make the SpecKit/HLDspec ownership split explicit.",
            affected_artifacts=[rel],
        )


def scan_judge_protocol(root: Path, cycles: list[Cycle]) -> None:
    protocol = read(root / "docs/JUDGE_LED_REVIEW_PROTOCOL.md")
    agents = read(root / "AGENTS.md")
    terms = read(root / "TERMINOLOGY.md")

    checks = [
        ("JDG-001", "Judge-Led Review Protocol", "docs/JUDGE_LED_REVIEW_PROTOCOL.md", agents),
        ("JDG-002", "Feedback Impact Map", "Feedback Impact Map", protocol),
        ("JDG-003", "Affected Artifact", "Affected Artifact", protocol),
        ("JDG-004", "Rebuild Loop", "Rebuild Loop", protocol),
        ("JDG-005", "What I will do after you answer", "What I will do after you answer", protocol),
        ("JDG-006", "Human Decision Owner", "Human Decision Owner", terms),
    ]

    for cid, spotlight, phrase, text in checks:
        rel = "AGENTS.md" if "docs/" in phrase else ("TERMINOLOGY.md" if spotlight == "Human Decision Owner" else "docs/JUDGE_LED_REVIEW_PROTOCOL.md")
        ok = phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="judge protocol",
            aspect="user_decision",
            spotlight=spotlight,
            decision="FIX",
            severity="PASS" if ok else "ACTION",
            finding=f"{spotlight} is documented." if ok else f"{spotlight} is not documented enough.",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Add or repair judge-led review protocol documentation.",
            affected_artifacts=[rel],
        )


def scan_constitution_quality(root: Path, cycles: list[Cycle]) -> None:
    prework = read(root / "scripts/build_speckit_prework_plan.py")
    quality = read(root / "scripts/build_speckit_prework_quality_review.py")
    proxy = read(root / "scripts/build_speckit_proxy_dossier.py")

    checks = [
        ("CON-001", "constitution_update_plan", "constitution_update_plan", prework, "scripts/build_speckit_prework_plan.py"),
        ("CON-002", "architecture rules", "HLD Architecture Source of Truth", prework, "scripts/build_speckit_prework_plan.py"),
        ("CON-003", "API separation rule", "API Contract and Processing Separation", prework, "scripts/build_speckit_prework_plan.py"),
        ("CON-004", "common foundation rule", "Common Foundation Before Dependents", prework, "scripts/build_speckit_prework_plan.py"),
        ("CON-005", "quality review constitution case", "constitution_case", quality, "scripts/build_speckit_prework_quality_review.py"),
        ("CON-006", "dossier constitution context", "constitution_context", proxy, "scripts/build_speckit_proxy_dossier.py"),
    ]

    for cid, spotlight, phrase, text, rel in checks:
        ok = phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="constitution",
            aspect="source_of_truth",
            spotlight=spotlight,
            decision="FIX",
            severity="PASS" if ok else "ACTION",
            finding=f"{spotlight} is represented." if ok else f"{spotlight} is missing.",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Strengthen constitution extraction and review.",
            affected_artifacts=[rel],
        )


def scan_api_decomposition(root: Path, cycles: list[Cycle]) -> None:
    prework = read(root / "scripts/build_speckit_prework_plan.py")
    quality = read(root / "scripts/build_speckit_prework_quality_review.py")

    checks = [
        ("API-001", "API words", "API_WORDS", prework, "scripts/build_speckit_prework_plan.py"),
        ("API-002", "processing words", "PROCESSING_WORDS", prework, "scripts/build_speckit_prework_plan.py"),
        ("API-003", "split flag", "SPLIT_API_CONTRACT_FROM_PROCESSING", prework, "scripts/build_speckit_prework_plan.py"),
        ("API-004", "surface boundary risk", "api_surface_boundary_risk", prework, "scripts/build_speckit_prework_plan.py"),
        ("API-005", "quality finding", "may mix API/interface contract with processing behavior", quality, "scripts/build_speckit_prework_quality_review.py"),
    ]

    for cid, spotlight, phrase, text, rel in checks:
        ok = phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="API decomposition",
            aspect="spec_decomposition",
            spotlight=spotlight,
            decision="DECOMPOSE" if ok else "FIX",
            severity="PASS" if ok else "ACTION",
            finding=f"{spotlight} check is present." if ok else f"{spotlight} check is missing.",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Add API contract vs processing detection.",
            affected_artifacts=[rel],
        )


def scan_runner_safety(root: Path, cycles: list[Cycle]) -> None:
    first_run = read(root / "scripts/first_run_readonly.sh")
    project = read(root / "scripts/project_continue.sh")

    checks = [
        ("SAFE-001", "source HLD copied", 'cp "$HLD_SOURCE" "$WORKSPACE/HLD.raw.md"', first_run, "scripts/first_run_readonly.sh"),
        ("SAFE-002", "source constitution not created", "read-only first run created target constitution unexpectedly", first_run, "scripts/first_run_readonly.sh"),
        ("SAFE-003", "specs not created in readonly", "read-only first run created specs unexpectedly", first_run, "scripts/first_run_readonly.sh"),
        ("SAFE-004", "source update queue", "write_hld_source_update_queue.py", project, "scripts/project_continue.sh"),
        ("SAFE-005", "decision log", "write_hld_decision_log.py", project, "scripts/project_continue.sh"),
        ("SAFE-006", "project-local uv cache", "UV_CACHE_DIR", project, "scripts/project_continue.sh"),
    ]

    for cid, spotlight, phrase, text, rel in checks:
        ok = phrase in text
        add(
            cycles,
            cycle_id=cid,
            area="safety",
            aspect="staged_write_safety",
            spotlight=spotlight,
            decision="FIX",
            severity="PASS" if ok else "BLOCKER",
            finding=f"{spotlight} safety guard exists." if ok else f"{spotlight} safety guard is missing.",
            evidence=[f"{rel}: {'contains' if ok else 'missing'} {phrase!r}"],
            recommendation="Keep." if ok else "Restore this safety guard before continuing.",
            affected_artifacts=[rel],
        )


def scan_test_coverage(root: Path, cycles: list[Cycle]) -> None:
    tests = list((root / "tests").glob("test_*.py")) if (root / "tests").exists() else []
    test_names = [p.name for p in tests]
    expected_fragments = [
        "speckit_prework",
        "speckit_proxy",
        "judge_led",
        "canonical_flow",
        "target_spec_work_order",
        "spec_branch_queue",
        "hld_section_classification",
    ]

    for idx, fragment in enumerate(expected_fragments, start=1):
        matched = [name for name in test_names if fragment in name]
        add(
            cycles,
            cycle_id=f"TEST-{idx:03d}",
            area="tests",
            aspect="verification_path",
            spotlight=fragment,
            decision="FIX",
            severity="PASS" if matched else "ACTION",
            finding=f"Test coverage exists for {fragment}: {', '.join(matched)}" if matched else f"No focused test file found for {fragment}.",
            evidence=[f"tests/: {len(tests)} test files"],
            recommendation="Keep." if matched else f"Add focused regression tests for {fragment}.",
            affected_artifacts=["tests/"],
        )


def build_cycles(root: Path) -> list[Cycle]:
    cycles: list[Cycle] = []
    scan_required_files(root, cycles)
    scan_RunSkeptic(root, cycles)
    scan_canonical_flow(root, cycles)
    scan_speckit_boundary(root, cycles)
    scan_judge_protocol(root, cycles)
    scan_constitution_quality(root, cycles)
    scan_api_decomposition(root, cycles)
    scan_runner_safety(root, cycles)
    scan_test_coverage(root, cycles)
    return cycles


def summarize(cycles: list[Cycle]) -> dict[str, object]:
    counts: dict[str, int] = {}
    for cycle in cycles:
        counts[cycle.severity] = counts.get(cycle.severity, 0) + 1
    blockers = [cycle for cycle in cycles if cycle.severity == "BLOCKER"]
    actions = [cycle for cycle in cycles if cycle.severity == "ACTION"]
    return {
        "total_cycles": len(cycles),
        "counts_by_severity": counts,
        "status": "BLOCKED" if blockers else ("ACTIONS_REMAIN" if actions else "PASS"),
        "blocker_count": len(blockers),
        "action_count": len(actions),
    }


def render_md(cycles: list[Cycle], summary: dict[str, object]) -> str:
    lines = [
        "# HLDspec RunSkeptic Meta Review",
        "",
        "",
        "",
        f"Status: `{summary['status']}`",
        f"Total cycles: {summary['total_cycles']}",
        f"Blockers: {summary['blocker_count']}",
        f"Actions: {summary['action_count']}",
        "",
        "## Counts by severity",
        "",
    ]
    for sev, count in sorted(summary["counts_by_severity"].items()):  # type: ignore[union-attr]
        lines.append(f"- {sev}: {count}")

    lines += [
        "",
        "## Highest priority findings",
        "",
    ]
    priority = [c for c in cycles if c.severity in {"BLOCKER", "ACTION"}]
    if not priority:
        lines.append("No blockers or actions.")
    for cycle in priority:
        lines += [
            f"### {cycle.cycle_id} - {cycle.area} / {cycle.aspect}",
            "",
            f"- severity: `{cycle.severity}`",
            f"- decision: `{cycle.decision}`",
            f"- spotlight: {cycle.spotlight}",
            f"- finding: {cycle.finding}",
            f"- recommendation: {cycle.recommendation}",
            f"- affected artifacts: {', '.join(cycle.affected_artifacts)}",
            "",
            "Evidence:",
        ]
        for ev in cycle.evidence:
            lines.append(f"- {ev}")
        lines.append("")

    lines += [
        "## All cycles",
        "",
    ]
    for cycle in cycles:
        lines += [
            f"### {cycle.cycle_id} - {cycle.spotlight}",
            "",
            f"- area: {cycle.area}",
            f"- aspect: {cycle.aspect}",
            f"- severity: `{cycle.severity}`",
            f"- decision: `{cycle.decision}`",
            f"- finding: {cycle.finding}",
            f"- recommendation: {cycle.recommendation}",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run many RunSkeptic meta-review cycles over the HLDspec repo.")
    parser.add_argument("--repo", default=".", help="Path to HLDspec repo root.")
    parser.add_argument("--output-dir", default=".hldspec-meta-review", help="Output directory for reports.")
    parser.add_argument("--fail-on-blocker", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)

    cycles = build_cycles(root)
    summary = summarize(cycles)
    payload = {
        "schema_version": 1,
        "summary": summary,
        "cycles": [asdict(cycle) for cycle in cycles],
    }

    json_path = out / "hldspec_skeptic_meta_review.json"
    md_path = out / "hldspec_skeptic_meta_review.md"

    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(cycles, summary), encoding="utf-8")

    print("HLDspec RunSkeptic meta review generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {summary['status']}")
    print(f"- cycles: {summary['total_cycles']}")
    print(f"- blockers: {summary['blocker_count']}")
    print(f"- actions: {summary['action_count']}")

    if args.fail_on_blocker and summary["blocker_count"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
