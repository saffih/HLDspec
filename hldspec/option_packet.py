"""Option packets for human-owned decisions.

When the HLD leaves a design decision unspecified, HLDspec generates an
option packet instead of filling the gap silently.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any


@dataclass
class OptionPacket:
    decision_id: str
    source_hld_sections: list[str]    # HLD section IDs where the gap was found
    missing_fact: str                  # What is unknown
    options: list[str]                 # Available choices
    tradeoffs: dict[str, str]          # option -> tradeoff description
    recommended_default: str           # "" if no safe default
    blast_radius: str                  # What breaks if wrong
    validation_expectations: str       # How to verify the decision
    affects_constitution: bool         # Whether this changes the constitution
    decision_type: str                 # "source_of_truth" | "api_boundary" | "data_ownership" | "dependency" | "rollout" | "security"


def make_option_packet(
    decision_id: str,
    *,
    missing_fact: str,
    options: list[str],
    decision_type: str,
    source_hld_sections: list[str] | None = None,
    tradeoffs: dict[str, str] | None = None,
    recommended_default: str = "",
    blast_radius: str = "",
    validation_expectations: str = "",
    affects_constitution: bool = False,
) -> OptionPacket:
    """Convenience constructor with sensible defaults."""
    return OptionPacket(
        decision_id=decision_id,
        source_hld_sections=source_hld_sections or [],
        missing_fact=missing_fact,
        options=options,
        tradeoffs=tradeoffs or {},
        recommended_default=recommended_default,
        blast_radius=blast_radius,
        validation_expectations=validation_expectations,
        affects_constitution=affects_constitution,
        decision_type=decision_type,
    )


HUMAN_OWNED_DECISION_TYPES = {
    "source_of_truth",
    "api_boundary",
    "data_ownership",
    "dependency_order",
    "rollout_strategy",
    "security_boundary",
}
