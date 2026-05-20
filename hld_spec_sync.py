#!/usr/bin/env -S uv run --script --no-project
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pexpect>=4.9.0",
# ]
# ///

"""
hld_spec_sync.py

Sync one large HLD into:
- .specify/memory/constitution.md
- specs/*/spec.md (native Spec Kit feature specs)
- .specify/sync/spec_index.json
- .specify/sync/feature_graph.json
- .specify/sync/sync_report.md
- .specify/sync/analyze_report.md
- .specify/sync/missing_report.json
- .specify/sync/duplicate_report.json
- .specify/sync/drift_report.json
- .specify/sync/constitution_change_report.md

Works for:
- Greenfield: compare HLD desired state against empty current state.
- Brownfield: compare HLD desired state against existing constitution/native Spec Kit specs/sync index/sync graph.

Backends:
- --agent devin  -> default model swe-1.6
- --agent claude -> default model opus-4.6
- --agent codex  -> default model gpt-5.5
- --agent custom

Default:
    ./hld_spec_sync.py --hld ./hld.md

The default agent is devin. If --model is omitted, the selected agent's
default model is used.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
import subprocess
import sys
from datetime import datetime
from pathlib import Path


DEFAULT_AGENT_MODELS = {
    "devin": "swe-1.6",
    "claude": "opus-4.6",
    "codex": "gpt-5.5",
}

FEATURE_SPECS_REL = Path("specs")
SYNC_REL = Path(".specify") / "sync"
SYNC_SKEPTIC_REPORT_REL = SYNC_REL / "skeptic_report.md"
SYNC_SKEPTIC_CONFLICTS_REL = SYNC_REL / "skeptic_conflicts.json"
SYNC_ALLOWED_SPEC_FILENAMES = {"spec.md"}
PROTECTED_RELS = {
    ".git",
    ".agents",
    ".codex",
    "logs",
}
CONFLICT_RETURN_CODE = 2
RESOLVED_CONFLICT_STATUSES = {"handled", "resolved", "closed", "fixed", "accepted"}
VALID_SKEPTIC_STATUSES = {"HANDLED", "CONFLICT"}
VALID_EVIDENCE_LEVELS = {"OBSERVED", "REPRODUCED", "HISTORICAL", "INFERRED RISK"}
REQUIRED_THINKER_CODES = ("CH", "OM", "FE", "PO", "KT", "SH")
REQUIRED_CONFLICT_FIELDS = (
    "issue",
    "thesis",
    "antithesis",
    "tradeoffs",
    "blocking_unknowns",
    "missing_evidence",
    "decision_needed",
)


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

    marker = "\n\n[...TRUNCATED BY hld_spec_sync.py...]\n\n"
    if max_chars <= len(marker):
        return marker[:max_chars]

    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return text[:head] + marker + text[-tail:]


def find_existing_spec_files(workspace: Path) -> list[Path]:
    specs_dir = workspace / FEATURE_SPECS_REL
    if not specs_dir.exists():
        return []
    return sorted(p for p in specs_dir.glob("*/spec.md") if p.is_file())


def list_existing_specs(workspace: Path, max_chars_per_spec: int, max_specs: int) -> str:
    files = find_existing_spec_files(workspace)
    if not files:
        return "No existing native Spec Kit specs/*/spec.md files found.\n"

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
        "spec_index": read_text(workspace / SYNC_REL / "spec_index.json", "No spec_index.json exists.\n"),
        "feature_graph": read_text(workspace / SYNC_REL / "feature_graph.json", "No feature_graph.json exists.\n"),
        "existing_specs": list_existing_specs(workspace, max_existing_spec_chars, max_existing_specs),
    }


def apply_write_blocks(
    log_path: Path,
    workspace: Path,
    *,
    allow_constitution: bool,
    allow_specs: bool,
) -> int:
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

        try:
            out_path.relative_to(workspace)
        except ValueError as exc:
            raise RuntimeError(f"Refusing to write outside workspace: {out_path}") from exc

        if not is_sync_allowed_path(
            out_path,
            workspace,
            allow_constitution=allow_constitution,
            allow_specs=allow_specs,
        ):
            raise RuntimeError(f"Refusing disallowed sync write target: {out_path.relative_to(workspace)}")

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


def has_thinker_code(text: str, code: str) -> bool:
    normalized = text.upper()
    return f"({code})" in normalized or normalized == code


def validate_skeptic_contract(data: object, conflicts_rel: Path, errors: list[str]) -> None:
    if not isinstance(data, dict):
        return

    status = str(data.get("status", "")).upper()
    if status not in VALID_SKEPTIC_STATUSES:
        errors.append(f"invalid skeptic status in {conflicts_rel}: expected HANDLED or CONFLICT")

    thinker_trace = data.get("thinker_trace")
    if not isinstance(thinker_trace, list) or not thinker_trace:
        errors.append(f"invalid skeptic thinker_trace in {conflicts_rel}: expected non-empty array")
    else:
        trace_texts: list[str] = []
        for idx, item in enumerate(thinker_trace, start=1):
            if not isinstance(item, dict):
                errors.append(f"invalid skeptic thinker_trace[{idx}] in {conflicts_rel}: expected object")
                continue
            thinker = str(item.get("thinker", "")).strip()
            found = str(item.get("found", "")).strip()
            changed = str(item.get("changed", "")).strip()
            trace_texts.append(thinker)
            if not thinker or not found or not changed:
                errors.append(
                    f"invalid skeptic thinker_trace[{idx}] in {conflicts_rel}: thinker, found, and changed are required"
                )
        for code in REQUIRED_THINKER_CODES:
            if not any(has_thinker_code(text, code) for text in trace_texts):
                errors.append(f"missing skeptic thinker trace for {code} in {conflicts_rel}")

    actions = data.get("actions", [])
    if not isinstance(actions, list):
        errors.append(f"invalid skeptic actions in {conflicts_rel}: expected array")
    else:
        for idx, item in enumerate(actions, start=1):
            if not isinstance(item, dict):
                errors.append(f"invalid skeptic actions[{idx}] in {conflicts_rel}: expected object")
                continue
            for field in ("issue", "action", "verification", "evidence_level"):
                if not str(item.get(field, "")).strip():
                    errors.append(f"invalid skeptic actions[{idx}] in {conflicts_rel}: missing {field}")
            evidence_level = str(item.get("evidence_level", "")).upper()
            if evidence_level and evidence_level not in VALID_EVIDENCE_LEVELS:
                errors.append(f"invalid skeptic actions[{idx}] evidence_level in {conflicts_rel}: {evidence_level}")

    conflicts = data.get("conflicts", [])
    if not isinstance(conflicts, list):
        errors.append(f"invalid skeptic conflicts in {conflicts_rel}: expected array")
    else:
        for idx, item in enumerate(conflicts, start=1):
            if not isinstance(item, dict):
                errors.append(f"invalid skeptic conflicts[{idx}] in {conflicts_rel}: expected object")
                continue
            item_status = str(item.get("status") or item.get("resolution") or "unresolved").lower()
            if item_status not in RESOLVED_CONFLICT_STATUSES:
                for field in REQUIRED_CONFLICT_FIELDS:
                    value = item.get(field)
                    if isinstance(value, list):
                        missing = not value
                    else:
                        missing = not str(value or "").strip()
                    if missing:
                        errors.append(f"invalid skeptic conflicts[{idx}] in {conflicts_rel}: missing {field}")


def evaluate_skeptic_outputs(
    workspace: Path,
    *,
    report_rel: Path,
    conflicts_rel: Path,
    errors: list[str],
) -> list[dict[str, object]]:
    report_path = workspace / report_rel
    conflicts_path = workspace / conflicts_rel

    if not report_path.exists():
        errors.append(f"missing required skeptic output: {report_rel}")
    if not conflicts_path.exists():
        errors.append(f"missing required skeptic output: {conflicts_rel}")
        return []

    try:
        data = json.loads(read_text(conflicts_path))
    except Exception as exc:
        errors.append(f"invalid skeptic JSON: {conflicts_rel}: {exc}")
        return []

    if not isinstance(data, dict):
        errors.append(f"invalid skeptic JSON shape: {conflicts_rel}: expected object")
        return []

    validate_skeptic_contract(data, conflicts_rel, errors)

    raw_conflicts = data.get("conflicts", [])
    status = str(data.get("status", "")).upper()

    if not isinstance(raw_conflicts, list):
        errors.append(f"invalid skeptic conflicts shape: {conflicts_rel}: conflicts must be an array")
        return []

    unresolved: list[dict[str, object]] = []
    for idx, item in enumerate(raw_conflicts, start=1):
        if isinstance(item, dict):
            item_status = str(item.get("status") or item.get("resolution") or "unresolved").lower()
            if item_status not in RESOLVED_CONFLICT_STATUSES:
                unresolved.append(item)
        else:
            unresolved.append({"id": f"SK-{idx:03d}", "issue": str(item), "status": "unresolved"})

    if status == "CONFLICT" and not unresolved:
        unresolved.append(
            {
                "id": "SK-STATUS",
                "issue": "Skeptic status is CONFLICT but no unresolved conflict item was provided.",
                "status": "unresolved",
                "decision_needed": "Provide the missing human decision or mark status HANDLED.",
            }
        )

    return unresolved


def print_skeptic_conflicts(conflicts: list[dict[str, object]], conflicts_rel: Path) -> None:
    eprint("Skeptic unresolved conflicts require human decision:")
    for idx, conflict in enumerate(conflicts, start=1):
        conflict_id = conflict.get("id") or f"SK-{idx:03d}"
        issue = conflict.get("issue") or conflict.get("title") or "(no issue provided)"
        decision = conflict.get("decision_needed") or conflict.get("decision") or "(no decision_needed provided)"
        eprint(f"- {conflict_id}: {issue}")
        eprint(f"  decision_needed: {decision}")
    eprint(f"See: {conflicts_rel}")


def validate_outputs(workspace: Path, *, require_constitution: bool, require_specs: bool) -> list[str]:
    errors: list[str] = []

    required_text = [
        ".specify/sync/sync_report.md",
        ".specify/sync/analyze_report.md",
        ".specify/sync/constitution_change_report.md",
    ]
    if require_constitution:
        required_text.insert(0, ".specify/memory/constitution.md")

    required_json = [
        ".specify/sync/spec_index.json",
        ".specify/sync/feature_graph.json",
        ".specify/sync/missing_report.json",
        ".specify/sync/duplicate_report.json",
        ".specify/sync/drift_report.json",
    ]

    for rel in required_text:
        if not (workspace / rel).exists():
            errors.append(f"missing required output: {rel}")

    for rel in required_json:
        validate_json_file(workspace / rel, errors)

    spec_files = find_existing_spec_files(workspace)
    if require_specs and not spec_files:
        errors.append("no native Spec Kit specs/*/spec.md files exist after sync")

    for path in spec_files:
        text = read_text(path)
        rel = str(path.relative_to(workspace))
        for section in ["## User Scenarios & Testing", "### Functional Requirements", "## Success Criteria"]:
            if section not in text:
                errors.append(f"{rel}: missing section {section}")

    return errors


def is_protected_path(path: Path, workspace: Path) -> bool:
    rel = path.relative_to(workspace)
    return bool(rel.parts) and rel.parts[0] in PROTECTED_RELS


def is_sync_allowed_path(
    path: Path,
    workspace: Path,
    *,
    allow_constitution: bool,
    allow_specs: bool,
) -> bool:
    rel = path.relative_to(workspace)
    parts = rel.parts
    if not parts:
        return False

    if is_protected_path(path, workspace):
        return False

    if allow_constitution and rel == Path(".specify") / "memory" / "constitution.md":
        return True

    if len(parts) >= 2 and parts[0] == ".specify" and parts[1] == "sync":
        return True

    if allow_specs and len(parts) == 3 and parts[0] == "specs" and parts[-1] in SYNC_ALLOWED_SPEC_FILENAMES:
        return True

    return False


def validate_write_targets(
    log_path: Path,
    workspace: Path,
    *,
    allow_constitution: bool,
    allow_specs: bool,
) -> None:
    text = read_text(log_path)
    pattern = re.compile(r"WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n", re.MULTILINE)
    workspace = workspace.resolve()
    for match in pattern.finditer(text):
        raw_path = match.group("path").strip()
        out_path = Path(raw_path)
        if not out_path.is_absolute():
            out_path = workspace / out_path
        out_path = out_path.resolve()
        try:
            out_path.relative_to(workspace)
        except ValueError as exc:
            raise RuntimeError(f"Refusing to write outside workspace: {out_path}") from exc
        if not is_sync_allowed_path(
            out_path,
            workspace,
            allow_constitution=allow_constitution,
            allow_specs=allow_specs,
        ):
            raise RuntimeError(f"Refusing disallowed sync write target: {out_path.relative_to(workspace)}")


def build_agent_command(
    *,
    agent: str,
    model: str | None,
    prompt: str,
    prompt_file: Path,
    custom_command: str | None,
    extra_args: list[str],
    stdin_prompt: bool,
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
        cmd = ["codex", "exec"]
        if model:
            cmd += ["--model", model]
        cmd += extra_args
        cmd.append("-" if stdin_prompt else prompt)
        return cmd

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
    model: str | None,
    prompt: str,
    prompt_file: Path,
    workspace: Path,
    log_path: Path,
    custom_command: str | None,
    extra_args: list[str],
    runner: str,
    timeout_seconds: int,
) -> int:
    if runner == "auto":
        runner = "pexpect" if agent == "devin" else "subprocess"

    stdin_prompt = agent == "codex" and runner == "subprocess"

    cmd = build_agent_command(
        agent=agent,
        model=model,
        prompt=prompt,
        prompt_file=prompt_file,
        custom_command=custom_command,
        extra_args=extra_args,
        stdin_prompt=stdin_prompt,
    )

    printable = " ".join(shlex.quote(x if len(x) < 180 else x[:180] + "...") for x in cmd)

    eprint(f"Running ({runner}): {printable}")

    if runner == "pexpect":
        return run_agent_pexpect(cmd=cmd, workspace=workspace, log_path=log_path, timeout_seconds=timeout_seconds)

    if runner != "subprocess":
        raise SystemExit(f"Unknown runner: {runner}")

    with log_path.open("w", encoding="utf-8") as log:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(workspace),
                input=prompt if stdin_prompt else None,
                text=True,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=timeout_seconds if timeout_seconds > 0 else None,
            )
        except subprocess.TimeoutExpired:
            log.write(f"\nAgent timed out after {timeout_seconds} seconds.\n")
            return 124
    return int(proc.returncode)


def run_agent_pexpect(*, cmd: list[str], workspace: Path, log_path: Path, timeout_seconds: int) -> int:
    try:
        import pexpect
    except ImportError as exc:
        raise SystemExit("pexpect runner requires the pexpect package") from exc

    if not cmd:
        raise SystemExit("Agent command is empty")

    with log_path.open("w", encoding="utf-8") as log:
        child = pexpect.spawn(
            cmd[0],
            cmd[1:],
            cwd=str(workspace),
            encoding="utf-8",
            codec_errors="replace",
            timeout=None,
        )
        child.logfile_read = log
        try:
            child.expect(pexpect.EOF, timeout=timeout_seconds if timeout_seconds > 0 else None)
        except pexpect.TIMEOUT:
            log.write(f"\nAgent timed out after {timeout_seconds} seconds.\n")
            child.terminate(force=True)
            child.close()
            return 124
        child.close()
        return int(child.exitstatus if child.exitstatus is not None else child.signalstatus or 1)


def skeptic_prompt_section(*, enabled: bool) -> str:
    if not enabled:
        return "SKEPTIC MODE\nDisabled. Do not write skeptic_report.md or skeptic_conflicts.json.\n"

    return f"""SKEPTIC MODE (--skeptic)
