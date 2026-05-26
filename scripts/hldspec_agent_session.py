#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hldspec.machines.project import ProjectMachine
from hldspec.result_renderer import render_machine_result
from hldspec.state_machine import MachineContext
from hldspec.workspace_adapter import TargetWorkspaceAdapter

SESSION_SCHEMA_VERSION = "1.0"
INTERVIEW_SCHEMA_VERSION = "1.0"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def json_write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def json_read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_target_dirs(target: Path) -> None:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    for rel in [
        "targetHLD/raw",
        "targetHLD/sections",
        ".hldspec",
        ".hldspec/sync",
        ".hldspec/context_packs",
        ".specify/memory",
        "prompts/agent",
        "prompts/tools",
        "prompts/speckit",
        "specs",
    ]:
        (target / rel).mkdir(parents=True, exist_ok=True)
    adapter.events_path.parent.mkdir(parents=True, exist_ok=True)


def detect_mode(target: Path, source_hash: str | None, requested_mode: str) -> str:
    if requested_mode != "auto":
        return requested_mode

    if not target.exists():
        return "create"

    session = json_read(target / ".hldspec" / "agent_session.json")
    if not session:
        return "adopt"

    previous_hash = (
        session.get("source", {}).get("sha256")
        if isinstance(session.get("source"), dict)
        else None
    )
    if source_hash and previous_hash and source_hash != previous_hash:
        return "update"

    conflicts = target / ".hldspec" / "conflicts.json"
    if conflicts.exists():
        return "blocked"

    return "resume"


def copy_source(source: Path, target: Path) -> None:
    raw = target / "targetHLD" / "raw" / "HLD.raw.md"
    working = target / "targetHLD" / "HLD.md"
    raw.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, raw)
    if not working.exists():
        shutil.copyfile(source, working)


def classify_intent(comment: str, mode: str) -> str:
    text = comment.lower()
    for intent in ("create", "update", "upgrade", "adopt", "resume", "review", "debug"):
        if intent in text:
            return intent.upper()
    if mode in {"create", "update", "upgrade", "adopt", "resume"}:
        return mode.upper()
    return "UNKNOWN"


def approval_expectations(comment: str) -> str:
    text = comment.strip()
    if not text:
        return "UNKNOWN"
    lowered = text.lower()
    if "approval" not in lowered and "approve" not in lowered:
        return "UNKNOWN"
    return text


def build_interview_answers(
    *,
    source: Path,
    source_hash: str,
    target: Path,
    mode: str,
    agent: str,
    comment: str,
    timestamp: str,
) -> dict[str, Any]:
    open_questions: list[str] = []
    if not source:
        open_questions.append("source")
    if not target:
        open_questions.append("target")
    if not comment.strip():
        open_questions.append("user_comment")

    return {
        "schema_version": INTERVIEW_SCHEMA_VERSION,
        "created_or_updated_at": timestamp,
        "source": {
            "path": str(source),
            "sha256": source_hash,
        },
        "target": str(target),
        "mode": mode,
        "agent": agent,
        "comment": comment,
        "intent_classification": classify_intent(comment, mode),
        "approval_expectations": approval_expectations(comment),
        "constraints": [],
        "open_questions": open_questions,
    }


def render_interview_answers_md(answers: dict[str, Any]) -> str:
    source = answers.get("source") if isinstance(answers.get("source"), dict) else {}
    constraints = answers.get("constraints") if isinstance(answers.get("constraints"), list) else []
    open_questions = answers.get("open_questions") if isinstance(answers.get("open_questions"), list) else []
    lines = [
        "# HLDspec Interview Answers",
        "",
        f"- schema_version: `{answers.get('schema_version', '')}`",
        f"- created_or_updated_at: `{answers.get('created_or_updated_at', '')}`",
        f"- source path: `{source.get('path', '')}`",
        f"- source sha256: `{source.get('sha256', '')}`",
        f"- target path: `{answers.get('target', '')}`",
        f"- detected mode: `{answers.get('mode', '')}`",
        f"- agent: `{answers.get('agent', '')}`",
        f"- user comment: {answers.get('comment') or 'UNKNOWN'}",
        f"- intent classification: `{answers.get('intent_classification', 'UNKNOWN')}`",
        f"- approval expectations: {answers.get('approval_expectations') or 'UNKNOWN'}",
        "",
        "## Constraints",
        "",
    ]
    lines.extend(f"- {item}" for item in constraints)
    if not constraints:
        lines.append("- none")
    lines.extend(["", "## Open Questions", ""])
    lines.extend(f"- {item}" for item in open_questions)
    if not open_questions:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)


