#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ALLOWED_PHASES = {"constitution", "specify", "clarify", "plan", "tasks", "analyze"}
FORBIDDEN_PHASES = {"implement", "implementation"}
APPROVAL_DECISION = "APPROVE_PLAN"
PHASE_ROUTING = {
    "constitution": {
        "assigned_agent_name": "HLDspec Judge Orchestrator",
        "model_tier": "MODEL_CRITICAL",
        "routing_reason": "Constitution changes govern all downstream SpecKit behavior.",
    },
    "specify": {
        "assigned_agent_name": "SpecKit Specify Proxy",
        "model_tier": "MODEL_STRONG",
        "routing_reason": "Specify translates promoted evidence into a bounded feature specification.",
    },
    "clarify": {
        "assigned_agent_name": "SpecKit Clarify Proxy",
        "model_tier": "MODEL_STRONG",
        "routing_reason": "Clarify resolves bounded questions but must escalate architecture or scope decisions.",
    },
    "plan": {
        "assigned_agent_name": "SpecKit Plan Proxy",
        "model_tier": "MODEL_CRITICAL",
        "routing_reason": "Plan sets architecture, data, dependency, and implementation boundaries.",
    },
    "tasks": {
        "assigned_agent_name": "SpecKit Tasks Proxy",
        "model_tier": "MODEL_STRONG",
        "routing_reason": "Tasks decomposes an approved plan without changing architecture.",
    },
    "analyze": {
        "assigned_agent_name": "SpecKit Analyze Reviewer",
        "model_tier": "MODEL_CRITICAL",
        "routing_reason": "Analyze judges cross-artifact consistency and readiness.",
    },
}


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


