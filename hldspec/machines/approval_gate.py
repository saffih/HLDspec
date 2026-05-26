from __future__ import annotations

import json
from pathlib import Path

from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    MachineContext,
    MachineResult,
    continue_result,
    human_checkpoint,
)


class ApprovalGateMachine:
    name = "ApprovalGateMachine"

    def run(self, context: MachineContext) -> MachineResult:
        workspace = Path(context.workspace or ".")
        sync = workspace / "firstrun" / ".specify" / "sync"

        # If the human has already recorded approval, advance to execution.
        approval_path = sync / "speckit_prework_approval.json"
        if approval_path.exists():
            try:
                record = json.loads(approval_path.read_text(encoding="utf-8"))
            except Exception:
                record = {}
            if record.get("status") == "APPROVED":
                return continue_result(
                    machine=self.name,
                    state="SPECKIT_PREWORK_APPROVED",
                    actions_run=("prework approval confirmed",),
                    artifacts_written=(
                        ArtifactRef(path=str(approval_path), role="speckit_prework_approval"),
                    ),
                )

        return human_checkpoint(
            machine=self.name,
            state="SPECKIT_PREWORK_APPROVAL_GATE",
            kind=CheckpointKind.SPECKIT_PREWORK_APPROVAL_GATE,
            blocking_reason="Prework is ready for human approval before SpecKit is invoked.",
            questions=(),
            controlling_artifacts=(
                ArtifactRef(path=str(sync / "architecture_handoff.md"), role="architecture_handoff", required=False),
                ArtifactRef(path=str(sync / "product_handoff.md"), role="product_handoff", required=False),
                ArtifactRef(path=str(sync / "speckit_prework_package.md"), role="speckit_prework_package"),
                ArtifactRef(path=str(sync / "speckit_prework_quality_review.md"), role="quality_review_report", required=False),
                ArtifactRef(path=str(sync / "speckit_proxy_dossier.md"), role="proxy_dossier", required=False),
                ArtifactRef(path=str(sync / "hldspec_state.md"), role="hldspec_state", required=False),
            ),
            next_action="Human reviews architecture_handoff.md, product_handoff.md, and prework package, then approves, rejects, or requests changes. Only after approval may SpecKit be invoked.",
            forbidden_actions=(
                "Do not write final specs manually from HLDspec.",
                "Do not invoke SpecKit until the human approves this gate.",
                "Do not implement app code.",
            ),
        )
