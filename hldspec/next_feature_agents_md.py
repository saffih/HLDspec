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
    # Prefer the target-local read-only wrapper so the agent/human never needs
    # the HLDspec checkout path; fall back to the direct script form.
    command = ".hldspec/bin/run-card"
    fallback_command = f"python3 scripts/next_feature_readiness_report.py --target {target_path}"

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
        "source of truth. **The human drives the build loop; you navigate and",
        "challenge.** HLDspec is a navigator: it reports where you are and the single",
        "next safe decision/action. SpecKit generates (specs, plans, tasks, code) only",
        "when the human explicitly runs or approves the command. You never generate,",
        "execute, or merge on the user's behalf.",
        "",
        "## When the user asks \"SpecKit run card for this repo\" / \"what's next?\"",
        "",
        "1. Run the **target-local, read-only** run-card wrapper from inside this repo.",
        "   It reads this repo's evidence and prints the **SpecKit run card** -- the",
        "   only source of truth for *where we are*. It never writes:",
        "",
        f"   ```",
        f"   {command}",
        f"   ```",
        "",
        f"   If `{command}` is not present yet, install it with `hldspec refresh-target`",
        f"   (it creates the read-only wrapper), or fall back to:",
        "",
        f"   ```",
        f"   {fallback_command}",
        f"   ```",
        "",
        "2. Read the actual `specs/<branch>/spec.md`, `plan.md`, `tasks.md`, and",
        "   relevant code to confirm what the artifacts contain.",
        "3. Answer the user with a **decision card** (not a passive status dump) in",
        "   this shape:",
        "   - **Target repo / branch / dirty state:** from the run card.",
        "   - **Setup readiness:** the driver's `setup_readiness` -- whether",
        "     `.specify/` and `.specify/memory/` exist, any detected SpecKit init",
        "     commands, hooks status (`HOOKS_READY` / `HOOKS_MISSING` /",
        "     `HOOKS_UNKNOWN`), and the current branch/spec binding. Check this first.",
        "   - **Constitution status / refresh-target status:** the driver's",
        "     `constitution_exists` and `refresh_target_status`.",
        "   - **Phase:** the driver's current phase.",
        "   - **Evidence:** the repo/file/git facts behind that phase.",
        "   - **Missing / Gaps:** the driver's `missing_evidence`, plus any gap you",
        "     see between intent and what the repo actually contains.",
        "   - **Blockers / Risks:** the driver's `blockers` and `advisory_actions`,",
        "     plus risks you judge from the evidence.",
        "   - **Open questions:** anything ambiguous about the human's intent or the",
        "     repo state that you need answered before recommending a step.",
        "   - **Next safe human decision or action:** the single next thing -- which",
        "     **may be a question, not a command.** If intent or evidence is",
        "     ambiguous, stop and ask the human instead of guessing.",
        "   - **Exact command (if applicable):** the driver's `speckit_next_action`.",
        "     Propose it precisely, but do **not** run it unless the human explicitly",
        "     approves.",
        "   - **Recommended model:** the driver's `recommended_model`.",
        "   - **Why now:** the driver's `why_now`.",
        "   - **Do not run yet:** the driver's `do_not_run_yet`.",
        "   - **Report back:** the driver's `report_back` -- what to tell the agent",
        "     after the human acts.",
        "4. Drive **one step at a time.** After the human acts, re-run the run card",
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
        "- Do **not** run SpecKit init or install hooks on the user's behalf -- report",
        "  `setup_readiness` and tell the user the exact command if one was detected,",
        "  or that none is known if not. Setup is always user-run.",
        "- Do **not** commit, push, open a PR, or merge on the user's behalf.",
        "- Do **not** write specs, plans, tasks, or product code yourself. SpecKit does that.",
        "- **Propose, never auto-run.** Show the exact command, then wait for the",
        "  human to run or explicitly approve it. The human drives; you navigate.",
        "- **Ask when ambiguous.** If the human's intent or the repo evidence is",
        "  unclear, the next safe item is a *question*, not a command. Stop and ask.",
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
