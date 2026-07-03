"""Journey 0 declared product-surface evidence adapter.

Converts explicit structured human declarations into typed EvidenceItems
with product-surface source types. This module does not read the filesystem,
invoke external tools, write files, approve decisions, generate HLD content,
create implementation scope, or wire into the command surface.
"""
from __future__ import annotations

from dataclasses import dataclass

from hldspec.journey0_artifacts import (
    BrownfieldEvidencePack,
    EvidenceItem,
    EvidenceLabel,
    Journey0ArtifactModelError,
)

_PRODUCT_SURFACE_SOURCE_TYPES = frozenset(
    {
        "product_capability",
        "product_actor",
        "product_input_output",
        "product_workflow",
        "product_limit",
    }
)

_MAX_SUMMARY_LENGTH = 280


@dataclass(frozen=True)
class DeclaredProductSurfaceItem:
    """A single explicit human declaration of a product-surface observation."""

    source_type: str
    summary: str
    provenance: str

    def __post_init__(self) -> None:
        if self.source_type not in _PRODUCT_SURFACE_SOURCE_TYPES:
            valid = ", ".join(sorted(_PRODUCT_SURFACE_SOURCE_TYPES))
            raise Journey0ArtifactModelError(
                f"source_type must be one of [{valid}]; "
                f"got {self.source_type!r}"
            )
        if not self.summary or not self.summary.strip():
            raise Journey0ArtifactModelError("summary must be non-empty")
        if len(self.summary) > _MAX_SUMMARY_LENGTH:
            raise Journey0ArtifactModelError(
                f"summary must be at most {_MAX_SUMMARY_LENGTH} characters; "
                f"got {len(self.summary)}"
            )
        if not self.provenance or not self.provenance.strip():
            raise Journey0ArtifactModelError("provenance must be non-empty")


def build_declared_evidence(
    items: tuple[DeclaredProductSurfaceItem, ...],
) -> BrownfieldEvidencePack:
    """Build a BrownfieldEvidencePack from explicit human declarations.

    Each item becomes one EvidenceItem with label=OBSERVED and a DECLARED-NNN
    evidence_id. Empty input produces an empty pack.
    """
    evidence: list[EvidenceItem] = []
    for i, item in enumerate(items, start=1):
        evidence.append(
            EvidenceItem(
                evidence_id=f"DECLARED-{i:03d}",
                source_type=item.source_type,
                source_ref=item.provenance,
                source_location="declared",
                summary=item.summary,
                label=EvidenceLabel.OBSERVED,
                confidence="high",
            )
        )
    return BrownfieldEvidencePack(evidence=tuple(evidence))
