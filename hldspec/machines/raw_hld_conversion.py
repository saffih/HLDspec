from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hldspec import control_paths
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    MachineContext,
    MachineResult,
    blocked_result,
    continue_result,
    done_result,
    error_result,
    human_checkpoint,
)


class RawHldConversionMachine:
    name = "RawHldConversionMachine"

    def run(self, context: MachineContext) -> MachineResult:
        if not context.workspace:
            return error_result(machine=self.name, state="NO_WORKSPACE", message="workspace is required")

        adapter = control_paths.build_target_adapter(
            context.workspace,
            layout=context.metadata.get("workspace_layout", "legacy"),
        )
        working_hld = adapter.working_hld
        queue_json = adapter.conversion_sync_dir / "hld_conversion_decision_queue.json"
        queue_md = adapter.conversion_sync_dir / "hld_conversion_decision_queue.md"

        if not working_hld.exists():
            return blocked_result(
                machine=self.name,
                state="NO_WORKING_HLD",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Working HLD does not exist. Run the read-only first run before conversion.",
                controlling_artifacts=(ArtifactRef(path=str(working_hld), role="working_hld", required=True),),
                forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit.", "Do not implement app code."),
            )

        if self._is_converted_hld(working_hld):
            return done_result(
                machine=self.name,
                state="WORKING_HLD_CONVERTED",
                actions_run=("detected converted working HLD",),
                artifacts_written=(ArtifactRef(path=str(working_hld), role="working_hld", required=True),),
            )

        if not queue_json.exists():
            return blocked_result(
                machine=self.name,
                state="CONVERSION_QUEUE_MISSING",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Working HLD is raw but the conversion decision queue is missing.",
                controlling_artifacts=(ArtifactRef(path=str(queue_json), role="decision_queue", required=True),),
                forbidden_actions=(
                    "Do not convert mechanically without a decision queue.",
                    "Do not modify the source HLD.",
                    "Do not invoke SpecKit.",
                ),
            )

        queue = self._load_queue(queue_json)
        questions = self._questions(queue)
        open_questions = tuple(q for q in questions if q.blocking and q.current_decision == "TBD")

        if open_questions:
            return human_checkpoint(
                machine=self.name,
                state="HLD_CONVERSION_DECISIONS",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Conversion decisions are still TBD.",
                questions=questions,
                controlling_artifacts=(
                    ArtifactRef(path=str(queue_json), role="decision_queue_json", required=True),
                    ArtifactRef(path=str(queue_md), role="decision_queue_report", required=False),
                ),
                next_action="Judge/orchestrator updates the decision queue, then reruns HLDspec.",
                forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit.", "Do not implement app code."),
            )

        return continue_result(
            machine=self.name,
            state="HLD_CONVERSION_DECISIONS_ANSWERED",
            actions_run=("all conversion decisions are answered",),
            artifacts_written=(ArtifactRef(path=str(queue_json), role="decision_queue_json", required=True),),
        )

    @staticmethod
    def _is_converted_hld(path: Path) -> bool:
        text = path.read_text(encoding="utf-8", errors="replace")
        return bool(re.search(r"^## HLD-\d{3} - ", text, flags=re.M))

    @staticmethod
    def _load_queue(path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"expected object in {path}")
        return data

    @staticmethod
    def _questions(queue: dict[str, Any]) -> tuple[HumanQuestion, ...]:
        result: list[HumanQuestion] = []
        for item in queue.get("questions", []):
            if not isinstance(item, dict):
                continue
            source_id = str(item.get("source_candidate_id", "")).strip()
            title = str(item.get("title", "")).strip()
            display_title = f"{source_id} - {title}".strip(" -")
            result.append(
                HumanQuestion(
                    question_id=str(item.get("question_id", "")),
                    title=display_title,
                    question=str(item.get("question", "")),
                    options=tuple(str(option) for option in item.get("options", [])),
                    current_decision=str(item.get("human_decision", "TBD")),
                    blocking=bool(item.get("blocking", True)),
                )
            )
        return tuple(result)
