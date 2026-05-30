#!/usr/bin/env python3
"""Tell whether an HLDspec workspace was built from the current source HLD.

The run state machine regenerates a workspace's downstream artifacts only when they
are absent, so a workspace built from an earlier source HLD is never rebuilt when the
source changes — it silently mixes old and new content. This records the source HLD's
content hash at first-run and reports, on later runs, whether the source still matches.

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
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def fingerprint(hld: Path) -> str:
    return hashlib.sha256(hld.read_bytes()).hexdigest()


def fp_path(workspace: Path) -> Path:
    return workspace / "source_hld_fingerprint.json"


def record(workspace: Path, hld: Path) -> None:
    workspace.mkdir(parents=True, exist_ok=True)
    fp_path(workspace).write_text(
        json.dumps(
            {
                "source_hld": str(hld),
                "sha256": fingerprint(hld),
                "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def status(workspace: Path, hld: Path) -> str:
    fp = fp_path(workspace)
    if not fp.exists():
        return "absent"
    try:
        recorded = json.loads(fp.read_text(encoding="utf-8")).get("sha256")
    except Exception:
        return "absent"
    return "fresh" if recorded == fingerprint(hld) else "stale"


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
        return 0
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
