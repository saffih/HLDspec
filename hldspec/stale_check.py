"""Stale-artifact detection — classifies HLD changes by impact on derived artifacts.

Inputs: the old reference map (from `hld_reference_map.json`) and the new HLD.
Only the *declared* derived artifacts from the source package are inspected (no
broad repo scan) — by default `speckit_single_spec_input.md`, which cites HLD
anchors as `(HLD-NNN)`.

Classification (structural defaults; a MODEL_SMART reviewer may downgrade REVIEW
to SAFE, never the reverse):

- SAFE       : no change. Only emitted when nothing changed — never on ambiguity.
- REVIEW     : added anchor, moved anchor (same hash), or changed-but-uncited.
- REGENERATE : changed anchor that a derived artifact cites — the artifact is stale.
- BLOCK      : deleted anchor cited by a derived artifact, or a derived artifact
               cites an anchor that does not exist (unknown citation).

`stale_anchors` (BLOCK + REGENERATE) feed the gate validator and block continuation.
The hash strategy flips on any text change, so a formatting-only edit cannot be
auto-classified SAFE; an uncited formatting change is REVIEW (not PASS), and a cited
one is REGENERATE — the cautious default the spec requires.
"""
from __future__ import annotations

import re

from .hld_diff import AnchorDiff, diff_reference_maps
from .script_io import load_json_dict, write_json_dict
from .workspace_adapter import TargetWorkspaceAdapter

SCHEMA_VERSION = 1

SAFE = "SAFE"
REVIEW = "REVIEW"
REGENERATE = "REGENERATE"
BLOCK = "BLOCK"

CITATION_RE = re.compile(r"\b(HLD-\d{3})\b")

# Declared derived artifacts that cite anchors (relative to the source package dir).
DEFAULT_DERIVED_FILES: tuple[str, ...] = ("speckit_single_spec_input.md",)

CHANGE_IMPACT_FILE = "hld_change_impact.json"
STALE_REPORT_FILE = "stale_artifact_report.md"


def citations_in_text(text: str) -> set[str]:
    return set(CITATION_RE.findall(text))


def collect_derived_citations(source_dir, derived_files=DEFAULT_DERIVED_FILES) -> dict[str, list[str]]:
    """Map anchor -> sorted list of derived files that cite it."""
    cited: dict[str, set[str]] = {}
    for filename in derived_files:
        path = source_dir / filename
        if not path.is_file():
            continue
        for anchor in citations_in_text(path.read_text(encoding="utf-8")):
            cited.setdefault(anchor, set()).add(filename)
    return {anchor: sorted(files) for anchor, files in cited.items()}


def classify_changes(diff: AnchorDiff, cited: dict[str, list[str]], new_anchors: set[str]) -> list[dict]:
    changes: list[dict] = []
    for anchor in diff.deleted:
        cited_by = cited.get(anchor, [])
        changes.append({
            "anchor": anchor, "kind": "deleted",
            "classification": BLOCK if cited_by else REVIEW,
            "cited_by": cited_by,
        })
    for anchor in diff.changed:
        cited_by = cited.get(anchor, [])
        changes.append({
            "anchor": anchor, "kind": "changed",
            "classification": REGENERATE if cited_by else REVIEW,
            "cited_by": cited_by,
        })
    for anchor in diff.moved:
        changes.append({
            "anchor": anchor, "kind": "moved",
            "classification": REVIEW, "cited_by": cited.get(anchor, []),
        })
    for anchor in diff.added:
        changes.append({
            "anchor": anchor, "kind": "added",
            "classification": REVIEW, "cited_by": [],
        })
    # Unknown citation: a derived artifact cites an anchor that exists in neither
    # old nor new (so it never appears in the diff). Deleted-cited anchors are
    # already covered above.
    for anchor in sorted(set(cited) - new_anchors):
        if anchor in diff.deleted:
            continue
        changes.append({
            "anchor": anchor, "kind": "unknown_citation",
            "classification": BLOCK, "cited_by": cited[anchor],
        })
    return changes


def build_change_impact(old_ref_map: dict, new_ref_map: dict, *, derived_citations: dict[str, list[str]]) -> dict:
    diff = diff_reference_maps(old_ref_map, new_ref_map)
    new_anchors = set(new_ref_map.get("anchors", {}) or {})
    changes = classify_changes(diff, derived_citations, new_anchors)

    blocking = [c for c in changes if c["classification"] == BLOCK]
    regenerating = [c for c in changes if c["classification"] == REGENERATE]
    stale_anchors = sorted({
        c["anchor"] for c in changes if c["classification"] in (BLOCK, REGENERATE)
    })
    requires_smart_review = any(
        c["classification"] in (REVIEW, REGENERATE) for c in changes
    )
    if not changes:
        overall = SAFE
    elif blocking:
        overall = BLOCK
    elif regenerating:
        overall = REGENERATE
    else:
        overall = REVIEW
    return {
        "schema_version": SCHEMA_VERSION,
        "overall": overall,
        "summary": diff.to_dict(),
        "changes": changes,
        "blocking": blocking,
        "stale_anchors": stale_anchors,
        "requires_smart_review": requires_smart_review,
    }


def render_stale_report(impact: dict) -> str:
    lines = ["# Stale Artifact Report", "", f"Overall: `{impact['overall']}`", ""]
    summary = impact["summary"]
    lines.append(
        f"Anchors — added: {len(summary['added'])}, changed: {len(summary['changed'])}, "
        f"deleted: {len(summary['deleted'])}, moved: {len(summary['moved'])}"
    )
    lines.append("")
    if impact["stale_anchors"]:
        lines.append("## Stale cited anchors (block / regenerate)")
        lines.append("")
        for anchor in impact["stale_anchors"]:
            lines.append(f"- {anchor}")
        lines.append("")
    lines.append("## Changes")
    lines.append("")
    if not impact["changes"]:
        lines.append("- (none — sources unchanged)")
    for change in impact["changes"]:
        cited = ", ".join(change["cited_by"]) or "none"
        lines.append(
            f"- {change['anchor']} [{change['kind']}] -> {change['classification']} "
            f"(cited by: {cited})"
        )
    lines.append("")
    return "\n".join(lines)


def run_stale_check(
    target_root,
    new_hld_text: str,
    *,
    derived_files=DEFAULT_DERIVED_FILES,
    layout: str = "new",
    write: bool = True,
) -> dict:
    """Compare the source package's current reference map against a new HLD, classify
    impact on declared derived artifacts, and (by default) write the impact JSON +
    stale report into the source package."""
    from . import hld_marking

    adapter = TargetWorkspaceAdapter(target_root=target_root, layout=layout)
    source_dir = adapter.source_package_dir
    old_ref_map = load_json_dict(source_dir / "hld_reference_map.json")
    new_ref_map = hld_marking.build_reference_map(new_hld_text)
    derived_citations = collect_derived_citations(source_dir, derived_files)
    impact = build_change_impact(old_ref_map, new_ref_map, derived_citations=derived_citations)
    if write:
        write_json_dict(source_dir / CHANGE_IMPACT_FILE, impact)
        (source_dir / STALE_REPORT_FILE).write_text(render_stale_report(impact), encoding="utf-8")
    return impact


def load_stale_anchors(source_dir) -> list[str]:
    """Stale cited anchors recorded in hld_change_impact.json (for the gate)."""
    impact = load_json_dict(source_dir / CHANGE_IMPACT_FILE)
    return list(impact.get("stale_anchors", []) or [])
