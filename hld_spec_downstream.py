#!/usr/bin/env -S uv run --script --no-project
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pexpect>=4.9.0",
# ]
# ///

"""
hld_spec_downstream.py

Continue after hld_spec_sync.py:
- read HLD, constitution, native Spec Kit specs, and .specify/sync reports
- analyze remaining gaps and blockers
- generate downstream Spec Kit artifacts such as plan.md, research.md,
  data-model.md, quickstart.md, contracts/, and tasks.md
- optionally allow implementation file writes to close gaps

Default behavior is planning-safe: implementation writes are blocked unless
--allow-implementation is set.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import shlex
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import hld_map


DEFAULT_AGENT_MODELS = {
    "devin": "swe-1.6",
    "claude": "opus-4.6",
    "codex": "gpt-5.5",
}

SPEC_DIR_REL = Path("specs")
SYNC_DIR_REL = Path(".specify") / "sync"
DOWNSTREAM_DIR_REL = SYNC_DIR_REL / "downstream"
STAGED_DIR_REL = SYNC_DIR_REL / "staged"
DOWNSTREAM_SKEPTIC_REPORT_REL = DOWNSTREAM_DIR_REL / "skeptic_report.md"
DOWNSTREAM_SKEPTIC_CONFLICTS_REL = DOWNSTREAM_DIR_REL / "skeptic_conflicts.json"
PLAN_ALLOWED_FILENAMES = {
    "plan.md",
    "research.md",
    "data-model.md",
    "quickstart.md",
}
TASK_ALLOWED_FILENAMES = {"tasks.md"}
SPEC_KIT_MANAGED_RELS = {".specify", "specs"}
PROTECTED_RELS = {
    ".git",
    ".agents",
    ".codex",
    "logs",
}
PROTECTED_PREFIXES = (".speckit",)
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


def parse_write_blocks_text(text: str, workspace: Path) -> list[dict[str, str]]:
    pattern = re.compile(
        r"^WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n(?P<content>.*?)(?=^WRITE FILE:|\Z)",
        re.DOTALL | re.MULTILINE,
    )
    writes: list[dict[str, str]] = []
    for match in pattern.finditer(text):
        raw_path = match.group("path").strip()
        content = match.group("content").rstrip() + "\n"
        out_path = Path(raw_path)
        if out_path.is_absolute():
            rel_path = out_path.resolve().relative_to(workspace.resolve())
        else:
            rel_path = out_path
        writes.append({"path": str(rel_path), "content": content})
    return writes


def stage_write_blocks(
    log_path: Path,
    workspace: Path,
    *,
    run_id: str,
    echoed_prompt: str | None = None,
) -> dict[str, object]:
    text = strip_echoed_prompt(read_text(log_path), echoed_prompt)
    writes = parse_write_blocks_text(text, workspace)
    staged_dir = workspace / STAGED_DIR_REL / run_id
    staged_dir.mkdir(parents=True, exist_ok=True)
    proposed_lines: list[str] = ["# Proposed Writes", ""]
    manifest_writes: list[dict[str, object]] = []
    for idx, write in enumerate(writes, start=1):
        rel_path = write["path"]
        staged_file = staged_dir / f"{idx:03d}" / rel_path
        write_text(staged_file, write["content"])
        proposed_lines.extend(
            [
                f"## {idx}. `{rel_path}`",
                "",
                "```text",
                write["content"].rstrip(),
                "```",
                "",
            ]
        )
        manifest_writes.append(
            {
                "path": rel_path,
                "staged_path": str(staged_file.relative_to(workspace)),
                "bytes": len(write["content"].encode("utf-8")),
            }
        )
    write_text(staged_dir / "proposed_writes.md", "\n".join(proposed_lines))
    manifest = {"run_id": run_id, "writes": manifest_writes}
    write_text(staged_dir / "write_manifest.json", json.dumps(manifest, indent=2))
    return {
        "staged_dir": str(staged_dir.relative_to(workspace)),
        "proposed_writes": str((staged_dir / "proposed_writes.md").relative_to(workspace)),
        "write_manifest": str((staged_dir / "write_manifest.json").relative_to(workspace)),
        "write_count": len(writes),
    }


def copy_validation_workspace(workspace: Path) -> tempfile.TemporaryDirectory[str]:
    tmp = tempfile.TemporaryDirectory()
    tmp_workspace = Path(tmp.name) / "workspace"

    def ignore(_dir_path: str, names: list[str]) -> set[str]:
        return {name for name in names if name in {".git", "logs", ".agents", ".codex"}}

    shutil.copytree(workspace, tmp_workspace, ignore=ignore)
    return tmp


def apply_staged_writes_to_workspace(
    *,
    staging_workspace: Path,
    target_workspace: Path,
    staging_info: dict[str, object],
    phase: str,
    allow_implementation: bool,
    implementation_roots: list[Path],
) -> int:
    staging_workspace = staging_workspace.resolve()
    target_workspace = target_workspace.resolve()
    implementation_roots = [root.resolve() for root in implementation_roots]
    manifest_path = staging_workspace / str(staging_info["write_manifest"])
    manifest = json.loads(read_text(manifest_path))
    count = 0

    for item in manifest.get("writes", []):
        rel_path = Path(str(item["path"]))
        staged_path = staging_workspace / str(item["staged_path"])
        out_path = (target_workspace / rel_path).resolve()

        validate_write_target(
            out_path,
            target_workspace,
            phase=phase,
            allow_implementation=allow_implementation,
            implementation_roots=implementation_roots,
        )

        write_text(out_path, read_text(staged_path))
        count += 1

    return count


def strip_echoed_prompt(text: str, prompt: str | None) -> str:
    if not prompt:
        return text
    prompt_idx = text.find(prompt)
    if prompt_idx >= 0:
        return (text[:prompt_idx] + text[prompt_idx + len(prompt):]).lstrip("\r\n")
    return text


def compact_middle(text: str, max_chars: int) -> str:
    if max_chars <= 0 or len(text) <= max_chars:
        return text

    marker = "\n\n[...TRUNCATED BY hld_spec_downstream.py...]\n\n"
    if max_chars <= len(marker):
        return marker[:max_chars]

    keep = max_chars - len(marker)
    head = keep // 2
    tail = keep - head
    return text[:head] + marker + text[-tail:]


def number_hld(hld_text: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(hld_text.splitlines(), start=1)) + "\n"


def json_or_text(path: Path, default: str = "") -> str:
    text = read_text(path, default)
    if not text.strip():
        return default
    try:
        return json.dumps(json.loads(text), indent=2)
    except Exception:
        return text


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


def find_spec_dirs(workspace: Path) -> list[Path]:
    specs_dir = workspace / SPEC_DIR_REL
    if not specs_dir.exists():
        return []
    return sorted(p for p in specs_dir.iterdir() if (p / "spec.md").is_file())


def parse_spec_id(spec_dir: Path) -> str:
    name = spec_dir.name
    match = re.match(r"^([0-9]{3,})-", name)
    return match.group(1) if match else name


def normalize_targets(targets: list[str]) -> list[str]:
    return targets or ["all"]


def spec_dir_matches_target(workspace: Path, spec_dir: Path, target: str) -> bool:
    rel = str(spec_dir.relative_to(workspace))
    spec_id = parse_spec_id(spec_dir)
    return target in {spec_id, spec_dir.name, rel}


def resolve_spec_dirs(workspace: Path, targets: list[str], *, strict: bool) -> list[Path]:
    all_dirs = find_spec_dirs(workspace)
    normalized_targets = normalize_targets(targets)
    if "all" in normalized_targets:
        if strict and len(normalized_targets) > 1:
            raise ValueError("--target all cannot be combined with other --target values")
        if strict and not all_dirs:
            raise ValueError("No specs/*/spec.md files found")
        return all_dirs

    selected: list[Path] = []
    missing: list[str] = []
    for target in normalized_targets:
        matches = [spec_dir for spec_dir in all_dirs if spec_dir_matches_target(workspace, spec_dir, target)]
        if not matches:
            missing.append(target)
            continue
        for spec_dir in matches:
            if spec_dir not in selected:
                selected.append(spec_dir)

    if strict and missing:
        raise ValueError(f"Unknown target(s): {', '.join(missing)}")
    if strict and not selected:
        raise ValueError("No selected specs found")
    return selected


def select_spec_dirs(workspace: Path, targets: list[str]) -> list[Path]:
    return resolve_spec_dirs(workspace, targets, strict=False)


def list_specs(workspace: Path, targets: list[str], max_chars_per_spec: int) -> str:
    spec_dirs = select_spec_dirs(workspace, targets)
    if not spec_dirs:
        return "No selected specs found.\n"

    parts: list[str] = []
    for idx, spec_dir in enumerate(spec_dirs, start=1):
        rel = spec_dir.relative_to(workspace)
        spec_text = compact_middle(read_text(spec_dir / "spec.md"), max_chars_per_spec)
        aux_parts = []
        for name in ["plan.md", "research.md", "data-model.md", "quickstart.md", "tasks.md"]:
            aux_path = spec_dir / name
            if aux_path.exists():
                aux_parts.append(f"\n--- EXISTING {name}: {rel / name} ---\n{compact_middle(read_text(aux_path), max_chars_per_spec // 2)}\n")
        parts.append(
            f"\n--- SELECTED SPEC {idx}: {rel}/spec.md ---\n"
            f"{spec_text}\n"
            f"{''.join(aux_parts)}"
            f"--- END SELECTED SPEC {idx} ---\n"
        )
    return "\n".join(parts)


def hld_spec_targets(section: hld_map.HldSection) -> list[str]:
    return [
        spec
        for spec in hld_map.split_metadata_list(section.metadata_value("HLD-SPECS"))
        if spec.upper() not in {"TBD", "CONSTITUTION"}
    ]



def target_hld_context(parsed_map: hld_map.HldMap, target_hld: str) -> tuple[str, dict[str, object]]:
    sections_by_id = parsed_map.section_by_id()
    if target_hld not in sections_by_id:
        raise ValueError(f"Unknown target HLD section: {target_hld}")

    queue: list[tuple[str, str, int]] = [(target_hld, "target", 0)]
    loaded: dict[str, str] = {}
    skipped_refs: list[dict[str, object]] = []

    while queue:
        section_id, reason, depth = queue.pop(0)
        if section_id in loaded:
            continue

        section = sections_by_id.get(section_id)
        if not section:
            skipped_refs.append(
                {
                    "section": section_id,
                    "reason": "missing-section",
                    "requested_by": reason,
                }
            )
            continue

        loaded[section_id] = reason

        max_depth = 2 if section.metadata_value("HLD-RISK").upper() == "HIGH" else 1
        if depth >= max_depth:
            for ref in section.references:
                if ref.target not in loaded:
                    skipped_refs.append(
                        {
                            "section": ref.target,
                            "reason": f"depth-limit-{max_depth}",
                            "requested_by": section.id,
                            "ref_kind": ref.kind,
                        }
                    )
            continue

        for ref in section.references:
            if ref.kind in {"DEPENDS", "BLOCKED_BY", "CONFLICTS_WITH"}:
                queue.append((ref.target, f"{ref.kind} from {section.id}", depth + 1))
            elif ref.kind == "REF":
                queue.append((ref.target, f"REF from {section.id}", depth + 1))

    parts = [
        "BOUNDED HLD MAP CONTEXT",
        "The full HLD is intentionally not included in this prompt.",
    ]

    for section_id, why in loaded.items():
        section = sections_by_id[section_id]
        parts.append(f"\n--- HLD SECTION {section.id}: {section.title} ({why}) ---\n{section.text}")

    target = sections_by_id[target_hld]
    report = {
        "target_section": target_hld,
        "loaded_sections": [
            {
                "id": section_id,
                "title": sections_by_id[section_id].title,
                "why_loaded": why,
                "line_start": sections_by_id[section_id].line_start,
                "line_end": sections_by_id[section_id].line_end,
            }
            for section_id, why in loaded.items()
        ],
        "skipped_refs": skipped_refs,
        "target_specs": hld_spec_targets(target),
    }
    return "\n".join(parts), report


def resolve_hld_targets(parsed_map: hld_map.HldMap, target_hld: str | None, targets: list[str]) -> list[str]:
    if not target_hld:
        return targets
    section = parsed_map.section_by_id().get(target_hld)
    if not section:
        raise ValueError(f"Unknown target HLD section: {target_hld}")
    spec_targets = hld_spec_targets(section)
    normalized_targets = normalize_targets(targets)
    if normalized_targets == ["all"] and spec_targets:
        return spec_targets
    if spec_targets and normalized_targets != ["all"]:
        unknown = [target for target in normalized_targets if target not in spec_targets]
        if unknown:
            raise ValueError(
                f"--target-hld {target_hld} maps to HLD-SPECS {', '.join(spec_targets)}; "
                f"inconsistent --target value(s): {', '.join(unknown)}"
            )
    return targets


def load_current_state(
    *,
    workspace: Path,
    hld_path: Path,
    targets: list[str],
    max_hld_chars: int,
    max_spec_chars: int,
) -> dict[str, str]:
    sync_dir = workspace / SYNC_DIR_REL
    return {
        "numbered_hld": compact_middle(number_hld(read_text(hld_path)), max_hld_chars),
        "constitution": read_text(workspace / ".specify" / "memory" / "constitution.md", "No constitution exists.\n"),
        "spec_index": json_or_text(sync_dir / "spec_index.json", "No spec_index.json exists.\n"),
        "feature_graph": json_or_text(sync_dir / "feature_graph.json", "No feature_graph.json exists.\n"),
        "sync_report": read_text(sync_dir / "sync_report.md", "No sync_report.md exists.\n"),
        "analyze_report": read_text(sync_dir / "analyze_report.md", "No analyze_report.md exists.\n"),
        "missing_report": json_or_text(sync_dir / "missing_report.json", "No missing_report.json exists.\n"),
        "duplicate_report": json_or_text(sync_dir / "duplicate_report.json", "No duplicate_report.json exists.\n"),
        "drift_report": json_or_text(sync_dir / "drift_report.json", "No drift_report.json exists.\n"),
        "constitution_change_report": read_text(
            sync_dir / "constitution_change_report.md",
            "No constitution_change_report.md exists.\n",
        ),
        "selected_specs": list_specs(workspace, targets, max_spec_chars),
    }


def is_protected_path(path: Path, workspace: Path) -> bool:
    rel = path.relative_to(workspace)
    if not rel.parts:
        return True
    first = rel.parts[0]
    return first in PROTECTED_RELS or first.startswith(PROTECTED_PREFIXES)


def is_speckit_managed_path(path: Path, workspace: Path) -> bool:
    rel = path.relative_to(workspace)
    return bool(rel.parts) and rel.parts[0] in SPEC_KIT_MANAGED_RELS


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def normalize_implementation_roots(workspace: Path, roots: list[str]) -> list[Path]:
    normalized: list[Path] = []
    workspace = workspace.resolve()
    for raw_root in roots:
        root = Path(raw_root)
        if not root.is_absolute():
            root = workspace / root
        root = root.resolve()
        try:
            root.relative_to(workspace)
        except ValueError as exc:
            raise ValueError(f"--implementation-root must be inside workspace: {raw_root}") from exc
        if root == workspace:
            raise ValueError("--implementation-root cannot be the workspace root")
        if is_protected_path(root, workspace):
            raise ValueError(f"--implementation-root cannot be protected path: {root.relative_to(workspace)}")
        if is_speckit_managed_path(root, workspace):
            raise ValueError(f"--implementation-root cannot be SpecKit-managed path: {root.relative_to(workspace)}")
        if root not in normalized:
            normalized.append(root)
    return normalized


def is_allowed_downstream_report(rel: Path, phase: str) -> bool:
    parts = rel.parts
    if len(parts) < 3 or parts[0] != ".specify" or parts[1] != "sync" or parts[2] != "downstream":
        return False
    if rel.name == "implementation_closure_report.md":
        return phase in {"implement", "all"}
    return True


def is_allowed_spec_artifact(rel: Path, phase: str) -> bool:
    parts = rel.parts
    if len(parts) < 3 or parts[0] != "specs":
        return False

    filename = parts[-1]
    if phase in {"plan", "all"}:
        if filename in PLAN_ALLOWED_FILENAMES:
            return True
        if "contracts" in parts[2:]:
            return True
        if "checklists" in parts[2:]:
            return True

    if phase in {"tasks", "all"} and filename in TASK_ALLOWED_FILENAMES:
        return True

    return False


def is_allowed_non_impl_path(path: Path, workspace: Path, *, phase: str) -> bool:
    rel = path.relative_to(workspace)
    parts = rel.parts
    if not parts:
        return False

    if is_protected_path(path, workspace):
        return False

    if is_allowed_downstream_report(rel, phase):
        return True

    if is_allowed_spec_artifact(rel, phase):
        return True

    return False


def is_allowed_implementation_path(path: Path, workspace: Path, implementation_roots: list[Path]) -> bool:
    if is_protected_path(path, workspace):
        return False
    if is_speckit_managed_path(path, workspace):
        return False
    return any(is_relative_to(path, root) for root in implementation_roots)


def validate_write_target(
    out_path: Path,
    workspace: Path,
    *,
    phase: str,
    allow_implementation: bool,
    implementation_roots: list[Path],
) -> None:
    try:
        out_path.relative_to(workspace)
    except ValueError as exc:
        raise RuntimeError(f"Refusing to write outside workspace: {out_path}") from exc

    rel = out_path.relative_to(workspace)
    if is_protected_path(out_path, workspace):
        raise RuntimeError(f"Refusing protected write target: {rel}")

    if is_allowed_non_impl_path(out_path, workspace, phase=phase):
        return

    if allow_implementation and is_allowed_implementation_path(out_path, workspace, implementation_roots):
        return

    if allow_implementation:
        roots = ", ".join(str(root.relative_to(workspace)) for root in implementation_roots) or "(none)"
        raise RuntimeError(f"Refusing implementation write outside --implementation-root ({roots}): {rel}")

    raise RuntimeError(f"Refusing implementation write without --allow-implementation: {rel}")


def iter_write_block_paths(log_path: Path, workspace: Path) -> list[Path]:
    text = read_text(log_path)
    pattern = re.compile(r"^WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n", re.MULTILINE)
    workspace = workspace.resolve()
    paths: list[Path] = []
    for match in pattern.finditer(text):
        raw_path = match.group("path").strip()
        out_path = Path(raw_path)
        if not out_path.is_absolute():
            out_path = workspace / out_path
        paths.append(out_path.resolve())
    return paths


def validate_write_targets(
    log_path: Path,
    workspace: Path,
    *,
    phase: str,
    allow_implementation: bool,
    implementation_roots: list[Path],
    echoed_prompt: str | None = None,
) -> None:
    workspace = workspace.resolve()
    text = strip_echoed_prompt(read_text(log_path), echoed_prompt)
    pattern = re.compile(r"^WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n", re.MULTILINE)
    for match in pattern.finditer(text):
        raw_path = match.group("path").strip()
        out_path = Path(raw_path)
        if not out_path.is_absolute():
            out_path = workspace / out_path
        out_path = out_path.resolve()
        validate_write_target(
            out_path,
            workspace,
            phase=phase,
            allow_implementation=allow_implementation,
            implementation_roots=implementation_roots,
        )


def apply_write_blocks(
    log_path: Path,
    workspace: Path,
    *,
    phase: str,
    allow_implementation: bool,
    implementation_roots: list[Path],
    echoed_prompt: str | None = None,
) -> int:
    text = strip_echoed_prompt(read_text(log_path), echoed_prompt)
    pattern = re.compile(
        r"^WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n(?P<content>.*?)(?=^WRITE FILE:|\Z)",
        re.DOTALL | re.MULTILINE,
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

        validate_write_target(
            out_path,
            workspace,
            phase=phase,
            allow_implementation=allow_implementation,
            implementation_roots=implementation_roots,
        )

        write_text(out_path, content)
        count += 1

    return count


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
        cmd = ["devin", "--prompt-file", str(prompt_file)]
        if model:
            cmd += ["--model", model]
        return cmd + extra_args

    if agent == "claude":
        cmd = ["claude", "-p", prompt]
        if model:
            cmd += ["--model", model]
        return cmd + extra_args

    if agent == "codex":
        cmd = ["codex", "exec"]
        if model:
            cmd += ["--model", model]
        cmd += extra_args
        cmd.append("-" if stdin_prompt else prompt)
        return cmd

    if agent == "custom":
        if not custom_command:
            raise SystemExit("--agent custom requires --agent-command")
        rendered = custom_command.replace("{prompt_file}", str(prompt_file)).replace("{model}", model or "")
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


def phase_write_policy(phase: str, *, skeptic: bool) -> str:
    base_reports = "- .specify/sync/downstream/downstream_analysis.md\n- .specify/sync/downstream/gap_closure_plan.md"
    implementation_report = "- .specify/sync/downstream/implementation_closure_report.md"
    plan_artifacts = "\n".join(
        [
            "- specs/<NNN-feature-slug>/plan.md",
            "- specs/<NNN-feature-slug>/research.md",
            "- specs/<NNN-feature-slug>/data-model.md",
            "- specs/<NNN-feature-slug>/quickstart.md",
            "- specs/<NNN-feature-slug>/contracts/<contract-name>",
            "- specs/<NNN-feature-slug>/checklists/requirements.md",
        ]
    )
    task_artifacts = "- specs/<NNN-feature-slug>/tasks.md"

    skeptic_artifacts = "\n".join(
        [
            "- .specify/sync/downstream/skeptic_report.md",
            "- .specify/sync/downstream/skeptic_conflicts.json",
        ]
    )
    suffix = f"\n{skeptic_artifacts}" if skeptic else ""

    if phase == "analyze":
        return f"{base_reports}{suffix}"
    if phase == "plan":
        return f"{base_reports}\n{plan_artifacts}{suffix}"
    if phase == "tasks":
        return f"{base_reports}\n{task_artifacts}{suffix}"
    if phase == "implement":
        return f"{base_reports}\n{implementation_report}{suffix}"
    return f"{base_reports}\n{implementation_report}\n{plan_artifacts}\n{task_artifacts}{suffix}"


def skeptic_prompt_section(*, enabled: bool, phase: str, allow_implementation: bool) -> str:
    if not enabled:
        return "SKEPTIC MODE\nDisabled. Do not write skeptic_report.md or skeptic_conflicts.json.\n"

    fix_boundary = (
        "Safe implementation fixes are allowed only under --implementation-root paths."
        if allow_implementation
        else "Implementation fixes are not allowed in this run; produce handoff/blockers instead."
    )

    return f"""SKEPTIC MODE (--skeptic)
