#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


MARKER_BEGIN = "<!-- HLDSPEC-DECISION-LOG:BEGIN -->"
MARKER_END = "<!-- HLDSPEC-DECISION-LOG:END -->"


def replace_or_append(source_text: str, appendix: str) -> str:
    pattern = re.compile(
        rf"\n?{re.escape(MARKER_BEGIN)}.*?{re.escape(MARKER_END)}\n?",
        flags=re.DOTALL,
    )
    normalized_appendix = appendix.strip() + "\n"
    if pattern.search(source_text):
        return pattern.sub("\n" + normalized_appendix, source_text).rstrip() + "\n"
    return source_text.rstrip() + "\n\n" + normalized_appendix


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply HLDspec decision appendix to the source HLD.")
    parser.add_argument("source_hld")
    parser.add_argument("appendix_md")
    parser.add_argument("--approved", action="store_true", help="Required: confirms the human approved modifying the source HLD.")
    args = parser.parse_args()

    if not args.approved:
        print("Refusing to modify source HLD without --approved.")
        return 2

    source = Path(args.source_hld)
    appendix = Path(args.appendix_md)

    if not source.exists():
        print(f"Source HLD not found: {source}")
        return 1
    if not appendix.exists():
        print(f"Appendix file not found: {appendix}")
        return 1

    source_text = source.read_text(encoding="utf-8", errors="replace")
    appendix_text = appendix.read_text(encoding="utf-8", errors="replace")
    if MARKER_BEGIN not in appendix_text or MARKER_END not in appendix_text:
        print("Appendix does not contain HLDspec decision-log markers.")
        return 1

    backup = source.with_suffix(source.suffix + ".pre-hldspec-decision-log.bak")
    if not backup.exists():
        backup.write_text(source_text, encoding="utf-8")

    source.write_text(replace_or_append(source_text, appendix_text), encoding="utf-8")
    print("Applied HLDspec decision log appendix to source HLD.")
    print(f"- source: {source}")
    print(f"- backup: {backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
