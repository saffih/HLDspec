#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())
    text = text.strip("-._")
    return text or "hld"


def default_workspace(source_hld: Path) -> Path:
    return Path("/tmp") / f"hldspec-agent-{safe_name(source_hld.stem)}"


def normalize_path(path: Path) -> Path:
    try:
        return path.resolve()
    except Exception:
        return path.absolute()


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def find_sync(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    for sync in (direct, nested):
        if (sync / "hldspec_state.json").exists():
            return sync
    return direct


def prepare_workspace(source_hld: Path, workspace: Path, *, force: bool = False) -> dict[str, Any]:
    workspace.mkdir(parents=True, exist_ok=True)
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)

    raw_copy = workspace / "HLD.raw.md"
    working_copy = workspace / "HLD.md"

    if force or not raw_copy.exists():
        shutil.copyfile(source_hld, raw_copy)
    if force or not working_copy.exists():
        shutil.copyfile(source_hld, working_copy)

    return {
        "workspace": str(workspace),
        "sync_dir": str(sync),
        "raw_copy": str(raw_copy),
        "working_copy": str(working_copy),
        "source_sha256": sha256(source_hld),
    }


def current_state(workspace: Path) -> dict[str, Any]:
    sync = find_sync(workspace)
    state = load_json(sync / "hldspec_state.json")
    if not state:
        return {
            "current_stage": "NOT_STARTED",
            "current_checkpoint": "",
            "controlling_artifacts": [],
            "blocking_questions": [],
            "state_path": "",
            "sync_dir": str(sync),
        }
    return {
        "current_stage": state.get("current_stage", "UNKNOWN"),
        "current_checkpoint": state.get("current_checkpoint", ""),
        "controlling_artifacts": state.get("controlling_artifacts", []),
        "blocking_questions": state.get("blocking_questions", []),
        "state_path": str(sync / "hldspec_state.json"),
        "sync_dir": str(sync),
    }


def allowed_commands(repo: Path, source_hld: Path, workspace: Path, state: dict[str, Any]) -> list[str]:
    stage = str(state.get("current_stage", "NOT_STARTED"))
    commands = [f"cd {repo}"]

    if stage == "NOT_STARTED":
        commands.append(f"bash scripts/hldspec_smoke.sh {source_hld} {workspace} --force")
    else:
        commands.append(f"bash scripts/hldspec_status.sh {workspace} {source_hld}")

    if stage in {"CONVERSION_CHECKPOINT", "SPEC_BUILD_PLAN_CHECKPOINT"} or state.get("blocking_questions"):
        commands.append(f"bash scripts/hldspec_question_guide.sh {workspace}")

    if stage == "CONVERSION_READY_TO_APPLY":
        commands.append(f"bash scripts/first_run_readonly.sh {workspace / 'HLD.md'} {workspace / 'firstrun'} --force")

    return commands


def next_action(state: dict[str, Any]) -> str:
    stage = str(state.get("current_stage", "NOT_STARTED"))
    if stage == "NOT_STARTED":
        return "Run the HLDspec smoke/prework tools internally, then inspect the generated state."
    if stage == "CONVERSION_CHECKPOINT":
        return "Run the question guide, explain one conversion question at a time, and ask the human to choose allowed split/keep options."
    if stage == "CONVERSION_READY_TO_APPLY":
        return "Convert only the workspace HLD copy, then rerun first_readonly on the converted workspace HLD."
    if stage == "SPEC_BUILD_PLAN_CHECKPOINT":
        return "Run the question guide for spec-build-plan questions and ask the human only required checkpoint questions."
    if stage == "SPECKIT_PREWORK_APPROVAL_GATE":
        return "Present prework/orchestration artifacts for review. Do not invoke real SpecKit."
    return "Inspect hldspec_state.md and follow the listed next allowed actions."


def minimal_trigger(source_hld: Path, workspace: Path) -> str:
    return f"HLDspec {source_hld} --workspace {workspace}"


def build_context(source_hld: Path, workspace: Path, repo: Path, *, force: bool = False) -> dict[str, Any]:
    source_hld = normalize_path(source_hld)
    workspace = normalize_path(workspace)
    repo = normalize_path(repo)

    if not source_hld.exists():
        raise FileNotFoundError(f"source HLD not found: {source_hld}")
    if not source_hld.is_file():
        raise ValueError(f"source HLD is not a file: {source_hld}")

    workspace_info = prepare_workspace(source_hld, workspace, force=force)
    state = current_state(workspace)
    commands = allowed_commands(repo, source_hld, workspace, state)
    trigger = minimal_trigger(source_hld, workspace)

    return {
        "schema_version": 2,
        "trigger": trigger,
        "minimal_human_prompt": trigger,
        "source_hld": str(source_hld),
        "source_hld_read_only": True,
        "workspace": str(workspace),
        "workspace_info": workspace_info,
        "current_stage": state["current_stage"],
        "current_checkpoint": state["current_checkpoint"],
        "controlling_artifacts": state.get("controlling_artifacts", []),
        "blocking_questions": state.get("blocking_questions", []),
        "allowed_internal_commands": commands,
        "next_safe_action": next_action(state),
        "agent_bootstrap_rule": (
            "When an agent receives the minimal trigger, it must read the generated context files if available, "
            "run HLDspec tools internally, preserve source read-only, and stop at gates/checkpoints."
        ),
        "forbidden_actions": [
            "Do not edit the source HLD.",
            "Do not invoke SpecKit.",
            "Do not create final specs manually.",
            "Do not implement.",
            "Do not answer checkpoint questions silently.",
            "Do not promote artifacts without judge approval.",
        ],
        "agent_roles": {
            "orchestrator": "owns process guidance, state, gates, and stop conditions",
            "junior_agents": "bounded extraction/explanation only",
            "product_lead": "synthesizes product/use-case/user-story outputs",
            "architect_lead": "synthesizes API/data/dependency/constitution outputs",
            "judge": "promotes or blocks artifacts",
        },
    }


