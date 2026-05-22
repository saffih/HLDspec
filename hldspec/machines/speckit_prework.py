from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hldspec.handoff_docs import write_handoff_docs
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    MachineContext,
    MachineResult,
    blocked_result,
    continue_result,
)


class SpeckitPreworkMachine:
    name = "SpeckitPreworkMachine"

    def run(self, context: MachineContext) -> MachineResult:
        if not context.workspace:
            return blocked_result(
                machine=self.name,
                state="NO_WORKSPACE",
                kind=CheckpointKind.SPECKIT_PREWORK_MISSING,
                blocking_reason="workspace is required",
            )

        sync = Path(context.workspace) / "firstrun" / ".specify" / "sync"
        package = sync / "speckit_prework_package.md"
        review_json = sync / "speckit_prework_quality_review.json"
        review_md = sync / "speckit_prework_quality_review.md"
        proxy = sync / "speckit_proxy_dossier.md"
        state = sync / "hldspec_state.md"

        if not package.exists() or not review_json.exists():
            return blocked_result(
                machine=self.name,
                state="SPECKIT_PREWORK_MISSING",
                kind=CheckpointKind.SPECKIT_PREWORK_MISSING,
                blocking_reason="SpecKit prework artifacts are missing.",
                controlling_artifacts=(
                    ArtifactRef(path=str(package), role="speckit_prework_package"),
                    ArtifactRef(path=str(review_json), role="speckit_prework_quality_review_json"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
            )

        review = self._load_json(review_json)
        status = review.get("status", "MISSING")
        findings = review.get("findings", [])
        blockers = [item for item in findings if isinstance(item, dict) and item.get("severity") == "BLOCKER"]

        if status == "REWORK_REQUIRED" or blockers:
            return blocked_result(
                machine=self.name,
                state="SPECKIT_PREWORK_REWORK",
                kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
                blocking_reason=f"SpecKit prework requires rework: status={status}, blockers={len(blockers)}.",
                controlling_artifacts=(
                    ArtifactRef(path=str(review_json), role="quality_review_json"),
                    ArtifactRef(path=str(review_md), role="quality_review_report", required=False),
                    ArtifactRef(path=str(package), role="speckit_prework_package"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
            )

        architecture_handoff, product_handoff = write_handoff_docs(sync)

        return continue_result(
            machine=self.name,
            state="SPECKIT_PREWORK_READY_FOR_APPROVAL",
            actions_run=("validated Speckit prework quality gate", "generated consolidated handoff docs"),
            artifacts_written=(
                ArtifactRef(path=str(package), role="speckit_prework_package"),
                ArtifactRef(path=str(review_json), role="quality_review_json"),
                ArtifactRef(path=str(proxy), role="speckit_proxy_dossier", required=False),
                ArtifactRef(path=str(state), role="hldspec_state", required=False),
                ArtifactRef(path=str(architecture_handoff), role="architecture_handoff", required=False),
                ArtifactRef(path=str(product_handoff), role="product_handoff", required=False),
            ),
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
