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
import hashlib
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

FEATURE_SPECS_REL = Path("specs")
SYNC_REL = Path(".specify") / "sync"
SYNC_SKEPTIC_REPORT_REL = SYNC_REL / "skeptic_report.md"
SYNC_SKEPTIC_CONFLICTS_REL = SYNC_REL / "skeptic_conflicts.json"
RUN_STATE_REL = SYNC_REL / "chunks" / "run_state.json"
SYNC_ALLOWED_SPEC_FILENAMES = {"spec.md"}
STAGED_REL = SYNC_REL / "staged"
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


def stable_hash(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def section_state(section: hld_map.HldSection) -> dict[str, object]:
    return {
        "section_id": section.id,
        "content_hash": hashlib.sha256(section.text.encode("utf-8")).hexdigest(),
        "metadata_hash": stable_hash({key: section.metadata_values(key) for key in sorted(section.metadata)}),
        "refs_hash": stable_hash([ref.to_dict() for ref in section.references]),
        "related_specs": hld_map.split_metadata_list(section.metadata_value("HLD-SPECS")),
    }


def load_run_state(workspace: Path) -> dict[str, object]:
    path = workspace / RUN_STATE_REL
    if not path.exists():
        return {"sections": {}}
    try:
        data = json.loads(read_text(path))
    except Exception:
        return {"sections": {}}
    if not isinstance(data, dict):
        return {"sections": {}}
    data.setdefault("sections", {})
    return data


def write_run_state(workspace: Path, state: dict[str, object]) -> None:
    write_text(workspace / RUN_STATE_REL, json.dumps(state, indent=2, sort_keys=True))


def target_required_section_ids(parsed_map: hld_map.HldMap, target_hld: str) -> list[str]:
    # Return target-context section IDs that should invalidate --resume.
    #
    # This intentionally includes normal REF links, not only required refs,
    # because map-aware target prompts load normal REF sections when depth
    # allows. Resume must not skip a run when any loaded context section changed.
    sections_by_id = parsed_map.section_by_id()
    if target_hld not in sections_by_id:
        return []

    queue: list[tuple[str, int]] = [(target_hld, 0)]
    ids: list[str] = []
    seen: set[str] = set()

    while queue:
        section_id, depth = queue.pop(0)
        if section_id in seen or section_id not in sections_by_id:
            continue

        seen.add(section_id)
        ids.append(section_id)

        section = sections_by_id[section_id]
        max_depth = 2 if section.metadata_value("HLD-RISK").upper() == "HIGH" else 1
        if depth >= max_depth:
            continue

        for ref in section.references:
            if ref.target in sections_by_id:
                queue.append((ref.target, depth + 1))

    return ids


def resume_skip_reason(workspace: Path, parsed_map: hld_map.HldMap, target_hld: str) -> str | None:
    state = load_run_state(workspace)
    sections_state = state.get("sections", {})
    if not isinstance(sections_state, dict):
        return None
    sections_by_id = parsed_map.section_by_id()
    for section_id in target_required_section_ids(parsed_map, target_hld):
        current = section_state(sections_by_id[section_id])
        saved = sections_state.get(section_id)
        if not isinstance(saved, dict):
            return None
        for key in ("content_hash", "metadata_hash", "refs_hash"):
            if saved.get(key) != current[key]:
                return None
        if section_id == target_hld and saved.get("status") != "done":
            return None
    return f"{target_hld} and loaded HLD context sections are unchanged and already done"


def update_run_state(
    workspace: Path,
    parsed_map: hld_map.HldMap,
    target_hld: str | None,
    *,
    status: str,
    prompt_path: Path,
    log_path: Path,
    staged_output_path: str | None,
) -> None:
    if not target_hld:
        return
    state = load_run_state(workspace)
    sections_state = state.setdefault("sections", {})
    if not isinstance(sections_state, dict):
        sections_state = {}
        state["sections"] = sections_state
    sections_by_id = parsed_map.section_by_id()
    for section_id in target_required_section_ids(parsed_map, target_hld):
        current = section_state(sections_by_id[section_id])
        current.update(
            {
                "status": status if section_id == target_hld else "done",
                "prompt_path": str(prompt_path.relative_to(workspace)),
                "log_path": str(log_path.relative_to(workspace)),
                "staged_output_path": staged_output_path,
            }
        )
        sections_state[section_id] = current
    write_run_state(workspace, state)


def number_hld(hld_text: str) -> str:
    return "\n".join(f"{i}: {line}" for i, line in enumerate(hld_text.splitlines(), start=1)) + "\n"


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
        if not out_path.is_absolute():
            rel_path = out_path
        else:
            rel_path = out_path.resolve().relative_to(workspace.resolve())
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
    staged_dir = workspace / STAGED_REL / run_id
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
    allow_constitution: bool,
    allow_specs: bool,
) -> int:
    staging_workspace = staging_workspace.resolve()
    target_workspace = target_workspace.resolve()
    manifest_path = staging_workspace / str(staging_info["write_manifest"])
    manifest = json.loads(read_text(manifest_path))
    count = 0

    for item in manifest.get("writes", []):
        rel_path = Path(str(item["path"]))
        staged_path = staging_workspace / str(item["staged_path"])
        out_path = (target_workspace / rel_path).resolve()

        if not is_sync_allowed_path(
            out_path,
            target_workspace,
            allow_constitution=allow_constitution,
            allow_specs=allow_specs,
        ):
            raise RuntimeError(f"Refusing disallowed sync write target: {rel_path}")

        write_text(out_path, read_text(staged_path))
        count += 1

    return count


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


