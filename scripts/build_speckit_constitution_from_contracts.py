#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


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


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def find_sync(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    for candidate in (direct, nested):
        if (candidate / "constitution_update_plan.json").exists():
            return candidate
    return direct


def existing_contract_ids(rules: list[dict[str, Any]]) -> set[str]:
    """Return contract_ids already covered in existing CONTRACT-* or DATA-* rules."""
    covered: set[str] = set()
    for rule in rules:
        rationale = str(rule.get("rationale", ""))
        if "interface_contract_map.json:" in rationale:
            cid = rationale.split("interface_contract_map.json:")[-1].strip()
            covered.add(cid)
        if "data_ownership_map.json:" in rationale:
            cid = rationale.split("data_ownership_map.json:")[-1].strip()
            covered.add(cid)
    return covered


def augment(workspace: Path) -> dict[str, Any]:
    sync = find_sync(workspace)
    constitution = load_json(sync / "constitution_update_plan.json")
    interface_map = load_json(sync / "interface_contract_map.json")
    data_map = load_json(sync / "data_ownership_map.json")

    rules: list[dict[str, Any]] = [
        r for r in as_list(constitution.get("required_rules")) if isinstance(r, dict)
    ]
    covered = existing_contract_ids(rules)

    # --- CONTRACT-* rules from interface_contract_map ---
    contract_counter = sum(
        1 for r in rules if str(r.get("rule_id", "")).startswith("CONTRACT-")
    )
    for contract in as_list(interface_map.get("contracts")):
        if not isinstance(contract, dict):
            continue
        cid = str(contract.get("contract_id", ""))
        if not cid or cid in covered:
            continue

        contract_counter += 1
        provider = str(contract.get("provider") or "TBD")
        consumer = str(contract.get("consumer") or "TBD")
        name = str(contract.get("contract_name") or cid)
        evidence = as_list(contract.get("evidence"))
        evidence_note = f" {evidence[0]}" if evidence else ""
        source_sections = as_list(contract.get("source_hld_sections"))

        rule_text = (
            f"{provider} provides the {name}; {consumer} consumes it."
            f"{evidence_note}"
        ).strip()

        rules.append(
            {
                "rule_id": f"CONTRACT-{contract_counter:03d}",
                "name": name,
                "rule": rule_text,
                "rationale": f"Derived from interface_contract_map.json:{cid}",
                "source_hld_sections": source_sections,
            }
        )
        covered.add(cid)

    # --- DATA-* rules from data_ownership_map (only where source_of_truth is known) ---
    data_counter = sum(
        1 for r in rules if str(r.get("rule_id", "")).startswith("DATA-")
    )
    for obj in as_list(data_map.get("data_objects")):
        if not isinstance(obj, dict):
            continue
        sot = str(obj.get("source_of_truth", "TBD"))
        if sot == "TBD":
            continue
        obj_name = str(obj.get("data_object", ""))
        if not obj_name:
            continue
        obj_key = f"data_ownership:{obj_name}"
        if obj_key in covered:
            continue

        data_counter += 1
        owner = str(obj.get("owner") or "TBD")
        update_timing = str(obj.get("update_timing") or "TBD")
        source_sections = as_list(obj.get("source_hld_sections"))

        rule_text = (
            f"{obj_name} source of truth: {sot}."
            f" Owner: {owner}."
            + (f" Update timing: {update_timing}." if update_timing != "TBD" else "")
        ).strip()

        rules.append(
            {
                "rule_id": f"DATA-{data_counter:03d}",
                "name": f"{obj_name} Data Ownership",
                "rule": rule_text,
                "rationale": f"Derived from data_ownership_map.json:{obj_name}",
                "source_hld_sections": source_sections,
            }
        )
        covered.add(obj_key)

    constitution["required_rules"] = rules
    write_json(sync / "constitution_update_plan.json", constitution)

    contract_rules = [r for r in rules if str(r.get("rule_id", "")).startswith("CONTRACT-")]
    data_rules = [r for r in rules if str(r.get("rule_id", "")).startswith("DATA-")]
    return {
        "workspace": str(workspace),
        "total_rules": len(rules),
        "contract_rules_added": len(contract_rules),
        "data_rules_added": len(data_rules),
        "status": "AUGMENTED" if (contract_rules or data_rules) else "NO_CONTRACTS_FOUND",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Augment constitution_update_plan.json with contract-derived rules."
    )
    parser.add_argument("workspace")
    args = parser.parse_args()

    result = augment(Path(args.workspace).resolve())
    print("Constitution augmented from contracts:")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
