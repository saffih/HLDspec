#!/usr/bin/env python3
"""E2E Proof Harness v0 -- narrow proof that HLDspec can drive one tiny brownfield path.

This is NOT an execution channel, autonomous executor, new helper, or general
proof system. It runs a single bounded check against an isolated `/tmp/proof-target`
repo and reports PASS / ACTION / BLOCKED:

- `--smoke` : one raw, bounded `claude` invocation; PASS only if it exits 0, prints
  `SMOKE_OK`, and leaves the target clean (report files aside).
- `--live`  : double-gated (requires env `HLDSPEC_LIVE_E2E=1` *and* a passing smoke),
  then reuses the existing `hldspec.speckit_invoker.SpecKitInvoker` seam for one
  bounded IMPLEMENT invocation and verifies the acceptance criteria. It adds no new
  execution machinery -- it only calls existing code.

Safety: refuses any target other than `/tmp/proof-target` unless
`--allow-non-temp-target` is passed (tests use that to point at a TemporaryDirectory).
The subprocess timeout lives here, local to the harness, so a hanging/interactive
agent maps to BLOCKED rather than wedging forever -- the shared `CommandRunner` is
left untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

DEFAULT_TARGET = "/tmp/proof-target"
DEFAULT_HLD = "/tmp/proof-target-HLD.md"
REPORT_DIR_NAME = ".hldspec-proof"
PROOF_JSON = "proof_e2e_v0.json"
PROOF_MD = "proof_e2e_v0.md"
SMOKE_TOKEN = "SMOKE_OK"
SMOKE_SKILL = "speckit-specify"
LIVE_ENV_VAR = "HLDSPEC_LIVE_E2E"
DEFAULT_TIMEOUT = 120
EXCERPT_LIMIT = 2000

# The only code/test files the live brownfield change may touch (plus the report dir,
# which is always allowed). `subtract` is added in-place to existing files.
EXPECTED_LIVE_FILES = ("calc/core.py", "calc/__init__.py", "tests/test_core.py")

STATUS_PASS = "PASS"
STATUS_ACTION = "ACTION"
STATUS_BLOCKED = "BLOCKED"

# An agent runner: (cmd, cwd, timeout, env) -> {returncode, stdout, stderr,
# timed_out, not_found}. Injectable so unit tests never call real `claude`.
AgentRunner = Callable[..., dict[str, Any]]


def _excerpt(text: str | None) -> str:
    text = text or ""
    return text if len(text) <= EXCERPT_LIMIT else text[:EXCERPT_LIMIT] + "\n...[truncated]"


def default_agent_runner(cmd: list[str], *, cwd: str | None, timeout: int, env: dict | None) -> dict[str, Any]:
    """Run a real command with a hard timeout. Maps hang/missing to structured fields."""
    try:
        proc = subprocess.run(
            cmd, cwd=cwd, env=env, text=True, capture_output=True, timeout=timeout
        )
        return {
            "returncode": proc.returncode,
            "stdout": proc.stdout or "",
            "stderr": proc.stderr or "",
            "timed_out": False,
            "not_found": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": None,
            "stdout": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr": ((exc.stderr or "") if isinstance(exc.stderr, str) else "")
            + f"\n[timed out after {timeout}s]",
            "timed_out": True,
            "not_found": False,
        }
    except FileNotFoundError as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": f"command not found: {exc}",
            "timed_out": False,
            "not_found": True,
        }


# --- git helpers (always real; deterministic and available, never faked) -------------

def _git(target: Path, *args: str) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            ["git", "-C", str(target), *args],
            text=True,
            capture_output=True,
            timeout=60,
        )
        return {"returncode": proc.returncode, "stdout": proc.stdout or "", "stderr": proc.stderr or ""}
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {"returncode": 1, "stdout": "", "stderr": str(exc)}


def is_git_repo(target: Path) -> bool:
    res = _git(target, "rev-parse", "--is-inside-work-tree")
    return res["returncode"] == 0 and res["stdout"].strip() == "true"


def git_status_porcelain(target: Path) -> str:
    return _git(target, "status", "--porcelain").get("stdout", "")


def changed_files(target: Path) -> list[str]:
    files: list[str] = []
    for line in git_status_porcelain(target).splitlines():
        if not line.strip():
            continue
        path = line[3:] if len(line) > 3 else line.strip()
        if " -> " in path:  # rename
            path = path.split(" -> ", 1)[1]
        files.append(path.strip())
    return files


# --- bounded diff --------------------------------------------------------------------

def check_bounded_diff(changed: list[str], expected: list[str] | tuple[str, ...]) -> dict[str, Any]:
    """Files in the report dir are always allowed; everything else must be in `expected`."""
    expected_set = set(expected)
    unexpected: list[str] = []
    for raw in changed:
        path = raw.strip()
        if not path:
            continue
        first = path.split("/", 1)[0]
        if first == REPORT_DIR_NAME:
            continue
        if path not in expected_set:
            unexpected.append(path)
    return {"ok": not unexpected, "unexpected": sorted(unexpected), "expected": sorted(expected_set)}


# --- report scaffolding --------------------------------------------------------------

def _new_report(target: Path, hld: Path, feature: str, mode: str, model: str | None) -> dict[str, Any]:
    return {
        "tool": "proof_e2e_v0",
        "version": 0,
        "mode": mode,
        "feature": feature,
        "target": str(target),
        "hld": str(hld),
        "model": model,
        "status": None,
        "command": None,
        "stdout_excerpt": "",
        "stderr_excerpt": "",
        "expected_artifacts": [],
        "observed_artifacts": [],
        "git_status_before": None,
        "git_status_after": None,
        "pytest": None,
        "bounded_diff": None,
        "blocker": None,
        "notes": [],
    }


def _render_md(report: dict[str, Any]) -> str:
    lines = [
        f"# E2E Proof Harness v0 -- {report['status']}",
        "",
        f"- mode: `{report['mode']}`",
        f"- feature: `{report['feature']}`",
        f"- target: `{report['target']}`",
        f"- hld: `{report['hld']}`",
        f"- model: `{report['model']}`",
        f"- command: `{report['command']}`",
    ]
    if report.get("blocker"):
        lines += ["", f"**Blocker:** {report['blocker']}"]
    lines += [
        "",
        "## Artifacts",
        f"- expected: {report['expected_artifacts']}",
        f"- observed: {report['observed_artifacts']}",
        "",
        "## Git status",
        f"- before: `{(report['git_status_before'] or '').strip() or '(clean)'}`",
        f"- after: `{(report['git_status_after'] or '').strip() or '(clean)'}`",
        "",
        "## Pytest",
        f"```\n{report['pytest']}\n```",
        "",
        "## Bounded diff",
        f"```\n{json.dumps(report['bounded_diff'], indent=2)}\n```",
        "",
        "## stdout (excerpt)",
        f"```\n{report['stdout_excerpt']}\n```",
        "",
        "## stderr (excerpt)",
        f"```\n{report['stderr_excerpt']}\n```",
    ]
    if report.get("notes"):
        lines += ["", "## Notes"] + [f"- {n}" for n in report["notes"]]
    return "\n".join(lines) + "\n"


def write_report(target: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    rdir = Path(target) / REPORT_DIR_NAME
    rdir.mkdir(parents=True, exist_ok=True)
    json_path = rdir / PROOF_JSON
    md_path = rdir / PROOF_MD
    json_path.write_text(json.dumps(report, indent=2, default=str))
    md_path.write_text(_render_md(report))
    return json_path, md_path


def _finalize(report: dict[str, Any], status: str, *, blocker: str | None = None, write: bool = False) -> dict[str, Any]:
    report["status"] = status
    if blocker:
        report["blocker"] = blocker
    if write:
        write_report(Path(report["target"]), report)
    return report


# --- pytest --------------------------------------------------------------------------

def run_pytest(target: Path, timeout: int = DEFAULT_TIMEOUT) -> dict[str, Any]:
    res = default_agent_runner(
        ["python3", "-m", "pytest", "tests/", "-q"], cwd=str(target), timeout=timeout, env=dict(os.environ)
    )
    return {"returncode": res["returncode"], "stdout": _excerpt(res["stdout"]), "stderr": _excerpt(res["stderr"])}


# --- core flow -----------------------------------------------------------------------

def run_proof(
    target: str | Path,
    hld: str | Path,
    feature: str,
    *,
    mode: str,
    model: str | None = None,
    allow_non_temp: bool = False,
    timeout: int = DEFAULT_TIMEOUT,
    runner: AgentRunner | None = None,
    env: dict | None = None,
) -> dict[str, Any]:
    """Run one proof pass. Pure orchestration over git + an injectable agent runner."""
    target = Path(target)
    hld = Path(hld)
    runner = runner or default_agent_runner
    env = dict(os.environ if env is None else env)
    report = _new_report(target, hld, feature, mode, model)

    # 1. Target location guard (report not written into a non-approved target).
    if not allow_non_temp and os.path.abspath(str(target)) != DEFAULT_TARGET:
        return _finalize(
            report,
            STATUS_BLOCKED,
            blocker=f"target {target} is not {DEFAULT_TARGET}; pass --allow-non-temp-target to override",
        )

    # 2. Target must exist and be a git repo (cannot write report into a non-repo).
    if not target.exists() or not target.is_dir():
        return _finalize(report, STATUS_BLOCKED, blocker=f"target does not exist: {target}")
    if not is_git_repo(target):
        return _finalize(report, STATUS_BLOCKED, blocker=f"target is not a git repo: {target}")

    # Snapshot cleanliness BEFORE writing any report files into the target.
    report["git_status_before"] = git_status_porcelain(target)
    if report["git_status_before"].strip():
        return _finalize(report, STATUS_BLOCKED, blocker="target is not clean before proof", write=True)
    if not hld.exists():
        return _finalize(report, STATUS_BLOCKED, blocker=f"HLD not found: {hld}", write=True)

    if mode == "smoke":
        return _run_smoke(report, target, model, timeout, runner, env)
    if mode == "live":
        return _run_live(report, target, hld, feature, model, timeout, env)
    return _finalize(report, STATUS_BLOCKED, blocker=f"unknown mode: {mode}", write=True)


def _run_smoke(report, target, model, timeout, runner, env) -> dict[str, Any]:
    cmd = ["claude", "--print", "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]
    cmd.append(f"/{SMOKE_SKILL} say only {SMOKE_TOKEN}")
    report["command"] = cmd
    report["expected_artifacts"] = ["(none -- smoke must not mutate the target)"]

    res = runner(cmd, cwd=str(target), timeout=timeout, env=env)
    report["stdout_excerpt"] = _excerpt(res.get("stdout"))
    report["stderr_excerpt"] = _excerpt(res.get("stderr"))
    report["git_status_after"] = git_status_porcelain(target)
    diff = check_bounded_diff(changed_files(target), [])
    report["bounded_diff"] = diff
    report["observed_artifacts"] = diff["unexpected"]

    if res.get("not_found"):
        return _finalize(report, STATUS_BLOCKED, blocker="claude command not found", write=True)
    if res.get("timed_out"):
        return _finalize(report, STATUS_BLOCKED, blocker=f"smoke timed out after {timeout}s (interactive/hang)", write=True)

    token_ok = SMOKE_TOKEN in (res.get("stdout") or "")
    exit_ok = res.get("returncode") == 0
    if exit_ok and token_ok and diff["ok"]:
        return _finalize(report, STATUS_PASS, write=True)

    reasons = []
    if not exit_ok:
        reasons.append(f"exit code {res.get('returncode')}")
    if not token_ok:
        reasons.append(f"missing {SMOKE_TOKEN} in stdout (/speckit-* likely unavailable)")
    if not diff["ok"]:
        reasons.append(f"unexpected target mutation: {diff['unexpected']}")
    return _finalize(report, STATUS_BLOCKED, blocker="; ".join(reasons), write=True)


def _run_live(report, target, hld, feature, model, timeout, env) -> dict[str, Any]:
    # Double gate: env var, then a passing smoke.
    if env.get(LIVE_ENV_VAR) != "1":
        return _finalize(report, STATUS_BLOCKED, blocker=f"{LIVE_ENV_VAR}=1 required for --live; refusing", write=True)

    smoke = run_proof(target, hld, feature, mode="smoke", model=model, allow_non_temp=True, timeout=timeout, env=env)
    if smoke["status"] != STATUS_PASS:
        report["notes"].append("live requires a passing smoke first")
        report["stdout_excerpt"] = smoke["stdout_excerpt"]
        report["stderr_excerpt"] = smoke["stderr_excerpt"]
        return _finalize(report, STATUS_BLOCKED, blocker=f"smoke did not PASS: {smoke.get('blocker')}", write=True)

    # Reuse the existing SpecKitInvoker seam; no new execution machinery is added.
    try:
        from hldspec.speckit_invoker import SpecKitInvoker
    except Exception as exc:  # pragma: no cover - import-time only
        return _finalize(report, STATUS_ACTION, blocker=f"need minimal callable proof seam for existing SpecKitInvoker: {exc}", write=True)

    prompt = (
        "Apply this brownfield change to the calc package and nothing else: add "
        "`subtract(a, b)` returning a - b to calc/core.py, expose `subtract` from "
        "calc/__init__.py, add `test_subtract` to tests/test_core.py. Do not change "
        "`add`, do not remove `test_add`, no CLI, no I/O, no dependencies."
    )
    bounded = _BoundedRunner(timeout)
    invoker = SpecKitInvoker(target, runner=bounded, route_models=False)
    if model:
        invoker.phase_models = {"IMPLEMENT": model}
        invoker.route_models = True
    result = invoker.invoke("IMPLEMENT", prompt)
    report["command"] = list(invoker._command(  # noqa: SLF001 - reusing existing builder for the receipt
        "speckit-implement", prompt, model
    ))
    report["stdout_excerpt"] = _excerpt(result.stdout)
    report["stderr_excerpt"] = _excerpt(result.stderr)
    report["git_status_after"] = git_status_porcelain(target)

    if bounded.timed_out:
        return _finalize(report, STATUS_BLOCKED, blocker=f"live invocation timed out after {timeout}s", write=True)
    if not result.ok:
        return _finalize(report, STATUS_BLOCKED, blocker=f"live invocation failed (rc={result.returncode})", write=True)

    return _verify_live(report, target, timeout)


def _verify_live(report, target, timeout) -> dict[str, Any]:
    diff = check_bounded_diff(changed_files(target), EXPECTED_LIVE_FILES)
    report["bounded_diff"] = diff
    report["expected_artifacts"] = list(EXPECTED_LIVE_FILES)
    report["observed_artifacts"] = [f for f in changed_files(target) if f.split("/", 1)[0] != REPORT_DIR_NAME]

    core = (target / "calc" / "core.py").read_text() if (target / "calc" / "core.py").exists() else ""
    init = (target / "calc" / "__init__.py").read_text() if (target / "calc" / "__init__.py").exists() else ""
    tests = (target / "tests" / "test_core.py").read_text() if (target / "tests" / "test_core.py").exists() else ""

    checks = {
        "subtract_in_core": "def subtract" in core,
        "subtract_exposed": "subtract" in init,
        "test_subtract_added": "def test_subtract" in tests,
        "add_preserved": "def add" in core,
        "test_add_preserved": "def test_add" in tests,
    }
    report["notes"].append(f"acceptance checks: {checks}")

    pytest_res = run_pytest(target, timeout=timeout)
    report["pytest"] = pytest_res
    pytest_ok = pytest_res["returncode"] == 0

    if all(checks.values()) and pytest_ok and diff["ok"]:
        return _finalize(report, STATUS_PASS, write=True)
    # Live ran but the outcome is incomplete -> ACTION (not a hard block).
    missing = [k for k, v in checks.items() if not v]
    blocker_bits = []
    if missing:
        blocker_bits.append(f"unmet acceptance: {missing}")
    if not pytest_ok:
        blocker_bits.append(f"pytest rc={pytest_res['returncode']}")
    if not diff["ok"]:
        blocker_bits.append(f"diff out of bounds: {diff['unexpected']}")
    return _finalize(report, STATUS_ACTION, blocker="; ".join(blocker_bits), write=True)


class _BoundedRunner:
    """A `CommandRunner`-shaped object with a hard per-call timeout, local to the
    harness. Reuses `CommandResult`; a timeout maps to rc=124 so the seam keeps working
    without modifying the shared runner."""

    def __init__(self, timeout: int) -> None:
        self.timeout = timeout
        self.timed_out = False

    def run(self, command, *, cwd=None, capture=False, input_text=None):
        from hldspec.command_runner import CommandResult

        try:
            proc = subprocess.run(
                list(command),
                cwd=cwd,
                text=True,
                input=input_text,
                stdout=subprocess.PIPE if capture else None,
                stderr=subprocess.PIPE if capture else None,
                check=False,
                timeout=self.timeout,
            )
            return CommandResult(proc.returncode, tuple(str(c) for c in command), proc.stdout or "", proc.stderr or "")
        except subprocess.TimeoutExpired as exc:
            self.timed_out = True
            err = exc.stderr if isinstance(exc.stderr, str) else ""
            return CommandResult(124, tuple(str(c) for c in command), "", err + f"\n[timed out after {self.timeout}s]")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="E2E Proof Harness v0 (smoke / live).")
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--hld", default=DEFAULT_HLD)
    parser.add_argument("--feature", default="C2")
    parser.add_argument("--model", default=None)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("--allow-non-temp-target", action="store_true")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)

    mode = "live" if args.live else "smoke"
    report = run_proof(
        args.target,
        args.hld,
        args.feature,
        mode=mode,
        model=args.model,
        allow_non_temp=args.allow_non_temp_target,
        timeout=args.timeout,
    )
    print(f"status: {report['status']}")
    if report.get("blocker"):
        print(f"blocker: {report['blocker']}")
    print(f"report: {Path(report['target']) / REPORT_DIR_NAME / PROOF_JSON}")
    return 0 if report["status"] == STATUS_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
