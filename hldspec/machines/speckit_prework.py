from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hldspec.artifact_contracts import stale_registered_artifacts
from hldspec.gates import prework_gate_status
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    MachineContext,
    MachineResult,
    RunSkepticStatus,
    blocked_result,
    continue_result,
)
from hldspec.workspace_adapter import TargetWorkspaceAdapter


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

        adapter = TargetWorkspaceAdapter.from_workspace_str(
            context.workspace,
            layout=context.metadata.get("workspace_layout", "legacy"),
        )
        sync = adapter.sync_dir
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
        gate = prework_gate_status(review)
        runskeptic = self._runskeptic_status_from_review(review, str(review_json), str(review_md))

        if runskeptic.status in {"ACTION", "CONFLICT"}:
            return blocked_result(
                machine=self.name,
                state="SPECKIT_PREWORK_RUNSKEPTIC_REWORK",
                kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
                blocking_reason=(
                    f"RunSkeptic status is {runskeptic.status}. "
                    "Resolve RunSkeptic findings before invoking SpecKit."
                ),
                controlling_artifacts=(
                    ArtifactRef(path=str(review_json), role="runskeptic_review_json"),
                    ArtifactRef(path=str(review_md), role="runskeptic_review_report", required=False),
                    ArtifactRef(path=str(package), role="speckit_prework_package"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
                runskeptic=runskeptic,
            )

        if not gate.ready:
            return blocked_result(
                machine=self.name,
                state="SPECKIT_PREWORK_REWORK",
                kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
                blocking_reason=(
                    f"SpecKit prework requires rework: status={gate.status}, blockers={gate.blocker_count}."
                ),
                controlling_artifacts=(
                    ArtifactRef(path=str(review_json), role="quality_review_json"),
                    ArtifactRef(path=str(review_md), role="quality_review_report", required=False),
                    ArtifactRef(path=str(package), role="speckit_prework_package"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
                runskeptic=runskeptic,
            )

        workspace_root = adapter.target_root
        stale = stale_registered_artifacts(sync, workspace=workspace_root)
        if stale:
            return blocked_result(
                machine=self.name,
                state="SPECKIT_PREWORK_STALE",
                kind=CheckpointKind.SPECKIT_PREWORK_REWORK,
                blocking_reason=(
                    "Stale prework artifacts detected — inputs changed since last build. "
                    "Rebuild before continuing: " + "; ".join(stale)
                ),
                controlling_artifacts=(
                    ArtifactRef(path=str(review_json), role="quality_review_json"),
                    ArtifactRef(path=str(package), role="speckit_prework_package"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
                runskeptic=runskeptic,
            )

        return continue_result(
            machine=self.name,
            state="SPECKIT_PREWORK_READY_FOR_APPROVAL",
            actions_run=("validated SpecKit prework quality gate",),
            artifacts_written=(
                ArtifactRef(path=str(package), role="speckit_prework_package"),
                ArtifactRef(path=str(review_json), role="quality_review_json"),
                ArtifactRef(path=str(proxy), role="speckit_proxy_dossier", required=False),
                ArtifactRef(path=str(state), role="hldspec_state", required=False),
            ),
            runskeptic=runskeptic,
        )

    @staticmethod
    def _runskeptic_status_from_review(
        review: dict[str, Any],
        review_json_path: str,
        review_md_path: str,
    ) -> RunSkepticStatus:
        explicit_value = None
        for key in ("runskeptic_status", "run_skeptic_status", "skeptic_status"):
            if key in review:
                explicit_value = review.get(key)
                break

        status = SpeckitPreworkMachine._normalize_runskeptic_status(explicit_value)
        next_safe_action = (
            "Resolve RunSkeptic ACTION/CONFLICT findings before invoking SpecKit."
            if status in {"ACTION", "CONFLICT"}
            else ""
        )
        return RunSkepticStatus(
            status=status,
            evidence=(
                ArtifactRef(path=review_json_path, role="runskeptic_review_json"),
                ArtifactRef(path=review_md_path, role="runskeptic_review_report", required=False),
            ),
            next_safe_action=next_safe_action,
        )

    @staticmethod
    def _normalize_runskeptic_status(value: object) -> str:
        text = str(value or "").strip().upper()
        if not text or text in {"MISSING", "UNKNOWN", "NOT_RUN"}:
            return "NOT_RUN"
        if text.startswith("PASS") or text in {"OK", "GREEN"}:
            return "PASS"
        if text.startswith("CONFLICT"):
            return "CONFLICT"
        if text.startswith("ACTION") or text in {"REWORK", "REWORK_REQUIRED", "FIX", "FAILED", "FAIL", "BLOCKER", "BLOCKED"}:
            return "ACTION"
        return "NOT_RUN"

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
