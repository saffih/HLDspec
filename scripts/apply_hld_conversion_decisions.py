#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


VALID_DECISIONS = {
    "SPLIT_AS_PROPOSED",
    "MODIFY_SPLIT",
    "KEEP_AS_ONE",
    "SPLIT",
}


@dataclass(frozen=True)
class ConversionSection:
    hld_id: str
    title: str
    start: int
    end: int
    role: str
    risk: str
    specs: str = "TBD"
    resources: str = "TBD"


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def question_map(queue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for question in queue.get("questions", []):
        if isinstance(question, dict) and question.get("source_candidate_id"):
            result[str(question["source_candidate_id"])] = question
    return result


def candidate_map(plan: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for candidate in plan.get("candidates", []):
        if isinstance(candidate, dict) and candidate.get("proposed_hld_id"):
            result[str(candidate["proposed_hld_id"])] = candidate
    return result


def validate_queue(queue: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for question in queue.get("questions", []):
        if not isinstance(question, dict):
            continue
        qid = str(question.get("question_id", "UNKNOWN"))
        candidate_id = str(question.get("source_candidate_id", "UNKNOWN"))
        decision = str(question.get("human_decision", "TBD"))
        if decision == "TBD":
            errors.append(f"{qid} {candidate_id}: human_decision is TBD")
            continue
        if decision not in VALID_DECISIONS:
            errors.append(f"{qid} {candidate_id}: unsupported human_decision {decision!r}")
            continue
        if decision in {"MODIFY_SPLIT", "SPLIT"} and not question.get("approved_split_plan"):
            errors.append(f"{qid} {candidate_id}: {decision} requires approved_split_plan")
        if decision == "KEEP_AS_ONE" and not str(question.get("approved_keep_reason", "")).strip():
            errors.append(f"{qid} {candidate_id}: KEEP_AS_ONE requires approved_keep_reason")
    return errors


def inherited_metadata(candidate: dict[str, Any]) -> tuple[str, str, str, str]:
    metadata = candidate.get("metadata_skeleton")
    if not isinstance(metadata, dict):
        metadata = {}
    role = str(candidate.get("proposed_role") or metadata.get("HLD-ROLE") or "architecture")
    risk = str(candidate.get("proposed_risk") or metadata.get("HLD-RISK") or "MEDIUM")
    specs = str(metadata.get("HLD-SPECS") or "TBD")
    resources = str(metadata.get("HLD-RESOURCES") or "TBD")
    return role, risk, specs, resources


def split_plan_to_sections(
    *,
    candidate: dict[str, Any],
    split_plan: list[Any],
    parent_start: int,
) -> list[ConversionSection]:
    role, risk, specs, resources = inherited_metadata(candidate)
    sections: list[ConversionSection] = []

    clean_splits = [item for item in split_plan if isinstance(item, dict)]
    for idx, split in enumerate(clean_splits):
        start = as_int(split.get("source_line_start") or split.get("start"), 0)
        end = as_int(split.get("source_line_end") or split.get("end"), 0)
        if idx == 0 and parent_start and start > parent_start:
            # Include the parent heading/preamble in the first split so no raw major heading is left before the first HLD anchor.
            start = parent_start
        section_id = str(split.get("proposed_hld_id") or split.get("id") or "").strip()
        title = str(split.get("title") or "").strip()
        if not section_id or not title or start <= 0 or end < start:
            raise ValueError(f"Invalid split entry: {split!r}")
        sections.append(
            ConversionSection(
                hld_id=section_id,
                title=title,
                start=start,
                end=end,
                role=str(split.get("role") or role),
                risk=str(split.get("risk") or risk),
                specs=str(split.get("specs") or specs),
                resources=str(split.get("resources") or resources),
            )
        )
    return sections


def renumber_sections_numeric(sections: list[ConversionSection]) -> list[ConversionSection]:
    """HLD map accepts only numeric IDs like HLD-001.

    Human-facing split proposals may use labels like HLD-009A for readability,
    but executable conversion must emit valid numeric HLD IDs.
    """
    result: list[ConversionSection] = []
    for idx, section in enumerate(sections, start=1):
        result.append(
            ConversionSection(
                hld_id=f"HLD-{idx:03d}",
                title=section.title,
                start=section.start,
                end=section.end,
                role=section.role,
                risk=section.risk,
                specs=section.specs,
                resources=section.resources,
            )
        )
    return result


def build_conversion_sections(plan: dict[str, Any], queue: dict[str, Any]) -> list[ConversionSection]:
    questions = question_map(queue)
    sections: list[ConversionSection] = []

    for candidate in plan.get("candidates", []):
        if not isinstance(candidate, dict):
            continue

        candidate_id = str(candidate.get("proposed_hld_id", "")).strip()
        title = str(candidate.get("title", "")).strip()
        start = as_int(candidate.get("source_line_start"), 0)
        end = as_int(candidate.get("source_line_end"), 0)
        role, risk, specs, resources = inherited_metadata(candidate)
        question = questions.get(candidate_id)

        if question:
            decision = str(question.get("human_decision", "TBD"))
            if decision == "SPLIT_AS_PROPOSED":
                proposal = question.get("default_proposal", {})
                if not isinstance(proposal, dict):
                    raise ValueError(f"{candidate_id}: missing default proposal")
                split_plan = proposal.get("proposed_split_plan", [])
                if not isinstance(split_plan, list) or not split_plan:
                    raise ValueError(f"{candidate_id}: SPLIT_AS_PROPOSED has no proposed split plan")
                sections.extend(split_plan_to_sections(candidate=candidate, split_plan=split_plan, parent_start=start))
                continue

            if decision in {"MODIFY_SPLIT", "SPLIT"}:
                split_plan = question.get("approved_split_plan", [])
                if not isinstance(split_plan, list) or not split_plan:
                    raise ValueError(f"{candidate_id}: {decision} has no approved_split_plan")
                sections.extend(split_plan_to_sections(candidate=candidate, split_plan=split_plan, parent_start=start))
                continue

            if decision == "KEEP_AS_ONE":
                sections.append(
                    ConversionSection(
                        hld_id=candidate_id,
                        title=title,
                        start=start,
                        end=end,
                        role=role,
                        risk=risk,
                        specs=specs,
                        resources=resources,
                    )
                )
                continue

            raise ValueError(f"{candidate_id}: unsupported decision {decision!r}")

        if not candidate_id or not title or start <= 0 or end < start:
            raise ValueError(f"Invalid conversion candidate: {candidate!r}")
        sections.append(
            ConversionSection(
                hld_id=candidate_id,
                title=title,
                start=start,
                end=end,
                role=role,
                risk=risk,
                specs=specs,
                resources=resources,
            )
        )

    sections.sort(key=lambda item: item.start)
    previous_end = 0
    for section in sections:
        if section.start <= previous_end:
            raise ValueError(f"Overlapping conversion section at {section.hld_id}: starts {section.start}, previous ended {previous_end}")
        previous_end = section.end

    return renumber_sections_numeric(sections)


def assert_input_not_already_converted(hld_path: Path) -> None:
    text = hld_path.read_text(encoding="utf-8", errors="replace")
    if re.search(r"^## HLD-\d{3}\s+-\s+", text, flags=re.MULTILINE) or re.search(
        r"^HLD-ID:\s*HLD-\d{3}", text, flags=re.MULTILINE
    ):
        raise ValueError(
            "Input HLD already appears to contain HLDspec anchors/metadata. "
            "Restore the raw working copy before applying conversion decisions. "
            "Example: cp HLD.md.pre-hldspec.bak HLD.md"
        )


def metadata_block(section: ConversionSection) -> list[str]:
    return [
        f"## {section.hld_id} - {section.title}",
        "",
        f"HLD-ID: {section.hld_id}",
        f"HLD-ROLE: {section.role}",
        "HLD-STATUS: active",
        f"HLD-RISK: {section.risk}",
        f"HLD-SPECS: {section.specs}",
        f"HLD-RESOURCES: {section.resources}",
        "HLD-VERIFY: section can be processed without loading the full HLD; original content is preserved under this HLD anchor",
        "",
    ]


def apply_conversion(hld_path: Path, sections: list[ConversionSection]) -> str:
    lines = hld_path.read_text(encoding="utf-8", errors="replace").splitlines()
    starts = {section.start: section for section in sections}

    out: list[str] = []
    for line_no, line in enumerate(lines, start=1):
        section = starts.get(line_no)
        if section:
            out.extend(metadata_block(section))
        out.append(line)
    return "\n".join(out).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply approved HLD conversion decisions to a working HLD copy.")
    parser.add_argument("hld")
    parser.add_argument("decision_queue_json")
    parser.add_argument("--plan", default="", help="Optional hld_conversion_plan.json. Defaults to queue plan_path or sibling file.")
    parser.add_argument("--output", default="", help="Output HLD path. Default: update input HLD in place.")
    parser.add_argument("--force", action="store_true", help="Allow overwriting output path.")
    args = parser.parse_args()

    hld_path = Path(args.hld)
    queue_path = Path(args.decision_queue_json)
    queue = load_json(queue_path)

    errors = validate_queue(queue)
    if errors:
        print("Refusing to apply conversion decisions:")
        for error in errors:
            print(f"- {error}")
        return 2

    if args.plan:
        plan_path = Path(args.plan)
    else:
        plan_path = Path(str(queue.get("plan_path", "")))
        if not plan_path.exists():
            plan_path = queue_path.with_name("hld_conversion_plan.json")
    if not plan_path.exists():
        print(f"Missing conversion plan: {plan_path}")
        return 1

    try:
        assert_input_not_already_converted(hld_path)
    except ValueError as exc:
        print(f"Refusing to apply conversion decisions: {exc}")
        return 2

    plan = load_json(plan_path)
    sections = build_conversion_sections(plan, queue)
    converted = apply_conversion(hld_path, sections)

    output_path = Path(args.output) if args.output else hld_path
    if output_path.exists() and output_path != hld_path and not args.force:
        print(f"Refusing to overwrite existing output without --force: {output_path}")
        return 1

    backup_path = hld_path.with_suffix(hld_path.suffix + ".pre-hldspec.bak")
    if output_path == hld_path and not backup_path.exists():
        shutil.copy2(hld_path, backup_path)

    output_path.write_text(converted, encoding="utf-8")

    print("Applied HLD conversion decisions.")
    print(f"- input: {hld_path}")
    print(f"- output: {output_path}")
    if output_path == hld_path:
        print(f"- backup: {backup_path}")
    print(f"- HLD sections inserted: {len(sections)}")
    print("- source content preserved under inserted HLD anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
