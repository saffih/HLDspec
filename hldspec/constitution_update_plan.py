"""Constitution update plan generator.

When an option packet with affects_constitution=True is answered, HLDspec
generates a constitution_update_plan artifact. It does NOT modify
.specify/memory/constitution.md directly — that requires human approval.

Usage:
    from hldspec.constitution_update_plan import build_update_plan, UpdatePlanEntry

    entries = build_update_plan(resolved_packets)
    # write to constitution_update_plan.json / .md and wait for approval
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from hldspec.option_packet import OptionPacket

UPDATE_PLAN_FILENAME = "constitution_update_plan.json"
SCHEMA_VERSION = 1


@dataclass
class UpdatePlanEntry:
    decision_id: str
    current_rule: str           # existing rule text, or "(none)"
    proposed_rule: str          # what the rule should say after the decision
    why: str                    # short rationale from the option packet
    artifacts_affected: list[str] = field(default_factory=list)
    human_approval_required: bool = True


def build_update_plan(
    resolved_packets: list[OptionPacket],
    *,
    existing_rules: dict[str, str] | None = None,
) -> list[UpdatePlanEntry]:
    """Build update plan entries for resolved packets that affect the constitution.

    Args:
        resolved_packets: packets that have been answered (recommended_default set)
        existing_rules: mapping of decision_id -> current rule text for lookup
    """
    rules = existing_rules or {}
    entries: list[UpdatePlanEntry] = []
    for packet in resolved_packets:
        if not packet.affects_constitution:
            continue
        if not packet.recommended_default:
            continue  # not yet answered
        entries.append(
            UpdatePlanEntry(
                decision_id=packet.decision_id,
                current_rule=rules.get(packet.decision_id, "(none)"),
                proposed_rule=(
                    f"{packet.missing_fact} — decision: {packet.recommended_default}. "
                    f"Blast radius: {packet.blast_radius or 'unknown'}."
                ),
                why=packet.tradeoffs.get(packet.recommended_default, ""),
                artifacts_affected=[],
                human_approval_required=True,
            )
        )
    return entries


def save_update_plan(entries: list[UpdatePlanEntry], path: Path) -> None:
    """Write update plan to JSON. Creates parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "human_approval_required": True,
        "note": (
            "This plan must be reviewed and approved before SpecKit applies any "
            "constitution changes. HLDspec never edits .specify/memory/constitution.md directly."
        ),
        "entries": [asdict(e) for e in entries],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def render_update_plan_md(entries: list[UpdatePlanEntry]) -> str:
    lines = [
        "# Constitution Update Plan",
        "",
        "> **Human approval required before any constitution change is applied.**",
        "> HLDspec never edits `.specify/memory/constitution.md` directly.",
        "",
    ]
    if not entries:
        lines.append("No constitution-impacting decisions pending.")
        return "\n".join(lines)

    for entry in entries:
        lines += [
            f"## {entry.decision_id}",
            "",
            f"**Current rule:** {entry.current_rule}",
            "",
            f"**Proposed rule:** {entry.proposed_rule}",
            "",
            f"**Why:** {entry.why or '(see option packet)'}",
            "",
            f"**Human approval required:** {str(entry.human_approval_required).lower()}",
            "",
        ]
    return "\n".join(lines)
