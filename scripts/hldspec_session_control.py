#!/usr/bin/env python3
"""Generate (and optionally render commands for) the HLDspec session-plan control
plane for a target repo.

Default backend is dry-run: it writes session_plan.json + bounded subagent packets
+ runner/consultant prompts + runbook under the target's
.hldspec/source_package/. Nothing is launched. `--execute` is required before any
launch commands are emitted for execution.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import session_control as sc


def resolve_execution(backend: str, execute: bool) -> tuple[bool, str]:
    """Whether to emit launch commands for execution, plus a human note.

    dry-run never emits launch commands. Any launching backend requires --execute.
    """
    if backend == "dry-run":
        return False, "dry-run: wrote control files only; no commands emitted."
    if not execute:
        return False, f"backend '{backend}' selected but --execute not supplied; no launch commands emitted."
    return True, f"--execute set: emitting '{backend}' commands (you launch them; this tool does not spawn agents)."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="HLDspec session-plan control plane generator.")
    parser.add_argument("--target", required=True, help="Target repo path.")
    parser.add_argument("--hldspec-repo", default=str(ROOT), help="HLDspec repo path.")
    parser.add_argument("--backend", default=sc.DEFAULT_BACKEND, choices=sc.BACKENDS)
    parser.add_argument("--session-name", default=sc.DEFAULT_SESSION_NAME)
    parser.add_argument("--current-gate", default=None, help="Gate the session is currently at.")
    parser.add_argument("--execute", action="store_true", help="Emit launch commands for a non-dry-run backend.")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()

    plan_kwargs = dict(backend=args.backend, session_name=args.session_name)
    if args.current_gate:
        plan_kwargs["current_gate"] = args.current_gate
    plan = sc.build_session_plan(target, Path(args.hldspec_repo).resolve(), **plan_kwargs)

    written = sc.write_session_artifacts(target, plan)

    print("HLDspec session control generated:")
    print(f"- backend: {plan['backend']}")
    print(f"- session: {plan['session_name']}")
    print(f"- current gate: {plan['current_gate']}")
    print(f"- target: {target}")
    for name, path in written.items():
        print(f"- {name}: {path}")

    emit, note = resolve_execution(args.backend, args.execute)
    print(f"\n{note}")
    if emit:
        if args.backend == "tmux":
            print("\n# tmux commands (run these yourself):")
            for cmd in sc.render_tmux_commands(plan):
                print(cmd)
        else:
            print("\n# role commands (run these yourself):")
            for role, cmd in sc.render_role_commands(plan).items():
                print(f"# {role}\n{cmd}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
