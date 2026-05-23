#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ARTIFACTS: dict[str, dict[str, str]] = {
    "hldspec_junior_task_packets": {"role": "Judge", "path": "hldspec_junior_task_packets.json", "kind": "junior_task_packets"},
    "speckit_product_manager_pack": {"role": "Product Lead", "path": "speckit_product_manager_pack.json", "kind": "domain_pack"},
    "speckit_architect_pack": {"role": "Architect Lead", "path": "speckit_architect_pack.json", "kind": "domain_pack"},
    "speckit_answer_pack": {"role": "Judge", "path": "speckit_answer_pack.json", "kind": "answer_pack"},
    "speckit_prework_package": {"role": "Judge", "path": "speckit_prework_package.json", "kind": "approval_package"},
    "speckit_proxy_dry_run": {"role": "SpecKit Proxy", "path": "speckit_proxy_dry_run.json", "kind": "proxy_plan"},
}
DEPENDENCIES = {"speckit_answer_pack": ["speckit_product_manager_pack", "speckit_architect_pack"], "speckit_proxy_dry_run": ["speckit_answer_pack"]}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_dir(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    for sync in (direct, nested):
        if any((sync / meta["path"]).exists() for meta in ARTIFACTS.values()):
            return sync
    return direct


def load_ledger(sync: Path) -> dict[str, Any]:
    data = load_json(sync / "hldspec_promotion_ledger.json")
    if not data:
        return {"schema_version": 1, "promotions": {}}
    data.setdefault("schema_version", 1)
    data.setdefault("promotions", {})
    if not isinstance(data["promotions"], dict):
        data["promotions"] = {}
    return data


def artifact_questions(data: dict[str, Any], artifact_id: str) -> list[dict[str, Any]]:
    if artifact_id == "speckit_product_manager_pack":
        return [q for q in data.get("product_open_questions", []) if isinstance(q, dict) and str(q.get("human_decision", "TBD")) == "TBD"]
    if artifact_id == "speckit_architect_pack":
        return [q for q in data.get("architecture_open_questions", []) if isinstance(q, dict) and str(q.get("human_decision", "TBD")) == "TBD"]
    if artifact_id == "speckit_answer_pack":
        return [q for q in data.get("blocking_open_questions", []) if isinstance(q, dict) and str(q.get("human_decision", "TBD")) == "TBD"]
    return []


def artifact_status(data: dict[str, Any]) -> str:
    return str(data.get("status", "PROPOSED")) if data else "MISSING"


def promotion_status(ledger: dict[str, Any], artifact_id: str, exists: bool) -> str:
    promotion = ledger.get("promotions", {}).get(artifact_id, {})
    if isinstance(promotion, dict) and promotion.get("promotion_status"):
        return str(promotion["promotion_status"])
    return "PROPOSED" if exists else "MISSING"


def accepted(ledger: dict[str, Any], artifact_id: str) -> bool:
    promotion = ledger.get("promotions", {}).get(artifact_id, {})
    return isinstance(promotion, dict) and promotion.get("promotion_status") == "ACCEPTED"


def consumers_for(artifact_id: str) -> list[str]:
    if artifact_id in {"speckit_product_manager_pack", "speckit_architect_pack"}:
        return ["speckit_answer_pack"]
    if artifact_id == "speckit_answer_pack":
        return ["speckit_proxy_dry_run"]
    if artifact_id == "speckit_proxy_dry_run":
        return ["judge_review_only"]
    return []


def build_state(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    ledger = load_ledger(sync)
    outputs: list[dict[str, Any]] = []
    blockers: list[str] = []
    promoted: list[str] = []
    for artifact_id, meta in ARTIFACTS.items():
        path = sync / meta["path"]
        data = load_json(path)
        exists = path.exists()
        questions = artifact_questions(data, artifact_id)
        promo = promotion_status(ledger, artifact_id, exists)
        deps = DEPENDENCIES.get(artifact_id, [])
        missing_deps = [dep for dep in deps if not accepted(ledger, dep)]
        if promo == "ACCEPTED":
            promoted.append(artifact_id)
        if exists and questions:
            blockers.append(f"{artifact_id} has {len(questions)} blocking open question(s)")
        if exists and missing_deps and artifact_id in {"speckit_answer_pack", "speckit_proxy_dry_run"}:
            blockers.append(f"{artifact_id} depends on unaccepted artifact(s): {', '.join(missing_deps)}")
        outputs.append({"artifact_id": artifact_id, "producer_role": meta["role"], "artifact_kind": meta["kind"], "path": str(path), "exists": exists, "artifact_status": artifact_status(data), "promotion_status": promo, "requires_judge_review": artifact_id != "hldspec_junior_task_packets", "blocking_question_count": len(questions), "dependencies": deps, "unaccepted_dependencies": missing_deps, "allowed_consumers": [] if promo != "ACCEPTED" else consumers_for(artifact_id)})
    answer_pack_accepted = accepted(ledger, "speckit_answer_pack")
    prework = load_json(sync / "speckit_prework_package.json")
    checkpoint = prework.get("human_checkpoint", {}) if isinstance(prework.get("human_checkpoint"), dict) else {}
    prework_approved = checkpoint.get("human_decision") == "APPROVE_PLAN"
    allowed: list[str] = []
    blocked: list[str] = []
    if not accepted(ledger, "speckit_product_manager_pack"):
        allowed.append("review/promote speckit_product_manager_pack after PMQ questions are resolved")
    if not accepted(ledger, "speckit_architect_pack"):
        allowed.append("review/promote speckit_architect_pack after ARQ questions are resolved")
    if accepted(ledger, "speckit_product_manager_pack") and accepted(ledger, "speckit_architect_pack") and not answer_pack_accepted:
        allowed.append("build/review/promote speckit_answer_pack")
    if answer_pack_accepted and prework_approved:
        allowed.append("run guarded SpecKit proxy dry-run")
    else:
        blocked.append("SpecKit proxy dry-run requires accepted answer pack and approved prework")
    if blockers:
        stage = "ORCHESTRATION_BLOCKED"
        checkpoint_id = "resolve_or_promote_required_artifacts"
    elif not answer_pack_accepted:
        stage = "ANSWER_PACK_PROMOTION_GATE"
        checkpoint_id = "judge_promotes_answer_pack"
    elif answer_pack_accepted and prework_approved:
        stage = "SPECKIT_PROXY_DRY_RUN_READY"
        checkpoint_id = "judge_may_run_proxy_dry_run"
    else:
        stage = "PREWORK_APPROVAL_GATE"
        checkpoint_id = "human_approves_prework"
    return {"schema_version": 1, "judge_controls": True, "workspace": str(workspace), "sync_dir": str(sync), "current_stage": stage, "current_checkpoint": checkpoint_id, "controlling_artifact": str(sync / "hldspec_orchestration_state.json"), "specialist_outputs": outputs, "promoted_artifacts": promoted, "blocking_reasons": blockers, "allowed_next_actions": allowed, "blocked_actions": blocked, "promotion_ledger": str(sync / "hldspec_promotion_ledger.json"), "source_hld_modified": False}


def render_md(state: dict[str, Any]) -> str:
    lines = ["# HLDspec Orchestration State", "", "made by AI", "", f"Current stage: `{state['current_stage']}`", f"Current checkpoint: `{state['current_checkpoint']}`", f"Judge controls: `{str(state['judge_controls']).lower()}`", "", "## Specialist outputs", ""]
    for item in state.get("specialist_outputs", []):
        lines += [f"### {item.get('artifact_id')}", "", f"- producer role: `{item.get('producer_role')}`", f"- exists: `{str(item.get('exists')).lower()}`", f"- artifact status: `{item.get('artifact_status')}`", f"- promotion status: `{item.get('promotion_status')}`", f"- blocking questions: {item.get('blocking_question_count')}", f"- unaccepted dependencies: {', '.join(item.get('unaccepted_dependencies') or []) or 'none'}", ""]
    for title, key in [("Blocking reasons", "blocking_reasons"), ("Allowed next actions", "allowed_next_actions"), ("Blocked actions", "blocked_actions")]:
        lines += ["", f"## {title}", ""]
        values = state.get(key, [])
        if not values:
            lines.append("- none")
        for value in values:
            lines.append(f"- {value}")
    lines.append("")
    return "\n".join(lines)


def write_state(workspace: Path) -> dict[str, Any]:
    sync = sync_dir(workspace)
    sync.mkdir(parents=True, exist_ok=True)
    state = build_state(workspace)
    write_json(sync / "hldspec_orchestration_state.json", state)
    (sync / "hldspec_orchestration_state.md").write_text(render_md(state), encoding="utf-8")
    return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Build judge-owned HLDspec orchestration state.")
    parser.add_argument("workspace")
    args = parser.parse_args()
    state = write_state(Path(args.workspace).resolve())
    print("HLDspec orchestration state generated:")
    print(f"- state: {state['controlling_artifact']}")
    print(f"- stage: {state['current_stage']}")
    print(f"- promoted artifacts: {len(state['promoted_artifacts'])}")
    print(f"- blockers: {len(state['blocking_reasons'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
