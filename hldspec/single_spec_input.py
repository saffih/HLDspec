"""Single SpecKit input generation + anchor-citation validation.

Default model (C4 resolution): ONE SpecKit input for one coherent HLD. Every
requirement claim cites the HLD anchor it derives from, in a fixed structural
form so the generator and the validator agree:

    ## Requirements
    - (HLD-001) <claim text>

A *claim* is defined narrowly: a `- ` bullet directly under the `## Requirements`
heading. Bullets in other sections (Source HLD anchors, Open Questions) are never
treated as claims, so the validator has no false positives on them. A claim that
lacks the `(HLD-NNN)` prefix, or cites an anchor not in the reference map, is
flagged as unsupported.
"""
from __future__ import annotations

import re

from . import hld_marking

CLAIM_SECTION_HEADING = "## Requirements"
ANCHORS_SECTION_HEADING = "## Source HLD Anchors"
OPEN_QUESTIONS_HEADING = "## Open Questions"
CLAIM_PREFIX_RE = re.compile(r"^- \((HLD-\d{3})\)\s")
_TBD_RE = re.compile(r"\bTBD\b")


def _summary_line(section_text: str) -> str:
    """First non-empty prose line of a section (skip heading + HLD-* metadata)."""
    for line in section_text.splitlines():
        s = line.strip()
        if not s or s.startswith("##") or s.startswith("HLD-") or s.startswith("###"):
            continue
        return s
    return ""


def collect_open_questions(hld_text: str) -> list[str]:
    """Structured signals only: sections marked needs-review, and TBD lines.
    No fuzzy '?' detection."""
    hld = hld_marking.parse(hld_text)
    out: list[str] = []
    for section in hld.sections:
        if section.metadata_value("HLD-STATUS") == "needs-review":
            out.append(f"({section.id}) status needs-review: {section.title}")
        for line in section.text.splitlines():
            if _TBD_RE.search(line):
                out.append(f"({section.id}) TBD: {line.strip()}")
    return out


def build_single_spec_input(hld_text: str, *, project_name: str = "") -> str:
    ref_map = hld_marking.build_reference_map(hld_text)
    anchors = ref_map["anchors"]
    hld = hld_marking.parse(hld_text)

    lines: list[str] = []
    title = project_name.strip() or "Single SpecKit Input"
    lines.append(f"# {title}")
    lines.append("")
    lines.append(
        "One SpecKit input derived from the approved HLD. Every requirement cites "
        "the HLD anchor it derives from. Decomposition into multiple specs happens "
        "later, only at meaningful boundaries."
    )
    lines.append("")

    lines.append(ANCHORS_SECTION_HEADING)
    lines.append("")
    if anchors:
        for anchor_id in anchors:
            meta = anchors[anchor_id]
            lines.append(f"- {anchor_id}: {meta['title']} (role={meta['role'] or 'n/a'})")
    else:
        lines.append("- (no HLD anchors found; HLD has no `## HLD-NNN` sections)")
    lines.append("")

    lines.append(CLAIM_SECTION_HEADING)
    lines.append("")
    if hld.sections:
        for section in hld.sections:
            summary = _summary_line(section.text) or section.title
            lines.append(f"- ({section.id}) {summary}")
    else:
        lines.append("- (no requirements: HLD has no anchored sections)")
    lines.append("")

    lines.append(OPEN_QUESTIONS_HEADING)
    lines.append("")
    open_qs = collect_open_questions(hld_text)
    if open_qs:
        for q in open_qs:
            lines.append(f"- {q}")
    else:
        lines.append("- (none)")
    lines.append("")

    return "\n".join(lines)


def find_unsupported_claims(spec_input_text: str, valid_anchors: set[str]) -> list[str]:
    """Flag claims under `## Requirements` that lack a valid `(HLD-NNN)` citation."""
    in_section = False
    flagged: list[str] = []
    for line in spec_input_text.splitlines():
        if line.startswith("## "):
            in_section = line.strip() == CLAIM_SECTION_HEADING
            continue
        if not in_section or not line.startswith("- "):
            continue
        if line.strip() == "- (no requirements: HLD has no anchored sections)":
            continue
        match = CLAIM_PREFIX_RE.match(line)
        if not match:
            flagged.append(f"claim missing (HLD-NNN) prefix: {line[:80]}")
        elif match.group(1) not in valid_anchors:
            flagged.append(f"claim cites unknown anchor: {line[:80]}")
    return flagged
