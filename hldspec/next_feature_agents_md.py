"""Target-side agent-guidance bootstrap for the ad-hoc next-feature flow.

Dropped into (or pasted from) a target repo, this tells any agent how to guide a
user through one feature end-to-end using the read-only next-feature readiness
driver (`next_feature_readiness.py`): ask "what's next?", report what's done /
missing / next, and drive one safe step at a time from `/speckit.specify`
through `/speckit.implement` -- while never running SpecKit, committing,
pushing, opening PRs, or merging on the user's behalf.

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
        "You are guiding the user through **one feature**, end to end, in this repo.",
        "HLDspec navigates (tells you where you are and the next safe step); SpecKit",
        "generates (specs, plans, tasks, code). You never generate or merge.",
        "",
        "## When the user asks \"what's next?\" / \"drive me through the feature\"",
        "",
        f"1. Run the read-only readiness driver as the source of truth for *where we are*:",
        "",
        f"   ```",
        f"   {command}",
        f"   ```",
        "",
        "2. Read the actual `specs/<branch>/spec.md`, `plan.md`, `tasks.md`, and",
        "   relevant code to confirm what the artifacts contain.",
        "3. Report back in this shape:",
        "   - **Done:** what is verified present and coherent.",
        "   - **Missing:** what the current phase needs that isn't there yet.",
        "   - **Next:** the single next command to run (the driver's `speckit_next_action`).",
        "   - **Blockers:** anything that stops progress.",
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
        "- Infer phase **only** from repo artifacts + git state, never from chat history.",
        "- Do **not** run SpecKit, commit, push, open a PR, or merge on the user's behalf —",
        "  tell the user the command and wait.",
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
