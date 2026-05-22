from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    MachineContext,
    MachineResult,
    blocked_result,
    continue_result,
)


class SpecBuildPlanMachine:
    name = "SpecBuildPlanMachine"

    def run(self, context: MachineContext) -> MachineResult:
        if not context.workspace:
            return blocked_result(
                machine=self.name,
                state="NO_WORKSPACE",
                kind=CheckpointKind.SPEC_BUILD_PLAN_CHECKPOINT,
                blocking_reason="workspace is required",
            )

        workspace = Path(context.workspace)
        sync = workspace / "firstrun" / ".specify" / "sync"
        review = sync / "spec_build_plan_review.md"
        plan_path = sync / "spec_build_plan.json"

        if not review.exists() or not plan_path.exists():
            return blocked_result(
                machine=self.name,
                state="SPEC_BUILD_PLAN_MISSING",
                kind=CheckpointKind.SPEC_BUILD_PLAN_CHECKPOINT,
                blocking_reason="Spec build plan artifacts are missing.",
                controlling_artifacts=(
                    ArtifactRef(path=str(review), role="spec_build_plan_review"),
                    ArtifactRef(path=str(plan_path), role="spec_build_plan_json"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
            )

        plan = self._load_json(plan_path)
        quality = self._quality(plan, review.read_text(encoding="utf-8", errors="replace"))

        if not quality["green"]:
            return blocked_result(
                machine=self.name,
                state="SPEC_BUILD_PLAN_CHECKPOINT",
                kind=CheckpointKind.SPEC_BUILD_PLAN_CHECKPOINT,
                blocking_reason=(
                    "Spec build plan is not green: "
                    f"decision={quality['decision']}, recommendation={quality['recommendation']}, "
                    f"conflicts={quality['conflict_count']}, flagged_specs={quality['flagged_count']}."
                ),
                controlling_artifacts=(
                    ArtifactRef(path=str(review), role="spec_build_plan_review"),
                    ArtifactRef(path=str(plan_path), role="spec_build_plan_json"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
            )

        return continue_result(
            machine=self.name,
            state="SPEC_BUILD_PLAN_GREEN",
            actions_run=("validated spec build plan gate",),
            artifacts_written=(
                ArtifactRef(path=str(review), role="spec_build_plan_review"),
                ArtifactRef(path=str(plan_path), role="spec_build_plan_json"),
            ),
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    @staticmethod
    def _quality(plan: dict[str, Any], review_text: str) -> dict[str, Any]:
        pq = plan.get("plan_quality", {}) if isinstance(plan.get("plan_quality"), dict) else {}
        decision = pq.get("decision", "")
        recommendation = pq.get("recommendation", "")
        conflicts = pq.get("conflicts", [])
        planned = plan.get("planned_specs", []) if isinstance(plan, dict) else []

        flagged = [
            spec.get("planned_spec_id")
            for spec in planned
            if isinstance(spec, dict) and (spec.get("quality_flags") or spec.get("requires_user_review"))
        ]

        continue_true = bool(re.search(r"Continue to target-spec generation:\s*`?true`?", review_text, re.I))
        continue_false = bool(re.search(r"Continue to target-spec generation:\s*`?false`?", review_text, re.I))
        green = continue_true and not continue_false and decision == "FIX" and recommendation == "KEEP_PLAN" and not conflicts and not flagged

        return {
            "green": green,
            "decision": decision,
            "recommendation": recommendation,
            "conflict_count": len(conflicts),
            "flagged_count": len(flagged),
        }
