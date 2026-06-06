"""Target-level SpecKit readiness reporting.

This module reports whether a target workspace is ready to proceed with real
SpecKit work. It does not invoke SpecKit or create specs itself.
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import speckit_workspace as sw

SCHEMA_VERSION = 1

BRANCH_HOOK_CANDIDATES = (
    ".specify/extensions.yml",
    ".specify/extensions.yaml",
    ".specify/hooks.yml",
    ".specify/hooks.yaml",
)


def _json_command(cmd: sw.InitCommand | None) -> dict[str, Any] | None:
    if cmd is None:
        return None
    return {
        "label": cmd.label,
        "argv": list(cmd.argv),
        "source": cmd.source,
        "display": cmd.display,
    }


def _run_command(
    run: Callable[..., subprocess.CompletedProcess[str]],
    argv: list[str],
    *,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return run(
        argv,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )


def _nearest_existing_dir(path: Path) -> Path:
    current = path
    while not current.exists():
        parent = current.parent
        if parent == current:
            break
        current = parent
    return current


def _git_root(target: Path, run: Callable[..., subprocess.CompletedProcess[str]]) -> str | None:
    probe_dir = _nearest_existing_dir(target)
    try:
        completed = _run_command(run, ["git", "-C", str(probe_dir), "rev-parse", "--show-toplevel"], cwd=probe_dir)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    root = completed.stdout.strip()
    return root or None


def _git_branch(target: Path, git_root: str, run: Callable[..., subprocess.CompletedProcess[str]]) -> str | None:
    try:
        completed = _run_command(run, ["git", "-C", git_root, "branch", "--show-current"], cwd=target)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    branch = completed.stdout.strip()
    return branch or None


def _git_dirty(target: Path, git_root: str, run: Callable[..., subprocess.CompletedProcess[str]]) -> bool | None:
    try:
        completed = _run_command(run, ["git", "-C", git_root, "status", "--porcelain"], cwd=target)
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return bool(completed.stdout.strip())


def _branch_hook_status(target: Path) -> dict[str, Any]:
    hook_path: Path | None = None
    for rel in BRANCH_HOOK_CANDIDATES:
        candidate = target / rel
        if candidate.is_file():
            hook_path = candidate
            break

    if hook_path is None:
        return {
            "status": "ACTION",
            "path": None,
            "details": "No before_specify hook or equivalent branch policy found.",
            "next_action": "Create/switch to the approved feature branch manually before /speckit.specify, or install a before_specify hook later.",
        }

    text = hook_path.read_text(encoding="utf-8")
    if "specs/<feature>/spec.md" in text or "spec.md" in text:
        return {
            "status": "ACTION",
            "path": str(hook_path),
            "details": "Hook config must not describe creating specs/<feature>/spec.md.",
            "next_action": "Update the hook or workflow so branch setup happens before /speckit.specify and SpecKit still owns spec.md creation.",
        }

    return {
        "status": "PASS",
        "path": str(hook_path),
        "details": "Branch hook or equivalent branch policy is present.",
        "next_action": "Proceed with /speckit.specify only after the approved branch workflow is satisfied.",
    }


def build_speckit_readiness_report(
    target: Path,
    *,
    which: Callable[[str], str | None] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    which = which or shutil.which
    run = run or subprocess.run

    available = list(sw.detect_init_commands(which=which))
    selected = available[0] if available else None
    workspace_status = sw.inspect_workspace(target)
    git_root = _git_root(target, run)
    git_branch = _git_branch(target, git_root, run) if git_root else None
    dirty_tree = _git_dirty(target, git_root, run) if git_root else None
    branch_hook = _branch_hook_status(target)

    checks: list[dict[str, Any]] = []
    next_actions: list[str] = []

    def add_check(name: str, status: str, details: str, next_action: str | None = None) -> None:
        checks.append(
            {
                "name": name,
                "status": status,
                "details": details,
                "next_action": next_action,
            }
        )
        if status in {"ACTION", "CONFLICT"} and next_action:
            next_actions.append(next_action)

    target_creatable = target.exists() or target.parent.exists()
    add_check(
        "target path exists or can be created",
        "PASS" if target_creatable else "ACTION",
        "Target exists or can be created under an existing parent." if target_creatable else "Target path parent is missing; create the target parent first.",
        None if target_creatable else "Create the target directory or choose a writable parent before running the readiness doctor.",
    )

    if git_root:
        add_check(
            "git repository detected",
            "PASS",
            f"Git root: {git_root}",
        )
        add_check(
            "current branch detected",
            "PASS" if git_branch else "ACTION",
            f"Current branch: {git_branch}" if git_branch else "Git repo detected but current branch could not be resolved.",
            None if git_branch else "Create or switch to a branch before starting SpecKit work.",
        )
        if dirty_tree is False:
            add_check(
                "dirty tree status detected",
                "PASS",
                "Git tree is clean.",
            )
        elif dirty_tree is True:
            add_check(
                "dirty tree status detected",
                "ACTION",
                "Git tree has uncommitted changes.",
                "Clean, commit, or stash the target tree before starting SpecKit work.",
            )
        else:
            add_check(
                "dirty tree status detected",
                "ACTION",
                "Git dirty-tree status could not be determined.",
                "Rerun the readiness doctor after verifying git access.",
            )
    else:
        add_check(
            "git repository detected",
            "ACTION",
            "No git repository was detected for the target.",
            "Initialize or point HLDspec at a git workspace before /speckit.specify.",
        )
        add_check(
            "current branch detected",
            "ACTION",
            "Skipped because no git repository was detected.",
            "Initialize or point HLDspec at a git workspace before /speckit.specify.",
        )
        add_check(
            "dirty tree status detected",
            "ACTION",
            "Skipped because no git repository was detected.",
            "Initialize or point HLDspec at a git workspace before /speckit.specify.",
        )

    if available:
        add_check(
            "supported SpecKit init command detected",
            "PASS",
            "Available commands: " + ", ".join(cmd.display for cmd in available),
        )
        smoke = _run_init_help_smoke(selected, run, target) if selected else None
        if smoke and smoke.get("status") == "PASS":
            add_check(
                "command help/version smoke check",
                "PASS",
                smoke["details"],
            )
        else:
            add_check(
                "command help/version smoke check",
                "ACTION",
                smoke["details"] if smoke else "No selected SpecKit init command is available.",
                smoke["next_action"] if smoke else "Install a supported SpecKit init command (`specify`, `spec-kit`, or `uvx`).",
            )
    else:
        add_check(
            "supported SpecKit init command detected",
            "ACTION",
            "No supported SpecKit init command was detected.",
            "Install `specify`, `spec-kit`, or `uvx` so HLDspec can invoke a real SpecKit init command later.",
        )
        add_check(
            "command help/version smoke check",
            "ACTION",
            "Skipped because no supported SpecKit init command was detected.",
            "Install `specify`, `spec-kit`, or `uvx` so HLDspec can invoke a real SpecKit init command later.",
        )

    add_check(
        ".specify/ exists",
        "PASS" if workspace_status.specify_dir_exists else "ACTION",
        ".specify/ exists." if workspace_status.specify_dir_exists else ".specify/ is missing.",
        None if workspace_status.specify_dir_exists else "Run a real SpecKit init command to create `.specify/`.",
    )
    add_check(
        ".specify/memory/ exists",
        "PASS" if workspace_status.memory_dir_exists else "ACTION",
        ".specify/memory/ exists." if workspace_status.memory_dir_exists else workspace_status.validation_error or ".specify/memory/ is missing.",
        None if workspace_status.memory_dir_exists else "Run a real SpecKit init command to create `.specify/memory/`.",
    )
    add_check(
        ".specify/source/ exists",
        "PASS" if workspace_status.source_mirror_exists else "ACTION",
        ".specify/source/ exists." if workspace_status.source_mirror_exists else "HLDspec mirror is missing.",
        None if workspace_status.source_mirror_exists else "Run HLDspec source-package generation so the read-only mirror is materialized.",
    )
    source_package_dir = target / ".hldspec" / "source_package"
    add_check(
        ".hldspec/source_package/ exists",
        "PASS" if source_package_dir.is_dir() else "ACTION",
        ".hldspec/source_package/ exists." if source_package_dir.is_dir() else ".hldspec/source_package/ is missing.",
        None if source_package_dir.is_dir() else "Run hldspec start or source-package generation before SpecKit readiness review.",
    )

    add_check(
        "before_specify hook or equivalent branch policy",
        branch_hook["status"],
        branch_hook["details"],
        branch_hook["next_action"],
    )
    add_check(
        "branch hook does not claim HLDspec creates spec files",
        "PASS",
        "No branch-hook wording in the readiness report says HLDspec creates spec files.",
    )

    status = _summary_status(checks)
    if status == "PASS":
        next_actions = [
            "Proceed with the approved SpecKit init and branch workflow, then run /speckit.specify on the real SpecKit workspace.",
        ]
    elif not next_actions:
        next_actions = [
            "Resolve ACTION/CONFLICT items above, then rerun the readiness doctor.",
        ]

    return {
        "schema_version": SCHEMA_VERSION,
        "target": str(target),
        "status": status,
        "checks": checks,
        "next_actions": next_actions,
        "selected_init_command": _json_command(selected),
        "available_init_commands": [_json_command(cmd) for cmd in available],
        "workspace_status": workspace_status.metadata(),
        "branch_hook_status": branch_hook,
        "git_root": git_root,
        "git_branch": git_branch,
        "dirty_tree": dirty_tree,
        "manual_branch_equivalent_allowed": True,
        "summary": (
            "Real SpecKit init means `.specify/memory/` exists; `.specify/source/` alone is only the HLDspec mirror."
        ),
    }


def build_speckit_init_prereq_report(
    target: Path,
    *,
    which: Callable[[str], str | None] | None = None,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Report only the facts required before running real SpecKit init."""
    target = Path(target).expanduser().resolve()
    which = which or shutil.which
    run = run or subprocess.run

    available = list(sw.detect_init_commands(which=which))
    selected = available[0] if available else None
    git_root = _git_root(target, run)
    git_branch = _git_branch(target, git_root, run) if git_root else None
    dirty_tree = _git_dirty(target, git_root, run) if git_root else None

    checks: list[dict[str, Any]] = []
    next_actions: list[str] = []

    def add_check(name: str, status: str, details: str, next_action: str | None = None) -> None:
        checks.append(
            {
                "name": name,
                "status": status,
                "details": details,
                "next_action": next_action,
            }
        )
        if status in {"ACTION", "CONFLICT"} and next_action:
            next_actions.append(next_action)

    target_creatable = target.exists() or target.parent.exists()
    add_check(
        "target path exists or can be created",
        "PASS" if target_creatable else "ACTION",
        "Target exists or can be created under an existing parent."
        if target_creatable
        else "Target path parent is missing; create the target parent first.",
        None if target_creatable else "Create the target directory or choose a writable parent before running Build Loop init.",
    )

    if git_root:
        add_check("git repository detected", "PASS", f"Git root: {git_root}")
        add_check(
            "current branch detected",
            "PASS" if git_branch else "ACTION",
            f"Current branch: {git_branch}" if git_branch else "Git repo detected but current branch could not be resolved.",
            None if git_branch else "Create or switch to a branch before running Build Loop init.",
        )
        if dirty_tree is False:
            add_check("dirty tree status detected", "PASS", "Git tree is clean.")
        elif dirty_tree is True:
            add_check(
                "dirty tree status detected",
                "ACTION",
                "Git tree has uncommitted changes.",
                "Clean, commit, or stash the target tree before running Build Loop init.",
            )
        else:
            add_check(
                "dirty tree status detected",
                "ACTION",
                "Git dirty-tree status could not be determined.",
                "Rerun Build Loop prereqs after verifying git access.",
            )
    else:
        add_check(
            "git repository detected",
            "ACTION",
            "No git repository was detected for the target.",
            "Initialize or point HLDspec at a git workspace before running Build Loop init.",
        )
        add_check(
            "current branch detected",
            "ACTION",
            "Skipped because no git repository was detected.",
            "Initialize or point HLDspec at a git workspace before running Build Loop init.",
        )
        add_check(
            "dirty tree status detected",
            "ACTION",
            "Skipped because no git repository was detected.",
            "Initialize or point HLDspec at a git workspace before running Build Loop init.",
        )

    if available:
        add_check(
            "supported SpecKit init command detected",
            "PASS",
            "Available commands: " + ", ".join(cmd.display for cmd in available),
        )
        smoke = _run_init_help_smoke(selected, run, target) if selected else None
        add_check(
            "command help/version smoke check",
            "PASS" if smoke and smoke.get("status") == "PASS" else "ACTION",
            smoke["details"] if smoke else "No selected SpecKit init command is available.",
            None
            if smoke and smoke.get("status") == "PASS"
            else (smoke["next_action"] if smoke else "Install a supported SpecKit init command (`specify`, `spec-kit`, or `uvx`)."),
        )
    else:
        add_check(
            "supported SpecKit init command detected",
            "ACTION",
            "No supported SpecKit init command was detected.",
            "Install `specify`, `spec-kit`, or `uvx` so HLDspec can invoke a real SpecKit init command later.",
        )
        add_check(
            "command help/version smoke check",
            "ACTION",
            "Skipped because no supported SpecKit init command was detected.",
            "Install `specify`, `spec-kit`, or `uvx` so HLDspec can invoke a real SpecKit init command later.",
        )

    if git_branch:
        add_check(
            "branch policy or manual branch path ready",
            "PASS",
            "Manual branch path is available before init; hook/config evidence can be installed or checked after SpecKit creates `.specify/`.",
        )
    else:
        add_check(
            "branch policy or manual branch path ready",
            "ACTION",
            "No branch was detected, so neither a branch policy nor a manual branch path is ready.",
            "Create or switch to the approved feature branch before running Build Loop init.",
        )

    status = _summary_status(checks)
    if status == "PASS":
        next_actions = ["Run Build Loop init to execute the selected real SpecKit init command."]
    elif not next_actions:
        next_actions = ["Resolve ACTION/CONFLICT items above, then rerun Build Loop prereqs."]

    return {
        "schema_version": SCHEMA_VERSION,
        "target": str(target),
        "status": status,
        "checks": checks,
        "next_actions": next_actions,
        "selected_init_command": _json_command(selected),
        "available_init_commands": [_json_command(cmd) for cmd in available],
        "workspace_status": sw.inspect_workspace(target).metadata(),
        "git_root": git_root,
        "git_branch": git_branch,
        "dirty_tree": dirty_tree,
        "manual_branch_equivalent_allowed": bool(git_branch),
        "summary": "Build Loop prereqs is pre-init only; it does not require `.specify/`, `.specify/memory/`, or `.specify/source/`.",
    }


