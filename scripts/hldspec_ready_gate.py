#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


@dataclass
class CheckResult:
    name: str
    status: str
    command: list[str]
    returncode: int
    summary: str
    stdout_tail: str = ""
    stderr_tail: str = ""


REQUIRED_FILES = [
    "AGENTS.md",
    "hld_spec_sync.py",
    "scripts/hldspec_run.sh",
    "scripts/project_continue.sh",
    "scripts/project_first_run.sh",
    "scripts/first_run_readonly.sh",
    "scripts/write_skeptic_cache.py",
    "scripts/build_hld_conversion_plan.py",
    "scripts/build_hld_conversion_decision_queue.py",
    "scripts/build_hldspec_state.py",
    "scripts/build_speckit_prework_package.py",
    "scripts/build_speckit_proxy_dossier.py",
    "scripts/review_spec_build_plan.py",
    "docs/CANONICAL_FLOW.md",
    "docs/CONTEXT_TAILORING_PROTOCOL.md",
    "docs/SPECKIT_PROXY_PROTOCOL.md",
    "docs/skeptic_framework_cache.json",
]

REQUIRED_TEST_MODULES = [
    "tests.test_raw_hld_marking_plan",
    "tests.test_spec_build_plan_quality_gate_fixtures",
    "tests.test_context_tailoring_protocol",
    "tests.test_context_tailoring_compliance_review",
    "tests.test_speckit_prework_plan",
    "tests.test_speckit_proxy_protocol",
]


