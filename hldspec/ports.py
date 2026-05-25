from __future__ import annotations
from typing import Protocol, Any, runtime_checkable


@runtime_checkable
class HumanDecisionPort(Protocol):
    """Interface for presenting checkpoints and collecting human decisions."""
    def present_checkpoint(self, checkpoint: Any) -> str:
        """Present a checkpoint and return the human's reply string."""
        ...
    def record_decision(self, question_id: str, decision: str, rationale: str = "") -> None:
        """Record a decision for audit trail."""
        ...


@runtime_checkable
class ArtifactStorePort(Protocol):
    """Interface for reading/writing artifacts."""
    def read(self, artifact_name: str, workspace: str) -> dict[str, Any]:
        ...
    def write(self, artifact_name: str, workspace: str, data: dict[str, Any]) -> None:
        ...
