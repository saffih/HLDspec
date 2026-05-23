#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REQUIRED_FOUNDATION_ARTIFACTS = [
    ".specify/sync/hld_index.md",
    ".specify/sync/hld_section_classification.json",
    ".specify/sync/hld_usecase_api_map.json",
    ".specify/sync/spec_build_plan.json",
    ".specify/sync/spec_build_plan_review.md",
    ".specify/sync/speckit_prework_quality_review.json",
    ".specify/sync/speckit_prework_package.json",
    ".specify/sync/hldspec_state.json",
    ".specify/sync/hldspec_junior_task_packets.json",
    ".specify/sync/hldspec_orchestration_state.json",
    ".specify/sync/speckit_product_manager_pack.json",
    ".specify/sync/speckit_architect_pack.json",
    ".specify/sync/speckit_answer_pack.json",
]

OPTIONAL_PROXY_ARTIFACTS = [
    ".specify/sync/speckit_prework_approval.json",
    ".specify/sync/speckit_proxy_dry_run.json",
    ".specify/sync/speckit_proxy_dry_run.md",
]


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_sync(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    if (direct / "hldspec_state.json").exists() or (direct / "spec_build_plan.json").exists():
        return direct
    if (nested / "hldspec_state.json").exists() or (nested / "spec_build_plan.json").exists():
        return nested
    return direct


def rel_exists(workspace_or_sync: Path, rel: str) -> bool:
    if rel.startswith(".specify/sync/"):
        return (workspace_or_sync / rel.removeprefix(".specify/sync/")).exists()
    return (workspace_or_sync / rel).exists()


def build_review(workspace: Path, source_hld: Path | None = None, expected_source_sha: str = "") -> dict[str, Any]:
    sync = resolve_sync(workspace)

    missing_foundation = [rel for rel in REQUIRED_FOUNDATION_ARTIFACTS if not rel_exists(sync, rel)]
    present_optional = [rel for rel in OPTIONAL_PROXY_ARTIFACTS if rel_exists(sync, rel)]
    missing_optional = [rel for rel in OPTIONAL_PROXY_ARTIFACTS if not rel_exists(sync, rel)]

    state = load_json(sync / "hldspec_state.json")
    prework_quality = load_json(sync / "speckit_prework_quality_review.json")
    prework_package = load_json(sync / "speckit_prework_package.json")
    dry_run = load_json(sync / "speckit_proxy_dry_run.json")

    blockers: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    if missing_foundation:
        blockers.append(
            {
                "id": "READY-FOUNDATION-MISSING",
                "finding": "Required foundation artifacts are missing.",
                "artifacts": missing_foundation,
                "recommendation": "Run scripts/hldspec_prework.sh on the source HLD.",
            }
        )

    quality_findings = prework_quality.get("findings", [])
    quality_blockers = [
        item for item in quality_findings
        if isinstance(item, dict) and str(item.get("severity", "")).upper() == "BLOCKER"
    ] if isinstance(quality_findings, list) else []
    if prework_quality.get("status") == "REWORK_REQUIRED" or quality_blockers:
        blockers.append(
            {
                "id": "READY-PREWORK-BLOCKERS",
                "finding": "SpecKit prework quality review still has blockers.",
                "blocker_count": len(quality_blockers),
                "recommendation": "Fix/rebuild prework before approving proxy work.",
            }
        )

    checkpoint = prework_package.get("human_checkpoint", {}) if isinstance(prework_package.get("human_checkpoint"), dict) else {}
    decision = str(checkpoint.get("human_decision", "TBD"))
    if decision != "APPROVE_PLAN":
        warnings.append(
            {
                "id": "READY-PREWORK-NOT-APPROVED",
                "finding": "SpecKit prework is not explicitly approved.",
                "decision": decision,
                "recommendation": "Review speckit_prework_package.md and run approve_hldspec_prework.py only if accepted.",
            }
        )

    dry_status = str(dry_run.get("status", "MISSING"))
    if dry_run and dry_status != "DRY_RUN_READY":
        warnings.append(
            {
                "id": "READY-DRY-RUN-NOT-READY",
                "finding": "SpecKit proxy dry-run exists but is not ready.",
                "status": dry_status,
                "refusal_reasons": dry_run.get("refusal_reasons", []),
            }
        )
    elif not dry_run:
        warnings.append(
            {
                "id": "READY-DRY-RUN-MISSING",
                "finding": "SpecKit proxy dry-run artifact is missing.",
                "recommendation": "Run scripts/hldspec_speckit_proxy.sh after approval.",
            }
        )

    source = {}
    if source_hld is not None and source_hld.exists():
        actual = sha256(source_hld)
        source = {
            "path": str(source_hld),
            "sha256": actual,
            "expected_sha256": expected_source_sha,
            "unchanged": (actual == expected_source_sha) if expected_source_sha else None,
        }
        if expected_source_sha and actual != expected_source_sha:
            blockers.append(
                {
                    "id": "READY-SOURCE-MUTATED",
                    "finding": "Source HLD hash changed during smoke/review.",
                    "recommendation": "Stop and inspect source HLD changes before continuing.",
                }
            )

    status = "REWORK_REQUIRED" if blockers else (
        "READY_FOR_DRY_RUN_REVIEW" if dry_status == "DRY_RUN_READY" else "CHECKPOINT_OR_APPROVAL_PENDING"
    )

    return {
        "schema_version": 1,
        "status": status,
        "workspace": str(workspace),
        "sync_dir": str(sync),
        "source_hld": source,
        "current_stage": state.get("current_stage", ""),
        "current_checkpoint": state.get("current_checkpoint", ""),
        "missing_foundation_artifacts": missing_foundation,
        "present_optional_proxy_artifacts": present_optional,
        "missing_optional_proxy_artifacts": missing_optional,
        "prework_quality_status": prework_quality.get("status", ""),
        "prework_approval_decision": decision,
        "proxy_dry_run_status": dry_status,
        "blockers": blockers,
        "warnings": warnings,
        "next_recommended_actions": next_actions(status, blockers, warnings),
    }


def next_actions(status: str, blockers: list[dict[str, Any]], warnings: list[dict[str, Any]]) -> list[str]:
    if status == "REWORK_REQUIRED":
        return ["Fix blockers listed in this readiness review, then rerun smoke."]
    warning_ids = {str(item.get("id")) for item in warnings}
    actions: list[str] = []
    if "READY-PREWORK-NOT-APPROVED" in warning_ids:
        actions.append("Review speckit_prework_package.md; approve only if acceptable.")
    if "READY-DRY-RUN-MISSING" in warning_ids:
        actions.append("Run scripts/hldspec_speckit_proxy.sh <workspace> --phase specify --dry-run after approval.")
    if status == "READY_FOR_DRY_RUN_REVIEW":
        actions.append("Review speckit_proxy_dry_run.md. Real SpecKit execution remains deferred.")
    if not actions:
        actions.append("No immediate action.")
    return actions


def render_md(review: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Readiness Review",
        "",
        "made by AI",
        "",
        f"Status: `{review['status']}`",
        f"Workspace: `{review['workspace']}`",
        f"Sync dir: `{review['sync_dir']}`",
        f"Current stage: `{review.get('current_stage', '')}`",
        f"Current checkpoint: `{review.get('current_checkpoint', '')}`",
        "",
        "## Source HLD",
        "",
    ]
    source = review.get("source_hld", {})
    if isinstance(source, dict) and source:
        lines += [
            f"- path: `{source.get('path', '')}`",
            f"- unchanged: `{source.get('unchanged')}`",
            f"- sha256: `{source.get('sha256', '')}`",
        ]
    else:
        lines.append("- not checked")

    for title, key in [
        ("Blockers", "blockers"),
        ("Warnings", "warnings"),
        ("Next recommended actions", "next_recommended_actions"),
    ]:
        lines += ["", f"## {title}", ""]
        items = review.get(key, [])
        if not items:
            lines.append("- none")
            continue
        for item in items:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('id', '')}` {item.get('finding', '')}")
                if item.get("recommendation"):
                    lines.append(f"  - recommendation: {item.get('recommendation')}")
                if item.get("refusal_reasons"):
                    lines.append(f"  - refusal reasons: {item.get('refusal_reasons')}")
            else:
                lines.append(f"- {item}")

    lines += ["", "## Artifact summary", ""]
    lines.append(f"- missing foundation artifacts: {len(review.get('missing_foundation_artifacts', []))}")
    lines.append(f"- present optional proxy artifacts: {len(review.get('present_optional_proxy_artifacts', []))}")
    lines.append(f"- prework quality status: `{review.get('prework_quality_status', '')}`")
    lines.append(f"- prework approval decision: `{review.get('prework_approval_decision', '')}`")
    lines.append(f"- proxy dry-run status: `{review.get('proxy_dry_run_status', '')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review HLDspec product readiness after smoke/prework/proxy dry-run.")
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default="")
    parser.add_argument("--expected-source-sha256", default="")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    source = Path(args.source_hld).resolve() if args.source_hld else None
    sync = resolve_sync(workspace)
    sync.mkdir(parents=True, exist_ok=True)

    review = build_review(workspace, source, args.expected_source_sha256)
    json_path = sync / "hldspec_readiness_review.json"
    md_path = sync / "hldspec_readiness_review.md"
    json_path.write_text(json.dumps(review, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(review), encoding="utf-8")

    print("HLDspec readiness review generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {review['status']}")
    return 1 if review["status"] == "REWORK_REQUIRED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
