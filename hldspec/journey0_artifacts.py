"""Typed Journey 0 artifact models.

This module implements Slice A from
docs/JOURNEY0_SCHEMA_AND_WIRING_PLAN.md: typed in-memory artifact models only.

It intentionally contains no collectors, classifiers, draftability computation,
target discovery, filesystem I/O, CLI surface, toolchain invocation, backlog
creation, HLD writing, or Journey 1/2/3 behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, TypeVar


class Journey0ArtifactModelError(ValueError):
    """Raised when a Journey 0 typed artifact is constructed with bad values."""


class EvidenceLabel(str, Enum):
    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"
    PRODUCT_DECISION_REQUIRED = "PRODUCT_DECISION_REQUIRED"


class Journey0Verdict(str, Enum):
    PASS = "PASS"
    ACTION = "ACTION"
    BLOCKED = "BLOCKED"


class DecisionStatus(str, Enum):
    OPEN = "open"
    DECIDED = "decided"
    DEFERRED = "deferred"


class GapType(str, Enum):
    HLD_GAP = "HLD_gap"
    CODE_GAP = "code_gap"
    HLD_CODE_CONFLICT = "HLD_code_conflict"
    STALE_SPEC_RESIDUE = "stale_spec_residue"
    SAFETY_AUTHORITY_GAP = "safety_authority_gap"


class SpecStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    SUPERSEDED = "superseded"
    PARTIAL = "partial"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


EnumT = TypeVar("EnumT", bound=Enum)


def _require_enum(value: Any, enum_type: type[EnumT], field_name: str) -> EnumT:
    if not isinstance(value, enum_type):
        valid = ", ".join(member.value for member in enum_type)
        raise Journey0ArtifactModelError(
            f"{field_name} must be {enum_type.__name__}; got {value!r} "
            f"(valid values: {valid})"
        )
    return value


def _tuple_of_strings(values: tuple[str, ...], field_name: str) -> tuple[str, ...]:
    if not isinstance(values, tuple) or not all(isinstance(item, str) for item in values):
        raise Journey0ArtifactModelError(f"{field_name} must be a tuple of strings")
    return values


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    source_type: str
    source_ref: str
    source_location: str
    summary: str
    label: EvidenceLabel
    confidence: str
    related_items: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_enum(self.label, EvidenceLabel, "label")
        _tuple_of_strings(self.related_items, "related_items")

    @property
    def is_authority(self) -> bool:
        """Journey 0 evidence is never authority by model construction."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "source_type": self.source_type,
            "source_ref": self.source_ref,
            "source_location": self.source_location,
            "summary": self.summary,
            "label": self.label.value,
            "confidence": self.confidence,
            "related_items": list(self.related_items),
        }


@dataclass(frozen=True)
class BrownfieldEvidencePack:
    evidence: tuple[EvidenceItem, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.evidence, tuple) or not all(
            isinstance(item, EvidenceItem) for item in self.evidence
        ):
            raise Journey0ArtifactModelError("evidence must be a tuple of EvidenceItem")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "brownfield_evidence_pack",
            "evidence": [item.to_dict() for item in self.evidence],
        }


