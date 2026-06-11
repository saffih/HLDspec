"""Non-stop multi-bundle SpecKit drive loop ("SpecKit drive").

Each bundle prompt produced by `spec_bundle_prompts.py` is self-driving: it
runs the full SpecKit ritual for its specs, applies real RunSkeptic, and
reports a final `RunSkeptic status: PASS|ACTION|CONFLICT` plus an optional
"Reassessment request" when something needs a human decision. By design every
bundle prompt ends with "stop for human review before the next bundle".

This module is the loop around that: it runs bundles one at a time via an
injected runner and decides, after each one, whether to continue automatically
(`PASS`, no reassessment, verified on-disk progress) or stop and hand control
back to the human.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Optional

from hldspec.command_runner import CommandRunner
from hldspec.script_io import write_json_dict
from hldspec.speckit_execution_state import (
    next_action,
    select_execution_sync_dir,
    write_execution_state,
)

REPORT_JSON = "speckit_drive_loop_report.json"
REPORT_MD = "speckit_drive_loop_report.md"

_RUNSKEPTIC_RE = re.compile(r"RunSkeptic status:\s*(PASS|ACTION|CONFLICT)", re.IGNORECASE)

# Stop reasons that mean "a human needs to look at this" vs. "nothing more to
# automate right now". Used only for exit-code mapping in the CLI.
ATTENTION_REASONS = frozenset({"NEEDS_ATTENTION", "IMPLEMENT_GATE"})
CLEAN_STOP_REASONS = frozenset({"MAX_BUNDLES"})


def parse_bundle_report(stdout: str) -> dict[str, Any]:
    """Extract the bundle's final RunSkeptic status and reassessment flag."""
    matches = _RUNSKEPTIC_RE.findall(stdout or "")
    status = matches[-1].upper() if matches else "UNKNOWN"
    return {
        "runskeptic_status": status,
        "has_reassessment_request": "Reassessment request" in (stdout or ""),
    }


def _resume_key(state: dict[str, Any]) -> tuple:
    resume = state.get("resume")
    if not isinstance(resume, dict):
        return ()
    return (resume.get("bundle_id"), resume.get("feature_id"), resume.get("phase"))


def run_drive_loop(
    workspace: Path,
    speckit_root: Path,
    *,
    runner: Optional[Any] = None,
    agent_cmd: str = "claude",
    runtime: str = "claude",
    max_bundles: Optional[int] = None,
) -> dict[str, Any]:
    """Drive bundles in dependency order until something needs attention.

    Returns a summary dict and writes `speckit_drive_loop_report.{json,md}`
    into the execution sync dir.
    """
    runner = runner or CommandRunner()
    workspace = Path(workspace)
    speckit_root = Path(speckit_root)
    sync = select_execution_sync_dir(workspace, create=True)

    bundles_run: list[dict[str, Any]] = []
    stop_reason = "NO_BUNDLES"
    last_report: dict[str, Any] = {}
    state: dict[str, Any] = {}

    while True:
        state = write_execution_state(workspace, speckit_root)
        action = next_action(state, runtime=runtime)
        mode = action.get("mode", "")

        if mode == "NO_BUNDLES":
            stop_reason = "NO_BUNDLES"
            break
        if mode == "IMPLEMENT_GATE":
            stop_reason = "IMPLEMENT_GATE"
            break
        if mode == "DO_IT_ALL":
            # Unassessable execution state (e.g. SpecKit root missing). The
            # loop needs assessable progress to decide when to continue.
            stop_reason = "UNASSESSABLE"
            break
        if mode != "CONTINUE":
            stop_reason = mode or "UNKNOWN"
            break

        bundle_prompt = action.get("bundle_prompt")
        if not bundle_prompt:
            stop_reason = "NO_BUNDLE_PROMPT"
            break

        prompt_path = Path(bundle_prompt)
        if not prompt_path.is_absolute():
            prompt_path = workspace / prompt_path
        if not prompt_path.exists():
            stop_reason = "PROMPT_MISSING"
            last_report = {"prompt_path": str(prompt_path)}
            break

        prompt_text = prompt_path.read_text(encoding="utf-8")
        before_key = _resume_key(state)

        result = runner.run(
            [agent_cmd, "--print", "--dangerously-skip-permissions"],
            cwd=workspace,
            capture=True,
            input_text=prompt_text,
        )

        if result.returncode != 0:
            stop_reason = "INVOCATION_FAILED"
            last_report = {"returncode": result.returncode, "stderr": result.stderr[-2000:]}
            break

        report = parse_bundle_report(result.stdout)
        last_report = report

        if report["runskeptic_status"] != "PASS" or report["has_reassessment_request"]:
            stop_reason = "NEEDS_ATTENTION"
            break

        new_state = write_execution_state(workspace, speckit_root)
        after_key = _resume_key(new_state)
        if after_key == before_key:
            stop_reason = "NO_PROGRESS"
            state = new_state
            break

        bundles_run.append(
            {
                "bundle_prompt": bundle_prompt,
                "resume_before": list(before_key),
                "resume_after": list(after_key),
                "runskeptic_status": report["runskeptic_status"],
            }
        )
        state = new_state

        if max_bundles is not None and len(bundles_run) >= max_bundles:
            stop_reason = "MAX_BUNDLES"
            break

    summary = {
        "bundles_run": bundles_run,
        "stop_reason": stop_reason,
        "last_report": last_report,
        "final_state": state,
    }
    write_json_dict(sync / REPORT_JSON, summary)
    (sync / REPORT_MD).write_text(render_drive_loop_report(summary), encoding="utf-8")
    return summary


def render_drive_loop_report(summary: dict[str, Any]) -> str:
    bundles_run = summary.get("bundles_run", [])
    lines = [
        "# SpecKit Drive Loop Report",
        "",
        f"Stop reason: `{summary.get('stop_reason', '')}`",
        f"Bundles run: {len(bundles_run)}",
        "",
    ]
    for index, bundle in enumerate(bundles_run, start=1):
        lines.append(
            f"{index}. `{bundle.get('bundle_prompt', '')}` -> RunSkeptic {bundle.get('runskeptic_status', '')}"
        )
    last_report = summary.get("last_report") or {}
    if last_report:
        lines += ["", "## Last report", ""]
        for key, value in last_report.items():
            lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"
