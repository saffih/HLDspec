"""Conservative Journey 0 product-surface mapping.

This Slice C2 helper builds a typed ProductSurfaceMap from an existing
BrownfieldEvidencePack. It does not collect evidence, classify gaps, compute
readiness, generate update plans, or perform target-side actions.
"""
from __future__ import annotations

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceItem,
    EvidenceLabel,
    ProductSurfaceMap,
)

_UNCLASSIFIED_PRODUCT_SURFACE = (
    "No explicit observed product-surface evidence was classified."
)

_SURFACE_FIELDS = {
    "product_capability": "observed_capabilities",
    "product_actor": "observed_users_or_actors",
    "product_input_output": "observed_inputs_outputs",
    "product_workflow": "observed_workflows",
    "product_limit": "known_limits",
}


def build_journey0_product_surface_map(
    evidence_pack: BrownfieldEvidencePack,
) -> ProductSurfaceMap:
    """Build a conservative product-surface map from typed evidence.

    Only explicit OBSERVED product-surface evidence populates observed fields.
    Generic file presence, code files, old spec state, and HLD-looking fragments
    do not become product claims.
    """

    surface: dict[str, list[str]] = {
        "observed_capabilities": [],
        "observed_users_or_actors": [],
        "observed_inputs_outputs": [],
        "observed_workflows": [],
        "known_limits": [],
        "unknowns": [],
        "source_refs": [],
    }

    for item in evidence_pack.evidence:
        field_name = _SURFACE_FIELDS.get(item.source_type)
        if field_name is None:
            continue
        if item.label == EvidenceLabel.OBSERVED:
            _append_unique(surface[field_name], _surface_text(item))
            _append_unique(surface["source_refs"], item.evidence_id)
        else:
            _append_unique(
                surface["unknowns"],
                f"{item.source_type} evidence is {item.label.value}: {item.summary}",
            )
            _append_unique(surface["source_refs"], item.evidence_id)

    if not _has_observed_surface(surface):
        _append_unique(surface["unknowns"], _UNCLASSIFIED_PRODUCT_SURFACE)

    return ProductSurfaceMap(
        observed_capabilities=tuple(surface["observed_capabilities"]),
        observed_users_or_actors=tuple(surface["observed_users_or_actors"]),
        observed_inputs_outputs=tuple(surface["observed_inputs_outputs"]),
        observed_workflows=tuple(surface["observed_workflows"]),
        known_limits=tuple(surface["known_limits"]),
        unknowns=tuple(surface["unknowns"]),
        source_refs=tuple(surface["source_refs"]),
    )


def _surface_text(item: EvidenceItem) -> str:
    return item.summary


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _has_observed_surface(surface: dict[str, list[str]]) -> bool:
    return any(
        surface[field_name]
        for field_name in (
            "observed_capabilities",
            "observed_users_or_actors",
            "observed_inputs_outputs",
            "observed_workflows",
            "known_limits",
        )
    )
