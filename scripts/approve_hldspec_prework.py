#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"Failed to read JSON {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"Expected object JSON in {path}")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def find_sync(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    for sync in (direct, nested):
        if (sync / "speckit_prework_package.json").exists():
            return sync
    return direct


def approve_prework(workspace: Path, decision: str, notes: str = "") -> dict[str, Any]:
    sync = find_sync(workspace)
    package_path = sync / "speckit_prework_package.json"
    if not package_path.exists():
        raise FileNotFoundError(f"Missing SpecKit prework package: {package_path}")

    package = load_json(package_path)
    checkpoint = package.get("human_checkpoint")
    if not isinstance(checkpoint, dict):
        raise ValueError("speckit_prework_package.json has no human_checkpoint object")

    options = [str(item) for item in checkpoint.get("options", [])]
    if options and decision not in options:
        raise ValueError(f"Invalid prework decision: {decision}. Allowed: {', '.join(options)}")

    checkpoint["human_decision"] = decision
    if notes:
        checkpoint["human_notes"] = notes
    package["human_checkpoint"] = checkpoint
    package["approval_record"] = {
        "decision": decision,
        "notes": notes,
        "source": "approve_hldspec_prework.py",
    }
    write_json(package_path, package)

    record = {
        "schema_version": 1,
        "status": "APPROVED" if decision == "APPROVE_PLAN" else "NOT_APPROVED",
        "decision": decision,
        "notes": notes,
        "prework_package": str(package_path),
    }
    write_json(sync / "speckit_prework_approval.json", record)
    (sync / "speckit_prework_approval.md").write_text(render_md(record), encoding="utf-8")
    return record


def render_md(record: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# SpecKit Prework Approval",
            "",
            "made by AI",
            "",
            f"Status: `{record.get('status', '')}`",
            f"Decision: `{record.get('decision', '')}`",
            f"Prework package: `{record.get('prework_package', '')}`",
            "",
            "Notes:",
            "",
            str(record.get("notes", "") or "none"),
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Record explicit human approval for SpecKit prework.")
    parser.add_argument("workspace")
    parser.add_argument("--decision", default="APPROVE_PLAN")
    parser.add_argument("--notes", default="")
    args = parser.parse_args()

    try:
        record = approve_prework(Path(args.workspace), args.decision, args.notes)
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record["status"] == "APPROVED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