def spec_paths_for_ids(workspace: Path, spec_ids: list[str], max_chars_per_spec: int) -> tuple[str, list[str]]:
    parts: list[str] = []
    included: list[str] = []
    if not spec_ids:
        return "No HLD-SPECS metadata selected.\n", included
    for spec_id in spec_ids:
        if spec_id.upper() in {"TBD", "CONSTITUTION"}:
            continue
        matches = sorted((workspace / FEATURE_SPECS_REL).glob(f"{spec_id}-*/spec.md"))
        for path in matches:
            rel = path.relative_to(workspace)
            included.append(str(rel))
            parts.append(f"\n--- RELATED SPEC: {rel} ---\n{compact_middle(read_text(path), max_chars_per_spec)}\n")
    return ("\n".join(parts) if parts else "No related specs found for selected HLD-SPECS.\n"), included


def resource_text_for_paths(workspace: Path, resources: list[str], max_chars: int = 12000) -> tuple[str, list[str], list[str]]:
    parts: list[str] = []
    included: list[str] = []
    skipped: list[str] = []
    for resource in resources:
        if resource.upper() == "TBD" or "*" in resource:
            skipped.append(resource)
            continue
        path = (workspace / resource).resolve()
        try:
            rel = path.relative_to(workspace.resolve())
        except ValueError:
            skipped.append(resource)
            continue
        if not path.is_file():
            skipped.append(resource)
            continue
        included.append(str(rel))
        parts.append(f"\n--- RELATED RESOURCE: {rel} ---\n{compact_middle(read_text(path), max_chars)}\n")
    return ("\n".join(parts) if parts else "No related resource files included.\n"), included, skipped


