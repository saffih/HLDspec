"""SpecKit Operator State reporting.

Operator State first gates the readiness boundary, then, when the target is ready
for SpecKit, composes existing execution-state evidence into a lifecycle state and
next safe action.
"""
from __future__ import annotations

import subprocess
import json
from pathlib import Path
from typing import Any, Callable

from . import speckit_execution_state as ses
from . import speckit_readiness as sr
from .source_freshness import load_source_freshness

SCHEMA_VERSION = 1

STATE_NO_TARGET = "NO_TARGET"
STATE_TARGET_MISSING = "TARGET_MISSING"
STATE_TARGET_NOT_GIT = "TARGET_NOT_GIT"
STATE_TARGET_DIRTY = "TARGET_DIRTY"
STATE_SOURCE_PACKAGE_MISSING = "SOURCE_PACKAGE_MISSING"
STATE_SPECKIT_NOT_INITIALIZED = "SPECKIT_NOT_INITIALIZED"
STATE_BRANCH_POLICY_MISSING = "BRANCH_POLICY_MISSING"
STATE_SOURCE_FRESHNESS_BLOCKED = "SOURCE_FRESHNESS_BLOCKED"
STATE_REASSESSMENT_REQUIRED = "REASSESSMENT_REQUIRED"
STATE_READY_FOR_SPECIFY = "READY_FOR_SPECIFY"
STATE_SPECIFY_ACTIVE = "SPECIFY_ACTIVE"
STATE_PLAN_ACTIVE = "PLAN_ACTIVE"
STATE_TASKS_ACTIVE = "TASKS_ACTIVE"
STATE_ANALYZE_READY = "ANALYZE_READY"
STATE_BLOCKED = "BLOCKED"

PROJECT_BLOCKING_STAGES = {
    "NO_WORKSPACE",
    "HLD_READY",
    "HLD_READY_WITH_ACTIONS",
    "HLD_BLOCKED",
    "HLD_READINESS_HLD_MISSING",
    "SOURCE_FRESHNESS_BLOCKED",
    "INIT_PREREQS_BLOCKED",
    "BUILD_LOOP_INIT_BLOCKED",
    "SPECKIT_APPROVAL_GATE_BLOCKED",
    "CONVERSION_CHECKPOINT",
    "CONVERSION_READY_TO_APPLY",
    "FIRST_RUN_PENDING",
    "SPEC_BUILD_PLAN_CHECKPOINT",
    "SPEC_BUILD_PLAN_BLOCKED",
    "SPECKIT_PREWORK_MISSING",
    "SPECKIT_PREWORK_REWORK_REQUIRED",
    "SPECKIT_PREWORK_APPROVAL_GATE",
}
PROJECT_NON_BLOCKING_STAGES = {
    "AGENT_SESSION_PREPARED",
    "INIT_PREREQS_READY",
    "WORKSPACE_INITIALIZED",
    "MIRROR_SYNCED",
    STATE_READY_FOR_SPECIFY,
    STATE_SPECIFY_ACTIVE,
    STATE_PLAN_ACTIVE,
    STATE_TASKS_ACTIVE,
    STATE_ANALYZE_READY,
}


def _next_action_or_default(readiness: dict[str, Any]) -> str:
    next_actions = readiness.get("next_actions") or []
    if next_actions:
        first = next_actions[0]
        if isinstance(first, str) and first.strip():
            return first
    return "Proceed with /speckit.specify after the approved branch workflow is satisfied."


def _list_command_labels(report: dict[str, Any]) -> list[str]:
    labels: list[str] = []
    for item in report.get("available_init_commands") or []:
        if isinstance(item, dict):
            label = item.get("label")
            if label:
                labels.append(str(label))
    return labels


def _has_any_spec_artifact(execution: dict[str, Any]) -> bool:
    for bundle in execution.get("bundles") or []:
        if not isinstance(bundle, dict):
            continue
        for spec in bundle.get("specs") or []:
            if not isinstance(spec, dict):
                continue
            if any(value == "DONE" for value in (spec.get("phases") or {}).values()):
                return True
    return False


def _specs_tree_has_files(specs_root: Path) -> bool:
    try:
        return specs_root.is_dir() and any(path.is_file() for path in specs_root.rglob("*"))
    except OSError:
        return False