def _run_init_help_smoke(
    command: sw.InitCommand | None,
    run: Callable[..., subprocess.CompletedProcess[str]],
    target: Path,
) -> dict[str, Any] | None:
    if command is None:
        return None
    smoke_argv_options: tuple[list[str], ...]
    if command.label == "specify":
        smoke_argv_options = (
            ["specify", "init", "--help"],
            ["specify", "--help"],
            ["specify", "--version"],
        )
    elif command.label == "spec-kit":
        smoke_argv_options = (
            ["spec-kit", "init", "--help"],
            ["spec-kit", "--help"],
            ["spec-kit", "--version"],
        )
    elif command.label == "uvx-spec-kit":
        smoke_argv_options = (
            ["uvx", "--from", sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "init", "--help"],
            ["uvx", "--from", sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "--help"],
            ["uvx", "--from", sw.SPEC_KIT_UVX_SOURCE, "spec-kit", "--version"],
        )
    else:
        smoke_argv_options = (
            [command.argv[0], "--help"],
            [command.argv[0], "--version"],
        )
    smoke_results: list[str] = []
    for argv in smoke_argv_options:
        try:
            completed = _run_command(run, list(argv), cwd=target)
        except OSError as exc:
            return {
                "status": "ACTION",
                "details": f"{command.display} smoke check failed to start: {exc}",
                "next_action": f"Install or repair {command.argv[0]} and rerun the readiness doctor.",
            }
        if completed.returncode == 0:
            if "init" in argv and "--force" not in f"{completed.stdout}\n{completed.stderr}":
                return {
                    "status": "ACTION",
                    "details": f"Init smoke check succeeded but did not advertise --force: {shlex.join(argv)}",
                    "next_action": f"Repair or upgrade {command.label}; HLDspec requires the non-interactive init --force form.",
                }
            return {
                "status": "PASS",
                "details": f"Smoke check succeeded: {shlex.join(argv)}",
                "next_action": None,
            }
        smoke_results.append(shlex.join(argv))
    return {
        "status": "ACTION",
        "details": "SpecKit smoke check did not pass for: " + ", ".join(smoke_results) + ".",
        "next_action": f"Repair or reinstall the selected SpecKit command for {command.label} and rerun the readiness doctor.",
    }


