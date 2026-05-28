"""SpecKit Operator State reporting.

This is the first Operator State layer: it turns existing HLDspec readiness facts
into a narrow readiness-boundary state and next safe action. It does not model the
full SpecKit lifecycle.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Callable

from . import speckit_readiness as sr

SCHEMA_VERSION = 1

STATE_NO_TARGET = "NO_TARGET"
STATE_TARGET_MISSING = "TARGET_MISSING"
STATE_TARGET_NOT_GIT = "TARGET_NOT_GIT"
STATE_TARGET_DIRTY = "TARGET_DIRTY"
STATE_SOURCE_PACKAGE_MISSING = "SOURCE_PACKAGE_MISSING"
STATE_SPECKIT_NOT_INITIALIZED = "SPECKIT_NOT_INITIALIZED"
STATE_BRANCH_POLICY_MISSING = "BRANCH_POLICY_MISSING"
STATE_REASSESSMENT_REQUIRED = "REASSESSMENT_REQUIRED"
STATE_READY_FOR_SPECIFY = "READY_FOR_SPECIFY"
STATE_BLOCKED = "BLOCKED"


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


def build_speckit_operator_state_report(
    target: Path | str | None,
    *,
    which: Callable[[str], str | None] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    readiness_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doctor_note = (
        "SpecKit Doctor is readiness/preflight only; Operator State uses those facts "
        "to decide the next safe action for the readiness boundary."
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

    return {
        "schema_version": SCHEMA_VERSION,
        "target": str(target_path),
        "status": status,
        "state": state,
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
        },
        "doctor_note": doctor_note,
        "readiness_report": readiness,
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
        "- SpecKit Doctor is readiness/preflight only; Operator State uses those facts to choose the next safe action.",
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
    doctor_note = report.get("doctor_note")
    if doctor_note:
        lines.extend(["", doctor_note, ""])
    else:
        lines.append("")
    return "\n".join(lines)
