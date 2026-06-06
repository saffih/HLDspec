#!/usr/bin/env python3
"""Tell whether an HLDspec workspace was built from the current source HLD.

Compatibility wrapper around ``hldspec.source_freshness``. The durable freshness
artifact is now ``.hldspec/source_freshness.json`` for both agent-first and legacy
shell paths.

Status (printed to stdout, one word):
  fresh   - recorded hash matches the current source HLD
  stale   - recorded hash differs (workspace built from a different source)
  absent  - no hash recorded (cannot verify; never silently adopted as fresh)

Usage:
  check_workspace_freshness.py <workspace> <source_hld>            # print status
  check_workspace_freshness.py <workspace> <source_hld> --record   # record hash
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.source_freshness import build_source_freshness, sha256_file, write_source_freshness  # noqa: E402


def fp_path(workspace: Path) -> Path:
    return workspace / ".hldspec" / "source_freshness.json"


def record(workspace: Path, hld: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    write_source_freshness(workspace, hld)


def status(workspace: Path, hld: Path) -> str:
    fp = fp_path(workspace)
    if not fp.exists():
        return "absent"
    if not hld.exists():
        return "absent"
    if not (workspace / "targetHLD" / "HLD.md").exists() and not (workspace / "HLD.md").exists():
        import json

        try:
            recorded = json.loads(fp.read_text(encoding="utf-8")).get("source_sha256")
        except Exception:
            return "absent"
        return "fresh" if recorded == sha256_file(hld) else "stale"
    report = build_source_freshness(workspace, hld)
    return "fresh" if not report.get("blocking") else "stale"


def main() -> int:
    ap = argparse.ArgumentParser(description="Report/record HLDspec workspace source freshness.")
    ap.add_argument("workspace")
    ap.add_argument("source_hld")
    ap.add_argument("--record", action="store_true", help="Record the current source hash.")
    args = ap.parse_args()

    workspace = Path(args.workspace)
    hld = Path(args.source_hld)
    if not hld.exists():
        print("absent")
        return 4
    if args.record:
        record(workspace, hld)
        print("recorded")
        return 0
    st = status(workspace, hld)
    print(st)
    # Distinct exit codes so the shell gate keys off the code, not parsed stdout.
    return {"fresh": 0, "stale": 3, "absent": 4}[st]


if __name__ == "__main__":
    raise SystemExit(main())
