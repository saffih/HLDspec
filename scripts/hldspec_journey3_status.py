#!/usr/bin/env python3
"""Journey 3 Driver — read-only status CLI ("where are we?").

Answers the journey-level question for a target repo by composing existing
read-only inspectors. It **inspects, never mutates**, never runs the helper, and
never executes a toolchain step.

    hldspec_journey3_status.py [--target PATH] [--json] [--no-phase]

Default: human-readable text. `--json`: the machine-readable report. The canonical
phase is obtained from the read-only `next_feature_readiness` engine (read-only git,
an allowed observation) and injected into the pure aggregator; `--no-phase` skips it
entirely (fully subprocess-free) and reports phase as UNKNOWN_REQUIRES_READINESS_RUN.

Exit code: 0 = PASS, 1 = ACTION, 2 = BLOCKED.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from hldspec import journey3_driver  # noqa: E402
from hldspec import next_feature_readiness  # noqa: E402

_EXIT = {
    journey3_driver.STATUS_PASS: 0,
    journey3_driver.STATUS_ACTION: 1,
    journey3_driver.STATUS_BLOCKED: 2,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Journey 3 Driver — read-only status.")
    parser.add_argument("--target", default=".", help="target repo root (default: cwd)")
    parser.add_argument("--json", action="store_true", help="emit the machine-readable JSON report")
    parser.add_argument(
        "--no-phase",
        action="store_true",
        help="skip the read-only phase engine (fully subprocess-free); phase = UNKNOWN_REQUIRES_READINESS_RUN",
    )
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()

    # Phase comes from the read-only readiness engine (read-only git observation),
    # injected into the pure aggregator so the driver itself runs no subprocess.
    next_feature_report = None
    if not args.no_phase:
        next_feature_report = next_feature_readiness.build_next_feature_readiness_report(target)

    report = journey3_driver.build_journey3_status(target, next_feature_report=next_feature_report)

    if args.json:
        print(json.dumps(report, indent=2, default=str))
    else:
        print(journey3_driver.render_status_text(report))

    return _EXIT.get(report["driver_status"], 1)


if __name__ == "__main__":
    raise SystemExit(main())