def _source_freshness_gate(target: Path) -> dict[str, Any]:
    return load_source_freshness(target)


def _project_checkpoint_gate(target: Path) -> dict[str, Any] | None:
    state_path = target / ".hldspec" / "sync" / "hldspec_state.json"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(state, dict):
        return None
    stage = str(state.get("current_stage") or state.get("stage") or "").strip()
    checkpoint = str(state.get("current_checkpoint") or state.get("checkpoint") or "").strip()
    if not stage:
        return None
    stage_upper = stage.upper()
    has_blocking_details = bool(state.get("blocking_questions") or state.get("stale_artifact_warnings"))
    if stage_upper in {"HLD_READY", "HLD_READY_WITH_ACTIONS"}:
        return {
            "path": str(state_path),
            "stage": stage,
            "checkpoint": checkpoint,
            "blockers": [
                f"check HLD completed with {stage}; this is only an HLD readiness review, not full SpecKit Preparation approval."
            ],
            "next_safe_action": "Continue HLDspec SpecKit Preparation or Build Loop prework before starting SpecKit.",
        }
    if stage_upper in PROJECT_NON_BLOCKING_STAGES and not has_blocking_details:
        return None
    if stage_upper not in PROJECT_BLOCKING_STAGES and not has_blocking_details:
        return {
            "path": str(state_path),
            "stage": stage,
            "checkpoint": checkpoint,
            "blockers": [f"Unrecognized Project checkpoint state requires reassessment: {stage}" + (f" / {checkpoint}" if checkpoint else "")],
            "next_safe_action": "Reassess the ProjectMachine checkpoint classification before continuing.",
        }
    next_actions = [str(item) for item in state.get("next_allowed_actions", []) if str(item).strip()]
    blockers = [f"Project checkpoint blocks readiness: {stage}" + (f" / {checkpoint}" if checkpoint else "")]
    for item in state.get("stale_artifact_warnings", []) or []:
        if str(item).strip():
            blockers.append(str(item))
    for item in state.get("blocking_questions", []) or []:
        if isinstance(item, dict):
            artifact = item.get("artifact") or item.get("question_id") or checkpoint or state_path
            count = item.get("open_question_count")
            blockers.append(f"Open checkpoint question: {artifact}" + (f" ({count})" if count is not None else ""))
        elif str(item).strip():
            blockers.append(str(item))
    return {
        "path": str(state_path),
        "stage": stage,
        "checkpoint": checkpoint,
        "blockers": blockers,
        "next_safe_action": next_actions[0] if next_actions else "Resolve the blocked ProjectMachine checkpoint, then rerun operator-state.",
    }


def _lifecycle_state_from_execution(target: Path) -> dict[str, Any]:
    specs_root = target / "specs"
    execution = ses.build_execution_state(target, specs_root)
    action = ses.next_action(execution)
    execution_status = str(execution.get("status", "UNKNOWN"))
    evidence = [
        {"fact": "speckit_lifecycle_status", "value": execution_status},
        {"fact": "speckit_specs_root", "value": str(specs_root)},
        {"fact": "speckit_specs_root_exists", "value": specs_root.is_dir()},
        {"fact": "speckit_bundle_count", "value": execution.get("bundle_count", 0)},
        {"fact": "speckit_resume", "value": execution.get("resume")},
    ]

    def out(state: str, status: str, next_safe_action: str, blockers: list[str] | None = None) -> dict[str, Any]:
        return {
            "status": status,
            "state": state,
            "next_safe_action": next_safe_action,
            "blockers": blockers or [],
            "evidence": evidence,
            "execution_state": execution,
            "next_action": action,
        }

    if execution_status == "UNKNOWN":
        return out(
            STATE_READY_FOR_SPECIFY,
            "PASS",
            "Start /speckit.specify from the approved Run Card after readiness and approval gates remain PASS.",
        )

    if execution_status == "NO_BUNDLES":
        if _specs_tree_has_files(specs_root):
            return out(
                STATE_REASSESSMENT_REQUIRED,
                "ACTION",
                "Rebuild HLDspec Run Cards or reassess; SpecKit artifacts exist but no bundle or invocation queue maps them to HLDspec scope.",
                ["SpecKit artifacts exist without a HLDspec bundle/invocation queue."],
            )
        return out(
            STATE_READY_FOR_SPECIFY,
            "PASS",
            "Generate the Run Card or invocation queue, then start /speckit.specify after gates remain PASS.",
        )

    if execution_status == "ALL_TASKS_DONE":
        return out(
            STATE_ANALYZE_READY,
            "PASS",
            "Run /speckit.analyze, resolve any findings, then require explicit implementation-slice approval before code changes.",
        )

    if execution_status == "IN_PROGRESS":
        resume = execution.get("resume") if isinstance(execution.get("resume"), dict) else {}
        phase = str(resume.get("phase") or "specify").lower()
        has_artifact = _has_any_spec_artifact(execution)
        if phase == "specify" and not has_artifact:
            return out(
                STATE_READY_FOR_SPECIFY,
                "PASS",
                "Start /speckit.specify from the approved Run Card after readiness and approval gates remain PASS.",
            )
        phase_state = {
            "specify": STATE_SPECIFY_ACTIVE,
            "plan": STATE_PLAN_ACTIVE,
            "tasks": STATE_TASKS_ACTIVE,
        }.get(phase, STATE_REASSESSMENT_REQUIRED)
        next_safe = str(action.get("instruction") or action.get("headline") or "Resume the next SpecKit phase from the current Run Card.")
        return out(phase_state, "PASS", next_safe)

    return out(
        STATE_REASSESSMENT_REQUIRED,
        "ACTION",
        "Reassess with HLDspec; lifecycle state could not be mapped to a safe next action.",
        [f"Unrecognized SpecKit lifecycle status: {execution_status}"],
    )


