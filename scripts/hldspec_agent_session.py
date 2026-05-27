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

from hldspec import session_control as sc
from hldspec.hld_source_package import build_source_package_content
from hldspec import speckit_workspace as sw
from hldspec.machines.project import ProjectMachine
from hldspec.promotion import read_json as read_promotion_json
from hldspec.result_renderer import render_machine_result
from hldspec.state_machine import ExitCode, MachineContext
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


def report_status(path: Path) -> tuple[str, str]:
    if not path.exists():
        return "not present", str(path)
    try:
        data = json_read(path)
    except Exception:
        return "ACTION", str(path)
    return str(data.get("status", "UNKNOWN")).upper(), str(path)


def status_is_blocking(status: str) -> bool:
    return status in {"ACTION", "CONFLICT"}


def collect_open_questions(target: Path) -> list[str]:
    questions: list[str] = []
    interview = json_read(target / ".hldspec" / "interview_answers.json")
    raw_open = interview.get("open_questions")
    if isinstance(raw_open, list):
        questions.extend(str(item) for item in raw_open if str(item).strip())

    hldspec_dir = target / ".hldspec"
    if hldspec_dir.exists():
        for path in sorted(hldspec_dir.rglob("*.json")):
            if "/validation/" in str(path):
                continue
            try:
                data = json_read(path)
            except Exception:
                continue
            checkpoint = data.get("human_checkpoint")
            if isinstance(checkpoint, dict):
                decision = str(checkpoint.get("human_decision", checkpoint.get("decision", "TBD"))).strip().upper()
                if decision in {"", "TBD", "UNKNOWN", "PENDING", "UNRESOLVED"}:
                    label = checkpoint.get("question") or path.relative_to(target)
                    questions.append(str(label))
            checkpoint = data.get("checkpoint")
            if isinstance(checkpoint, dict):
                open_count = checkpoint.get("open_question_count")
                if isinstance(open_count, int) and open_count > 0:
                    checkpoint_id = checkpoint.get("checkpoint_id", path.relative_to(target))
                    questions.append(f"{checkpoint_id}: {open_count} open question(s)")
    return sorted(dict.fromkeys(questions))


def current_state(target: Path, session: dict[str, Any]) -> str:
    for path in [
        target / ".hldspec" / "sync" / "hldspec_state.json",
        target / ".hldspec" / "hldspec_state.json",
    ]:
        state = json_read(path)
        if state:
            stage = state.get("current_stage") or state.get("stage")
            checkpoint = state.get("current_checkpoint") or state.get("checkpoint")
            if stage and checkpoint:
                return f"{stage} / {checkpoint}"
            if stage:
                return str(stage)
    return "agent session prepared" if session else "no session"


def print_bullet_list(items: list[str], empty: str = "none") -> None:
    if not items:
        print(f"- {empty}")
        return
    for item in items:
        print(f"- {item}")


def next_safe_action(session: dict[str, Any], blockers: list[str], open_questions: list[str]) -> str:
    if blockers:
        return "Resolve ACTION/CONFLICT blockers, then rerun status or doctor."
    if open_questions:
        return "Answer open human questions, then rerun hldspec continue."
    return str(session.get("next_action") or "Run hldspec review --target <target> or hldspec continue --target <target>.")


def summary_status(blockers: list[str], conflicts: list[str] | None = None) -> str:
    conflicts = conflicts or []
    if conflicts:
        return "CONFLICT"
    if blockers:
        return "ACTION"
    return "PASS"


