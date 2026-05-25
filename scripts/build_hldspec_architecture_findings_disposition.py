#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict


DISPOSITION_BY_DECISION = {
    "SPLIT": "HANDLED_BY_SPLIT",
    "KEEP_AS_ONE": "HANDLED_BY_KEEP_AS_ONE",
    "MERGE_WITH_ACTIVE_SPEC": "HANDLED_BY_ACTIVE_SPEC_MERGE",
    "DEMOTE_TO_CONTEXT": "HANDLED_BY_DEMOTE_TO_CONTEXT",
    "CONSTITUTION_ONLY": "HANDLED_BY_CONSTITUTION_ONLY",
    "REFERENCE_ONLY": "HANDLED_BY_REFERENCE_ONLY",
}


def sync_dir(workspace: Path) -> Path:
    return select_sync_dir(workspace, ("hldspec_architecture_analysis.json", "hldspec_speckit_spec_list.json"))


def build_disposition(workspace: Path, approved: bool = False) -> dict[str, Any]:
    sync = sync_dir(workspace)
    arch = load_json_dict(sync / "hldspec_architecture_analysis.json")
    spec_list = load_json_dict(sync / "hldspec_speckit_spec_list.json")
    decisions = {
        str(item.get("hld_id")): item
        for item in spec_list.get("boundary_decisions", [])
        if isinstance(item, dict) and item.get("hld_id")
    }

    dispositions: list[dict[str, Any]] = []
    unresolved: list[str] = []
    counts: dict[str, int] = {}

    for finding in arch.get("findings", []):
        if not isinstance(finding, dict):
            continue
        hld_id = str(finding.get("hld_id", ""))
        decision = decisions.get(hld_id, {})
        boundary_decision = str(decision.get("decision", "TBD"))
        disposition = DISPOSITION_BY_DECISION.get(boundary_decision, "TBD")
        finding_id = str(finding.get("finding_id", ""))
        if disposition == "TBD":
            unresolved.append(finding_id or hld_id or "UNKNOWN")
        counts[disposition] = counts.get(disposition, 0) + 1
        dispositions.append(
            {
                "finding_id": finding_id,
                "hld_id": hld_id,
                "title": finding.get("title", ""),
                "severity": finding.get("severity", ""),
                "issue": finding.get("issue", ""),
                "boundary_decision": boundary_decision,
                "boundary_reason": decision.get("reason", ""),
                "active_spec_id": decision.get("active_spec_id", ""),
                "disposition": disposition,
            }
        )

    if not dispositions:
        status = "NO_FINDINGS"
    elif unresolved:
        status = "NEEDS_REVIEW"
    elif not approved:
        status = "PROPOSED_REQUIRES_HUMAN_APPROVAL"
    else:
        status = "DISPOSITIONED"

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "status": status,
        "finding_count": len(dispositions),
        "unresolved": unresolved,
        "approval_required": bool(dispositions) and not approved,
        "approved_by_human": approved,
        "disposition_counts": counts,
        "decision_source": str(sync / "hldspec_speckit_spec_list.json"),
        "human_decision_context": (
            "Boundary dispositions are proposed from HLDspec boundary decisions. "
            "Use --approve-human-reviewed-decisions only after a real human checkpoint approves them."
        ),
        "dispositions": dispositions,
    }


def render_md(data: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Architecture Findings Disposition",
        "",
        f"Status: `{data.get('status')}`",
        f"Workspace: `{data.get('workspace')}`",
        f"Findings: {data.get('finding_count', 0)}",
        f"Approved by human: `{str(data.get('approved_by_human', False)).lower()}`",
        "",
        "## Disposition Counts",
        "",
    ]
    counts = data.get("disposition_counts") or {}
    if counts:
        for key in sorted(counts):
            lines.append(f"- {key}: {counts[key]}")
    else:
        lines.append("- none")

    lines += ["", "## Unresolved", ""]
    if data.get("unresolved"):
        for item in data["unresolved"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines += ["", "## Findings", ""]
    records = [item for item in data.get("dispositions", []) if isinstance(item, dict)]
    if not records:
        lines.append("- none")
    else:
        for item in records:
            active = f"; active spec `{item.get('active_spec_id')}`" if item.get("active_spec_id") else ""
            lines.append(
                f"- `{item.get('finding_id')}` / `{item.get('hld_id')}`: "
                f"`{item.get('disposition')}` via `{item.get('boundary_decision')}`{active}"
            )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Disposition architecture findings against reviewed HLDspec boundary decisions.")
    parser.add_argument("workspace")
    parser.add_argument(
        "--approve-human-reviewed-decisions",
        action="store_true",
        help="Promote proposed dispositions only after a human checkpoint has approved the boundary decisions.",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sync = sync_dir(workspace)
    data = build_disposition(workspace, approved=args.approve_human_reviewed_decisions)
    json_path = sync / "hldspec_architecture_findings_disposition.json"
    md_path = sync / "hldspec_architecture_findings_disposition.md"
    write_json_dict(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLDspec architecture findings disposition generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
