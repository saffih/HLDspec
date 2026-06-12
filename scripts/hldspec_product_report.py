#!/usr/bin/env python3
"""Read-only Product Runability / Demo Gate report for a target.

Inspects the target (no commands run, no files modified except HLDspec
control reports) and answers: what was built, how would the user install,
test, start, and open it, and what is the next safe action.

Exit codes: 0 = PASS, 2 = ACTION/UNKNOWN (user attention), 3 = BLOCKED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.product_runability import render_product_runability_md, write_product_runability_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only product runability report for a target workspace.")
    parser.add_argument("--target", required=True)
    parser.add_argument("--json", action="store_true", help="Print the JSON report instead of markdown.")
    args = parser.parse_args()

    report = write_product_runability_report(Path(args.target))
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_product_runability_md(report))

    status = report.get("runability_status")
    if status == "PASS":
        return 0
    if status == "BLOCKED":
        return 3
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
