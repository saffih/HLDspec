#!/usr/bin/env python3
"""Assess SpecKit progress and emit the next action / prompt to run.

HLDspec hands the ball to SpecKit, then needs to catch up on where SpecKit
left off. This script inspects the SpecKit project, derives per-spec phase
status, and prints what to run next. Exit codes mirror hldspec_v2.py:

    0  a clear next step exists (continue)
    2  a human checkpoint is required (e.g. implementation approval)
    3  blocked / unassessable -> use the do-it-all handoff
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.speckit_execution_state import next_action, write_execution_state


def render(action: dict[str, Any]) -> str:
    lines = [f"SpecKit next action: {action.get('mode', '')}", "", action.get("headline", ""), ""]
    if action.get("bundle_prompt"):
        lines += [f"Run this bundle prompt: {action['bundle_prompt']}", ""]
    if action.get("instruction"):
        lines += [action["instruction"], ""]
    ordered = action.get("ordered_prompts") or []
    if action.get("mode") == "DO_IT_ALL" and ordered:
        lines += ["Ordered bundle prompts:"]
        lines += [f"  {i}. {path}" for i, path in enumerate(ordered, start=1)]
        lines += [""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Assess SpecKit progress and emit the next action.")
    parser.add_argument("workspace")
    parser.add_argument(
        "--speckit-root",
        default=None,
        help="Where SpecKit writes specs/<short-name>/. Defaults to <workspace>/specs.",
    )
    parser.add_argument("--runtime", default="claude", choices=("claude", "codex", "devin"))
    parser.add_argument("--json", action="store_true", help="Emit JSON (state + action) instead of text.")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    speckit_root = Path(args.speckit_root).resolve() if args.speckit_root else (workspace / "specs")

    payload = write_execution_state(workspace, speckit_root)
    action = next_action(payload, runtime=args.runtime)

    if args.json:
        print(json.dumps({"state": payload, "action": action}, indent=2, sort_keys=True))
    else:
        print(render(action))

    return int(action.get("exit_code", 3))


if __name__ == "__main__":
    raise SystemExit(main())
