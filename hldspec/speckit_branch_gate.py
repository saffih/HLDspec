"""Read-only SpecKit branch/artifact binding gate.

SpecKit owns branch creation through `/speckit.specify`. HLDspec only
verifies readiness, branch/artifact consistency, blockers, and the next safe
action. This module must never create branches, commit, push, open PRs,
merge, or run SpecKit.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import control_paths
from .spec_bundles import utc_now
from .workspace_adapter import reserved_workspace_root_suffix

SCHEMA_VERSION = 1

REPORT_JSON = "speckit_branch_gate.json"
REPORT_MD = "speckit_branch_gate.md"

STATUS_WORKSPACE_ROOT_INVALID = "WORKSPACE_ROOT_INVALID"
STATUS_NO_GIT = "NO_GIT"
STATUS_NO_BRANCH = "NO_BRANCH"
STATUS_READY_FOR_SPECKIT_SPECIFY = "READY_FOR_SPECKIT_SPECIFY"
STATUS_SPECKIT_BRANCH_CREATED = "SPECKIT_BRANCH_CREATED"
STATUS_BRANCH_SPEC_DIR_MISMATCH = "BRANCH_SPEC_DIR_MISMATCH"
STATUS_SPEC_MISSING = "SPEC_MISSING"
STATUS_STALE_ARTIFACT_FROM_OTHER_BRANCH = "STALE_ARTIFACT_FROM_OTHER_BRANCH"

SAFETY_PASS = "PASS"
SAFETY_ACTION = "ACTION"
SAFETY_BLOCKED = "BLOCKED"

# SpecKit feature branches/spec directories follow `<NNN>-<slug>`, e.g. `001-feature-name`.
FEATURE_BRANCH_RE = re.compile(r"^[0-9]{3}-[a-z0-9]+(?:-[a-z0-9]+)*$")

PHASE_ARTIFACT_NAMES = ("plan.md", "tasks.md")


def _run_git(
    target: Path,
    argv: list[str],
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> str | None:
    runner = run or subprocess.run
    try:
        completed = runner(
            ["git", "-C", str(target), *argv],
            cwd=str(target),
            text=True,
            capture_output=True,
            check=False,
        )
    except Exception:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.rstrip("\n")


def _is_feature_branch(branch: str) -> bool:
    return bool(FEATURE_BRANCH_RE.match(branch))


def _other_feature_spec_dirs(specs_root: Path, current_branch: str) -> list[str]:
    if not specs_root.is_dir():
        return []
    return sorted(
        entry.name
        for entry in specs_root.iterdir()
        if entry.is_dir() and entry.name != current_branch and _is_feature_branch(entry.name)
    )


def _find_stale_artifact(specs_root: Path, current_branch: str, current_spec_dir: Path) -> dict[str, str] | None:
    if not specs_root.is_dir():
        return None
    for name in PHASE_ARTIFACT_NAMES:
        current_file = current_spec_dir / name
        if not current_file.is_file():
            continue
        try:
            current_bytes = current_file.read_bytes()
        except OSError:
            continue
        for other_dir in sorted(specs_root.iterdir(), key=lambda p: p.name):
            if not other_dir.is_dir() or other_dir.name == current_branch:
                continue
            other_file = other_dir / name
            if not other_file.is_file():
                continue
            try:
                other_bytes = other_file.read_bytes()
            except OSError:
                continue
            if other_bytes == current_bytes:
                return {
                    "file": name,
                    "current_path": str(current_file),
                    "other_path": str(other_file),
                    "other_branch": other_dir.name,
                }
    return None


def build_speckit_branch_gate_report(
    target: Path | str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    target_path = Path(target).expanduser().resolve()

    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target_path),
        "git_root": None,
        "current_branch": None,
        "is_feature_branch": False,
        "specs_root": str(target_path / "specs"),
        "current_spec_dir": None,
        "spec_md_exists": False,
        "plan_md_exists": False,
        "tasks_md_exists": False,
        "stale_artifact": None,
        "other_feature_spec_dirs": [],
        "merge_allowed": False,
    }

    reserved_suffix = reserved_workspace_root_suffix(target_path)
    if reserved_suffix is not None:
        base.update(
            gate_status=STATUS_WORKSPACE_ROOT_INVALID,
            safety_status=SAFETY_BLOCKED,
            blockers=[
                "Target points inside a generated path ending in "
                f"'{'/'.join(reserved_suffix)}'; it must not be accepted as a workspace root."
            ],
            next_safe_action="Point HLDspec at the authoritative target root, not a generated tool-run/sync path.",
        )
        return base

    if not target_path.exists():
        base.update(
            gate_status=STATUS_NO_GIT,
            safety_status=SAFETY_ACTION,
            blockers=[f"Target path does not exist: {target_path}"],
            next_safe_action="Create or point HLDspec at an existing git workspace before checking the SpecKit branch gate.",
        )
        return base

    git_root = _run_git(target_path, ["rev-parse", "--show-toplevel"], run=run)
    base["git_root"] = git_root
    if git_root is None:
        base.update(
            gate_status=STATUS_NO_GIT,
            safety_status=SAFETY_ACTION,
            blockers=["No git repository was detected for the target."],
            next_safe_action="Initialize or point HLDspec at a git workspace before /speckit.specify.",
        )
        return base

    current_branch = _run_git(target_path, ["branch", "--show-current"], run=run)
    base["current_branch"] = current_branch
    if not current_branch:
        base.update(
            gate_status=STATUS_NO_BRANCH,
            safety_status=SAFETY_ACTION,
            blockers=["Git repository exists but no current branch could be resolved."],
            next_safe_action="Create or switch to a branch before /speckit.specify.",
        )
        return base

    is_feature_branch = _is_feature_branch(current_branch)
    base["is_feature_branch"] = is_feature_branch

    specs_root = target_path / "specs"
    current_spec_dir = specs_root / current_branch
    spec_md = current_spec_dir / "spec.md"
    plan_md = current_spec_dir / "plan.md"
    tasks_md = current_spec_dir / "tasks.md"
    base["current_spec_dir"] = str(current_spec_dir)

    if not is_feature_branch:
        base.update(
            gate_status=STATUS_READY_FOR_SPECKIT_SPECIFY,
            safety_status=SAFETY_PASS,
            blockers=[],
            next_safe_action="Repo is ready for /speckit.specify; SpecKit owns branch/spec-directory creation.",
        )
        return base

    if not current_spec_dir.is_dir():
        other_dirs = _other_feature_spec_dirs(specs_root, current_branch)
        base["other_feature_spec_dirs"] = other_dirs
        if other_dirs:
            base.update(
                gate_status=STATUS_BRANCH_SPEC_DIR_MISMATCH,
                safety_status=SAFETY_BLOCKED,
                blockers=[
                    f"Current branch `{current_branch}` has no matching `specs/{current_branch}/`, "
                    f"but other SpecKit spec directories exist: {', '.join(other_dirs)}."
                ],
                next_safe_action="Switch to the branch matching the existing specs/ directory, or run /speckit.specify on this branch to create its spec directory.",
            )
            return base
        base.update(
            gate_status=STATUS_READY_FOR_SPECKIT_SPECIFY,
            safety_status=SAFETY_PASS,
            blockers=[],
            next_safe_action="Repo is ready for /speckit.specify; SpecKit owns branch/spec-directory creation.",
        )
        return base

    base["spec_md_exists"] = spec_md.is_file()
    base["plan_md_exists"] = plan_md.is_file()
    base["tasks_md_exists"] = tasks_md.is_file()

    if not base["spec_md_exists"]:
        base.update(
            gate_status=STATUS_SPEC_MISSING,
            safety_status=SAFETY_BLOCKED,
            blockers=[f"`specs/{current_branch}/spec.md` is missing for the current SpecKit feature branch."],
            next_safe_action="Run /speckit.specify to generate spec.md for this branch before continuing.",
        )
        return base

    stale = _find_stale_artifact(specs_root, current_branch, current_spec_dir)
    if stale is not None:
        base["stale_artifact"] = stale
        base.update(
            gate_status=STATUS_STALE_ARTIFACT_FROM_OTHER_BRANCH,
            safety_status=SAFETY_BLOCKED,
            blockers=[
                f"`specs/{current_branch}/{stale['file']}` is byte-identical to "
                f"`specs/{stale['other_branch']}/{stale['file']}`; it looks copied from another branch, not generated for `{current_branch}`."
            ],
            next_safe_action=f"Regenerate `specs/{current_branch}/{stale['file']}` for this branch through SpecKit, or remove the stale copy.",
        )
        return base

    base.update(
        gate_status=STATUS_SPECKIT_BRANCH_CREATED,
        safety_status=SAFETY_PASS,
        blockers=[],
        next_safe_action="SpecKit branch and spec directory are bound and consistent; continue only through the approved Build Loop gates.",
    )
    return base


def render_speckit_branch_gate_report(report: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Branch Gate",
        "",
        f"Status: `{report.get('gate_status', 'UNKNOWN')}`",
        f"Safety: `{report.get('safety_status', SAFETY_ACTION)}`",
        f"Target: `{report.get('target')}`",
        f"Git root: `{report.get('git_root')}`",
        f"Current branch: `{report.get('current_branch')}`",
        f"Is feature branch: `{str(bool(report.get('is_feature_branch'))).lower()}`",
        f"Current spec dir: `{report.get('current_spec_dir')}`",
        "",
        "## Artifacts",
        "",
        f"- spec.md: `{str(bool(report.get('spec_md_exists'))).lower()}`",
        f"- plan.md: `{str(bool(report.get('plan_md_exists'))).lower()}`",
        f"- tasks.md: `{str(bool(report.get('tasks_md_exists'))).lower()}`",
        "",
        "## Blockers",
        "",
    ]
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
            "- SpecKit owns branch creation through `/speckit.specify`; this gate only verifies readiness and consistency.",
            "",
        ]
    )
    return "\n".join(lines)


def write_speckit_branch_gate_report(
    target: Path | str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    target_path = Path(target).expanduser().resolve()
    report = build_speckit_branch_gate_report(target_path, run=run)
    if report.get("gate_status") in {STATUS_WORKSPACE_ROOT_INVALID, STATUS_NO_GIT} and not target_path.exists():
        report["report_paths"] = {}
        return report
    if report.get("gate_status") == STATUS_WORKSPACE_ROOT_INVALID:
        report["report_paths"] = {}
        return report
    sync = control_paths.resolve_control_sync_dir(target_path, create=True)
    json_path = sync / REPORT_JSON
    md_path = sync / REPORT_MD
    report["report_paths"] = {"json": str(json_path), "md": str(md_path)}
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_speckit_branch_gate_report(report), encoding="utf-8")
    return report
