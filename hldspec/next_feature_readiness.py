"""Read-only "next feature" readiness driver.

For the future user intent "I want the next feature: <feature description>",
this module reports which phase of the SpecKit-by-the-book ritual the target
is currently in:

    preflight -> /speckit.specify -> branch/spec binding -> clarify/checklist
    -> /speckit.plan -> /speckit.tasks -> /speckit.analyze -> /speckit.implement
    -> tests -> commit/push/PR/merge gates

It composes existing read-only facts (SpecKit workspace inspection, the
SpecKit branch/artifact binding gate, and the git lifecycle report) and infers
the current phase from durable repo evidence only -- never from chat history
or agent memory. Rerunning this report after an interruption must reproduce
the same phase from the same repo state.

This module never creates branches, commits, pushes, opens PRs, merges, runs
SpecKit, or edits target product code. `merge_allowed` is always `False`.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from . import control_paths
from . import git_lifecycle as gl
from . import model_routing as mr
from . import refresh_target as rt
from . import speckit_branch_gate as bg
from . import speckit_workspace as sw
from .spec_bundles import utc_now
from .workspace_adapter import reserved_workspace_root_suffix

SCHEMA_VERSION = 1

REPORT_JSON = "next_feature_readiness.json"
REPORT_MD = "next_feature_readiness.md"

# Phase states -- the single `phase` field always holds exactly one of these.
PHASE_NEEDS_SPECKIT_INIT = "NEEDS_SPECKIT_INIT"
PHASE_NEEDS_CONSTITUTION = "NEEDS_CONSTITUTION"
PHASE_READY_FOR_SPECKIT_SPECIFY = "READY_FOR_SPECKIT_SPECIFY"
PHASE_SPEC_BRANCH_BOUND = "SPEC_BRANCH_BOUND"
PHASE_NEEDS_CLARIFY_OR_CHECKLIST = "NEEDS_CLARIFY_OR_CHECKLIST"
PHASE_READY_FOR_PLAN = "READY_FOR_PLAN"
PHASE_PLAN_READY = "PLAN_READY"
PHASE_READY_FOR_TASKS = "READY_FOR_TASKS"
PHASE_TASKS_READY = "TASKS_READY"
PHASE_READY_FOR_ANALYZE = "READY_FOR_ANALYZE"
PHASE_ANALYZE_READY = "ANALYZE_READY"
PHASE_READY_FOR_IMPLEMENT = "READY_FOR_IMPLEMENT"
PHASE_IMPLEMENTATION_REVIEW_REQUIRED = "IMPLEMENTATION_REVIEW_REQUIRED"
PHASE_READY_FOR_COMMIT = "READY_FOR_COMMIT"
PHASE_READY_FOR_PUSH_OR_PR = "READY_FOR_PUSH_OR_PR"
PHASE_MERGE_BLOCKED_PENDING_CI_OR_APPROVAL = "MERGE_BLOCKED_PENDING_CI_OR_APPROVAL"

# Reached only on a hard branch/spec-directory binding conflict reported by the
# branch gate (BRANCH_SPEC_DIR_MISMATCH / STALE_ARTIFACT_FROM_OTHER_BRANCH).
# Not part of the SpecKit ritual phases above; surfaced separately so callers
# can distinguish "binding conflict" from "ritual phase".
PHASE_BRANCH_BINDING_BLOCKED = "BRANCH_BINDING_BLOCKED"

SAFETY_PASS = "PASS"
SAFETY_ACTION = "ACTION"
SAFETY_BLOCKED = "BLOCKED"

# A spec.md (or plan.md/tasks.md) carrying this marker is treated as not yet
# resolved by /speckit.clarify.
CLARIFY_MARKER = "[NEEDS CLARIFICATION"

# Convention for SpecKit /speckit.analyze evidence for the current feature.
# No analyze-output template exists in this repo to derive a stronger
# signature from (see Slice 5 stale-artifact heuristic for the same
# limitation); either filename below is accepted as evidence.
ANALYZE_EVIDENCE_NAMES = ("analyze_report.md", "analysis.md")

# Read-only consumption of human/CI-recorded execution evidence, mirroring the
# git_lifecycle.py manual-branch-equivalent-approval pattern. HLDspec never
# writes this file; it only reads it to avoid inferring implementation/push
# state beyond what is recorded. An optional top-level "branch" field is
# checked against the current branch; evidence recorded for a different
# branch is treated as stale (ignored), same as manual_branch_equivalent.json.
EXECUTION_EVIDENCE_FILE = "next_feature_execution_evidence.json"
EVIDENCE_TESTS_PASSED = "TESTS_PASSED"
EVIDENCE_IMPLEMENTED_COMMITTED = "IMPLEMENTED_COMMITTED"
EVIDENCE_PUSHED = "PUSHED"

# Constant guidance for the "Do not run yet" / "Report back" sections of the
# SpecKit run card. These hold for every phase: the report names exactly one
# next safe action, and re-running the driver is how the loop continues.
DO_NOT_RUN_YET = (
    "Do not run any SpecKit command beyond the one named as `speckit_next_action` "
    "above. Do not commit, push, open a PR, or merge -- those require their own "
    "explicit human-approved gates, and `merge_allowed` is always `false`."
)

REPORT_BACK = (
    "After taking the next safe action, re-run "
    "`python3 scripts/next_feature_readiness_report.py --target <path>` and report "
    "back: the new `phase`, any new `blockers`, whether `[NEEDS CLARIFICATION]` "
    "markers remain, and the resulting `speckit_next_action`."
)

# The only target-write Journey 3 command (see hldspec/refresh_target.py). Recommended
# in place of "/speckit.constitution" when refresh-target can safely
# create/refresh the managed constitution support, and advisory elsewhere.
REFRESH_TARGET_SCRIPT = "scripts/hldspec_refresh_target.py"
READINESS_SCRIPT = "scripts/next_feature_readiness_report.py"

FUTURE_EXECUTION_PLAN: dict[str, Any] = {
    "one_step_executor": (
        "Future: a supervised single-step executor that runs exactly one "
        "SpecKit command (e.g. /speckit.plan) for the phase indicated by "
        "`phase`/`speckit_next_action`, then re-runs this readiness report."
    ),
    "multi_step_supervised_driver": (
        "Future: a supervised driver that repeats the one-step executor across "
        "phases, stopping at any ACTION/BLOCKED phase or unresolved "
        "[NEEDS CLARIFICATION] marker for human review."
    ),
    "commit_push_pr_gates": (
        "Future: commit/push/PR steps require their own explicit human-approved "
        "gates; this report only identifies READY_FOR_COMMIT / "
        "READY_FOR_PUSH_OR_PR as candidates, it does not perform them."
    ),
    "merge_gate": (
        "Future: merge is only ever proposed after explicit human approval plus "
        "CI/review evidence is recorded; `merge_allowed` remains `False` in "
        "every phase produced by this module."
    ),
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _has_clarify_marker(path: Path) -> bool:
    if not path.is_file():
        return False
    return CLARIFY_MARKER in _read_text(path)


def _checklist_incomplete(spec_dir: Path) -> list[str]:
    checklists_dir = spec_dir / "checklists"
    if not checklists_dir.is_dir():
        return []
    incomplete: list[str] = []
    for path in sorted(checklists_dir.glob("*.md")):
        if "- [ ]" in _read_text(path):
            incomplete.append(str(path))
    return incomplete


def _analyze_evidence_path(spec_dir: Path) -> Path | None:
    for name in ANALYZE_EVIDENCE_NAMES:
        candidate = spec_dir / name
        if candidate.is_file():
            return candidate
    return None


def _read_execution_evidence(target_path: Path, *, current_branch: str | None) -> dict[str, Any]:
    sync = control_paths.resolve_control_sync_dir(target_path, create=False)
    path = sync / EXECUTION_EVIDENCE_FILE
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    # Mirror git_lifecycle's manual-branch-equivalent staleness check: evidence
    # recorded for a different branch must not be read as current.
    evidence_branch = str(data.get("branch") or "").strip()
    if current_branch and evidence_branch and evidence_branch != current_branch:
        return {}
    return data


def _refresh_target_status(
    target_path: Path,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    """Read-only: classify the target's HLDspec/SpecKit support files via refresh_target.

    Mirrors `hldspec refresh-target`'s dry-run classification without writing
    anything, so the run card can recommend refresh-target as a next/advisory
    action.
    """
    plan = rt.build_refresh_plan(target_path, run=run)
    helper_name = rt.nfa.BOOTSTRAP_FILE
    helper_item: dict[str, Any] = {}
    for item in plan.get("items", []):
        if str(item.get("path", "")).endswith(helper_name):
            helper_item = item
            break
    constitution_item = plan.get("constitution_status", {})
    return {
        "constitution": constitution_item,
        "helper": helper_item,
        "constitution_refresh_recommended": constitution_item.get("classification") in rt.PLANNED_CLASSIFICATIONS,
        "constitution_review_required": constitution_item.get("classification") == rt.EXISTS_WITH_LOCAL_CHANGES_REQUIRES_REVIEW,
        "helper_refresh_recommended": helper_item.get("classification") == rt.MISSING_CAN_CREATE,
    }


def build_next_feature_readiness_report(
    target: Path | str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    target_path = Path(target).expanduser().resolve()

    base: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target_path),
        "phase": None,
        "safety_status": SAFETY_ACTION,
        "completed_phases": [],
        "verified_evidence": {},
        "missing_evidence": [],
        "blockers": [],
        "speckit_next_action": None,
        "git_next_action": "No git operation is safe until the target state is known.",
        "next_safe_action": None,
        "recommended_model": None,
        "why_now": None,
        "do_not_run_yet": DO_NOT_RUN_YET,
        "report_back": REPORT_BACK.replace("<path>", str(target_path)),
        "merge_allowed": False,
        "branch_gate": None,
        "git_lifecycle": None,
        "constitution_exists": False,
        "workspace_status": None,
        "future_execution_plan": FUTURE_EXECUTION_PLAN,
        "refresh_target_status": None,
        "advisory_actions": [],
    }

    def finish(
        *,
        phase: str,
        safety: str,
        speckit_next_action: str | None,
        git_next_action: str,
        next_safe_action: str,
        recommended_model: str,
        why_now: str,
        blockers: list[str] | None = None,
        do_not_run_yet: str | None = None,
        report_back: str | None = None,
    ) -> dict[str, Any]:
        base["phase"] = phase
        base["safety_status"] = safety
        base["speckit_next_action"] = speckit_next_action
        base["git_next_action"] = git_next_action
        base["next_safe_action"] = next_safe_action
        base["recommended_model"] = recommended_model
        base["why_now"] = why_now
        base["blockers"] = blockers or []
        if do_not_run_yet is not None:
            base["do_not_run_yet"] = do_not_run_yet
        if report_back is not None:
            base["report_back"] = report_back
        return base

    reserved_suffix = reserved_workspace_root_suffix(target_path)
    if reserved_suffix is not None:
        return finish(
            phase=PHASE_NEEDS_SPECKIT_INIT,
            safety=SAFETY_BLOCKED,
            speckit_next_action=None,
            git_next_action="No git operation is safe; the target root itself is invalid.",
            next_safe_action="Point HLDspec at the authoritative target root, not a generated tool-run/sync path.",
            recommended_model=mr.MODEL_CRITICAL,
            why_now="The target root itself is invalid; a human must correct the target path before any other step is safe.",
            blockers=[
                "Target points inside a generated path ending in "
                f"'{'/'.join(reserved_suffix)}'; it must not be accepted as a workspace root."
            ],
        )

    if not target_path.exists():
        return finish(
            phase=PHASE_NEEDS_SPECKIT_INIT,
            safety=SAFETY_ACTION,
            speckit_next_action=None,
            git_next_action="No git operation is safe until the target exists.",
            next_safe_action="Create or point HLDspec at an existing git workspace before SpecKit init.",
            recommended_model=mr.MODEL_DEFAULT,
            why_now="The target workspace does not exist yet, so no ritual phase can be inferred until it does.",
            blockers=[f"Target path does not exist: {target_path}"],
        )

    branch_gate = bg.build_speckit_branch_gate_report(target_path, run=run)
    base["branch_gate"] = {
        "gate_status": branch_gate.get("gate_status"),
        "safety_status": branch_gate.get("safety_status"),
        "current_branch": branch_gate.get("current_branch"),
        "is_feature_branch": branch_gate.get("is_feature_branch"),
        "current_spec_dir": branch_gate.get("current_spec_dir"),
        "spec_md_exists": branch_gate.get("spec_md_exists"),
        "plan_md_exists": branch_gate.get("plan_md_exists"),
        "tasks_md_exists": branch_gate.get("tasks_md_exists"),
    }

    if branch_gate.get("gate_status") in {bg.STATUS_NO_GIT, bg.STATUS_NO_BRANCH}:
        return finish(
            phase=PHASE_NEEDS_SPECKIT_INIT,
            safety=branch_gate.get("safety_status", SAFETY_ACTION),
            speckit_next_action=None,
            git_next_action="No git operation is safe until a git repository and branch are resolved.",
            next_safe_action=str(branch_gate.get("next_safe_action") or "Resolve git repository/branch before SpecKit init."),
            recommended_model=mr.MODEL_DEFAULT,
            why_now="Git repository/branch state could not be resolved, so no SpecKit ritual phase can be inferred yet.",
            blockers=list(branch_gate.get("blockers") or []),
        )

    workspace = sw.inspect_workspace(target_path)
    base["workspace_status"] = workspace.metadata()

    if not (workspace.specify_dir_exists and workspace.memory_dir_exists):
        missing = []
        if not workspace.specify_dir_exists:
            missing.append(".specify/")
        if not workspace.memory_dir_exists:
            missing.append(".specify/memory/")
        base["missing_evidence"] = missing
        return finish(
            phase=PHASE_NEEDS_SPECKIT_INIT,
            safety=SAFETY_ACTION,
            speckit_next_action="Run a real SpecKit init command to create .specify/ and .specify/memory/.",
            git_next_action="No git operation is needed until SpecKit is initialized.",
            next_safe_action="Run a real SpecKit init command to initialize the target workspace before /speckit.specify.",
            recommended_model=mr.MODEL_DEFAULT,
            why_now="SpecKit has not been initialized in this repo, so no ritual phase can be inferred until init creates .specify/.",
            blockers=[f"SpecKit workspace is not initialized; missing: {', '.join(missing)}."],
        )

    base["verified_evidence"][".specify/memory/"] = str(target_path / ".specify" / "memory")

    dry_run_cmd = f"python3 {REFRESH_TARGET_SCRIPT} --target {target_path} --dry-run"
    apply_cmd = f"python3 {REFRESH_TARGET_SCRIPT} --target {target_path} --apply"
    readiness_cmd = f"python3 {READINESS_SCRIPT} --target {target_path}"

    refresh_status = _refresh_target_status(target_path, run=run)
    base["refresh_target_status"] = refresh_status
    if refresh_status["helper_refresh_recommended"]:
        helper_path = refresh_status["helper"].get("path", rt.nfa.BOOTSTRAP_FILE)
        base["advisory_actions"].append(
            f"`{helper_path}` (target-side agent-guidance bootstrap) is missing. Run `{dry_run_cmd}` "
            "to preview safely creating it -- advisory only, not required before the next SpecKit step."
        )
    if refresh_status["constitution_review_required"]:
        base["advisory_actions"].append(
            f"`{refresh_status['constitution'].get('path')}` exists without HLDspec managed markers; "
            f"`hldspec refresh-target` will not modify it. Run `{dry_run_cmd}` for a review/merge plan if "
            "you want to opt in -- this does not block the current phase."
        )

    constitution_path = target_path / ".specify" / "memory" / "constitution.md"
    constitution_exists = constitution_path.is_file()
    base["constitution_exists"] = constitution_exists
    if not constitution_exists:
        base["missing_evidence"].append(str(constitution_path))
        return finish(
            phase=PHASE_NEEDS_CONSTITUTION,
            safety=SAFETY_ACTION,
            speckit_next_action=None,
            git_next_action="No git operation is needed until the constitution is recorded.",
            next_safe_action=(
                f"Run `{dry_run_cmd}` to preview safely creating the HLDspec/SpecKit-managed "
                f"`.specify/memory/constitution.md` support file. If the plan has no conflict files, run "
                f"`{apply_cmd}`, then re-run `{readiness_cmd}`."
            ),
            recommended_model=mr.MODEL_STRONG,
            why_now=(
                "SpecKit is initialized but has no constitution; `hldspec refresh-target` can safely "
                "install the HLDspec/SpecKit-managed constitution support before the ritual continues -- "
                "do not run /speckit.constitution blindly while this safer, non-destructive path exists."
            ),
            blockers=["SpecKit constitution is missing: .specify/memory/constitution.md."],
            do_not_run_yet=(
                f"Do not run `{apply_cmd}` until the dry-run plan from `{dry_run_cmd}` has no conflict "
                "files. Do not run /speckit.specify, /speckit.plan, /speckit.tasks, or /speckit.implement "
                "until the constitution exists."
            ),
            report_back=(
                f"After the dry-run, report the planned updates and any conflict files from `{dry_run_cmd}`, "
                f"and whether `--apply` is safe. After apply, re-run `{readiness_cmd}` and report the "
                "resulting `phase` and `constitution_exists`."
            ),
        )

    base["verified_evidence"]["constitution.md"] = str(constitution_path)

    if branch_gate.get("gate_status") in {
        bg.STATUS_BRANCH_SPEC_DIR_MISMATCH,
        bg.STATUS_STALE_ARTIFACT_FROM_OTHER_BRANCH,
    }:
        return finish(
            phase=PHASE_BRANCH_BINDING_BLOCKED,
            safety=SAFETY_BLOCKED,
            speckit_next_action=None,
            git_next_action="No git operation is safe until the branch/spec-directory binding conflict is resolved.",
            next_safe_action=str(branch_gate.get("next_safe_action") or "Resolve the SpecKit branch/artifact binding gate blockers."),
            recommended_model=mr.MODEL_CRITICAL,
            why_now="The current branch and its bound spec directory disagree; proceeding would risk writing the wrong feature's artifacts.",
            blockers=list(branch_gate.get("blockers") or []),
        )

    if not branch_gate.get("is_feature_branch"):
        return finish(
            phase=PHASE_READY_FOR_SPECKIT_SPECIFY,
            safety=SAFETY_PASS,
            speckit_next_action="/speckit.specify",
            git_next_action="No git operation is needed; SpecKit owns feature branch creation.",
            next_safe_action="Repo is ready for /speckit.specify; SpecKit owns branch/spec-directory creation.",
            recommended_model=mr.MODEL_DEFAULT,
            why_now="The constitution exists and the repo is on a non-feature branch with no spec bound yet; /speckit.specify is the only step that doesn't risk drift.",
        )

    if not branch_gate.get("spec_md_exists"):
        base["missing_evidence"].append(f"{branch_gate.get('current_spec_dir')}/spec.md")
        return finish(
            phase=PHASE_READY_FOR_SPECKIT_SPECIFY,
            safety=SAFETY_ACTION,
            speckit_next_action="/speckit.specify",
            git_next_action="No git operation is needed; SpecKit owns spec.md creation for this branch.",
            next_safe_action=str(branch_gate.get("next_safe_action") or "Run /speckit.specify to generate spec.md for this branch."),
            recommended_model=mr.MODEL_DEFAULT,
            why_now="This feature branch has no spec.md yet; /speckit.specify must run before any later step can be trusted.",
            blockers=list(branch_gate.get("blockers") or []),
        )

    spec_dir = Path(str(branch_gate.get("current_spec_dir")))
    spec_md = spec_dir / "spec.md"
    base["verified_evidence"]["spec.md"] = str(spec_md)
    base["completed_phases"].append(PHASE_SPEC_BRANCH_BOUND)

    checklist_incomplete = _checklist_incomplete(spec_dir)
    if _has_clarify_marker(spec_md) or checklist_incomplete:
        blockers = []
        if _has_clarify_marker(spec_md):
            blockers.append(f"{spec_md} contains an unresolved '{CLARIFY_MARKER}' marker.")
        blockers.extend(f"Checklist has unresolved items: {path}" for path in checklist_incomplete)
        return finish(
            phase=PHASE_NEEDS_CLARIFY_OR_CHECKLIST,
            safety=SAFETY_ACTION,
            speckit_next_action="/speckit.clarify or /speckit.checklist",
            git_next_action="No git operation is needed until clarification/checklist items are resolved.",
            next_safe_action="Resolve outstanding [NEEDS CLARIFICATION] markers and/or checklist items before /speckit.plan.",
            recommended_model=mr.MODEL_STRONG,
            why_now="spec.md is bound to this branch but still has unresolved clarification/checklist markers; resolving them now prevents /speckit.plan from building on an ambiguous spec.",
            blockers=blockers,
        )

    if not branch_gate.get("plan_md_exists"):
        base["missing_evidence"].append(str(spec_dir / "plan.md"))
        return finish(
            phase=PHASE_READY_FOR_PLAN,
            safety=SAFETY_PASS,
            speckit_next_action="/speckit.plan",
            git_next_action="No git operation is needed until plan.md is generated.",
            next_safe_action="Spec is bound and clear; run /speckit.plan next.",
            recommended_model=mr.MODEL_STRONG,
            why_now="The spec is bound and free of open clarification markers, and plan.md does not exist yet; /speckit.plan is the next step in the ritual.",
        )

    base["verified_evidence"]["plan.md"] = str(spec_dir / "plan.md")
    base["completed_phases"].append(PHASE_PLAN_READY)

    if not branch_gate.get("tasks_md_exists"):
        base["missing_evidence"].append(str(spec_dir / "tasks.md"))
        return finish(
            phase=PHASE_READY_FOR_TASKS,
            safety=SAFETY_PASS,
            speckit_next_action="/speckit.tasks",
            git_next_action="No git operation is needed until tasks.md is generated.",
            next_safe_action="plan.md is present; run /speckit.tasks next.",
            recommended_model=mr.MODEL_STRONG,
            why_now="plan.md exists and tasks.md does not; /speckit.tasks is the next step in the ritual.",
        )

    base["verified_evidence"]["tasks.md"] = str(spec_dir / "tasks.md")
    base["completed_phases"].append(PHASE_TASKS_READY)

    analyze_evidence = _analyze_evidence_path(spec_dir)
    if analyze_evidence is None:
        base["missing_evidence"].append(
            " or ".join(str(spec_dir / name) for name in ANALYZE_EVIDENCE_NAMES)
        )
        return finish(
            phase=PHASE_READY_FOR_ANALYZE,
            safety=SAFETY_PASS,
            speckit_next_action="/speckit.analyze",
            git_next_action="No git operation is needed until analyze evidence is recorded.",
            next_safe_action="tasks.md is present; run /speckit.analyze next.",
            recommended_model=mr.MODEL_STRONG,
            why_now="tasks.md exists with no recorded analyze evidence; /speckit.analyze is the next step before implementation begins.",
        )

    base["verified_evidence"]["analyze_evidence"] = str(analyze_evidence)
    base["completed_phases"].append(PHASE_ANALYZE_READY)

    git_lifecycle = gl.build_git_lifecycle_report(target_path, run=run)
    base["git_lifecycle"] = {
        "lifecycle_status": git_lifecycle.get("lifecycle_status"),
        "safety_status": git_lifecycle.get("safety_status"),
        "product_dirty_files": git_lifecycle.get("product_dirty_files"),
        "phase_dirty_files": git_lifecycle.get("phase_dirty_files"),
    }
    product_dirty = list(git_lifecycle.get("product_dirty_files") or [])
    phase_dirty = list(git_lifecycle.get("phase_dirty_files") or [])
    evidence = _read_execution_evidence(target_path, current_branch=branch_gate.get("current_branch"))
    evidence_status = str(evidence.get("status") or "")

    if product_dirty:
        if evidence_status == EVIDENCE_TESTS_PASSED:
            return finish(
                phase=PHASE_READY_FOR_COMMIT,
                safety=SAFETY_ACTION,
                speckit_next_action="/speckit.implement (continue) or none if implementation is complete",
                git_next_action="Commit the implementation changes once reviewed.",
                next_safe_action=f"Tests passed per recorded evidence; commit: {', '.join(product_dirty[:8])}.",
                recommended_model=mr.MODEL_DEFAULT,
                why_now="Recorded evidence says tests passed for the current implementation changes; committing them is the next safe step.",
                blockers=[],
            )
        return finish(
            phase=PHASE_IMPLEMENTATION_REVIEW_REQUIRED,
            safety=SAFETY_ACTION,
            speckit_next_action="Review /speckit.implement output before continuing.",
            git_next_action="No commit yet; review and run tests on the dirty implementation files first.",
            next_safe_action="Uncommitted implementation changes exist with no recorded test/verification evidence; review and test before commit.",
            recommended_model=mr.MODEL_CRITICAL,
            why_now="Implementation files changed but no test evidence has been recorded; a human/agent must review and test before committing.",
            blockers=[f"Uncommitted implementation changes without recorded test evidence: {', '.join(product_dirty[:8])}."],
        )

    if phase_dirty:
        return finish(
            phase=PHASE_READY_FOR_COMMIT,
            safety=SAFETY_ACTION,
            speckit_next_action=None,
            git_next_action="Commit the updated SpecKit phase artifacts once reviewed.",
            next_safe_action=f"SpecKit phase artifacts are uncommitted: {', '.join(phase_dirty[:8])}.",
            recommended_model=mr.MODEL_DEFAULT,
            why_now="Only SpecKit phase artifacts (not product code) are uncommitted; committing them keeps the ritual state in sync with git.",
            blockers=[],
        )

    if evidence_status == EVIDENCE_PUSHED:
        return finish(
            phase=PHASE_MERGE_BLOCKED_PENDING_CI_OR_APPROVAL,
            safety=SAFETY_ACTION,
            speckit_next_action=None,
            git_next_action="No further git operation; wait for CI and explicit human review/approval before merge.",
            next_safe_action="Branch is pushed; wait for CI and human approval. HLDspec never merges.",
            recommended_model=mr.MODEL_CRITICAL,
            why_now="The branch is pushed; merge requires CI and human approval that HLDspec cannot perform or verify.",
        )

    if evidence_status == EVIDENCE_IMPLEMENTED_COMMITTED:
        return finish(
            phase=PHASE_READY_FOR_PUSH_OR_PR,
            safety=SAFETY_PASS,
            speckit_next_action=None,
            git_next_action="Push the branch and open a PR once approved.",
            next_safe_action="Implementation is committed per recorded evidence; push and open a PR through the approved workflow.",
            recommended_model=mr.MODEL_DEFAULT,
            why_now="Implementation is committed per recorded evidence and the tree is clean; pushing and opening a PR is the next step in the approved workflow.",
        )

    return finish(
        phase=PHASE_READY_FOR_IMPLEMENT,
        safety=SAFETY_PASS,
        speckit_next_action="/speckit.implement",
        git_next_action="No git operation is needed until implementation produces changes.",
        next_safe_action="Analyze evidence is present and the tree is clean; run /speckit.implement next.",
        recommended_model=mr.MODEL_STRONG,
        why_now="Analyze evidence is present and the tree is clean; /speckit.implement is the next step in the ritual.",
    )


def render_next_feature_readiness_report(report: dict[str, Any]) -> str:
    paths = report.get("report_paths") if isinstance(report.get("report_paths"), dict) else {}
    branch_gate = report.get("branch_gate") or {}
    git_lifecycle = report.get("git_lifecycle") or {}

    lines = [
        "# SpecKit Run Card",
        "",
        "Single-feature, target-repo run card from the read-only next-feature",
        "readiness driver. Re-run the driver before each next step; do not rely on",
        "chat history.",
        "",
        "## Phase",
        "",
        f"- Phase: `{report.get('phase', 'UNKNOWN')}`",
        f"- Safety: `{report.get('safety_status', SAFETY_ACTION)}`",
        f"- Target: `{report.get('target')}`",
        f"- Current branch: `{branch_gate.get('current_branch')}`",
        f"- Current spec dir: `{branch_gate.get('current_spec_dir')}`",
        f"- Constitution present: `{str(bool(report.get('constitution_exists'))).lower()}`",
        "",
        "## Completed phases",
        "",
    ]
    completed = report.get("completed_phases") or []
    lines.extend(f"- {item}" for item in completed)
    if not completed:
        lines.append("- none")

    lines.extend(["", "## Evidence", ""])
    verified = report.get("verified_evidence") or {}
    for name, path in verified.items():
        lines.append(f"- {name}: `{path}`")
    if not verified:
        lines.append("- none")

    lines.extend(["", "## Missing", ""])
    missing = report.get("missing_evidence") or []
    lines.extend(f"- {item}" for item in missing)
    if not missing:
        lines.append("- none")

    refresh_status = report.get("refresh_target_status") or {}
    if refresh_status:
        constitution_item = refresh_status.get("constitution") or {}
        helper_item = refresh_status.get("helper") or {}
        lines.extend(
            [
                "",
                "## Refresh target status",
                "",
                f"- constitution: `{constitution_item.get('path')}` -- `{constitution_item.get('classification')}`",
                f"- helper bootstrap: `{helper_item.get('path')}` -- `{helper_item.get('classification')}`",
            ]
        )

    lines.extend(["", "## Advisory actions", ""])
    advisory = report.get("advisory_actions") or []
    lines.extend(f"- {item}" for item in advisory)
    if not advisory:
        lines.append("- none")

    if git_lifecycle:
        lines.extend(
            [
                "",
                "## Git lifecycle",
                "",
                f"- lifecycle status: `{git_lifecycle.get('lifecycle_status', 'UNKNOWN')}`",
                f"- product dirty files: {git_lifecycle.get('product_dirty_files') or 'none'}",
                f"- phase dirty files: {git_lifecycle.get('phase_dirty_files') or 'none'}",
            ]
        )

    lines.extend(
        [
            "",
            "## Blockers",
            "",
        ]
    )
    blockers = report.get("blockers") or []
    lines.extend(f"- {item}" for item in blockers)
    if not blockers:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next safe action",
            "",
            f"- {report.get('next_safe_action')}",
            "",
            "## Command to run",
            "",
            f"- SpecKit: {report.get('speckit_next_action') or 'none'}",
            f"- Git: {report.get('git_next_action')}",
            "",
            "## Recommended model",
            "",
            f"- {report.get('recommended_model') or 'none'}",
            "",
            "## Why now",
            "",
            f"- {report.get('why_now') or 'none'}",
            "",
            "## Do not run yet",
            "",
            f"- {report.get('do_not_run_yet')}",
            "",
            "## Report back",
            "",
            f"- {report.get('report_back')}",
            "",
            f"Merge allowed: `{str(bool(report.get('merge_allowed'))).lower()}`",
            "",
            "## Future execution plan (not implemented)",
            "",
        ]
    )
    for key, text in (report.get("future_execution_plan") or {}).items():
        lines.append(f"- {key}: {text}")

    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "- Read-only: HLDspec did not create a branch, commit, push, open a PR, merge, run SpecKit, or edit product code.",
            "- This report infers phase from durable repo evidence only; rerunning it after an interruption reproduces the same phase from the same repo state.",
            f"- Report: `{paths.get('json', 'UNKNOWN')}`",
            "",
        ]
    )
    return "\n".join(lines)


def write_next_feature_readiness_report(
    target: Path | str,
    *,
    run: Callable[..., subprocess.CompletedProcess[str]] | None = None,
) -> dict[str, Any]:
    target_path = Path(target).expanduser().resolve()
    report = build_next_feature_readiness_report(target_path, run=run)
    if report.get("phase") == PHASE_NEEDS_SPECKIT_INIT and (
        not target_path.exists() or reserved_workspace_root_suffix(target_path) is not None
    ):
        report["report_paths"] = {}
        return report
    sync = control_paths.resolve_control_sync_dir(target_path, create=True)
    json_path = sync / REPORT_JSON
    md_path = sync / REPORT_MD
    report["report_paths"] = {"json": str(json_path), "md": str(md_path)}
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_next_feature_readiness_report(report), encoding="utf-8")
    return report
