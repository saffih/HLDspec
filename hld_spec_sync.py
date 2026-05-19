#!/usr/bin/env -S uv run --script --no-project
# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///

"""
hld_spec_sync.py

Sync one large HLD into:
- .specify/memory/constitution.md
- specs/*/spec.md
- specs/spec_index.json
- specs/feature_graph.json
- specs/sync_report.md
- specs/analyze_report.md
- specs/missing_report.json
- specs/duplicate_report.json
- specs/drift_report.json
- specs/constitution_change_report.md

Works for:
- Greenfield: compare HLD desired state against empty current state.
- Brownfield: compare HLD desired state against existing constitution/specs/index/graph.

Backends:
- --agent devin
- --agent claude
- --agent codex
- --agent custom

Default:
    ./hld_spec_sync.py --hld ./hld.md --agent devin --model swe-1.6
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def read_text(path: Path, default: str = "") -> str:
    if not path.exists():
        return default
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def number_hld(hld_text: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(hld_text.splitlines(), start=1)) + "\n"


def compact_middle(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n\n[...TRUNCATED BY hld_spec_sync.py...]\n\n" + text[-half:]


def find_existing_spec_files(workspace: Path) -> list[Path]:
    specs_dir = workspace / "specs"
    if not specs_dir.exists():
        return []
    return sorted(p for p in specs_dir.glob("*/spec.md") if p.is_file())


def list_existing_specs(workspace: Path, max_chars_per_spec: int, max_specs: int) -> str:
    files = find_existing_spec_files(workspace)
    if not files:
        return "No existing specs/*/spec.md files found.\n"

    parts: list[str] = []
    for idx, path in enumerate(files, start=1):
        if max_specs > 0 and idx > max_specs:
            parts.append(f"\n[...{len(files) - max_specs} additional specs omitted...]\n")
            break
        rel = path.relative_to(workspace)
        text = compact_middle(read_text(path), max_chars_per_spec)
        parts.append(f"\n--- EXISTING SPEC {idx}: {rel} ---\n{text}\n--- END EXISTING SPEC {idx} ---\n")
    return "\n".join(parts)


def load_current_state(workspace: Path, mode: str, max_existing_spec_chars: int, max_existing_specs: int) -> dict[str, str]:
    if mode == "greenfield":
        return {
            "constitution": "No constitution exists. Treat current state as empty.\n",
            "spec_index": "No spec_index.json exists. Treat current state as empty.\n",
            "feature_graph": "No feature_graph.json exists. Treat current state as empty.\n",
            "existing_specs": "Greenfield mode: current specs are intentionally treated as empty.\n",
        }

    return {
        "constitution": read_text(workspace / ".specify" / "memory" / "constitution.md", "No constitution exists.\n"),
        "spec_index": read_text(workspace / "specs" / "spec_index.json", "No spec_index.json exists.\n"),
        "feature_graph": read_text(workspace / "specs" / "feature_graph.json", "No feature_graph.json exists.\n"),
        "existing_specs": list_existing_specs(workspace, max_existing_spec_chars, max_existing_specs),
    }


def apply_write_blocks(log_path: Path, workspace: Path) -> int:
    text = read_text(log_path)
    pattern = re.compile(
        r"WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n(?P<content>.*?)(?=\nWRITE FILE:|\Z)",
        re.DOTALL,
    )

    workspace = workspace.resolve()
    count = 0

    for match in pattern.finditer(text):
        raw_path = match.group("path").strip()
        content = match.group("content").rstrip() + "\n"

        out_path = Path(raw_path)
        if not out_path.is_absolute():
            out_path = workspace / out_path
        out_path = out_path.resolve()

        if not str(out_path).startswith(str(workspace)):
            raise RuntimeError(f"Refusing to write outside workspace: {out_path}")

        write_text(out_path, content)
        count += 1

    return count


def validate_json_file(path: Path, errors: list[str]) -> None:
    if not path.exists():
        errors.append(f"missing required output: {path}")
        return
    try:
        json.loads(read_text(path))
    except Exception as exc:
        errors.append(f"invalid JSON: {path}: {exc}")


def validate_outputs(workspace: Path, require_specs: bool) -> list[str]:
    errors: list[str] = []

    required_text = [
        ".specify/memory/constitution.md",
        "specs/sync_report.md",
        "specs/analyze_report.md",
        "specs/constitution_change_report.md",
    ]

    required_json = [
        "specs/spec_index.json",
        "specs/feature_graph.json",
        "specs/missing_report.json",
        "specs/duplicate_report.json",
        "specs/drift_report.json",
    ]

    for rel in required_text:
        if not (workspace / rel).exists():
            errors.append(f"missing required output: {rel}")

    for rel in required_json:
        validate_json_file(workspace / rel, errors)

    spec_files = find_existing_spec_files(workspace)
    if require_specs and not spec_files:
        errors.append("no specs/*/spec.md files exist after sync")

    for path in spec_files:
        text = read_text(path)
        rel = str(path.relative_to(workspace))
        for section in ["## Source Anchors", "## Requirements", "## Acceptance Criteria", "## Traceability"]:
            if section not in text:
                errors.append(f"{rel}: missing section {section}")

    return errors


def build_agent_command(
    *,
    agent: str,
    model: str,
    prompt: str,
    prompt_file: Path,
    custom_command: str | None,
    extra_args: list[str],
) -> list[str]:
    if agent == "devin":
        cmd = ["devin", "-p", prompt]
        if model:
            cmd += ["--model", model]
        return cmd + extra_args

    if agent == "claude":
        cmd = ["claude", "-p", prompt]
        if model:
            cmd += ["--model", model]
        return cmd + extra_args

    if agent == "codex":
        # Codex CLI interfaces may vary by version. This default is intended
        # for non-interactive execution. If it fails, use --agent custom.
        cmd = ["codex", "exec", prompt]
        if model:
            cmd += ["--model", model]
        return cmd + extra_args

    if agent == "custom":
        if not custom_command:
            raise SystemExit("--agent custom requires --agent-command")
        rendered = (
            custom_command
            .replace("{prompt_file}", str(prompt_file))
            .replace("{model}", model or "")
        )
        return shlex.split(rendered) + extra_args

    raise SystemExit(f"Unknown agent: {agent}")


def run_agent(
    *,
    agent: str,
    model: str,
    prompt: str,
    prompt_file: Path,
    workspace: Path,
    log_path: Path,
    custom_command: str | None,
    extra_args: list[str],
) -> int:
    cmd = build_agent_command(
        agent=agent,
        model=model,
        prompt=prompt,
        prompt_file=prompt_file,
        custom_command=custom_command,
        extra_args=extra_args,
    )

    printable = " ".join(shlex.quote(x if len(x) < 180 else x[:180] + "...") for x in cmd)
    eprint(f"Running: {printable}")

    with log_path.open("w", encoding="utf-8") as log:
        proc = subprocess.run(
            cmd,
            cwd=str(workspace),
            text=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    return int(proc.returncode)


def build_prompt(
    *,
    mode: str,
    hld_path: Path,
    numbered_hld: str,
    current_state: dict[str, str],
    report_only: bool,
    analyze_only: bool,
) -> str:
    if analyze_only:
        work_mode = "ANALYZE ONLY: Do not update constitution or specs. Write reports only."
    elif report_only:
        work_mode = "REPORT ONLY: Do not update specs. Write reports only."
    else:
        work_mode = "SYNC MODE: Update/create/deprecate constitution and specs as needed."

    return f"""You are a careful HLD-to-SpecKit synchronization agent.

