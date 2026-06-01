"""The HLD-DESC canonical line: one controlled sentence per section that is
equivalent to a set of property:value signals.

Design (see docs / the constitution-building thread):
- One standard line of description per HLD section, carried on an ``HLD-DESC:``
  metadata line. It reads as a sentence but every value before the evidence
  quote is drawn from a CLOSED vocabulary (``hld_vocabulary.json``), so parsing
  back into fields is deterministic — not the keyword-matching-meaning guesswork
  it replaces.
- Closed but not fixed: an unknown term is flagged, never silently accepted; the
  vocabulary file is extended additively (a reviewed change) when a new signal is
  genuinely needed.

Frame::

    <ID> is <scope> <role> at <risk> risk, touching <surfaces>; "<evidence>".

e.g. ``HLD-011 is out-of-scope governance at low risk, touching none; "sockets,
HTTP API, web UI deliberately stripped".``

The quoted evidence tail is for humans and is never parsed into a signal.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

VOCAB_PATH = Path(__file__).with_name("hld_vocabulary.json")

# Frozen frame. The leading "<ID> is" is optional (a section already knows its id).
CANON_RE = re.compile(
    r"^\s*(?:(?P<id>HLD-\d+)\s+is\s+)?"
    r"(?P<scope>[A-Za-z_-]+)\s+(?P<role>[A-Za-z_-]+)\s+"
    r"at\s+(?P<risk>[A-Za-z_-]+)\s+risk,\s+"
    r"touching\s+(?P<surfaces>[^;]+?)\s*;\s*"
    r'"(?P<evidence>.*)"\s*\.?\s*$'
)

_SECTION_RE = re.compile(r"^##\s+(?P<id>HLD-\d+)\b", re.MULTILINE)
_DESC_RE = re.compile(r"^HLD-DESC:\s*(?P<value>.+?)\s*$", re.MULTILINE)

# Scopes that mean "do not derive requirements/surfaces from this section."
EXCLUDED_SCOPES = frozenset({"out_of_scope", "non_goal"})


def load_vocabulary(path: Path | None = None) -> dict[str, list[str]]:
    data = json.loads((path or VOCAB_PATH).read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _norm(token: str) -> str:
    return token.strip().lower().replace("-", "_")


def _parse_surfaces(phrase: str) -> list[str]:
    raw = re.split(r",|\band\b", phrase)
    surfaces = [_norm(s) for s in raw if s.strip()]
    return [] if surfaces == ["none"] else surfaces


def parse_canonical_line(line: str) -> dict | None:
    """Parse an HLD-DESC value into a structured record, or None if it does not
    match the frame. Values are normalized (lowercase, hyphens->underscores);
    terms are NOT validated here — call validate_record for that."""
    match = CANON_RE.match(line.strip())
    if not match:
        return None
    return {
        "id": match.group("id"),
        "scope": _norm(match.group("scope")),
        "role": _norm(match.group("role")),
        "risk": _norm(match.group("risk")),
        "surfaces": _parse_surfaces(match.group("surfaces")),
        "evidence": match.group("evidence"),
    }


def validate_record(record: dict, vocab: dict[str, list[str]] | None = None) -> list[str]:
    """Return one message per term not present in the (closed) vocabulary."""
    vocab = vocab or load_vocabulary()
    errors: list[str] = []
    for field in ("scope", "role", "risk"):
        value = record.get(field)
        if value and value not in vocab.get(field, []):
            errors.append(f"unknown {field} term '{value}' (not in vocabulary)")
    for surface in record.get("surfaces", []):
        if surface not in vocab.get("surfaces", []):
            errors.append(f"unknown surface term '{surface}' (not in vocabulary)")
    return errors


def render_canonical_line(record: dict) -> str:
    surfaces = record.get("surfaces") or []
    if not surfaces:
        phrase = "none"
    elif len(surfaces) == 1:
        phrase = surfaces[0]
    else:
        phrase = ", ".join(surfaces[:-1]) + " and " + surfaces[-1]
    prefix = f"{record['id']} is " if record.get("id") else ""
    scope = record["scope"].replace("_", "-")
    return f'{prefix}{scope} {record["role"]} at {record["risk"]} risk, touching {phrase}; "{record.get("evidence", "")}".'


def section_records(hld_text: str) -> dict[str, dict]:
    """Map section id -> parsed HLD-DESC record, for sections that carry one."""
    records: dict[str, dict] = {}
    starts = [(m.group("id"), m.start()) for m in _SECTION_RE.finditer(hld_text)]
    for i, (sid, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(hld_text)
        body = hld_text[start:end]
        desc = _DESC_RE.search(body)
        if not desc:
            continue
        record = parse_canonical_line(desc.group("value"))
        if record is not None:
            record.setdefault("id", sid)
            records[sid] = record
    return records


def strip_excluded_sections(hld_text: str) -> str:
    """Return hld_text with the bodies of out_of_scope/non_goal sections removed,
    so downstream keyword scans never derive signals from excluded scope. Sections
    without an HLD-DESC line (the common case today) are untouched — no regression."""
    records = section_records(hld_text)
    excluded = {sid for sid, rec in records.items() if rec.get("scope") in EXCLUDED_SCOPES}
    if not excluded:
        return hld_text

    starts = [(m.group("id"), m.start()) for m in _SECTION_RE.finditer(hld_text)]
    out: list[str] = []
    cursor = 0
    for i, (sid, start) in enumerate(starts):
        end = starts[i + 1][1] if i + 1 < len(starts) else len(hld_text)
        out.append(hld_text[cursor:start])  # text before this section (preamble/gap)
        if sid not in excluded:
            out.append(hld_text[start:end])
        cursor = end
    out.append(hld_text[cursor:])
    return "".join(out)
