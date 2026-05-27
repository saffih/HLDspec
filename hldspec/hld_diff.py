"""Mechanical HLD diff — compares two reference maps by anchor and hash.

This is MODEL_SIMPLE work: it detects added / changed / deleted / moved anchors
from the hashes already in `hld_reference_map.json`. It makes no semantic
judgement; classification of *what a change means* is `stale_check` (with a
MODEL_SMART override path).

- added   : anchor present in new, absent in old.
- deleted : anchor present in old, absent in new.
- changed : anchor in both, section sha256 differs (any text change, incl. whitespace).
- moved   : anchor in both, same sha256, different line range.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AnchorDiff:
    added: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    moved: list[str] = field(default_factory=list)

    @property
    def any_change(self) -> bool:
        return bool(self.added or self.deleted or self.changed or self.moved)

    def to_dict(self) -> dict:
        return {
            "added": self.added,
            "deleted": self.deleted,
            "changed": self.changed,
            "moved": self.moved,
        }


def diff_reference_maps(old: dict, new: dict) -> AnchorDiff:
    old_a = old.get("anchors", {}) or {}
    new_a = new.get("anchors", {}) or {}
    diff = AnchorDiff(
        added=sorted(set(new_a) - set(old_a)),
        deleted=sorted(set(old_a) - set(new_a)),
    )
    for anchor in sorted(set(old_a) & set(new_a)):
        o, n = old_a[anchor], new_a[anchor]
        if o.get("sha256") != n.get("sha256"):
            diff.changed.append(anchor)
        elif (o.get("line_start"), o.get("line_end")) != (n.get("line_start"), n.get("line_end")):
            diff.moved.append(anchor)
    return diff


def diff_hlds(old_hld_text: str, new_hld_text: str) -> AnchorDiff:
    from . import hld_marking

    return diff_reference_maps(
        hld_marking.build_reference_map(old_hld_text),
        hld_marking.build_reference_map(new_hld_text),
    )
