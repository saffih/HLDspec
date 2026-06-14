#!/usr/bin/env python3
"""``hldspec refresh-target``: safely refresh target-side HLDspec/SpecKit support files.

Default mode is dry-run: shows planned writes, skipped files, conflict files, and
constitution status without writing anything. Pass ``--apply`` to perform the
planned writes.

See `hldspec/refresh_target.py` for the safety model. This command never modifies
product code, `specs/` progress artifacts, or resets/stashes/cleans the target repo,
and never runs SpecKit or git mutation commands.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import refresh_target as rt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safely refresh target-side HLDspec/SpecKit support files.")
    parser.add_argument("--target", required=True, help="Path to the target repo.")
    parser.add_argument("--dry-run", action="store_true", help="Explicit no-op alias for the default dry-run mode.")
    parser.add_argument("--apply", action="store_true", help="Write planned updates (default is dry-run).")
    parser.add_argument(
        "--adopt-constitution-managed-block",
        action="store_true",
        help=(
            "Explicitly adopt an existing unmarked constitution into managed-block mode: back up, insert the "
            "managed block at the top, preserve all existing content below. Never performed by --apply alone."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print the result as JSON instead of markdown.")
    args = parser.parse_args(list(argv or sys.argv[1:]))

    if args.dry_run and args.apply:
        parser.error("--dry-run and --apply are mutually exclusive.")
    if args.adopt_constitution_managed_block and args.apply:
        parser.error("--adopt-constitution-managed-block is a standalone step; do not combine it with --apply.")

    target = Path(args.target).expanduser().resolve()
    result = rt.refresh_target(
        target,
        apply=args.apply,
        adopt=args.adopt_constitution_managed_block,
    )

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(rt.render_refresh_report(result), end="")

    return 1 if result.get("conflict_files") else 0


if __name__ == "__main__":
    raise SystemExit(main())
