#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.agent_context_handoff import write_agent_context_handoff


def main() -> int:
    parser = argparse.ArgumentParser(description="Write runtime-facing agent context handoff artifacts after bundle prompts exist.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    result = write_agent_context_handoff(Path(args.workspace))
    print(json.dumps(result, indent=2, sort_keys=True))
    if result.get("status") == "ACTION":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
