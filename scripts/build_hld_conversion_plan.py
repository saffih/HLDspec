#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


LARGE_SECTION_LINES = 400
CHUNK_SIZE = 5


def candidate_line_count(item: dict[str, Any]) -> int:
    for key in ("line_count", "approx_lines_until_next_candidate", "approx_lines", "lines"):
        try:
            count = int(item.get(key) or 0)
        except (TypeError, ValueError):
            count = 0
        if count > 0:
            return count
    return 0


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def internal_headings_for(item: dict[str, Any], headings: list[dict[str, Any]], line_end: int) -> list[dict[str, Any]]:
    start = as_int(item.get("line"), 0)
    level = as_int(item.get("heading_level"), 2)
    result: list[dict[str, Any]] = []
    for heading in headings:
        line = as_int(heading.get("line"), 0)
        heading_level = as_int(heading.get("level"), 9)
        if start < line <= line_end and heading_level > level:
            result.append({"line": line, "level": heading_level, "title": str(heading.get("title", "")).strip()})
    return result


def split_boundary_headings(item: dict[str, Any], headings: list[dict[str, Any]], line_end: int) -> list[dict[str, Any]]:
    internal = internal_headings_for(item, headings, line_end)
    if not internal:
        return []
    child_level = min(as_int(heading.get("level"), 9) for heading in internal)
    return [heading for heading in internal if as_int(heading.get("level"), 9) == child_level]


def split_suffix(index: int) -> str:
    if index < 26:
        return chr(ord("A") + index)
    return str(index + 1)


def proposed_split_plan(boundaries: list[dict[str, Any]], parent_line_end: int, parent_id: str) -> list[dict[str, Any]]:
    plan: list[dict[str, Any]] = []
    for idx, heading in enumerate(boundaries):
        start = as_int(heading.get("line"), 0)
        if idx + 1 < len(boundaries):
            end = as_int(boundaries[idx + 1].get("line"), parent_line_end + 1) - 1
        else:
            end = parent_line_end
        plan.append(
            {
                "proposed_hld_id": f"{parent_id}{split_suffix(idx)}",
                "title": str(heading.get("title", "")).strip(),
                "source_line_start": start,
                "source_line_end": end,
                "source_line_count": max(1, end - start + 1),
                "boundary_source": "first_internal_heading_level",
                "heading_level": as_int(heading.get("level"), 0),
            }
        )
    return plan


def recommended_action(line_count: int, boundary_count: int) -> tuple[str, bool, str]:
    if line_count >= LARGE_SECTION_LINES:
        if boundary_count >= 2:
            return (
                "STOP_SPLIT_DECISION_REQUIRED",
                True,
                (
                    f"Candidate is {line_count} lines, above the {LARGE_SECTION_LINES}-line large-section threshold, "
                    f"and has {boundary_count} peer internal headings that can be reviewed as split boundaries."
                ),
            )
        return (
            "PROCEED_SINGLE_SECTION_REVIEW",
            True,
            (
                f"Candidate is {line_count} lines, above the {LARGE_SECTION_LINES}-line large-section threshold, "
                "but no clear peer internal split boundaries were detected. Review as one large section."
            ),
        )
    return ("PROCEED_METADATA_ONLY", False, "Candidate is within metadata-only conversion bounds.")


def group_chunks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    def flush_current() -> None:
        nonlocal current
        if not current:
            return
        chunks.append(
            {
                "chunk_id": f"chunk-{len(chunks) + 1:03d}",
                "status": "PROCEED_METADATA_ONLY",
                "candidate_ids": [str(item["proposed_hld_id"]) for item in current],
                "source_line_start": current[0]["source_line_start"],
                "source_line_end": current[-1]["source_line_end"],
                "human_decision_required": False,
                "reason": "Metadata-only batch of small/normal major sections.",
            }
        )
        current = []

    for item in entries:
        if item["recommended_action"] in {"STOP_SPLIT_DECISION_REQUIRED", "PROCEED_SINGLE_SECTION_REVIEW"}:
            flush_current()
            chunks.append(
                {
                    "chunk_id": f"chunk-{len(chunks) + 1:03d}",
                    "status": item["recommended_action"],
                    "candidate_ids": [str(item["proposed_hld_id"])],
                    "source_line_start": item["source_line_start"],
                    "source_line_end": item["source_line_end"],
                    "human_decision_required": True,
                    "reason": item["reason"],
                }
            )
            continue

        current.append(item)
        if len(current) >= CHUNK_SIZE:
            flush_current()

    flush_current()
    return chunks


