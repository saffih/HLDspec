from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from hldspec.command_runner import CommandRunner
from hldspec.event_log import HldspecEvent, append_event, make_event_id
from hldspec.handoff_docs import write_handoff_docs
from hldspec import engineering_selection, hld_source_package
from hldspec.machines.apply_hld_conversion import ApplyHldConversionMachine
from hldspec.machines.approval_gate import ApprovalGateMachine
from hldspec.machines.hld_readiness import HldReadinessMachine
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
        self.hld_readiness = HldReadinessMachine()
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
        adapter = self._adapter(context)
        workspace = adapter.target_root
        if workspace.exists() and not workspace.is_dir():
            return error_result(machine=self.name, state="WORKSPACE_NOT_A_DIRECTORY", message=f"workspace must be a directory, got a file: {context.workspace}")
        working_hld = adapter.working_hld

        if adapter.layout == "new":
            self._ensure_new_layout_hld(adapter, Path(context.source_hld))

        if context.metadata.get("trigger") == "check_hld":
            self._ensure_check_hld_workspace_hld(adapter, Path(context.source_hld))
            readiness_result = self.hld_readiness.run(context)
            self._write_check_hld_state(adapter, readiness_result)
            self._log_terminal(context, readiness_result)
            return self._wrap(readiness_result)

        if not working_hld.exists():
            first = self._run_script(repo, "project_first_run.sh", context.source_hld, str(workspace))
            if first.returncode not in {0, 2}:
                return error_result(machine=self.name, state="FIRST_RUN_FAILED", message=f"project_first_run.sh failed rc={first.returncode}: {first.stderr[-1000:]}")

        if adapter.layout == "new" and not (adapter.conversion_sync_dir / "hld_conversion_decision_queue.json").exists():
            first_readonly = self._ensure_first_readonly(repo, context)
            if first_readonly is not None:
                return first_readonly

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
        self._ensure_source_package_guidance(adapter, context)

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
        return self._adapter(context).events_path

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

    @staticmethod
    def _hld_fingerprint(hld: Path) -> str:
        import hashlib
        return hashlib.sha256(hld.read_bytes()).hexdigest() if hld.exists() else ""

    def _ensure_first_readonly(self, repo: Path, context: MachineContext) -> MachineResult | None:
        adapter = self._adapter(context)
        review = adapter.sync_dir / "spec_build_plan_review.md"
        # Rebuild when the readonly artifacts are absent OR the working HLD changed since
        # they were built. Keying only on review.exists() let a changed source reuse a
        # stale plan (same stale-skip bug fixed for the old layout in project_continue.sh).
        fp_file = adapter.firstrun_dir / "source_hld_fingerprint.txt"
        current_fp = self._hld_fingerprint(adapter.working_hld)
        recorded_fp = fp_file.read_text(encoding="utf-8").strip() if fp_file.exists() else ""
        if review.exists() and recorded_fp and recorded_fp == current_fp:
            return None

        result = self._run_script(repo, "first_run_readonly.sh", str(adapter.working_hld), str(adapter.firstrun_dir), "--force")
        if result.returncode not in {0, 2}:
            return error_result(machine=self.name, state="FIRST_READONLY_FAILED", message=f"first_run_readonly.sh failed rc={result.returncode}: {result.stderr[-1000:]}")
        if current_fp:
            fp_file.parent.mkdir(parents=True, exist_ok=True)
            fp_file.write_text(current_fp + "\n", encoding="utf-8")
        self._mirror_tool_sync(adapter)
        if os.environ.get("HLDSPEC_ROLE_REVIEWS", "").strip().lower() == "local":
            self._ensure_local_role_review_artifacts(adapter.working_hld, adapter.sync_dir)
        return None

    def _adapter(self, context: MachineContext) -> TargetWorkspaceAdapter:
        return TargetWorkspaceAdapter.from_workspace_str(
            context.workspace or ".",
            layout=context.metadata.get("workspace_layout", "legacy"),
        )

    @staticmethod
    def _ensure_new_layout_hld(adapter: TargetWorkspaceAdapter, source_hld: Path) -> None:
        adapter.raw_hld.parent.mkdir(parents=True, exist_ok=True)
        adapter.working_hld.parent.mkdir(parents=True, exist_ok=True)
        if source_hld.exists() and not adapter.raw_hld.exists():
            shutil.copyfile(source_hld, adapter.raw_hld)
        if source_hld.exists() and not adapter.working_hld.exists():
            shutil.copyfile(source_hld, adapter.working_hld)

    @staticmethod
    def _ensure_check_hld_workspace_hld(adapter: TargetWorkspaceAdapter, source_hld: Path) -> None:
        adapter.raw_hld.parent.mkdir(parents=True, exist_ok=True)
        adapter.working_hld.parent.mkdir(parents=True, exist_ok=True)
        if not source_hld.exists():
            return
        if not adapter.raw_hld.exists():
            shutil.copyfile(source_hld, adapter.raw_hld)
        if not adapter.working_hld.exists():
            shutil.copyfile(source_hld, adapter.working_hld)

    @staticmethod
    def _ensure_source_package_guidance(adapter: TargetWorkspaceAdapter, context: MachineContext) -> None:
        guidelines = adapter.source_package_dir / "engineering_guidelines.md"
        if guidelines.exists():
            errors = engineering_selection.validate_engineering_guidelines(
                guidelines.read_text(encoding="utf-8", errors="replace")
            )
            if not errors:
                return
        if not adapter.working_hld.exists():
            return
        hld_text = adapter.working_hld.read_text(encoding="utf-8", errors="replace")
        hld_source_ref = context.source_hld or str(adapter.working_hld)
        hld_source_package.build_source_package_content(
            adapter.target_root,
            hld_text,
            hld_source_ref=hld_source_ref,
            project_name=adapter.target_root.name,
            layout=adapter.layout,
            materialize_mirror=False,
        )

    @staticmethod
    def _mirror_tool_sync(adapter: TargetWorkspaceAdapter) -> None:
        if adapter.layout != "new":
            return
        generated_sync = adapter.firstrun_dir / ".specify" / "sync"
        if not generated_sync.exists():
            return
        adapter.sync_dir.mkdir(parents=True, exist_ok=True)
        for item in generated_sync.iterdir():
            dest = adapter.sync_dir / item.name
            if item.is_dir():
                if dest.exists() and not dest.is_dir():
                    dest.unlink()
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

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
            runskeptic=result.runskeptic,
        )

    @staticmethod
    def _write_check_hld_state(adapter: TargetWorkspaceAdapter, result: MachineResult) -> None:
        checkpoint_kind = result.checkpoint.kind.value if result.checkpoint is not None else ""
        next_actions = [result.checkpoint.next_action] if result.checkpoint and result.checkpoint.next_action else []
        freshness_path = adapter.target_root / ".hldspec" / "source_freshness.json"
        stale_warnings: list[str] = []
        working_hld_differs = False
        source_hld_modified = False
        if freshness_path.exists():
            try:
                freshness = json.loads(freshness_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                freshness = {}
            if isinstance(freshness.get("warnings"), list):
                stale_warnings = [str(item) for item in freshness["warnings"] if str(item).strip()]
            working_hld_differs = bool(freshness.get("working_hld_differs_from_source", False))
            source_hld_modified = bool(freshness.get("source_hld_modified", False))
        state = {
            "schema_version": 1,
            "source_hld_modified": source_hld_modified,
            "working_hld_modified": working_hld_differs,
            "current_stage": result.state,
            "last_completed_stage": "HLD_READINESS_CHECK",
            "current_checkpoint": checkpoint_kind,
            "blocking_questions": [
                {
                    "question_id": question.question_id,
                    "title": question.title,
                    "current_decision": question.current_decision,
                }
                for question in (result.checkpoint.open_questions() if result.checkpoint else ())
            ],
            "stale_artifact_warnings": stale_warnings,
            "next_allowed_actions": next_actions,
            "controlling_artifacts": [ref.path for ref in (result.checkpoint.controlling_artifacts if result.checkpoint else ())],
            "supporting_artifacts": [ref.path for ref in result.artifacts_written],
            "legacy_supporting_artifacts": [],
            "notes": [
                "Practical HLD readiness review completed through the check HLD trigger.",
                "This state stops before full SpecKit Preparation, Build Loop init, or implementation.",
            ],
        }
        lines = [
            "# HLDspec State",
            "",
            f"Current stage: `{state['current_stage']}`",
            f"Current checkpoint: `{state['current_checkpoint']}`",
            "",
            "## Next allowed actions",
            "",
        ]
        if next_actions:
            lines.extend(f"- {action}" for action in next_actions)
        else:
            lines.append("- none")
        lines.extend(["", "## Controlling artifacts", ""])
        if state["controlling_artifacts"]:
            lines.extend(f"- {path}" for path in state["controlling_artifacts"])
        else:
            lines.append("- none")
        if stale_warnings:
            lines.extend(["", "## Stale artifact warnings", ""])
            lines.extend(f"- {warning}" for warning in stale_warnings)
        lines.extend(["", "## Notes", ""])
        lines.extend(f"- {note}" for note in state["notes"])
        adapter.sync_dir.mkdir(parents=True, exist_ok=True)
        (adapter.sync_dir / "hldspec_state.json").write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (adapter.sync_dir / "hldspec_state.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