def select_hld_context(
    *,
    parsed_map: hld_map.HldMap,
    workspace: Path,
    target_hld: str | None,
    max_chars: int,
    max_spec_chars: int,
) -> tuple[str, dict[str, object]]:
    sections_by_id = parsed_map.section_by_id()
    if target_hld:
        if target_hld not in sections_by_id:
            raise ValueError(f"Unknown target HLD section: {target_hld}")
        root_ids = [target_hld]
    else:
        root_ids = [section.id for section in parsed_map.sections]

    queue: list[tuple[str, str, int]] = []
    loaded: dict[str, str] = {}
    skipped_refs: list[dict[str, object]] = []

    def ref_kind_from_reason(reason: str) -> str:
        return reason.split(" ", 1)[0] if reason.startswith(("REF ", "DEPENDS ", "BLOCKED_BY ", "CONFLICTS_WITH ")) else ""

    for section_id in root_ids:
        queue.append((section_id, "target" if target_hld else "all-sections", 0))

    while queue:
        section_id, reason, depth = queue.pop(0)
        if section_id in loaded:
            continue
        section = sections_by_id.get(section_id)
        if not section:
            skipped_refs.append({"section": section_id, "reason": "missing-section", "requested_by": reason})
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
        for ref in section.references:
            if ref.kind == "REF":
                queue.append((ref.target, f"REF from {section.id}", depth + 1))

    selected_sections = [sections_by_id[section_id] for section_id in loaded if section_id in sections_by_id]
    section_parts = []
    included_sections: list[hld_map.HldSection] = []
    budget_used = 0
    for section in selected_sections:
        part = f"\n--- HLD SECTION {section.id}: {section.title} (lines {section.line_start}-{section.line_end}) ---\n{section.text}"
        part_len = len(part)
        if max_chars > 0 and budget_used + part_len > max_chars:
            skip: dict[str, object] = {
                "section": section.id,
                "reason": "prompt-budget-exceeded",
                "requested_by": loaded[section.id],
            }
            ref_kind = ref_kind_from_reason(loaded[section.id])
            if ref_kind:
                skip["ref_kind"] = ref_kind
            skipped_refs.append(skip)
            continue
        budget_used += part_len
        included_sections.append(section)
        section_parts.append(part)

    selected_specs = sorted({spec for section in included_sections for spec in hld_map.split_metadata_list(section.metadata_value("HLD-SPECS"))})
    selected_resources = sorted({resource for section in included_sections for resource in hld_map.split_metadata_list(section.metadata_value("HLD-RESOURCES"))})
    related_specs_text, related_specs_included = spec_paths_for_ids(workspace, selected_specs, max_spec_chars)
    resources_text, resources_included, resources_skipped = resource_text_for_paths(workspace, selected_resources)

    context = "\n".join(
        [
            "BOUNDED HLD MAP CONTEXT",
            "The full HLD is intentionally not included in this prompt.",
            "\n".join(section_parts),
            "\nRELATED SPECS",
            related_specs_text,
            "\nRELATED RESOURCES",
            resources_text,
        ]
    )
    report: dict[str, object] = {
        "target_section": target_hld,
        "loaded_sections": [
            {
                "id": section.id,
                "title": section.title,
                "line_start": section.line_start,
                "line_end": section.line_end,
                "why_loaded": loaded[section.id],
            }
            for section in included_sections
            if section.id in loaded
        ],
        "skipped_refs": skipped_refs,
        "prompt_size_estimate": len(context),
        "budget_used": budget_used,
        "budget_limit": max_chars,
        "related_specs_included": related_specs_included,
        "related_resources_included": resources_included,
        "related_resources_skipped": resources_skipped,
    }
    return context, report



def infer_hld_role(title: str) -> str:
    lower = title.lower()
    role_keywords = [
        ("governance", ("governance", "source of truth", "ownership", "decision", "policy", "constitution")),
        ("architecture", ("architecture", "design", "overview", "component", "system")),
        ("processing", ("flow", "process", "pipeline", "sync", "workflow", "orchestration")),
        ("api", ("api", "interface", "contract", "endpoint", "integration")),
        ("data", ("data", "state", "storage", "database", "persistence", "schema")),
        ("operations", ("failure", "recovery", "rollback", "observability", "operations", "deploy")),
        ("testing", ("test", "verification", "validation", "quality", "acceptance")),
        ("risk", ("risk", "conflict", "open question", "unknown", "blocker")),
        ("purpose", ("summary", "purpose", "goal", "scope", "introduction")),
    ]
    for role, keywords in role_keywords:
        if any(keyword in lower for keyword in keywords):
            return role
    return "architecture"