Apply the Skeptic framework from https://github.com/saffih/skeptic/blob/main/skeptic.md as part of this run.

Required Skeptic flow:
- GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN.
- Start detect-only. Do not fix until findings are stabilized and DECIDE says FIX.
- Use all thinkers/checks: Charlie Munger (CH), Occam's Razor (OM), Richard Feynman (FE), Karl Popper (PO), Immanuel Kant (KT), and Saffi (SH).
- Track findings, unknowns, assumptions, evidence strength, skipped/uncertain areas, detection confidence, and evidence level.
- A safe FIX may update only the allowed sync targets for this run.
- A CONFLICT must not be patched in the conflicted area. It must be handed to the human with a decision_needed field.
- You may still close independent safe gaps while reporting unresolved conflicts.
- End as HANDLED or CONFLICT.

Skeptic must defend:
- HLD anchors and source-of-truth hierarchy
- spec boundaries and ownership
- contracts, dependencies, exceptions, acceptance criteria
- verification path, drift/failure modes, and human approval needs

Always include thinker-to-change trace in the form: "thinker found X, so we changed Y".

Required Skeptic artifacts:
WRITE FILE: {SYNC_SKEPTIC_REPORT_REL}
CONTENT:
# Skeptic Report

## Outcome
HANDLED or CONFLICT

