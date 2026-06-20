#!/usr/bin/env python3
"""Proof Target SpecKit Readiness Doctor (read-only).

Classifies *why* the E2E proof target can or cannot honestly run ``/speckit.*``
commands, and *proposes* (never performs) the human-owned remediation.

Where do ``/speckit.*`` commands come from? -> a real **SpecKit init** in the
target: ``specify init`` / ``spec-kit init`` / ``uvx --from <spec-kit> spec-kit
init`` (see hldspec/speckit_workspace.py), which materializes ``.specify/`` and the
project-local ``/speckit.*`` commands. They are NOT global Claude skills and NOT
HLDspec-vendored (HLDspec vendors only the read-only run-card runtime).

This doctor never installs skills, never initializes SpecKit, and never mutates the
target. Per hldspec/helper_registry.py the ``speckit`` helper is GUIDE_ONLY/
PROPOSE_COMMAND and is explicitly forbidden to "initialize SpecKit ... on the
human's behalf", so ``--prepare-proof-target`` only *proposes* the sandbox-scoped
init command (and refuses any non-temp target); it does not run it.

Scope note: init/git prerequisite classification already lives in
hldspec/speckit_readiness.py::build_speckit_init_prereq_report. This script's novel
contribution is the *claude ``/speckit.*`` skill-availability smoke* for the proof
target -- it reuses init detection rather than reimplementing it.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec import speckit_workspace as sw  # noqa: E402  (after sys.path setup)

# Reuse the e2e harness's smoke semantics so there is one source of truth for token
# confirmation, unavailability markers, and the bounded agent runner.
_E2E_PATH = Path(__file__).resolve().parent / "proof_e2e_v0.py"
_spec = importlib.util.spec_from_file_location("proof_e2e_v0", _E2E_PATH)
assert _spec and _spec.loader
e2e = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(e2e)

DEFAULT_TARGET = "/tmp/proof-target"
DEFAULT_TIMEOUT = 120

STATUS_CLAUDE_MISSING = "CLAUDE_MISSING"
STATUS_MODEL_REJECTED = "MODEL_REJECTED"
STATUS_UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
STATUS_SKILL_UNAVAILABLE = "SKILL_UNAVAILABLE"
STATUS_TARGET_NOT_SPECKIT_READY = "TARGET_NOT_SPECKIT_READY"
STATUS_SMOKE_PASS = "SMOKE_PASS"
STATUS_TIMEOUT = "TIMEOUT"  # not in the required set, but an honest distinct outcome

# Phrases claude emits when the --model is bad. Confirmed live against claude 2.1.x:
# "There's an issue with the selected model (...). It may not exist or you may not
# have access to it." Plus common fallbacks.
MODEL_REJECTED_MARKERS = (
    "issue with the selected model",
    "may not exist or you may not have access",
    "invalid model",
    "unknown model",
    "model not found",
    "no such model",
)

REPORT_DIR_NAME = ".hldspec-proof"
REPORT_JSON = "proof_speckit_readiness.json"
REPORT_MD = "proof_speckit_readiness.md"


def _specify_dir_present(target: Path) -> bool:
    return (target / ".specify").is_dir()


def _under_temp_root(path: Path) -> bool:
    ap = Path(os.path.realpath(os.path.abspath(path)))
    for root in (Path("/tmp"), Path(os.path.realpath("/tmp"))):
        try:
            if ap.relative_to(root).parts:
                return True
        except ValueError:
            continue
    # Also honor the OS temp dir (e.g. macOS /private/var/folders) for hermetic tests.
    import tempfile

    tmp_root = Path(os.path.realpath(tempfile.gettempdir()))
    try:
        return bool(ap.relative_to(tmp_root).parts)
    except ValueError:
        return False


def _remediation(status: str, target: Path, init_labels: list[str], smoke_command: str) -> str:
    if status == STATUS_CLAUDE_MISSING:
        return "Install/enable the `claude` CLI on PATH, then rerun readiness."
    if status == STATUS_MODEL_REJECTED:
        return "Pass a valid --model (the selected model was rejected by claude)."
    if status == STATUS_UNKNOWN_COMMAND:
        return f"Command syntax rejected; try the alternate spelling {e2e.alternate_spelling(smoke_command)!r}."
    if status == STATUS_TARGET_NOT_SPECKIT_READY:
        have = f"detected init tools: {init_labels}" if init_labels else "no SpecKit init tool detected (specify/spec-kit/uvx)"
        return (
            f"Target has no .specify/; run a real SpecKit init in {target} to materialize "
            f"/speckit.* commands ({have}). HLDspec will not run it for you "
            f"(speckit helper is GUIDE_ONLY/PROPOSE_COMMAND); see --prepare-proof-target."
        )
    if status == STATUS_SKILL_UNAVAILABLE:
        return ".specify/ exists but /speckit.* is still not exposed; verify the SpecKit init created the project-local commands."
    if status == STATUS_TIMEOUT:
        return "The smoke command did not return in time (possible interactive prompt or hang)."
    if status == STATUS_SMOKE_PASS:
        return "Target can run /speckit.*; proceed to the bounded smoke / live proof."
    return "Unclassified; inspect the smoke output."


def classify_readiness(
    target: str | Path,
    *,
    model: str | None = None,
    smoke_command: str | None = None,
    timeout: int = DEFAULT_TIMEOUT,
    runner: Callable[..., dict[str, Any]] | None = None,
    which: Callable[[str], str | None] | None = None,
    env: dict | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Classify proof-target SpecKit readiness. Pure over injectable runner/which.

    Precedence mirrors the e2e harness: an unavailability marker BLOCKS *before* the
    SMOKE_OK token, so a hollow completion ("...not available...\\nSMOKE_OK") can never
    be mis-read as SMOKE_PASS.
    """
    target = Path(target)
    runner = runner or e2e.default_agent_runner
    which = which or shutil.which
    env = dict(os.environ if env is None else env)
    smoke_command = smoke_command or e2e.DEFAULT_SMOKE_COMMAND

    init_cmds = sw.detect_init_commands(which=which)
    init_labels = [c.label for c in init_cmds]
    specify_present = target.is_dir() and _specify_dir_present(target)
    claude_path = which("claude")

    report: dict[str, Any] = {
        "tool": "proof_speckit_readiness",
        "version": 0,
        "target": str(target),
        "model": model,
        "smoke_command": smoke_command,
        "claude_available": bool(claude_path),
        "specify_dir_present": specify_present,
        "speckit_init_tooling": init_labels,
        "speckit_skills_origin": "SpecKit init output (specify/spec-kit/uvx init -> .specify/ + project-local /speckit.* commands)",
        "command": None,
        "stdout_excerpt": "",
        "stderr_excerpt": "",
        "status": None,
        "remediation": None,
        "notes": [],
    }

    def finish(status: str) -> dict[str, Any]:
        report["status"] = status
        report["remediation"] = _remediation(status, target, init_labels, smoke_command)
        if write and target.is_dir():
            _write_report(target, report)
        return report

    if not claude_path:
        return finish(STATUS_CLAUDE_MISSING)

    cmd = ["claude", "--print", "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]
    cmd.append(smoke_command)
    report["command"] = cmd

    res = runner(cmd, cwd=str(target) if target.is_dir() else None, timeout=timeout, env=env)
    report["stdout_excerpt"] = e2e._excerpt(res.get("stdout"))
    report["stderr_excerpt"] = e2e._excerpt(res.get("stderr"))
    combined = f"{res.get('stdout') or ''}\n{res.get('stderr') or ''}".lower()

    if res.get("not_found"):
        return finish(STATUS_CLAUDE_MISSING)
    if res.get("timed_out"):
        return finish(STATUS_TIMEOUT)
    if any(m in combined for m in MODEL_REJECTED_MARKERS):
        return finish(STATUS_MODEL_REJECTED)
    if "unknown command" in combined:
        report["notes"].append(f"alternate spelling to try: {e2e.alternate_spelling(smoke_command)}")
        return finish(STATUS_UNKNOWN_COMMAND)

    # Unavailability marker BLOCKS before the token (hollow-completion guard).
    if any(m in combined for m in e2e.SKILL_UNAVAILABLE_MARKERS):
        return finish(STATUS_TARGET_NOT_SPECKIT_READY if not specify_present else STATUS_SKILL_UNAVAILABLE)

    if e2e.smoke_confirmed(res.get("stdout") or "") and res.get("returncode") == 0:
        return finish(STATUS_SMOKE_PASS)

    # Not confirmed and no explicit marker: root-cause by structure.
    return finish(STATUS_TARGET_NOT_SPECKIT_READY if not specify_present else STATUS_SKILL_UNAVAILABLE)


def propose_prepare(target: str | Path, *, which: Callable[[str], str | None] | None = None) -> dict[str, Any]:
    """PROPOSE (never run) a sandbox-scoped SpecKit init. Refuses any non-temp target.

    HLDspec does not initialize SpecKit on the human's behalf (helper_registry speckit
    forbidden_actions); this only hands back the exact command to run in /tmp.
    """
    target = Path(target)
    if not _under_temp_root(target):
        raise ValueError(
            f"refusing to prepare a non-temp target: {target}. Only a target under a "
            f"temp root (e.g. {DEFAULT_TARGET}) may be prepared."
        )
    which = which or shutil.which
    init_cmds = sw.detect_init_commands(which=which)
    if not init_cmds:
        return {
            "prepared": False,
            "proposed_command": None,
            "run_in": str(target),
            "note": "PROPOSAL ONLY -- not executed. No SpecKit init tool (specify/spec-kit/uvx) detected to propose.",
        }
    return {
        "prepared": False,  # always: this function never executes anything
        "proposed_command": list(init_cmds[0].argv),
        "run_in": str(target),
        "note": (
            "PROPOSAL ONLY -- not executed. Run this yourself in the target to "
            "materialize .specify/ and the /speckit.* commands. HLDspec will not "
            "initialize SpecKit on your behalf (speckit helper is GUIDE_ONLY/"
            "PROPOSE_COMMAND)."
        ),
    }


def _render_md(report: dict[str, Any]) -> str:
    lines = [
        f"# Proof Target SpecKit Readiness -- {report['status']}",
        "",
        f"- target: `{report['target']}`",
        f"- model: `{report['model']}`",
        f"- claude available: `{report['claude_available']}`",
        f"- .specify/ present: `{report['specify_dir_present']}`",
        f"- SpecKit init tooling: `{report['speckit_init_tooling']}`",
        f"- /speckit.* origin: {report['speckit_skills_origin']}",
        f"- smoke command: `{report['smoke_command']}`",
        f"- command: `{report['command']}`",
        "",
        f"**Remediation:** {report['remediation']}",
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


def _write_report(target: Path, report: dict[str, Any]) -> tuple[Path, Path]:
    rdir = Path(target) / REPORT_DIR_NAME
    rdir.mkdir(parents=True, exist_ok=True)
    json_path = rdir / REPORT_JSON
    md_path = rdir / REPORT_MD
    json_path.write_text(json.dumps(report, indent=2, default=str))
    md_path.write_text(_render_md(report))
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Proof target SpecKit readiness doctor (read-only).")
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--model", default=None)
    parser.add_argument("--smoke-command", default=None)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument(
        "--prepare-proof-target",
        action="store_true",
        help="PROPOSE (never run) a sandbox-scoped SpecKit init; refuses non-temp targets.",
    )
    args = parser.parse_args(argv)

    report = classify_readiness(
        args.target, model=args.model, smoke_command=args.smoke_command, timeout=args.timeout
    )
    print(f"status: {report['status']}")
    print(f"remediation: {report['remediation']}")
    print(f"report: {Path(report['target']) / REPORT_DIR_NAME / REPORT_JSON}")

    if args.prepare_proof_target:
        try:
            proposal = propose_prepare(args.target)
        except ValueError as exc:
            print(f"prepare refused: {exc}")
            return 1
        print(f"prepare (PROPOSAL ONLY, not executed): {proposal['proposed_command']} (run in {proposal['run_in']})")
        print(f"  {proposal['note']}")

    return 0 if report["status"] == STATUS_SMOKE_PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