def tail(text: str, max_chars: int = 4000) -> str:
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def python_cmd(repo: Path) -> list[str]:
    if subprocess.run(["bash", "-lc", "command -v uv"], cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
        return ["uv", "run", "python"]
    return [sys.executable]


def run_check(repo: Path, name: str, command: Sequence[str], *, env: dict[str, str] | None = None) -> CheckResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    proc = subprocess.run(
        list(command),
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=merged_env,
        check=False,
    )
    status = "PASS" if proc.returncode == 0 else "FAIL"
    summary = "command passed" if proc.returncode == 0 else f"command failed with rc={proc.returncode}"
    return CheckResult(
        name=name,
        status=status,
        command=list(command),
        returncode=proc.returncode,
        summary=summary,
        stdout_tail=tail(proc.stdout),
        stderr_tail=tail(proc.stderr),
    )


def run_flow_checkpoint_check(repo: Path, command: Sequence[str], workspace: Path) -> CheckResult:
    proc = subprocess.run(
        list(command),
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    checkpoint_files = [
        workspace / ".specify" / "sync" / "hld_conversion_decision_queue.md",
        workspace / ".specify" / "sync" / "raw_hld_marking_plan.md",
        workspace / "firstrun" / ".specify" / "sync" / "hldspec_state.md",
        workspace / "firstrun" / ".specify" / "sync" / "speckit_prework_package.md",
    ]
    reached_checkpoint = any(path.exists() for path in checkpoint_files)
    if proc.returncode == 0:
        status = "PASS"
        summary = "flow dry run completed and reached a clean checkpoint"
    elif proc.returncode == 2 and reached_checkpoint:
        status = "PASS"
        summary = "flow dry run stopped at an expected safe checkpoint; rc=2 is accepted when checkpoint artifacts exist"
    else:
        status = "FAIL"
        summary = f"flow dry run failed with rc={proc.returncode}"
    return CheckResult(
        name="flow_local_checkpoint_dry_run",
        status=status,
        command=list(command),
        returncode=proc.returncode,
        summary=summary,
        stdout_tail=tail(proc.stdout),
        stderr_tail=tail(proc.stderr),
    )


def file_presence_check(repo: Path) -> CheckResult:
    missing = [rel for rel in REQUIRED_FILES if not (repo / rel).exists()]
    status = "PASS" if not missing else "FAIL"
    summary = "all required files exist" if not missing else "missing: " + ", ".join(missing)
    return CheckResult(
        name="required_files",
        status=status,
        command=[],
        returncode=0 if not missing else 2,
        summary=summary,
    )


def test_module_exists(repo: Path, module: str) -> bool:
    rel = module.replace(".", "/") + ".py"
    return (repo / rel).exists()


def test_module_has_tests(repo: Path, module: str) -> bool:
    rel = module.replace(".", "/") + ".py"
    path = repo / rel
    if not path.exists():
        return False
    content = path.read_text(encoding="utf-8", errors="replace")
    return "unittest.TestCase" in content or "(unittest.TestCase)" in content or "def test_" in content


def render_report(data: dict[str, object]) -> str:
    lines = [
        "# HLDspec Ready Gate Report",
        "",
        "made by AI",
        "",
        f"Status: `{data['status']}`",
        "",
        "## Meaning",
        "",
    ]

    if data["status"] == "READY_FOR_PAID_AGENT_TEST":
        lines.append("HLDspec passed the local no-credit readiness gate. It is reasonable to spend agent/SpecKit credits on the next bounded test.")
    else:
        lines.append("HLDspec is not ready for paid agent/SpecKit work. Fix the blockers below first.")

    lines += [
        "",
        "## Checks",
        "",
    ]

    for item in data["checks"]:
        assert isinstance(item, dict)
        lines += [
            f"### {item['name']}",
            "",
            f"- status: `{item['status']}`",
            f"- return code: `{item['returncode']}`",
            f"- summary: {item['summary']}",
        ]
        command = item.get("command") or []
        if command:
            lines.append(f"- command: `{' '.join(shlex.quote(str(part)) for part in command)}`")
        if item.get("stdout_tail"):
            lines += ["", "stdout tail:", "", "```text", str(item["stdout_tail"]).rstrip(), "```"]
        if item.get("stderr_tail"):
            lines += ["", "stderr tail:", "", "```text", str(item["stderr_tail"]).rstrip(), "```"]
        lines.append("")

    lines += [
        "## Blockers",
        "",
    ]
    blockers = data.get("blockers", [])
    if not blockers:
        lines.append("- none")
    else:
        for blocker in blockers:
            lines.append(f"- {blocker}")

    lines += [
        "",
        "## Ready definition",
        "",
        "- required HLDspec files exist",
        "- RunSkeptic naming/file tests pass",
        "- raw-HLD marking test passes",
        "- product-readiness plan-quality fixtures pass",
        "- SpecKit prework/proxy tests pass",
        "- full unittest discovery passes",
        "- optional Flow dry checkpoint passes when `--flow-hld` is provided",
        "- no paid agent, SpecKit, implementation, or final spec generation was invoked by this gate",
        "",
    ]

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the local no-credit HLDspec readiness gate.")
    parser.add_argument("--repo", default=".", help="HLDspec repo root")
    parser.add_argument("--output-dir", default=".hldspec-ready-gate")
    parser.add_argument("--flow-hld", default="", help="Optional target HLD for a local dry checkpoint run")
    parser.add_argument("--fail-on-not-ready", action="store_true")
    parser.add_argument("--structure-only", action="store_true", help="Check required files only; do not run tests. Used by contract tests to avoid recursion.")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    out_dir = Path(args.output_dir)
    if not out_dir.is_absolute():
        out_dir = repo / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    py = python_cmd(repo)
    checks: list[CheckResult] = []

    checks.append(file_presence_check(repo))
    checks.append(run_check(repo, "git_status", ["git", "status", "--short"]))

    if args.structure_only:
        narrow_modules = []
        missing_modules = []
    else:
        narrow_modules = [
            module
            for module in REQUIRED_TEST_MODULES
            if test_module_exists(repo, module) and test_module_has_tests(repo, module)
        ]
        missing_modules = [module for module in REQUIRED_TEST_MODULES if not test_module_exists(repo, module)]
    if missing_modules:
        checks.append(
            CheckResult(
                name="required_test_modules",
                status="FAIL",
                command=[],
                returncode=2,
                summary="missing test modules: " + ", ".join(missing_modules),
            )
        )
    else:
        checks.append(
            CheckResult(
                name="required_test_modules",
                status="PASS",
                command=[],
                returncode=0,
                summary="all required test modules exist",
            )
        )

    for module in narrow_modules:
        checks.append(run_check(repo, f"narrow_test:{module}", [*py, "-m", "unittest", module, "-v"]))

    if not args.structure_only:
        checks.append(run_check(repo, "full_unittest_discovery", [*py, "-m", "unittest", "discover", "-s", "tests", "-v"]))

    context_review = repo / "scripts" / "review_context_tailoring_compliance.py"
    if context_review.exists() and not args.structure_only:
        checks.append(
            run_check(
                repo,
                "context_tailoring_compliance",
                [*py, str(context_review), "--repo", str(repo), "--output-dir", str(out_dir / "context_tailoring")],
            )
        )

    skeptic_review = repo / "scripts" / "run_skeptic_meta_review.py"
    if skeptic_review.exists() and not args.structure_only:
        checks.append(
            run_check(
                repo,
                "runskeptic_meta_review",
                [*py, str(skeptic_review), "--repo", str(repo), "--output-dir", str(out_dir / "runskeptic_meta_review"), "--fail-on-blocker"],
            )
        )

    if args.flow_hld and not args.structure_only:
        flow_hld = Path(args.flow_hld).expanduser().resolve()
        if not flow_hld.exists():
            checks.append(
                CheckResult(
                    name="flow_hld_exists",
                    status="FAIL",
                    command=[],
                    returncode=2,
                    summary=f"flow HLD not found: {flow_hld}",
                )
            )
        else:
            flow_workspace = out_dir / "flow-dry-run"
            checks.append(
                run_flow_checkpoint_check(
                    repo,
                    ["bash", str(repo / "scripts" / "hldspec_run.sh"), str(flow_hld), str(flow_workspace)],
                    flow_workspace,
                )
            )

    blockers = [f"{check.name}: {check.summary}" for check in checks if check.status != "PASS"]
    status = "READY_FOR_PAID_AGENT_TEST" if not blockers else "NOT_READY"

    data = {
        "schema_version": 1,
        "status": status,
        "repo": str(repo),
        "flow_hld": args.flow_hld,
        "blockers": blockers,
        "checks": [asdict(check) for check in checks],
    }

    json_path = out_dir / "hldspec_ready_gate.json"
    md_path = out_dir / "hldspec_ready_gate.md"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_report(data), encoding="utf-8")

    print(f"HLDspec Ready Gate: {status}")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    if blockers:
        print("Blockers:")
        for blocker in blockers:
            print(f"- {blocker}")

    if args.fail_on_not_ready and blockers:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
