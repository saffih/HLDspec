#!/usr/bin/env python3
"""SpecKit drive: run bundles non-stop until something needs attention.

Drives `speckit_invocation_queue.json` / `speckit_bundle_queue.json` bundles
in dependency order, one self-driving bundle prompt at a time, auto-continuing
on RunSkeptic PASS + verified progress. Exit codes mirror hldspec_v2.py:

    0  stopped cleanly (e.g. hit --max-bundles)
    2  stopped for human attention (RunSkeptic ACTION/CONFLICT, reassessment
       request, or implementation approval gate)
    3  blocked / unassessable / errored
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.speckit_drive_loop import ATTENTION_REASONS, CLEAN_STOP_REASONS, render_drive_loop_report, run_drive_loop


def main() -> int:
    parser = argparse.ArgumentParser(description="Drive SpecKit bundles non-stop until attention is needed.")
    parser.add_argument("workspace")
    parser.add_argument(
        "--speckit-root",
        default=None,
        help="Where SpecKit writes specs/<short-name>/. Defaults to <workspace>/specs.",
    )
    parser.add_argument("--runtime", default="claude", choices=("claude", "codex", "devin"))
    parser.add_argument("--agent-cmd", default="claude", help="Headless agent command to invoke per bundle.")
    parser.add_argument("--max-bundles", type=int, default=None, help="Stop after running this many bundles.")
    parser.add_argument("--json", action="store_true", help="Emit JSON summary instead of text.")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    speckit_root = Path(args.speckit_root).resolve() if args.speckit_root else (workspace / "specs")

    summary = run_drive_loop(
        workspace,
        speckit_root,
        agent_cmd=args.agent_cmd,
        runtime=args.runtime,
        max_bundles=args.max_bundles,
    )

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(render_drive_loop_report(summary))

    stop_reason = summary.get("stop_reason", "")
    if stop_reason in ATTENTION_REASONS:
        return 2
    if stop_reason in CLEAN_STOP_REASONS:
        return 0
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