def render_minimal_trigger(context: dict[str, Any]) -> str:
    return str(context["minimal_human_prompt"]).strip() + "\n"


def render_prompt(context: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Orchestrator Agent Context",
        "",
        "made by AI",
        "",
        "This file is internal context for the HLDspec Orchestrator Agent.",
        "The human-facing prompt is intentionally minimal:",
        "",
        "```text",
        str(context["minimal_human_prompt"]),
        "```",
        "",
        "## Source and workspace",
        "",
        f"- source HLD: `{context['source_hld']}`",
        f"- source HLD read-only: `{str(context['source_hld_read_only']).lower()}`",
        f"- workspace: `{context['workspace']}`",
        f"- raw workspace copy: `{context['workspace_info']['raw_copy']}`",
        f"- working workspace copy: `{context['workspace_info']['working_copy']}`",
        "",
        "## Current state",
        "",
        f"- current stage: `{context['current_stage']}`",
        f"- current checkpoint: `{context['current_checkpoint']}`",
        f"- next safe action: {context['next_safe_action']}",
        "",
        "## Controlling artifacts",
        "",
    ]
    artifacts = context.get("controlling_artifacts") or []
    if artifacts:
        for item in artifacts:
            lines.append(f"- `{item}`")
    else:
        lines.append("- none")

    lines += ["", "## Blocking questions", ""]
    blockers = context.get("blocking_questions") or []
    if blockers:
        for item in blockers:
            if isinstance(item, dict):
                lines.append(f"- `{item.get('artifact', '')}`: {item.get('open_question_count', '')} open")
            else:
                lines.append(f"- {item}")
    else:
        lines.append("- none")

    lines += ["", "## Allowed internal commands", ""]
    for cmd in context.get("allowed_internal_commands", []):
        lines.append(f"```bash\n{cmd}\n```")

    lines += [
        "",
        "## Rules",
        "",
        "- Use the HLDspec tools internally.",
        "- Ask the human only real checkpoint questions.",
        "- Use bounded junior agents only for cheap/simple extraction or explanation.",
        "- Senior Product/Architect roles synthesize; they do not globally promote.",
        "- Judge/orchestrator controls promotion and stop conditions.",
        "- Stop when a checkpoint blocks the flow.",
        "",
        "## Forbidden actions",
        "",
    ]
    for action in context.get("forbidden_actions", []):
        lines.append(f"- {action}")

    lines += [
        "",
        "## If blocked at conversion",
        "",
        "Run the question guide, explain one question at a time, show allowed options, and ask the human to choose.",
        "Do not convert until the validated queue has no blocking TBD questions.",
        "",
        "## If later stages are reached",
        "",
        "Build/use Product Manager pack, Architect pack, answer pack, orchestration state, and proxy dry-run only after earlier gates pass.",
        "Do not invoke real SpecKit from this start context.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(context: dict[str, Any], workspace: Path) -> tuple[Path, Path, Path]:
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)
    json_path = sync / "hldspec_agent_start_context.json"
    md_path = sync / "hldspec_agent_start_context.md"
    trigger_path = sync / "hldspec_agent_trigger.txt"
    json_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_prompt(context), encoding="utf-8")
    trigger_path.write_text(render_minimal_trigger(context), encoding="utf-8")
    # Backward-compatible path. It is now internal context, not the thing the human must paste.
    (sync / "hldspec_agent_start_prompt.md").write_text(render_prompt(context), encoding="utf-8")
    return json_path, md_path, trigger_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HLDspec agent-first minimal trigger and internal context.")
    parser.add_argument("source_hld")
    parser.add_argument("--workspace", default="")
    parser.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--force", action="store_true", help="Refresh workspace HLD.raw.md and HLD.md from source.")
    parser.add_argument("--print-context", action="store_true", help="Print full internal context after the minimal trigger.")
    args = parser.parse_args()

    source = Path(args.source_hld).expanduser()
    workspace = Path(args.workspace).expanduser() if args.workspace else default_workspace(source)
    repo = Path(args.repo).expanduser()

    context = build_context(source, workspace, repo, force=args.force)
    json_path, md_path, trigger_path = write_outputs(context, Path(context["workspace"]))

    print("HLDspec minimal agent trigger:")
    print(render_minimal_trigger(context).strip())
    print()
    print("Internal context generated:")
    print(f"- json: {json_path}")
    print(f"- context: {md_path}")
    print(f"- trigger: {trigger_path}")
    print(f"- stage: {context['current_stage']}")
    if args.print_context:
        print()
        print(render_prompt(context))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
