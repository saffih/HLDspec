#!/usr/bin/env python3
"""PROCESS-001 — Preflight checks for multi-agent repo safety.

Read-only diagnostics. No destructive actions.

Checks:
  1. Merge in progress (MERGE_HEAD present)
  2. Staged changes
  3. Unstaged changes
  4. Untracked files
  5. Branch divergence (ahead/behind remote)

Output:
  - JSON: preflight_check.json
  - Human-readable: preflight_check.md
  - Stdout: concise summary + "safe_to_run: true/false"

Exit codes:
  0 — safe to run
  1 — warnings only (untracked files)
  2 — unsafe (merge-in-progress, staged, unstaged, or diverged)
"""
from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class PreflightIssue:
    check: str
    level: str      # "UNSAFE" | "WARN"
    message: str
    detail: str = ""


@dataclass
class PreflightResult:
    safe_to_run: bool
    issues: list[PreflightIssue] = field(default_factory=list)
    checks_run: list[str] = field(default_factory=list)


def _run(cmd: list[str], cwd: Path) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def check_merge_in_progress(repo: Path) -> PreflightIssue | None:
    merge_head = repo / ".git" / "MERGE_HEAD"
    cherry_head = repo / ".git" / "CHERRY_PICK_HEAD"
    rebase_dir = repo / ".git" / "rebase-merge"
    rebase_apply = repo / ".git" / "rebase-apply"

    if merge_head.exists():
        return PreflightIssue("merge_in_progress", "UNSAFE", "Merge in progress (MERGE_HEAD exists). Resolve before running.")
    if cherry_head.exists():
        return PreflightIssue("merge_in_progress", "UNSAFE", "Cherry-pick in progress (CHERRY_PICK_HEAD). Resolve before running.")
    if rebase_dir.exists() or rebase_apply.exists():
        return PreflightIssue("merge_in_progress", "UNSAFE", "Rebase in progress. Resolve before running.")
    return None


def check_staged_changes(repo: Path) -> PreflightIssue | None:
    rc, out, _ = _run(["git", "diff", "--cached", "--name-only"], repo)
    if rc != 0:
        return PreflightIssue("staged_changes", "UNSAFE", "Could not check staged changes.", detail=out)
    if out:
        files = out.splitlines()
        return PreflightIssue(
            "staged_changes", "UNSAFE",
            f"{len(files)} staged file(s). Commit or stash before running.",
            detail="\n".join(files[:10]) + (" ..." if len(files) > 10 else ""),
        )
    return None


def check_unstaged_changes(repo: Path) -> PreflightIssue | None:
    rc, out, _ = _run(["git", "diff", "--name-only"], repo)
    if rc != 0:
        return PreflightIssue("unstaged_changes", "UNSAFE", "Could not check unstaged changes.", detail=out)
    if out:
        files = out.splitlines()
        return PreflightIssue(
            "unstaged_changes", "UNSAFE",
            f"{len(files)} unstaged modified file(s). Commit or stash before running.",
            detail="\n".join(files[:10]) + (" ..." if len(files) > 10 else ""),
        )
    return None


def check_untracked_files(repo: Path) -> PreflightIssue | None:
    rc, out, _ = _run(["git", "ls-files", "--others", "--exclude-standard"], repo)
    if rc != 0:
        return None  # Not critical if this fails
    if out:
        files = out.splitlines()
        return PreflightIssue(
            "untracked_files", "WARN",
            f"{len(files)} untracked file(s). These will not be committed automatically.",
            detail="\n".join(files[:10]) + (" ..." if len(files) > 10 else ""),
        )
    return None


