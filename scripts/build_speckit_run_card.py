#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.speckit_run_card import write_run_cards


def main() -> int:
    parser = argparse.ArgumentParser(description="Build first-class SpecKit Run Cards from approved HLDspec prework.")
    parser.add_argument("workspace")
    parser.add_argument(
        "--allow-unapproved-preview",
        action="store_true",
        help="Generate PREVIEW Run Cards without approved prework. Preview cards are not executable handoffs.",
    )
    args = parser.parse_args()
    result = write_run_cards(Path(args.workspace), allow_unapproved_preview=args.allow_unapproved_preview)
    print(json.dumps(result, indent=2, sort_keys=True))
    if isinstance(result, dict) and result.get("status") in {"ACTION", "CONFLICT"}:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
