#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


ALLOWED_ARTIFACTS = [
    "docs/CONTEXT_TAILORING_PROTOCOL.md",
    "AGENTS.md",
    "TERMINOLOGY.md",
    "docs/CANONICAL_FLOW.md",
    "docs/SPECKIT_PROXY_PROTOCOL.md",
    "scripts/project_continue.sh",
    "scripts/build_hldspec_state.py",
    "scripts/build_speckit_prework_package.py",
    "scripts/build_speckit_proxy_dossier.py",
]


@dataclass
class Finding:
    finding_id: str
    rule: str
    artifact: str
    decision: str
    recommendation: str
    evidence: list[str]
    issue_type: str


def read(root: Path, rel: str) -> str:
    path = root / rel
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def contains(text: str, needles: Iterable[str]) -> list[str]:
    low = text.lower()
    return [n for n in needles if n.lower() in low]


def check_marker(root: Path, idx: int, rule: str, rel: str, markers: list[str]) -> Finding:
    path = root / rel
    if not path.exists():
        return Finding(f"CTX-{idx:03d}", rule, rel, "ACTION", "FIX", [f"missing artifact: {rel}"], "missing_artifact")

    text = read(root, rel)
    found = contains(text, markers)
    if found:
        return Finding(f"CTX-{idx:03d}", rule, rel, "PASS", "KEEP", [f"found marker(s): {', '.join(found)}"], "none")

    return Finding(
        f"CTX-{idx:03d}",
        rule,
        rel,
        "ACTION",
        "FIX",
        [f"missing expected marker(s): {', '.join(markers)}"],
        "real_issue",
    )


def build_review(root: Path) -> dict[str, object]:
    findings: list[Finding] = []
    checks = [
        ("Weakest sufficient agent", "docs/CONTEXT_TAILORING_PROTOCOL.md", ["weakest sufficient agent", "Level 0 - deterministic tool/script"]),
        ("Smallest sufficient context", "docs/CONTEXT_TAILORING_PROTOCOL.md", ["smallest sufficient context", "minimum relevant files"]),
        ("Strictest sufficient prompt", "docs/CONTEXT_TAILORING_PROTOCOL.md", ["strictest sufficient prompt", "The simpler the task"]),
        ("Nested delegation guard", "docs/CONTEXT_TAILORING_PROTOCOL.md", ["Nested delegation", "parent verifies the result"]),
        ("Context tailoring terms", "TERMINOLOGY.md", ["Context Tailoring", "Task Context Package", "Weakest Sufficient Agent"]),
        ("Canonical SpecKit boundary", "docs/CANONICAL_FLOW.md", ["HLDspec prepares and reviews", "SpecKit owns"]),
        ("Deprecated target-spec wording documented", "docs/CANONICAL_FLOW.md", ["Deprecated wording", "target-spec generation is allowed"]),
        ("SpecKit proxy question policy", "docs/SPECKIT_PROXY_PROTOCOL.md", ["ANSWER_FROM_EVIDENCE", "ESCALATE_TO_HUMAN"]),
        ("AGENTS references context tailoring", "AGENTS.md", ["docs/CONTEXT_TAILORING_PROTOCOL.md", "weakest sufficient agent"]),
        ("AGENTS prioritizes state/prework", "AGENTS.md", ["hldspec_state.md", "speckit_prework_package.md"]),
        ("AGENTS marks legacy artifacts", "AGENTS.md", ["Legacy/supporting when SpecKit is available", "target_spec_work_order", "spec_branch_queue"]),
        ("project_continue prints state/prework", "scripts/project_continue.sh", ["HLDspec state", "SpecKit prework package"]),
        ("state builder has approval gate", "scripts/build_hldspec_state.py", ["SPECKIT_PREWORK_APPROVAL_GATE", "speckit_prework_package.md"]),
        ("proxy dossier is bounded", "scripts/build_speckit_proxy_dossier.py", ["allowed_evidence_sources", "question_answering_policy"]),
    ]

    for idx, (rule, rel, markers) in enumerate(checks, start=1):
        findings.append(check_marker(root, idx, rule, rel, markers))

    agents = read(root, "AGENTS.md")
    stale_phrases = ["report whether target-spec generation is allowed", "whether target-spec generation is allowed"]
    stale_found = contains(agents, stale_phrases)
    if stale_found:
        findings.append(
            Finding(
                f"CTX-{len(findings)+1:03d}",
                "No active stale target-spec wording in AGENTS",
                "AGENTS.md",
                "ACTION",
                "FIX",
                [f"stale active wording found: {', '.join(stale_found)}"],
                "real_issue",
            )
        )
    else:
        findings.append(
            Finding(
                f"CTX-{len(findings)+1:03d}",
                "No active stale target-spec wording in AGENTS",
                "AGENTS.md",
                "PASS",
                "KEEP",
                ["no stale active wording found"],
                "none",
            )
        )

    action = sum(1 for f in findings if f.decision == "ACTION")
    conflict = sum(1 for f in findings if f.decision == "CONFLICT")
    status = "CONFLICTS_FOUND" if conflict else ("ACTIONS_FOUND" if action else "PASS")

    return {
        "schema_version": 1,
        "review_type": "CONTEXT_TAILORING_COMPLIANCE_REVIEW",
        "status": status,
        "allowed_context": ALLOWED_ARTIFACTS,
        "summary": {
            "total_findings": len(findings),
            "pass": sum(1 for f in findings if f.decision == "PASS"),
            "action": action,
            "conflict": conflict,
        },
        "findings": [asdict(f) for f in findings],
    }


def render_md(review: dict[str, object]) -> str:
    summary = review["summary"]
    lines = [
        "# Context Tailoring Compliance Review",
        "",
        "",
        "",
        f"Status: `{review['status']}`",
        "",
        "## Summary",
        "",
        f"- total findings: {summary['total_findings']}",
        f"- pass: {summary['pass']}",
        f"- action: {summary['action']}",
        f"- conflict: {summary['conflict']}",
        "",
        "## Allowed context",
        "",
    ]

    for rel in review["allowed_context"]:
        lines.append(f"- `{rel}`")

    lines += ["", "## Findings", ""]
    for item in review["findings"]:
        lines += [
            f"### {item['finding_id']} - {item['rule']}",
            "",
            f"- artifact: `{item['artifact']}`",
            f"- decision: `{item['decision']}`",
            f"- recommendation: `{item['recommendation']}`",
            f"- issue type: `{item['issue_type']}`",
            "",
            "Evidence:",
        ]
        for ev in item["evidence"]:
            lines.append(f"- {ev}")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only Context Tailoring compliance review.")
    parser.add_argument("--repo", default=".", help="HLDspec repository root.")
    parser.add_argument("--output-dir", default=".hldspec-context-tailoring-review")
    parser.add_argument("--fail-on-action", action="store_true")
    args = parser.parse_args()

    root = Path(args.repo).resolve()
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)

    review = build_review(root)
    (out / "context_tailoring_compliance_review.json").write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "context_tailoring_compliance_review.md").write_text(render_md(review), encoding="utf-8")

    print("Context Tailoring compliance review generated:")
    print(f"- json: {out / 'context_tailoring_compliance_review.json'}")
    print(f"- report: {out / 'context_tailoring_compliance_review.md'}")
    print(f"- status: {review['status']}")
    print(f"- pass: {review['summary']['pass']}")
    print(f"- action: {review['summary']['action']}")
    print(f"- conflict: {review['summary']['conflict']}")

    if args.fail_on_action and review["summary"]["action"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