def check_branch_divergence(repo: Path) -> PreflightIssue | None:
    # Get current branch
    rc, branch, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], repo)
    if rc != 0 or branch in ("HEAD", ""):
        return PreflightIssue("branch_divergence", "WARN", "Could not determine current branch (detached HEAD?).")

    # Check if remote tracking branch exists
    rc, remote_ref, _ = _run(["git", "rev-parse", "--abbrev-ref", f"{branch}@{{u}}"], repo)
    if rc != 0:
        # No upstream configured — normal for local-only branches; not a warning
        return None

    # Count ahead/behind
    rc, counts, _ = _run(["git", "rev-list", "--left-right", "--count", f"{remote_ref}...HEAD"], repo)
    if rc != 0:
        return None

    parts = counts.split()
    if len(parts) != 2:
        return None

    behind, ahead = int(parts[0]), int(parts[1])
    if behind > 0:
        return PreflightIssue(
            "branch_divergence", "UNSAFE",
            f"Branch '{branch}' is {behind} commit(s) behind '{remote_ref}'. Pull before running.",
            detail=f"ahead={ahead}, behind={behind}",
        )
    if ahead > 0:
        # Ahead-only is safe — just note it
        return PreflightIssue(
            "branch_divergence", "WARN",
            f"Branch '{branch}' is {ahead} commit(s) ahead of '{remote_ref}'. Consider pushing.",
            detail=f"ahead={ahead}, behind=0",
        )
    return None


def run_preflight(repo: Path) -> PreflightResult:
    issues: list[PreflightIssue] = []
    checks_run: list[str] = []

    for name, fn in [
        ("merge_in_progress", lambda: check_merge_in_progress(repo)),
        ("staged_changes",    lambda: check_staged_changes(repo)),
        ("unstaged_changes",  lambda: check_unstaged_changes(repo)),
        ("untracked_files",   lambda: check_untracked_files(repo)),
        ("branch_divergence", lambda: check_branch_divergence(repo)),
    ]:
        checks_run.append(name)
        issue = fn()
        if issue is not None:
            issues.append(issue)

    unsafe = any(i.level == "UNSAFE" for i in issues)
    return PreflightResult(safe_to_run=not unsafe, issues=issues, checks_run=checks_run)


def render_md(result: PreflightResult) -> str:
    status = "✅ SAFE" if result.safe_to_run else "🚫 UNSAFE"
    lines = [
        "# HLDspec Preflight Check",
        "",
        f"Status: `{'SAFE' if result.safe_to_run else 'UNSAFE'}`",
        f"safe_to_run: `{str(result.safe_to_run).lower()}`",
        "",
    ]

    if not result.issues:
        lines.append("All checks passed. Repository is clean.")
    else:
        for issue in result.issues:
            icon = "🚫" if issue.level == "UNSAFE" else "⚠️"
            lines += [
                f"### {icon} {issue.check} — {issue.level}",
                "",
                issue.message,
            ]
            if issue.detail:
                lines += ["", "```", issue.detail, "```"]
            lines.append("")

    lines += [
        "## Checks run",
        "",
    ]
    for check in result.checks_run:
        lines.append(f"- {check}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run preflight safety checks on the repo.")
    parser.add_argument("--repo", default=".", help="Repo root (default: cwd)")
    parser.add_argument("--output-dir", default=None, help="Write JSON + MD report to this dir")
    parser.add_argument("--fail-on-unsafe", action="store_true", help="Exit 2 if unsafe")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    result = run_preflight(repo)

    print(f"Preflight: {'SAFE' if result.safe_to_run else 'UNSAFE'}")
    for issue in result.issues:
        print(f"  [{issue.level}] {issue.check}: {issue.message}")
    if not result.issues:
        print("  All checks passed.")

    if args.output_dir:
        out = Path(args.output_dir)
        if not out.is_absolute():
            out = repo / out
        out.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": 1,
            "safe_to_run": result.safe_to_run,
            "issues": [asdict(i) for i in result.issues],
            "checks_run": result.checks_run,
        }
        (out / "preflight_check.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        (out / "preflight_check.md").write_text(render_md(result), encoding="utf-8")

    if args.fail_on_unsafe and not result.safe_to_run:
        return 2
    return 1 if any(i.level == "WARN" for i in result.issues) else 0


if __name__ == "__main__":
    raise SystemExit(main())
