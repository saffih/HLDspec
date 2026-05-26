from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from hldspec.command_runner import CommandRunner
from hldspec.event_log import HldspecEvent, append_event, make_event_id
from hldspec.handoff_docs import write_handoff_docs
from hldspec.machines.apply_hld_conversion import ApplyHldConversionMachine
from hldspec.machines.approval_gate import ApprovalGateMachine
from hldspec.machines.raw_hld_conversion import RawHldConversionMachine
from hldspec.machines.spec_build_plan import SpecBuildPlanMachine
from hldspec.machines.speckit_execution import SpecKitExecutionMachine
from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import MachineContext, MachineResult, MachineStatus, error_result
from hldspec.workspace_adapter import TargetWorkspaceAdapter


class ProjectMachine:
    name = "ProjectMachine"

    def __init__(self, runner: CommandRunner | None = None) -> None:
        self.runner = runner or CommandRunner()
        self.raw = RawHldConversionMachine()
        self.apply = ApplyHldConversionMachine(self.runner)
        self.plan = SpecBuildPlanMachine()
        self.prework = SpeckitPreworkMachine()
        self.approval = ApprovalGateMachine()
        self.execution = SpecKitExecutionMachine()

    def run(self, context: MachineContext) -> MachineResult:
        if not context.repo_root or not context.workspace or not context.source_hld:
            return error_result(machine=self.name, state="MISSING_CONTEXT", message="repo_root, source_hld, and workspace are required")

        repo = Path(context.repo_root)
        adapter = TargetWorkspaceAdapter.from_workspace_str(context.workspace)
        workspace = adapter.target_root
        if workspace.exists() and not workspace.is_dir():
            return error_result(machine=self.name, state="WORKSPACE_NOT_A_DIRECTORY", message=f"workspace must be a directory, got a file: {context.workspace}")
        working_hld = adapter.working_hld

        if not working_hld.exists():
            first = self._run_script(repo, "project_first_run.sh", context.source_hld, str(workspace))
            if first.returncode not in {0, 2}:
                return error_result(machine=self.name, state="FIRST_RUN_FAILED", message=f"project_first_run.sh failed rc={first.returncode}: {first.stderr[-1000:]}")

        raw_result = self.raw.run(context)
        self._log_machine_completed(context, raw_result, from_state="START")
        if raw_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            self._log_terminal(context, raw_result)
            return self._wrap(raw_result)

        if raw_result.status == MachineStatus.CONTINUE:
            apply_result = self.apply.run(context)
            self._log_machine_completed(context, apply_result, from_state=raw_result.state)
            if apply_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
                self._log_terminal(context, apply_result)
                return self._wrap(apply_result)
        else:
            apply_result = raw_result

        first_readonly = self._ensure_first_readonly(repo, context)
        if first_readonly is not None:
            return first_readonly

        plan_result = self.plan.run(context)
        self._log_machine_completed(context, plan_result, from_state=apply_result.state)
        if plan_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            self._log_terminal(context, plan_result)
            return self._wrap(plan_result)

        prework_result = self.prework.run(context)
        self._log_machine_completed(context, prework_result, from_state=plan_result.state)
        if prework_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            self._log_terminal(context, prework_result)
            return self._wrap(prework_result)

        write_handoff_docs(adapter.sync_dir)

        approval_result = self.approval.run(context)
        self._log_machine_completed(context, approval_result, from_state=prework_result.state)
        if approval_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            self._log_terminal(context, approval_result)
            return self._wrap(approval_result)

        execution_result = self.execution.run(context)
        self._log_machine_completed(context, execution_result, from_state=approval_result.state)
        self._log_terminal(context, execution_result)
        return self._wrap(execution_result)

    def _event_log_path(self, context: MachineContext) -> Path | None:
        if not context.workspace:
            return None
        return TargetWorkspaceAdapter.from_workspace_str(context.workspace).events_path

    def _log_machine_completed(self, context: MachineContext, result: MachineResult, from_state: str) -> None:
        log_path = self._event_log_path(context)
        if log_path is None:
            return
        event = HldspecEvent(
            event_id=make_event_id(result.machine, from_state),
            timestamp=__import__("time").time(),
            machine=result.machine,
            from_state=from_state,
            to_state=result.state,
            event="machine_completed",
            outputs=[ref.path for ref in result.artifacts_written],
            decision=result.status.value,
        )
        append_event(log_path, event)

    def _log_terminal(self, context: MachineContext, result: MachineResult) -> None:
        log_path = self._event_log_path(context)
        if log_path is None:
            return
        if result.status in {MachineStatus.DONE, MachineStatus.CONTINUE}:
            event_name = "pipeline_complete"
        elif result.status == MachineStatus.ERROR:
            event_name = "pipeline_error"
        else:
            event_name = "pipeline_halted"
        event = HldspecEvent(
            event_id=make_event_id(self.name, result.state),
            timestamp=__import__("time").time(),
            machine=self.name,
            from_state=result.state,
            to_state=result.state,
            event=event_name,
            decision=result.status.value,
        )
        append_event(log_path, event)

    def _ensure_first_readonly(self, repo: Path, context: MachineContext) -> MachineResult | None:
        adapter = TargetWorkspaceAdapter.from_workspace_str(context.workspace or ".")
        review = adapter.sync_dir / "spec_build_plan_review.md"
        if review.exists():
            return None

        result = self._run_script(repo, "first_run_readonly.sh", str(adapter.working_hld), str(adapter.firstrun_dir), "--force")
        if result.returncode not in {0, 2}:
            return error_result(machine=self.name, state="FIRST_READONLY_FAILED", message=f"first_run_readonly.sh failed rc={result.returncode}: {result.stderr[-1000:]}")
        if os.environ.get("HLDSPEC_ROLE_REVIEWS", "").strip().lower() == "local":
            self._ensure_local_role_review_artifacts(adapter.working_hld, adapter.sync_dir)
        return None

    def _run_script(self, repo: Path, name: str, *args: str):
        script = repo / "scripts" / name
        if not script.exists():
            return self.runner.run([sys.executable, "-c", f"import sys; print('missing {script}', file=sys.stderr); sys.exit(1)"], cwd=repo, capture=True)
        return self.runner.run(["bash", str(script), *args], cwd=repo, capture=True)

    def _ensure_local_role_review_artifacts(self, working_hld: Path, sync: Path) -> None:
        sync.mkdir(parents=True, exist_ok=True)
        text = working_hld.read_text(encoding="utf-8", errors="replace") if working_hld.exists() else ""
        headings = [line.strip() for line in text.splitlines() if line.startswith("## ")]
        chunks_path = sync / "raw_hld_chunks.jsonl"
        if not chunks_path.exists():
            chunks = [
                {
                    "chunk_id": f"chunk-{idx:03d}",
                    "heading": heading.removeprefix("## ").strip(),
                    "source": str(working_hld),
                }
                for idx, heading in enumerate(headings or ["## HLD"], start=1)
            ]
            chunks_path.write_text("".join(json.dumps(chunk, sort_keys=True) + "\n" for chunk in chunks), encoding="utf-8")

        findings_path = sync / "raw_hld_scan_findings.jsonl"
        if not findings_path.exists():
            finding = {"finding_id": "LOCAL-SCAN-001", "severity": "INFO", "message": "Local role-review fallback scan completed."}
            findings_path.write_text(json.dumps(finding, sort_keys=True) + "\n", encoding="utf-8")

        review_docs = {
            "architecture_review.md": "Architecture Review",
            "product_review.md": "Product Review",
            "governance_review.md": "Governance Review",
            "role_review_summary.md": "Role Review Summary",
        }
        for filename, title in review_docs.items():
            path = sync / filename
            if not path.exists():
                path.write_text(f"# {title}\n\nLocal fallback review generated from the converted workspace HLD.\n", encoding="utf-8")

    def _wrap(self, result: MachineResult) -> MachineResult:
        return MachineResult(
            machine=self.name,
            state=result.state,
            status=result.status,
            checkpoint=result.checkpoint,
            actions_run=(f"{result.machine}:{result.status.value}", *result.actions_run),
            artifacts_written=result.artifacts_written,
            errors=result.errors,
        )