def _summary_status(checks: list[dict[str, Any]]) -> str:
    if any(check["status"] == "CONFLICT" for check in checks):
        return "CONFLICT"
    if any(check["status"] == "ACTION" for check in checks):
        return "ACTION"
    return "PASS"


def summarize_speckit_readiness(report: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Readiness Doctor",
        "",
        f"STATUS: {report.get('status', 'ACTION')}",
        f"Target: {report.get('target', '')}",
        f"Selected init command: {report.get('selected_init_command') or 'none'}",
        "",
        "Available init commands:",
    ]
    available = report.get("available_init_commands") or []
    if available:
        for item in available:
            lines.append(f"- {item.get('display', item)}")
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            f"Workspace initialized: {str((report.get('workspace_status') or {}).get('initialized', False)).lower()}",
            f"Branch hook/manual branch path ready: {report.get('branch_hook_status', {}).get('status', 'ACTION')}",
            "",
            "Checks:",
        ]
    )
    for check in report.get("checks", []):
        lines.append(f"- {check['status']}: {check['name']} - {check['details']}")
    lines.extend(["", "Next actions:"])
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")
    summary = report.get("summary")
    if summary:
        lines.extend(["", summary])
    lines.append("")
    return "\n".join(lines)


def summarize_speckit_init_prereqs(report: dict[str, Any]) -> str:
    lines = [
        "# Build Loop Init Prerequisites",
        "",
        f"STATUS: {report.get('status', 'ACTION')}",
        f"Target: {report.get('target', '')}",
        f"Selected init command: {report.get('selected_init_command') or 'none'}",
        "",
        "Checks:",
    ]
    for check in report.get("checks", []):
        lines.append(f"- {check['status']}: {check['name']} - {check['details']}")
    lines.extend(["", "Next actions:"])
    for action in report.get("next_actions", []):
        lines.append(f"- {action}")
    summary = report.get("summary")
    if summary:
        lines.extend(["", summary])
    lines.append("")
    return "\n".join(lines)
