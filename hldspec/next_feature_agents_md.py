"""Target-side agent-guidance bootstrap for Journey 3 (the ad-hoc next-feature flow).

Journey 3 happens **in the target repo**: the user and agent operate there, not
in HLDspec. Dropped into (or pasted from) the target repo, this tells any agent
how to guide a user through one feature end-to-end using the read-only
next-feature readiness driver (`next_feature_readiness.py`): read the target
repo's evidence-based "SpecKit run card" (phase, evidence, missing items,
blockers, single next safe action), report it back, and drive one safe step at
a time from `/speckit.specify` through `/speckit.implement` -- while never
running SpecKit, creating branches, committing, pushing, opening PRs, or
merging on the user's behalf.

This module only *builds* the bootstrap text and writes it under the HLDspec
control sync dir. It never runs SpecKit, edits product code, or performs git
operations.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from . import control_paths
from . import next_feature_readiness as nfr

BOOTSTRAP_FILE = "next_feature_AGENTS.md"

_TITLE = "# Next feature — agent guide (HLDspec)"


def build_next_feature_agents_md(target: Path | str, report: dict[str, Any] | None = None) -> str:
    """Build the target-side agent-guidance bootstrap markdown.

    `report` is an optional snapshot from
    `next_feature_readiness.build_next_feature_readiness_report`; when given, the
    current phase and next action are shown as a hint. The live driver remains
    the source of truth -- the agent must re-run it, not trust the snapshot.
    """
    target_path = Path(target).expanduser().resolve()
    command = f"python3 scripts/next_feature_readiness_report.py --target {target_path}"

    phase = (report or {}).get("phase")
    next_action = (report or {}).get("speckit_next_action")
    snapshot = ""
    if phase:
        snapshot = f"- Last known phase: `{phase}`" + (
            f" — next: `{next_action}`" if next_action else ""
        )

    lines = [
        _TITLE,
        "",
        "**You are operating in this target repo.** The user and you communicate and",
        "work here, not in the HLDspec repo -- this repo's files and git state are the",
        "source of truth. HLDspec is a navigator: it tells you where you are and the",
        "single next safe step. SpecKit generates (specs, plans, tasks, code). You",
        "never generate, execute, or merge on the user's behalf.",
        "",
        "## When the user asks \"SpecKit run card for this repo\" / \"what's next?\"",
        "",
        "1. Run the read-only readiness driver to read this target repo's state and",
        "   produce the **SpecKit run card** -- the only source of truth for *where we",
        "   are*:",
        "",
        f"   ```",
        f"   {command}",
        f"   ```",
        "",
        "2. Read the actual `specs/<branch>/spec.md`, `plan.md`, `tasks.md`, and",
        "   relevant code to confirm what the artifacts contain.",
        "3. Answer the user with a **SpecKit run card** in this shape:",
        "   - **Phase:** the driver's current phase.",
        "   - **Evidence:** the repo/file/git facts behind that phase.",
        "   - **Missing:** what the current phase needs that isn't there yet.",
        "   - **Blockers:** anything that stops progress.",
        "   - **Next safe action:** the single next command to run (the driver's",
        "     `speckit_next_action`), and why it is next.",
        "   - **Recommended model:** the driver's `recommended_model`.",
        "   - **Do not run yet:** the driver's `do_not_run_yet`.",
        "   - **Report back:** the driver's `report_back` -- what to tell the agent",
        "     after the user runs the next safe action.",
        "4. Drive **one step at a time.** After the user runs a step, re-run the driver",
        "   before suggesting the next one. Repeat until implementation is done.",
        "",
        "## The ritual chain you are driving through",
        "",
        "```",
        "CONSTITUTION → SPECIFY → CLARIFY → PLAN → CHECKLIST → TASKS → ANALYZE → IMPLEMENT",
        "```",
        "",
        "Full detail: `docs/SPECKIT_DRIVING_MODELS.md`. SpecKit owns branch + spec",
        "creation at `/speckit.specify`; you do not create or name branches.",
        "",
        "## Hard rules (never break these)",
        "",
        "- Infer phase **only** from this target repo's artifacts + git state, never",
        "  from chat history or memory.",
        "- Do **not** run SpecKit on the user's behalf -- tell the user the command and",
        "  wait. In Journey 3, the current target-side run-card loop is",
        "  guidance-only; no Journey 3 execution mode exists yet.",
        "- Do **not** create branches yourself. SpecKit owns branch creation through",
        "  `/speckit.specify`; you do not create or name branches manually.",
        "- Do **not** commit, push, open a PR, or merge on the user's behalf.",
        "- Do **not** write specs, plans, tasks, or product code yourself. SpecKit does that.",
        "- **Never** claim merge is allowed (`merge_allowed` is always `false`).",
        "- **Stop** and tell the user on any blocker, unresolved `[NEEDS CLARIFICATION]`,",
        "  or branch/spec binding conflict.",
        "",
    ]
    if snapshot:
        lines.extend(["## Snapshot at generation (re-run the driver for live state)", "", snapshot, ""])
    return "\n".join(lines)


def write_next_feature_agents_md(
    target: Path | str, report: dict[str, Any] | None = None
) -> dict[str, str]:
    """Write the bootstrap under the HLDspec control sync dir and return its path."""
    target_path = Path(target).expanduser().resolve()
    if report is None:
        report = nfr.build_next_feature_readiness_report(target_path)
    text = build_next_feature_agents_md(target_path, report)
    sync = control_paths.resolve_control_sync_dir(target_path, create=True)
    path = sync / BOOTSTRAP_FILE
    path.write_text(text, encoding="utf-8")
    return {"agents_md": str(path)}
