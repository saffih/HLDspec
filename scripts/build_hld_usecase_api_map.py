#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hld_map
from hldspec.hld_canonical_line import EXCLUDED_SCOPES, parse_canonical_line

SYNC_REL = Path(".specify") / "sync"

# A section that carries exactly one of these as its HLD-ROLE has already declared
# its API/interface-vs-processing boundary; a keyword co-occurrence is not a real
# ambiguity, so it must not be minted as a human checkpoint question. This is the
# canonical role vocabulary from HLD_FORMAT.md (plus `reference`, used in practice).
RECOGNIZED_ROLES = (
    "purpose",
    "reference",
    "governance",
    "architecture",
    "processing",
    "api",
    "ui",
    "operations",
    "testing",
    "risk",
)

ACTOR_TERMS = (
    "user",
    "human",
    "operator",
    "admin",
    "developer",
    "engineer",
    "agent",
    "judge",
    "orchestrator",
    "speckit",
    "hldspec",
    "system",
)
API_TERMS = (
    "api",
    "interface",
    "endpoint",
    "http",
    "rest",
    "grpc",
    "cli",
    "command",
    "contract",
    "request",
    "response",
    "webhook",
    "proxy",
)
DATA_TERMS = (
    "data",
    "state",
    "source of truth",
    "storage",
    "database",
    "schema",
    "json",
    "markdown",
    "md",
    "queue",
    "manifest",
    "artifact",
    "dossier",
    "index",
)
PROCESSING_TERMS = (
    "flow",
    "workflow",
    "process",
    "processing",
    "orchestration",
    "pipeline",
    "sync",
    "run",
    "execute",
    "convert",
    "build",
    "generate",
)
UI_TERMS = (
    "ui",
    "web ui",
    "screen",
    "view",
    "display",
    "status",
    "interview",
    "question",
    "prompt",
)
OPERATIONS_TERMS = (
    "rollback",
    "recovery",
    "retry",
    "failure",
    "observability",
    "timeout",
    "runbook",
    "checkpoint",
)
RISK_TERMS = (
    "risk",
    "conflict",
    "blocker",
    "failure",
    "unsafe",
    "unknown",
    "missing",
)
NON_GOAL_TERMS = (
    "non-goal",
    "non goal",
    "out of scope",
    "must not",
    "do not",
    "should not",
    "never",
)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def words_present(text: str, terms: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    found: list[str] = []
    for term in terms:
        if term in lower:
            found.append(term)
    return sorted(dict.fromkeys(found))


def short_text(text: str, limit: int = 220) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def classification_by_id(workspace: Path) -> dict[str, dict[str, Any]]:
    data = read_json(workspace / SYNC_REL / "hld_section_classification.json")
    result: dict[str, dict[str, Any]] = {}
    for item in as_list(data.get("sections")):
        if isinstance(item, dict) and item.get("hld_id"):
            result[str(item["hld_id"])] = item
    return result


def section_kind(section: hld_map.HldSection, classes: dict[str, dict[str, Any]]) -> str:
    item = classes.get(section.id, {})
    if isinstance(item, dict) and item.get("section_kind"):
        return str(item["section_kind"])
    return "SPEC_CANDIDATE"


def is_spec_candidate(section: hld_map.HldSection, classes: dict[str, dict[str, Any]]) -> bool:
    specs = [part for part in hld_map.split_metadata_list(section.metadata_value("HLD-SPECS")) if part and part.upper() != "TBD" and part.lower() != "constitution"]
    if specs:
        return True
    item = classes.get(section.id)
    if not isinstance(item, dict):
        return True
    return bool(item.get("spec_candidate", True))


def buildability_signals(section: hld_map.HldSection) -> list[str]:
    text = f"{section.title}\n{section.text}\n{section.metadata_value('HLD-ROLE')}\n{section.metadata_value('HLD-RESOURCES')}".lower()
    signals: list[str] = []
    checks = [
        ("api_interface", API_TERMS),
        ("data_source_of_truth", DATA_TERMS),
        ("processing_workflow", PROCESSING_TERMS),
        ("ui_interaction", UI_TERMS),
        ("operations_runtime", OPERATIONS_TERMS),
    ]
    for name, terms in checks:
        if any(term in text for term in terms):
            signals.append(name)
    if section.metadata_value("HLD-VERIFY"):
        signals.append("verification")
    return sorted(dict.fromkeys(signals))


def dependency_records(parsed: hld_map.HldMap) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for section in parsed.sections:
        for ref in section.references:
            records.append(
                {
                    "from_hld_id": section.id,
                    "from_title": section.title,
                    "to_hld_id": ref.target,
                    "kind": ref.kind,
                    "line": ref.line,
                    "evidence": ref.text,
                }
            )
    return records


def first_buildable_feature(candidates: list[dict[str, Any]], deps: list[dict[str, Any]]) -> dict[str, Any]:
    if not candidates:
        return {}
    candidate_ids = {str(item["hld_id"]) for item in candidates}
    depended_by_candidate: set[str] = set()
    for dep in deps:
        source = str(dep.get("from_hld_id", ""))
        target = str(dep.get("to_hld_id", ""))
        if source in candidate_ids and target in candidate_ids and source != target:
            depended_by_candidate.add(source)
    roots = [item for item in candidates if str(item["hld_id"]) not in depended_by_candidate]
    selected = roots[0] if roots else candidates[0]
    return {
        "hld_id": selected.get("hld_id", ""),
        "title": selected.get("title", ""),
        "why_first": "First buildable feature candidate with no candidate-level dependency." if roots else "Fallback to first buildable candidate because no dependency-free candidate was identified.",
        "buildability_signals": selected.get("buildability_signals", []),
    }


def build_map(parsed: hld_map.HldMap, workspace: Path) -> dict[str, Any]:
    classes = classification_by_id(workspace)
    deps = dependency_records(parsed)
    actors: dict[str, dict[str, Any]] = {}
    journeys: list[dict[str, Any]] = []
    use_cases: list[dict[str, Any]] = []
    api_surfaces: list[dict[str, Any]] = []
    data_objects: list[dict[str, Any]] = []
    feature_candidates: list[dict[str, Any]] = []
    context_only: list[dict[str, Any]] = []
    non_goals: list[dict[str, Any]] = []
    risks: list[dict[str, Any]] = []
    open_questions: list[dict[str, Any]] = []

    for section in parsed.sections:
        text = f"{section.title}\n{section.text}"
        lower = text.lower()
        kind = section_kind(section, classes)
        spec_candidate = is_spec_candidate(section, classes)
        actor_hits = words_present(text, ACTOR_TERMS)
        api_hits = words_present(text, API_TERMS)
        data_hits = words_present(text, DATA_TERMS)
        processing_hits = words_present(text, PROCESSING_TERMS)
        ui_hits = words_present(text, UI_TERMS)
        operations_hits = words_present(text, OPERATIONS_TERMS)
        risk_hits = words_present(text, RISK_TERMS)
        signals = buildability_signals(section)
        role_tokens = [t for t in re.split(r"[,\s]+", section.metadata_value("HLD-ROLE").strip().lower()) if t]
        has_clean_role = len(role_tokens) == 1 and role_tokens[0] in RECOGNIZED_ROLES
        is_high_risk = section.metadata_value("HLD-RISK").strip().upper() == "HIGH"

        for actor in actor_hits:
            normalized = actor.title() if actor not in {"api", "ui"} else actor.upper()
            item = actors.setdefault(
                normalized,
                {
                    "name": normalized,
                    "source_hld_sections": [],
                    "evidence": [],
                },
            )
            item["source_hld_sections"].append(section.id)
            if len(item["evidence"]) < 3:
                item["evidence"].append(section.title)

        if any(term in lower for term in ("journey", "flow", "workflow", "run", "interview", "approval", "conversion")):
            journeys.append(
                {
                    "id": f"J-{len(journeys) + 1:03d}",
                    "name": section.title,
                    "source_hld_sections": [section.id],
                    "summary": short_text(section.text),
                }
            )

        if spec_candidate and signals:
            use_cases.append(
                {
                    "id": f"UC-{len(use_cases) + 1:03d}",
                    "name": section.title,
                    "source_hld_sections": [section.id],
                    "buildability_signals": signals,
                    "summary": short_text(section.text),
                }
            )
            feature_candidates.append(
                {
                    "hld_id": section.id,
                    "title": section.title,
                    "section_kind": kind,
                    "buildable": True,
                    "buildability_signals": signals,
                    "source_hld_sections": [section.id],
                    "risk": section.metadata_value("HLD-RISK"),
                    "verify": section.metadata_value("HLD-VERIFY"),
                    "depends_on_hld_sections": section.required_refs() + section.normal_refs(),
                }
            )
        elif not spec_candidate:
            classification = classes.get(section.id, {})
            context_only.append(
                {
                    "hld_id": section.id,
                    "title": section.title,
                    "section_kind": kind,
                    "recommended_action": classification.get("recommended_action", "KEEP_AS_CONTEXT") if isinstance(classification, dict) else "KEEP_AS_CONTEXT",
                    "feeds": ["constitution", "planning", "prioritization", "verification_context"],
                    "reason": classification.get("reason", "Classified as non-buildable context.") if isinstance(classification, dict) else "Classified as non-buildable context.",
                }
            )

        if api_hits:
            api_surfaces.append(
                {
                    "name": section.title,
                    "source_hld_sections": [section.id],
                    "terms": api_hits,
                    "contract_risk": "review_api_processing_split" if processing_hits and not has_clean_role else "normal",
                    "summary": short_text(section.text),
                }
            )

        if data_hits:
            data_objects.append(
                {
                    "name": section.title,
                    "source_hld_sections": [section.id],
                    "terms": data_hits,
                    "source_of_truth_risk": "source of truth" in lower or "state" in lower or "database" in lower,
                    "summary": short_text(section.text),
                }
            )

        if risk_hits or section.metadata_value("HLD-RISK").upper() == "HIGH" or section.refs_by_kind("CONFLICTS_WITH"):
            risks.append(
                {
                    "source_hld_sections": [section.id],
                    "title": section.title,
                    "risk": section.metadata_value("HLD-RISK"),
                    "terms": risk_hits,
                    "conflicts_with": section.refs_by_kind("CONFLICTS_WITH"),
                    "summary": short_text(section.text),
                }
            )

        hld_desc = section.metadata_value("HLD-DESC").strip()
        canonical = parse_canonical_line(hld_desc) if hld_desc else None
        if (canonical and canonical.get("scope") in EXCLUDED_SCOPES) or (
            not canonical and any(term in lower for term in NON_GOAL_TERMS)
        ):
            non_goals.append(
                {
                    "source_hld_sections": [section.id],
                    "title": section.title,
                    "summary": short_text(section.text),
                }
            )

        # Only a spec-candidate HIGH-risk anchor genuinely needs a governing spec
        # named: there, a TBD HLD-SPECS is a real gap. On descriptive, low-risk, or
        # not-yet-built anchors, an empty spec/resources field is legitimate, not a
        # human decision — flagging it halts the pipeline on noise.
        tbd_fields = [
            key
            for key in ("HLD-SPECS", "HLD-RESOURCES", "HLD-OWNER")
            if section.metadata_value(key).upper() == "TBD"
        ]
        if tbd_fields and spec_candidate and is_high_risk:
            open_questions.append(
                {
                    "source_hld_sections": [section.id],
                    "question": f"Resolve TBD metadata for {section.title}: {', '.join(tbd_fields)}.",
                    "type": "metadata_tbd",
                }
            )

    for item in actors.values():
        item["source_hld_sections"] = sorted(dict.fromkeys(str(x) for x in item["source_hld_sections"]))

    first = first_buildable_feature(feature_candidates, deps)
    status = "ready" if feature_candidates else "REWORK_REQUIRED"
    blockers: list[dict[str, Any]] = []
    if not feature_candidates:
        blockers.append(
            {
                "id": "UCAPI-001",
                "severity": "BLOCKER",
                "finding": "No buildable feature candidates were extracted from the HLD.",
                "recommendation": "Fix HLD section classification or add implementable API/data/processing/UI/system sections before SpecKit handoff.",
            }
        )

    return {
        "schema_version": 1,
        "status": status,
        "source_hld": parsed.source_path,
        "purpose": "Show what HLDspec thinks the system does before SpecKit work begins.",
        "actors": sorted(actors.values(), key=lambda item: str(item["name"])),
        "user_journeys": journeys,
        "system_use_cases": use_cases,
        "api_interface_surfaces": api_surfaces,
        "data_source_of_truth_objects": data_objects,
        "feature_candidates": feature_candidates,
        "first_buildable_feature": first,
        "context_only_sections": context_only,
        "dependencies": deps,
        "non_goals": non_goals,
        "risks": risks,
        "open_questions": open_questions,
        "blockers": blockers,
        "counts": {
            "actors": len(actors),
            "user_journeys": len(journeys),
            "system_use_cases": len(use_cases),
            "api_interface_surfaces": len(api_surfaces),
            "data_source_of_truth_objects": len(data_objects),
            "feature_candidates": len(feature_candidates),
            "context_only_sections": len(context_only),
            "dependencies": len(deps),
            "non_goals": len(non_goals),
            "risks": len(risks),
            "open_questions": len(open_questions),
        },
    }


def render_md(data: dict[str, Any]) -> str:
    lines = [
        "# HLD Use-case and API Map",
        "",
        "",
        "",
        f"Status: `{data.get('status')}`",
        f"Source HLD: `{data.get('source_hld')}`",
        "",
        "Purpose: Show what HLDspec thinks the system does before SpecKit work begins.",
        "",
        "## Summary",
        "",
    ]
    counts = data.get("counts", {}) if isinstance(data.get("counts"), dict) else {}
    for key in [
        "actors",
        "user_journeys",
        "system_use_cases",
        "api_interface_surfaces",
        "data_source_of_truth_objects",
        "feature_candidates",
        "context_only_sections",
        "dependencies",
        "risks",
        "open_questions",
    ]:
        lines.append(f"- {key}: {counts.get(key, 0)}")

    first = data.get("first_buildable_feature", {}) if isinstance(data.get("first_buildable_feature"), dict) else {}
    lines += ["", "## First buildable feature", ""]
    if first:
        lines += [
            f"- HLD: `{first.get('hld_id', '')}`",
            f"- title: {first.get('title', '')}",
            f"- why first: {first.get('why_first', '')}",
            f"- buildability signals: {', '.join(first.get('buildability_signals', [])) or 'none'}",
        ]
    else:
        lines.append("- none identified")

    sections = [
        ("Actors", "actors", "name"),
        ("User journeys", "user_journeys", "name"),
        ("System use cases", "system_use_cases", "name"),
        ("API/interface surfaces", "api_interface_surfaces", "name"),
        ("Data/source-of-truth objects", "data_source_of_truth_objects", "name"),
        ("Feature candidates", "feature_candidates", "title"),
        ("Context-only sections", "context_only_sections", "title"),
        ("Risks", "risks", "title"),
        ("Open questions", "open_questions", "question"),
    ]
    for title, key, name_key in sections:
        lines += ["", f"## {title}", ""]
        items = data.get(key, [])
        if not isinstance(items, list) or not items:
            lines.append("- none")
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            hlds = item.get("source_hld_sections", [])
            if not isinstance(hlds, list):
                hlds = []
            label = item.get(name_key, item.get("hld_id", ""))
            lines.append(f"- {label} [{', '.join(str(h) for h in hlds) or item.get('hld_id', '')}]")
            if item.get("buildability_signals"):
                lines.append(f"  - buildability: {', '.join(item.get('buildability_signals', []))}")
            if item.get("section_kind"):
                lines.append(f"  - kind: `{item.get('section_kind')}`")
            if item.get("contract_risk"):
                lines.append(f"  - contract risk: `{item.get('contract_risk')}`")
            if item.get("summary"):
                lines.append(f"  - summary: {item.get('summary')}")

    lines += ["", "## Dependencies", ""]
    deps = data.get("dependencies", [])
    if not isinstance(deps, list) or not deps:
        lines.append("- none")
    else:
        for dep in deps:
            if isinstance(dep, dict):
                lines.append(f"- `{dep.get('from_hld_id')}` --{dep.get('kind')}--> `{dep.get('to_hld_id')}`")

    blockers = data.get("blockers", [])
    if isinstance(blockers, list) and blockers:
        lines += ["", "## Blockers", ""]
        for blocker in blockers:
            if isinstance(blocker, dict):
                lines.append(f"- {blocker.get('id')}: {blocker.get('finding')} Recommendation: {blocker.get('recommendation')}")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build HLD use-case/API map before SpecKit prework.")
    parser.add_argument("hld")
    parser.add_argument("workspace")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    hld_path = Path(args.hld)
    if not hld_path.is_absolute():
        hld_path = (workspace / hld_path).resolve()

    parsed = hld_map.parse_hld_file(hld_path)
    if parsed.validation_errors:
        print("Invalid HLD map; cannot build use-case/API map.", file=sys.stderr)
        for error in parsed.validation_errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    data = build_map(parsed, workspace)
    out = workspace / SYNC_REL
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / "hld_usecase_api_map.json"
    md_path = out / "hld_usecase_api_map.md"
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLD use-case/API map generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    return 0 if data["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
