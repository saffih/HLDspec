#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import session_control as sc
from hldspec.hld_source_package import build_source_package_content
from hldspec.minimal_agent_request import _workflow_trigger_candidates, detect_workflow_trigger, parse_minimal_agent_request
from hldspec import run_state
from hldspec.source_freshness import load_source_freshness, write_source_freshness
from hldspec import speckit_operator_state as sos
from hldspec import speckit_readiness as sr
from hldspec import git_lifecycle as gl
from hldspec import target_discovery as td
from hldspec import speckit_workspace as sw
from hldspec.machines.project import ProjectMachine
from hldspec.promotion import read_json as read_promotion_json
from hldspec.result_renderer import render_machine_result
from hldspec.state_machine import ArtifactRef, CheckpointKind, ExitCode, MachineContext, MachineResult, human_checkpoint
from hldspec.workspace_adapter import TargetWorkspaceAdapter

SESSION_SCHEMA_VERSION = "1.0"
INTERVIEW_SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def report_status(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "not present", str(path)
    try:
        data = json_read(path)
    except Exception:
        return "ACTION", str(path)
    return str(data.get("status", "UNKNOWN")).upper(), str(path)


def status_is_blocking(status: str) -> bool:
    return status in {"ACTION", "CONFLICT"}


def collect_open_questions(target: Path) -> list[str]:
    questions: list[str] = []
    # Resolve the controller root in external mode; falls back to target/.hldspec
    # otherwise, so non-external behavior is unchanged (hldspec_dir.parent == target).
    hldspec_dir = _resolve_hldspec_dir(target)
    rel_base = hldspec_dir.parent
    interview = json_read(hldspec_dir / "interview_answers.json")
    raw_open = interview.get("open_questions")
    if isinstance(raw_open, list):
        questions.extend(str(item) for item in raw_open if str(item).strip())

    if hldspec_dir.exists():
        for path in sorted(hldspec_dir.rglob("*.json")):
            if "/validation/" in str(path):
                continue
            try:
                data = json_read(path)
            except Exception:
                continue
            checkpoint = data.get("human_checkpoint")
            if isinstance(checkpoint, dict):
                decision = str(checkpoint.get("human_decision", checkpoint.get("decision", "TBD"))).strip().upper()
                if decision in {"", "TBD", "UNKNOWN", "PENDING", "UNRESOLVED"}:
                    label = checkpoint.get("question") or path.relative_to(rel_base)
                    questions.append(str(label))
            checkpoint = data.get("checkpoint")
            if isinstance(checkpoint, dict):
                open_count = checkpoint.get("open_question_count")
                if isinstance(open_count, int) and open_count > 0:
                    checkpoint_id = checkpoint.get("checkpoint_id", path.relative_to(rel_base))
                    questions.append(f"{checkpoint_id}: {open_count} open question(s)")
    return sorted(dict.fromkeys(questions))


def current_state(target: Path, session: dict[str, Any]) -> str:
    hldspec_dir = _resolve_hldspec_dir(target)
    for path in [
        hldspec_dir / "sync" / "hldspec_state.json",
        hldspec_dir / "hldspec_state.json",
    ]:
        state = json_read(path)
        if state:
            stage = state.get("current_stage") or state.get("stage")
            checkpoint = state.get("current_checkpoint") or state.get("checkpoint")
            if stage and checkpoint:
                return f"{stage} / {checkpoint}"
            if stage:
                return str(stage)
    return "agent session prepared" if session else "no session"


def print_bullet_list(items: list[str], empty: str = "none") -> None:
    if not items:
        print(f"- {empty}")
        return
    for item in items:
        print(f"- {item}")


def print_discovery_summary(discovery: dict[str, Any]) -> None:
    paths = discovery.get("report_paths") if isinstance(discovery.get("report_paths"), dict) else {}
    print("## Target Discovery")
    print(f"Classification: {discovery.get('classification', 'UNKNOWN')}")
    print(f"Trusted HLDspec lineage: {str(discovery.get('trusted_hldspec_lineage', False)).lower()}")
    print(f"Phase ledger status: {discovery.get('phase_ledger_status', 'UNKNOWN')}")
    print(f"Phase ledger safety: {discovery.get('phase_ledger_safety', 'UNKNOWN')}")
    if discovery.get("reports_written", True):
        print(f"Discovery report: {paths.get('discovery_json', 'UNKNOWN')}")
        print(f"Phase ledger: {paths.get('ledger_json', 'UNKNOWN')}")
    else:
        print("Discovery reports: not written (target does not exist yet)")
    print("")


def print_git_lifecycle_summary(report: dict[str, Any]) -> None:
    paths = report.get("report_paths") if isinstance(report.get("report_paths"), dict) else {}
    print("## Git Lifecycle")
    print(f"Status: {report.get('lifecycle_status', 'UNKNOWN')}")
    print(f"Safety: {report.get('safety_status', 'UNKNOWN')}")
    print(f"Current branch: {report.get('current_branch') or 'UNKNOWN'}")
    print(f"Report: {paths.get('json', 'UNKNOWN')}")
    print("")


def next_safe_action(session: dict[str, Any], blockers: list[str], open_questions: list[str]) -> str:
    if blockers:
        return "Resolve ACTION/CONFLICT blockers, then rerun status or doctor."
    if open_questions:
        if str(session.get("workflow_trigger") or "") in {"check_hld", "build_loop_prereqs", "build_loop_init", "build_loop_ready"}:
            return str(session.get("next_action") or "Resolve the current checkpoint blockers, then rerun hldspec continue.")
        return "Answer open human questions, then rerun hldspec continue."
    return str(session.get("next_action") or "Run hldspec review --target <target> or hldspec continue --target <target>.")


def source_freshness(target: Path) -> dict[str, Any]:
    return load_source_freshness(target)


def source_freshness_warnings(target: Path) -> list[str]:
    data = source_freshness(target)
    warnings = data.get("warnings", [])
    if not isinstance(warnings, list):
        return []
    return [str(item) for item in warnings if str(item).strip()]


def source_freshness_blocks_build_loop(target: Path) -> bool:
    data = source_freshness(target)
    return bool(data.get("blocking") or data.get("working_hld_differs_from_source") or source_freshness_warnings(target))


def active_workflow_report_path(target: Path, session: dict[str, Any]) -> Path | None:
    trigger = str(session.get("workflow_trigger") or "")
    hldspec_dir = _resolve_hldspec_dir(target)
    mapping = {
        "check_hld": hldspec_dir / "sync" / "hld_readiness_check.json",
        "build_loop_prereqs": hldspec_dir / "sync" / "build_loop_prereqs_report.json",
        "build_loop_init": hldspec_dir / "sync" / "build_loop_init_report.json",
        "build_loop_ready": hldspec_dir / "sync" / "build_loop_ready_report.json",
    }
    return mapping.get(trigger)


def active_workflow_blockers(target: Path, session: dict[str, Any]) -> tuple[list[str], str | None]:
    blockers: list[str] = []
    next_action: str | None = None
    for warning in source_freshness_warnings(target):
        blockers.append(f"Source freshness: {warning}")
    report_path = active_workflow_report_path(target, session)
    report = json_read(report_path) if report_path else {}
    if report:
        status = str(report.get("status") or "").upper()
        state = str(report.get("state") or "")
        if status in {"ACTION", "CONFLICT"}:
            label = state or report_path.name if report_path else "workflow report"
            blockers.append(f"Workflow report: {status} ({label})")
        for item in report.get("blockers") or report.get("warnings") or []:
            if str(item).strip():
                blockers.append(str(item))
        preflight = report.get("approval_preflight")
        if isinstance(preflight, dict):
            for item in preflight.get("blockers") or []:
                if str(item).strip():
                    blockers.append(str(item))
        if isinstance(report.get("next_safe_action"), str) and report["next_safe_action"].strip():
            next_action = str(report["next_safe_action"])
        elif isinstance(report.get("next_actions"), list) and report["next_actions"]:
            next_action = str(report["next_actions"][0])
    state_data = json_read(_resolve_hldspec_dir(target) / "sync" / "hldspec_state.json")
    if state_data:
        for warning in state_data.get("stale_artifact_warnings") or []:
            if str(warning).strip():
                blockers.append(f"Stale artifact: {warning}")
        allowed = state_data.get("next_allowed_actions")
        if not next_action and isinstance(allowed, list) and allowed:
            next_action = str(allowed[0])
    return sorted(dict.fromkeys(blockers)), next_action


def _resolve_hldspec_dir(target: Path) -> Path:
    controller = run_state.controller_root_from_pointer(target)
    return (controller / ".hldspec") if controller is not None else (target / ".hldspec")


def _ensure_target_gitignore(target: Path) -> None:
    gitignore = target / ".gitignore"
    entries = [".hldspec/", "prompts/", run_state.POINTER_FILE]
    existing = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    lines = existing.splitlines()
    new_lines = [e for e in entries if e not in lines]
    if new_lines:
        text = (existing.rstrip("\n") + "\n" + "\n".join(new_lines) + "\n").lstrip("\n")
        gitignore.write_text(text, encoding="utf-8")


def continuation_gate_blockers(target: Path) -> tuple[list[str], str | None]:
    preflight = sc.session_continue_preflight(target)
    if not (preflight.gated and not preflight.allowed):
        return [], None
    blockers = [f"Continuation gate blocked: {preflight.gate or 'UNKNOWN_GATE'}"]
    blockers.extend(str(item) for item in preflight.blockers if str(item).strip())
    next_action = (
        "Provide a valid Context Receipt + Phase Report, resolve the blockers above "
        "(RunSkeptic/Consultant/validation/dirty tree), then rerun continue."
    )
    return sorted(dict.fromkeys(blockers)), next_action


def update_session_after_result(target: Path, result: MachineResult) -> None:
    session_path = _resolve_hldspec_dir(target) / "agent_session.json"
    session = json_read(session_path)
    if not session:
        return
    session["last_machine"] = result.machine
    session["last_state"] = result.state
    session["last_status"] = result.status.value
    if result.checkpoint is not None:
        session["last_checkpoint_kind"] = result.checkpoint.kind.value
        session["next_action"] = result.checkpoint.next_action or session.get("next_action", "")
    elif result.actions_run:
        session["next_action"] = session.get("next_action", "")
    json_write(session_path, session)


def _write_workflow_state(
    target: Path,
    *,
    current_stage: str,
    checkpoint_kind: CheckpointKind,
    next_action: str,
    controlling_artifacts: list[Path],
    notes: list[str],
) -> None:
    sync = _resolve_hldspec_dir(target) / "sync"
    freshness = source_freshness(target)
    stale_warnings = source_freshness_warnings(target)
    state = {
        "schema_version": 1,
        "source_hld_modified": bool(freshness.get("source_hld_modified", False)),
        "working_hld_modified": bool(freshness.get("working_hld_differs_from_source", False)),
        "current_stage": current_stage,
        "last_completed_stage": checkpoint_kind.value,
        "current_checkpoint": checkpoint_kind.value,
        "blocking_questions": [],
        "stale_artifact_warnings": stale_warnings,
        "next_allowed_actions": [next_action] if next_action else [],
        "controlling_artifacts": [str(path) for path in controlling_artifacts],
        "supporting_artifacts": [],
        "legacy_supporting_artifacts": [],
        "notes": notes,
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
    lines.extend([f"- {next_action}"] if next_action else ["- none"])
    lines.extend(["", "## Controlling artifacts", ""])
    lines.extend([f"- {path}" for path in state["controlling_artifacts"]] if state["controlling_artifacts"] else ["- none"])
    if stale_warnings:
        lines.extend(["", "## Stale artifact warnings", ""])
        lines.extend(f"- {warning}" for warning in stale_warnings)
    lines.extend(["", "## Notes", ""])
    lines.extend(f"- {note}" for note in notes)
    json_write(sync / "hldspec_state.json", state)
    (sync / "hldspec_state.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_report(sync: Path, stem: str, payload: dict[str, Any], markdown: str) -> tuple[Path, Path]:
    json_path = sync / f"{stem}.json"
    md_path = sync / f"{stem}.md"
    json_write(json_path, payload)
    md_path.write_text(markdown, encoding="utf-8")
    return json_path, md_path


def _build_loop_checkpoint(
    *,
    state: str,
    kind: CheckpointKind,
    blocking_reason: str,
    next_action: str,
    report_paths: tuple[Path, Path],
    forbidden_actions: tuple[str, ...],
) -> MachineResult:
    return human_checkpoint(
        machine="BuildLoopWorkflow",
        state=state,
        kind=kind,
        blocking_reason=blocking_reason,
        questions=(),
        controlling_artifacts=(
            ArtifactRef(path=str(report_paths[0]), role="workflow_report_json"),
            ArtifactRef(path=str(report_paths[1]), role="workflow_report_md"),
        ),
        next_action=next_action,
        forbidden_actions=forbidden_actions,
    )


def run_workflow_trigger(target: Path, session: dict[str, Any]) -> MachineResult | None:
    workflow_trigger = str(session.get("workflow_trigger") or "")
    if workflow_trigger not in {"build_loop_prereqs", "build_loop_init", "build_loop_ready"}:
        return None

    sync = _resolve_hldspec_dir(target) / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new", controller_root=run_state.controller_root_from_pointer(target))
    source = session.get("source", {}).get("path") if isinstance(session.get("source"), dict) else None
    session_source_sha = session.get("source", {}).get("sha256") if isinstance(session.get("source"), dict) else None

    if source_freshness_blocks_build_loop(target):
        warnings = source_freshness_warnings(target)
        payload = {
            "schema_version": 1,
            "status": "ACTION",
            "state": "SOURCE_FRESHNESS_BLOCKED",
            "warnings": warnings,
            "next_safe_action": "Reconcile targetHLD/HLD.md with the current source HLD or rerun the HLD update/conversion flow before Build Loop work.",
        }
        lines = [
            "# Build Loop Source Freshness Blocker",
            "",
            "STATUS: ACTION",
            "State: SOURCE_FRESHNESS_BLOCKED",
            "",
            "Warnings:",
        ]
        lines.extend(f"- {warning}" for warning in warnings)
        lines.extend(["", f"Next safe action: {payload['next_safe_action']}", ""])
        report_name = {
            "build_loop_prereqs": "build_loop_prereqs_report",
            "build_loop_init": "build_loop_init_report",
            "build_loop_ready": "build_loop_ready_report",
        }[workflow_trigger]
        paths = _write_report(sync, report_name, payload, "\n".join(lines))
        _write_workflow_state(
            target,
            current_stage="SOURCE_FRESHNESS_BLOCKED",
            checkpoint_kind={
                "build_loop_prereqs": CheckpointKind.BUILD_LOOP_PREREQS,
                "build_loop_init": CheckpointKind.BUILD_LOOP_INIT,
                "build_loop_ready": CheckpointKind.BUILD_LOOP_READY,
            }[workflow_trigger],
            next_action=str(payload["next_safe_action"]),
            controlling_artifacts=[paths[0], paths[1]],
            notes=["Build Loop refused to proceed because the workspace HLD copy does not match current source truth."],
        )
        return _build_loop_checkpoint(
            state="SOURCE_FRESHNESS_BLOCKED",
            kind={
                "build_loop_prereqs": CheckpointKind.BUILD_LOOP_PREREQS,
                "build_loop_init": CheckpointKind.BUILD_LOOP_INIT,
                "build_loop_ready": CheckpointKind.BUILD_LOOP_READY,
            }[workflow_trigger],
            blocking_reason="Source HLD freshness blocks Build Loop work.",
            next_action=str(payload["next_safe_action"]),
            report_paths=paths,
            forbidden_actions=("Do not run SpecKit init.", "Do not start /speckit.specify.", "Do not implement app code."),
        )

    if workflow_trigger == "build_loop_prereqs":
        report = sr.build_speckit_init_prereq_report(target)
        paths = _write_report(sync, "build_loop_prereqs_report", report, sr.summarize_speckit_init_prereqs(report))
        state = "INIT_PREREQS_READY" if report.get("status") == "PASS" else "INIT_PREREQS_BLOCKED"
        next_action = str((report.get("next_actions") or ["Use Build Loop init after prerequisite blockers are resolved or remain PASS."])[0])
        _write_workflow_state(
            target,
            current_stage=state,
            checkpoint_kind=CheckpointKind.BUILD_LOOP_PREREQS,
            next_action=next_action,
            controlling_artifacts=[paths[0], paths[1]],
            notes=["Build Loop prereqs checks install/init/git/branch/dirty-tree readiness only.", "Real SpecKit init was not executed."],
        )
        return _build_loop_checkpoint(
            state=state,
            kind=CheckpointKind.BUILD_LOOP_PREREQS,
            blocking_reason="Build Loop prerequisite checkpoint completed.",
            next_action=next_action,
            report_paths=paths,
            forbidden_actions=("Do not start /speckit.specify.", "Do not implement app code."),
        )

    if workflow_trigger == "build_loop_init":
        prereq_report = sr.build_speckit_init_prereq_report(target)
        if prereq_report.get("status") != "PASS":
            payload = {
                "prereq_report": prereq_report,
                "init_result": None,
                "mirror_synced": False,
            }
            lines = [
                "# Build Loop Init Report",
                "",
                "- initialized: `false`",
                "- executed: `false`",
                "- selected command: `none`",
                "- mirror synced: `false`",
                "",
                sr.summarize_speckit_init_prereqs(prereq_report).rstrip(),
                "",
            ]
            paths = _write_report(sync, "build_loop_init_report", payload, "\n".join(lines))
            next_action = str((prereq_report.get("next_actions") or ["Repair Build Loop init prerequisites, then rerun Build Loop init."])[0])
            _write_workflow_state(
                target,
                current_stage="INIT_PREREQS_BLOCKED",
                checkpoint_kind=CheckpointKind.BUILD_LOOP_INIT,
                next_action=next_action,
                controlling_artifacts=[paths[0], paths[1]],
                notes=["Build Loop init refused to execute real SpecKit init because pre-init prerequisites did not PASS."],
            )
            return _build_loop_checkpoint(
                state="INIT_PREREQS_BLOCKED",
                kind=CheckpointKind.BUILD_LOOP_INIT,
                blocking_reason="Build Loop init prerequisites are blocked.",
                next_action=next_action,
                report_paths=paths,
                forbidden_actions=("Do not run SpecKit init until INIT_PREREQS_READY.", "Do not start /speckit.specify.", "Do not implement app code."),
            )

        init_result = sw.plan_or_init_workspace(target, execute=True)
        if init_result.workspace_status and init_result.workspace_status.initialized and adapter.working_hld.exists():
            build_source_package_content(
                target,
                adapter.working_hld.read_text(encoding="utf-8"),
                hld_source_ref=str(source or adapter.working_hld),
                materialize_mirror=True,
                source_sha256=str(session_source_sha) if session_source_sha else None,
            )
        report = sr.build_speckit_readiness_report(target)
        payload = {
            "prereq_report": prereq_report,
            "init_result": init_result.metadata(),
            "readiness_report": report,
            "mirror_synced": bool((target / ".specify" / "source").is_dir()),
        }
        lines = [
            "# Build Loop Init Report",
            "",
            f"- initialized: `{str(init_result.workspace_status.initialized if init_result.workspace_status else False).lower()}`",
            f"- executed: `{str(init_result.executed).lower()}`",
            f"- selected command: `{init_result.selected.display if init_result.selected else 'none'}`",
            f"- mirror synced: `{str((target / '.specify' / 'source').is_dir()).lower()}`",
            "",
            sr.summarize_speckit_readiness(report).rstrip(),
            "",
        ]
        paths = _write_report(sync, "build_loop_init_report", payload, "\n".join(lines))
        initialized = bool(init_result.workspace_status and init_result.workspace_status.initialized)
        mirrored = bool((target / ".specify" / "source").is_dir())
        state = "MIRROR_SYNCED" if initialized and mirrored else ("WORKSPACE_INITIALIZED" if initialized else "BUILD_LOOP_INIT_BLOCKED")
        next_action = (
            "Use Build Loop ready to verify READY_FOR_SPECIFY once branch/gate prerequisites remain PASS."
            if initialized
            else str((report.get("next_actions") or ["Repair SpecKit init blockers, then rerun Build Loop init."])[0])
        )
        _write_workflow_state(
            target,
            current_stage=state,
            checkpoint_kind=CheckpointKind.BUILD_LOOP_INIT,
            next_action=next_action,
            controlling_artifacts=[paths[0], paths[1]],
            notes=["Build Loop init performs or validates real SpecKit init.", "When initialization succeeds, HLDspec rematerializes the .specify/source mirror from the current source package."],
        )
        return _build_loop_checkpoint(
            state=state,
            kind=CheckpointKind.BUILD_LOOP_INIT,
            blocking_reason="Build Loop init checkpoint completed.",
            next_action=next_action,
            report_paths=paths,
            forbidden_actions=("Do not start /speckit.specify unless READY_FOR_SPECIFY is reached.", "Do not implement app code."),
        )

    prereq_report = sr.build_speckit_init_prereq_report(target)
    if prereq_report.get("status") != "PASS":
        payload = {
            "prereq_report": prereq_report,
            "operator_state_report": None,
            "init_result": None,
            "mirror_synced": False,
        }
        paths = _write_report(sync, "build_loop_ready_report", payload, sr.summarize_speckit_init_prereqs(prereq_report))
        next_action = str((prereq_report.get("next_actions") or ["Repair Build Loop prerequisites, then rerun Build Loop ready."])[0])
        _write_workflow_state(
            target,
            current_stage="INIT_PREREQS_BLOCKED",
            checkpoint_kind=CheckpointKind.BUILD_LOOP_READY,
            next_action=next_action,
            controlling_artifacts=[paths[0], paths[1]],
            notes=["Build Loop ready refused to execute real SpecKit init because pre-init prerequisites did not PASS."],
        )
        return _build_loop_checkpoint(
            state="INIT_PREREQS_BLOCKED",
            kind=CheckpointKind.BUILD_LOOP_READY,
            blocking_reason="Build Loop ready prerequisites are blocked.",
            next_action=next_action,
            report_paths=paths,
            forbidden_actions=("Do not run SpecKit init until INIT_PREREQS_READY.", "Do not start /speckit.specify.", "Do not implement app code."),
        )

    init_result = sw.plan_or_init_workspace(target, execute=True)
    if init_result.workspace_status and init_result.workspace_status.initialized and adapter.working_hld.exists():
        build_source_package_content(
            target,
            adapter.working_hld.read_text(encoding="utf-8"),
            hld_source_ref=str(source or adapter.working_hld),
            materialize_mirror=True,
            source_sha256=str(session_source_sha) if session_source_sha else None,
        )
    report = sos.build_speckit_operator_state_report(target)
    preflight = sc.session_continue_preflight(target)
    if report.get("state") == sos.STATE_READY_FOR_SPECIFY and preflight.gated and not preflight.allowed:
        blockers = [str(item) for item in preflight.blockers if str(item).strip()]
        report["status"] = "ACTION"
        report["state"] = "SPECKIT_APPROVAL_GATE_BLOCKED"
        report["next_safe_action"] = (
            "Provide a valid Context Receipt + Phase Report, RunSkeptic/consultant PASS, validation PASS, and human approval before /speckit.specify."
        )
        report["blockers"] = (report.get("blockers") or []) + blockers
        report["approval_preflight"] = {
            "gated": preflight.gated,
            "allowed": preflight.allowed,
            "gate": preflight.gate,
            "blockers": blockers,
        }
    paths = _write_report(sync, "build_loop_ready_report", report, sos.summarize_speckit_operator_state(report))
    state = str(report.get("state", "ACTION"))
    next_action = str(report.get("next_safe_action") or "Resolve Build Loop blockers, then rerun Build Loop ready.")
    _write_workflow_state(
        target,
        current_stage=state,
        checkpoint_kind=CheckpointKind.BUILD_LOOP_READY,
        next_action=next_action,
        controlling_artifacts=[paths[0], paths[1]],
        notes=["Build Loop ready drives to READY_FOR_SPECIFY when all readiness and lifecycle gates pass.", "This checkpoint stops before /speckit.specify."],
    )
    return _build_loop_checkpoint(
        state=state,
        kind=CheckpointKind.BUILD_LOOP_READY,
        blocking_reason="Build Loop ready checkpoint completed.",
        next_action=next_action,
        report_paths=paths,
        forbidden_actions=("Do not start /speckit.specify unless this checkpoint reaches READY_FOR_SPECIFY.", "Do not implement app code."),
    )


def summary_status(blockers: list[str], conflicts: list[str] | None = None) -> str:
    conflicts = conflicts or []
    if conflicts:
        return "CONFLICT"
    if blockers:
        return "ACTION"
    return "PASS"


def ensure_target_dirs(target: Path) -> None:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    # External mode still stages control artifacts locally during start; they are
    # copied to the controller and removed only after the pointer is durable.
    for rel in [
        "targetHLD/raw",
        "targetHLD/sections",
        ".hldspec",
        ".hldspec/sync",
        ".hldspec/context_packs",
        "prompts/agent",
        "prompts/tools",
        "prompts/speckit",
        "specs",
    ]:
        (target / rel).mkdir(parents=True, exist_ok=True)
    adapter.events_path.parent.mkdir(parents=True, exist_ok=True)


def detect_mode(target: Path, source_hash: str | None, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode

    if not target.exists():
        return "create"

    hldspec_dir = _resolve_hldspec_dir(target)
    session = json_read(hldspec_dir / "agent_session.json")
    if not session:
        return "adopt"

    previous_hash = (
        session.get("source", {}).get("sha256")
        if isinstance(session.get("source"), dict)
        else None
    )
    if source_hash and previous_hash and source_hash != previous_hash:
        return "update"

    conflicts = hldspec_dir / "conflicts.json"
    if conflicts.exists():
        return "blocked"

    return "resume"


def copy_source(source: Path, target: Path) -> dict[str, Any]:
    raw = target / "targetHLD" / "raw" / "HLD.raw.md"
    working = target / "targetHLD" / "HLD.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, raw)
    if not working.exists():
        shutil.copyfile(source, working)
    return write_source_freshness(target, source)


def classify_intent(comment: str, mode: str) -> str:
    text = comment.lower()
    for intent in ("create", "update", "upgrade", "adopt", "resume", "review", "debug"):
        if intent in text:
            return intent.upper()
    if mode in {"create", "update", "upgrade", "adopt", "resume"}:
        return mode.upper()
    return "UNKNOWN"


def approval_expectations(comment: str) -> str:
    text = comment.strip()
    if not text:
        return "UNKNOWN"
    lowered = text.lower()
    if "approval" not in lowered and "approve" not in lowered:
        return "UNKNOWN"
    return text


def build_interview_answers(
    *,
    source: Path,
    source_hash: str,
    target: Path,
    mode: str,
    agent: str,
    comment: str,
    timestamp: str,
) -> dict[str, Any]:
    open_questions: list[str] = []
    if not source:
        open_questions.append("source")
    if not target:
        open_questions.append("target")
    if not comment.strip():
        open_questions.append("user_comment")

    return {
        "schema_version": INTERVIEW_SCHEMA_VERSION,
        "created_or_updated_at": timestamp,
        "source": {
            "path": str(source),
            "sha256": source_hash,
        },
        "target": str(target),
        "mode": mode,
        "agent": agent,
        "comment": comment,
        "intent_classification": classify_intent(comment, mode),
        "approval_expectations": approval_expectations(comment),
        "constraints": [],
        "open_questions": open_questions,
    }


def render_interview_answers_md(answers: dict[str, Any]) -> str:
    source = answers.get("source") if isinstance(answers.get("source"), dict) else {}
    constraints = answers.get("constraints") if isinstance(answers.get("constraints"), list) else []
    open_questions = answers.get("open_questions") if isinstance(answers.get("open_questions"), list) else []
    lines = [
        "# HLDspec Interview Answers",
        "",
        f"- schema_version: `{answers.get('schema_version', '')}`",
        f"- created_or_updated_at: `{answers.get('created_or_updated_at', '')}`",
        f"- source path: `{source.get('path', '')}`",
        f"- source sha256: `{source.get('sha256', '')}`",
        f"- target path: `{answers.get('target', '')}`",
        f"- detected mode: `{answers.get('mode', '')}`",
        f"- agent: `{answers.get('agent', '')}`",
        f"- user comment: {answers.get('comment') or 'UNKNOWN'}",
        f"- intent classification: `{answers.get('intent_classification', 'UNKNOWN')}`",
        f"- approval expectations: {answers.get('approval_expectations') or 'UNKNOWN'}",
        "",
        "## Constraints",
        "",
    ]
    lines.extend(f"- {item}" for item in constraints)
    if not constraints:
        lines.append("- none")
    lines.extend(["", "## Open Questions", ""])
    lines.extend(f"- {item}" for item in open_questions)
    if not open_questions:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def write_interview_answers(target: Path, answers: dict[str, Any]) -> tuple[Path, Path]:
    # Start-time staging path: external mode copies this into the controller
    # before deleting target-local control state.
    json_path = target / ".hldspec" / "interview_answers.json"
    md_path = target / ".hldspec" / "interview_answers.md"
    json_write(json_path, answers)
    md_path.write_text(render_interview_answers_md(answers), encoding="utf-8")
    return json_path, md_path


def write_start_prompt(target: Path, session: dict[str, Any], *, controller_root: Path | None = None) -> Path:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new", controller_root=controller_root)
    prompt_root = controller_root or target
    prompt = target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
    prompt.parent.mkdir(parents=True, exist_ok=True)
    source = session["source"]["path"]
    mode = session["mode"]
    agent = session["agent"]
    comment = session.get("comment") or ""
    workflow_trigger = session.get("workflow_trigger") or "default"

    speckit_plan = session.get("speckit_workspace_init", {})
    selected_command = speckit_plan.get("selected_command")
    selected_command_text = " ".join(selected_command) if isinstance(selected_command, list) else "BLOCKED"
    stop_boundary = {
        "check_hld": "Stop after the HLD readiness verdict, grouped clarification questions, and auxiliary reason trail.",
        "build_loop_prereqs": "Stop after the Build Loop prerequisite report. Do not run real SpecKit init.",
        "build_loop_init": "Stop after real SpecKit init validation and post-init mirror sync when applicable.",
        "build_loop_ready": "Stop at READY_FOR_SPECIFY or the first blocking Build Loop checkpoint.",
    }.get(workflow_trigger, "Stop after the next safe checkpoint and report:")
    first_tool = {
        "check_hld": f'scripts/hldspec continue --target "{target}"   # routes to check HLD readiness and stops before SpecKit Preparation',
        "build_loop_prereqs": f'scripts/hldspec continue --target "{target}"   # routes to Build Loop prerequisite checking only',
        "build_loop_init": f'scripts/hldspec continue --target "{target}"   # routes to real SpecKit init validation and mirror sync',
        "build_loop_ready": f'scripts/hldspec continue --target "{target}"   # routes to READY_FOR_SPECIFY when all gates pass',
    }.get(workflow_trigger, f'scripts/hldspec continue --target "{target}"')
    init_boundary = {
        "build_loop_init": (
            "- `hldspec start` records the planned init command without running it.\n"
            "- This `Build Loop init` trigger is an explicit request for `continue` to run or validate real SpecKit init and then stop.\n"
            "- If SpecKit init is blocked, stop and report the blocker. Do not hand-create `.specify/`, `spec.md`, `plan.md`, `tasks.md`, or other final SpecKit artifacts."
        ),
        "build_loop_ready": (
            "- `hldspec start` records the planned init command without running it.\n"
            "- This `Build Loop ready` trigger is an explicit request for `continue` to run or validate real SpecKit init, sync the mirror, and stop at READY_FOR_SPECIFY or the first blocker.\n"
            "- Do not start `/speckit.specify` unless the checkpoint reaches READY_FOR_SPECIFY."
        ),
    }.get(
        workflow_trigger,
        (
            "- `hldspec start` records the planned init command without running it.\n"
            "- Run real SpecKit init only through an explicit Build Loop init/ready trigger or an explicit maintainer `--execute` path.\n"
            "- If SpecKit init is blocked, stop and report the blocker. Do not hand-create `.specify/`, `spec.md`, `plan.md`, `tasks.md`, or other final SpecKit artifacts."
        ),
    )
    prompt.write_text(
        f"""# HLDspec Agent Session

## Role

You are the HLDspec orchestrating agent.

This is an agent-first workflow. Scripts are tools. You own orchestration, judgment, RunSkeptic usage, conflict handling, cost/context economy, and human checkpoints.

## Session

- Agent: `{agent}`
- Mode: `{mode}`
- Workflow trigger: `{workflow_trigger}`
- Source: `{source}`
- Target: `{target}`
- Comment: `{comment}`

## Core rules

1. Treat source HLD/resources as read-only evidence.
2. Work inside `target/`.
3. Use `target/targetHLD/` for HLD evidence and working HLD.
4. Use HLDspec scripts as deterministic tools.
5. Do not manually create final SpecKit specs.
6. Run or apply RunSkeptic at key junctions.
7. Use smallest sufficient context.
8. Use weakest sufficient model.
9. Stop on unresolved CONFLICT.
10. Ask for human approval before risky transitions.

## First tools to consider

```bash
{first_tool}
```

Then inspect:

```text
{adapter.source_package_dir / 'source_package.json'}
{adapter.source_package_dir / 'session_plan.json'}
{adapter.sync_dir / 'spec_build_plan_review.md'}
{adapter.sync_dir / 'speckit_prework_quality_review.md'}
{adapter.sync_dir / 'speckit_proxy_dossier.md'}
```

## Required outputs

Generate or refresh target-specific artifacts:

```text
{adapter.source_package_dir / 'source_package.json'}
{adapter.source_package_dir / 'session_plan.json'}
{adapter.source_package_dir / 'source_manifest.json'}
{adapter.hldspec_dir / 'mediator' / 'mediator_packet.json'}
{prompt_root / 'prompts' / 'mediator' / 'START_MEDIATOR.md'}
{prompt_root / 'prompts' / 'mediator' / 'DEVIN_MEDIATOR_SKILL.md'}
{prompt_root / 'prompts' / 'mediator' / 'CODEX_CLAUDE_MEDIATOR.md'}
target/.specify/                 (from real SpecKit init only; not hand-authored)
target/.specify/source/          (generated mirror only)
{prompt_root / 'prompts'}
```

## Journey 3 mediator guidance

HLDspec generates mediator guidance only; it does not create live Devin/tmux sessions.

Mediator artifacts:

```text
{adapter.hldspec_dir / 'mediator' / 'mediator_packet.json'}
{prompt_root / 'prompts' / 'mediator' / 'START_MEDIATOR.md'}
{prompt_root / 'prompts' / 'mediator' / 'DEVIN_MEDIATOR_SKILL.md'}
{prompt_root / 'prompts' / 'mediator' / 'CODEX_CLAUDE_MEDIATOR.md'}
```

Devin activation sentence:

```text
create agent on {{path}} as {{session-name}} using model {{model}} [permission-mode {{mode}}]
```

## SpecKit workspace/init boundary

- Planned init command: `{selected_command_text}`
{init_boundary}

## Stop condition

{stop_boundary}

- files created or changed
- RunSkeptic PASS/ACTION/CONFLICT findings
- human decisions required
- next allowed action
""",
        encoding="utf-8",
    )
    return prompt


def write_tool_manifest(target: Path, *, controller_root: Path | None = None) -> Path:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new", controller_root=controller_root)
    manifest = target / ".hldspec" / "agent_tool_manifest.md"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        f"""# HLDspec Agent Tool Manifest

Scripts are tools for the HLDspec agent.

## Preferred first analysis tool

```bash
scripts/hldspec continue --target "{target}"
```

## V2 machine tool

```bash
python3 scripts/hldspec_v2.py "{adapter.working_hld}" "{target}"
```

## Canonical target paths

```text
working_hld: {adapter.working_hld}
raw_hld: {adapter.raw_hld}
hldspec_sync: {adapter.sync_dir}
event_log: {adapter.events_path}
speckit_workspace: {adapter.specify_dir}
```

## Rules

- Do not use scripts as the public user workflow.
- Use tools to produce evidence and controlled artifacts.
- Gate promotion through RunSkeptic and human checkpoints.
- Keep final SpecKit artifacts owned by SpecKit.
""",
        encoding="utf-8",
    )
    return manifest


def command_start(args: argparse.Namespace) -> int:
    source_arg = args.source
    target_arg = args.target
    comment = args.comment or ""
    requested_runtime: str | None = None
    effective_agent = args.agent

    if args.request:
        try:
            parsed = parse_minimal_agent_request(args.request)
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        source_arg = parsed.source_hld
        target_arg = parsed.target_workspace
        if not comment:
            comment = parsed.comment
        requested_runtime = parsed.runtime
        if args.agent == "manual":
            effective_agent = parsed.runtime
    else:
        workflow_candidates = _workflow_trigger_candidates(comment)
        if len(workflow_candidates) > 1:
            print(
                "ERROR: ambiguous HLDspec workflow trigger: "
                + ", ".join(workflow_candidates)
                + ". Ask for exactly one of: check HLD, Build Loop prereqs, Build Loop init, Build Loop ready.",
                file=sys.stderr,
            )
            return 2

    if not source_arg or not target_arg:
        print("ERROR: start requires either --request or both --source and --target", file=sys.stderr)
        return 2

    source = Path(source_arg).expanduser().resolve()
    target = Path(target_arg).expanduser().resolve()

    if not source.exists() or not source.is_file():
        print(f"ERROR: source HLD not found: {source}", file=sys.stderr)
        return 2

    source_hash = sha256_file(source)
    mode = detect_mode(target, source_hash, args.mode)
    workflow_trigger = detect_workflow_trigger(comment)
    state_location = args.state_location
    initial_discovery = td.write_discovery_reports(target)
    if initial_discovery.get("classification") == td.CLASS_UNKNOWN_BROWNFIELD:
        print("## HLDspec Start Blocked")
        print_discovery_summary(initial_discovery)
        print("## Blockers")
        print_bullet_list([str(item) for item in initial_discovery.get("blockers", []) if str(item).strip()])
        print("")
        print("## Next Safe Action")
        print(initial_discovery.get("next_safe_action"))
        return ExitCode.GATE_BLOCKED.value
    external_controller_root = (
        run_state.external_run_root(target, source_hash)
        if state_location == "external"
        else None
    )
    session_controller_root = external_controller_root or (target / ".hldspec")

    ensure_target_dirs(target)
    copy_source(source, target)
    _ensure_target_gitignore(target)
    speckit_init = sw.plan_or_init_workspace(target, execute=bool(args.execute))

    timestamp = utc_now()
    _start_adapter = TargetWorkspaceAdapter(target_root=target, layout="new", controller_root=external_controller_root)
    manifest = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "created_or_updated_at": timestamp,
        "agent": effective_agent,
        "requested_runtime": requested_runtime,
        "mode": mode,
        "workflow_trigger": workflow_trigger,
        "state_location": state_location,
        "controller_root": str(session_controller_root),
        "comment": comment,
        "source": {
            "path": str(source),
            "sha256": source_hash,
        },
        "target": str(target),
        "paths": {
            "working_hld": str(_start_adapter.working_hld),
            "raw_hld": str(_start_adapter.raw_hld),
            "hldspec_sync": str(_start_adapter.sync_dir),
            "events": str(_start_adapter.events_path),
            "specify_dir": str(_start_adapter.specify_dir),
            "interview_answers_json": str(_start_adapter.hldspec_dir / "interview_answers.json"),
            "interview_answers_md": str(_start_adapter.hldspec_dir / "interview_answers.md"),
            "start_prompt": str(target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"),
            "tool_manifest": str(_start_adapter.hldspec_dir / "agent_tool_manifest.md"),
            "target_pointer": str(target / run_state.POINTER_FILE),
        },
        "speckit_workspace_init": speckit_init.metadata(),
        "next_action": {
            "check_hld": "Run hldspec continue to execute the HLD readiness check and stop after the readiness verdict.",
            "build_loop_prereqs": "Run hldspec continue to execute the Build Loop prerequisite checkpoint and stop after the prerequisite report.",
            "build_loop_init": "Run hldspec continue to execute the Build Loop init checkpoint and stop after real init validation.",
            "build_loop_ready": "Run hldspec continue to drive the target to READY_FOR_SPECIFY or the first blocking Build Loop checkpoint.",
        }.get(detect_workflow_trigger(comment), "Open prompts/agent/START_HLDSPEC_AGENT.md in an agent session."),
    }
    interview_answers = build_interview_answers(
        source=source,
        source_hash=source_hash,
        target=target,
        mode=mode,
        agent=effective_agent,
        comment=comment,
        timestamp=timestamp,
    )
    json_write(target / ".hldspec" / "agent_session.json", manifest)
    interview_json, interview_md = write_interview_answers(target, interview_answers)
    json_write(
        target / "targetHLD" / "raw" / "resources_manifest.json",
        {
            "schema_version": SESSION_SCHEMA_VERSION,
            "resources": [
                {
                    "kind": "source_hld",
                    "path": str(source),
                    "sha256": source_hash,
                }
            ],
        },
    )
    prompt = write_start_prompt(target, manifest, controller_root=external_controller_root)
    tool_manifest = write_tool_manifest(target, controller_root=external_controller_root)

    # Scaffold the session-plan control plane (dry-run): session_plan.json +
    # bounded subagent packets + runner/consultant prompts + runbook. Written
    # first so the content build hashes the runbook/prompts and mirrors them.
    session_plan = sc.build_session_plan(target, ROOT, backend=sc.DEFAULT_BACKEND)
    session_plan["speckit_workspace_init"] = speckit_init.metadata()
    session_artifacts = sc.write_session_artifacts(target, session_plan)

    # Generate the source-package content from the working HLD (real content flow):
    # HLD.md, HLD.marked.md, hld_reference_map.json, speckit_single_spec_input.md,
    # manifest + metadata, and the derived .specify/source/ mirror.
    # The working HLD is target-owned, so this adapter intentionally has no
    # controller_root even when control state is external.
    working_hld = TargetWorkspaceAdapter(target_root=target, layout="new").working_hld
    source_build = None
    if working_hld.is_file():
        source_build = build_source_package_content(
            target,
            working_hld.read_text(encoding="utf-8"),
            hld_source_ref=str(source),
            materialize_mirror=speckit_init.initialized,
            source_sha256=source_hash,
        )

    print(f"HLDspec agent session prepared.")
    print(f"Mode: {mode}")
    print(f"Target: {target}")
    print(f"Prompt: {prompt}")
    print(f"Tool manifest: {tool_manifest}")
    print(f"Interview answers: {interview_json}")
    print(f"Interview report: {interview_md}")
    print(f"Session plan: {session_artifacts[sc.SESSION_PLAN_FILE]}")
    if speckit_init.selected is not None:
        print(f"SpecKit init command: {' '.join(speckit_init.selected.argv)}")
    if speckit_init.blocker:
        print(f"SpecKit init blocker: {speckit_init.blocker}")
    elif speckit_init.execute:
        if speckit_init.ok:
            print(f"SpecKit workspace initialized: {target / '.specify'}")
        else:
            print(f"SpecKit init validation: {speckit_init.validation_error or speckit_init.stderr or 'FAILED'}")
    if source_build is not None:
        print(f"Source package: {source_build.source_dir} ({source_build.anchor_count} HLD anchors)")
        if source_build.unsupported_claims:
            print(f"Unsupported claims: {len(source_build.unsupported_claims)} (review before approval)")
    if state_location == "external" and external_controller_root is not None:
        copied = run_state.copy_target_control_artifacts(target, controller_root=external_controller_root)
        pointer = run_state.write_pointer(
            target,
            controller_root=external_controller_root,
            source=source,
            source_hash=source_hash,
            mode=mode,
            agent=effective_agent,
            workflow_trigger=workflow_trigger,
            created_or_updated_at=timestamp,
        )
        moved = run_state.delete_target_control_artifacts(target, copied)
        print(f"HLDspec controller state externalized: {external_controller_root}")
        print(f"Target pointer: {pointer}")
        if moved:
            print("Moved controller artifacts:")
            for item in moved:
                print(f"  {item['from']} -> {item['to']}")
    # After externalization the pointer exists, so discovery reports and the
    # printed paths resolve to the controller sync dir, not deleted
    # target-local copies.
    discovery = td.write_discovery_reports(target)
    discovery_paths = discovery.get("report_paths") if isinstance(discovery.get("report_paths"), dict) else {}
    print("Target discovery:")
    print(f"  Classification: {discovery.get('classification')}")
    print(f"  Phase ledger status: {discovery.get('phase_ledger_status')}")
    print(f"  Phase ledger safety: {discovery.get('phase_ledger_safety')}")
    print(f"  Discovery report: {discovery_paths.get('discovery_json', 'UNKNOWN')}")
    print(f"  Phase ledger: {discovery_paths.get('ledger_json', 'UNKNOWN')}")
    mediator_packet = _resolve_hldspec_dir(target) / "mediator" / "mediator_packet.json"
    mediator_start = target / "prompts" / "mediator" / "START_MEDIATOR.md"
    mediator_devin = target / "prompts" / "mediator" / "DEVIN_MEDIATOR_SKILL.md"
    mediator_direct = target / "prompts" / "mediator" / "CODEX_CLAUDE_MEDIATOR.md"
    print("Mediator guidance:")
    print(f"  Mediator packet: {mediator_packet}")
    print(f"  Mediator start prompt: {mediator_start}")
    print(f"  Devin mediator prompt: {mediator_devin}")
    print(f"  Codex/Claude mediator prompt: {mediator_direct}")
    print(
        "  Devin activation sentence: "
        "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]"
    )
    print("  HLDspec generates mediator guidance only; it does not create live Devin/tmux sessions.")
    print("Next: start an agent session with the prompt above.")
    return 0


def command_status(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    hldspec_dir = _resolve_hldspec_dir(target)
    discovery = td.write_discovery_reports(target)
    git_lifecycle = gl.write_git_lifecycle_report(target) if target.exists() else {}
    session_path = hldspec_dir / "agent_session.json"
    session = json_read(session_path)
    if not session:
        print("## HLDspec Status")
        print(f"Target: {target}")
        print("Mode: UNKNOWN")
        print("Workflow trigger: default")
        print("Source: UNKNOWN")
        print("Current state: no session")
        print("")
        print_discovery_summary(discovery)
        if git_lifecycle:
            print_git_lifecycle_summary(git_lifecycle)
        print("## Blockers")
        print_bullet_list([str(item) for item in discovery.get("blockers", []) if str(item).strip()])
        print("")
        print("## Next Safe Action")
        print(discovery.get("next_safe_action"))
        return 0

    validation_status, validation_path = report_status(hldspec_dir / "validation" / "context_prompt_validation.json")
    promotion_status, promotion_path = report_status(hldspec_dir / "validation" / "promotion_gate.json")
    operator_report = sos.build_speckit_operator_state_report(target)
    open_questions = collect_open_questions(target)
    workflow_blockers, workflow_next_action = active_workflow_blockers(target, session)
    gate_blockers, gate_next_action = continuation_gate_blockers(target)
    blockers: list[str] = []
    conflicts: list[str] = []
    for label, status, path in [
        ("Validation", validation_status, validation_path),
        ("Promotion gate", promotion_status, promotion_path),
    ]:
        if status == "CONFLICT":
            conflicts.append(f"{label}: {status} ({path})")
        elif status == "ACTION":
            blockers.append(f"{label}: {status} ({path})")
    blockers.extend(workflow_blockers)
    if str(operator_report.get("status", "")).upper() in {"ACTION", "CONFLICT"}:
        operator_item = f"Operator state: {operator_report.get('status')} ({operator_report.get('state')})"
        if str(operator_report.get("status", "")).upper() == "CONFLICT":
            conflicts.append(operator_item)
        else:
            blockers.append(operator_item)
        blockers.extend(str(item) for item in operator_report.get("blockers", []) if str(item).strip())
    blockers.extend(gate_blockers)

    source = session.get("source", {}).get("path", "UNKNOWN") if isinstance(session.get("source"), dict) else "UNKNOWN"
    print("## HLDspec Status")
    print(f"Target: {target}")
    print(f"Mode: {session.get('mode', 'UNKNOWN')}")
    print(f"Workflow trigger: {session.get('workflow_trigger') or 'default'}")
    print(f"Source: {source}")
    print(f"Current state: {current_state(target, session)}")
    print("")
    print_discovery_summary(discovery)
    print_git_lifecycle_summary(operator_report.get("git_lifecycle_report") if isinstance(operator_report.get("git_lifecycle_report"), dict) else git_lifecycle)
    print("## Validation")
    print(f"Validation status: {validation_status} ({validation_path})")
    print(f"Promotion gate status: {promotion_status} ({promotion_path})")
    print(f"Operator state: {operator_report.get('status')} ({operator_report.get('state')})")
    print("")
    print("## Blockers")
    print_bullet_list(conflicts + blockers)
    print("")
    print("## Open Questions")
    print_bullet_list(open_questions)
    print("")
    print("## Next Safe Action")
    operator_status = str(operator_report.get("status", "")).upper()
    if workflow_next_action:
        selected_next_action = workflow_next_action
    elif operator_status in {"ACTION", "CONFLICT"} and operator_report.get("next_safe_action"):
        selected_next_action = str(operator_report.get("next_safe_action"))
    elif gate_next_action:
        selected_next_action = gate_next_action
    else:
        selected_next_action = str(operator_report.get("next_safe_action") or next_safe_action(session, conflicts + blockers, open_questions))
    print(selected_next_action)
    return 0


def command_review(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    _ctrl = run_state.controller_root_from_pointer(target)
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new", controller_root=_ctrl)
    session = json_read(_resolve_hldspec_dir(target) / "agent_session.json")
    workflow_trigger = session.get("workflow_trigger") if isinstance(session, dict) else None
    blocking_paths = [
        adapter.hldspec_dir / "constitution_update_plan.md",
        adapter.hldspec_dir / "feature_dependency_graph.md",
        adapter.hldspec_dir / "speckit_invocation_queue.md",
        adapter.sync_dir / "spec_build_plan_review.md",
        adapter.sync_dir / "speckit_prework_quality_review.md",
    ]
    optional_paths = [
        adapter.hldspec_dir / "backend_technology_recommendation.md",
        adapter.hldspec_dir / "design_principles_selection.md",
        adapter.hldspec_dir / "spec_packages.md",
        adapter.hldspec_dir / "validation" / "context_prompt_validation.md",
        adapter.hldspec_dir / "validation" / "promotion_gate.md",
    ]
    if workflow_trigger == "check_hld":
        blocking_paths = [
            adapter.sync_dir / "hld_cross_examination.md",
            adapter.sync_dir / "hld_readiness_check.md",
        ]
        optional_paths = [
            adapter.sync_dir / "hld_cross_examination.json",
            adapter.sync_dir / "hld_readiness_check.json",
        ]
    elif workflow_trigger == "build_loop_prereqs":
        blocking_paths = [adapter.sync_dir / "build_loop_prereqs_report.md"]
        optional_paths = [adapter.sync_dir / "build_loop_prereqs_report.json"]
    elif workflow_trigger == "build_loop_init":
        blocking_paths = [adapter.sync_dir / "build_loop_init_report.md"]
        optional_paths = [adapter.sync_dir / "build_loop_init_report.json"]
    elif workflow_trigger == "build_loop_ready":
        blocking_paths = [adapter.sync_dir / "build_loop_ready_report.md"]
        optional_paths = [adapter.sync_dir / "build_loop_ready_report.json"]
    print("## HLDspec Review")
    print("")
    print("## Blocking Review Files")
    print_bullet_list([str(path) for path in blocking_paths if path.exists()])
    print("")
    print("## Optional Context Files")
    print_bullet_list([str(path) for path in optional_paths if path.exists()])
    print("")
    print("## Missing Blocking Files")
    print_bullet_list([str(path) for path in blocking_paths if not path.exists()])
    print("")
    print("## Missing Non-Blocking Files")
    print_bullet_list([str(path) for path in optional_paths if not path.exists()])
    print("")
    print("## Next Safe Action")
    if any(not path.exists() for path in blocking_paths):
        print("Generate or resolve missing blocking review files before approval or promotion.")
    else:
        print("Review blocking files for PASS/ACTION/CONFLICT decisions, then continue only after human-owned checkpoints are resolved.")
    return 0


def command_continue(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    session = json_read(_resolve_hldspec_dir(target) / "agent_session.json")
    workflow_trigger = session.get("workflow_trigger") if isinstance(session, dict) else None
    discovery = td.write_discovery_reports(target)
    unsafe_discovery = (
        discovery.get("classification") == td.CLASS_UNKNOWN_BROWNFIELD
        or bool(discovery.get("blockers"))
        # Safety, not lifecycle: any UNVERIFIED, STALE, or BLOCKED phase
        # artifact makes safety non-PASS and must block continuation.
        or discovery.get("phase_ledger_safety") != td.SAFETY_PASS
    )
    if unsafe_discovery:
        print("## Continuation BLOCKED by target discovery")
        print_discovery_summary(discovery)
        print("Blockers:")
        print_bullet_list([str(item) for item in discovery.get("blockers", []) if str(item).strip()])
        print("Next safe action:")
        print(discovery.get("next_safe_action"))
        return ExitCode.GATE_BLOCKED.value

    # Control-plane gate: when a session plan exists, the gate validator decides
    # continuation. No plan -> legacy behaviour (run ProjectMachine unchanged).
    preflight = sc.session_continue_preflight(target)
    if workflow_trigger not in {"check_hld", "build_loop_prereqs", "build_loop_init", "build_loop_ready"} and preflight.gated and not preflight.allowed:
        print("## Continuation BLOCKED by the control plane")
        print(f"Gate: {preflight.gate}")
        print("Blockers:")
        print_bullet_list(preflight.blockers)
        print("Next safe action:")
        print(
            "Provide a valid Context Receipt + Phase Report, resolve the blockers above "
            "(RunSkeptic/Consultant/validation/dirty tree), then rerun continue."
        )
        return ExitCode.GATE_BLOCKED.value

    source = session.get("source", {}).get("path") if isinstance(session.get("source"), dict) else None
    if not source:
        print(f"ERROR: no source recorded in {_resolve_hldspec_dir(target) / 'agent_session.json'}", file=sys.stderr)
        return 2
    workflow_result = run_workflow_trigger(target, session)
    if workflow_result is not None:
        update_session_after_result(target, workflow_result)
        print(render_machine_result(workflow_result), end="")
        return int(workflow_result.exit_code())
    metadata = {"workspace_layout": "new"}
    if workflow_trigger == "check_hld":
        metadata["trigger"] = "check_hld"

    result = ProjectMachine().run(
        MachineContext(
            repo_root=str(ROOT),
            source_hld=str(Path(source).expanduser()),
            workspace=str(target),
            metadata=metadata,
        )
    )
    update_session_after_result(target, result)
    print(render_machine_result(result), end="")
    return int(result.exit_code())


def command_diff(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()
    session = json_read(_resolve_hldspec_dir(target) / "agent_session.json")

    if not source.exists():
        print(f"ERROR: source not found: {source}", file=sys.stderr)
        return 2

    current_hash = sha256_file(source)
    previous_hash = session.get("source", {}).get("sha256") if session else None

    print(f"Source: {source}")
    print(f"Current hash:  {current_hash}")
    print(f"Recorded hash: {previous_hash or 'none'}")
    if previous_hash == current_hash:
        print("Diff status: unchanged")
        return 0
    print("Diff status: changed")
    return 1


def command_doctor(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve() if args.target else None
    required = [
        ROOT / "AGENTS.md",
        ROOT / "TASKS.md",
        ROOT / "docs" / "DOCS_INDEX.md",
        ROOT / "docs" / "HLDSPEC_TERMINOLOGY_AND_FLOW.md",
        ROOT / "docs" / "HLDSPEC_DEVELOPMENT_HANDOFF.md",
        ROOT / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md",
        ROOT / "docs" / "CANONICAL_FLOW.md",
        ROOT / "docs" / "ARCHITECTURE_V2.md",
        ROOT / "docs" / "HLDSPEC_STABILITY_ARCHITECTURE.md",
    ]
    informational = [
        ROOT / "docs" / "HLDSPEC_MINIMAL_AGENT_UX.md",
        ROOT / "docs" / "ANTI_DRIFT_CONTRACTS.md",
        ROOT / "docs" / "AGENT_FIRST_PRODUCT_MODEL.md",
        ROOT / "docs" / "USER_RUN_MODEL.md",
        ROOT / "scripts" / "first_run_readonly.sh",
        ROOT / "scripts" / "hldspec_v2.py",
    ]
    ok = True
    action_items: list[str] = []
    conflict_items: list[str] = []
    print("## Repo Checks")
    for path in required:
        exists = path.exists()
        print(f"{'OK' if exists else 'MISSING'}: {path}")
        ok = ok and exists
        if not exists:
            action_items.append(f"Missing repo file: {path}")
    print("")
    print("## Repo Informational Checks")
    for path in informational:
        exists = path.exists()
        print(f"{'OK' if exists else 'MISSING'}: {path}")

    if target:
        discovery = td.write_discovery_reports(target)
        _hldspec_dir = _resolve_hldspec_dir(target)
        _ctrl_root = _hldspec_dir.parent
        print("")
        print_discovery_summary(discovery)
        for item in discovery.get("blockers", []) or []:
            if str(item).strip():
                action_items.append(f"Target discovery: {item}")
        print("")
        print("## Target Layout Checks")
        _layout_paths = [
            target / "targetHLD/HLD.md",
            target / "targetHLD/raw/HLD.raw.md",
            _hldspec_dir,
            _hldspec_dir / "sync",
            _ctrl_root / "prompts/agent",
            _ctrl_root / "prompts/speckit",
        ]
        for path in _layout_paths:
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists
            if not exists:
                action_items.append(f"Missing target layout path: {path}")

        print("")
        print("## SpecKit Workspace Checks")
        speckit_dir = target / ".specify"
        session = json_read(_hldspec_dir / "agent_session.json")
        init_meta = session.get("speckit_workspace_init", {}) if isinstance(session, dict) else {}
        print(f"{'OK' if speckit_dir.exists() else 'PLANNED'}: {speckit_dir}")
        if isinstance(init_meta, dict):
            selected = init_meta.get("selected_command")
            if isinstance(selected, list) and selected:
                print(f"Planned init command: {' '.join(str(part) for part in selected)}")
            blocker = init_meta.get("blocker")
            if blocker:
                action_items.append(f"SpecKit init blocker: {blocker}")

        print("")
        print("## Session Checks")
        for path in [_hldspec_dir / "agent_session.json", _ctrl_root / "prompts/agent/START_HLDSPEC_AGENT.md"]:
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists
            if not exists:
                action_items.append(f"Missing session file: {path}")

        print("")
        print("## Source Freshness")
        freshness = source_freshness(target)
        freshness_path = _hldspec_dir / "source_freshness.json"
        print(f"{'OK' if freshness_path.exists() else 'MISSING'}: {freshness_path}")
        print(f"Working HLD differs from source: {str(bool(freshness.get('working_hld_differs_from_source', False))).lower()}")
        freshness_warnings = source_freshness_warnings(target)
        print("Warnings:")
        print_bullet_list(freshness_warnings)
        if not freshness_path.exists():
            action_items.append(f"Missing source freshness metadata: {freshness_path}")
        for warning in freshness_warnings:
            action_items.append(f"Source freshness: {warning}")

        print("")
        print("## Interview Checks")
        for path in [_hldspec_dir / "interview_answers.json", _hldspec_dir / "interview_answers.md"]:
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists
            if not exists:
                action_items.append(f"Missing interview file: {path}")

        readiness = sr.build_speckit_readiness_report(target)
        operator_report = sos.build_speckit_operator_state_report(target, readiness_report=readiness)
        git_lifecycle = operator_report.get("git_lifecycle_report") if isinstance(operator_report.get("git_lifecycle_report"), dict) else {}
        print("")
        print("## SpecKit Readiness")
        print(f"Status: {readiness['status']}")
        print(f"Workspace initialized: {str((readiness.get('workspace_status') or {}).get('initialized', False)).lower()}")
        print(f"Branch hook/manual branch path ready: {readiness.get('branch_hook_status', {}).get('status', 'ACTION')}")
        print("Selected init command:")
        selected = readiness.get("selected_init_command")
        if selected:
            print(f"- {selected['display']}")
        else:
            print("- none")
        print("Available init commands:")
        print_bullet_list([item["display"] for item in readiness.get("available_init_commands", [])])
        print(readiness.get("summary", ""))
        print("Next actions:")
        print_bullet_list(readiness.get("next_actions", []))
        if str(readiness.get("status", "")).upper() == "CONFLICT":
            conflict_items.append("SpecKit readiness: CONFLICT")
        elif str(readiness.get("status", "")).upper() == "ACTION":
            action_items.append("SpecKit readiness: ACTION")
            action_items.extend(str(item) for item in readiness.get("next_actions", []) if str(item).strip())

        print("")
        print("## Operator State")
        print(f"Status: {operator_report.get('status')}")
        print(f"State: {operator_report.get('state')}")
        print(f"Next safe action: {operator_report.get('next_safe_action')}")
        print("Blockers:")
        print_bullet_list([str(item) for item in operator_report.get("blockers", [])])
        if str(operator_report.get("status", "")).upper() == "CONFLICT":
            conflict_items.append(f"Operator state: CONFLICT ({operator_report.get('state')})")
        elif str(operator_report.get("status", "")).upper() == "ACTION":
            action_items.append(f"Operator state: ACTION ({operator_report.get('state')})")
            action_items.extend(str(item) for item in operator_report.get("blockers", []) if str(item).strip())

        print("")
        print_git_lifecycle_summary(git_lifecycle)
        if str(git_lifecycle.get("safety_status", "")).upper() in {"ACTION", "BLOCKED"}:
            action_items.append(f"Git lifecycle: {git_lifecycle.get('lifecycle_status')}")
            action_items.extend(str(item) for item in git_lifecycle.get("blockers", []) if str(item).strip())

        print("")
        print("## Control Plane Checks")
        adapter = TargetWorkspaceAdapter(
            target_root=target,
            layout="new",
            controller_root=run_state.controller_root_from_pointer(target),
        )
        plan_path = adapter.source_package_dir / sc.SESSION_PLAN_FILE
        if plan_path.exists():
            print(f"OK: {plan_path}")
            # Structural health: packets present and plan well-formed are ACTION
            # items. Whether you can continue *right now* (a Phase Report exists,
            # gates satisfied) is informational, not a workspace-health failure.
            for rel in ["subagent_packets/basepack_packet.md", "subagent_packets/runner_packet.md", "subagent_packets/consultant_packet.md"]:
                p = adapter.source_package_dir / rel
                print(f"{'OK' if p.exists() else 'MISSING'}: {p}")
                if not p.exists():
                    action_items.append(f"Missing subagent packet: {p}")
            plan_data = json_read(plan_path)
            if not plan_data.get("current_gate"):
                action_items.append(f"Session plan missing current_gate: {plan_path}")
            preflight = sc.session_continue_preflight(target)
            print(f"Continuation gate: {preflight.gate}")
            print(f"Continuation allowed now: {str(preflight.allowed).lower()}")
            print("Continuation blockers (informational):")
            print_bullet_list(preflight.blockers)
            if preflight.gated and not preflight.allowed:
                action_items.append(f"Continuation gate blocked: {preflight.gate}")
                action_items.extend(preflight.blockers)
        else:
            print(f"MISSING: {plan_path}")
            action_items.append(f"No session plan (run start or hldspec_session_control): {plan_path}")

        print("")
        print("## Validation Reports")
        validation_status, validation_path = report_status(_hldspec_dir / "validation" / "context_prompt_validation.json")
        promotion_status, promotion_path = report_status(_hldspec_dir / "validation" / "promotion_gate.json")
        print(f"Validation status: {validation_status} ({validation_path})")
        print(f"Promotion gate status: {promotion_status} ({promotion_path})")
        for label, status, path in [
            ("Validation", validation_status, validation_path),
            ("Promotion gate", promotion_status, promotion_path),
        ]:
            if status == "CONFLICT":
                conflict_items.append(f"{label}: {status} ({path})")
            elif status == "ACTION":
                action_items.append(f"{label}: {status} ({path})")
        promotion_gate = _hldspec_dir / "validation" / "promotion_gate.json"
        if promotion_gate.exists():
            try:
                gate = read_promotion_json(promotion_gate)
                status = gate.get("status", "UNKNOWN") if isinstance(gate, dict) else "UNKNOWN"
            except Exception:
                status = "INVALID"
            print(f"Promotion gate: {status} ({promotion_gate})")

    print("")
    print("## Final Summary")
    final_status = summary_status(action_items, conflict_items)
    print(f"Summary: {final_status}")
    print("Blockers:")
    print_bullet_list(conflict_items + action_items)
    print("Next safe action:")
    if final_status == "PASS":
        print("Continue with hldspec status, review, or continue as appropriate.")
    else:
        print("Resolve listed ACTION/CONFLICT items, then rerun doctor.")
    if final_status in {"ACTION", "CONFLICT"}:
        return ExitCode.GATE_BLOCKED.value
    return 0 if ok else 2


def command_speckit_doctor(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    report = sr.build_speckit_readiness_report(target)
    print(sr.summarize_speckit_readiness(report), end="")
    return 0 if report["status"] == "PASS" else 2


def command_operator_state(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve() if args.target else None
    report = sos.build_speckit_operator_state_report(target)
    print(sos.summarize_speckit_operator_state(report), end="")
    return 0 if report["status"] == "PASS" else 2


def command_git_lifecycle(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    report = gl.write_git_lifecycle_report(target)
    print(gl.render_git_lifecycle_report(report), end="")
    return 0 if report.get("safety_status") == gl.SAFETY_PASS else ExitCode.GATE_BLOCKED.value


HELP_TOPICS: dict[str, dict[str, str]] = {
    "status": {
        "purpose": "Show where the target is now and what HLDspec thinks the next safe action is.",
        "does": "Reads target discovery, workflow reports, validation/promotion gates, Operator State, blockers, and open questions.",
        "stops_at": "A short summary with Current state, Summary, Blockers, Open questions, and Next safe action.",
        "will_not": "Run SpecKit, edit product code, resolve human decisions, or advance a checkpoint.",
        "example": "HLDspec status target: /path/to/target",
    },
    "doctor": {
        "purpose": "Diagnose why the target is not ready or why status reports ACTION/CONFLICT.",
        "does": "Checks repo docs, target session files, discovery, readiness, Operator State, validation gates, and continuation blockers.",
        "stops_at": "PASS when no action/conflict is visible, otherwise the list of blockers to resolve before continuing.",
        "will_not": "Repair the target automatically, invoke SpecKit, or treat warnings as approval.",
        "example": "HLDspec doctor target: /path/to/target",
    },
    "operator-state": {
        "purpose": "Ask the strongest current readiness/lifecycle question: is this target safe for the next SpecKit/build-loop step?",
        "does": "Combines readiness facts, source freshness, target discovery, phase evidence, and SpecKit lifecycle evidence.",
        "stops_at": "PASS/ACTION/CONFLICT with state, blockers, evidence, and next safe action.",
        "will_not": "Create branches, run SpecKit phases, approve implementation, commit, merge, or adopt unknown brownfield code.",
        "example": "HLDspec operator-state target: /path/to/target",
    },
    "review": {
        "purpose": "Show the human-facing checkpoint/review artifacts for the target.",
        "does": "Lists blocking and optional files the user or judge should inspect.",
        "stops_at": "The available review files and any immediate blockers.",
        "will_not": "Answer checkpoint questions silently or promote artifacts.",
        "example": "HLDspec review target: /path/to/target",
    },
    "continue": {
        "purpose": "Advance only to the next safe HLDspec checkpoint when gates permit.",
        "does": "Runs the ProjectMachine continuation path and stops at blockers or human checkpoints.",
        "stops_at": "The next safe checkpoint, blocker, or completed preparation step.",
        "will_not": "Bypass ACTION/CONFLICT, run implementation, auto-merge, or skip human-owned decisions.",
        "example": "HLDspec continue target: /path/to/target",
    },
    "check hld": {
        "purpose": "Cross-examine the HLD for readiness before investing in SpecKit groundwork.",
        "does": "Reviews HLD readiness, reason trail, grouped clarification questions, and evidence gaps.",
        "stops_at": "Readiness verdict, auxiliary reason trail, grouped clarification questions, and next safe action.",
        "will_not": "Mutate the source HLD, run SpecKit, initialize the Build Loop, or ask repetitive line-by-line questions.",
        "example": "HLDspec review-hld HLD: /path/to/HLD.md target: /path/to/target",
    },
    "build loop": {
        "purpose": "Prepare or supervise the SpecKit Build Loop only through approved boundaries.",
        "does": "Uses Build Loop prereqs/init/ready/status triggers to check prerequisites, init readiness, and next safe SpecKit action.",
        "stops_at": "Prereq report, init report, READY_FOR_SPECIFY, or a blocker that must be resolved first.",
        "will_not": "Run product implementation, create a competing git workflow, or continue past unverified/stale/blocked evidence.",
        "example": "HLDspec build-status target: /path/to/target",
    },
    "git lifecycle": {
        "purpose": "Show read-only branch/commit/merge lifecycle evidence before Build Loop continuation.",
        "does": "Writes git_lifecycle_report.json/md under the HLDspec control sync dir and reports blockers.",
        "stops_at": "PASS/ACTION/BLOCKED lifecycle status with next safe action.",
        "will_not": "Create branches, commit, push, open PRs, merge, run SpecKit, or edit product code.",
        "example": "HLDspec git-lifecycle target: /path/to/target",
    },
    "target prompts": {
        "purpose": "Explain which generated prompts can be used from inside the target repo.",
        "does": "Points to target-side agent, mediator, slice, and bundle prompts after HLDspec has produced them.",
        "stops_at": "A list of prompt paths and the safe sentence to paste into a target-side agent.",
        "will_not": "Treat missing prompts as approval to improvise or execute product work without handoff.",
        "example": "Read prompts/agent/START_HLDSPEC_AGENT.md and follow it exactly. Report blockers, evidence, and next safe action.",
    },
}


def _normalise_help_topic(topic: str) -> str:
    text = " ".join(topic.lower().replace("-", " ").split())
    aliases = {
        "": "",
        "what next": "status",
        "next": "status",
        "state": "status",
        "build status": "status",
        "speckit state": "operator-state",
        "operator": "operator-state",
        "operator state": "operator-state",
        "check-hld": "check hld",
        "review hld": "check hld",
        "review-hld": "check hld",
        "build-loop": "build loop",
        "build loop status": "build loop",
        "git-lifecycle": "git lifecycle",
        "git lifecycle": "git lifecycle",
        "branch-gate": "git lifecycle",
        "branch gate": "git lifecycle",
        "commit-gate": "git lifecycle",
        "commit gate": "git lifecycle",
        "merge-gate": "git lifecycle",
        "merge gate": "git lifecycle",
        "prompts": "target prompts",
        "target prompt": "target prompts",
        "target prompts": "target prompts",
    }
    return aliases.get(text, text)


def _render_help_topic(name: str, item: dict[str, str]) -> str:
    return "\n".join(
        [
            f"# HLDspec Help: {name}",
            "",
            f"Purpose: {item['purpose']}",
            f"Does: {item['does']}",
            f"Stops at: {item['stops_at']}",
            f"Will not: {item['will_not']}",
            f"Example: `{item['example']}`",
            "",
        ]
    )


def command_help(args: argparse.Namespace) -> int:
    topic = _normalise_help_topic(" ".join(args.topic or []))
    if topic and topic in HELP_TOPICS:
        print(_render_help_topic(topic, HELP_TOPICS[topic]), end="")
        return 0
    if topic:
        print(f"Unknown HLDspec help topic: {topic}")
        print("")
    print("# HLDspec Help")
    print("")
    print("Use `status` first when you are unsure. It is the safest way to ask what should happen next.")
    print("")
    print("Most useful questions:")
    print("- `HLDspec status target: /path/to/target` — current state, blockers, open questions, next safe action.")
    print("- `HLDspec doctor target: /path/to/target` — why the target is not ready and what to fix.")
    print("- `HLDspec operator-state target: /path/to/target` — readiness/lifecycle safety for Build Loop or SpecKit work.")
    print("- `HLDspec review target: /path/to/target` — human-facing review files and checkpoint evidence.")
    print("- `HLDspec continue target: /path/to/target` — advance only if gates say it is safe.")
    print("")
    print("Start/resume examples:")
    print("- `HLDspec use HLD: /path/to/HLD.md target: /path/to/target`")
    print("- `HLDspec HLD: /path/to/HLD.md create /path/to/target runtime: claude`")
    print("")
    print("Help topics:")
    for name in sorted(HELP_TOPICS):
        print(f"- `HLDspec help {name}`")
    print("")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent-first HLDspec session facade.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("help", help="Show user-facing trigger help and status/next-action guidance.")
    p.add_argument("topic", nargs="*", help="Optional topic, e.g. status, doctor, check HLD, build loop, target prompts.")
    p.set_defaults(func=command_help)

    p = sub.add_parser("start", help="Prepare or resume an HLDspec agent session.")
    p.add_argument("--source", help="Source HLD path.")
    p.add_argument("--target", help="Target product workspace path.")
    p.add_argument("--request", help="Minimal agent request string, for example 'HLDspec HLD: /path/HLD.md create /path/target'.")
    p.add_argument("--agent", default="manual", choices=["manual", "devin", "claude", "codex"], help="Target agent.")
    p.add_argument("--mode", default="auto", choices=["auto", "create", "update", "upgrade", "adopt", "resume"], help="Intent override.")
    p.add_argument("--comment", default="", help="User intent/comment.")
    p.add_argument("--execute", action="store_true", help="Run the detected SpecKit init command instead of dry-run planning only.")
    p.add_argument(
        "--state-location",
        default="target",
        choices=["external", "target"],
        help="Store HLDspec controller/process artifacts in the target by default; use external to leave only .hldspec-run.json in the target.",
    )
    p.set_defaults(func=command_start)

    p = sub.add_parser("status", help="Show current HLDspec agent session status.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_status)

    p = sub.add_parser("review", help="Show human review files.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_review)

    p = sub.add_parser("continue", help="Run ProjectMachine to the next safe checkpoint.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_continue)

    p = sub.add_parser("diff", help="Compare source hash to recorded session hash.")
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_diff)

    p = sub.add_parser("doctor", help="Check agent-first docs and target session files.")
    p.add_argument("--target", default=None)
    p.set_defaults(func=command_doctor)

    p = sub.add_parser("speckit-doctor", help="Check target-level SpecKit readiness.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_speckit_doctor)

    p = sub.add_parser("operator-state", aliases=["speckit-state"], help="Check target-level SpecKit Operator State.")
    p.add_argument("--target", default=None)
    p.set_defaults(func=command_operator_state)

    p = sub.add_parser("git-lifecycle", help="Write/read the read-only Git lifecycle gate report.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_git_lifecycle)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