def infer_hld_risk(title: str, role: str) -> str:
    lower = title.lower()
    high_keywords = (
        "security",
        "permission",
        "auth",
        "data",
        "state",
        "persistence",
        "failure",
        "recovery",
        "rollback",
        "migration",
        "api",
        "contract",
        "governance",
        "source of truth",
        "conflict",
    )
    if role in {"governance", "api", "data", "operations", "risk"}:
        return "HIGH"
    if any(keyword in lower for keyword in high_keywords):
        return "HIGH"
    if role in {"architecture", "processing", "testing"}:
        return "MEDIUM"
    return "LOW"


def build_hld_format_report(hld_text: str, *, source_path: str) -> tuple[dict[str, object], str]:
    lines = hld_text.splitlines()
    fence_mask = hld_map.iter_code_fence_mask(lines)
    generic_heading_re = re.compile(r"^(?P<marks>#{1,6})\s+(?P<title>.+?)\s*$")

    headings: list[dict[str, object]] = []
    existing_hld_ids: set[str] = set()

    for idx, line in enumerate(lines, start=1):
        if fence_mask[idx - 1]:
            continue
        match = generic_heading_re.match(line)
        if not match:
            continue
        title = match.group("title").strip()
        level = len(match.group("marks"))
        hld_match = hld_map.SECTION_HEADING_RE.match(line)
        hld_id = hld_match.group("id") if hld_match else ""
        if hld_id:
            existing_hld_ids.add(hld_id)
        headings.append(
            {
                "line": idx,
                "level": level,
                "title": title,
                "is_hldspec_heading": bool(hld_id),
                "hld_id": hld_id or None,
            }
        )

    warnings: list[str] = []
    if not headings:
        warnings.append("No markdown headings were detected outside fenced code blocks.")
    if existing_hld_ids:
        warnings.append("The HLD already contains HLDspec-style headings; do not renumber existing HLD IDs.")

    if existing_hld_ids:
        candidate_headings = [heading for heading in headings if heading["is_hldspec_heading"]]
    else:
        candidate_headings = [
            heading
            for pos, heading in enumerate(headings)
            if int(heading["level"]) <= 2 and not (pos == 0 and int(heading["level"]) == 1 and len(headings) > 1)
        ]
        if not candidate_headings:
            candidate_headings = [heading for heading in headings if int(heading["level"]) <= 3]

    suggestions: list[dict[str, object]] = []
    large_section_warnings: list[str] = []
    for idx, heading in enumerate(candidate_headings, start=1):
        title = str(heading["title"])
        role = infer_hld_role(title)
        risk = infer_hld_risk(title, role)
        suggested_id = str(heading.get("hld_id") or f"HLD-{idx:03d}")
        line_start = int(heading["line"])
        next_line = int(candidate_headings[idx]["line"]) if idx < len(candidate_headings) else len(lines) + 1
        approx_lines = max(1, next_line - line_start)

        if approx_lines > 500:
            large_section_warnings.append(
                f"{suggested_id} candidate '{title}' spans about {approx_lines} lines; consider splitting before sync."
            )

        suggestions.append(
            {
                "suggested_id": suggested_id,
                "line": line_start,
                "heading_level": heading["level"],
                "title": title,
                "role": role,
                "risk": risk,
                "approx_lines_until_next_candidate": approx_lines,
                "metadata_skeleton": {
                    "HLD-ID": suggested_id,
                    "HLD-ROLE": role,
                    "HLD-STATUS": "active",
                    "HLD-RISK": risk,
                    "HLD-SPECS": "TBD",
                    "HLD-RESOURCES": "TBD",
                    "HLD-VERIFY": "section can be processed without loading the full HLD; related specs preserve HLD anchors",
                },
            }
        )

    warnings.extend(large_section_warnings)

    report: dict[str, object] = {
        "source_path": source_path,
        "line_count": len(lines),
        "heading_count": len(headings),
        "existing_hldspec_section_count": len(existing_hld_ids),
        "candidate_section_count": len(suggestions),
        "headings": headings,
        "suggested_hld_sections": suggestions,
        "warnings": warnings,
        "next_steps": [
            "Preserve the original as HLD.raw.md.",
            "Edit a working HLD.md copy only.",
            "Apply HLD-xxx IDs only to major sections.",
            "Use TBD for unknown specs, resources, and owners.",
            "Add REF HLD-xxx relationships where known.",
            "Run ./hld_spec_sync.py --hld HLD.md --hld-map-only before syncing.",
            "Run --use-hld-map --target-hld <id> --prompt-only before applying agent output.",
        ],
    }

    md_lines: list[str] = [
        "# HLD Format Report",
        "",
        f"Source: `{source_path}`",
        f"Lines: {len(lines)}",
        f"Markdown headings detected: {len(headings)}",
        f"Existing HLDspec headings: {len(existing_hld_ids)}",
        f"Candidate major sections: {len(suggestions)}",
        "",
        "## Verdict",
        "",
    ]
    if existing_hld_ids:
        md_lines.append("This HLD appears partially or fully formatted for HLDspec. Preserve existing HLD IDs.")
    elif suggestions:
        md_lines.append("This HLD is not yet HLDspec-formatted. Convert major sections first; do not run full sync yet.")
    else:
        md_lines.append("This HLD has no detectable markdown heading structure. Add major headings before HLDspec conversion.")

    if warnings:
        md_lines.extend(["", "## Warnings", ""])
        md_lines.extend(f"- {warning}" for warning in warnings)

    md_lines.extend(["", "## Detected headings", ""])
    for heading in headings[:200]:
        marker = "HLDspec" if heading["is_hldspec_heading"] else "plain"
        md_lines.append(
            f"- line {heading['line']}: level {heading['level']} [{marker}] {heading['title']}"
        )
    if len(headings) > 200:
        md_lines.append(f"- ... {len(headings) - 200} more headings omitted from markdown report; see JSON.")

    md_lines.extend(["", "## Suggested HLD section skeletons", ""])
    for item in suggestions[:80]:
        metadata = item["metadata_skeleton"]
        if not isinstance(metadata, dict):
            continue
        md_lines.extend(
            [
                f"### {item['suggested_id']} - {item['title']}",
                "",
                "```md",
                f"## {item['suggested_id']} - {item['title']}",
                "",
                f"HLD-ID: {metadata['HLD-ID']}",
                f"HLD-ROLE: {metadata['HLD-ROLE']}",
                f"HLD-STATUS: {metadata['HLD-STATUS']}",
                f"HLD-RISK: {metadata['HLD-RISK']}",
                f"HLD-SPECS: {metadata['HLD-SPECS']}",
                f"HLD-RESOURCES: {metadata['HLD-RESOURCES']}",
                f"HLD-VERIFY: {metadata['HLD-VERIFY']}",
                "```",
                "",
            ]
        )
    if len(suggestions) > 80:
        md_lines.append(f"... {len(suggestions) - 80} more suggestions omitted from markdown report; see JSON.")

    md_lines.extend(
        [
            "",
            "## Safe next steps",
            "",
            "1. Preserve the original as `HLD.raw.md`.",
            "2. Edit a working `HLD.md` copy only.",
            "3. Convert only major sections to `## HLD-xxx - Title`.",
            "4. Add required `HLD-*` metadata.",
            "5. Use `TBD` for unknown mappings.",
            "6. Add `REF HLD-xxx` links only where relationships are known.",
            "7. Run `./hld_spec_sync.py --hld HLD.md --hld-map-only`.",
            "8. Fix validation errors before syncing specs.",
            "",
            "## Do not",
            "",
            "- Do not overwrite the raw HLD.",
            "- Do not tag every subsection.",
            "- Do not invent spec IDs, owners, or resources.",
            "- Do not run full-HLD sync before the map validates.",
            "- Do not auto-convert or auto-chunk without reviewing a report or plan.",
            "",
        ]
    )

    return report, "\n".join(md_lines)

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


