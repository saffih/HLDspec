#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow direct execution as: python scripts/hldspec_v2.py ...
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.machines.project import ProjectMachine
from hldspec.result_renderer import render_machine_result
from hldspec.state_machine import MachineContext


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run HLDspec V2 to the next state-machine checkpoint.")
    parser.add_argument("source_hld", help="Path to source HLD")
    parser.add_argument(
        "workspace",
        nargs="?",
        default=None,
        help="Workspace. Defaults to $PWD/.hldspec-v2-run",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(list(argv or sys.argv[1:]))
    workspace = Path(args.workspace).expanduser() if args.workspace else Path.cwd() / ".hldspec-v2-run"

    context = MachineContext(
        repo_root=str(ROOT),
        source_hld=str(Path(args.source_hld).expanduser()),
        workspace=str(workspace),
    )

    result = ProjectMachine().run(context)
    print(render_machine_result(result), end="")
    return int(result.exit_code())


if __name__ == "__main__":
    raise SystemExit(main())