def find_sync(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    for sync in (direct, nested):
        if any((sync / name).exists() for name in ("speckit_prework_package.json", "speckit_proxy_dossier.json", "hldspec_state.json", "speckit_answer_pack.json", "hldspec_promotion_ledger.json")):
            return sync
    return direct


def promotion_status(sync: Path, artifact_id: str) -> str:
    ledger = load_json(sync / "hldspec_promotion_ledger.json")
    promotions = ledger.get("promotions", {}) if isinstance(ledger.get("promotions"), dict) else {}
    record = promotions.get(artifact_id, {}) if isinstance(promotions, dict) else {}
    if isinstance(record, dict) and record.get("promotion_status"):
        return str(record["promotion_status"])
    return "PROPOSED"


def normalize_phase(phase: str) -> tuple[bool, str, str]:
    clean = phase.strip().lower()
    if not clean:
        return False, clean, "missing phase"
    if "," in clean or "+" in clean or " " in clean:
        return False, clean, "one phase only; do not pass multiple phases"
    if clean in FORBIDDEN_PHASES:
        return False, clean, "implementation is explicitly forbidden by HLDspec proxy dry-run"
    if clean not in ALLOWED_PHASES:
        return False, clean, f"unknown phase: {phase}"
    return True, clean, ""


def phase_routing(phase: str) -> dict[str, str]:
    return PHASE_ROUTING.get(
        phase,
        {
            "assigned_agent_name": "SpecKit Phase Agent",
            "model_tier": "MODEL_CRITICAL",
            "routing_reason": "Unknown or invalid phase requires judge review before delegation.",
        },
    )


def blockers_from_quality(quality: dict[str, Any]) -> list[dict[str, Any]]:
    findings = quality.get("findings", [])
    if not isinstance(findings, list):
        return []
    return [item for item in findings if isinstance(item, dict) and str(item.get("severity", "")).upper() == "BLOCKER"]


def approval_decision(package: dict[str, Any]) -> str:
    checkpoint = package.get("human_checkpoint")
    if isinstance(checkpoint, dict):
        return str(checkpoint.get("human_decision", "TBD"))
    return "TBD"


def selected_feature(dossier: dict[str, Any], queue: dict[str, Any]) -> dict[str, Any]:
    selected = dossier.get("selected_feature")
    if isinstance(selected, dict) and selected.get("feature_id"):
        return selected
    items = queue.get("items", [])
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                return item
    return {}


def phase_prompt(phase: str, dossier: dict[str, Any]) -> str:
    selected = dossier.get("selected_feature", {}) if isinstance(dossier.get("selected_feature"), dict) else {}
    specify_input = str(dossier.get("speckit_specify_input", "")).strip()
    feature_id = selected.get("feature_id", "")
    feature_name = selected.get("feature_name", "")
    answer_path_note = "Use only judge-promoted speckit_answer_pack plus Product Manager and Architect packs."
    if phase == "constitution":
        return "Prepare/update constitution from approved HLDspec constitution answers only. Do not implement. " + answer_path_note
    if phase == "specify":
        return "\n".join([f"Run only SpecKit specify for feature {feature_id} - {feature_name}.", answer_path_note, "Use this approved HLDspec input:", "", specify_input or "TBD", "", "Stop after the specify phase and report changed files/questions. Do not plan, create tasks, or implement."])
    if phase == "clarify":
        return "Run only SpecKit clarify for the active feature. Answer only from promoted answer pack. Escalate all blocking questions. Do not implement."
    if phase == "plan":
        return "Run only SpecKit plan after specify/clarify are complete. Stop after plan outputs. Do not create tasks or implement."
    if phase == "tasks":
        return "Run only SpecKit tasks after approved plan. Stop after tasks. Do not implement."
    if phase == "analyze":
        return "Run only consistency/analyze review on existing SpecKit artifacts. Do not implement."
    return ""


def build_dry_run(workspace: Path, phase: str = "specify") -> dict[str, Any]:
    sync = find_sync(workspace)
    state = load_json(sync / "hldspec_state.json")
    orchestration = load_json(sync / "hldspec_orchestration_state.json")
    package = load_json(sync / "speckit_prework_package.json")
    quality = load_json(sync / "speckit_prework_quality_review.json")
    dossier = load_json(sync / "speckit_proxy_dossier.json")
    queue = load_json(sync / "speckit_invocation_queue.json")
    answer_pack = load_json(sync / "speckit_answer_pack.json")
    phase_ok, normalized_phase, phase_error = normalize_phase(phase)
    routing = phase_routing(normalized_phase)
    blockers = blockers_from_quality(quality)
    decision = approval_decision(package)
    state_stage = str(state.get("current_stage", ""))
    feature = selected_feature(dossier, queue)
    answer_status = str(answer_pack.get("status", "MISSING"))
    answer_promotion = promotion_status(sync, "speckit_answer_pack")
    answer_blockers = answer_pack.get("blocking_open_questions", [])
    if not isinstance(answer_blockers, list):
        answer_blockers = []
    refusal_reasons: list[str] = []
    status = "DRY_RUN_READY"
    if not phase_ok:
        refusal_reasons.append(phase_error)
        status = "REFUSED_INVALID_PHASE"
        if normalized_phase in FORBIDDEN_PHASES:
            status = "REFUSED_IMPLEMENT_FORBIDDEN"
    if not package:
        refusal_reasons.append("missing speckit_prework_package.json")
        status = "REFUSED_PREWORK_NOT_APPROVED"
    elif decision != APPROVAL_DECISION:
        refusal_reasons.append(f"prework human decision is {decision}, expected {APPROVAL_DECISION}")
        status = "REFUSED_PREWORK_NOT_APPROVED"
    if blockers:
        refusal_reasons.append("prework quality review contains BLOCKER findings")
        status = "REFUSED_PREWORK_BLOCKERS"
    if state and state_stage != "SPECKIT_PREWORK_APPROVAL_GATE":
        refusal_reasons.append(f"state is {state_stage}, expected SPECKIT_PREWORK_APPROVAL_GATE")
        status = "REFUSED_WRONG_STAGE"
    if not feature.get("feature_id"):
        refusal_reasons.append("no selected feature found in proxy dossier or invocation queue")
        status = "REFUSED_NO_FEATURE"
    if not answer_pack:
        refusal_reasons.append("missing speckit_answer_pack.json; build Product Manager and Architect packs first")
        status = "REFUSED_ANSWER_PACK_MISSING"
    elif answer_status != "READY" or answer_blockers:
        refusal_reasons.append(f"answer pack status is {answer_status} with {len(answer_blockers)} blocking open questions")
        status = "REFUSED_ANSWER_PACK_BLOCKED"
    elif answer_promotion != "ACCEPTED":
        refusal_reasons.append(f"answer pack promotion status is {answer_promotion}, expected ACCEPTED")
        status = "REFUSED_ANSWER_PACK_NOT_PROMOTED"
    return {
        "schema_version": 1,
        "status": status,
        "dry_run": True,
        "workspace": str(workspace),
        "sync_dir": str(sync),
        "phase": normalized_phase,
        "model_routing": routing,
        "one_phase_only": True,
        "implementation_allowed": False,
        "will_invoke_speckit": False,
        "will_modify_source_hld": False,
        "refusal_reasons": refusal_reasons,
        "approval": {"required_decision": APPROVAL_DECISION, "actual_decision": decision, "prework_package": str(sync / "speckit_prework_package.json")},
        "state": {"current_stage": state_stage, "state_path": str(sync / "hldspec_state.json")},
        "orchestration": {"state_path": str(sync / "hldspec_orchestration_state.json"), "current_stage": orchestration.get("current_stage", "")},
        "answer_pack": {"status": answer_status, "promotion_status": answer_promotion, "blocking_open_questions": len(answer_blockers), "path": str(sync / "speckit_answer_pack.json")},
        "selected_feature": feature,
        "would_run": [] if refusal_reasons else [{
            "phase": normalized_phase,
            "assigned_agent_name": routing["assigned_agent_name"],
            "model_tier": routing["model_tier"],
            "routing_reason": routing["routing_reason"],
            "mode": "DRY_RUN_ONLY",
            "prompt": phase_prompt(normalized_phase, dossier),
            "stop_condition": "stop after this single phase and write a phase completion report",
        }],
        "guardrails": ["Do not invoke implementation.", "Do not run more than one SpecKit phase.", "Do not modify source HLD.", "Use only judge-promoted answer pack evidence.", "Use Product Manager pack for product/user-story questions.", "Use Architect pack for API/data/dependency/constitution questions.", "Escalate unanswered blocking PMQ/ARQ questions.", "Report changed files and next readiness after the phase."],
    }


def render_md(data: dict[str, Any]) -> str:
    routing = data.get("model_routing", {}) if isinstance(data.get("model_routing"), dict) else {}
    lines = ["# SpecKit Proxy Dry Run", "", "", "", f"Status: `{data.get('status')}`", f"Phase: `{data.get('phase')}`", f"Assigned agent: `{routing.get('assigned_agent_name', '')}`", f"Model tier: `{routing.get('model_tier', '')}`", f"Routing reason: {routing.get('routing_reason', '')}", f"Dry run: `{str(data.get('dry_run')).lower()}`", f"Implementation allowed: `{str(data.get('implementation_allowed')).lower()}`", f"Will invoke SpecKit: `{str(data.get('will_invoke_speckit')).lower()}`", f"Answer pack status: `{data.get('answer_pack', {}).get('status', '')}`", f"Answer pack promotion: `{data.get('answer_pack', {}).get('promotion_status', '')}`", f"Answer pack blocking questions: `{data.get('answer_pack', {}).get('blocking_open_questions', '')}`", ""]
    reasons = data.get("refusal_reasons", [])
    if isinstance(reasons, list) and reasons:
        lines += ["## Refusal reasons", ""]
        for reason in reasons:
            lines.append(f"- {reason}")
        lines.append("")
    lines += ["## Would run", ""]
    would = data.get("would_run", [])
    if isinstance(would, list) and would:
        for item in would:
            if isinstance(item, dict):
                lines += [f"### {item.get('phase')}", "", f"- assigned agent: `{item.get('assigned_agent_name')}`", f"- model tier: `{item.get('model_tier')}`", f"- routing reason: {item.get('routing_reason')}", f"- mode: `{item.get('mode')}`", f"- stop condition: {item.get('stop_condition')}", "", "Prompt:", "", "```text", str(item.get("prompt", "")), "```", ""]
    else:
        lines.append("- none")
    lines += ["", "## Guardrails", ""]
    for guard in data.get("guardrails", []):
        lines.append(f"- {guard}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a guarded one-phase SpecKit proxy dry run.")
    parser.add_argument("workspace")
    parser.add_argument("--phase", default="specify")
    parser.add_argument("--out-dir", default="")
    args = parser.parse_args()
    workspace = Path(args.workspace).resolve()
    sync = Path(args.out_dir).resolve() if args.out_dir else find_sync(workspace)
    sync.mkdir(parents=True, exist_ok=True)
    dry_run = build_dry_run(workspace, args.phase)
    json_path = sync / "speckit_proxy_dry_run.json"
    md_path = sync / "speckit_proxy_dry_run.md"
    write_json(json_path, dry_run)
    md_path.write_text(render_md(dry_run), encoding="utf-8")
    print("SpecKit proxy dry-run generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {dry_run['status']}")
    print(f"- phase: {dry_run['phase']}")
    return 0 if dry_run["status"] == "DRY_RUN_READY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
