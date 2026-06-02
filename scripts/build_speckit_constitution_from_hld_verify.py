#!/usr/bin/env python3
"""Augment constitution_update_plan.json with rules derived from HLD-VERIFY invariants.

Gate: HLD-SPECS contains "constitution" AND HLD-VERIFY is non-empty.
Rule fields:
  rule_id   : HLD section ID (e.g. HLD-003)
  name      : section title
  rule      : HLD-VERIFY text verbatim
  rationale : evidence clause from HLD-DESC canonical line; falls back to section title.

Sections flagged HLD-SPECS: constitution but missing HLD-VERIFY are recorded in the
result (skipped_no_verify) so downstream can surface them as a quality-gate finding.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
import hld_map  # noqa: E402
from hldspec.hld_canonical_line import parse_canonical_line  # noqa: E402


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


def read_hld_text(workspace: Path, source_hld: str | None) -> str:
    candidates: list[Path] = []
    if source_hld:
        candidates.append(Path(source_hld))
    candidates += [workspace / "HLD.md", workspace / "firstrun" / "HLD.md"]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def _is_constitution_section(section: Any) -> bool:
    specs = hld_map.split_metadata_list(section.metadata_value("HLD-SPECS"))
    return "constitution" in specs


def _rationale(section: Any) -> str:
    desc = section.metadata_value("HLD-DESC")
    if desc:
        rec = parse_canonical_line(desc)
        if rec and rec.get("evidence"):
            return rec["evidence"]
    return section.title


def _existing_rule_ids(rules: list[dict[str, Any]]) -> set[str]:
    return {str(r.get("rule_id", "")) for r in rules}


def augment(workspace: Path, source_hld: str | None = None) -> dict[str, Any]:
    sync = find_sync(workspace)
    constitution = load_json(sync / "constitution_update_plan.json")
    hld_text = read_hld_text(workspace, source_hld)

    if not hld_text:
        return {
            "workspace": str(workspace),
            "status": "NO_HLD",
            "rules_added": 0,
            "skipped_no_verify": [],
            "total_rules": 0,
        }

    rules: list[dict[str, Any]] = [
        r for r in as_list(constitution.get("required_rules")) if isinstance(r, dict)
    ]
    existing_ids = _existing_rule_ids(rules)
    hld = hld_map.parse_hld_text(hld_text)

    added = 0
    skipped: list[str] = []

    for section in hld.sections:
        if not _is_constitution_section(section):
            continue
        verify = section.metadata_value("HLD-VERIFY")
        if not verify:
            skipped.append(section.id)
            continue
        if section.id in existing_ids:
            continue
        rules.append(
            {
                "name": section.title,
                "rationale": _rationale(section),
                "rule": verify,
                "rule_id": section.id,
            }
        )
        existing_ids.add(section.id)
        added += 1

    constitution["required_rules"] = rules
    write_json(sync / "constitution_update_plan.json", constitution)

    return {
        "workspace": str(workspace),
        "rules_added": added,
        "skipped_no_verify": skipped,
        "status": "AUGMENTED" if added else "NO_NEW_RULES",
        "total_rules": len(rules),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Augment constitution_update_plan.json with HLD-VERIFY invariant rules."
    )
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default=None)
    args = parser.parse_args()

    result = augment(Path(args.workspace).resolve(), source_hld=args.source_hld)
    print("Constitution augmented from HLD-VERIFY invariants:")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
