"""Tiered re-sync: iterate on the HLD without wiping the workspace (P1-009 A/C/E).

The whole-file freshness gate is binary: any HLD edit marks the entire
workspace stale and the only remedy is a full wipe, which destroys answered
decisions. This module makes re-sync incremental and non-destructive:

- Slice A — section fingerprints: per-`HLD-NNN` sha256 of the working HLD
  (via `hld_marking.build_reference_map`), diffed against the previous sync.
- Slice C — done ledger: when a spec is observed DONE, snapshot the hashes of
  its `source_hld_sections`. A later HLD edit to those sections turns the spec
  `DONE_STALE` instead of invalidating everything. If the spec's artifacts are
  rebuilt after the snapshot, the ledger re-records and the spec is DONE again.
- Slice E — `run_sync`: one cheap idempotent pass — refresh fingerprints,
  report changed sections and per-spec DONE_VERIFIED/DONE_STALE/PENDING status,
  regenerate Tier-2 prompts, and propose the next action. Never deletes
  human answers or derived plans; `HLDSPEC_FRESH=1` stays the explicit
  nuclear option elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hldspec import hld_marking
from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict
from hldspec.spec_bundles import as_dict, as_list, utc_now
from hldspec.speckit_execution_state import assess_spec, select_execution_sync_dir

SCHEMA_VERSION = 1
FINGERPRINTS_JSON = "hld_section_fingerprints.json"
DONE_LEDGER_JSON = "speckit_done_ledger.json"
SYNC_REPORT_JSON = "hldspec_sync_report.json"
SYNC_REPORT_MD = "hldspec_sync_report.md"


def working_hld_path(workspace: Path) -> Path:
    """Same resolution order as source_freshness: targetHLD copy, then legacy."""
    default = workspace / "targetHLD" / "HLD.md"
    legacy = workspace / "HLD.md"
    return default if default.is_file() or not legacy.is_file() else legacy


def section_fingerprints(hld_text: str) -> dict[str, str]:
    reference = hld_marking.build_reference_map(hld_text)
    return {anchor: str(entry.get("sha256", "")) for anchor, entry in as_dict(reference.get("anchors")).items()}


def diff_sections(old: dict[str, str], new: dict[str, str]) -> dict[str, list[str]]:
    return {
        "changed": sorted(a for a in old.keys() & new.keys() if old[a] != new[a]),
        "added": sorted(new.keys() - old.keys()),
        "removed": sorted(old.keys() - new.keys()),
        "unchanged": sorted(a for a in old.keys() & new.keys() if old[a] == new[a]),
    }


def _queue_specs(sync: Path) -> list[dict[str, Any]]:
    queue = load_json_dict(sync / "speckit_bundle_queue.json") or load_json_dict(sync / "speckit_invocation_queue.json")
    specs: list[dict[str, Any]] = []
    for bundle in as_list(queue.get("bundles")):
        for spec in as_list(as_dict(bundle).get("included_specs")):
            if isinstance(spec, dict) and spec.get("short_name"):
                specs.append(spec)
    return specs


def _artifacts_mtime(speckit_root: Path, short_name: str) -> float:
    spec_dir = speckit_root / short_name
    mtimes = [p.stat().st_mtime for p in (spec_dir / f for f in ("spec.md", "plan.md", "tasks.md")) if p.is_file()]
    return max(mtimes) if mtimes else 0.0


def _ledger_status(
    entry: dict[str, Any] | None,
    spec_sections: list[str],
    fingerprints: dict[str, str],
    artifacts_mtime: float,
    hld_mtime: float,
) -> tuple[str, dict[str, Any]]:
    """Decide DONE_VERIFIED vs DONE_STALE for a spec observed DONE_VERIFIED on disk, and the
    ledger entry to keep. Re-records when artifacts were rebuilt after the
    snapshot AND after the last HLD edit — a rebuild older than the HLD edit
    was built against the pre-edit HLD and must not clear staleness."""
    current = {anchor: fingerprints.get(anchor, "") for anchor in spec_sections}
    rebuilt = entry is not None and artifacts_mtime > float(entry.get("artifacts_mtime", 0.0))
    if entry is None or (rebuilt and artifacts_mtime >= hld_mtime):
        return "DONE_VERIFIED", {"sections": current, "recorded_at": utc_now(), "artifacts_mtime": artifacts_mtime}
    recorded = as_dict(entry.get("sections"))
    stale = sorted(
        anchor
        for anchor in spec_sections
        if str(recorded.get(anchor, "")) != current.get(anchor, "") or not current.get(anchor)
    )
    if stale:
        kept = dict(entry)
        kept["stale_sections"] = stale
        return "DONE_STALE", kept
    return "DONE_VERIFIED", dict(entry)


def run_sync(workspace: Path, speckit_root: Path) -> dict[str, Any]:
    workspace = Path(workspace)
    speckit_root = Path(speckit_root)
    hld_path = working_hld_path(workspace)
    if not hld_path.is_file():
        return {
            "schema_version": SCHEMA_VERSION,
            "generated_at": utc_now(),
            "status": "UNASSESSABLE",
            "warnings": [f"Working HLD not found: {hld_path}"],
        }

    sync = select_execution_sync_dir(workspace, create=True)
    warnings: list[str] = []

    fingerprints = section_fingerprints(hld_path.read_text(encoding="utf-8"))
    previous = as_dict(load_json_dict(sync / FINGERPRINTS_JSON).get("sections"))
    previous = {anchor: str(sha) for anchor, sha in previous.items()}
    section_diff = diff_sections(previous, fingerprints)
    if not fingerprints:
        warnings.append("Working HLD has no HLD-NNN sections; run conversion before section-level sync.")

    queue_sync = select_sync_dir(workspace, ("speckit_bundle_queue.json", "speckit_invocation_queue.json"))
    specs = _queue_specs(queue_sync)
    ledger = as_dict(load_json_dict(sync / DONE_LEDGER_JSON).get("specs"))
    new_ledger: dict[str, Any] = {}
    spec_rows: list[dict[str, Any]] = []
    for spec in specs:
        short_name = str(spec.get("short_name"))
        sections = [str(s) for s in as_list(spec.get("source_hld_sections"))]
        assessment = assess_spec(speckit_root, short_name)
        status = str(assessment.get("status"))
        row = {
            "short_name": short_name,
            "feature_id": str(spec.get("feature_id", "")),
            "source_hld_sections": sections,
            "status": status,
        }
        if status == "DONE_VERIFIED" and fingerprints:
            entry = ledger.get(short_name) if isinstance(ledger.get(short_name), dict) else None
            row["status"], new_ledger[short_name] = _ledger_status(
                entry, sections, fingerprints, _artifacts_mtime(speckit_root, short_name), hld_path.stat().st_mtime
            )
            if row["status"] == "DONE_STALE":
                row["stale_sections"] = new_ledger[short_name].get("stale_sections", [])
        elif status == "DONE_VERIFIED" and isinstance(ledger.get(short_name), dict):
            new_ledger[short_name] = ledger[short_name]
        spec_rows.append(row)

    # Tier-2 regeneration: deterministic, safe to do every sync — but only
    # when the queue actually exists where the prompt builder looks, so an
    # empty regeneration can never wipe prompts built from elsewhere.
    prompts_regenerated = False
    if (queue_sync / "speckit_bundle_queue.json").is_file():
        from hldspec.spec_bundle_prompts import write_bundle_prompts

        write_bundle_prompts(workspace)
        prompts_regenerated = True

    stale_specs = [row["short_name"] for row in spec_rows if row["status"] == "DONE_STALE"]
    pending_specs = [row["short_name"] for row in spec_rows if row["status"] not in {"DONE_VERIFIED", "DONE_STALE"}]
    if stale_specs:
        status = "STALE_SPECS"
        next_action = (
            f"Re-run the SpecKit phases for stale specs ({', '.join(stale_specs)}) against the "
            "updated HLD sections, then sync again."
        )
    elif pending_specs:
        status = "IN_SYNC_PENDING"
        next_action = "No spec is stale. Continue the build loop on the pending specs."
    else:
        status = "IN_SYNC"
        next_action = "Everything is in sync. Continue from the execution state's next action."

    report = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "working_hld": str(hld_path),
        "section_count": len(fingerprints),
        "section_diff": {k: v for k, v in section_diff.items() if k != "unchanged"},
        "specs": spec_rows,
        "stale_specs": stale_specs,
        "pending_specs": pending_specs,
        "prompts_regenerated": prompts_regenerated,
        "next_action": next_action,
        "warnings": warnings,
    }

    write_json_dict(sync / FINGERPRINTS_JSON, {"schema_version": SCHEMA_VERSION, "generated_at": utc_now(), "sections": fingerprints})
    write_json_dict(sync / DONE_LEDGER_JSON, {"schema_version": SCHEMA_VERSION, "generated_at": utc_now(), "specs": new_ledger})
    write_json_dict(sync / SYNC_REPORT_JSON, report)
    (sync / SYNC_REPORT_MD).write_text(render_sync_report_md(report), encoding="utf-8")
    return report


def render_sync_report_md(report: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Sync Report",
        "",
        f"Status: `{report.get('status', '')}`",
        f"Working HLD: `{report.get('working_hld', '')}` ({report.get('section_count', 0)} sections)",
        f"Prompts regenerated: `{report.get('prompts_regenerated', False)}`",
        "",
    ]
    diff = as_dict(report.get("section_diff"))
    if any(diff.get(k) for k in ("changed", "added", "removed")):
        lines += ["## HLD section changes since last sync", ""]
        for kind in ("changed", "added", "removed"):
            for anchor in as_list(diff.get(kind)):
                lines.append(f"- {kind}: `{anchor}`")
        lines.append("")
    specs = as_list(report.get("specs"))
    if specs:
        lines += ["## Specs", "", "| Spec | Status | HLD sections |", "|---|---|---|"]
        for row in specs:
            row = as_dict(row)
            sections = ", ".join(f"`{s}`" for s in as_list(row.get("source_hld_sections")))
            stale = as_list(row.get("stale_sections"))
            note = f" (stale: {', '.join(f'`{s}`' for s in stale)})" if stale else ""
            lines.append(f"| `{row.get('short_name', '')}` | `{row.get('status', '')}`{note} | {sections} |")
        lines.append("")
    for warning in as_list(report.get("warnings")):
        lines.append(f"- WARNING: {warning}")
    if as_list(report.get("warnings")):
        lines.append("")
    lines += ["## Next action", "", str(report.get("next_action", "")), ""]
    return "\n".join(lines)