def strip_echoed_prompt(text: str, prompt: str | None) -> str:
    if not prompt:
        return text
    prompt_idx = text.find(prompt)
    if prompt_idx >= 0:
        return (text[:prompt_idx] + text[prompt_idx + len(prompt):]).lstrip("\r\n")
    return text


def apply_write_blocks(
    log_path: Path,
    workspace: Path,
    *,
    allow_constitution: bool,
    allow_specs: bool,
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


def validate_map_consolidation(workspace: Path, parsed_map: hld_map.HldMap | None) -> list[str]:
    if parsed_map is None:
        return []
    errors: list[str] = []

    duplicate_path = workspace / SYNC_REL / "duplicate_report.json"
    if duplicate_path.exists():
        try:
            duplicate_report = json.loads(read_text(duplicate_path))
            if isinstance(duplicate_report, list):
                for idx, item in enumerate(duplicate_report, start=1):
                    if isinstance(item, dict) and str(item.get("status", "")).upper() == "DUPLICATE_RISK":
                        errors.append(f"duplicate spec risk remains in duplicate_report.json item {idx}")
        except Exception as exc:
            errors.append(f"invalid duplicate_report.json during consolidation: {exc}")

    missing_path = workspace / SYNC_REL / "missing_report.json"
    if missing_path.exists():
        try:
            missing_report = json.loads(read_text(missing_path))
            if isinstance(missing_report, list):
                for idx, item in enumerate(missing_report, start=1):
                    if isinstance(item, dict) and item.get("recommended_action") not in {"mark_out_of_scope", "needs_review"}:
                        errors.append(f"unresolved missing HLD coverage remains in missing_report.json item {idx}")
        except Exception as exc:
            errors.append(f"invalid missing_report.json during consolidation: {exc}")

    drift_path = workspace / SYNC_REL / "drift_report.json"
    if drift_path.exists():
        try:
            drift_report = json.loads(read_text(drift_path))
            if isinstance(drift_report, list):
                for idx, item in enumerate(drift_report, start=1):
                    if isinstance(item, dict) and item.get("drift_type") in {"anchor_missing", "stale_spec"}:
                        errors.append(f"stale or missing HLD ref remains in drift_report.json item {idx}")
        except Exception as exc:
            errors.append(f"invalid drift_report.json during consolidation: {exc}")

    for section in parsed_map.sections:
        if section.metadata_value("HLD-STATUS").lower() == "active" and not section.metadata_value("HLD-SPECS"):
            errors.append(f"{section.id}: active HLD section has no HLD-SPECS coverage marker")
        for ref in section.references:
            if ref.kind in {"BLOCKED_BY", "CONFLICTS_WITH"}:
                errors.append(f"{section.id}: unresolved blocking/conflict ref remains: {ref.kind} REF {ref.target}")

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
    echoed_prompt: str | None = None,
) -> None:
    text = strip_echoed_prompt(read_text(log_path), echoed_prompt)
    pattern = re.compile(r"^WRITE FILE:\s*(?P<path>[^\n]+)\nCONTENT:\n", re.MULTILINE)
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
    ap.add_argument("--hld-map-only", action="store_true", help="Parse/validate HLD map artifacts and exit without agent.")
    ap.add_argument("--hld-format-report", action="store_true", help="Write a read-only report to help convert a raw/huge HLD into HLDspec format and exit without agent.")
    ap.add_argument("--use-hld-map", action="store_true", help="Use HLD section map for bounded context selection.")
    ap.add_argument("--target-hld", default=None, help="Target one HLD section such as HLD-003 for map-aware runs.")
    ap.add_argument("--resume", action="store_true", help="Resume a map-aware target run when section hashes still match.")
    ap.add_argument("--restart-map-run", action="store_true", help="Clear map-aware run state before running.")

    ap.add_argument("--max-hld-chars", type=int, default=0, help="0 means no HLD truncation")
    ap.add_argument("--max-hld-map-context-chars", type=int, default=60000, help="0 means no map-context budget")
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
    if args.hld_format_report:
        report_json, report_md = build_hld_format_report(hld_text, source_path=str(hld_path))
        report_path = logs_dir / "hld_format_report.md"
        json_path = logs_dir / "suggested_hld_sections.json"
        write_text(report_path, report_md)
        write_text(json_path, json.dumps(report_json, indent=2, sort_keys=True))
        print("HLD format report generated:")
        print(f"- report: {report_path}")
        print(f"- suggestions: {json_path}")
        return 0

    parsed_hld_map: hld_map.HldMap | None = None
    context_selection: dict[str, object] | None = None
    if args.hld_map_only or args.use_hld_map:
        parsed_hld_map = hld_map.parse_hld_text(hld_text, source_path=str(hld_path))
        map_outputs = hld_map.write_hld_map_outputs(parsed_hld_map, workspace)
        if parsed_hld_map.validation_errors:
            eprint("Invalid HLD map:")
            for error in parsed_hld_map.validation_errors:
                eprint(f"- {error}")
            write_text(
                logs_dir / "run_summary.json",
                json.dumps(
                    {
                        "mode": "hld-map-only" if args.hld_map_only else "map-aware",
                        "hld": str(hld_path),
                        "map_outputs": map_outputs,
                        "validation_errors": parsed_hld_map.validation_errors,
                    },
                    indent=2,
                ),
            )
            return 1
        if args.hld_map_only:
            print("HLD map generated:")
            for key, value in map_outputs.items():
                if key != "sections":
                    print(f"- {key}: {value}")
            print(f"- sections: {len(map_outputs['sections'])}")
            return 0
        if args.restart_map_run:
            write_run_state(workspace, {"sections": {}})
        if args.resume and args.target_hld:
            reason = resume_skip_reason(workspace, parsed_hld_map, args.target_hld)
            if reason:
                print(f"Resume: skipped {args.target_hld}: {reason}")
                return 0

    if args.use_hld_map:
        assert parsed_hld_map is not None
        try:
            numbered_hld, context_selection = select_hld_context(
                parsed_map=parsed_hld_map,
                workspace=workspace,
                target_hld=args.target_hld,
                max_chars=args.max_hld_map_context_chars,
                max_spec_chars=args.max_existing_spec_chars,
            )
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        write_text(logs_dir / "context_selection.json", json.dumps(context_selection, indent=2))
    else:
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
        if args.use_hld_map and parsed_hld_map is not None:
            update_run_state(
                workspace,
                parsed_hld_map,
                args.target_hld,
                status="failed",
                prompt_path=prompt_path,
                log_path=log_path,
                staged_output_path=None,
            )
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
            "use_hld_map": args.use_hld_map,
            "target_hld": args.target_hld,
            "context_selection": context_selection,
        }
        write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))
        eprint(f"Agent failed with rc={rc}. WRITE FILE blocks were not applied. See: {log_path}")
        return rc

    writes = 0
    staging_info: dict[str, object] | None = None
    if not args.no_apply_write_blocks:
        try:
            validate_write_targets(
                log_path,
                workspace,
                allow_constitution=allow_sync_mutations,
                allow_specs=allow_sync_mutations,
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
                    apply_staged_writes_to_workspace(
                        staging_workspace=workspace,
                        target_workspace=tmp_workspace,
                        staging_info=staging_info,
                        allow_constitution=allow_sync_mutations,
                        allow_specs=allow_sync_mutations,
                    )
                    staged_validation_errors = validate_outputs(
                        tmp_workspace,
                        require_constitution=allow_sync_mutations,
                        require_specs=allow_sync_mutations,
                    )
                    staged_validation_errors.extend(validate_map_consolidation(tmp_workspace, parsed_hld_map))
                    if staged_validation_errors:
                        raise RuntimeError(
                            "staged validation failed before apply: "
                            + "; ".join(staged_validation_errors)
                        )
                    writes = apply_staged_writes_to_workspace(
                        staging_workspace=workspace,
                        target_workspace=workspace,
                        staging_info=staging_info,
                        allow_constitution=allow_sync_mutations,
                        allow_specs=allow_sync_mutations,
                    )
                finally:
                    tmp_holder.cleanup()
            else:
                writes = apply_write_blocks(
                    log_path,
                    workspace,
                    allow_constitution=allow_sync_mutations,
                    allow_specs=allow_sync_mutations,
                    echoed_prompt=prompt,
                )
        except Exception as exc:
            if args.use_hld_map and parsed_hld_map is not None:
                update_run_state(
                    workspace,
                    parsed_hld_map,
                    args.target_hld,
                    status="failed",
                    prompt_path=prompt_path,
                    log_path=log_path,
                    staged_output_path=(str(staging_info["staged_dir"]) if staging_info else None),
                )
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
                "use_hld_map": args.use_hld_map,
                "target_hld": args.target_hld,
                "context_selection": context_selection,
                "staging": staging_info,
            }
            write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))
            return 1

    validation_errors = validate_outputs(
        workspace,
        require_constitution=allow_sync_mutations,
        require_specs=allow_sync_mutations,
    )
    if args.use_hld_map:
        validation_errors.extend(validate_map_consolidation(workspace, parsed_hld_map))
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
        "use_hld_map": args.use_hld_map,
        "target_hld": args.target_hld,
        "context_selection": context_selection,
        "staging": staging_info,
        "skeptic_conflicts_path": str((workspace / SYNC_SKEPTIC_CONFLICTS_REL).relative_to(workspace)) if args.skeptic else None,
        "skeptic_unresolved_conflicts": len(skeptic_conflicts),
    }
    write_text(logs_dir / "run_summary.json", json.dumps(run_summary, indent=2))

    if validation_errors:
        if args.use_hld_map and parsed_hld_map is not None:
            update_run_state(
                workspace,
                parsed_hld_map,
                args.target_hld,
                status="failed",
                prompt_path=prompt_path,
                log_path=log_path,
                staged_output_path=(str(staging_info["staged_dir"]) if staging_info else None),
            )
        eprint("Completed with validation errors:")
        for err in validation_errors:
            eprint(f"- {err}")
        eprint(f"See: {logs_dir / 'run_summary.json'}")
        return 1

    if skeptic_conflicts:
        if args.use_hld_map and parsed_hld_map is not None:
            update_run_state(
                workspace,
                parsed_hld_map,
                args.target_hld,
                status="failed",
                prompt_path=prompt_path,
                log_path=log_path,
                staged_output_path=(str(staging_info["staged_dir"]) if staging_info else None),
            )
        print_skeptic_conflicts(skeptic_conflicts, SYNC_SKEPTIC_CONFLICTS_REL)
        eprint(f"Run summary: {logs_dir / 'run_summary.json'}")
        return CONFLICT_RETURN_CODE

    print("PASS")
    if args.use_hld_map and parsed_hld_map is not None:
        update_run_state(
            workspace,
            parsed_hld_map,
            args.target_hld,
            status="done",
            prompt_path=prompt_path,
            log_path=log_path,
            staged_output_path=(str(staging_info["staged_dir"]) if staging_info else None),
        )
    print("Updated files under:")
    print("- .specify/memory/constitution.md")
    print("- specs/ (native Spec Kit feature specs)")
    print("- .specify/sync/")
    print(f"Run summary: {logs_dir / 'run_summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
