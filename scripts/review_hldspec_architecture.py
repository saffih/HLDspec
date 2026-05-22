#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


SCRIPT_GLOBS = ("scripts/*.py", "scripts/*.sh")
TEST_GLOBS = ("tests/test_*.py",)

SRP_MIXED_RESPONSIBILITY_PATTERNS = {
    "shell_embedded_python": re.compile(r"<<'PY|<<PY|python3\s+-\s+<<|uv run python\s+-\s+<<"),
    "checkpoint_rendering": re.compile(r"Current checkpoint:|Human decision needed:|Continuation protocol:|Blocking reason:"),
    "json_parsing": re.compile(r"json\.loads|jq\b|json\.load"),
    "subprocess_orchestration": re.compile(r"subprocess\.run|bash\s+\"\$|bash\s+"),
    "file_generation": re.compile(r"write_text|cat\s+>\s+|tee\s+"),
}

RUNSKEPTIC_REQUIRED_FIELDS = [
    "observed_evidence",
    "evidence_level",
    "confidence",
    "unknowns",
    "verification",
    "residual_risk",
]


@dataclass
class Finding:
    artifact: str
    line_start: int
    line_end: int
    principle: str
    severity: str
    decision: str
    issue: str
    observed_evidence: str
    evidence_level: str
    confidence: str
    unknowns: list[str]
    verification: str
    residual_risk: str
    recommendation: str


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def line_count(text: str) -> int:
    return len(text.splitlines())


def find_line(text: str, needle: str) -> int:
    for idx, line in enumerate(text.splitlines(), start=1):
        if needle in line:
            return idx
    return 1


def script_paths(repo: Path, include_tests: bool = False) -> list[Path]:
    paths: set[Path] = set()
    for glob in SCRIPT_GLOBS:
        paths.update(repo.glob(glob))
    if include_tests:
        for glob in TEST_GLOBS:
            paths.update(repo.glob(glob))
    return sorted(path for path in paths if path.is_file())


def responsibility_hits(text: str) -> list[str]:
    hits = []
    for name, pattern in SRP_MIXED_RESPONSIBILITY_PATTERNS.items():
        if pattern.search(text):
            hits.append(name)
    return hits


def has_main_guard(text: str) -> bool:
    return 'if __name__ == "__main__"' in text or "if __name__ == '__main__'" in text


def public_functions(text: str) -> list[str]:
    return re.findall(r"^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", text, flags=re.M)


