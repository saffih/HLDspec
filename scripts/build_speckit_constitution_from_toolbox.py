#!/usr/bin/env python3
"""Augment constitution_update_plan.json with Engineering Toolbox rules.

This is the missing Link-1 wire: engineering_selection flags durable cards with
``constitution_candidate: yes``, but until now those candidates only reached the
advisory ``engineering_guidelines.md`` and never the constitution update plan.

This augmenter mirrors build_speckit_constitution_from_contracts.py: it reads the
existing constitution_update_plan.json, appends one ENG-* rule per selected
constitution-candidate card (deduped by rationale marker), and writes it back.
HLDspec proposes; the human still approves the plan before it reaches
.specify/memory/constitution.md.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))
from hldspec.engineering_selection import select_p0_cards, _is_constitution_candidate  # noqa: E402

TOOLBOX_MARKER = "engineering_toolbox:"


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
    """Locate the source HLD text for card selection (best effort)."""
    candidates: list[Path] = []
    if source_hld:
        candidates.append(Path(source_hld))
    candidates += [workspace / "HLD.md", workspace / "firstrun" / "HLD.md"]
    for path in candidates:
        if path.is_file():
            return path.read_text(encoding="utf-8")
    return ""


def existing_card_ids(rules: list[dict[str, Any]]) -> set[str]:
    """Return card ids already covered by an ENG-* rule (dedup on re-run)."""
    covered: set[str] = set()
    for rule in rules:
        rationale = str(rule.get("rationale", ""))
        if TOOLBOX_MARKER in rationale:
            covered.add(rationale.split(TOOLBOX_MARKER)[-1].strip())
    return covered


def _card_name(card_id: str) -> str:
    """Readable rule name from a card id, e.g. testing.design_for_testability."""
    parts = card_id.split(".")
    return ": ".join(p.replace("_", " ").title() for p in parts)


def augment(workspace: Path, source_hld: str | None = None) -> dict[str, Any]:
    sync = find_sync(workspace)
    constitution = load_json(sync / "constitution_update_plan.json")
    hld_text = read_hld_text(workspace, source_hld)

    rules: list[dict[str, Any]] = [
        r for r in as_list(constitution.get("required_rules")) if isinstance(r, dict)
    ]
    covered = existing_card_ids(rules)
    eng_counter = sum(
        1 for r in rules if str(r.get("rule_id", "")).startswith("ENG-")
    )

    added = 0
    for card in select_p0_cards(hld_text):
        if not _is_constitution_candidate(card.get("constitution_candidate", "")):
            continue
        card_id = str(card["id"])
        if card_id in covered:
            continue

        eng_counter += 1
        added += 1
        rules.append(
            {
                "rule_id": f"ENG-{eng_counter:03d}",
                "name": _card_name(card_id),
                "rule": str(card["default_choice"]),
                "rationale": f"Derived from {TOOLBOX_MARKER}{card_id}",
                "source_hld_sections": [],
            }
        )
        covered.add(card_id)

    constitution["required_rules"] = rules
    write_json(sync / "constitution_update_plan.json", constitution)

    return {
        "workspace": str(workspace),
        "total_rules": len(rules),
        "toolbox_rules_added": added,
        "status": "AUGMENTED" if added else "NO_TOOLBOX_CANDIDATES",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Augment constitution_update_plan.json with Engineering Toolbox rules."
    )
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default=None)
    args = parser.parse_args()

    result = augment(Path(args.workspace).resolve(), source_hld=args.source_hld)
    print("Constitution augmented from engineering toolbox:")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
