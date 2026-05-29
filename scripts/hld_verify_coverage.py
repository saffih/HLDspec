#!/usr/bin/env python3
"""HLD-VERIFY coverage gate.

Turns the slice_test_policy rule "no HLD anchor may be marked implemented
without test evidence" from prose into a deterministic check: every HIGH-risk
HLD section carries an HLD-VERIFY invariant, and each such anchor must be cited
by at least one test in the test corpus (by its `HLD-NNN` id).

Convention: tests reference the anchor they cover, e.g. a comment `# HLD-004`.
This makes the regression net self-enforcing — add a HIGH-risk section to the
HLD and this gate fails until its invariant has a failing-if-violated test.

Usage:
    hld_verify_coverage.py --hld HLD.md --tests tests/ test_foo.py \
        [--waive HLD-007 --waive ...] [--output coverage.md] [--strict]

With --strict, exits 2 when any HIGH-risk invariant is uncovered (and unwaived),
mirroring review_spec_build_plan.py --strict.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hld_map

TEST_NAME_HINT = "test"
TEXT_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".go", ".rs", ".java", ".rb", ".md"}


def collect_test_text(paths: list[str]) -> str:
    """Concatenate the text of test files under the given paths."""
    chunks: list[str] = []
    for raw in paths:
        p = Path(raw)
        files = [p] if p.is_file() else sorted(p.rglob("*")) if p.is_dir() else []
        for f in files:
            if not f.is_file() or f.suffix.lower() not in TEXT_SUFFIXES:
                continue
            if p.is_dir() and TEST_NAME_HINT not in f.name.lower():
                continue
            try:
                chunks.append(f.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError):
                continue
    return "\n".join(chunks)


def build_coverage(hld_path: Path, test_text: str, waived: set[str]) -> dict:
    parsed = hld_map.parse_hld_file(hld_path)
    rows = []
    for section in parsed.sections:
        if section.metadata_value("HLD-RISK").upper() != "HIGH":
            continue
        verify = section.metadata_value("HLD-VERIFY")
        covered = section.id in test_text
        status = "covered" if covered else ("waived" if section.id in waived else "MISSING")
        rows.append({
            "id": section.id,
            "title": section.title,
            "verify": verify,
            "status": status,
        })
    missing = [r["id"] for r in rows if r["status"] == "MISSING"]
    return {
        "hld": str(hld_path),
        "high_risk_anchors": [r["id"] for r in rows],
        "rows": rows,
        "missing": missing,
        "decision": "FAIL" if missing else "PASS",
        "validation_errors": parsed.validation_errors,
    }


def render_md(cov: dict) -> str:
    lines = [
        "# HLD-VERIFY Coverage",
        "",
        f"Decision: `{cov['decision']}`",
        f"HIGH-risk anchors: `{len(cov['high_risk_anchors'])}`",
        f"Missing coverage: `{len(cov['missing'])}`",
        "",
        "## Invariants",
        "",
    ]
    for r in cov["rows"]:
        mark = {"covered": "x", "waived": "~", "MISSING": " "}[r["status"]]
        lines.append(f"- [{mark}] **{r['id']}** {r['title']} — {r['status']}")
        if r["verify"]:
            lines.append(f"      verify: {r['verify']}")
    if cov["missing"]:
        lines += ["", "## Action", "",
                  "Write a failing-if-violated test citing each id, or waive with reason:"]
        lines += [f"- {a}" for a in cov["missing"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="HLD-VERIFY test coverage gate.")
    parser.add_argument("--hld", default="HLD.md")
    parser.add_argument("--tests", nargs="+", default=["."])
    parser.add_argument("--waive", action="append", default=[])
    parser.add_argument("--output", help="Markdown report path.")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    hld_path = Path(args.hld)
    if not hld_path.exists():
        print(f"HLD not found: {hld_path}")
        return 1

    cov = build_coverage(hld_path, collect_test_text(args.tests), set(args.waive))
    md = render_md(cov)
    if args.output:
        out = Path(args.output)
        out.write_text(md, encoding="utf-8")
        out.with_suffix(".json").write_text(json.dumps(cov, indent=2), encoding="utf-8")

    print(f"HLD-VERIFY coverage: {cov['decision']}")
    print(f"- HIGH-risk anchors: {len(cov['high_risk_anchors'])}")
    print(f"- missing: {cov['missing'] or 'none'}")
    if cov["validation_errors"]:
        print(f"- WARNING invalid HLD: {cov['validation_errors']}")

    if args.strict and cov["missing"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
