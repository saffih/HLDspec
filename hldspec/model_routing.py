"""Model routing — KISS two-tier operational model with a lossless mapping to
the four canonical tiers.

Resolved 2026-05-27 (see docs/archive/REWRITE_PROMPT_RUNSKEPTIC_REVIEW_2026-05-27.md):
operate on two tiers, but keep the four-tier taxonomy as a documented projection
so the set can expand when a concrete need appears.

- MODEL_SIMPLE: mechanical work that cannot change meaning (copy, hash, validate
  paths, generate manifests, mechanical diff, stale-by-hash, formatting, run
  commands/tests, anchor generation when structure is unambiguous).
- MODEL_SMART: anything where meaning can change (product/architecture meaning,
  HLD compression/patching, clarification, RunSkeptic/Consultant review, approval
  gates, contradiction handling, deciding whether the runner may continue).

Hard rule: MODEL_SIMPLE cannot approve source-truth changes, cannot approve
continuation after meaningful SpecKit output, and cannot resolve contradictions.
"""
from __future__ import annotations

MODEL_SIMPLE = "MODEL_SIMPLE"
MODEL_SMART = "MODEL_SMART"
OPERATIONAL_TIERS: tuple[str, ...] = (MODEL_SIMPLE, MODEL_SMART)

# Canonical four-tier taxonomy (retained; not the operational default).
MODEL_ROUTINE = "MODEL_ROUTINE"
MODEL_DEFAULT = "MODEL_DEFAULT"
MODEL_STRONG = "MODEL_STRONG"
MODEL_CRITICAL = "MODEL_CRITICAL"
CANONICAL_TIERS: tuple[str, ...] = (
    MODEL_ROUTINE,
    MODEL_DEFAULT,
    MODEL_STRONG,
    MODEL_CRITICAL,
)

# Lossless projection: canonical -> operational. SIMPLE absorbs only ROUTINE;
# everything that can change meaning maps to SMART.
CANONICAL_TO_OPERATIONAL: dict[str, str] = {
    MODEL_ROUTINE: MODEL_SIMPLE,
    MODEL_DEFAULT: MODEL_SMART,
    MODEL_STRONG: MODEL_SMART,
    MODEL_CRITICAL: MODEL_SMART,
}

# Machine-readable operation registry. Mechanical -> SIMPLE; meaning -> SMART.
OPERATION_REGISTRY: dict[str, str] = {
    # mechanical
    "file_copy": MODEL_SIMPLE,
    "checksum": MODEL_SIMPLE,
    "path_validation": MODEL_SIMPLE,
    "anchor_generation": MODEL_SIMPLE,
    "manifest_generation": MODEL_SIMPLE,
    "mechanical_diff": MODEL_SIMPLE,
    "stale_check_by_hash": MODEL_SIMPLE,
    "formatting": MODEL_SIMPLE,
    "command_execution": MODEL_SIMPLE,
    "test_running": MODEL_SIMPLE,
    "mirror_materialization": MODEL_SIMPLE,
    # meaning-changing
    "product_meaning": MODEL_SMART,
    "architecture_meaning": MODEL_SMART,
    "hld_compression": MODEL_SMART,
    "hld_patching": MODEL_SMART,
    "clarification_questions": MODEL_SMART,
    "runskeptic_review": MODEL_SMART,
    "consultant_review": MODEL_SMART,
    "approval_gate": MODEL_SMART,
    "contradiction_handling": MODEL_SMART,
    "continuation_decision": MODEL_SMART,
    "single_spec_input_authoring": MODEL_SMART,
    "constitution_proposal": MODEL_SMART,
}

# Operations a MODEL_SIMPLE actor must never own.
SMART_ONLY_AUTHORITIES: frozenset[str] = frozenset(
    {
        "approve_source_truth",
        "approve_continuation_after_meaningful_output",
        "resolve_contradiction",
    }
)


class UnknownOperation(KeyError):
    pass


def operational_tier(canonical_tier: str) -> str:
    """Project a canonical tier onto the operational two-tier model."""
    try:
        return CANONICAL_TO_OPERATIONAL[canonical_tier]
    except KeyError as exc:
        raise UnknownOperation(f"unknown canonical tier: {canonical_tier!r}") from exc


def tier_for_operation(operation: str) -> str:
    """Return the required operational tier for a named operation."""
    try:
        return OPERATION_REGISTRY[operation]
    except KeyError as exc:
        raise UnknownOperation(f"unknown operation: {operation!r}") from exc


def requires_smart(operation: str) -> bool:
    return tier_for_operation(operation) == MODEL_SMART


def can_perform(tier: str, operation: str) -> bool:
    """A SMART actor can perform anything; a SIMPLE actor only SIMPLE operations."""
    required = tier_for_operation(operation)
    if tier == MODEL_SMART:
        return True
    if tier == MODEL_SIMPLE:
        return required == MODEL_SIMPLE
    raise UnknownOperation(f"unknown operational tier: {tier!r}")


def can_own_authority(tier: str, authority: str) -> bool:
    """SMART-only authorities (approve source truth, approve continuation after
    meaningful output, resolve contradiction) are forbidden to SIMPLE."""
    if authority in SMART_ONLY_AUTHORITIES:
        return tier == MODEL_SMART
    return tier in OPERATIONAL_TIERS