## Thinker Trace
| Thinker/check | Found | Changed |
|---|---|---|
| Charlie Munger (CH) | ... | ... |

## Findings
- ...

## Fixes Applied
- ...

## Unresolved Conflicts
- ...

## Verification
- ...

WRITE FILE: {SYNC_SKEPTIC_CONFLICTS_REL}
CONTENT:
{{
  "status": "HANDLED|CONFLICT",
  "scope": "hld_spec_sync",
  "thinker_trace": [
    {{
      "thinker": "Charlie Munger (CH)",
      "found": "...",
      "changed": "..."
    }}
  ],
  "actions": [
    {{
      "id": "SK-ACTION-001",
      "status": "handled",
      "issue": "...",
      "root_cause": "...",
      "action": "...",
      "verification": "...",
      "evidence_level": "OBSERVED|REPRODUCED|HISTORICAL|INFERRED RISK"
    }}
  ],
  "conflicts": [
    {{
      "id": "SK-CONFLICT-001",
      "status": "unresolved",
      "issue": "...",
      "thesis": "...",
      "antithesis": "...",
      "tradeoffs": "...",
      "blocking_unknowns": ["..."],
      "missing_evidence": ["..."],
      "safe_recommendation": "...",
      "decision_needed": "..."
    }}
  ],
  "human_loop": "required|not_required"
}}
"""


def build_prompt(
    *,
    mode: str,
    hld_path: Path,
    numbered_hld: str,
    current_state: dict[str, str],
    report_only: bool,
    analyze_only: bool,
    skeptic: bool,
) -> str:
    if analyze_only:
        work_mode = "ANALYZE ONLY: Do not update constitution or specs. Write reports only."
    elif report_only:
        work_mode = "REPORT ONLY: Do not update specs. Write reports only."
    else:
        work_mode = "SYNC MODE: Update/create/deprecate constitution and specs as needed."

    if analyze_only or report_only:
        allowed_write_targets = "- .specify/sync/**"
    else:
        allowed_write_targets = "\n".join(
            [
                "- .specify/memory/constitution.md",
                "- .specify/sync/**",
                "- specs/<NNN-feature-slug>/spec.md",
            ]
        )

    return f"""You are a careful HLD-to-SpecKit synchronization agent.