def build_plan(report: dict[str, Any], *, source_hld: str, report_json: str) -> dict[str, Any]:
    suggestions = report.get("suggested_hld_sections", [])
    if not isinstance(suggestions, list):
        suggestions = []
    headings = report.get("headings", [])
    if not isinstance(headings, list):
        headings = []

    entries: list[dict[str, Any]] = []
    for raw in suggestions:
        if not isinstance(raw, dict):
            continue

        line_start = as_int(raw.get("line"), 0)
        line_count = candidate_line_count(raw)
        line_end = line_start + max(line_count, 1) - 1
        metadata = raw.get("metadata_skeleton")
        if not isinstance(metadata, dict):
            metadata = {}

        proposed_id = str(raw.get("suggested_id", "")).strip()
        role = str(raw.get("role") or metadata.get("HLD-ROLE") or "architecture")
        risk = str(raw.get("risk") or metadata.get("HLD-RISK") or "MEDIUM")
        internal = internal_headings_for(raw, headings, line_end)
        boundaries = split_boundary_headings(raw, headings, line_end)
        split_plan = proposed_split_plan(boundaries, line_end, proposed_id)
        action, human_required, reason = recommended_action(line_count, len(boundaries))

        entries.append(
            {
                "source_line_start": line_start,
                "source_line_end": line_end,
                "source_line_count": line_count,
                "title": str(raw.get("title", "")).strip(),
                "proposed_hld_id": proposed_id,
                "proposed_role": role,
                "proposed_risk": risk,
                "large_section": line_count >= LARGE_SECTION_LINES,
                "recommended_action": action,
                "human_decision_required": human_required,
                "reason": reason,
                "split_candidate_headings": internal,
                "split_boundary_headings": boundaries,
                "proposed_split_plan": split_plan,
                "metadata_skeleton": {
                    "HLD-ID": proposed_id,
                    "HLD-ROLE": role,
                    "HLD-STATUS": str(metadata.get("HLD-STATUS") or "active"),
                    "HLD-RISK": risk,
                    "HLD-SPECS": str(metadata.get("HLD-SPECS") or "TBD"),
                    "HLD-RESOURCES": str(metadata.get("HLD-RESOURCES") or "TBD"),
                    "HLD-VERIFY": str(
                        metadata.get("HLD-VERIFY")
                        or "section can be processed without loading the full HLD; related specs preserve HLD anchors"
                    ),
                },
            }
        )

    chunks = group_chunks(entries)
    if any(item["recommended_action"] == "STOP_SPLIT_DECISION_REQUIRED" for item in entries):
        status = "STOP_SPLIT_DECISION_REQUIRED"
    elif any(item["recommended_action"] == "PROCEED_SINGLE_SECTION_REVIEW" for item in entries):
        status = "PROCEED_SINGLE_SECTION_REVIEW"
    elif len(chunks) > 1:
        status = "PROCEED_CHUNKED_CONVERSION"
    else:
        status = "PROCEED_METADATA_ONLY"

    return {
        "status": status,
        "source_hld": source_hld,
        "format_report_json": report_json,
        "large_section_threshold_lines": LARGE_SECTION_LINES,
        "candidate_count": len(entries),
        "large_candidate_section_count": sum(1 for item in entries if item["large_section"]),
        "human_decision_required": status in {"STOP_SPLIT_DECISION_REQUIRED", "PROCEED_SINGLE_SECTION_REVIEW"},
        "candidates": entries,
        "chunks": chunks,
    }


