from __future__ import annotations

from pathlib import Path

from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    MachineContext,
    MachineResult,
    human_checkpoint,
)


class ApprovalGateMachine:
    name = "ApprovalGateMachine"

    def run(self, context: MachineContext) -> MachineResult:
        workspace = Path(context.workspace or ".")
        sync = workspace / "firstrun" / ".specify" / "sync"

        return human_checkpoint(
            machine=self.name,
            state="SPECKIT_PREWORK_APPROVAL_GATE",
            kind=CheckpointKind.SPECKIT_PREWORK_APPROVAL_GATE,
            blocking_reason="Prework is ready for human approval before SpecKit is invoked.",
            questions=(),
            controlling_artifacts=(
                ArtifactRef(path=str(sync / "speckit_prework_package.md"), role="speckit_prework_package"),
                ArtifactRef(path=str(sync / "speckit_prework_quality_review.md"), role="quality_review_report", required=False),
                ArtifactRef(path=str(sync / "speckit_proxy_dossier.md"), role="proxy_dossier", required=False),
                ArtifactRef(path=str(sync / "hldspec_state.md"), role="hldspec_state", required=False),
            ),
            next_action="Human approves, rejects, or requests changes. Only after approval may SpecKit be invoked.",
            forbidden_actions=(
                "Do not write final specs manually from HLDspec.",
                "Do not invoke SpecKit until the human approves this gate.",
                "Do not implement app code.",
            ),
        )