def write_interview_answers(target: Path, answers: dict[str, Any]) -> tuple[Path, Path]:
    json_path = target / ".hldspec" / "interview_answers.json"
    md_path = target / ".hldspec" / "interview_answers.md"
    json_write(json_path, answers)
    md_path.write_text(render_interview_answers_md(answers), encoding="utf-8")
    return json_path, md_path


def write_start_prompt(target: Path, session: dict[str, Any]) -> Path:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    prompt = target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
    source = session["source"]["path"]
    mode = session["mode"]
    agent = session["agent"]
    comment = session.get("comment") or ""

    prompt.write_text(
        f"""# HLDspec Agent Session

## Role

You are the HLDspec orchestrating agent.

This is an agent-first workflow. Scripts are tools. You own orchestration, judgment, RunSkeptic usage, conflict handling, cost/context economy, and human checkpoints.

## Session

- Agent: `{agent}`
- Mode: `{mode}`
- Source: `{source}`
- Target: `{target}`
- Comment: `{comment}`

## Core rules

1. Treat source HLD/resources as read-only evidence.
2. Work inside `target/`.
3. Use `target/targetHLD/` for HLD evidence and working HLD.
4. Use HLDspec scripts as deterministic tools.
5. Do not manually create final SpecKit specs.
6. Run or apply RunSkeptic at key junctions.
7. Use smallest sufficient context.
8. Use weakest sufficient model.
9. Stop on unresolved CONFLICT.
10. Ask for human approval before risky transitions.

## First tools to consider

```bash
scripts/hldspec continue --target "{target}"
```

Then inspect:

```text
{adapter.sync_dir / 'spec_build_plan_review.md'}
{adapter.sync_dir / 'speckit_prework_quality_review.md'}
{adapter.sync_dir / 'speckit_proxy_dossier.md'}
```

## Required outputs

Generate or refresh target-specific artifacts:

```text
target/.hldspec/design_principles_selection.*
target/.hldspec/backend_technology_recommendation.*
target/.hldspec/constitution_update_plan.*
target/.hldspec/spec_packages.*
target/.hldspec/feature_dependency_graph.*
target/.hldspec/speckit_invocation_queue.*
target/prompts/
```

## Stop condition

Stop after the next safe checkpoint and report:

- files created or changed
- RunSkeptic PASS/ACTION/CONFLICT findings
- human decisions required
- next allowed action
""",
        encoding="utf-8",
    )
    return prompt


def write_tool_manifest(target: Path) -> Path:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    manifest = target / ".hldspec" / "agent_tool_manifest.md"
    manifest.write_text(
        f"""# HLDspec Agent Tool Manifest

Scripts are tools for the HLDspec agent.

## Preferred first analysis tool

```bash
scripts/hldspec continue --target "{target}"
```

## V2 machine tool

```bash
python3 scripts/hldspec_v2.py "{adapter.working_hld}" "{target}"
```

## Canonical target paths

```text
working_hld: {adapter.working_hld}
raw_hld: {adapter.raw_hld}
hldspec_sync: {adapter.sync_dir}
event_log: {adapter.events_path}
speckit_workspace: {adapter.specify_dir}
```

## Rules

- Do not use scripts as the public user workflow.
- Use tools to produce evidence and controlled artifacts.
- Gate promotion through RunSkeptic and human checkpoints.
- Keep final SpecKit artifacts owned by SpecKit.
""",
        encoding="utf-8",
    )
    return manifest


