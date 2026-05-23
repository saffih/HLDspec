#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional


REQUIRED_FIELDS = [
    "HLD-ID:",
    "HLD-ROLE:",
    "HLD-STATUS:",
    "HLD-RISK:",
    "HLD-SPECS:",
    "HLD-RESOURCES:",
    "HLD-VERIFY:",
]


@dataclass
class ConvertedSection:
    hld_id: str
    title: str
    role: str
    risk: str
    source_start_line: int
    source_end_line: int
    original_parent: Optional[str] = None


def clean_title(title: str) -> str:
    return re.sub(r"\s+", " ", title.strip())


def clean_split_title(title: str) -> str:
    return re.sub(r"^\d+\.\s*", "", clean_title(title))


def infer_role(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ["single source", "decision log", "assumptions", "open conflicts", "changelog", "success criteria"]):
        return "governance_context"
    if any(k in t for k in ["stakeholder", "personas", "business case", "user stories", "executive summary"]):
        return "product_context"
    if any(k in t for k in ["architecture", "component", "brain", "ai integration", "tea"]):
        return "architecture"
    if any(k in t for k in ["api", "interface", "http", "cli", "endpoint", "contract"]):
        return "interface_contract"
    if any(k in t for k in ["database", "schema", "entity model", "model", "storage"]):
        return "data_model"
    if "security" in t:
        return "security"
    if "performance" in t:
        return "performance"
    if any(k in t for k in ["error", "failure", "recovery"]):
        return "reliability"
    if any(k in t for k in ["milestone", "implementation", "handoff", "scope"]):
        return "planning"
    if any(k in t for k in ["environment", "config"]):
        return "configuration"
    if any(k in t for k in ["runbook", "operational"]):
        return "operations"
    return "architecture"


def infer_risk(title: str, role: str) -> str:
    t = title.lower()
    if any(k in t for k in ["critical", "security", "database", "schema", "session", "socket", "failure", "error", "api", "ai integration", "brain"]):
        return "high"
    if role in {"architecture", "interface_contract", "data_model", "reliability", "configuration"}:
        return "medium"
    return "low"


def verify_text(role: str) -> str:
    if role == "interface_contract":
        return "Verify contract inputs, outputs, errors, consumers, and backward-compatibility constraints."
    if role == "data_model":
        return "Verify source of truth, ownership, persistence, mutation rules, and dependent consumers."
    if role == "architecture":
        return "Verify boundaries, responsibilities, dependencies, and downstream SpecKit implications."
    if role == "security":
        return "Verify security assumptions, threat model, access controls, and failure behavior."
    if role == "reliability":
        return "Verify failure modes, recovery paths, observability, and regression coverage."
    if role == "product_context":
        return "Verify user value, scope, constraints, and mapping into feature candidates."
    if role == "governance_context":
        return "Verify governance/source-of-truth implications and whether this section should remain context-only."
    return "Verify this section against the HLD source-of-truth and downstream planning impact."


def top_level_sections(lines: list[str]) -> list[tuple[int, int, str]]:
    heads = [(idx, clean_title(line[3:])) for idx, line in enumerate(lines) if line.startswith("## ")]
    sections = []
    for pos, (start, title) in enumerate(heads):
        end = heads[pos + 1][0] if pos + 1 < len(heads) else len(lines)
        sections.append((start, end, title))
    return sections


def split_parent_sections(lines: list[str], start: int, end: int) -> list[tuple[int, int, str]]:
    subheads = [
        (idx, clean_title(line[4:]))
        for idx, line in enumerate(lines[start + 1 : end], start=start + 1)
        if line.startswith("### ")
    ]
    chunks = []
    for pos, (chunk_start, subtitle) in enumerate(subheads):
        chunk_end = subheads[pos + 1][0] if pos + 1 < len(subheads) else end
        chunks.append((chunk_start, chunk_end, clean_split_title(subtitle)))
    return chunks


def make_metadata(hld_id: str, title: str, source_start: int, source_end: int) -> tuple[str, str, list[str]]:
    role = infer_role(title)
    risk = infer_risk(title, role)
    metadata = [
        f"HLD-ID: {hld_id}",
        f"HLD-ROLE: {role}",
        "HLD-STATUS: accepted",
        f"HLD-RISK: {risk}",
        "HLD-SPECS: TBD",
        "HLD-RESOURCES: TBD",
        f"HLD-SOURCE-LINES: {source_start}-{source_end}",
        f"HLD-VERIFY: {verify_text(role)}",
        "",
    ]
    return role, risk, metadata


def convert_raw_hld(raw_text: str, split_sections: set[str]) -> tuple[str, list[ConvertedSection]]:
    lines = raw_text.splitlines()
    sections = top_level_sections(lines)
    if not sections:
        raise ValueError("No top-level '## ' sections found; cannot convert to HLDspec format.")

    out = []
    first_top = sections[0][0]
    out.extend(lines[:first_top])

    if "made by AI" not in "\n".join(out[:20]):
        insert_at = 1 if out else 0
        out[insert_at:insert_at] = ["", "<!-- made by AI -->", ""]

    converted = []
    counter = 1

    for start, end, title in sections:
        chunks = split_parent_sections(lines, start, end) if title in split_sections else []

        if chunks:
            out.append("")
            # Do not include a raw "## <parent>" string here; tests verify original top-level headings are removed.
            out.append(f"<!-- Original parent section split for HLDspec conversion: {title} -->")
            for chunk_start, chunk_end, subtitle in chunks:
                hld_id = f"HLD-{counter:03d}"
                role, risk, metadata = make_metadata(hld_id, subtitle, chunk_start + 1, chunk_end)
                out.append("")
                out.append(f"## {hld_id} - {subtitle}")
                out.extend(metadata)
                out.append(f"> Original parent section: {title}")
                out.append("")
                out.extend(lines[chunk_start + 1 : chunk_end])
                converted.append(ConvertedSection(hld_id, subtitle, role, risk, chunk_start + 1, chunk_end, title))
                counter += 1
            continue

        hld_id = f"HLD-{counter:03d}"
        role, risk, metadata = make_metadata(hld_id, title, start + 1, end)
        out.append("")
        out.append(f"## {hld_id} - {title}")
        out.extend(metadata)
        out.extend(lines[start + 1 : end])
        converted.append(ConvertedSection(hld_id, title, role, risk, start + 1, end))
        counter += 1

    return "\n".join(out).rstrip() + "\n", converted


