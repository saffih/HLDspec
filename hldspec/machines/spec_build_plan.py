from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    MachineContext,
    MachineResult,
    continue_result,
    human_checkpoint,
)


class SpecBuildPlanMachine:
    name = "SpecBuildPlanMachine"

    def run(self, context: MachineContext) -> MachineResult:
        if not context.workspace:
            return self._blocked_checkpoint(
                state="NO_WORKSPACE",
                blocking_reason="workspace is required",
                sync=Path("."),
                artifacts=(),
                flagged_specs=(),
                quality={},
            )

        workspace = Path(context.workspace)
        sync = workspace / "firstrun" / ".specify" / "sync"
        review = sync / "spec_build_plan_review.md"
        plan_path = sync / "spec_build_plan.json"
        debug_json = sync / "spec_build_plan_quality_debug.json"
        debug_md = sync / "spec_build_plan_quality_debug.md"

        if not review.exists() or not plan_path.exists():
            quality = {
                "green": False,
                "decision": "MISSING",
                "recommendation": "RUN_FIRST_READONLY",
                "conflict_count": 0,
                "flagged_count": 0,
                "flagged_specs": [],
                "continue_true": False,
                "continue_false": False,
            }
            self._write_debug(debug_json, debug_md, quality)
            return self._blocked_checkpoint(
                state="SPEC_BUILD_PLAN_MISSING",
                blocking_reason="Spec build plan artifacts are missing.",
                sync=sync,
                artifacts=(
                    ArtifactRef(path=str(review), role="spec_build_plan_review"),
                    ArtifactRef(path=str(plan_path), role="spec_build_plan_json"),
                    ArtifactRef(path=str(debug_md), role="spec_build_plan_quality_debug", required=False),
                ),
                flagged_specs=(),
                quality=quality,
            )

        plan = self._load_json(plan_path)
        review_text = review.read_text(encoding="utf-8", errors="replace")
        quality = self._quality(plan, review_text)
        self._write_debug(debug_json, debug_md, quality)

        if not quality["green"]:
            flagged_specs = tuple(quality["flagged_specs"])
            return self._blocked_checkpoint(
                state="SPEC_BUILD_PLAN_CHECKPOINT",
                blocking_reason=(
                    "Spec build plan is not green: "
                    f"decision={quality['decision']}, recommendation={quality['recommendation']}, "
                    f"conflicts={quality['conflict_count']}, flagged_specs={quality['flagged_count']}."
                ),
                sync=sync,
                artifacts=(
                    ArtifactRef(path=str(review), role="spec_build_plan_review"),
                    ArtifactRef(path=str(plan_path), role="spec_build_plan_json"),
                    ArtifactRef(path=str(debug_md), role="spec_build_plan_quality_debug", required=False),
                    ArtifactRef(path=str(debug_json), role="spec_build_plan_quality_debug_json", required=False),
                ),
                flagged_specs=flagged_specs,
                quality=quality,
            )

        return continue_result(
            machine=self.name,
            state="SPEC_BUILD_PLAN_GREEN",
            actions_run=("validated spec build plan gate",),
            artifacts_written=(
                ArtifactRef(path=str(review), role="spec_build_plan_review"),
                ArtifactRef(path=str(plan_path), role="spec_build_plan_json"),
                ArtifactRef(path=str(debug_md), role="spec_build_plan_quality_debug", required=False),
            ),
        )

    def _blocked_checkpoint(
        self,
        *,
        state: str,
        blocking_reason: str,
        sync: Path,
        artifacts: tuple[ArtifactRef, ...],
        flagged_specs: tuple[dict[str, Any], ...],
        quality: dict[str, Any],
    ) -> MachineResult:
        questions = (
            HumanQuestion(
                question_id="SPEC-BUILD-PLAN-001",
                title="Spec build plan not green",
                question=(
                    "Should the judge/orchestrator fix the HLD/spec-boundary plan, accept the current plan with rationale, "
                    "or stop for manual redesign?"
                ),
                options=("FIX_PLAN", "ACCEPT_WITH_RATIONALE", "STOP_FOR_MANUAL_REDESIGN"),
                current_decision="TBD",
                blocking=True,
            ),
        )

        return human_checkpoint(
            machine=self.name,
            state=state,
            kind=CheckpointKind.SPEC_BUILD_PLAN_CHECKPOINT,
            blocking_reason=self._format_blocking_reason(blocking_reason, flagged_specs, quality),
            questions=questions,
            controlling_artifacts=artifacts,
            next_action=(
                "Review spec_build_plan_quality_debug.md and decide whether to fix boundaries, accept with rationale, "
                "or stop for manual redesign. Do not invoke SpecKit while this checkpoint is open."
            ),
            forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
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

        flagged: list[dict[str, Any]] = []
        for idx, spec in enumerate(planned, start=1):
            if not isinstance(spec, dict):
                continue
            quality_flags = spec.get("quality_flags") or []
            requires_review = bool(spec.get("requires_user_review"))
            if quality_flags or requires_review:
                flagged.append(
                    {
                        "index": idx,
                        "planned_spec_id": spec.get("planned_spec_id") or spec.get("id") or f"planned_spec_{idx}",
                        "title": spec.get("title") or spec.get("name") or "",
                        "source_hld_ids": spec.get("source_hld_ids") or spec.get("hld_ids") or spec.get("sources") or [],
                        "quality_flags": quality_flags,
                        "requires_user_review": requires_review,
                        "recommendation": spec.get("recommendation") or spec.get("quality_recommendation") or "",
                    }
                )

        continue_true = bool(re.search(r"Continue to target-spec generation:\s*`?true`?", review_text, re.I))
        continue_false = bool(re.search(r"Continue to target-spec generation:\s*`?false`?", review_text, re.I))
        green = continue_true and not continue_false and decision == "FIX" and recommendation == "KEEP_PLAN" and not conflicts and not flagged

        return {
            "green": green,
            "decision": decision,
            "recommendation": recommendation,
            "conflict_count": len(conflicts),
            "conflicts": conflicts if isinstance(conflicts, list) else [],
            "flagged_count": len(flagged),
            "flagged_specs": flagged,
            "continue_true": continue_true,
            "continue_false": continue_false,
        }

    @staticmethod
    def _format_blocking_reason(blocking_reason: str, flagged_specs: tuple[dict[str, Any], ...], quality: dict[str, Any]) -> str:
        lines = [blocking_reason]
        if flagged_specs:
            lines.append("Flagged planned specs:")
            for spec in flagged_specs:
                flags = spec.get("quality_flags") or []
                flags_text = ", ".join(str(item) for item in flags) if isinstance(flags, list) else str(flags)
                title = spec.get("title") or "(untitled)"
                sid = spec.get("planned_spec_id") or "(unknown)"
                lines.append(f"- {sid}: {title}; flags={flags_text}; requires_user_review={spec.get('requires_user_review')}")
        elif quality:
            lines.append("No flagged spec details were found in plan JSON.")
        return "\n".join(lines)

    @staticmethod
    def _write_debug(json_path: Path, md_path: Path, quality: dict[str, Any]) -> None:
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(quality, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        lines = [
            "# Spec Build Plan Quality Debug",
            "",
            "made by AI",
            "",
            f"Green: `{str(quality.get('green')).lower()}`",
            f"Decision: `{quality.get('decision')}`",
            f"Recommendation: `{quality.get('recommendation')}`",
            f"Conflicts: `{quality.get('conflict_count')}`",
            f"Flagged specs: `{quality.get('flagged_count')}`",
            f"Continue true marker: `{str(quality.get('continue_true')).lower()}`",
            f"Continue false marker: `{str(quality.get('continue_false')).lower()}`",
            "",
            "## Flagged planned specs",
            "",
        ]

        flagged = quality.get("flagged_specs") or []
        if not flagged:
            lines.append("- none")
        else:
            for spec in flagged:
                if not isinstance(spec, dict):
                    continue
                lines.extend(
                    [
                        f"### {spec.get('planned_spec_id')}",
                        "",
                        f"- title: {spec.get('title') or '(untitled)'}",
                        f"- source_hld_ids: {spec.get('source_hld_ids')}",
                        f"- quality_flags: {spec.get('quality_flags')}",
                        f"- requires_user_review: `{str(spec.get('requires_user_review')).lower()}`",
                        f"- recommendation: {spec.get('recommendation') or '(none)'}",
                        "",
                    ]
                )

        lines.extend(
            [
                "## Required decision",
                "",
                "Choose one:",
                "",
                "```text",
                "FIX_PLAN",
                "ACCEPT_WITH_RATIONALE",
                "STOP_FOR_MANUAL_REDESIGN",
                "```",
                "",
                "SpecKit remains blocked until the plan gate is green or explicitly accepted with rationale.",
                "",
            ]
        )

        md_path.write_text("\n".join(lines), encoding="utf-8")
