#!/usr/bin/env python3
"""Architecture fitness function checker.

Runs invariant checks on the codebase and exits:
  0 = all pass
  1 = warnings only
  2 = any failures
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# Finding types
# ---------------------------------------------------------------------------

@dataclass
class FitnessResult:
    name: str
    level: str   # "PASS", "WARN", or "FAIL"
    message: str


@dataclass
class CheckReport:
    results: list[FitnessResult] = field(default_factory=list)

    @property
    def has_failures(self) -> bool:
        return any(r.level == "FAIL" for r in self.results)

    @property
    def has_warnings(self) -> bool:
        return any(r.level == "WARN" for r in self.results)

    def exit_code(self) -> int:
        if self.has_failures:
            return 2
        if self.has_warnings:
            return 1
        return 0


# ---------------------------------------------------------------------------
# Check 1: shell scripts must not contain Python-style conditional logic on artifact fields
# ---------------------------------------------------------------------------

# Patterns that indicate embedded decision logic in shell (not just reading a status value)
_SHELL_DECISION_PATTERNS = [
    re.compile(r'if.*decision.*=='),
    re.compile(r'if.*status.*=='),
]

# Shell scripts allowed to reference REWORK_REQUIRED for status reading (not encoding logic)
_SHELL_STATUS_EXEMPT = {"project_continue.sh"}


def check_shell_policy_markers(repo_root: Path) -> list[FitnessResult]:
    """Check 1: shell scripts must not contain Python-style conditional logic on artifact fields."""
    name = "shell scripts must not contain product policy markers"
    results = []
    sh_files = list((repo_root / "scripts").glob("*.sh"))

    for sh_file in sh_files:
        text = sh_file.read_text(encoding="utf-8", errors="replace")
        for pattern in _SHELL_DECISION_PATTERNS:
            if pattern.search(text):
                results.append(FitnessResult(
                    name=name,
                    level="WARN",
                    message=f"{sh_file.name}: Python-style conditional on artifact field ({pattern.pattern!r})",
                ))
                break  # one finding per file

    if not results:
        results.append(FitnessResult(name=name, level="PASS", message="No shell scripts contain embedded decision logic"))
    return results


# ---------------------------------------------------------------------------
# Check 2: generated JSON artifacts should declare schema_version
# ---------------------------------------------------------------------------

def check_schema_version(sync_dir: Path | None) -> list[FitnessResult]:
    """Check 2: generated JSON artifacts should declare schema_version."""
    name = "generated JSON artifacts should declare schema_version"
    if sync_dir is None:
        return [FitnessResult(name=name, level="PASS", message="No workspace given; skipped")]

    json_files = list(sync_dir.rglob("*.json"))
    if not json_files:
        return [FitnessResult(name=name, level="PASS", message="No JSON files found in sync dir")]

    results = []
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8", errors="replace"))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and "schema_version" not in data:
            results.append(FitnessResult(
                name=name,
                level="WARN",
                message=f"{jf.name}: missing schema_version",
            ))

    if not results:
        results.append(FitnessResult(name=name, level="PASS", message="All JSON artifacts declare schema_version"))
    return results


# ---------------------------------------------------------------------------
# Check 3: machines must not import subprocess or requests directly
# ---------------------------------------------------------------------------

_FORBIDDEN_MACHINE_IMPORTS = ["import subprocess", "import requests", "import urllib"]


def check_machine_forbidden_imports(repo_root: Path) -> list[FitnessResult]:
    """Check 3: machines must not import subprocess or requests directly."""
    name = "machines must not import subprocess or requests directly"
    results = []
    machines_dir = repo_root / "hldspec" / "machines"

    for py_file in machines_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for forbidden in _FORBIDDEN_MACHINE_IMPORTS:
            if forbidden in text:
                results.append(FitnessResult(
                    name=name,
                    level="FAIL",
                    message=f"{py_file.name}: contains forbidden import {forbidden!r}",
                ))

    if not results:
        results.append(FitnessResult(name=name, level="PASS", message="No machines contain forbidden imports"))
    return results


# ---------------------------------------------------------------------------
# Check 4: deprecated terms must not appear in active control logic
# ---------------------------------------------------------------------------

_DEPRECATED_TERMS = [
    "FIX+KEEP_PLAN",
    "target-spec generation is allowed",
    "next safe checkpoint",
]


def check_deprecated_terms(repo_root: Path) -> list[FitnessResult]:
    """Check 4: deprecated terms must not appear in active control logic."""
    name = "deprecated terms must not appear in active control logic"
    results = []
    machines_dir = repo_root / "hldspec" / "machines"

    for py_file in machines_dir.glob("*.py"):
        text = py_file.read_text(encoding="utf-8", errors="replace")
        for term in _DEPRECATED_TERMS:
            if term in text:
                results.append(FitnessResult(
                    name=name,
                    level="FAIL",
                    message=f"{py_file.name}: contains deprecated term {term!r}",
                ))

    if not results:
        results.append(FitnessResult(name=name, level="PASS", message="No deprecated terms found in machines"))
    return results


# ---------------------------------------------------------------------------
# Check 5: SkepticFinding required fields match REQUIRED_FINDING_FIELDS
# ---------------------------------------------------------------------------

def check_skeptic_finding_fields(repo_root: Path) -> list[FitnessResult]:
    """Check 5: SkepticFinding required fields match REQUIRED_FINDING_FIELDS."""
    name = "SkepticFinding required fields match REQUIRED_FINDING_FIELDS"
    try:
        import importlib.util
        _mod_name = "hldspec.skeptic_schema"
        spec = importlib.util.spec_from_file_location(
            _mod_name,
            repo_root / "hldspec" / "skeptic_schema.py",
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[_mod_name] = module
        spec.loader.exec_module(module)
    except Exception as e:
        return [FitnessResult(name=name, level="FAIL", message=f"Could not import skeptic_schema: {e}")]

    import dataclasses
    try:
        finding_cls = module.SkepticFinding
        required_fields = set(module.REQUIRED_FINDING_FIELDS)
    except AttributeError as e:
        return [FitnessResult(name=name, level="FAIL", message=f"Missing attribute in skeptic_schema: {e}")]

    dc_fields = {f.name for f in dataclasses.fields(finding_cls)}
    missing_from_dataclass = required_fields - dc_fields
    if missing_from_dataclass:
        return [FitnessResult(
            name=name,
            level="FAIL",
            message=f"REQUIRED_FINDING_FIELDS has entries not in SkepticFinding: {sorted(missing_from_dataclass)}",
        )]

    return [FitnessResult(name=name, level="PASS", message="SkepticFinding fields match REQUIRED_FINDING_FIELDS")]


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all_checks(repo_root: Path, sync_dir: Path | None) -> CheckReport:
    report = CheckReport()
    report.results.extend(check_shell_policy_markers(repo_root))
    report.results.extend(check_schema_version(sync_dir))
    report.results.extend(check_machine_forbidden_imports(repo_root))
    report.results.extend(check_deprecated_terms(repo_root))
    report.results.extend(check_skeptic_finding_fields(repo_root))
    return report


def print_report(report: CheckReport) -> None:
    # Group by check name
    by_name: dict[str, list[FitnessResult]] = {}
    for r in report.results:
        by_name.setdefault(r.name, []).append(r)

    for check_name, findings in by_name.items():
        print(f"Fitness check: {check_name}")
        for f in findings:
            print(f"  {f.level}: {f.message}")
        print()


def write_outputs(report: CheckReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    json_data = [
        {"name": r.name, "level": r.level, "message": r.message}
        for r in report.results
    ]
    (output_dir / "architecture_fitness.json").write_text(
        json.dumps(json_data, indent=2), encoding="utf-8"
    )

    lines = ["# Architecture Fitness Report\n"]
    by_name: dict[str, list[FitnessResult]] = {}
    for r in report.results:
        by_name.setdefault(r.name, []).append(r)
    for check_name, findings in by_name.items():
        lines.append(f"## {check_name}\n")
        for f in findings:
            lines.append(f"- **{f.level}**: {f.message}")
        lines.append("")
    (output_dir / "architecture_fitness.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Architecture fitness checker")
    parser.add_argument("--repo-root", default=".", help="Path to repo root")
    parser.add_argument("--output-dir", default=None, help="Write JSON + MD report here")
    parser.add_argument("--workspace", default=None, help="Workspace dir (for schema_version check)")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    sync_dir = None
    if args.workspace:
        sync_dir = Path(args.workspace) / "firstrun" / ".specify" / "sync"
        if not sync_dir.exists():
            sync_dir = None

    report = run_all_checks(repo_root, sync_dir)
    print_report(report)

    if args.output_dir:
        write_outputs(report, Path(args.output_dir))

    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())
