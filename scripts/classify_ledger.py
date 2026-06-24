#!/usr/bin/env python3
"""Product QA Loop Driver — Slice 2A: ledger row classifier.

Classifies rows from the product QA feature ledger into actionable categories.
Reads the target-owned ledger; writes classification output to the control
plane only. Does not modify the ledger, invoke SpecKit, create work orders,
or touch product code.

CLI:       python3 scripts/classify_ledger.py --target <path>
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import control_paths, feature_ledger as fl, ledger_classifier as lc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Product QA ledger row classifier (Slice 2A)")
    parser.add_argument("--target", required=True, help="path to the target app/repo")
    args = parser.parse_args(argv)

    target = Path(args.target).resolve()
    if not target.is_dir():
        print(f"ERROR: target is not a directory: {target}", file=sys.stderr)
        return 2

    qa_dir = fl.resolve_product_qa_dir(target)
    # Resolve now; write_classification() creates the directory only after input validation.
    control_sync = control_paths.resolve_control_sync_dir(target)

    try:
        result, paths = lc.load_and_classify(qa_dir, control_sync)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 4

    print(f"Classified {result.total_rows} ledger rows:")
    for cls_val in sorted(result.summary):
        print(f"  {cls_val}: {result.summary[cls_val]}")
    print(f"  output: {paths.json_path}")
    print(f"  report: {paths.md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