def shell_functions(text: str) -> list[str]:
    return re.findall(r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)\s*\{", text, flags=re.M)


def test_for_script(repo: Path, script: Path) -> bool:
    stem = script.stem.replace("-", "_")
    tests = "\n".join(read(path) for path in repo.glob("tests/test_*.py"))
    return stem in tests or script.name in tests


def add_finding(findings: list[Finding], **kwargs: object) -> None:
    findings.append(Finding(**kwargs))  # type: ignore[arg-type]


def review_script(repo: Path, path: Path) -> list[Finding]:
    text = read(path)
    rel = str(path.relative_to(repo))
    findings: list[Finding] = []
    lc = line_count(text)
    suffix = path.suffix

    if lc > 320:
        add_finding(
            findings,
            artifact=rel,
            line_start=1,
            line_end=lc,
            principle="SRP",
            severity="ACTION",
            decision="DECOMPOSE",
            issue="Script is large enough to hide multiple responsibilities.",
            observed_evidence=f"{rel} has {lc} lines.",
            evidence_level="observed",
            confidence="adequate",
            unknowns=[],
            verification="After decomposition, rerun full unittest discovery and the script's narrow tests.",
            residual_risk="Large script may continue to couple orchestration, rendering, parsing, and file mutation.",
            recommendation="Extract stable modules/classes/functions around one reason to change.",
        )

    hits = responsibility_hits(text)
    if len(hits) >= 3:
        add_finding(
            findings,
            artifact=rel,
            line_start=1,
            line_end=lc,
            principle="SRP",
            severity="ACTION",
            decision="DECOMPOSE",
            issue="Script appears to mix several responsibilities.",
            observed_evidence=f"Detected responsibility markers: {', '.join(hits)}.",
            evidence_level="observed",
            confidence="adequate",
            unknowns=[],
            verification="Create characterization tests for current behavior, then extract one responsibility per patch.",
            residual_risk="Mixed responsibilities make checkpoint UX and state-machine changes fragile.",
            recommendation="Separate orchestration from rendering, parsing, persistence, and review policy.",
        )

    if suffix == ".sh" and SRP_MIXED_RESPONSIBILITY_PATTERNS["shell_embedded_python"].search(text):
        line = find_line(text, "<<'PY")
        add_finding(
            findings,
            artifact=rel,
            line_start=line,
            line_end=line,
            principle="SRP/DIP",
            severity="ACTION",
            decision="DECOMPOSE",
            issue="Shell script embeds Python logic.",
            observed_evidence="Shell heredoc invokes Python from inside the script.",
            evidence_level="observed",
            confidence="high",
            unknowns=[],
            verification="Extract embedded Python to a named Python script with tests; shell calls it through a stable CLI.",
            residual_risk="Shell quoting and heredoc bugs can break checkpoint flow.",
            recommendation="Move Python logic into scripts/*.py and keep shell as orchestration only.",
        )

    if suffix == ".sh" and SRP_MIXED_RESPONSIBILITY_PATTERNS["checkpoint_rendering"].search(text):
        line = min(
            [find_line(text, marker) for marker in ["Current checkpoint:", "Human decision needed:", "Continuation protocol:", "Blocking reason:"] if marker in text]
            or [1]
        )
        add_finding(
            findings,
            artifact=rel,
            line_start=line,
            line_end=line,
            principle="OCP/SRP",
            severity="ACTION",
            decision="DECOMPOSE",
            issue="Checkpoint user-facing rendering appears inside shell orchestration.",
            observed_evidence="Checkpoint UX phrases are present in shell runner.",
            evidence_level="observed",
            confidence="adequate",
            unknowns=[],
            verification="Renderer behavior tests cover all checkpoint types; shell source tests only check invocation/guards.",
            residual_risk="Adding checkpoint types requires editing brittle shell prose.",
            recommendation="Route checkpoint UX through scripts/render_hldspec_checkpoint.py or equivalent renderer.",
        )

    if suffix == ".py" and not has_main_guard(text) and rel.startswith("scripts/"):
        add_finding(
            findings,
            artifact=rel,
            line_start=1,
            line_end=min(lc, 20),
            principle="Interface Contract",
            severity="ACTION",
            decision="FIX",
            issue="Python script lacks explicit CLI main guard.",
            observed_evidence="No if __name__ == \"__main__\" guard found.",
            evidence_level="observed",
            confidence="high",
            unknowns=[],
            verification="Run the module as a CLI or test import behavior.",
            residual_risk="Importing script may execute side effects or make CLI boundary unclear.",
            recommendation="Expose a main() and guard all CLI execution.",
        )

    if suffix == ".py":
        funcs = public_functions(text)
        if len(funcs) > 18:
            add_finding(
                findings,
                artifact=rel,
                line_start=1,
                line_end=lc,
                principle="SRP/ISP",
                severity="ACTION",
                decision="DECOMPOSE",
                issue="Python module exposes many functions, suggesting broad responsibility.",
                observed_evidence=f"Detected {len(funcs)} top-level functions.",
                evidence_level="observed",
                confidence="adequate",
                unknowns=[],
                verification="Split by responsibility and preserve tests for public CLI behavior.",
                residual_risk="Large function surface encourages accidental coupling.",
                recommendation="Group cohesive functions into smaller modules or classes with narrow interfaces.",
            )

    if suffix == ".sh":
        funcs = shell_functions(text)
        if len(funcs) > 6:
            add_finding(
                findings,
                artifact=rel,
                line_start=1,
                line_end=lc,
                principle="SRP",
                severity="ACTION",
                decision="DECOMPOSE",
                issue="Shell runner exposes many functions.",
                observed_evidence=f"Detected shell functions: {', '.join(funcs)}.",
                evidence_level="observed",
                confidence="adequate",
                unknowns=[],
                verification="Extract non-orchestration behavior into Python CLIs with tests.",
                residual_risk="Shell remains hard to test and easy to break with quoting changes.",
                recommendation="Keep shell wrapper thin; move policy and rendering out.",
            )

    if not test_for_script(repo, path) and rel.startswith("scripts/"):
        add_finding(
            findings,
            artifact=rel,
            line_start=1,
            line_end=lc,
            principle="Testability",
            severity="ACTION",
            decision="FIX",
            issue="No obvious test references this script.",
            observed_evidence=f"No test file text references `{path.stem}` or `{path.name}`.",
            evidence_level="observed",
            confidence="weak",
            unknowns=["Script may be exercised indirectly through an integration test."],
            verification="Add direct contract test or document indirect test coverage.",
            residual_risk="Refactors may silently break CLI behavior.",
            recommendation="Add a narrow test for CLI contract, output schema, or generated artifact.",
        )

    return findings


def summarize(findings: list[Finding]) -> dict[str, object]:
    by_principle: dict[str, int] = {}
    by_decision: dict[str, int] = {}
    by_artifact: dict[str, int] = {}
    for finding in findings:
        by_principle[finding.principle] = by_principle.get(finding.principle, 0) + 1
        by_decision[finding.decision] = by_decision.get(finding.decision, 0) + 1
        by_artifact[finding.artifact] = by_artifact.get(finding.artifact, 0) + 1
    return {
        "total_findings": len(findings),
        "by_principle": by_principle,
        "by_decision": by_decision,
        "top_artifacts": sorted(by_artifact.items(), key=lambda item: item[1], reverse=True)[:20],
    }


def render_md(review: dict[str, object]) -> str:
    findings = review["findings"]
    assert isinstance(findings, list)
    summary = review["summary"]
    assert isinstance(summary, dict)

    lines = [
        "# HLDspec Architecture Review",
        "",
        "made by AI",
        "",
        f"Status: `{review['status']}`",
        f"Scripts reviewed: `{review['scripts_reviewed']}`",
        f"Findings: `{len(findings)}`",
        "",
        "## Uncle Bob / SOLID Lens",
        "",
        "- SRP: one reason to change per script/module.",
        "- OCP: new checkpoint/review behavior should be added through extension points, not shell text rewrites.",
        "- DIP: shell runners depend on stable Python CLIs, not embedded implementation details.",
        "- ISP: interfaces should be narrow; checkpoint renderers, review tools, and orchestrators have separate contracts.",
        "- Testability: behavior tests should exercise rendered outputs and JSON contracts, not only implementation strings.",
        "",
        "## RunSkeptic Trace Contract",
        "",
    ]

    for field in RUNSKEPTIC_REQUIRED_FIELDS:
        lines.append(f"- `{field}`")

    lines += [
        "",
        "## Summary",
        "",
        "```json",
        json.dumps(summary, indent=2, sort_keys=True),
        "```",
        "",
        "## Findings",
        "",
    ]

    if not findings:
        lines.append("- none")
    else:
        for item in findings:
            assert isinstance(item, dict)
            lines += [
                f"### {item['artifact']}:{item['line_start']}-{item['line_end']} - {item['principle']}",
                "",
                f"- severity: `{item['severity']}`",
                f"- decision: `{item['decision']}`",
                f"- issue: {item['issue']}",
                f"- observed evidence: {item['observed_evidence']}",
                f"- evidence level: `{item['evidence_level']}`",
                f"- confidence: `{item['confidence']}`",
                f"- unknowns: {', '.join(item['unknowns']) if item['unknowns'] else 'none'}",
                f"- verification: {item['verification']}",
                f"- residual risk: {item['residual_risk']}",
                f"- recommendation: {item['recommendation']}",
                "",
            ]

    lines += [
        "## Gate meaning",
        "",
        "- `PASS`: no architecture findings.",
        "- `ACTION`: refactor candidates exist; fix one responsibility seam per patch.",
        "- `CONFLICT`: architecture findings require human decision before refactor.",
        "",
    ]

    return "\n".join(lines)


def build_review(repo: Path, include_tests: bool = False) -> dict[str, object]:
    paths = script_paths(repo, include_tests=include_tests)
    findings: list[Finding] = []
    for path in paths:
        findings.extend(review_script(repo, path))

    status = "ACTION" if findings else "PASS"
    return {
        "schema_version": 1,
        "status": status,
        "repo": str(repo),
        "scripts_reviewed": len(paths),
        "summary": summarize(findings),
        "findings": [asdict(item) for item in findings],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Review HLDspec scripts with Uncle Bob/SOLID + RunSkeptic evidence fields.")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--output-dir", default=".hldspec-architecture-review")
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--fail-on-action", action="store_true")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out = Path(args.output_dir)
    if not out.is_absolute():
        out = repo / out
    out.mkdir(parents=True, exist_ok=True)

    review = build_review(repo, include_tests=args.include_tests)
    json_path = out / "hldspec_architecture_review.json"
    md_path = out / "hldspec_architecture_review.md"
    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(review), encoding="utf-8")

    print(f"HLDspec architecture review: {review['status']}")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- findings: {len(review['findings'])}")

    if args.fail_on_action and review["status"] != "PASS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