Apply the Skeptic framework from https://github.com/saffih/skeptic/blob/main/skeptic.md as part of this downstream phase.

Required Skeptic flow:
- GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN.
- Start detect-only. Do not fix until findings are stabilized and DECIDE says FIX.
- Use all thinkers/checks: Charlie Munger (CH), Occam's Razor (OM), Richard Feynman (FE), Karl Popper (PO), Immanuel Kant (KT), and Saffi (SH).
- Track findings, unknowns, assumptions, evidence strength, skipped/uncertain areas, detection confidence, and evidence level.
- A safe FIX may update only the allowed write targets for phase `{phase}`.
- {fix_boundary}
- A CONFLICT must not be patched in the conflicted area. It must be handed to the human with a decision_needed field.
- You may still close independent safe gaps while reporting unresolved conflicts.
- End as HANDLED or CONFLICT.

Skeptic must defend:
- HLD anchors and source-of-truth hierarchy
- downstream artifact boundaries and ownership
- contracts, dependencies, exceptions, acceptance criteria
- verification path, drift/failure modes, and human approval needs

Always include thinker-to-change trace in the form: "thinker found X, so we changed Y".

Required Skeptic artifacts:
WRITE FILE: {DOWNSTREAM_SKEPTIC_REPORT_REL}
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

