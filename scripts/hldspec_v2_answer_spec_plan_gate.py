#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


VALID_DECISIONS = {
    "FIX_PLAN",
    "ACCEPT_WITH_RATIONALE",
    "STOP_FOR_MANUAL_REDESIGN",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Answer the V2 spec-build-plan gate.")
    parser.add_argument("sync_dir", help="Path to firstrun/.specify/sync")
    parser.add_argument("--decision", required=True, choices=sorted(VALID_DECISIONS))
    parser.add_argument("--rationale", default="")
    parser.add_argument(
        "--accept-flagged-spec",
        action="append",
        default=[],
        help="Flagged planned spec ID to accept. Repeat for all flagged specs.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    sync = Path(args.sync_dir)
    if not sync.exists():
        print(f"ERROR: sync dir not found: {sync}")
        return 2

    if args.decision == "ACCEPT_WITH_RATIONALE" and not args.rationale.strip():
        print("ERROR: ACCEPT_WITH_RATIONALE requires --rationale")
        return 2

    payload = {
        "decision_id": "SPEC-BUILD-PLAN-001",
        "decision": args.decision,
        "rationale": args.rationale.strip(),
        "accepted_flagged_specs": [str(item).strip() for item in args.accept_flagged_spec if str(item).strip()],
    }

    out = sync / "spec_build_plan_gate_decision.json"

    if args.dry_run:
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0

    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Updated spec build plan gate decision: {out}")
    print(f"- decision: {payload['decision']}")
    print(f"- accepted_flagged_specs: {', '.join(payload['accepted_flagged_specs']) or 'none'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