def ensure_target_dirs(target: Path) -> None:
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    for rel in [
        "targetHLD/raw",
        "targetHLD/sections",
        ".hldspec",
        ".hldspec/sync",
        ".hldspec/context_packs",
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

    speckit_plan = session.get("speckit_workspace_init", {})
    selected_command = speckit_plan.get("selected_command")
    selected_command_text = " ".join(selected_command) if isinstance(selected_command, list) else "BLOCKED"
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
{adapter.source_package_dir / 'source_package.json'}
{adapter.source_package_dir / 'session_plan.json'}
{adapter.sync_dir / 'spec_build_plan_review.md'}
{adapter.sync_dir / 'speckit_prework_quality_review.md'}
{adapter.sync_dir / 'speckit_proxy_dossier.md'}
```

## Required outputs

Generate or refresh target-specific artifacts:

```text
target/.hldspec/source_package/source_package.json
target/.hldspec/source_package/session_plan.json
target/.hldspec/source_package/source_manifest.json
target/.specify/                 (from real SpecKit init only; not hand-authored)
target/.specify/source/          (generated mirror only)
target/prompts/
```

## SpecKit workspace/init boundary

- Planned init command: `{selected_command_text}`
- Default mode is dry-run planning only.
- Execute init only with explicit `--execute`.
- If SpecKit init is blocked, stop and report the blocker. Do not hand-create `.specify/`, `spec.md`, `plan.md`, `tasks.md`, or other final SpecKit artifacts.

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
    speckit_init = sw.plan_or_init_workspace(target, execute=bool(args.execute))

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
        "speckit_workspace_init": speckit_init.metadata(),
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

    # Scaffold the session-plan control plane (dry-run): session_plan.json +
    # bounded subagent packets + runner/consultant prompts + runbook. Written
    # first so the content build hashes the runbook/prompts and mirrors them.
    session_plan = sc.build_session_plan(target, ROOT, backend=sc.DEFAULT_BACKEND)
    session_plan["speckit_workspace_init"] = speckit_init.metadata()
    session_artifacts = sc.write_session_artifacts(target, session_plan)

    # Generate the source-package content from the working HLD (real content flow):
    # HLD.md, HLD.marked.md, hld_reference_map.json, speckit_single_spec_input.md,
    # manifest + metadata, and the derived .specify/source/ mirror.
    working_hld = TargetWorkspaceAdapter(target_root=target, layout="new").working_hld
    source_build = None
    if working_hld.is_file():
        source_build = build_source_package_content(
            target,
            working_hld.read_text(encoding="utf-8"),
            hld_source_ref=str(source),
            materialize_mirror=speckit_init.initialized,
        )

    print(f"HLDspec agent session prepared.")
    print(f"Mode: {mode}")
    print(f"Target: {target}")
    print(f"Prompt: {prompt}")
    print(f"Tool manifest: {tool_manifest}")
    print(f"Interview answers: {interview_json}")
    print(f"Interview report: {interview_md}")
    print(f"Session plan: {session_artifacts[sc.SESSION_PLAN_FILE]}")
    if speckit_init.selected is not None:
        print(f"SpecKit init command: {' '.join(speckit_init.selected.argv)}")
    if speckit_init.blocker:
        print(f"SpecKit init blocker: {speckit_init.blocker}")
    elif speckit_init.execute:
        if speckit_init.ok:
            print(f"SpecKit workspace initialized: {target / '.specify'}")
        else:
            print(f"SpecKit init validation: {speckit_init.validation_error or speckit_init.stderr or 'FAILED'}")
    if source_build is not None:
        print(f"Source package: {source_build.source_dir} ({source_build.anchor_count} HLD anchors)")
        if source_build.unsupported_claims:
            print(f"Unsupported claims: {len(source_build.unsupported_claims)} (review before approval)")
    print("Next: start an agent session with the prompt above.")
    return 0


def command_status(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    session_path = target / ".hldspec" / "agent_session.json"
    session = json_read(session_path)
    if not session:
        print(f"NO_SESSION: {session_path}")
        return 2

    validation_status, validation_path = report_status(target / ".hldspec" / "validation" / "context_prompt_validation.json")
    promotion_status, promotion_path = report_status(target / ".hldspec" / "validation" / "promotion_gate.json")
    open_questions = collect_open_questions(target)
    blockers: list[str] = []
    conflicts: list[str] = []
    for label, status, path in [
        ("Validation", validation_status, validation_path),
        ("Promotion gate", promotion_status, promotion_path),
    ]:
        if status == "CONFLICT":
            conflicts.append(f"{label}: {status} ({path})")
        elif status == "ACTION":
            blockers.append(f"{label}: {status} ({path})")

    source = session.get("source", {}).get("path", "UNKNOWN") if isinstance(session.get("source"), dict) else "UNKNOWN"
    print("## HLDspec Status")
    print(f"Target: {target}")
    print(f"Mode: {session.get('mode', 'UNKNOWN')}")
    print(f"Source: {source}")
    print(f"Current state: {current_state(target, session)}")
    print("")
    print("## Validation")
    print(f"Validation status: {validation_status} ({validation_path})")
    print(f"Promotion gate status: {promotion_status} ({promotion_path})")
    print("")
    print("## Blockers")
    print_bullet_list(conflicts + blockers)
    print("")
    print("## Open Questions")
    print_bullet_list(open_questions)
    print("")
    print("## Next Safe Action")
    print(next_safe_action(session, conflicts + blockers, open_questions))
    return 0


def command_review(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
    blocking_paths = [
        target / ".hldspec" / "constitution_update_plan.md",
        target / ".hldspec" / "feature_dependency_graph.md",
        target / ".hldspec" / "speckit_invocation_queue.md",
        adapter.sync_dir / "spec_build_plan_review.md",
        adapter.sync_dir / "speckit_prework_quality_review.md",
    ]
    optional_paths = [
        target / ".hldspec" / "backend_technology_recommendation.md",
        target / ".hldspec" / "design_principles_selection.md",
        target / ".hldspec" / "spec_packages.md",
        target / ".hldspec" / "validation" / "context_prompt_validation.md",
        target / ".hldspec" / "validation" / "promotion_gate.md",
    ]
    print("## HLDspec Review")
    print("")
    print("## Blocking Review Files")
    print_bullet_list([str(path) for path in blocking_paths if path.exists()])
    print("")
    print("## Optional Context Files")
    print_bullet_list([str(path) for path in optional_paths if path.exists()])
    print("")
    print("## Missing Blocking Files")
    print_bullet_list([str(path) for path in blocking_paths if not path.exists()])
    print("")
    print("## Missing Non-Blocking Files")
    print_bullet_list([str(path) for path in optional_paths if not path.exists()])
    print("")
    print("## Next Safe Action")
    if any(not path.exists() for path in blocking_paths):
        print("Generate or resolve missing blocking review files before approval or promotion.")
    else:
        print("Review blocking files for PASS/ACTION/CONFLICT decisions, then continue only after human-owned checkpoints are resolved.")
    return 0


def command_continue(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()

    # Control-plane gate: when a session plan exists, the gate validator decides
    # continuation. No plan -> legacy behaviour (run ProjectMachine unchanged).
    preflight = sc.session_continue_preflight(target)
    if preflight.gated and not preflight.allowed:
        print("## Continuation BLOCKED by the control plane")
        print(f"Gate: {preflight.gate}")
        print("Blockers:")
        print_bullet_list(preflight.blockers)
        print("Next safe action:")
        print(
            "Provide a valid Context Receipt + Phase Report, resolve the blockers above "
            "(RunSkeptic/Consultant/validation/dirty tree), then rerun continue."
        )
        return ExitCode.GATE_BLOCKED.value

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
    action_items: list[str] = []
    conflict_items: list[str] = []
    print("## Repo Checks")
    for path in required:
        exists = path.exists()
        print(f"{'OK' if exists else 'MISSING'}: {path}")
        ok = ok and exists
        if not exists:
            action_items.append(f"Missing repo file: {path}")

    if target:
        print("")
        print("## Target Layout Checks")
        for rel in [
            "targetHLD/HLD.md",
            "targetHLD/raw/HLD.raw.md",
            ".hldspec",
            ".hldspec/sync",
            "prompts/agent",
            "prompts/speckit",
        ]:
            path = target / rel
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists
            if not exists:
                action_items.append(f"Missing target layout path: {path}")

        print("")
        print("## SpecKit Workspace Checks")
        speckit_dir = target / ".specify"
        session = json_read(target / ".hldspec" / "agent_session.json")
        init_meta = session.get("speckit_workspace_init", {}) if isinstance(session, dict) else {}
        print(f"{'OK' if speckit_dir.exists() else 'PLANNED'}: {speckit_dir}")
        if isinstance(init_meta, dict):
            selected = init_meta.get("selected_command")
            if isinstance(selected, list) and selected:
                print(f"Planned init command: {' '.join(str(part) for part in selected)}")
            blocker = init_meta.get("blocker")
            if blocker:
                action_items.append(f"SpecKit init blocker: {blocker}")

        print("")
        print("## Session Checks")
        for rel in [
            ".hldspec/agent_session.json",
            "prompts/agent/START_HLDSPEC_AGENT.md",
        ]:
            path = target / rel
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists
            if not exists:
                action_items.append(f"Missing session file: {path}")

        print("")
        print("## Interview Checks")
        for rel in [
            ".hldspec/interview_answers.json",
            ".hldspec/interview_answers.md",
        ]:
            path = target / rel
            exists = path.exists()
            print(f"{'OK' if exists else 'MISSING'}: {path}")
            ok = ok and exists
            if not exists:
                action_items.append(f"Missing interview file: {path}")

        print("")
        print("## Control Plane Checks")
        adapter = TargetWorkspaceAdapter(target_root=target, layout="new")
        plan_path = adapter.source_package_dir / sc.SESSION_PLAN_FILE
        if plan_path.exists():
            print(f"OK: {plan_path}")
            # Structural health: packets present and plan well-formed are ACTION
            # items. Whether you can continue *right now* (a Phase Report exists,
            # gates satisfied) is informational, not a workspace-health failure.
            for rel in ["subagent_packets/basepack_packet.md", "subagent_packets/runner_packet.md", "subagent_packets/consultant_packet.md"]:
                p = adapter.source_package_dir / rel
                print(f"{'OK' if p.exists() else 'MISSING'}: {p}")
                if not p.exists():
                    action_items.append(f"Missing subagent packet: {p}")
            plan_data = json_read(plan_path)
            if not plan_data.get("current_gate"):
                action_items.append(f"Session plan missing current_gate: {plan_path}")
            preflight = sc.session_continue_preflight(target)
            print(f"Continuation gate: {preflight.gate}")
            print(f"Continuation allowed now: {str(preflight.allowed).lower()}")
            print("Continuation blockers (informational):")
            print_bullet_list(preflight.blockers)
        else:
            print(f"MISSING: {plan_path}")
            action_items.append(f"No session plan (run start or hldspec_session_control): {plan_path}")

        print("")
        print("## Validation Reports")
        validation_status, validation_path = report_status(target / ".hldspec" / "validation" / "context_prompt_validation.json")
        promotion_status, promotion_path = report_status(target / ".hldspec" / "validation" / "promotion_gate.json")
        print(f"Validation status: {validation_status} ({validation_path})")
        print(f"Promotion gate status: {promotion_status} ({promotion_path})")
        for label, status, path in [
            ("Validation", validation_status, validation_path),
            ("Promotion gate", promotion_status, promotion_path),
        ]:
            if status == "CONFLICT":
                conflict_items.append(f"{label}: {status} ({path})")
            elif status == "ACTION":
                action_items.append(f"{label}: {status} ({path})")
        promotion_gate = target / ".hldspec" / "validation" / "promotion_gate.json"
        if promotion_gate.exists():
            try:
                gate = read_promotion_json(promotion_gate)
                status = gate.get("status", "UNKNOWN") if isinstance(gate, dict) else "UNKNOWN"
            except Exception:
                status = "INVALID"
            print(f"Promotion gate: {status} ({promotion_gate})")

    print("")
    print("## Final Summary")
    final_status = summary_status(action_items, conflict_items)
    print(f"Summary: {final_status}")
    print("Blockers:")
    print_bullet_list(conflict_items + action_items)
    print("Next safe action:")
    if final_status == "PASS":
        print("Continue with hldspec status, review, or continue as appropriate.")
    else:
        print("Resolve listed ACTION/CONFLICT items, then rerun doctor.")
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
    p.add_argument("--execute", action="store_true", help="Run the detected SpecKit init command instead of dry-run planning only.")
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