WRITE FILE: {DOWNSTREAM_SKEPTIC_CONFLICTS_REL}
CONTENT:
{{
  "status": "HANDLED|CONFLICT",
  "scope": "hld_spec_downstream:{phase}",
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
    hld_path: Path,
    phase: str,
    allow_implementation: bool,
    implementation_roots: list[Path],
    targets: list[str],
    state: dict[str, str],
    skeptic: bool,
) -> str:
    if allow_implementation:
        root_text = ", ".join(str(root) for root in implementation_roots)
        implementation_policy = (
            "IMPLEMENTATION WRITES ARE ALLOWED only under these implementation roots: "
            f"{root_text}. Protected paths are still forbidden."
        )
    else:
        implementation_policy = "IMPLEMENTATION WRITES ARE FORBIDDEN. Write only specs/, .specify/memory/, and .specify/sync/ artifacts."

    target_text = ", ".join(targets) if targets else "all"

    return f"""You are a careful HLD-to-SpecKit downstream closure agent.

USER GOAL
Continue after HLD sync and drive downstream work toward implementation closure.

SOURCE OF TRUTH
- Parent HLD: {hld_path}
- Native Spec Kit feature specs: specs/<NNN-feature-slug>/spec.md
- HLD sync metadata: .specify/sync/
- Constitution: .specify/memory/constitution.md

PHASE
{phase}

TARGETS
{target_text}

IMPLEMENTATION POLICY
{implementation_policy}
Protected paths are always forbidden: .git/, .agents/, .codex/, logs/, and .speckit* paths.

{skeptic_prompt_section(enabled=skeptic, phase=phase, allow_implementation=allow_implementation)}

CORE RULES
1. HLD remains the canonical parent source.
2. Feature specs must remain native Spec Kit artifacts.
3. Do not invent a parallel spec format.
4. Treat .specify/sync/* reports as evidence for gaps, drift, duplicate risks, and blockers.
5. Close gaps downstream by producing the next Spec Kit artifacts needed for planning and implementation.
6. If a gap cannot be closed safely from available evidence, mark it NEEDS_REVIEW and explain the missing decision.

PHASE MEANING
- analyze: create/update .specify/sync/downstream/downstream_analysis.md and gap_closure_plan.md only.
- plan: create/update plan.md, research.md, data-model.md, quickstart.md, and contracts/ for target specs when evidence is sufficient.
- tasks: create/update tasks.md for target specs when plan artifacts are sufficient.
- implement: close implementation gaps only if implementation writes are allowed; otherwise produce an implementation handoff and blockers.
- all: perform analyze, plan, tasks, and implementation handoff; only modify implementation files if implementation writes are allowed.

REQUIRED DOWNSTREAM REPORTS
Always write:
WRITE FILE: .specify/sync/downstream/downstream_analysis.md
CONTENT:
# Downstream Analysis
...

WRITE FILE: .specify/sync/downstream/gap_closure_plan.md
CONTENT:
# Gap Closure Plan
...

If phase is implement or all, also write:
WRITE FILE: .specify/sync/downstream/implementation_closure_report.md
CONTENT:
# Implementation Closure Report
...

SPEC KIT ARTIFACT RULES
When writing downstream Spec Kit artifacts, use these locations:
- specs/<NNN-feature-slug>/plan.md
- specs/<NNN-feature-slug>/research.md
- specs/<NNN-feature-slug>/data-model.md
- specs/<NNN-feature-slug>/quickstart.md
- specs/<NNN-feature-slug>/contracts/<contract-name>
- specs/<NNN-feature-slug>/tasks.md
- specs/<NNN-feature-slug>/checklists/requirements.md

OUTPUT FORMAT
You MUST output all file changes using WRITE FILE blocks only.
Allowed non-implementation WRITE FILE targets for this phase are only:
{phase_write_policy(phase, skeptic=skeptic)}

CURRENT CONSTITUTION
{state["constitution"]}

CURRENT SPEC INDEX
{state["spec_index"]}

CURRENT FEATURE GRAPH
{state["feature_graph"]}

CURRENT SYNC REPORT
{state["sync_report"]}

CURRENT ANALYZE REPORT
{state["analyze_report"]}

CURRENT MISSING REPORT
{state["missing_report"]}

CURRENT DUPLICATE REPORT
{state["duplicate_report"]}

CURRENT DRIFT REPORT
{state["drift_report"]}

CURRENT CONSTITUTION CHANGE REPORT
{state["constitution_change_report"]}

SELECTED SPECS AND EXISTING DOWNSTREAM ARTIFACTS
{state["selected_specs"]}

NUMBERED HLD INPUT
{state["numbered_hld"]}
"""


def validate_workspace(workspace: Path, phase: str, targets: list[str]) -> list[str]:
    errors: list[str] = []
    if not (workspace / ".specify" / "memory" / "constitution.md").exists():
        errors.append("missing .specify/memory/constitution.md")
    if not (workspace / SYNC_DIR_REL / "spec_index.json").exists():
        errors.append("missing .specify/sync/spec_index.json")
    try:
        selected_spec_dirs = resolve_spec_dirs(workspace, targets, strict=True)
    except ValueError as exc:
        errors.append(str(exc))
        selected_spec_dirs = []

    if not find_spec_dirs(workspace):
        errors.append("no specs/*/spec.md files found")
    if phase in {"analyze", "plan", "tasks", "implement", "all"}:
        if not (workspace / DOWNSTREAM_DIR_REL / "downstream_analysis.md").exists():
            errors.append("missing .specify/sync/downstream/downstream_analysis.md")
        if not (workspace / DOWNSTREAM_DIR_REL / "gap_closure_plan.md").exists():
            errors.append("missing .specify/sync/downstream/gap_closure_plan.md")
    if phase in {"plan", "all"}:
        for spec_dir in selected_spec_dirs:
            if not (spec_dir / "plan.md").exists():
                errors.append(f"missing {spec_dir.relative_to(workspace) / 'plan.md'}")
    if phase in {"tasks", "all"}:
        for spec_dir in selected_spec_dirs:
            if not (spec_dir / "tasks.md").exists():
                errors.append(f"missing {spec_dir.relative_to(workspace) / 'tasks.md'}")
    if phase in {"implement", "all"} and not (workspace / DOWNSTREAM_DIR_REL / "implementation_closure_report.md").exists():
        errors.append("missing .specify/sync/downstream/implementation_closure_report.md")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Continue HLD-derived Spec Kit specs downstream toward gap closure and implementation readiness.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Agent model defaults:\n"
            "  devin  -> swe-1.6\n"
            "  claude -> opus-4.6\n"
            "  codex  -> gpt-5.5\n"
            "  custom -> no default model"
        ),
    )
    ap.add_argument("--hld", required=True, help="Path to HLD markdown file")
    ap.add_argument("--workspace", default=".", help="Repo/workspace root")
    ap.add_argument("--phase", choices=["analyze", "plan", "tasks", "implement", "all"], default="all")
    ap.add_argument("--target", action="append", default=[], help="Spec id, directory name, or path. Repeatable. Default: all")
    ap.add_argument(
        "--allow-implementation",
        action="store_true",
        help="Allow WRITE FILE blocks outside specs/.specify sync artifacts, limited to --implementation-root paths",
    )
    ap.add_argument(
        "--implementation-root",
        action="append",
        default=[],
        help="Implementation path allowed when --allow-implementation is set. Repeatable. Must be inside workspace.",
    )
    ap.add_argument("--agent", choices=["devin", "claude", "codex", "custom"], default="devin")
    ap.add_argument("--model", default=None)
    ap.add_argument("--agent-command", default=None, help="For --agent custom. Supports {prompt_file} and {model}.")
    ap.add_argument("--agent-extra-arg", action="append", default=[])
    ap.add_argument(
        "--runner",
        choices=["auto", "subprocess", "pexpect"],
        default="auto",
        help="How to run the agent. Auto uses pexpect for Devin and subprocess for other agents.",
    )
    ap.add_argument(
        "--skeptic",
        action="store_true",
        help="Apply Skeptic gap/conflict review, write skeptic reports, and exit 2 on unresolved conflicts.",
    )
    ap.add_argument("--prompt-only", action="store_true")
    ap.add_argument("--no-apply-write-blocks", action="store_true")
    ap.add_argument("--hld-map-only", action="store_true", help="Parse/validate HLD map artifacts and exit without agent.")
    ap.add_argument("--use-hld-map", action="store_true", help="Use HLD section map for bounded context selection.")
    ap.add_argument("--target-hld", default=None, help="Target one HLD section such as HLD-007 for map-aware runs.")
    ap.add_argument("--max-hld-chars", type=int, default=0, help="0 means no HLD truncation")
    ap.add_argument(
        "--allow-full-hld-context",
        action="store_true",
        help=(
            "Allow downstream prompts to include the full HLD when --use-hld-map is not used "
            "and --max-hld-chars is 0. Use only with explicit human approval."
        ),
    )
    ap.add_argument("--max-spec-chars", type=int, default=18000)
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

    parsed_hld_map: hld_map.HldMap | None = None
    context_selection: dict[str, object] | None = None
    if args.hld_map_only or args.use_hld_map:
        parsed_hld_map = hld_map.parse_hld_file(hld_path)
        map_outputs = hld_map.write_hld_map_outputs(parsed_hld_map, workspace)
        if parsed_hld_map.validation_errors:
            eprint("Invalid HLD map:")
            for error in parsed_hld_map.validation_errors:
                eprint(f"- {error}")
            return 1
        if args.hld_map_only:
            print("HLD map generated:")
            for key, value in map_outputs.items():
                if key != "sections":
                    print(f"- {key}: {value}")
            print(f"- sections: {len(map_outputs['sections'])}")
            return 0

    targets = normalize_targets(args.target)
    if parsed_hld_map is not None and args.target_hld:
        try:
            targets = normalize_targets(resolve_hld_targets(parsed_hld_map, args.target_hld, args.target))
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
    try:
        resolve_spec_dirs(workspace, targets, strict=True)
        implementation_roots = normalize_implementation_roots(workspace, args.implementation_root)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.allow_implementation and not implementation_roots:
        raise SystemExit("--allow-implementation requires at least one --implementation-root")

    if not args.use_hld_map and args.max_hld_chars == 0 and not args.allow_full_hld_context:
        raise SystemExit(
            "Refusing to build an unbounded downstream prompt: --use-hld-map was not provided "
            "and --max-hld-chars is 0. Use --use-hld-map --target-hld for bounded downstream "
            "context, set --max-hld-chars to an explicit limit, or pass --allow-full-hld-context "
            "only with explicit human approval."
        )

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    logs_dir = workspace / "logs" / "hld_spec_downstream" / ts
    logs_dir.mkdir(parents=True, exist_ok=True)

    state = load_current_state(
        workspace=workspace,
        hld_path=hld_path,
        targets=targets,
        max_hld_chars=args.max_hld_chars,
        max_spec_chars=args.max_spec_chars,
    )
    if args.use_hld_map:
        if not args.target_hld:
            raise SystemExit("--use-hld-map requires --target-hld for downstream bounded context")
        assert parsed_hld_map is not None
        try:
            state["numbered_hld"], context_selection = target_hld_context(parsed_hld_map, args.target_hld)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        write_text(logs_dir / "context_selection.json", json.dumps(context_selection, indent=2))

    write_text(logs_dir / "hld_numbered.md", state["numbered_hld"])
    prompt = build_prompt(
        hld_path=hld_path,
        phase=args.phase,
        allow_implementation=args.allow_implementation,
        implementation_roots=implementation_roots,
        targets=targets,
        state=state,
        skeptic=args.skeptic,
    )

    prompt_path = logs_dir / "prompt.md"
    log_path = logs_dir / "agent.log"
    write_text(prompt_path, prompt)

    print(f"Phase: {args.phase}")
    print(f"Targets: {', '.join(targets)}")
    print(f"Allow implementation: {args.allow_implementation}")
    if implementation_roots:
        print("Implementation roots:")
        for root in implementation_roots:
            print(f"- {root.relative_to(workspace)}")
    print(f"Agent: {args.agent}")
    print(f"Model: {args.model or '(none)'}")
    print(f"Skeptic: {args.skeptic}")
    print(f"HLD map: {args.use_hld_map}")
    if args.target_hld:
        print(f"Target HLD: {args.target_hld}")
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
        summary = {
            "phase": args.phase,
            "targets": targets,
            "allow_implementation": args.allow_implementation,
            "agent": args.agent,
            "model": args.model,
            "hld": str(hld_path),
            "prompt": str(prompt_path),
            "log": str(log_path),
            "returncode": rc,
            "write_blocks_applied": 0,
            "validation_errors": [],
            "implementation_roots": [str(root.relative_to(workspace)) for root in implementation_roots],
            "agent_timeout_seconds": args.agent_timeout_seconds,
            "skeptic": args.skeptic,
            "use_hld_map": args.use_hld_map,
            "target_hld": args.target_hld,
            "allow_full_hld_context": args.allow_full_hld_context,
            "context_selection": context_selection,
        }
        write_text(logs_dir / "run_summary.json", json.dumps(summary, indent=2))
        eprint(f"Agent failed with rc={rc}. WRITE FILE blocks were not applied. See: {log_path}")
        return rc

    writes = 0
    staging_info: dict[str, object] | None = None
    if not args.no_apply_write_blocks:
        try:
            validate_write_targets(
                log_path=log_path,
                workspace=workspace,
                phase=args.phase,
                allow_implementation=args.allow_implementation,
                implementation_roots=implementation_roots,
                echoed_prompt=prompt,
            )
            if args.use_hld_map:
                staging_info = stage_write_blocks(
                    log_path,
                    workspace,
                    run_id=ts,
                    echoed_prompt=prompt,
                )
                tmp_holder = copy_validation_workspace(workspace)
                try:
                    tmp_workspace = Path(tmp_holder.name) / "workspace"
                    tmp_implementation_roots = [
                        tmp_workspace / root.relative_to(workspace)
                        for root in implementation_roots
                    ]
                    apply_staged_writes_to_workspace(
                        staging_workspace=workspace,
                        target_workspace=tmp_workspace,
                        staging_info=staging_info,
                        phase=args.phase,
                        allow_implementation=args.allow_implementation,
                        implementation_roots=tmp_implementation_roots,
                    )
                    staged_validation_errors = validate_workspace(tmp_workspace, args.phase, targets)
                    if args.skeptic:
                        evaluate_skeptic_outputs(
                            tmp_workspace,
                            report_rel=DOWNSTREAM_SKEPTIC_REPORT_REL,
                            conflicts_rel=DOWNSTREAM_SKEPTIC_CONFLICTS_REL,
                            errors=staged_validation_errors,
                        )
                    if staged_validation_errors:
                        raise RuntimeError(
                            "staged validation failed before apply: "
                            + "; ".join(staged_validation_errors)
                        )
                    writes = apply_staged_writes_to_workspace(
                        staging_workspace=workspace,
                        target_workspace=workspace,
                        staging_info=staging_info,
                        phase=args.phase,
                        allow_implementation=args.allow_implementation,
                        implementation_roots=implementation_roots,
                    )
                finally:
                    tmp_holder.cleanup()
            else:
                writes = apply_write_blocks(
                    log_path=log_path,
                    workspace=workspace,
                    phase=args.phase,
                    allow_implementation=args.allow_implementation,
                    implementation_roots=implementation_roots,
                    echoed_prompt=prompt,
                )
        except Exception as exc:
            eprint(f"Failed to apply WRITE FILE blocks: {exc}")
            summary = {
                "phase": args.phase,
                "targets": targets,
                "allow_implementation": args.allow_implementation,
                "implementation_roots": [str(root.relative_to(workspace)) for root in implementation_roots],
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
                "use_hld_map": args.use_hld_map,
                "target_hld": args.target_hld,
                "allow_full_hld_context": args.allow_full_hld_context,
                "context_selection": context_selection,
                "staging": staging_info,
            }
            write_text(logs_dir / "run_summary.json", json.dumps(summary, indent=2))
            return 1

    validation_errors = validate_workspace(workspace, args.phase, targets)
    skeptic_conflicts: list[dict[str, object]] = []
    if args.skeptic:
        skeptic_conflicts = evaluate_skeptic_outputs(
            workspace,
            report_rel=DOWNSTREAM_SKEPTIC_REPORT_REL,
            conflicts_rel=DOWNSTREAM_SKEPTIC_CONFLICTS_REL,
            errors=validation_errors,
        )
    summary = {
        "phase": args.phase,
        "targets": targets,
        "allow_implementation": args.allow_implementation,
        "implementation_roots": [str(root.relative_to(workspace)) for root in implementation_roots],
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
        "use_hld_map": args.use_hld_map,
        "target_hld": args.target_hld,
        "allow_full_hld_context": args.allow_full_hld_context,
        "context_selection": context_selection,
        "staging": staging_info,
        "skeptic_conflicts_path": (
            str((workspace / DOWNSTREAM_SKEPTIC_CONFLICTS_REL).relative_to(workspace)) if args.skeptic else None
        ),
        "skeptic_unresolved_conflicts": len(skeptic_conflicts),
    }
    write_text(logs_dir / "run_summary.json", json.dumps(summary, indent=2))

    if validation_errors:
        eprint("Completed with validation errors:")
        for err in validation_errors:
            eprint(f"- {err}")
        eprint(f"See: {logs_dir / 'run_summary.json'}")
        return 1

    if skeptic_conflicts:
        print_skeptic_conflicts(skeptic_conflicts, DOWNSTREAM_SKEPTIC_CONFLICTS_REL)
        eprint(f"Run summary: {logs_dir / 'run_summary.json'}")
        return CONFLICT_RETURN_CODE

    print("PASS")
    print("Updated downstream artifacts under:")
    print("- .specify/sync/downstream/")
    print("- specs/<NNN-feature-slug>/")
    if args.allow_implementation:
        print("- implementation files under --implementation-root")
    print(f"Run summary: {logs_dir / 'run_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
