"""Synthetic Journey 0 evidence collector.

This module is a pre-scanner proof slice. It accepts controlled in-memory
fixture data and produces Journey 0 artifact-contract data that can be handed to
the draftability gate. It is not a real repository scanner and performs no
filesystem, process, network, CLI, or tool operations.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_draftability_gate as gate


@dataclass(frozen=True)
class SyntheticEvidence:
    """One declared synthetic evidence item."""

    label: str
    statement: str
    source: str = "synthetic"


@dataclass(frozen=True)
class SyntheticDecision:
    """One declared synthetic product decision."""

    id: str
    status: str = "OPEN"
    question: str = ""


@dataclass(frozen=True)
class SyntheticRequirement:
    """A candidate Journey 1 requirement with declared evidence backing."""

    id: str
    evidence_label: str
    statement: str = ""


@dataclass(frozen=True)
class SyntheticBrownfieldInput:
    """Controlled synthetic fixture input for Journey 0 collector tests."""

    evidence: Sequence[SyntheticEvidence]
    product_decisions: Sequence[SyntheticDecision] = ()
    open_questions: Sequence[str] = ()
    candidate_requirements: Sequence[SyntheticRequirement] = ()
    safety_authority_gaps: Sequence[str] = ()
    repo_state_conflict: bool = False


@dataclass(frozen=True)
class SyntheticJourney0Artifacts:
    """Collected Journey 0 artifact-contract data for a synthetic fixture."""

    evidence_pack: dict[str, Any]
    product_decision_register: list[dict[str, Any]]
    gap_report: dict[str, Any]
    candidate_requirements: list[dict[str, Any]]
    open_questions: list[str]
    safety_authority_gaps: list[str]
    authority: dict[str, Any]

    def draftability_input(self) -> gate.DraftabilityInput:
        return gate.DraftabilityInput(
            evidence_pack=self.evidence_pack,
            gap_report=self.gap_report,
            product_decision_register=self.product_decision_register,
            open_questions=tuple(self.open_questions),
            candidate_requirements=tuple(self.candidate_requirements),
            safety_authority_gaps=tuple(self.safety_authority_gaps),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_pack": self.evidence_pack,
            "product_decision_register": self.product_decision_register,
            "gap_report": self.gap_report,
            "candidate_requirements": self.candidate_requirements,
            "open_questions": self.open_questions,
            "safety_authority_gaps": self.safety_authority_gaps,
            "authority": self.authority,
        }


def collect_synthetic_brownfield_evidence(
    synthetic_input: SyntheticBrownfieldInput,
) -> SyntheticJourney0Artifacts:
    """Collect Journey 0 artifact data from controlled synthetic input only."""

    evidence_pack = {
        "kind": j0.ARTIFACT_BROWNFIELD_EVIDENCE_PACK,
        "evidence": [
            _evidence_item(item)
            for item in synthetic_input.evidence
        ],
    }
    j0.evidence_items(evidence_pack)

    decision_register = [_decision_item(d) for d in synthetic_input.product_decisions]
    j0.open_product_decisions(decision_register)

    gap_report = {
        "kind": j0.ARTIFACT_HLD_GAP_REPORT,
        "repo_state_conflict": bool(synthetic_input.repo_state_conflict),
    }
    j0.validate_artifact(gap_report)

    requirements = [
        _requirement_item(requirement)
        for requirement in synthetic_input.candidate_requirements
    ]

    return SyntheticJourney0Artifacts(
        evidence_pack=evidence_pack,
        product_decision_register=decision_register,
        gap_report=gap_report,
        candidate_requirements=requirements,
        open_questions=list(synthetic_input.open_questions),
        safety_authority_gaps=list(synthetic_input.safety_authority_gaps),
        authority=j0.journey0_authority_profile(),
    )


def evaluate_synthetic_brownfield_fixture(
    synthetic_input: SyntheticBrownfieldInput,
) -> gate.DraftabilityResult:
    """Collect synthetic artifacts and evaluate them with the draftability gate."""

    artifacts = collect_synthetic_brownfield_evidence(synthetic_input)
    return gate.evaluate_hld_draftability(artifacts.draftability_input())


def _evidence_item(item: SyntheticEvidence) -> dict[str, str]:
    label = j0.validate_evidence_label(item.label)
    if not item.statement:
        raise j0.InvalidJourney0ArtifactError("synthetic evidence has no statement")
    return {
        "label": label,
        "statement": item.statement,
        "source": item.source,
    }


def _decision_item(decision: SyntheticDecision) -> dict[str, str]:
    if not decision.id:
        raise j0.InvalidJourney0ArtifactError("synthetic decision has no id")
    return {
        "id": decision.id,
        "status": decision.status,
        "question": decision.question,
    }


def _requirement_item(requirement: SyntheticRequirement) -> dict[str, str]:
    if not requirement.id:
        raise j0.InvalidJourney0ArtifactError("synthetic requirement has no id")
    label = j0.validate_evidence_label(requirement.evidence_label)
    return {
        "id": requirement.id,
        "evidence_label": label,
        "statement": requirement.statement,
    }
