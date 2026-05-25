"""Canonical RunSkeptic finding schema.

Single source of truth for required fields, aliases, and normalization.
Both the meta-review producer and the evidence-quality reviewer import from here.

Required evidence fields (every RunSkeptic item must have all of these):
  - observed_evidence  : what was directly checked
  - evidence_level     : observed / inferred / unknown
  - confidence         : HIGH / MEDIUM / LOW
  - unknowns           : open questions, or explicit "none"
  - verification       : how the finding can be verified
  - residual_risk      : risk remaining after any recommended fix
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Required field names (canonical)
# ---------------------------------------------------------------------------

REQUIRED_FINDING_FIELDS: list[str] = [
    "observed_evidence",
    "evidence_level",
    "confidence",
    "unknowns",
    "verification",
    "residual_risk",
]

# ---------------------------------------------------------------------------
# Field aliases — each canonical name maps to the synonyms accepted in JSON.
# First alias in each tuple is the canonical output key.
# ---------------------------------------------------------------------------

FIELD_ALIASES: dict[str, tuple[str, ...]] = {
    "observed_evidence": ("observed_evidence", "evidence", "evidence_checked"),
    "evidence_level":    ("evidence_level", "evidence_levels"),
    "confidence":        ("confidence", "confidence_level"),
    "unknowns":          ("unknowns", "open_questions"),
    "verification":      ("verification", "verify", "verification_plan"),
    "residual_risk":     ("residual_risk", "remaining_risk", "risk_after_fix"),
}

# Fields whose canonical output key differs from their primary alias
# (i.e., the producer uses the shorter alias form)
_ALIAS_TO_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in FIELD_ALIASES.items()
    for alias in aliases
}

# Evidence level allowed values
EVIDENCE_LEVEL_VALUES: frozenset[str] = frozenset({
    "observed", "inferred", "unknown",
})

# Confidence allowed values
CONFIDENCE_VALUES: frozenset[str] = frozenset({
    "HIGH", "MEDIUM", "LOW",
})

# Default values used when a required field has no real value.
# Explicit defaults are required — implicit magic (silent None) is forbidden.
FIELD_DEFAULTS: dict[str, str] = {
    "observed_evidence": "not checked",
    "evidence_level":    "unknown",
    "confidence":        "LOW",
    "unknowns":          "unknown",
    "verification":      "manual review required",
    "residual_risk":     "unknown",
}

# ---------------------------------------------------------------------------
# Canonical finding dataclass (used by the producer)
# ---------------------------------------------------------------------------

@dataclass
class SkepticFinding:
    """One RunSkeptic cycle/finding with all required evidence fields."""
    cycle_id: str
    area: str
    aspect: str
    spotlight: str
    decision: str
    severity: str
    finding: str
    evidence: list[str]               # maps to observed_evidence alias
    recommendation: str
    affected_artifacts: list[str]
    # Required evidence fields
    observed_evidence: list[str] = field(default_factory=list)
    evidence_level: str = FIELD_DEFAULTS["evidence_level"]
    confidence: str = FIELD_DEFAULTS["confidence"]
    unknowns: str = FIELD_DEFAULTS["unknowns"]
    verification: str = FIELD_DEFAULTS["verification"]
    residual_risk: str = FIELD_DEFAULTS["residual_risk"]

    def __post_init__(self) -> None:
        # If observed_evidence is empty, inherit from evidence
        if not self.observed_evidence and self.evidence:
            self.observed_evidence = list(self.evidence)


# ---------------------------------------------------------------------------
# Normalization helpers (used by the reviewer)
# ---------------------------------------------------------------------------

def has_key(item: dict[str, Any], field_name: str) -> bool:
    """Return True if item contains any alias for field_name."""
    return any(key in item for key in FIELD_ALIASES[field_name])


def value_for(item: dict[str, Any], field_name: str) -> Any:
    """Return the first matching alias value for field_name, or None."""
    for key in FIELD_ALIASES[field_name]:
        if key in item:
            return item[key]
    return None


def normalize_text(value: Any) -> str:
    """Flatten any JSON-compatible value to a plain string."""
    import json as _json
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(normalize_text(item) for item in value if normalize_text(item))
    if isinstance(value, dict):
        return _json.dumps(value, sort_keys=True)
    return str(value).strip()


def is_empty_value(value: Any) -> bool:
    """Return True if value is None, empty string, empty list, or empty dict."""
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (dict, list)):
        return len(value) == 0
    return False


def unresolved_unknowns(value: Any) -> bool:
    """Return True if the unknowns field contains unresolved open questions."""
    text = normalize_text(value).lower()
    if not text:
        return False
    return text not in {"none", "n/a", "na", "no", "not applicable", "resolved", "[]"}
