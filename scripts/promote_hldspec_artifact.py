#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ALLOWED_DECISIONS = {"ACCEPTED", "REJECTED", "NEEDS_REWORK", "NEEDS_HUMAN_ANSWERS", "SUPERSEDED"}
ARTIFACT_PATHS = {"speckit_product_manager_pack": "speckit_product_manager_pack.json", "speckit_architect_pack": "speckit_architect_pack.json", "speckit_answer_pack": "speckit_answer_pack.json", "speckit_proxy_dry_run": "speckit_proxy_dry_run.json"}


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
        if any((sync / rel).exists() for rel in ARTIFACT_PATHS.values()):
            return sync
    return direct


def ledger(sync: Path) -> dict[str, Any]:
    data = load_json(sync / "hldspec_promotion_ledger.json")
    if not data:
        data = {"schema_version": 1, "promotions": {}}
    data.setdefault("promotions", {})
    if not isinstance(data["promotions"], dict):
        data["promotions"] = {}
    return data


def existing_promotion(sync: Path, artifact_id: str) -> str:
    data = ledger(sync).get("promotions", {}).get(artifact_id, {})
    if isinstance(data, dict):
        return str(data.get("promotion_status", "PROPOSED"))
    return "PROPOSED"


def blocking_questions(data: dict[str, Any], artifact_id: str) -> list[Any]:
    if artifact_id == "speckit_product_manager_pack":
        return [q for q in data.get("product_open_questions", []) if isinstance(q, dict) and str(q.get("human_decision", "TBD")) == "TBD"]
    if artifact_id == "speckit_architect_pack":
        return [q for q in data.get("architecture_open_questions", []) if isinstance(q, dict) and str(q.get("human_decision", "TBD")) == "TBD"]
    if artifact_id == "speckit_answer_pack":
        return [q for q in data.get("blocking_open_questions", []) if isinstance(q, dict) and str(q.get("human_decision", "TBD")) == "TBD"]
    return []


def validate_acceptance(sync: Path, artifact_id: str, data: dict[str, Any]) -> None:
    questions = blocking_questions(data, artifact_id)
    if questions:
        raise ValueError(f"Cannot ACCEPT {artifact_id}: {len(questions)} blocking open question(s) remain")
    if artifact_id == "speckit_answer_pack":
        for dep in ("speckit_product_manager_pack", "speckit_architect_pack"):
            if existing_promotion(sync, dep) != "ACCEPTED":
                raise ValueError(f"Cannot ACCEPT speckit_answer_pack before {dep} is ACCEPTED")
    if artifact_id == "speckit_proxy_dry_run":
        if existing_promotion(sync, "speckit_answer_pack") != "ACCEPTED":
            raise ValueError("Cannot ACCEPT speckit_proxy_dry_run before speckit_answer_pack is ACCEPTED")
        if data.get("status") != "DRY_RUN_READY":
            raise ValueError(f"Cannot ACCEPT speckit_proxy_dry_run with status {data.get('status')}")


def promote(workspace: Path, artifact_id: str, decision: str, notes: str = "", promoted_by: str = "judge") -> dict[str, Any]:
    decision = decision.upper()
    if decision not in ALLOWED_DECISIONS:
        raise ValueError(f"Invalid decision: {decision}. Allowed: {', '.join(sorted(ALLOWED_DECISIONS))}")
    if artifact_id not in ARTIFACT_PATHS:
        raise ValueError(f"Unknown artifact id: {artifact_id}")
    sync = sync_dir(workspace)
    path = sync / ARTIFACT_PATHS[artifact_id]
    if not path.exists():
        raise FileNotFoundError(f"Missing artifact: {path}")
    data = load_json(path)
    if decision == "ACCEPTED":
        validate_acceptance(sync, artifact_id, data)
    led = ledger(sync)
    led["promotions"][artifact_id] = {"artifact_id": artifact_id, "artifact_path": str(path), "promotion_status": decision, "promoted_by": promoted_by, "notes": notes, "artifact_status_at_promotion": data.get("status", ""), "requires_judge_review": False if decision == "ACCEPTED" else True}
    write_json(sync / "hldspec_promotion_ledger.json", led)
    # Refresh orchestration state in-process when available. Avoid subprocesses here so unit tests cannot hang on nested process output.
    try:
        script_dir = Path(__file__).resolve().parent
        if str(script_dir) not in sys.path:
            sys.path.insert(0, str(script_dir))
        import build_hldspec_orchestration_state as state_builder  # type: ignore
        state_builder.write_state(workspace)
    except Exception:
        pass
    return led["promotions"][artifact_id]


def main() -> int:
    parser = argparse.ArgumentParser(description="Record judge promotion decision for an HLDspec artifact.")
    parser.add_argument("workspace")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--decision", required=True, choices=sorted(ALLOWED_DECISIONS))
    parser.add_argument("--notes", default="")
    parser.add_argument("--promoted-by", default="judge")
    args = parser.parse_args()
    try:
        record = promote(Path(args.workspace).resolve(), args.artifact, args.decision, args.notes, args.promoted_by)
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