def render_md(plan: dict[str, Any]) -> str:
    lines: list[str] = [
        "# HLD Conversion Plan",
        "",
        "made by AI",
        "",
        f"Status: `{plan['status']}`",
        f"Candidate sections: {plan['candidate_count']}",
        f"Large candidate sections: {plan['large_candidate_section_count']}",
        f"Human decision required: `{str(plan['human_decision_required']).lower()}`",
        "",
        "## Meaning",
        "",
    ]

    if plan["status"] == "STOP_SPLIT_DECISION_REQUIRED":
        lines += [
            "At least one candidate section is too large for safe metadata-only conversion and has peer internal headings that require split-boundary review.",
            "Do not auto-convert those sections until split boundaries are accepted.",
            "",
        ]
    elif plan["status"] == "PROCEED_SINGLE_SECTION_REVIEW":
        lines += [
            "At least one large candidate section has no clear peer split boundaries. Review whether to keep it as one large section.",
            "",
        ]
    elif plan["status"] == "PROCEED_CHUNKED_CONVERSION":
        lines += ["No split blocker was detected, but conversion should proceed in bounded chunks.", ""]
    else:
        lines += ["The HLD appears safe for metadata-only conversion in one small batch.", ""]

    lines += ["## Chunks", ""]
    for chunk in plan["chunks"]:
        lines += [
            f"### {chunk['chunk_id']} - {chunk['status']}",
            "",
            f"- candidates: {', '.join(chunk['candidate_ids'])}",
            f"- source lines: {chunk['source_line_start']}-{chunk['source_line_end']}",
            f"- human decision required: `{str(chunk['human_decision_required']).lower()}`",
            f"- reason: {chunk['reason']}",
            "",
        ]

    lines += ["## Candidate sections", ""]
    for item in plan["candidates"]:
        lines += [
            f"### {item['proposed_hld_id']} - {item['title']}",
            "",
            f"- source lines: {item['source_line_start']}-{item['source_line_end']}",
            f"- approx lines: {item['source_line_count']}",
            f"- role: `{item['proposed_role']}`",
            f"- risk: `{item['proposed_risk']}`",
            f"- large section: `{str(item['large_section']).lower()}`",
            f"- recommended action: `{item['recommended_action']}`",
            f"- human decision required: `{str(item['human_decision_required']).lower()}`",
            f"- reason: {item['reason']}",
        ]

        split_plan = item.get("proposed_split_plan") or []
        if split_plan:
            lines += ["", "Proposed split plan:"]
            for split in split_plan:
                lines.append(
                    f"- {split['proposed_hld_id']} - {split['title']} "
                    f"(lines {split['source_line_start']}-{split['source_line_end']}, "
                    f"{split['source_line_count']} lines)"
                )

        boundary_headings = item.get("split_boundary_headings") or []
        if boundary_headings and not split_plan:
            lines += ["", "Peer internal headings for review:"]
            for heading in boundary_headings:
                lines.append(f"- line {heading['line']}: level {heading['level']} {heading['title']}")

        all_headings = item.get("split_candidate_headings") or []
        if all_headings:
            shown = {heading.get("line") for heading in boundary_headings}
            nested = [heading for heading in all_headings if heading.get("line") not in shown]
            if nested:
                lines += ["", "Nested internal headings, shown for context:"]
                for heading in nested[:40]:
                    lines.append(f"- line {heading['line']}: level {heading['level']} {heading['title']}")
                if len(nested) > 40:
                    lines.append(f"- ... {len(nested) - 40} more nested headings omitted from markdown only; see JSON.")
        lines.append("")

    lines += [
        "## Rules",
        "",
        "- Preserve all original HLD content.",
        "- Metadata-only conversion may add HLD headings and metadata but must not delete, summarize, or reinterpret content.",
        "- Use `HLD-SPECS: TBD` unless mapping is certain.",
        "- Use `HLD-RESOURCES: TBD` unless resources/interfaces/contracts are explicit.",
        "- Do not split sections marked `STOP_SPLIT_DECISION_REQUIRED` without human approval.",
        "- After conversion, rerun `scripts/first_run_readonly.sh` on the converted HLD.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a read-only HLD conversion plan from hld_format_report JSON.")
    parser.add_argument("report_json")
    parser.add_argument("workspace")
    parser.add_argument("--source-hld", default="")
    args = parser.parse_args()

    report_path = Path(args.report_json)
    workspace = Path(args.workspace)
    report = json.loads(report_path.read_text(encoding="utf-8"))

    out_dir = workspace / ".specify" / "sync"
    out_dir.mkdir(parents=True, exist_ok=True)

    plan = build_plan(report, source_hld=args.source_hld, report_json=str(report_path))
    (out_dir / "hld_conversion_plan.json").write_text(json.dumps(plan, indent=2, sort_keys=True), encoding="utf-8")
    (out_dir / "hld_conversion_plan.md").write_text(render_md(plan), encoding="utf-8")

    print("HLD conversion plan generated:")
    print(f"- json: {out_dir / 'hld_conversion_plan.json'}")
    print(f"- report: {out_dir / 'hld_conversion_plan.md'}")
    print(f"- status: {plan['status']}")
    print(f"- large sections: {plan['large_candidate_section_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
