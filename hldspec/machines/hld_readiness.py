from __future__ import annotations

from hldspec.hld_readiness import write_hld_readiness_artifacts
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    MachineContext,
    MachineResult,
    done_result,
    error_result,
    human_checkpoint,
)
from hldspec.workspace_adapter import TargetWorkspaceAdapter


class HldReadinessMachine:
    name = "HldReadinessMachine"

    def run(self, context: MachineContext) -> MachineResult:
        if not context.workspace:
            return error_result(machine=self.name, state="NO_WORKSPACE", message="workspace is required")

        adapter = TargetWorkspaceAdapter.from_workspace_str(
            context.workspace,
            layout=context.metadata.get("workspace_layout", "legacy"),
        )
        hld = adapter.working_hld
        if not hld.exists():
            return human_checkpoint(
                machine=self.name,
                state="HLD_READINESS_HLD_MISSING",
                kind=CheckpointKind.HLD_READINESS_CHECK,
                blocking_reason="Working HLD is missing; copy or create the workspace HLD before checking readiness.",
                questions=(),
                controlling_artifacts=(ArtifactRef(path=str(hld), role="working_hld", required=True),),
                next_action="Provide a working HLD, then rerun check HLD.",
                forbidden_actions=("Do not invoke SpecKit.", "Do not initialize Build Loop.", "Do not implement app code."),
            )

        readiness = write_hld_readiness_artifacts(hld, adapter.sync_dir)
        artifacts = (
            ArtifactRef(path=str(adapter.sync_dir / "hld_cross_examination.json"), role="cross_examination_json"),
            ArtifactRef(path=str(adapter.sync_dir / "hld_cross_examination.md"), role="cross_examination_report"),
            ArtifactRef(path=str(adapter.sync_dir / "hld_readiness_check.json"), role="readiness_json"),
            ArtifactRef(path=str(adapter.sync_dir / "hld_readiness_check.md"), role="readiness_report"),
        )
        verdict = str(readiness.get("verdict", "HLD_BLOCKED"))
        if verdict == "HLD_READY":
            return done_result(
                machine=self.name,
                state="HLD_READY",
                actions_run=("generated HLD readiness cross-examination",),
                artifacts_written=artifacts,
            )

        questions = tuple(
            HumanQuestion(
                question_id=str(item.get("question_id", "")),
                title=str(item.get("group_id", "HLD readiness question")),
                question=str(item.get("question", "")),
                options=tuple(str(option) for option in item.get("options", [])),
                current_decision=str(item.get("human_decision", "TBD")),
                blocking=True,
            )
            for item in readiness.get("grouped_questions", [])
            if isinstance(item, dict)
        )
        return human_checkpoint(
            machine=self.name,
            state=verdict,
            kind=CheckpointKind.HLD_READINESS_CHECK,
            blocking_reason="HLD readiness cross-examination found grouped questions or accepted-risk choices.",
            questions=questions,
            controlling_artifacts=artifacts,
            next_action=str(readiness.get("next_safe_action", "Review readiness artifacts before continuing.")),
            forbidden_actions=("Do not invoke SpecKit.", "Do not initialize Build Loop.", "Do not implement app code."),
        )
