from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

from hldspec.command_runner import CommandResult, CommandRunner
from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    MachineContext,
    MachineResult,
    blocked_result,
    done_result,
    error_result,
)


class ApplyHldConversionMachine:
    name = "ApplyHldConversionMachine"

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()

    def run(self, context: MachineContext) -> MachineResult:
        if not context.repo_root or not context.workspace:
            return error_result(
                machine=self.name,
                state="MISSING_CONTEXT",
                message="repo_root and workspace are required",
            )

        repo_root = Path(context.repo_root)
        workspace = Path(context.workspace)
        sync = workspace / ".specify" / "sync"
        working_hld = workspace / "HLD.md"
        queue_json = sync / "hld_conversion_decision_queue.json"
        apply_script = repo_root / "scripts" / "apply_hld_conversion_decisions.py"

        if not working_hld.exists():
            return blocked_result(
                machine=self.name,
                state="NO_WORKING_HLD",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Cannot apply conversion because working HLD is missing.",
                controlling_artifacts=(ArtifactRef(path=str(working_hld), role="working_hld"),),
                forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit."),
            )

        if self._is_converted_hld(working_hld):
            return done_result(
                machine=self.name,
                state="WORKING_HLD_ALREADY_CONVERTED",
                artifacts_written=(ArtifactRef(path=str(working_hld), role="working_hld"),),
            )

        if not queue_json.exists():
            return blocked_result(
                machine=self.name,
                state="CONVERSION_QUEUE_MISSING",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Cannot apply conversion because the conversion decision queue is missing.",
                controlling_artifacts=(ArtifactRef(path=str(queue_json), role="decision_queue"),),
                forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit."),
            )

        if self._has_tbd(queue_json):
            return blocked_result(
                machine=self.name,
                state="CONVERSION_DECISIONS_STILL_TBD",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Cannot apply conversion while blocking decisions are still TBD.",
                controlling_artifacts=(ArtifactRef(path=str(queue_json), role="decision_queue"),),
                forbidden_actions=("Do not modify the source HLD.", "Do not invoke SpecKit."),
            )

        if not apply_script.exists():
            return error_result(
                machine=self.name,
                state="APPLY_SCRIPT_MISSING",
                message=f"missing: {apply_script}",
            )

        before_source_hash = self._source_hash(context.source_hld)
        result = self.runner.run(
            [sys.executable, str(apply_script), str(working_hld), str(queue_json)],
            cwd=repo_root,
            capture=True,
        )
        debug_artifacts = self._write_command_debug(sync, result)

        if result.returncode == 2:
            message = self._combined_output(result) or "apply_hld_conversion_decisions.py refused conversion with rc=2"
            return blocked_result(
                machine=self.name,
                state="APPLY_REFUSED",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason=message,
                controlling_artifacts=(
                    ArtifactRef(path=str(queue_json), role="decision_queue"),
                    *debug_artifacts,
                ),
                forbidden_actions=(
                    "Do not modify the source HLD.",
                    "Do not invoke SpecKit.",
                    "Fix the decision queue and rerun HLDspec.",
                ),
                errors=(message,),
            )

        if result.returncode != 0:
            message = self._combined_output(result) or f"apply_hld_conversion_decisions.py failed with rc={result.returncode}"
            return error_result(
                machine=self.name,
                state="APPLY_FAILED",
                message=message,
            )

        after_source_hash = self._source_hash(context.source_hld)
        if before_source_hash is not None and after_source_hash is not None and before_source_hash != after_source_hash:
            return error_result(
                machine=self.name,
                state="SOURCE_HLD_MUTATED",
                message="source HLD changed during conversion apply",
            )

        if not self._is_converted_hld(working_hld):
            return blocked_result(
                machine=self.name,
                state="WORKING_HLD_NOT_CONVERTED",
                kind=CheckpointKind.HLD_CONVERSION_DECISIONS,
                blocking_reason="Apply command completed but the working HLD still does not contain HLD section markers.",
                controlling_artifacts=(
                    ArtifactRef(path=str(working_hld), role="working_hld"),
                    *debug_artifacts,
                ),
                forbidden_actions=("Do not invoke SpecKit.",),
            )

        return done_result(
            machine=self.name,
            state="WORKING_HLD_CONVERTED",
            actions_run=("apply_hld_conversion_decisions.py",),
            artifacts_written=(
                ArtifactRef(path=str(working_hld), role="working_hld"),
                *debug_artifacts,
            ),
        )

    @staticmethod
    def _is_converted_hld(path: Path) -> bool:
        text = path.read_text(encoding="utf-8", errors="replace")
        return bool(re.search(r"^## HLD-\d{3} - ", text, flags=re.M))

    @staticmethod
    def _has_tbd(queue_path: Path) -> bool:
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        for question in queue.get("questions", []):
            if isinstance(question, dict) and question.get("blocking", True) and str(question.get("human_decision", "TBD")) == "TBD":
                return True
        return False

    @staticmethod
    def _source_hash(source_hld: str | None) -> str | None:
        if not source_hld:
            return None
        path = Path(source_hld)
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    @staticmethod
    def _combined_output(result: CommandResult) -> str:
        parts = []
        if result.stdout.strip():
            parts.append("stdout:\n" + result.stdout.strip())
        if result.stderr.strip():
            parts.append("stderr:\n" + result.stderr.strip())
        return "\n\n".join(parts).strip()

    @staticmethod
    def _write_command_debug(sync: Path, result: CommandResult) -> tuple[ArtifactRef, ...]:
        sync.mkdir(parents=True, exist_ok=True)
        json_path = sync / "apply_hld_conversion_command.json"
        md_path = sync / "apply_hld_conversion_command.md"

        payload: dict[str, Any] = {
            "command": list(result.command),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
        json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        md_path.write_text(
            "# Apply HLD Conversion Command\n\n"
            "\n\n"
            f"Return code: `{result.returncode}`\n\n"
            "## Command\n\n"
            "```text\n"
            + " ".join(result.command)
            + "\n```\n\n"
            "## stdout\n\n"
            "```text\n"
            + (result.stdout or "")
            + "\n```\n\n"
            "## stderr\n\n"
            "```text\n"
            + (result.stderr or "")
            + "\n```\n",
            encoding="utf-8",
        )

        return (
            ArtifactRef(path=str(json_path), role="apply_command_debug_json", required=False),
            ArtifactRef(path=str(md_path), role="apply_command_debug_report", required=False),
        )
