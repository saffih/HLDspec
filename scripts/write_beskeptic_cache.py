#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CACHE_JSON = ROOT / "docs" / "BESKEPTIC_FRAMEWORK_CACHE.json"
CACHE_MD = ROOT / "docs" / "BESKEPTIC_FRAMEWORK_CACHE.md"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write the HLDspec Beskeptic framework cache into a workspace.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    json_out = out_dir / "beskeptic_framework_cache.json"
    md_out = out_dir / "beskeptic_framework_cache.md"

    json_out.write_text(CACHE_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    md_out.write_text(CACHE_MD.read_text(encoding="utf-8"), encoding="utf-8")

    cache = json.loads(json_out.read_text(encoding="utf-8"))
    print("Beskeptic framework cache written:")
    print(f"- json: {json_out}")
    print(f"- report: {md_out}")
    print(f"- source: {cache['authoritative_source']['repository']}/{cache['authoritative_source']['path']}")
    print(f"- flow: {cache['phase_flow_text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