def validate_hldspec(text: str) -> dict[str, object]:
    lines = text.splitlines()
    headers = []
    bad_headers = []

    for idx, line in enumerate(lines, start=1):
        if not line.startswith("## "):
            continue
        match = re.match(r"^## (HLD-\d{3}) - .+", line)
        if match:
            headers.append((idx, match.group(1), line))
        else:
            bad_headers.append((idx, line))

    missing = []
    seen = {}
    duplicates = []

    for pos, (start, hld_id, _header) in enumerate(headers):
        end = headers[pos + 1][0] - 1 if pos + 1 < len(headers) else len(lines)
        block = "\n".join(lines[start:end])
        for field in REQUIRED_FIELDS:
            if field not in block:
                missing.append((hld_id, field))
        if hld_id in seen:
            duplicates.append((hld_id, seen[hld_id], start))
        else:
            seen[hld_id] = start

    return {
        "section_count": len(headers),
        "invalid_heading_count": len(bad_headers),
        "missing_metadata_count": len(missing),
        "duplicate_id_count": len(duplicates),
        "invalid_headings": bad_headers,
        "missing_metadata": missing,
        "duplicate_ids": duplicates,
        "valid": not bad_headers and not missing and not duplicates and bool(headers),
    }


def render_index(sections: list[ConvertedSection]) -> str:
    lines = [
        "# HLDspec Conversion Index",
        "",
        "made by AI",
        "",
        f"Converted sections: {len(sections)}",
        "",
        "| HLD-ID | Title | Role | Risk | Source lines | Original parent |",
        "|---|---|---|---|---|---|",
    ]
    for item in sections:
        title = item.title.replace("|", "/")
        parent = (item.original_parent or "").replace("|", "/")
        lines.append(
            f"| {item.hld_id} | {title} | {item.role} | {item.risk} | "
            f"{item.source_start_line}-{item.source_end_line} | {parent} |"
        )
    return "\n".join(lines) + "\n"


def default_output_for(input_path: Path) -> Path:
    return input_path.with_name(input_path.stem + ".hldspec.md")


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert a raw Markdown HLD into HLDspec section format.")
    parser.add_argument("input_hld", help="Raw HLD markdown file.")
    parser.add_argument("-o", "--output", help="Output HLDspec markdown path. Defaults to <input>.hldspec.md.")
    parser.add_argument("--index-output", help="Optional conversion index markdown path.")
    parser.add_argument("--split-section", action="append", default=[], help="Exact top-level section title to split by ### subsections. Repeatable.")
    parser.add_argument("--default-flow-splits", action="store_true", help="Split Flow's Component Deep-Dive and Component Interface Definitions by ### subsections.")
    parser.add_argument("--json-report", help="Optional JSON validation/conversion report path.")
    parser.add_argument("--overwrite", action="store_true", help="Allow output path to overwrite an existing file.")
    args = parser.parse_args()

    input_path = Path(args.input_hld)
    if not input_path.exists():
        raise SystemExit(f"ERROR: input HLD not found: {input_path}")

    output_path = Path(args.output) if args.output else default_output_for(input_path)
    if output_path.exists() and not args.overwrite:
        raise SystemExit(f"ERROR: output already exists. Pass --overwrite to replace: {output_path}")

    split_sections = set(args.split_section or [])
    if args.default_flow_splits:
        split_sections.update({"Component Deep-Dive", "Component Interface Definitions"})

    converted_text, sections = convert_raw_hld(input_path.read_text(encoding="utf-8", errors="replace"), split_sections)
    validation = validate_hldspec(converted_text)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(converted_text, encoding="utf-8")

    index_path = Path(args.index_output) if args.index_output else output_path.with_name(output_path.stem + ".conversion_index.md")
    index_path.write_text(render_index(sections), encoding="utf-8")

    report = {
        "input": str(input_path),
        "output": str(output_path),
        "index_output": str(index_path),
        "split_sections": sorted(split_sections),
        "converted_sections": [asdict(item) for item in sections],
        "validation": validation,
    }

    if args.json_report:
        Path(args.json_report).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print("HLD conversion complete:")
    print(f"- input: {input_path}")
    print(f"- output: {output_path}")
    print(f"- index: {index_path}")
    print(f"- sections: {validation['section_count']}")
    print(f"- invalid headings: {validation['invalid_heading_count']}")
    print(f"- missing metadata: {validation['missing_metadata_count']}")
    print(f"- duplicate IDs: {validation['duplicate_id_count']}")

    if not validation["valid"]:
        print("- status: INVALID")
        return 2

    print("- status: VALID")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
