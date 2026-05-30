#!/usr/bin/env python3
"""Report each HLD anchor's implementation status from evidence.

The planner re-plans the whole HLD every run with no notion of "already built,"
so a human can't tell from the plan what is implemented vs deferred vs missing.
This derives that per anchor, deterministically, from two evidence sources:

- the anchor's own STATUS metadata (planned -> deferred), and
- whether the anchor id is cited by a test in the given test corpus.

Statuses use the anchor_coverage vocabulary: implemented / deferred /
missing / documented. It cannot infer "partial-by-design" (runner-judgment)
anchors — those still need a human note — but it makes the implemented/
deferred/missing split explicit and repeatable.

Usage:
  python scripts/hld_anchor_status.py --hld HLD.md --tests test_flow.py
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ANCHOR = re.compile(r"^## (HLD-\d{3}) - (.+)$", re.M)


def parse_anchors(hld_text: str) -> list[dict]:
    out = []
    for m in ANCHOR.finditer(hld_text):
        block = hld_text[m.start():m.start() + 800]
        status = (re.search(r"HLD-STATUS:\s*(\w+)", block) or [None, "active"])[1]
        risk = (re.search(r"HLD-RISK:\s*(\w+)", block) or [None, "?"])[1]
        out.append({"id": m.group(1), "title": m.group(2).strip(),
                    "status": status, "risk": risk})
    return out


def classify(anchor: dict, cited: bool) -> str:
    if anchor["status"].lower() == "planned":
        return "deferred"
    if cited:
        return "implemented"
    if anchor["risk"].upper() == "HIGH":
        return "missing"
    return "documented"


def build(hld: Path, tests: list[Path]) -> dict:
    corpus = "\n".join(p.read_text(encoding="utf-8") for p in tests if p.exists())
    anchors = parse_anchors(hld.read_text(encoding="utf-8"))
    rows = []
    for a in anchors:
        a["coverage_status"] = classify(a, a["id"] in corpus)
        rows.append(a)
    return {"hld": str(hld), "anchors": rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--hld", required=True)
    ap.add_argument("--tests", nargs="+", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report = build(Path(args.hld), [Path(t) for t in args.tests])
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"Anchor implementation status — {report['hld']}")
    for a in report["anchors"]:
        print(f"  {a['id']:8} {a['coverage_status']:12} ({a['risk']:6}) {a['title'][:44]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
