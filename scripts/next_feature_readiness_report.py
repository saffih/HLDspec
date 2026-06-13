#!/usr/bin/env python3
"""Internal CLI for the read-only next-feature readiness report.

Not part of the documented public command facade (`scripts/hldspec_agent_session.py`).
Writes `next_feature_readiness.json/md` under the target's HLDspec sync dir and
prints the human-readable report.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import next_feature_readiness as nfr
from hldspec.state_machine import ExitCode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write/read the read-only next-feature SpecKit-ritual readiness report.")
    parser.add_argument("--target", required=True)
    args = parser.parse_args(list(argv or sys.argv[1:]))

    target = Path(args.target).expanduser().resolve()
    report = nfr.write_next_feature_readiness_report(target)
    print(nfr.render_next_feature_readiness_report(report), end="")
    return 0 if report.get("safety_status") == nfr.SAFETY_PASS else ExitCode.GATE_BLOCKED.value


if __name__ == "__main__":
    raise SystemExit(main())
