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

from hldspec.prework_contracts import architecture_disposition_blockers, missing_constitution_keys
from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict


def sync_dir(workspace: Path) -> Path:
    return select_sync_dir(workspace, ("speckit_constitution_context.json", "hldspec_speckit_spec_list.json"))


def build_review(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    arch = load_json_dict(sync / "hldspec_architecture_analysis.json")
    arch_disposition = load_json_dict(sync / "hldspec_architecture_findings_disposition.json")
    constitution = load_json_dict(sync / "speckit_constitution_context.json")
    spec_list = load_json_dict(sync / "hldspec_speckit_spec_list.json")

    missing: list[str] = []
    if not arch:
        missing.append("hldspec_architecture_analysis")
    if not constitution:
        missing.append("speckit_constitution_context")
    if not spec_list:
        missing.append("hldspec_speckit_spec_list")
    missing.extend([f"constitution.{x}" for x in missing_constitution_keys(constitution)])

    blocking: list[str] = []
    if missing:
        blocking.append("missing readiness artifacts or required constitution sections")
    if spec_list.get("spec_count", 0) == 0:
        blocking.append("no planned specs generated")
    if spec_list.get("status") != "SPEC_LIST_READY_FOR_REVIEW":
        blocking.append(f"spec list is {spec_list.get('status', 'MISSING')}")
    for item in spec_list.get("blocking", []) if isinstance(spec_list.get("blocking"), list) else []:
        blocking.append(f"spec list: {item}")
    blocking.extend(architecture_disposition_blockers(arch, arch_disposition))

    status = "SPECKIT_PREWORK_READY_FOR_HUMAN_REVIEW" if not blocking else "SPECKIT_PREWORK_NOT_READY"

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "status": status,
        "not_real_speckit_execution": True,
        "implementation_allowed": False,
        "missing": missing,
        "blocking": blocking,
        "architecture_status": arch.get("status", "MISSING"),
        "architecture_disposition_status": arch_disposition.get("status", "MISSING"),
        "constitution_status": constitution.get("status", "MISSING"),
        "spec_list_status": spec_list.get("status", "MISSING"),
        "spec_count": spec_list.get("spec_count", 0),
        "next_safe_action": (
            "Human review of constitution context and spec list; do not invoke SpecKit yet."
            if status == "SPECKIT_PREWORK_READY_FOR_HUMAN_REVIEW"
            else "Resolve architecture/spec-list blockers before SpecKit prework approval."
        ),
    }


def render_md(data: dict[str, Any]) -> str:
    lines = [
        "# HLDspec SpecKit Readiness Review",
        "",
        "",
        "",
        f"Status: `{data.get('status')}`",
        f"Workspace: `{data.get('workspace')}`",
        f"Spec count: {data.get('spec_count')}",
        f"Implementation allowed: `{str(data.get('implementation_allowed')).lower()}`",
        f"Real SpecKit execution: `false`",
        "",
        "## Component statuses",
        "",
        f"- architecture analysis: `{data.get('architecture_status')}`",
        f"- architecture disposition: `{data.get('architecture_disposition_status')}`",
        f"- constitution context: `{data.get('constitution_status')}`",
        f"- spec list: `{data.get('spec_list_status')}`",
        "",
        "## Blocking",
        "",
    ]
    if data.get("blocking"):
        for item in data["blocking"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines += ["", "## Missing", ""]
    if data.get("missing"):
        for item in data["missing"]:
            lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines += ["", "## Next safe action", "", data.get("next_safe_action", ""), ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review whether HLDspec outputs are ready for human SpecKit prework review.")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    sync = sync_dir(workspace)
    data = build_review(workspace)
    json_path = sync / "hldspec_speckit_readiness.json"
    md_path = sync / "hldspec_speckit_readiness.md"
    write_json_dict(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLDspec SpecKit readiness review generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