@dataclass(frozen=True)
class ProductSurfaceMap:
    observed_capabilities: tuple[str, ...] = ()
    observed_users_or_actors: tuple[str, ...] = ()
    observed_inputs_outputs: tuple[str, ...] = ()
    observed_workflows: tuple[str, ...] = ()
    known_limits: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "observed_capabilities",
            "observed_users_or_actors",
            "observed_inputs_outputs",
            "observed_workflows",
            "known_limits",
            "unknowns",
            "source_refs",
        ):
            _tuple_of_strings(getattr(self, field_name), field_name)

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "product_surface_map",
            "observed_capabilities": list(self.observed_capabilities),
            "observed_users_or_actors": list(self.observed_users_or_actors),
            "observed_inputs_outputs": list(self.observed_inputs_outputs),
            "observed_workflows": list(self.observed_workflows),
            "known_limits": list(self.known_limits),
            "unknowns": list(self.unknowns),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class SpecInventoryItem:
    spec_id: str
    location: str
    status: SpecStatus
    summary: str
    covered_intent: tuple[str, ...] = ()
    implementation_overlap: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_enum(self.status, SpecStatus, "status")
        for field_name in (
            "covered_intent",
            "implementation_overlap",
            "conflicts",
            "source_refs",
        ):
            _tuple_of_strings(getattr(self, field_name), field_name)

    @property
    def becomes_backlog(self) -> bool:
        """Old spec inventory does not become backlog in Journey 0."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "location": self.location,
            "status": self.status.value,
            "summary": self.summary,
            "covered_intent": list(self.covered_intent),
            "implementation_overlap": list(self.implementation_overlap),
            "conflicts": list(self.conflicts),
            "source_refs": list(self.source_refs),
        }


@dataclass(frozen=True)
class SpecInventory:
    specs: tuple[SpecInventoryItem, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.specs, tuple) or not all(
            isinstance(item, SpecInventoryItem) for item in self.specs
        ):
            raise Journey0ArtifactModelError("specs must be a tuple of SpecInventoryItem")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "spec_inventory",
            "specs": [item.to_dict() for item in self.specs],
        }


@dataclass(frozen=True)
class GapItem:
    gap_id: str
    gap_type: GapType
    description: str
    evidence_refs: tuple[str, ...] = ()
    disposition: str = ""
    required_decision_or_next_action: str = ""

    def __post_init__(self) -> None:
        _require_enum(self.gap_type, GapType, "gap_type")
        _tuple_of_strings(self.evidence_refs, "evidence_refs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "description": self.description,
            "evidence_refs": list(self.evidence_refs),
            "disposition": self.disposition,
            "required_decision_or_next_action": self.required_decision_or_next_action,
        }


@dataclass(frozen=True)
class HldCodeSpecGapReport:
    gaps: tuple[GapItem, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.gaps, tuple) or not all(
            isinstance(item, GapItem) for item in self.gaps
        ):
            raise Journey0ArtifactModelError("gaps must be a tuple of GapItem")

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "hld_code_spec_gap_report",
            "gaps": [item.to_dict() for item in self.gaps],
        }


@dataclass(frozen=True)
class ProductDecision:
    decision_id: str
    question: str
    why_human_owned: str
    options: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    recommended_default_if_any: str | None
    decision_status: DecisionStatus
    owner: str | None

    def __post_init__(self) -> None:
        _tuple_of_strings(self.options, "options")
        _tuple_of_strings(self.evidence_refs, "evidence_refs")
        _require_enum(self.decision_status, DecisionStatus, "decision_status")

    @property
    def agent_approved(self) -> bool:
        """Product decisions remain human-owned; the model grants no approval."""
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "question": self.question,
            "why_human_owned": self.why_human_owned,
            "options": list(self.options),
            "evidence_refs": list(self.evidence_refs),
            "recommended_default_if_any": self.recommended_default_if_any,
            "decision_status": self.decision_status.value,
            "owner": self.owner,
        }


@dataclass(frozen=True)
class ProductDecisionRegister:
    decisions: tuple[ProductDecision, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.decisions, tuple) or not all(
            isinstance(item, ProductDecision) for item in self.decisions
        ):
            raise Journey0ArtifactModelError(
                "decisions must be a tuple of ProductDecision"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "product_decision_register",
            "decisions": [item.to_dict() for item in self.decisions],
        }


@dataclass(frozen=True)
class HldDraftabilityVerdict:
    verdict: Journey0Verdict
    reason: str
    blocking_items: tuple[str, ...] = ()
    accepted_evidence_refs: tuple[str, ...] = ()
    required_human_decisions: tuple[str, ...] = ()
    safe_next_action: str = ""

    def __post_init__(self) -> None:
        _require_enum(self.verdict, Journey0Verdict, "verdict")
        for field_name in (
            "blocking_items",
            "accepted_evidence_refs",
            "required_human_decisions",
        ):
            _tuple_of_strings(getattr(self, field_name), field_name)

    @property
    def journey1_only(self) -> bool:
        return True

    @property
    def implementation_ready(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "hld_draftability_verdict",
            "verdict": self.verdict.value,
            "reason": self.reason,
            "blocking_items": list(self.blocking_items),
            "accepted_evidence_refs": list(self.accepted_evidence_refs),
            "required_human_decisions": list(self.required_human_decisions),
            "safe_next_action": self.safe_next_action,
        }


@dataclass(frozen=True)
class HldUpdatePlan:
    hld_sections_to_create_or_update: tuple[str, ...] = ()
    evidence_refs_per_section: dict[str, tuple[str, ...]] = field(default_factory=dict)
    decisions_required_before_writing: tuple[str, ...] = ()
    known_stale_material_to_exclude: tuple[str, ...] = ()
    open_questions_to_carry_forward: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "hld_sections_to_create_or_update",
            "decisions_required_before_writing",
            "known_stale_material_to_exclude",
            "open_questions_to_carry_forward",
        ):
            _tuple_of_strings(getattr(self, field_name), field_name)
        if not isinstance(self.evidence_refs_per_section, dict):
            raise Journey0ArtifactModelError(
                "evidence_refs_per_section must be a dict"
            )
        for section, refs in self.evidence_refs_per_section.items():
            if not isinstance(section, str):
                raise Journey0ArtifactModelError(
                    "evidence_refs_per_section keys must be strings"
                )
            _tuple_of_strings(refs, f"evidence_refs_per_section[{section!r}]")

    @property
    def contains_backlog(self) -> bool:
        return False

    @property
    def contains_helper_handoff(self) -> bool:
        return False

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact": "hld_update_plan",
            "hld_sections_to_create_or_update": list(
                self.hld_sections_to_create_or_update
            ),
            "evidence_refs_per_section": {
                section: list(refs)
                for section, refs in self.evidence_refs_per_section.items()
            },
            "decisions_required_before_writing": list(
                self.decisions_required_before_writing
            ),
            "known_stale_material_to_exclude": list(
                self.known_stale_material_to_exclude
            ),
            "open_questions_to_carry_forward": list(
                self.open_questions_to_carry_forward
            ),
        }