def command_start(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()

    if not source.exists() or not source.is_file():
        print(f"ERROR: source HLD not found: {source}", file=sys.stderr)
        return 2

    source_hash = sha256_file(source)
    mode = detect_mode(target, source_hash, args.mode)

    ensure_target_dirs(target)
    copy_source(source, target)

    timestamp = utc_now()
    manifest = {
        "schema_version": SESSION_SCHEMA_VERSION,
        "created_or_updated_at": timestamp,
        "agent": args.agent,
        "mode": mode,
        "comment": args.comment or "",
        "source": {
            "path": str(source),
            "sha256": source_hash,
        },
        "target": str(target),
        "paths": {
            "working_hld": str(TargetWorkspaceAdapter(target_root=target, layout="new").working_hld),
            "raw_hld": str(TargetWorkspaceAdapter(target_root=target, layout="new").raw_hld),
            "hldspec_sync": str(TargetWorkspaceAdapter(target_root=target, layout="new").sync_dir),
            "events": str(TargetWorkspaceAdapter(target_root=target, layout="new").events_path),
            "specify_dir": str(TargetWorkspaceAdapter(target_root=target, layout="new").specify_dir),
            "interview_answers_json": str(target / ".hldspec" / "interview_answers.json"),
            "interview_answers_md": str(target / ".hldspec" / "interview_answers.md"),
            "start_prompt": str(target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"),
            "tool_manifest": str(target / ".hldspec" / "agent_tool_manifest.md"),
        },
        "next_action": "Open prompts/agent/START_HLDSPEC_AGENT.md in an agent session.",
    }
    interview_answers = build_interview_answers(
        source=source,
        source_hash=source_hash,
        target=target,
        mode=mode,
        agent=args.agent,
        comment=args.comment or "",
        timestamp=timestamp,
    )
    json_write(target / ".hldspec" / "agent_session.json", manifest)
    interview_json, interview_md = write_interview_answers(target, interview_answers)
    json_write(
        target / "targetHLD" / "raw" / "resources_manifest.json",
        {
            "schema_version": SESSION_SCHEMA_VERSION,
            "resources": [
                {
                    "kind": "source_hld",
                    "path": str(source),
                    "sha256": source_hash,
                }
            ],
        },
    )
    prompt = write_start_prompt(target, manifest)
    tool_manifest = write_tool_manifest(target)

    print(f"HLDspec agent session prepared.")
    print(f"Mode: {mode}")
    print(f"Target: {target}")
    print(f"Prompt: {prompt}")
    print(f"Tool manifest: {tool_manifest}")
    print(f"Interview answers: {interview_json}")
    print(f"Interview report: {interview_md}")
    print("Next: start an agent session with the prompt above.")
    return 0


def command_status(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    session_path = target / ".hldspec" / "agent_session.json"
    session = json_read(session_path)
    if not session:
        print(f"NO_SESSION: {session_path}")
        return 2

    print(f"Target: {target}")
    print(f"Mode: {session.get('mode', 'UNKNOWN')}")
    print(f"Agent: {session.get('agent', 'UNKNOWN')}")
    print(f"Source: {session.get('source', {}).get('path', 'UNKNOWN')}")
    print(f"Prompt: {target / 'prompts' / 'agent' / 'START_HLDSPEC_AGENT.md'}")
    print(f"Next: {session.get('next_action', 'Review target/.hldspec')}")
    return 0


def command_review(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    review_paths = [
        target / ".hldspec" / "backend_technology_recommendation.md",
        target / ".hldspec" / "design_principles_selection.md",
        target / ".hldspec" / "constitution_update_plan.md",
        target / ".hldspec" / "spec_packages.md",
        target / ".hldspec" / "feature_dependency_graph.md",
        target / ".hldspec" / "speckit_invocation_queue.md",
        adapter.sync_dir / "spec_build_plan_review.md",
        adapter.sync_dir / "speckit_prework_quality_review.md",
    ]
    print("Review these files if present:")
    for path in review_paths:
        status = "EXISTS" if path.exists() else "missing"
        print(f"- {status}: {path}")
    return 0


def command_continue(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    session = json_read(target / ".hldspec" / "agent_session.json")
    source = session.get("source", {}).get("path") if isinstance(session.get("source"), dict) else None
    if not source:
        print(f"ERROR: no source recorded in {target / '.hldspec' / 'agent_session.json'}", file=sys.stderr)
        return 2

    result = ProjectMachine().run(
        MachineContext(
            repo_root=str(ROOT),
            source_hld=str(Path(source).expanduser()),
            workspace=str(target),
            metadata={"workspace_layout": "new"},
        )
    )
    print(render_machine_result(result), end="")
    return int(result.exit_code())


def command_diff(args: argparse.Namespace) -> int:
    source = Path(args.source).expanduser().resolve()
    target = Path(args.target).expanduser().resolve()
    session = json_read(target / ".hldspec" / "agent_session.json")

    if not source.exists():
        print(f"ERROR: source not found: {source}", file=sys.stderr)
        return 2

    current_hash = sha256_file(source)
    previous_hash = session.get("source", {}).get("sha256") if session else None

    print(f"Source: {source}")
    print(f"Current hash:  {current_hash}")
    print(f"Recorded hash: {previous_hash or 'none'}")
    if previous_hash == current_hash:
        print("Diff status: unchanged")
        return 0
    print("Diff status: changed")
    return 1


def command_doctor(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve() if args.target else None
    required = [
        ROOT / "docs" / "AGENT_FIRST_PRODUCT_MODEL.md",
        ROOT / "docs" / "USER_RUN_MODEL.md",
        ROOT / "docs" / "CANONICAL_FLOW.md",
        ROOT / "docs" / "ARCHITECTURE_V2.md",
        ROOT / "scripts" / "first_run_readonly.sh",
        ROOT / "scripts" / "hldspec_v2.py",
    ]
    ok = True
    for path in required:
        exists = path.exists()
        print(f"{'OK' if exists else 'MISSING'}: {path}")
        ok = ok and exists

    if target:
        for rel in [
            "targetHLD/HLD.md",
            ".hldspec/agent_session.json",
            ".hldspec/interview_answers.json",
            ".hldspec/interview_answers.md",
            "prompts/agent/START_HLDSPEC_AGENT.md",
        ]:
            path = target / rel
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists

    return 0 if ok else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Agent-first HLDspec session facade.")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("start", help="Prepare or resume an HLDspec agent session.")
    p.add_argument("--source", required=True, help="Source HLD path.")
    p.add_argument("--target", required=True, help="Target product workspace path.")
    p.add_argument("--agent", default="manual", choices=["manual", "devin", "claude", "codex"], help="Target agent.")
    p.add_argument("--mode", default="auto", choices=["auto", "create", "update", "upgrade", "adopt", "resume"], help="Intent override.")
    p.add_argument("--comment", default="", help="User intent/comment.")
    p.set_defaults(func=command_start)

    p = sub.add_parser("status", help="Show current HLDspec agent session status.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_status)

    p = sub.add_parser("review", help="Show human review files.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_review)

    p = sub.add_parser("continue", help="Run ProjectMachine to the next safe checkpoint.")
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_continue)

    p = sub.add_parser("diff", help="Compare source hash to recorded session hash.")
    p.add_argument("--source", required=True)
    p.add_argument("--target", required=True)
    p.set_defaults(func=command_diff)

    p = sub.add_parser("doctor", help="Check agent-first docs and target session files.")
    p.add_argument("--target", default=None)
    p.set_defaults(func=command_doctor)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