USER GOAL
Maintain one large HLD as the parent source of truth while keeping:
- .specify/memory/constitution.md
- specs/*/spec.md (native Spec Kit feature specs)
- .specify/sync/spec_index.json
- .specify/sync/feature_graph.json
- missing/duplicate/drift/analyze reports

synchronized with that HLD.

MODE
{mode}

WORK MODE
{work_mode}

{skeptic_prompt_section(enabled=skeptic)}

IMPORTANT MODEL
Use the same algorithm for greenfield and brownfield:
- Desired state = what the HLD says should exist now.
- Current state = existing constitution/native Spec Kit specs/sync index/sync graph.
- In greenfield, current state is intentionally empty.
- Diff desired vs current.
- Create missing, update changed, deprecate removed/stale, report uncertain.

SOURCE OF TRUTH RULES
1. Constitution governs all specs and implementation.
2. HLD is the canonical parent source for system intent, architecture, work units, scope, and ordering.
3. Feature specs are derived living contracts, one per stable capability, written as native Spec Kit specs under specs/.
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
- Do not write any implementation files. This sync tool will reject WRITE FILE targets outside the allowed sync paths.
- Do not create tasks.md or plan.md.
- Do not create a new spec for every HLD change.
- Do not duplicate specs.
- Do not turn non-goals into features.
- Do not turn context-only architecture/rationale into unnecessary specs.
- Do not silently ignore missing feature coverage.
- Do not write sync metadata files into specs/. Keep specs/ for native Spec Kit feature directories only.
- Do not invent a parallel custom spec format.

DO
- Create/update .specify/memory/constitution.md.
- Create/update .specify/sync/spec_index.json.
- Create/update .specify/sync/feature_graph.json.
- Create/update .specify/sync/sync_report.md.
- Create/update .specify/sync/analyze_report.md.
- Create/update .specify/sync/missing_report.json.
- Create/update .specify/sync/duplicate_report.json.
- Create/update .specify/sync/drift_report.json.
- Create/update .specify/sync/constitution_change_report.md.
- Create/update specs/<NNN-feature-slug>/spec.md when not in analyze-only/report-only mode.
- Update existing related specs when HLD changes existing capabilities.
- Create a new spec only for a new independent capability.
- Mark removed/deprecated behavior clearly.
- Preserve HLD line anchors and quote anchors in every spec.
- Include HLD traceability in every spec without breaking the native Spec Kit template structure.
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
Every specs/<NNN-feature-slug>/spec.md MUST be a native Spec Kit feature spec matching .specify/templates/spec-template.md.

Use this section order and heading style:

# Feature Specification: <title>

**Feature Branch**: `[<NNN-feature-slug>]`

**Created**: <YYYY-MM-DD>

**Status**: Draft

**Input**: HLD-derived feature from `{hld_path}`; HLD lines <start-end>; anchor quote: "<exact quote>"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - <brief title> (Priority: P1)

<plain-language independently testable journey>

**Why this priority**: <why this is the first viable slice>

**Independent Test**: <how this story can be tested independently>

**Acceptance Scenarios**:

1. **Given** <state>, **When** <action>, **Then** <result>

### Edge Cases

- <edge case>

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: <technology-agnostic requirement>

### Key Entities *(include if feature involves data)*

- **<Entity>**: <what it represents and relationships>

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: <measurable outcome>

## Assumptions

- <assumption, dependency, or out-of-scope boundary>

## HLD Traceability

- Parent HLD: `{hld_path}`
- HLD lines: <start-end>
- Anchor quote: "<exact quote>"
- Source anchors:
  - HLD lines <start-end>: "<quote>"
- Related specs: <spec ids/paths>
- Sync status: synced|missing|drift|duplicate-risk|needs-review

Rules for native Spec Kit compatibility:
- Preserve the Spec Kit top-level sections and order.
- Do not use the old custom sections `## Source of Truth`, `## Constitution Checks`, `## Acceptance Criteria`, `## Dependencies`, or `## Traceability`.
- Put dependencies, blockers, non-goals, and open questions in Assumptions or HLD Traceability unless they need their own Spec Kit story/requirement.
- Use `[NEEDS CLARIFICATION: ...]` markers for unresolved ambiguity.

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
Allowed WRITE FILE targets are only:
{allowed_write_targets}

Example:
WRITE FILE: .specify/sync/sync_report.md
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
        description="Sync HLD -> constitution + SpecKit specs + missing/duplicate/drift/analyze reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Agent model defaults:\n"
            "  devin  -> swe-1.6\n"
            "  claude -> opus-4.6\n"
            "  codex  -> gpt-5.5\n"
            "  custom -> no default model\n\n"
            "Use --model to override the selected agent default."
        ),
    )
    ap.add_argument("--hld", required=True, help="Path to HLD markdown file")
    ap.add_argument("--workspace", default=".", help="Repo/workspace root")
    ap.add_argument("--agent", choices=["devin", "claude", "codex", "custom"], default="devin")
    ap.add_argument(
        "--model",
        default=None,
        help=(
            "Model to pass to the selected agent. Defaults by agent: "
            "devin=swe-1.6, claude=opus-4.6, codex=gpt-5.5. "
            "Custom has no default model."
        ),
    )
    ap.add_argument("--agent-command", default=None, help="For --agent custom. Supports {prompt_file} and {model}.")
    ap.add_argument("--agent-extra-arg", action="append", default=[])
    ap.add_argument(
        "--runner",
        choices=["auto", "subprocess", "pexpect"],
        default="auto",
        help="How to run the agent. Auto uses pexpect for Devin and subprocess for other agents.",
    )

    ap.add_argument("--mode", choices=["auto", "greenfield", "brownfield"], default="auto")
    ap.add_argument("--report-only", action="store_true")
    ap.add_argument("--analyze-only", action="store_true")
    ap.add_argument(
        "--skeptic",
        action="store_true",
        help="Apply Skeptic gap/conflict review, write skeptic reports, and exit 2 on unresolved conflicts.",
    )
    ap.add_argument("--prompt-only", action="store_true")
    ap.add_argument("--no-apply-write-blocks", action="store_true")

    ap.add_argument("--max-hld-chars", type=int, default=0, help="0 means no HLD truncation")
    ap.add_argument("--max-existing-spec-chars", type=int, default=16000)
    ap.add_argument("--max-existing-specs", type=int, default=80)
    ap.add_argument("--agent-timeout-seconds", type=int, default=0, help="0 means no timeout")
    args = ap.parse_args()

    if args.model is None:
        args.model = DEFAULT_AGENT_MODELS.get(args.agent)

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
    allow_sync_mutations = not args.report_only and not args.analyze_only

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
        skeptic=args.skeptic,
    )

    prompt_path = logs_dir / "prompt.md"
    log_path = logs_dir / "agent.log"
    write_text(prompt_path, prompt)

    print(f"Mode: {mode}")
    print(f"Agent: {args.agent}")
    print(f"Model: {args.model or '(none)'}")
    print(f"Skeptic: {args.skeptic}")
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
            runner=args.runner,
            timeout_seconds=args.agent_timeout_seconds,
        )
    except FileNotFoundError as exc:
        eprint(f"Agent binary not found: {exc}")
        return 127

    if rc != 0:
        run_summary = {
            "mode": mode,
            "agent": args.agent,
            "model": args.model,
            "hld": str(hld_path),
            "prompt": str(prompt_path),
            "log": str(log_path),
            "returncode": rc,
            "write_blocks_applied": 0,
            "validation_errors": [],
            "agent_timeout_seconds": args.agent_timeout_seconds,
            "skeptic": args.skeptic,
        }
        write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))
        eprint(f"Agent failed with rc={rc}. WRITE FILE blocks were not applied. See: {log_path}")
        return rc

    writes = 0
    if not args.no_apply_write_blocks:
        try:
            validate_write_targets(
                log_path,
                workspace,
                allow_constitution=allow_sync_mutations,
                allow_specs=allow_sync_mutations,
            )
            writes = apply_write_blocks(
                log_path,
                workspace,
                allow_constitution=allow_sync_mutations,
                allow_specs=allow_sync_mutations,
            )
        except Exception as exc:
            eprint(f"Failed to apply WRITE FILE blocks: {exc}")
            run_summary = {
                "mode": mode,
                "agent": args.agent,
                "model": args.model,
                "hld": str(hld_path),
                "prompt": str(prompt_path),
                "log": str(log_path),
                "returncode": rc,
                "write_blocks_applied": writes,
                "validation_errors": [f"failed to apply WRITE FILE blocks: {exc}"],
                "agent_timeout_seconds": args.agent_timeout_seconds,
                "skeptic": args.skeptic,
            }
            write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))
            return 1

    validation_errors = validate_outputs(
        workspace,
        require_constitution=allow_sync_mutations,
        require_specs=allow_sync_mutations,
    )
    skeptic_conflicts: list[dict[str, object]] = []
    if args.skeptic:
        skeptic_conflicts = evaluate_skeptic_outputs(
            workspace,
            report_rel=SYNC_SKEPTIC_REPORT_REL,
            conflicts_rel=SYNC_SKEPTIC_CONFLICTS_REL,
            errors=validation_errors,
        )

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
        "agent_timeout_seconds": args.agent_timeout_seconds,
        "skeptic": args.skeptic,
        "skeptic_conflicts_path": str((workspace / SYNC_SKEPTIC_CONFLICTS_REL).relative_to(workspace)) if args.skeptic else None,
        "skeptic_unresolved_conflicts": len(skeptic_conflicts),
    }
    write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))

    if validation_errors:
        eprint("Completed with validation errors:")
        for err in validation_errors:
            eprint(f"- {err}")
        eprint(f"See: {logs_dir / 'run_summary.json'}")
        return 1

    if skeptic_conflicts:
        print_skeptic_conflicts(skeptic_conflicts, SYNC_SKEPTIC_CONFLICTS_REL)
        eprint(f"Run summary: {logs_dir / 'run_summary.json'}")
        return CONFLICT_RETURN_CODE

    print("PASS")
    print("Updated files under:")
    print("- .specify/memory/constitution.md")
    print("- specs/ (native Spec Kit feature specs)")
    print("- .specify/sync/")
    print(f"Run summary: {logs_dir / 'run_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