USER GOAL
Maintain one large HLD as the parent source of truth while keeping:
- .specify/memory/constitution.md
- specs/*/spec.md
- specs/spec_index.json
- specs/feature_graph.json
- missing/duplicate/drift/analyze reports

synchronized with that HLD.

MODE
{mode}

WORK MODE
{work_mode}

IMPORTANT MODEL
Use the same algorithm for greenfield and brownfield:
- Desired state = what the HLD says should exist now.
- Current state = existing constitution/specs/index/graph.
- In greenfield, current state is intentionally empty.
- Diff desired vs current.
- Create missing, update changed, deprecate removed/stale, report uncertain.

SOURCE OF TRUTH RULES
1. Constitution governs all specs and implementation.
2. HLD is the canonical parent source for system intent, architecture, work units, scope, and ordering.
3. Feature specs are derived living contracts, one per stable capability.
4. Implementation is derived from specs.
5. If a spec conflicts with the HLD, flag drift and update the spec unless a documented exception says otherwise.

CONSTITUTION SYNC IS REQUIRED
Every run must evaluate whether the constitution needs updates from the HLD, including:
- source-of-truth hierarchy
- non-goals and scope
- performance/memory/resource constraints
- reliability rules
- human approval rules
- feature ordering rules
- implementation boundaries
- dependency rules
- testing/validation gates

DO NOT
- Do not implement code.
- Do not modify source code outside .specify/ and specs/.
- Do not create tasks.md or plan.md.
- Do not create a new spec for every HLD change.
- Do not duplicate specs.
- Do not turn non-goals into features.
- Do not turn context-only architecture/rationale into unnecessary specs.
- Do not silently ignore missing feature coverage.

DO
- Create/update .specify/memory/constitution.md.
- Create/update specs/spec_index.json.
- Create/update specs/feature_graph.json.
- Create/update specs/sync_report.md.
- Create/update specs/analyze_report.md.
- Create/update specs/missing_report.json.
- Create/update specs/duplicate_report.json.
- Create/update specs/drift_report.json.
- Create/update specs/constitution_change_report.md.
- Create/update specs/<NNN-feature-slug>/spec.md when not in analyze-only/report-only mode.
- Update existing related specs when HLD changes existing capabilities.
- Create a new spec only for a new independent capability.
- Mark removed/deprecated behavior clearly.
- Preserve HLD line anchors and quote anchors in every spec.
- Include constitution checks in every spec.
- Build bottom-up feature ordering:
  1. constitution/governance
  2. foundation/data models/interfaces
  3. generation/processing core
  4. API/integration
  5. UI/workflows
  6. operations/reliability
  7. testing/validation

SPEC BOUNDARY RULES
A spec is a stable capability, not a commit and not necessarily an HLD section.
Default decisions:
- Existing capability changed -> update existing spec.
- New independent capability -> create new spec.
- Cross-cutting rule -> update constitution and affected specs.
- Wording-only clarification -> update anchors/notes or no-op.
- Future-phase item -> out of scope or future status.
- Technical debt -> debt/refactor spec only if actionable and HLD says it matters.

REQUIRED SPEC FORMAT
Every specs/<NNN-feature-slug>/spec.md must include:

# Feature Specification: <title>

## Status
active|needs-review|deprecated

## Source of Truth
- Parent HLD: {hld_path}
- HLD lines: <start-end>
- Anchor quote: "<exact quote>"

## Source Anchors
- ...

## Constitution Checks
- HLD anchored: PASS|FAIL
- Single-goal spec: PASS|FAIL
- No source-code implementation included: PASS|FAIL
- Non-goals respected: PASS|FAIL
- Dependencies declared: PASS|FAIL

## User Story
As a ...
I want ...
So that ...

## Requirements
- FR-001: ...

## Acceptance Criteria
- Given ...
  When ...
  Then ...

## Dependencies
- Depends on: ...
- Blocks: ...

## Edge Cases
- ...

## Out of Scope
- ...

## Open Questions
- ...

## Traceability
- HLD lines ...
- Related specs ...

REQUIRED spec_index.json SCHEMA
[
  {{
    "spec_id": "001",
    "title": "...",
    "spec_path": "specs/001-feature-slug/spec.md",
    "status": "active|needs-review|deprecated",
    "layer": "constitution|foundation|generation|processing|api|ui|operations|testing|debt",
    "hld_anchors": [
      {{
        "section": "...",
        "quote": "...",
        "line_hint": [start, end]
      }}
    ],
    "depends_on": [],
    "blocks": [],
    "sync_status": "synced|missing|drift|duplicate-risk|needs-review",
    "notes": ""
  }}
]

REQUIRED feature_graph.json SCHEMA
{{
  "nodes": [
    {{
      "id": "001",
      "title": "...",
      "layer": "...",
      "spec_path": "..."
    }}
  ],
  "edges": [
    ["001", "002"]
  ],
  "recommended_order": ["001", "002"]
}}

REQUIRED missing_report.json SCHEMA
[
  {{
    "hld_anchor": {{"section": "...", "quote": "...", "line_hint": [start, end]}},
    "missing_capability": "...",
    "recommended_action": "create_spec|update_spec|mark_out_of_scope|needs_review",
    "reason": ""
  }}
]

REQUIRED duplicate_report.json SCHEMA
[
  {{
    "status": "PASS|DUPLICATE_RISK",
    "specs": [],
    "reason": "",
    "recommended_action": "keep|merge|rename|deprecate"
  }}
]

REQUIRED drift_report.json SCHEMA
[
  {{
    "spec_path": "...",
    "drift_type": "anchor_missing|hld_changed|spec_conflicts_with_hld|stale_spec|constitution_violation",
    "severity": "HIGH|MEDIUM|LOW",
    "recommended_action": "update_spec|deprecate_spec|update_index|needs_review",
    "evidence": ""
  }}
]

REQUIRED sync_report.md
Must summarize:
- Result: PASS or NEEDS_REVIEW
- Mode: greenfield or brownfield
- Specs created
- Specs updated
- Specs deprecated
- Missing coverage
- Duplicate risks
- Drift risks
- Constitution changes
- Recommended implementation order
- Open questions

REQUIRED analyze_report.md
Must answer:
- Are all current-scope HLD capabilities covered by active specs?
- Are duplicate capabilities present?
- Are HLD anchors stale or missing?
- Does the constitution conflict with HLD?
- Do specs conflict with constitution?
- Is the feature graph bottom-up and sane?
- Which specs are ready for planning?
- Which specs are blocked?

REQUIRED constitution_change_report.md
Must summarize:
- Constitution updates made or recommended
- HLD evidence for each update
- Whether changes are blocking

OUTPUT FORMAT
You MUST output all file changes using WRITE FILE blocks only.

Example:
WRITE FILE: specs/sync_report.md
CONTENT:
# Sync Report
...

CURRENT CONSTITUTION
{current_state["constitution"]}

CURRENT SPEC INDEX
{current_state["spec_index"]}

CURRENT FEATURE GRAPH
{current_state["feature_graph"]}

CURRENT EXISTING SPECS
{current_state["existing_specs"]}

NUMBERED HLD INPUT
{numbered_hld}
"""


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Sync HLD -> constitution + SpecKit specs + missing/duplicate/drift/analyze reports."
    )
    ap.add_argument("--hld", required=True, help="Path to HLD markdown file")
    ap.add_argument("--workspace", default=".", help="Repo/workspace root")
    ap.add_argument("--agent", choices=["devin", "claude", "codex", "custom"], default="devin")
    ap.add_argument("--model", default="swe-1.6")
    ap.add_argument("--agent-command", default=None, help="For --agent custom. Supports {prompt_file} and {model}.")
    ap.add_argument("--agent-extra-arg", action="append", default=[])

    ap.add_argument("--mode", choices=["auto", "greenfield", "brownfield"], default="auto")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument("--prompt-only", action="store_true")
    ap.add_argument("--no-apply-write-blocks", action="store_true")

    ap.add_argument("--max-hld-chars", type=int, default=0, help="0 means no HLD truncation")
    ap.add_argument("--max-existing-spec-chars", type=int, default=16000)
    ap.add_argument("--max-existing-specs", type=int, default=80)
    args = ap.parse_args()

    workspace = Path(args.workspace).resolve()
    hld_path = Path(args.hld)
    if not hld_path.is_absolute():
        hld_path = (workspace / hld_path).resolve()

    if not hld_path.exists():
        raise SystemExit(f"Missing HLD file: {hld_path}")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    logs_dir = workspace / "logs" / "hld_spec_sync" / ts
    logs_dir.mkdir(parents=True, exist_ok=True)

    existing_specs = find_existing_spec_files(workspace)
    if args.mode == "auto":
        mode = "brownfield" if existing_specs else "greenfield"
    else:
        mode = args.mode

    hld_text = read_text(hld_path)
    numbered_hld = compact_middle(number_hld(hld_text), args.max_hld_chars)
    write_text(logs_dir / "hld_numbered.md", numbered_hld)

    current_state = load_current_state(
        workspace=workspace,
        mode=mode,
        max_existing_spec_chars=args.max_existing_spec_chars,
        max_existing_specs=args.max_existing_specs,
    )

    prompt = build_prompt(
        mode=mode,
        hld_path=hld_path,
        numbered_hld=numbered_hld,
        current_state=current_state,
        report_only=args.report_only,
        analyze_only=args.analyze_only,
    )

    prompt_path = logs_dir / "prompt.md"
    log_path = logs_dir / "agent.log"
    write_text(prompt_path, prompt)

    print(f"Mode: {mode}")
    print(f"Agent: {args.agent}")
    print(f"Model: {args.model}")
    print(f"Prompt: {prompt_path}")
    print(f"Log: {log_path}")

    if args.prompt_only:
        print("Prompt-only mode. Agent was not called.")
        return 0

    try:
        rc = run_agent(
            agent=args.agent,
            model=args.model,
            prompt=prompt,
            prompt_file=prompt_path,
            workspace=workspace,
            log_path=log_path,
            custom_command=args.agent_command,
            extra_args=args.agent_extra_arg,
        )
    except FileNotFoundError as exc:
        eprint(f"Agent binary not found: {exc}")
        return 127

    writes = 0
    if not args.no_apply_write_blocks:
        try:
            writes = apply_write_blocks(log_path, workspace)
        except Exception as exc:
            eprint(f"Failed to apply WRITE FILE blocks: {exc}")

    validation_errors = validate_outputs(workspace, require_specs=not args.report_only and not args.analyze_only)

    run_summary = {
        "mode": mode,
        "agent": args.agent,
        "model": args.model,
        "hld": str(hld_path),
        "prompt": str(prompt_path),
        "log": str(log_path),
        "returncode": rc,
        "write_blocks_applied": writes,
        "validation_errors": validation_errors,
    }
    write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))

    if rc != 0:
        eprint(f"Agent failed with rc={rc}. See: {log_path}")
        return rc

    if validation_errors:
        eprint("Completed with validation errors:")
        for err in validation_errors:
            eprint(f"- {err}")
        eprint(f"See: {logs_dir / 'run_summary.json'}")
        return 1

    print("PASS")
    print("Updated files under:")
    print("- .specify/memory/constitution.md")
    print("- specs/")
    print(f"Run summary: {logs_dir / 'run_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
