from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


SECTION_HEADING_RE = re.compile(r"^## (?P<id>HLD-\d{3}) - (?P<title>.+?)\s*$")
METADATA_RE = re.compile(r"^(?P<key>HLD-[A-Z0-9-]+):\s*(?P<value>.*)$")
REF_RE = re.compile(r"\b(?:(?P<kind>DEPENDS|BLOCKED_BY|CONFLICTS_WITH)\s+)?REF\s+(?P<target>HLD-\d{3})\b")
REQUIRED_METADATA = ("HLD-ID", "HLD-ROLE", "HLD-STATUS", "HLD-RISK", "HLD-SPECS", "HLD-RESOURCES")
OPTIONAL_METADATA = ("HLD-OWNER", "HLD-NOTES", "HLD-INPUTS", "HLD-OUTPUTS", "HLD-DESC")
KNOWN_METADATA = set(REQUIRED_METADATA) | set(OPTIONAL_METADATA) | {"HLD-VERIFY"}


@dataclass
class HldReference:
    target: str
    kind: str
    line: int
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target,
            "kind": self.kind,
            "line": self.line,
            "text": self.text,
        }


@dataclass
class HldSection:
    id: str
    title: str
    line_start: int
    line_end: int
    text: str
    metadata: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    references: list[HldReference] = field(default_factory=list)

    def metadata_values(self, key: str) -> list[str]:
        return [str(item["value"]) for item in self.metadata.get(key, [])]

    def metadata_value(self, key: str, default: str = "") -> str:
        values = self.metadata_values(key)
        return values[0] if values else default

    def refs_by_kind(self, kind: str) -> list[str]:
        return sorted({ref.target for ref in self.references if ref.kind == kind})

    def normal_refs(self) -> list[str]:
        return self.refs_by_kind("REF")

    def required_refs(self) -> list[str]:
        return sorted(
            {
                ref.target
                for ref in self.references
                if ref.kind in {"DEPENDS", "BLOCKED_BY", "CONFLICTS_WITH"}
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "metadata": {
                key: [item["value"] for item in values]
                for key, values in sorted(self.metadata.items())
            },
            "refs": self.normal_refs(),
            "depends_refs": self.refs_by_kind("DEPENDS"),
            "blocked_by_refs": self.refs_by_kind("BLOCKED_BY"),
            "conflicts_with_refs": self.refs_by_kind("CONFLICTS_WITH"),
            "required_refs": self.required_refs(),
            "references": [ref.to_dict() for ref in self.references],
            "specs": split_metadata_list(self.metadata_value("HLD-SPECS")),
            "resources": split_metadata_list(self.metadata_value("HLD-RESOURCES")),
            "risk": self.metadata_value("HLD-RISK"),
            "status": self.metadata_value("HLD-STATUS"),
            "role": self.metadata_value("HLD-ROLE"),
        }


@dataclass
class HldMap:
    source_path: str
    sections: list[HldSection]
    validation_errors: list[str] = field(default_factory=list)
    cycles: list[list[str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def section_by_id(self) -> dict[str, HldSection]:
        return {section.id: section for section in self.sections}

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "sections": [section.to_dict() for section in self.sections],
            "validation_errors": self.validation_errors,
            "cycles": self.cycles,
            "warnings": self.warnings,
        }


def split_metadata_list(value: str) -> list[str]:
    if not value.strip():
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def iter_code_fence_mask(lines: list[str]) -> list[bool]:
    in_fence = False
    mask: list[bool] = []
    for line in lines:
        stripped = line.lstrip()
        is_fence = stripped.startswith("```") or stripped.startswith("~~~")
        mask.append(in_fence or is_fence)
        if is_fence:
            in_fence = not in_fence
    return mask


def parse_hld_text(text: str, *, source_path: str = "HLD.md") -> HldMap:
    lines = text.splitlines()
    fence_mask = iter_code_fence_mask(lines)
    heading_hits: list[tuple[int, str, str]] = []

    for idx, line in enumerate(lines, start=1):
        if fence_mask[idx - 1]:
            continue
        match = SECTION_HEADING_RE.match(line)
        if match:
            heading_hits.append((idx, match.group("id"), match.group("title")))

    sections: list[HldSection] = []
    for pos, (line_start, section_id, title) in enumerate(heading_hits):
        next_start = heading_hits[pos + 1][0] if pos + 1 < len(heading_hits) else len(lines) + 1
        line_end = next_start - 1
        section_lines = lines[line_start - 1:line_end]
        section = HldSection(
            id=section_id,
            title=title,
            line_start=line_start,
            line_end=line_end,
            text="\n".join(section_lines) + ("\n" if section_lines else ""),
        )

        for idx in range(line_start, line_end + 1):
            line = lines[idx - 1]
            if fence_mask[idx - 1]:
                continue
            metadata_match = METADATA_RE.match(line)
            if metadata_match and metadata_match.group("key") in KNOWN_METADATA:
                key = metadata_match.group("key")
                section.metadata.setdefault(key, []).append(
                    {"value": metadata_match.group("value").strip(), "line": idx}
                )
            for ref_match in REF_RE.finditer(line):
                section.references.append(
                    HldReference(
                        target=ref_match.group("target"),
                        kind=ref_match.group("kind") or "REF",
                        line=idx,
                        text=line.strip(),
                    )
                )
        sections.append(section)

    hld_map = HldMap(source_path=source_path, sections=sections)
    hld_map.validation_errors = validate_hld_map(hld_map, lines=lines, fence_mask=fence_mask)
    hld_map.cycles = detect_cycles(hld_map, kinds={"DEPENDS", "BLOCKED_BY"})
    for cycle in hld_map.cycles:
        hld_map.validation_errors.append(f"required reference cycle detected: {' -> '.join(cycle)}")
    for cycle in detect_cycles(hld_map, kinds={"CONFLICTS_WITH"}):
        hld_map.warnings.append(f"conflict reference cycle detected: {' -> '.join(cycle)}")
    for cycle in detect_cycles(hld_map, kinds={"REF"}):
        hld_map.warnings.append(f"normal reference cycle detected: {' -> '.join(cycle)}")
    return hld_map


def parse_hld_file(path: Path) -> HldMap:
    return parse_hld_text(path.read_text(encoding="utf-8"), source_path=str(path))


def has_nearby_tbd(lines: list[str], line_no: int) -> bool:
    start = max(1, line_no - 2)
    end = min(len(lines), line_no + 2)
    for line in lines[start - 1:end]:
        if METADATA_RE.match(line):
            continue
        if "TBD" in line:
            return True
    return False


def validate_hld_map(hld_map: HldMap, *, lines: list[str], fence_mask: list[bool]) -> list[str]:
    errors: list[str] = []
    seen: dict[str, int] = {}

    for section in hld_map.sections:
        if section.id in seen:
            errors.append(f"duplicate HLD-ID heading: {section.id} at lines {seen[section.id]} and {section.line_start}")
        else:
            seen[section.id] = section.line_start

        id_entries = section.metadata.get("HLD-ID", [])
        if len(id_entries) != 1:
            errors.append(f"{section.id}: expected exactly one HLD-ID, found {len(id_entries)}")
        elif id_entries[0]["value"] != section.id:
            errors.append(f"{section.id}: heading ID does not match HLD-ID {id_entries[0]['value']}")

        for key in REQUIRED_METADATA:
            if key == "HLD-ID":
                continue
            entries = section.metadata.get(key, [])
            if not entries:
                errors.append(f"{section.id}: missing {key}")

        if section.metadata_value("HLD-RISK").upper() == "HIGH" and not section.metadata_value("HLD-VERIFY"):
            errors.append(f"{section.id}: HIGH risk section missing HLD-VERIFY")

        for ref in section.references:
            if ref.target not in seen and not any(existing.id == ref.target for existing in hld_map.sections):
                if not has_nearby_tbd(lines, ref.line):
                    errors.append(f"{section.id}: reference to unknown {ref.target} at line {ref.line}")

    for idx, line in enumerate(lines, start=1):
        if fence_mask[idx - 1]:
            continue
        if line.startswith("## HLD-") and not SECTION_HEADING_RE.match(line):
            errors.append(f"invalid HLD heading at line {idx}: {line}")

    return errors


def detect_cycles(hld_map: HldMap, *, kinds: set[str]) -> list[list[str]]:
    graph = {
        section.id: sorted({ref.target for ref in section.references if ref.kind in kinds})
        for section in hld_map.sections
    }
    cycles: list[list[str]] = []
    path: list[str] = []
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            start = path.index(node)
            cycles.append(path[start:] + [node])
            return
        if node in visited:
            return
        visiting.add(node)
        path.append(node)
        for target in graph.get(node, []):
            if target in graph:
                visit(target)
        path.pop()
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
    unique: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()
    for cycle in cycles:
        key = tuple(cycle)
        if key not in seen:
            unique.append(cycle)
            seen.add(key)
    return unique


def hld_index_markdown(hld_map: HldMap) -> str:
    lines = [
        "# HLD Index",
        "",
        f"Source: `{hld_map.source_path}`",
        "",
        "| ID | Title | Lines | Role | Status | Risk | Specs | Required refs | Refs |",
        "|---|---|---:|---|---|---|---|---|---|",
    ]
    for section in hld_map.sections:
        lines.append(
            "| {id} | {title} | {line_start}-{line_end} | {role} | {status} | {risk} | {specs} | {required} | {refs} |".format(
                id=section.id,
                title=section.title.replace("|", "\\|"),
                line_start=section.line_start,
                line_end=section.line_end,
                role=section.metadata_value("HLD-ROLE"),
                status=section.metadata_value("HLD-STATUS"),
                risk=section.metadata_value("HLD-RISK"),
                specs=", ".join(split_metadata_list(section.metadata_value("HLD-SPECS"))) or "TBD",
                required=", ".join(section.required_refs()),
                refs=", ".join(section.normal_refs()),
            )
        )
    if hld_map.validation_errors:
        lines.extend(["", "## Validation Errors", ""])
        lines.extend(f"- {error}" for error in hld_map.validation_errors)
    if hld_map.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in hld_map.warnings)
    return "\n".join(lines) + "\n"


def write_hld_map_outputs(hld_map: HldMap, workspace: Path) -> dict[str, str]:
    sync_dir = workspace / ".specify" / "sync"
    sections_dir = sync_dir / "hld_sections"
    sections_dir.mkdir(parents=True, exist_ok=True)
    map_path = sync_dir / "hld_ref_map.json"
    index_path = sync_dir / "hld_index.md"
    map_path.write_text(json.dumps(hld_map.to_dict(), indent=2), encoding="utf-8")
    index_path.write_text(hld_index_markdown(hld_map), encoding="utf-8")
    section_paths: dict[str, str] = {}
    for section in hld_map.sections:
        section_path = sections_dir / f"{section.id}.md"
        section_path.write_text(section.text, encoding="utf-8")
        section_paths[section.id] = str(section_path.relative_to(workspace))
    return {
        "map": str(map_path.relative_to(workspace)),
        "index": str(index_path.relative_to(workspace)),
        "sections_dir": str(sections_dir.relative_to(workspace)),
        "sections": section_paths,
    }


def load_hld_map_json(path: Path) -> HldMap:
    data = json.loads(path.read_text(encoding="utf-8"))
    sections: list[HldSection] = []
    for item in data.get("sections", []):
        metadata = {
            key: [{"value": value, "line": 0} for value in values]
            for key, values in item.get("metadata", {}).items()
        }
        section = HldSection(
            id=item["id"],
            title=item.get("title", ""),
            line_start=int(item.get("line_start", 0)),
            line_end=int(item.get("line_end", 0)),
            text="",
            metadata=metadata,
            references=[
                HldReference(
                    target=ref["target"],
                    kind=ref.get("kind", "REF"),
                    line=int(ref.get("line", 0)),
                    text=ref.get("text", ""),
                )
                for ref in item.get("references", [])
            ],
        )
        sections.append(section)
    return HldMap(
        source_path=data.get("source_path", ""),
        sections=sections,
        validation_errors=list(data.get("validation_errors", [])),
        cycles=list(data.get("cycles", [])),
        warnings=list(data.get("warnings", [])),
    )
