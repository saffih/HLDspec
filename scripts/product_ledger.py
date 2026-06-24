#!/usr/bin/env python3
"""Product QA Loop Driver — Slice 1: feature-ledger inventory.

Read-only-first scan of a target app/repo that writes one canonical product QA
feature ledger:

    <target>/qa/feature-ledger.json
    <target>/qa/feature-ledger.csv

Scanner metadata/report is written under the resolved HLDspec control plane:

    <control_state_root>/sync/product_qa_loop/product-ledger-scan-report.{json,md}

The ledger is a target-owned product QA artifact, not a SpecKit artifact. This
slice does NOT invoke SpecKit, run browser tests, modify product code, or
auto-fix anything. An incompatible/manual existing ledger is never silently
overwritten — a conflict is reported and the run stops.

Trigger:   HLDspec product-ledger target: <path>
CLI:       python3 scripts/product_ledger.py --target <path>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import control_paths, feature_ledger as fl


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Product QA feature-ledger inventory (Slice 1)")
    parser.add_argument("--target", required=True, help="path to the target app/repo to scan")
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"ERROR: target is not a directory: {target}", file=sys.stderr)
        return 2

    qa_dir = fl.resolve_product_qa_dir(target)
    control_sync = control_paths.resolve_control_sync_dir(target, create=True)
    provenance_dir = control_sync / fl.PRODUCT_QA_REPORT_SUBDIR

    ledger = fl.scan_target(target)
    errors = ledger.validate()
    if errors:
        print("ERROR: scanned ledger failed validation:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 3

    result = fl.safe_write(ledger, qa_dir, provenance_dir)

    meta = {
        "target": str(target),
        "qa_dir": str(qa_dir),
        "rows_scanned": len(ledger.rows),
        "rows_written": len(ledger.rows) if result.written else 0,
        "written": result.written,
        "conflict": result.conflict,
        "conflict_reason": result.reason,
    }
    report = fl.write_scan_report(control_sync, meta)

    if result.conflict:
        print(f"CONFLICT: {result.reason}")
        print(f"  Existing ledger left untouched: {qa_dir / fl.LEDGER_JSON}")
        print(f"  Conflict report: {report.json_path}")
        return 4

    print(f"Wrote {len(ledger.rows)} ledger rows:")
    print(f"  {qa_dir / fl.LEDGER_JSON}")
    print(f"  {qa_dir / fl.LEDGER_CSV}")
    print(f"  scan report: {report.json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
