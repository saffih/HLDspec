#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

EXPECTED_ANCHORS = ("HLD-001", "HLD-002", "HLD-003")
SLICE_FILES = (
    "implementation_slicing_policy.md",
    "implementation_slices.json",
    "slice_test_policy.md",
    "speckit_slice_execution_prompt.md",
    "anchor_coverage_schema.json",
)


@dataclass
class Check:
    name: str
    ok: bool
    details: str = ""


@dataclass
class SmokeResult:
    result: str
    source_hld: str
    target_dir: str
    source_package: str
    specify_source: str
    tmux_status: str
    checks: list[dict[str, Any]]
    failed_check: str | None
    details: str
    preserved: bool
    repo_status_changed: bool


def run(cmd: list[str], *, cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def git_status() -> str:
    cp = run(["git", "status", "--short", "--untracked-files=normal"])
    return cp.stdout


def default_fixture() -> Path:
    return ROOT / "tests_v2" / "fixtures" / "tiny_smoke_HLD.md"


def check_file(checks: list[Check], path: Path, name: str | None = None) -> None:
    checks.append(Check(name or str(path), path.is_file(), str(path)))


def check_dir(checks: list[Check], path: Path, name: str | None = None) -> None:
    checks.append(Check(name or str(path), path.is_dir(), str(path)))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def create_tmux_session(target: Path, attach: bool) -> str:
    if os.environ.get("HLDSPEC_SMOKE_FORCE_NO_TMUX") == "1":
        return "SKIP_TMUX"
    if shutil.which("tmux") is None:
        return "SKIP_TMUX"
    session = f"hldspec-smoke-{uuid.uuid4().hex[:8]}"
    log_dir = target / ".hldspec" / "tmux"
    log_dir.mkdir(parents=True, exist_ok=True)
    roles = ["main-controller", "hldspec-basepack", "target-runner", "consultant"]
    try:
        for idx, role in enumerate(roles):
            message = f"role={role}\ntarget={target}\nrequired_reads=.specify/source + .hldspec/source_package\nstop_condition=report only; no approval state\n"
            (log_dir / f"{role}.log").write_text(message, encoding="utf-8")
            if idx == 0:
                run(["tmux", "new-session", "-d", "-s", session, "sh", "-lc", f"printf '%s' {json.dumps(message)}; sleep 3600"])
            else:
                run(["tmux", "new-window", "-t", session, "-n", role, "sh", "-lc", f"printf '%s' {json.dumps(message)}; sleep 3600"])
        if attach:
            print(f"tmux attach -t {session}")
        return "PASS"
    except Exception as exc:  # pragma: no cover - depends on local tmux
        (log_dir / "tmux_error.log").write_text(str(exc), encoding="utf-8")
        return "FAIL"


def run_smoke(args: argparse.Namespace) -> SmokeResult:
    before_status = git_status()
    keep = bool(args.keep)
    explicit_root = Path(args.target_root).expanduser() if args.target_root else None
    temp_root = explicit_root or Path(tempfile.mkdtemp(prefix="hldspec-smoke-"))
    temp_root.mkdir(parents=True, exist_ok=True)
    target = temp_root / "target"
    source_input = Path(args.source_hld).expanduser().resolve() if args.source_hld else default_fixture()
    source_hld = temp_root / "tiny_HLD.md"
    shutil.copyfile(source_input, source_hld)

    checks: list[Check] = []
    failed: str | None = None
    details = ""
    tmux_status = "NOT_REQUESTED"

    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.setdefault("PYTHONPYCACHEPREFIX", str(ROOT / ".tmp" / "pycache"))

    try:
        start_cmd = [
            sys.executable,
            str(ROOT / "scripts" / "hldspec_agent_session.py"),
            "start",
            "--source",
            str(source_hld),
            "--target",
            str(target),
            "--agent",
            "manual",
            "--comment",
            "production smoke scenario",
        ]
        start = run(start_cmd, env=env)
        checks.append(Check("hldspec_agent_session start exits 0", start.returncode == 0, start.stdout))
        if start.returncode != 0:
            raise AssertionError("hldspec_agent_session start failed")

        # Smoke 1 validates the source-package/mirror path without requiring a real SpecKit install.
        from hldspec import mediator_guidance as mg
        from hldspec.hld_source_package import build_source_package_content

        build = build_source_package_content(
            target,
            source_hld.read_text(encoding="utf-8"),
            hld_source_ref=str(source_hld),
            project_name="tiny-smoke",
            materialize_mirror=True,
        )
        checks.append(Check("source package build ok", build.ok, f"anchors={build.anchor_count} unsupported={build.unsupported_claims} marking={build.marking_errors}"))

        packet_path = target / ".hldspec" / "mediator" / "mediator_packet.json"
        start_prompt = target / "prompts" / "mediator" / "START_MEDIATOR.md"
        devin_prompt = target / "prompts" / "mediator" / "DEVIN_MEDIATOR_SKILL.md"
        direct_prompt = target / "prompts" / "mediator" / "CODEX_CLAUDE_MEDIATOR.md"
        check_file(checks, packet_path, "mediator packet exists")
        check_file(checks, start_prompt, "mediator start prompt exists")
        check_file(checks, devin_prompt, "mediator Devin prompt exists")
        check_file(checks, direct_prompt, "mediator direct prompt exists")

        packet = load_json(packet_path)
        checks.append(Check("mediator packet validates", not mg.validate_mediator_packet(packet), str(packet_path)))
        devin_text = devin_prompt.read_text(encoding="utf-8")
        direct_text = direct_prompt.read_text(encoding="utf-8")
        checks.append(Check("devin prompt has exact activation sentence", "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]" in devin_text))
        checks.append(Check("devin prompt has exact go", "`go`" in devin_text))
        checks.append(Check("devin prompt has exact stop", "`stop`" in devin_text))
        checks.append(Check("devin prompt rejects stop now", "Stop now is not a valid Devin control word." in devin_text))
        checks.append(Check("direct prompt documents stop now optional", "stop now is a direct-mode optional behavior only" in direct_text))
        checks.append(Check("direct prompt preserves mediator boundary", "Agent Mediator is not the Implementation Agent." in direct_text))
        for label, text in (("devin", devin_text), ("direct", direct_text)):
            checks.append(Check(
                f"{label} prompt references generated engineering_guidelines.md",
                "target/.hldspec/source_package/engineering_guidelines.md" in text
                and "if missing in an older/manual workspace, stop and reassess." in text,
                label,
            ))
            checks.append(Check(
                f"{label} prompt drops stale not-generated note",
                "HLDspec does not yet auto-generate it" not in text,
                label,
            ))

        source_package = target / ".hldspec" / "source_package"
        specify_source = target / ".specify" / "source"
        check_dir(checks, target / "targetHLD", "targetHLD exists")
        check_dir(checks, source_package, ".hldspec/source_package exists")
        check_dir(checks, specify_source, ".specify/source exists")

        required_source = [
            "HLD.md",
            "HLD.marked.md",
            "hld_reference_map.json",
            "speckit_single_spec_input.md",
            "engineering_guidelines.md",
            "source_package.json",
            "source_manifest.json",
            *SLICE_FILES,
        ]
        required_mirror = [
            "HLD.md",
            "HLD.marked.md",
            "hld_reference_map.json",
            "speckit_single_spec_input.md",
            "engineering_guidelines.md",
            *SLICE_FILES,
        ]
        for name in required_source:
            check_file(checks, source_package / name, f"source package file {name}")
        for name in required_mirror:
            check_file(checks, specify_source / name, f"mirror file {name}")

        guidelines = (source_package / "engineering_guidelines.md").read_text(encoding="utf-8")
        for card in (
            "architecture.business_logic_container",
            "testing.design_for_testability",
            "environment.stage_safe_testing",
            "environment.prod_test_separation",
        ):
            checks.append(Check(f"engineering_guidelines names {card}", card in guidelines))
        checks.append(Check(
            "engineering_guidelines is real selected guidance",
            "generated by HLDspec" in guidelines
            and "Do not silently overwrite the target constitution" in guidelines,
        ))

        marked = (source_package / "HLD.marked.md").read_text(encoding="utf-8")
        ref_map = load_json(source_package / "hld_reference_map.json")
        anchors = set(ref_map.get("anchors", {}).keys())
        spec_input = (source_package / "speckit_single_spec_input.md").read_text(encoding="utf-8")
        for anchor in EXPECTED_ANCHORS:
            checks.append(Check(f"marked HLD has {anchor}", f"<!-- ANCHOR: {anchor} -->" in marked))
            checks.append(Check(f"reference map has {anchor}", anchor in anchors))
            checks.append(Check(f"single spec input cites {anchor}", f"({anchor})" in spec_input))

        slices = load_json(source_package / "implementation_slices.json")
        names = {item.get("name") for item in slices.get("slices", [])}
        for required in ["FOUNDATION", "WALKING_SKELETON", "DOMAIN_MODEL", "CONTRACTS", "BUSINESS_LOGIC", "PERSISTENCE", "API", "CLI", "UI", "INTEGRATION_HARDENING"]:
            checks.append(Check(f"slice exists {required}", required in names))

        policy = (source_package / "implementation_slicing_policy.md").read_text(encoding="utf-8").lower()
        for phrase in ["run specify", "run plan", "run tasks", "run analyze", "controlled slices"]:
            checks.append(Check(f"policy mentions {phrase}", phrase in policy))

        if args.tmux:
            tmux_status = create_tmux_session(target, bool(args.attach))
            checks.append(Check("tmux optional status acceptable", tmux_status in {"PASS", "SKIP_TMUX"}, tmux_status))

    except Exception as exc:
        details = str(exc)

    after_status = git_status()
    repo_status_changed = before_status != after_status
    checks.append(Check("no repo pollution", not repo_status_changed, f"before={before_status!r} after={after_status!r}"))

    failed_check = None
    for check in checks:
        if not check.ok:
            failed_check = check.name
            if not details:
                details = check.details
            break
    result = "PASS" if failed_check is None else "FAIL"
    preserve = keep or result == "FAIL"
    if result == "PASS" and not keep and explicit_root is None:
        shutil.rmtree(temp_root, ignore_errors=True)
    return SmokeResult(
        result=result,
        source_hld=str(source_hld),
        target_dir=str(target),
        source_package=str(target / ".hldspec" / "source_package"),
        specify_source=str(target / ".specify" / "source"),
        tmux_status=tmux_status,
        checks=[asdict(c) for c in checks],
        failed_check=failed_check,
        details=details,
        preserved=preserve,
        repo_status_changed=repo_status_changed,
    )


def print_result(result: SmokeResult, json_mode: bool) -> None:
    passed = sum(1 for check in result.checks if check["ok"])
    failed = sum(1 for check in result.checks if not check["ok"])
    if json_mode:
        print("HLDSPEC_SMOKE_JSON: " + json.dumps(asdict(result), sort_keys=True))
    print(f"source_hld: {result.source_hld}")
    print(f"target_dir: {result.target_dir}")
    print(f"source_package: {result.source_package}")
    print(f"specify_source: {result.specify_source}")
    print(f"tmux: {result.tmux_status}")
    print(f"checks_passed: {passed}")
    print(f"checks_failed: {failed}")
    if result.failed_check:
        print(f"failed_check: {result.failed_check}")
        print(f"details: {result.details}")
        print("next_action: inspect target and rerun with --keep")
    print(f"HLDSPEC_SMOKE_RESULT: {result.result}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the deterministic HLDspec slice smoke scenario.")
    parser.add_argument("--keep", action="store_true", help="Preserve temp output on PASS.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON result line.")
    parser.add_argument("--tmux", action="store_true", help="Create optional visibility-only tmux session if available.")
    parser.add_argument("--attach", action="store_true", help="Print attach command for tmux session.")
    parser.add_argument("--target-root", default="", help="Explicit temp root. Target will be <target-root>/target.")
    parser.add_argument("--source-hld", default="", help="Optional source HLD fixture/path. Copied to <temp_root>/tiny_HLD.md.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_smoke(args)
    print_result(result, bool(args.json))
    return 0 if result.result == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
