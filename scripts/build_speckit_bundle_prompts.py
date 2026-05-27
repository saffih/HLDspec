#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.spec_bundle_prompts import write_bundle_prompts


def main() -> int:
    parser = argparse.ArgumentParser(description="Build runtime-aware one-go SpecKit bundle prompts.")
    parser.add_argument("workspace")
    parser.add_argument(
        "--skeptic-path",
        default="~/code/skeptic/skeptic.md",
        help="Path the prompts tell agents to read for the real RunSkeptic framework.",
    )
    args = parser.parse_args()

    result = write_bundle_prompts(Path(args.workspace), skeptic_path=args.skeptic_path)
    print(json.dumps(result, indent=2, sort_keys=True))
    if isinstance(result, dict) and result.get("status") in {"ACTION", "CONFLICT"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
