"""Read-only Product Runability / Demo Gate.

Journey 3 (Build Loop Supervision) needs to answer the half-built-target
question: "what was built, how do I install/test/start it, and what should I
expect?" — without running anything. This module inspects a target read-only
and reports what run instructions exist, or that they are missing.

Hard rules:
- Read-only: no commands, no installs, no servers, no target file changes.
- Reports are HLDspec control state, written only when the target exists,
  under the pointer-resolved controller sync dir.
- PASS means explicit, coherent instructions were *discovered* — it never
  claims the product was executed or smoke-tested.
- Unknown brownfield or a BLOCKED phase ledger blocks the gate.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from hldspec import control_paths
from hldspec import target_discovery as td
from hldspec.spec_bundles import utc_now

SCHEMA_VERSION = 1
REPORT_JSON = "product_runability_report.json"
REPORT_MD = "product_runability_report.md"

STATUS_PASS = "PASS"
STATUS_ACTION = "ACTION"
STATUS_UNKNOWN = "UNKNOWN"
STATUS_BLOCKED = "BLOCKED"

DEPENDENCY_FILES: dict[str, str] = {
    "package.json": "npm",
    "package-lock.json": "npm",
    "yarn.lock": "yarn",
    "pnpm-lock.yaml": "pnpm",
    "pyproject.toml": "pip/uv/poetry",
    "requirements.txt": "pip",
    "requirements-dev.txt": "pip",
    "setup.py": "pip",
    "setup.cfg": "pip",
    "Pipfile": "pipenv",
    "poetry.lock": "poetry",
    "go.mod": "go",
    "Cargo.toml": "cargo",
    "Gemfile": "bundler",
    "Makefile": "make",
}

SOURCE_SUFFIXES = {".py", ".js", ".ts", ".tsx", ".go", ".rs", ".rb", ".java"}
CONTROL_DIRS = {".git", ".hldspec", ".specify", "specs", "prompts", "targetHLD", "docs", "__pycache__", "node_modules", ".venv", "venv"}

_INSTALL_RE = re.compile(r"^\s*(pip3? install|npm (install|ci)|yarn install|pnpm install|poetry install|uv (sync|pip install)|bundle install|go mod download|cargo build|make (install|deps))\b")
_TEST_RE = re.compile(r"^\s*(pytest\b|python3? -m (pytest|unittest)|npm test|yarn test|go test|cargo test|make test)")
_START_RE = re.compile(r"^\s*(python3? \S+\.py\b|npm (start|run dev)|yarn (start|dev)|node \S+|uvicorn \S+|flask run|gunicorn \S+|go run \S+|cargo run|make (run|start|serve)|\./\S+)")
# Start commands are often wrapped (shell aliases/functions) — also extract an
# embedded interpreter invocation from anywhere in a line.
_START_EMBEDDED_RE = re.compile(r"\bpython3? \S+\.py\b")
_URL_RE = re.compile(r"https?://(?:localhost|127\.0\.0\.1)[^\s)\"'`]*")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _doc_files(target: Path, patterns: tuple[str, ...]) -> list[Path]:
    found: list[Path] = []
    for pattern in patterns:
        for base in (target, target / "docs"):
            if base.is_dir():
                found.extend(sorted(p for p in base.glob(pattern) if p.is_file()))
    return found


def _command_lines(text: str, regex: re.Pattern[str]) -> list[str]:
    commands: list[str] = []
    for line in text.splitlines():
        candidate = line.strip().lstrip("$ ").strip()
        if regex.match(candidate) and candidate not in commands:
            commands.append(candidate)
    return commands


def _implementation_files(target: Path) -> list[str]:
    seen: list[str] = []
    if not target.is_dir():
        return seen
    for child in sorted(target.iterdir()):
        if child.name in CONTROL_DIRS or child.name.startswith(".hldspec"):
            continue
        if child.is_file() and child.suffix in SOURCE_SUFFIXES:
            seen.append(str(child.relative_to(target)))
        elif child.is_dir() and not child.name.startswith("."):
            for sub in sorted(child.iterdir()):
                if sub.is_file() and sub.suffix in SOURCE_SUFFIXES:
                    seen.append(str(sub.relative_to(target)))
    return seen


def _smoke_test_candidates(target: Path, implementation_files: list[str]) -> list[str]:
    candidates = [
        name for name in implementation_files
        if Path(name).name.startswith("test_") or Path(name).stem.endswith("_test")
    ]
    tests_dir = target / "tests"
    if tests_dir.is_dir():
        candidates.extend(str(p.relative_to(target)) for p in sorted(tests_dir.glob("test_*.py")))
    package = _load_package_json(target)
    if isinstance(package.get("scripts"), dict) and package["scripts"].get("test"):
        candidates.append("npm test")
    return list(dict.fromkeys(candidates))


def _load_package_json(target: Path) -> dict[str, Any]:
    try:
        data = json.loads((target / "package.json").read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _git_branch(target: Path) -> str | None:
    head = _read_text(target / ".git" / "HEAD").strip()
    if head.startswith("ref: refs/heads/"):
        return head.removeprefix("ref: refs/heads/")
    return head[:12] if head else None


def _detect_product_type(target: Path, doc_text: str, start_commands: list[str], dependency_files: list[str]) -> tuple[str, list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    package = _load_package_json(target)
    deps = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})} if package else {}
    if any(name in deps for name in ("react", "vue", "svelte", "next", "@angular/core")) or (target / "index.html").is_file():
        evidence.append({"fact": "web_ui_marker", "value": "frontend framework dependency or index.html"})
        return "web_ui", evidence
    api_markers = ("fastapi", "flask", "django", "express", "uvicorn", "gunicorn")
    lowered = doc_text.lower()
    if any(marker in deps for marker in api_markers) or any(marker in lowered for marker in api_markers):
        evidence.append({"fact": "api_marker", "value": "API framework referenced in dependencies or docs"})
        return "api", evidence
    if (target / "docker-compose.yml").is_file() or (target / "Procfile").is_file():
        evidence.append({"fact": "service_marker", "value": "docker-compose.yml or Procfile"})
        return "service", evidence
    if any(cmd.startswith(("python", "node", "./", "cargo run", "go run")) for cmd in start_commands) or "cli" in lowered:
        evidence.append({"fact": "cli_marker", "value": "script-style start command or CLI mention in docs"})
        return "cli", evidence
    if any(name in {"setup.py", "pyproject.toml", "Cargo.toml", "package.json"} for name in dependency_files):
        evidence.append({"fact": "library_marker", "value": "packaging metadata without start instructions"})
        return "library", evidence
    return "unknown", evidence


def build_product_runability(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    discovery = td.build_target_discovery(target)
    blockers: list[str] = []
    warnings: list[str] = []
    evidence: list[dict[str, Any]] = []

    readme_files = _doc_files(target, ("README*", "readme*"))
    quickstart_files = _doc_files(target, ("QUICKSTART*", "GETTING_STARTED*", "quickstart*"))
    runbook_files = _doc_files(target, ("*runbook*",))
    doc_text = "\n".join(_read_text(path) for path in readme_files + quickstart_files + runbook_files)

    dependency_files = sorted(name for name in DEPENDENCY_FILES if (target / name).is_file())
    package_managers = sorted({DEPENDENCY_FILES[name] for name in dependency_files})

    install_commands = _command_lines(doc_text, _INSTALL_RE)
    test_commands = _command_lines(doc_text, _TEST_RE)
    start_commands = _command_lines(doc_text, _START_RE)
    if not start_commands:
        start_commands = list(dict.fromkeys(m.group(0) for m in _START_EMBEDDED_RE.finditer(doc_text)))
    # Bare "pytest" prose mention counts as an explicit test instruction.
    if not test_commands and re.search(r"\bpytest\b", doc_text):
        test_commands = ["pytest"]
    ui_urls = sorted(set(_URL_RE.findall(doc_text)))

    implementation_files = _implementation_files(target)
    smoke_candidates = _smoke_test_candidates(target, implementation_files)
    product_type, type_evidence = _detect_product_type(target, doc_text, start_commands, dependency_files)
    evidence.extend(type_evidence)

    branch = _git_branch(target)
    if branch:
        evidence.append({"fact": "git_branch", "value": branch})
    evidence.append({"fact": "target_discovery_classification", "value": discovery.get("classification")})
    evidence.append({"fact": "phase_ledger_safety", "value": discovery.get("phase_ledger_safety")})
    for path in readme_files:
        evidence.append({"fact": "readme", "value": str(path)})

    if discovery.get("classification") == td.CLASS_UNKNOWN_BROWNFIELD:
        status = STATUS_BLOCKED
        blockers.append("Target is UNKNOWN_BROWNFIELD: no trusted HLDspec lineage; runability is not assessed for unadopted code.")
        next_safe_action = "Stop. Resolve target trust first (see target discovery report); arbitrary brownfield adoption is unsupported."
    elif str(discovery.get("phase_ledger_safety")) == td.SAFETY_BLOCKED:
        status = STATUS_BLOCKED
        blockers.append("HLDspec phase ledger safety is BLOCKED (stale or failing phase evidence).")
        next_safe_action = "Resolve the phase ledger blockers before running or demoing the product."
    elif not implementation_files:
        status = STATUS_UNKNOWN
        next_safe_action = "No product implementation files were found. Continue the build loop; there is nothing to run yet."
    elif start_commands and test_commands and (install_commands or not dependency_files):
        status = STATUS_PASS
        next_safe_action = (
            "Instructions discovered (not executed). Review the commands below, run the tests first, then start the product."
        )
    else:
        status = STATUS_ACTION
        missing = [
            label
            for label, ok in (
                ("start instructions", bool(start_commands)),
                ("test instructions", bool(test_commands)),
                ("install instructions", bool(install_commands or not dependency_files)),
            )
            if not ok
        ]
        warnings.append(f"Product code exists but documentation lacks: {', '.join(missing)}.")
        next_safe_action = (
            f"Add explicit {', '.join(missing)} to the README/quickstart (or have the build loop produce a runbook), then rerun the runability gate."
        )

    if str(discovery.get("phase_ledger_safety")) == td.SAFETY_ACTION and status != STATUS_BLOCKED:
        warnings.append("Phase ledger safety is ACTION: some SpecKit artifacts lack passing validation evidence.")

    sync = control_paths.resolve_control_sync_dir(target)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "detected_product_type": product_type,
        "dependency_files": dependency_files,
        "detected_package_managers": package_managers,
        "likely_install_commands": install_commands,
        "likely_test_commands": test_commands,
        "likely_start_commands": start_commands,
        "likely_ui_urls": ui_urls,
        "readme_files": [str(p) for p in readme_files],
        "quickstart_files": [str(p) for p in quickstart_files],
        "runbook_files": [str(p) for p in runbook_files],
        "smoke_test_candidates": smoke_candidates,
        "implementation_files_seen": implementation_files,
        "runability_status": status,
        "blockers": blockers,
        "warnings": warnings,
        "next_safe_action": next_safe_action,
        "evidence": evidence,
        "report_paths": {
            "report_json": str(sync / REPORT_JSON),
            "report_md": str(sync / REPORT_MD),
        },
    }


def render_product_runability_md(report: dict[str, Any]) -> str:
    def section(title: str, items: list[str]) -> list[str]:
        lines = [f"## {title}", ""]
        lines.extend(f"- {item}" for item in items) if items else lines.append("- none found")
        lines.append("")
        return lines

    lines = [
        "# Product Runability Report (read-only)",
        "",
        f"Status: `{report.get('runability_status', STATUS_UNKNOWN)}`",
        f"Target: `{report.get('target', '')}`",
        f"Detected product type: `{report.get('detected_product_type', 'unknown')}`",
        "",
        "No command was executed and no file was modified to produce this report.",
        "A PASS means run instructions were discovered, not that the product was run.",
        "",
    ]
    lines += section("Install (likely)", list(report.get("likely_install_commands") or []))
    lines += section("Test (likely)", list(report.get("likely_test_commands") or []))
    lines += section("Start (likely)", list(report.get("likely_start_commands") or []))
    lines += section("UI / URLs", list(report.get("likely_ui_urls") or []))
    lines += section("Smoke test candidates", list(report.get("smoke_test_candidates") or []))
    lines += section("Blockers", list(report.get("blockers") or []))
    lines += section("Warnings", list(report.get("warnings") or []))
    lines += ["## Next safe action", "", str(report.get("next_safe_action", "")), ""]
    return "\n".join(lines)


def write_product_runability_report(target: Path) -> dict[str, Any]:
    target = Path(target).expanduser().resolve()
    report = build_product_runability(target)
    # Same read-only rule as discovery: never create a missing target.
    if not target.is_dir():
        report["reports_written"] = False
        return report
    sync = control_paths.resolve_control_sync_dir(target, create=True)
    (sync / REPORT_JSON).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (sync / REPORT_MD).write_text(render_product_runability_md(report), encoding="utf-8")
    report["reports_written"] = True
    return report
