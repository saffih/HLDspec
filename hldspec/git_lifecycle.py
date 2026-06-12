"""Read-only Git lifecycle evidence for SpecKit Build Loop supervision.

HLDspec observes and gates branch/commit/merge evidence; it must not create
branches, commit, push, open PRs, or merge. This module writes only HLDspec
control reports through the pointer-aware sync resolver.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import control_paths
from .spec_bundles import utc_now

SCHEMA_VERSION = 1

REPORT_JSON = "git_lifecycle_report.json"
REPORT_MD = "git_lifecycle_report.md"

STATUS_NO_GIT = "NO_GIT"
STATUS_NO_BRANCH = "NO_BRANCH"
STATUS_BRANCH_POLICY_MISSING = "BRANCH_POLICY_MISSING"
STATUS_MANUAL_BRANCH_APPROVAL_MISSING = "MANUAL_BRANCH_APPROVAL_MISSING"
STATUS_BRANCH_READY = "BRANCH_READY"
STATUS_DIRTY_BEFORE_PHASE = "DIRTY_BEFORE_PHASE"
STATUS_PHASE_CHANGES_PRESENT = "PHASE_CHANGES_PRESENT"
STATUS_COMMIT_REQUIRED = "COMMIT_REQUIRED"
STATUS_COMMIT_RECORDED = "COMMIT_RECORDED"
STATUS_MERGE_NOT_READY = "MERGE_NOT_READY"
STATUS_MERGE_READY = "MERGE_READY"
STATUS_MERGED = "MERGED"
STATUS_UNKNOWN = "UNKNOWN"

SAFETY_PASS = "PASS"
SAFETY_ACTION = "ACTION"
SAFETY_BLOCKED = "BLOCKED"

BRANCH_POLICY_CANDIDATES = (
    ".specify/extensions.yml",
    ".specify/extensions.yaml",
    ".specify/hooks.yml",
    ".specify/hooks.yaml",
)
MANUAL_BRANCH_APPROVAL_FILES = (
    "git_lifecycle_manual_branch_approval.json",
    "manual_branch_equivalent.json",
)
CONTROL_PREFIXES = (".hldspec/", "prompts/")
CONTROL_NAMES = (".hldspec-run.json",)


def _run_git(
    target: Path,
    argv: list[str],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> subprocess.CompletedProcess[str]:
    runner = run or subprocess.run
    return runner(
        ["git", "-C", str(target), *argv],
        cwd=str(target),
        text=True,
        capture_output=True,
        check=False,
    )


def _git_text(
    target: Path,
    argv: list[str],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str | None:
    try:
        completed = _run_git(target, argv, run=run)
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    # Preserve leading porcelain status columns; callers that need a scalar
    # command result can still receive a trailing-newline-trimmed value.
    return completed.stdout.rstrip("\n")


def _porcelain_paths(porcelain: str) -> tuple[list[str], list[str]]:
    changed: list[str] = []
    untracked: list[str] = []
    for line in porcelain.splitlines():
        if not line.strip():
            continue
        status = line[:2]
        raw = line[3:] if len(line) > 3 else line.strip()
        path = raw.split(" -> ")[-1].strip()
        if not path:
            continue
        if status == "??":
            untracked.append(path)
        else:
            changed.append(path)
    return changed, untracked


def _is_control_path(path: str) -> bool:
    return path in CONTROL_NAMES or any(path.startswith(prefix) for prefix in CONTROL_PREFIXES)


def _phase_artifact_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if path.startswith("specs/")]


def _product_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if not _is_control_path(path)]


def _hook_policy_evidence(target: Path) -> dict[str, Any]:
    for rel in BRANCH_POLICY_CANDIDATES:
        path = target / rel
        if path.is_file():
            return {
                "state": "PRESENT_UNVERIFIED",
                "path": str(path),
                "note": "Hook policy file exists; HLDspec records it as policy evidence, not proof the hook was invoked or enforced.",
            }
    return {
        "state": "MISSING",
        "path": None,
        "note": "No hook policy file was found.",
    }


def _manual_branch_equivalent(sync: Path, current_branch: str | None) -> dict[str, Any]:
    for name in MANUAL_BRANCH_APPROVAL_FILES:
        path = sync / name
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"state": "INVALID", "path": str(path), "reason": "approval JSON is malformed"}
        if not isinstance(data, dict):
            return {"state": "INVALID", "path": str(path), "reason": "approval JSON is not an object"}
        status = str(data.get("status") or data.get("decision") or "").upper()
        branch = str(data.get("branch") or data.get("current_branch") or "").strip()
        if status not in {"APPROVED", "PASS"}:
            return {"state": "INVALID", "path": str(path), "reason": f"approval status is {status or 'missing'}"}
        if current_branch and branch and branch != current_branch:
            return {
                "state": "MISMATCH",
                "path": str(path),
                "reason": f"approval branch {branch} does not match current branch {current_branch}",
            }
        if current_branch and not branch:
            return {"state": "INVALID", "path": str(path), "reason": "approval does not name the current branch"}
        return {"state": "APPROVED", "path": str(path), "branch": branch or current_branch}
    return {"state": "MISSING", "path": None, "reason": "no explicit manual branch-equivalent approval artifact"}


def _specs_exist(target: Path) -> bool:
    specs = target / "specs"
    if not specs.is_dir():
        return False
    try:
        return any(path.is_file() for path in specs.rglob("*"))
    except OSError:
        return False


def build_git_lifecycle_report(
    target: Path | str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    create_sync: bool = False,
) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    sync = control_paths.resolve_control_sync_dir(target, create=create_sync)

    blockers: list[str] = []
    next_safe_action = "No Git lifecycle action is safe until the target state is known."
    git_root = _git_text(target, ["rev-parse", "--show-toplevel"], run=run) if target.exists() else None
    current_branch = _git_text(target, ["branch", "--show-current"], run=run) if git_root else None
    latest_commit_sha = _git_text(target, ["rev-parse", "HEAD"], run=run) if git_root else None
    base_branch = _git_text(target, ["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], run=run) if git_root else None
    porcelain = _git_text(target, ["status", "--porcelain"], run=run) if git_root else None
    changed_files, untracked_files = _porcelain_paths(porcelain or "")
    all_dirty = changed_files + untracked_files
    product_dirty = _product_paths(all_dirty)
    phase_dirty = _phase_artifact_paths(product_dirty)
    non_phase_product_dirty = [path for path in product_dirty if path not in phase_dirty]
    hook_policy = _hook_policy_evidence(target)
    manual_branch = _manual_branch_equivalent(sync, current_branch)
    specs_exist = _specs_exist(target)

    lifecycle_status = STATUS_UNKNOWN
    safety_status = SAFETY_ACTION

    if git_root is None:
        lifecycle_status = STATUS_NO_GIT
        safety_status = SAFETY_ACTION
        blockers.append("No git repository was detected for the target.")
        next_safe_action = "Initialize or point HLDspec at a git workspace before Build Loop supervision."
    elif not current_branch:
        lifecycle_status = STATUS_NO_BRANCH
        safety_status = SAFETY_ACTION
        blockers.append("Git repository exists but no current branch could be resolved.")
        next_safe_action = "Create or switch to an explicit Build Loop branch before continuing."
    elif non_phase_product_dirty:
        lifecycle_status = STATUS_DIRTY_BEFORE_PHASE
        safety_status = SAFETY_BLOCKED
        blockers.append("Product files are dirty outside SpecKit phase artifacts: " + ", ".join(non_phase_product_dirty[:8]))
        next_safe_action = "Clean, commit, or stash product changes before starting or resuming a SpecKit phase."
    elif phase_dirty:
        lifecycle_status = STATUS_COMMIT_REQUIRED
        safety_status = SAFETY_BLOCKED
        blockers.append("SpecKit phase artifacts changed without a recorded commit: " + ", ".join(phase_dirty[:8]))
        next_safe_action = "Review and commit the phase artifacts through the approved SpecKit/git workflow before continuing."
    elif hook_policy["state"] == "MISSING" and manual_branch["state"] == "MISSING":
        lifecycle_status = STATUS_BRANCH_POLICY_MISSING
        safety_status = SAFETY_BLOCKED
        blockers.append("No hook policy or explicit manual branch-equivalent approval evidence was found.")
        next_safe_action = "Install/record branch policy evidence or add explicit manual branch-equivalent approval before Build Loop continuation."
    elif hook_policy["state"] == "MISSING" and manual_branch["state"] != "APPROVED":
        lifecycle_status = STATUS_MANUAL_BRANCH_APPROVAL_MISSING
        safety_status = SAFETY_BLOCKED
        blockers.append(str(manual_branch.get("reason") or "Manual branch-equivalent approval is missing or invalid."))
        next_safe_action = "Record an explicit approved manual branch-equivalent artifact matching the current branch."
    elif specs_exist:
        lifecycle_status = STATUS_COMMIT_RECORDED
        safety_status = SAFETY_PASS
        next_safe_action = "SpecKit phase artifacts are clean in git; continue only through the next approved Build Loop gate."
    else:
        lifecycle_status = STATUS_BRANCH_READY
        safety_status = SAFETY_PASS
        next_safe_action = "Branch evidence is present; proceed only through the approved SpecKit Run Card and Build Loop gates."

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "git_root": git_root,
        "current_branch": current_branch,
        "base_branch": base_branch,
        "dirty_tree": bool(product_dirty),
        "latest_commit_sha": latest_commit_sha,
        "changed_files": changed_files,
        "untracked_files": untracked_files,
        "product_dirty_files": product_dirty,
        "phase_dirty_files": phase_dirty,
        "hook_policy_evidence": hook_policy,
        "manual_branch_equivalent_evidence": manual_branch,
        "lifecycle_status": lifecycle_status,
        "safety_status": safety_status,
        "merge_allowed": False,
        "blockers": blockers,
        "next_safe_action": next_safe_action,
    }


def render_git_lifecycle_report(report: dict[str, Any]) -> str:
    lines = [
        "# Git Lifecycle Report",
        "",
        f"Status: `{report.get('lifecycle_status', STATUS_UNKNOWN)}`",
        f"Safety: `{report.get('safety_status', SAFETY_ACTION)}`",
        f"Target: `{report.get('target')}`",
        f"Git root: `{report.get('git_root')}`",
        f"Current branch: `{report.get('current_branch')}`",
        f"Latest commit: `{report.get('latest_commit_sha')}`",
        f"Merge allowed: `{str(bool(report.get('merge_allowed'))).lower()}`",
        "",
        "## Evidence",
        "",
        f"- hook policy: `{(report.get('hook_policy_evidence') or {}).get('state', 'UNKNOWN')}` {(report.get('hook_policy_evidence') or {}).get('path') or ''}",
        f"- manual branch equivalent: `{(report.get('manual_branch_equivalent_evidence') or {}).get('state', 'UNKNOWN')}` {(report.get('manual_branch_equivalent_evidence') or {}).get('path') or ''}",
        "",
        "## Dirty files",
        "",
    ]
    dirty = report.get("product_dirty_files") or []
    lines.extend(f"- {path}" for path in dirty)
    if not dirty:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = report.get("blockers") or []
    lines.extend(f"- {item}" for item in blockers)
    if not blockers:
        lines.append("- none")
    lines.extend(["", "## Next safe action", "", str(report.get("next_safe_action") or ""), ""])
    lines.extend(
        [
            "## Boundary",
            "",
            "- Read-only: HLDspec did not create a branch, commit, push, open a PR, merge, run SpecKit, or edit product code.",
            "- Hook policy evidence is not proof that a hook was invoked or enforced.",
            "",
        ]
    )
    return "\n".join(lines)


def write_git_lifecycle_report(
    target: Path | str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    target_path = Path(target).expanduser().resolve()
    if not target_path.exists():
        report = build_git_lifecycle_report(target_path, run=run, create_sync=False)
        report["report_paths"] = {}
        return report
    report = build_git_lifecycle_report(target_path, run=run, create_sync=True)
    sync = control_paths.resolve_control_sync_dir(target_path, create=True)
    json_path = sync / REPORT_JSON
    md_path = sync / REPORT_MD
    report["report_paths"] = {"json": str(json_path), "md": str(md_path)}
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_git_lifecycle_report(report), encoding="utf-8")
    return report