def build_speckit_operator_state_report(
    target: Path | str | None,
    *,
    which: Callable[[str], str | None] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    readiness_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doctor_note = (
        "SpecKit Doctor is readiness/preflight only; Operator State uses those facts "
        "before composing post-readiness lifecycle evidence."
    )

    if target is None:
        blockers = ["No target path was provided."]
        evidence = [{"fact": "target_path", "value": None}]
        return {
            "schema_version": SCHEMA_VERSION,
            "target": None,
            "status": "ACTION",
            "state": STATE_NO_TARGET,
            "next_safe_action": "Choose or create a target workspace path, then rerun operator-state.",
            "blockers": blockers,
            "evidence": evidence,
            "source_facts_used": {
                "target_path": None,
                "readiness_report": None,
            },
            "doctor_note": doctor_note,
        }

    target_path = Path(target).expanduser().resolve()
    if not target_path.exists():
        blockers = [f"Target path does not exist: {target_path}"]
        evidence = [{"fact": "target_path_exists", "value": False}]
        return {
            "schema_version": SCHEMA_VERSION,
            "target": str(target_path),
            "status": "ACTION",
            "state": STATE_TARGET_MISSING,
            "next_safe_action": "Create or choose the target workspace path, then rerun operator-state.",
            "blockers": blockers,
            "evidence": evidence,
            "source_facts_used": {
                "target_path": str(target_path),
                "target_exists": False,
                "readiness_report": None,
            },
            "doctor_note": doctor_note,
        }

    readiness = readiness_report or sr.build_speckit_readiness_report(target_path, which=which, run=run)
    workspace = readiness.get("workspace_status") if isinstance(readiness.get("workspace_status"), dict) else {}
    branch_hook = readiness.get("branch_hook_status") if isinstance(readiness.get("branch_hook_status"), dict) else {}
    selected_init_command = readiness.get("selected_init_command")
    available_init_commands = readiness.get("available_init_commands") or []
    source_package_dir = target_path / ".hldspec" / "source_package"
    source_package_exists = source_package_dir.is_dir()
    git_root = readiness.get("git_root")
    git_branch = readiness.get("git_branch")
    dirty_tree = readiness.get("dirty_tree")
    freshness = _source_freshness_gate(target_path)
    project_checkpoint = _project_checkpoint_gate(target_path)

    evidence: list[dict[str, Any]] = [
        {"fact": "target_path", "value": str(target_path)},
        {"fact": "git_root", "value": git_root},
        {"fact": "git_branch", "value": git_branch},
        {"fact": "dirty_tree", "value": dirty_tree},
        {"fact": "source_package_exists", "value": source_package_exists},
        {"fact": "specify_dir_exists", "value": workspace.get("specify_dir_exists")},
        {"fact": "memory_dir_exists", "value": workspace.get("memory_dir_exists")},
        {"fact": "source_mirror_exists", "value": workspace.get("source_mirror_exists")},
        {"fact": "branch_policy_status", "value": branch_hook.get("status")},
        {"fact": "readiness_status", "value": readiness.get("status")},
        {"fact": "selected_init_command", "value": selected_init_command},
        {"fact": "available_init_commands", "value": available_init_commands},
        {"fact": "available_init_command_labels", "value": _list_command_labels(readiness)},
        {"fact": "source_freshness_state", "value": freshness.get("state")},
        {"fact": "source_freshness_path", "value": freshness.get("path")},
        {"fact": "project_checkpoint_stage", "value": project_checkpoint.get("stage") if project_checkpoint else None},
        {"fact": "project_checkpoint_path", "value": project_checkpoint.get("path") if project_checkpoint else None},
    ]

    blockers: list[str] = []
    status = "PASS"
    state = STATE_READY_FOR_SPECIFY
    next_safe_action = _next_action_or_default(readiness)

    if readiness.get("status") == "CONFLICT":
        status = "CONFLICT"
        state = STATE_BLOCKED
        blockers.append("SpecKit readiness reported CONFLICT.")
        next_safe_action = "Resolve conflicting readiness evidence, then rerun operator-state."
    elif freshness.get("blocking"):
        status = "ACTION"
        state = STATE_SOURCE_FRESHNESS_BLOCKED
        blockers.extend(str(item) for item in freshness.get("warnings", []) if str(item).strip())
        next_safe_action = "Reconcile source freshness before rerunning operator-state or starting Build Loop work."
    elif project_checkpoint is not None:
        status = "ACTION"
        state = STATE_BLOCKED
        blockers.extend(project_checkpoint["blockers"])
        next_safe_action = str(project_checkpoint["next_safe_action"])
    elif git_root is None:
        status = "ACTION"
        state = STATE_TARGET_NOT_GIT
        blockers.append("No git repository was detected for the target.")
        next_safe_action = "Initialize or point HLDspec at a git workspace before rerunning operator-state."
    elif dirty_tree is True:
        status = "ACTION"
        state = STATE_TARGET_DIRTY
        blockers.append("Git tree has uncommitted changes.")
        next_safe_action = "Clean, commit, or stash the target tree before rerunning operator-state."
    elif dirty_tree is None:
        status = "ACTION"
        state = STATE_REASSESSMENT_REQUIRED
        blockers.append("Git dirty-tree status could not be determined.")
        next_safe_action = "Rerun operator-state after verifying git access."
    elif not source_package_exists:
        status = "ACTION"
        state = STATE_SOURCE_PACKAGE_MISSING
        blockers.append("Missing .hldspec/source_package/")
        next_safe_action = "Run hldspec start or source-package generation before rerunning operator-state."
    elif not workspace.get("specify_dir_exists") or not workspace.get("memory_dir_exists"):
        status = "ACTION"
        state = STATE_SPECKIT_NOT_INITIALIZED
        blockers.append("Real SpecKit workspace is not initialized.")
        next_safe_action = "Run a real SpecKit init command to create `.specify/memory/` before rerunning operator-state."
    elif branch_hook.get("status") != "PASS":
        branch_status = str(branch_hook.get("status", "ACTION")).upper()
        status = "CONFLICT" if branch_status == "CONFLICT" else "ACTION"
        state = STATE_BRANCH_POLICY_MISSING
        details = str(branch_hook.get("details") or "Branch policy is not ready.")
        blockers.append(details)
        next_safe_action = str(branch_hook.get("next_action") or "Create or switch to the approved feature branch before rerunning operator-state.")
    elif readiness.get("status") != "PASS":
        status = "ACTION"
        state = STATE_REASSESSMENT_REQUIRED
        blockers.extend(str(action) for action in (readiness.get("next_actions") or []) if str(action).strip())
        next_safe_action = _next_action_or_default(readiness)
    else:
        selected_label = (
            str(selected_init_command.get("label"))
            if isinstance(selected_init_command, dict) and selected_init_command.get("label")
            else None
        )
        evidence.append({"fact": "selected_init_command_label", "value": selected_label})
        if selected_label not in {"specify", "spec-kit", "uvx-spec-kit"}:
            status = "ACTION"
            state = STATE_REASSESSMENT_REQUIRED
            blockers.append("Selected SpecKit init command is not one of the supported labels.")
            next_safe_action = "Select a supported SpecKit init command and rerun operator-state."

    lifecycle: dict[str, Any] | None = None
    if status == "PASS" and state == STATE_READY_FOR_SPECIFY:
        lifecycle = _lifecycle_state_from_execution(target_path)
        evidence.extend(lifecycle.get("evidence", []))
        lifecycle_state = str(lifecycle.get("state") or STATE_READY_FOR_SPECIFY)
        if lifecycle_state != STATE_READY_FOR_SPECIFY:
            status = str(lifecycle.get("status") or status)
            state = lifecycle_state
            next_safe_action = str(lifecycle.get("next_safe_action") or next_safe_action)
            blockers.extend(str(item) for item in lifecycle.get("blockers", []) if str(item).strip())

    return {
        "schema_version": SCHEMA_VERSION,
        "target": str(target_path),
        "status": status,
        "state": state,
        "lifecycle_status": lifecycle.get("status") if isinstance(lifecycle, dict) else None,
        "lifecycle_state": lifecycle.get("state") if isinstance(lifecycle, dict) else None,
        "lifecycle_next_safe_action": lifecycle.get("next_safe_action") if isinstance(lifecycle, dict) else None,
        "next_safe_action": next_safe_action,
        "blockers": blockers,
        "evidence": evidence,
        "source_facts_used": {
            "readiness_status": readiness.get("status"),
            "workspace_status": workspace,
            "branch_hook_status": branch_hook,
            "selected_init_command": selected_init_command,
            "selected_init_command_label": selected_init_command.get("label") if isinstance(selected_init_command, dict) else None,
            "available_init_commands": available_init_commands,
            "available_init_command_labels": _list_command_labels(readiness),
            "git_root": git_root,
            "git_branch": git_branch,
            "dirty_tree": dirty_tree,
            "source_package_exists": source_package_exists,
            "source_freshness": freshness,
        },
        "doctor_note": doctor_note,
        "readiness_report": readiness,
        "speckit_execution_state": lifecycle.get("execution_state") if isinstance(lifecycle, dict) else None,
        "speckit_next_action": lifecycle.get("next_action") if isinstance(lifecycle, dict) else None,
    }


def summarize_speckit_operator_state(report: dict[str, Any]) -> str:
    source_facts_used = report.get("source_facts_used") or {}
    lines = [
        "# SpecKit Operator State",
        "",
        f"STATUS: {report.get('status', 'ACTION')}",
        f"State: {report.get('state', 'UNKNOWN')}",
        f"Target: {report.get('target', 'none')}",
        f"Next safe action: {report.get('next_safe_action', 'none')}",
        "",
        "Boundary:",
        "- SpecKit Doctor is readiness/preflight only; Operator State uses those facts first, then adds lifecycle evidence when readiness is PASS.",
        "",
        "Blockers:",
    ]
    blockers = report.get("blockers") or []
    if blockers:
        for item in blockers:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "Evidence:",
        ]
    )
    evidence = report.get("evidence") or []
    if evidence:
        for item in evidence:
            fact = item.get("fact", "fact") if isinstance(item, dict) else "fact"
            value = item.get("value") if isinstance(item, dict) else item
            lines.append(f"- {fact}: {value}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "Source facts used:",
        ]
    )
    if isinstance(source_facts_used, dict) and source_facts_used:
        for key, value in source_facts_used.items():
            lines.append(f"- {key}: {value}")
    else:
        lines.append("- none")
    lifecycle_state = report.get("lifecycle_state")
    if lifecycle_state:
        lines.extend(
            [
                "",
                "Lifecycle:",
                f"- lifecycle status: {report.get('lifecycle_status', 'UNKNOWN')}",
                f"- lifecycle state: {lifecycle_state}",
                f"- lifecycle next safe action: {report.get('lifecycle_next_safe_action', 'none')}",
            ]
        )
    doctor_note = report.get("doctor_note")
    if doctor_note:
        lines.extend(["", doctor_note, ""])
    else:
        lines.append("")
    return "\n".join(lines)
