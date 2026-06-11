#!/usr/bin/env python3
"""Cheap idempotent re-sync after an HLD edit. Never deletes workspace state.

Exit codes: 0 = in sync (possibly with pending work), 2 = stale specs need
attention, 3 = unassessable.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.hld_sync import render_sync_report_md, run_sync


def main() -> int:
    parser = argparse.ArgumentParser(description="Incremental HLDspec sync: section fingerprints, done ledger, Tier-2 regeneration.")
    parser.add_argument("workspace")
    parser.add_argument("--speckit-root", default=None, help="SpecKit specs root (default: <workspace>/specs).")
    parser.add_argument("--json", action="store_true", help="Print the JSON report instead of markdown.")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    speckit_root = Path(args.speckit_root) if args.speckit_root else workspace / "specs"
    report = run_sync(workspace, speckit_root)
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_sync_report_md(report))

    status = report.get("status")
    if status == "UNASSESSABLE":
        return 3
    if status == "STALE_SPECS":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
