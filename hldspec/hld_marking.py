"""HLD marking + reference map.

Built on the existing HLD parser (`hld_map.py` at the repo root) rather than a
fork — it already handles `## HLD-NNN - Title` headings, `HLD-*` metadata, REF
semantics, code-fence masking, and duplicate-ID detection.

This module produces the marking-side source-package content:
- `HLD.marked.md`        : the HLD with a stable `<!-- ANCHOR: HLD-NNN -->` marker
                           before each section heading.
- `hld_reference_map.json`: anchor -> {heading, title, role, risk, status,
                           line_start, line_end, sha256}.

Section hash is over the *raw* section text (no normalisation): any change —
including whitespace — flips the hash. That is intentional for stale detection.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import hld_map  # noqa: E402  (repo-root module, path-guarded above)

SCHEMA_VERSION = 1
ANCHOR_MARKER = "<!-- ANCHOR: {anchor} -->"


def parse(hld_text: str):
    return hld_map.parse_hld_text(hld_text)


def anchor_ids(hld_text: str) -> set[str]:
    return {section.id for section in parse(hld_text).sections}


def _section_sha256(section_text: str) -> str:
    return hashlib.sha256(section_text.encode("utf-8")).hexdigest()


def build_reference_map(hld_text: str) -> dict:
    hld = parse(hld_text)
    anchors: dict[str, dict] = {}
    for section in hld.sections:
        anchors[section.id] = {
            "heading": f"## {section.id} - {section.title}",
            "title": section.title,
            "role": section.metadata_value("HLD-ROLE"),
            "risk": section.metadata_value("HLD-RISK"),
            "status": section.metadata_value("HLD-STATUS"),
            "line_start": section.line_start,
            "line_end": section.line_end,
            "sha256": _section_sha256(section.text),
        }
    return {"schema_version": SCHEMA_VERSION, "anchors": anchors}


def build_marked_hld(hld_text: str) -> str:
    """Insert a stable anchor marker line immediately before each section heading."""
    hld = parse(hld_text)
    # Map 1-based heading line number -> anchor id.
    heading_line_to_anchor = {s.line_start: s.id for s in hld.sections}
    out: list[str] = []
    for idx, line in enumerate(hld_text.splitlines(), start=1):
        anchor = heading_line_to_anchor.get(idx)
        if anchor:
            out.append(ANCHOR_MARKER.format(anchor=anchor))
        out.append(line)
    return "\n".join(out) + ("\n" if hld_text.endswith("\n") else "")


def validate_marking(hld_text: str) -> list[str]:
    """Return marking errors (duplicate anchors, ID/heading mismatch, etc.),
    delegating to the canonical parser's validator."""
    lines = hld_text.splitlines()
    fence_mask = hld_map.iter_code_fence_mask(lines)
    hld = hld_map.parse_hld_text(hld_text)
    return hld_map.validate_hld_map(hld, lines=lines, fence_mask=fence_mask)


def anchor_integrity_errors(hld_text: str) -> list[str]:
    """Errors that corrupt the anchor -> section mapping (and thus the reference
    map): duplicate anchors and heading/HLD-ID mismatches. This is narrower than
    `validate_marking`, which also enforces the full HLD metadata format — that
    stricter check belongs to a later marking-quality gate, not the build."""
    errors: list[str] = []
    seen: dict[str, int] = {}
    for section in parse(hld_text).sections:
        if section.id in seen:
            errors.append(f"duplicate anchor: {section.id}")
        else:
            seen[section.id] = section.line_start
        ids = section.metadata_values("HLD-ID")
        if ids and ids[0] != section.id:
            errors.append(
                f"anchor heading/HLD-ID mismatch: heading {section.id} vs HLD-ID {ids[0]}"
            )
    return errors


def duplicate_anchors(hld_text: str) -> list[str]:
    seen: dict[str, int] = {}
    dupes: list[str] = []
    for section in parse(hld_text).sections:
        if section.id in seen:
            dupes.append(section.id)
        else:
            seen[section.id] = section.line_start
    return dupes
