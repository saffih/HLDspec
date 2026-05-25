from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from hldspec.command_runner import CommandRunner
from hldspec.handoff_docs import write_handoff_docs
from hldspec.machines.apply_hld_conversion import ApplyHldConversionMachine
from hldspec.machines.approval_gate import ApprovalGateMachine
from hldspec.machines.raw_hld_conversion import RawHldConversionMachine
from hldspec.machines.spec_build_plan import SpecBuildPlanMachine
from hldspec.machines.speckit_execution import SpecKitExecutionMachine
from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import MachineContext, MachineResult, MachineStatus, error_result


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
        workspace = Path(context.workspace)
        if workspace.exists() and not workspace.is_dir():
            return error_result(machine=self.name, state="WORKSPACE_NOT_A_DIRECTORY", message=f"workspace must be a directory, got a file: {context.workspace}")
        working_hld = workspace / "HLD.md"

        if not working_hld.exists():
            first = self._run_script(repo, "project_first_run.sh", context.source_hld, str(workspace))
            if first.returncode not in {0, 2}:
                return error_result(machine=self.name, state="FIRST_RUN_FAILED", message=f"project_first_run.sh failed rc={first.returncode}: {first.stderr[-1000:]}")

        raw_result = self.raw.run(context)
        if raw_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            return self._wrap(raw_result)

        if raw_result.status == MachineStatus.CONTINUE:
            apply_result = self.apply.run(context)
            if apply_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
                return self._wrap(apply_result)
        else:
            apply_result = raw_result

        first_readonly = self._ensure_first_readonly(repo, context)
        if first_readonly is not None:
            return first_readonly

        plan_result = self.plan.run(context)
        if plan_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            return self._wrap(plan_result)

        prework_result = self.prework.run(context)
        if prework_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            return self._wrap(prework_result)

        sync = workspace / "firstrun" / ".specify" / "sync"
        write_handoff_docs(sync)

        approval_result = self.approval.run(context)
        if approval_result.status in {MachineStatus.STOP_CHECKPOINT, MachineStatus.BLOCKED, MachineStatus.ERROR}:
            return self._wrap(approval_result)

        execution_result = self.execution.run(context)
        return self._wrap(execution_result)

    def _ensure_first_readonly(self, repo: Path, context: MachineContext) -> MachineResult | None:
        workspace = Path(context.workspace or ".")
        review = workspace / "firstrun" / ".specify" / "sync" / "spec_build_plan_review.md"
        if review.exists():
            return None

        working_hld = workspace / "HLD.md"
        firstrun = workspace / "firstrun"
        result = self._run_script(repo, "first_run_readonly.sh", str(working_hld), str(firstrun), "--force")
        if result.returncode not in {0, 2}:
            return error_result(machine=self.name, state="FIRST_READONLY_FAILED", message=f"first_run_readonly.sh failed rc={result.returncode}: {result.stderr[-1000:]}")
        if os.environ.get("HLDSPEC_ROLE_REVIEWS", "").strip().lower() == "local":
            self._ensure_local_role_review_artifacts(working_hld, firstrun / ".specify" / "sync")
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
