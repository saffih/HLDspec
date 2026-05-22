from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARCHITECTURE_HANDOFF = "architecture_handoff.md"
PRODUCT_HANDOFF = "product_handoff.md"


def _read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _artifact_status(sync: Path, names: list[str]) -> list[str]:
    lines: list[str] = []
    for name in names:
        path = sync / name
        status = "present" if path.exists() else "missing"
        lines.append(f"- {name}: `{status}`")
    return lines


def _planned_spec_lines(plan: dict[str, Any]) -> list[str]:
    planned = plan.get("planned_specs", [])
    if not isinstance(planned, list) or not planned:
        return ["- none found"]

    lines: list[str] = []
    for idx, spec in enumerate(planned, start=1):
        if not isinstance(spec, dict):
            continue
        spec_id = spec.get("planned_spec_id") or spec.get("id") or f"planned_spec_{idx}"
        title = spec.get("title") or spec.get("name") or "(untitled)"
        flags = spec.get("quality_flags") or []
        requires_review = bool(spec.get("requires_user_review"))
        recommendation = spec.get("recommendation") or spec.get("quality_recommendation") or ""
        line = f"- {spec_id}: {title}"
        extra = []
        if flags:
            extra.append(f"flags={flags}")
        if requires_review:
            extra.append("requires_user_review=true")
        if recommendation:
            extra.append(f"recommendation={recommendation}")
        if extra:
            line += " (" + "; ".join(str(item) for item in extra) + ")"
        lines.append(line)
    return lines or ["- none found"]


def _quality_summary(plan: dict[str, Any], gate: dict[str, Any]) -> list[str]:
    quality = plan.get("plan_quality", {}) if isinstance(plan.get("plan_quality"), dict) else {}
    return [
        f"- plan_quality.decision: `{quality.get('decision', 'unknown')}`",
        f"- plan_quality.recommendation: `{quality.get('recommendation', 'unknown')}`",
        f"- plan_quality.conflicts: `{len(quality.get('conflicts', []) if isinstance(quality.get('conflicts', []), list) else [])}`",
        f"- gate decision: `{gate.get('decision', 'TBD')}`",
        f"- gate rationale: {gate.get('rationale', 'none') or 'none'}",
    ]


def _excerpt_block(title: str, text: str, limit: int = 1200) -> list[str]:
    clean = text.strip()
    if not clean:
        return [f"## {title}", "", "_Missing or empty._", ""]
    excerpt = clean[:limit]
    if len(clean) > limit:
        excerpt += "\n\n... truncated in consolidated handoff; see source artifact ..."
    return [f"## {title}", "", "```text", excerpt, "```", ""]


def build_architecture_handoff(sync: Path) -> str:
    plan = _load_json(sync / "spec_build_plan.json")
    gate = _load_json(sync / "spec_build_plan_gate_decision.json")

    lines: list[str] = [
        "# Architecture Handoff",
        "",
        "made by AI",
        "",
        "## Purpose",
        "",
        "Consolidated architecture handoff generated from HLDspec V2 sync artifacts.",
        "",
        "This document is a review aid. Source artifacts remain authoritative.",
        "",
        "## Source artifacts",
        "",
        *_artifact_status(
            sync,
            [
                "feature_dependency_graph.md",
                "constitution_update_plan.md",
                "spec_build_plan.md",
                "spec_build_plan_review.md",
                "spec_build_plan.json",
                "spec_build_plan_gate_decision.json",
                "speckit_proxy_dossier.md",
                "hldspec_state.md",
            ],
        ),
        "",
        "## Plan quality and gate decision",
        "",
        *_quality_summary(plan, gate),
        "",
        "## Architecture / dependency focus",
        "",
        "- Verify API and data boundaries before SpecKit.",
        "- Preserve source-of-truth ownership.",
        "- Keep critical database/storage API boundaries explicit.",
        "- Do not merge planning/context sections into fake implementation specs.",
        "- Treat source-HLD mutation as a separate approval path.",
        "",
        "## Planned specs with architecture review flags",
        "",
        *_planned_spec_lines(plan),
        "",
    ]

    lines.extend(_excerpt_block("Feature dependency graph", _read_text(sync / "feature_dependency_graph.md")))
    lines.extend(_excerpt_block("Constitution update plan", _read_text(sync / "constitution_update_plan.md")))
    lines.extend(_excerpt_block("Spec build plan review", _read_text(sync / "spec_build_plan_review.md")))
    lines.extend(_excerpt_block("SpecKit proxy dossier", _read_text(sync / "speckit_proxy_dossier.md")))

    lines.extend(
        [
            "## Safety",
            "",
            "- SpecKit is not invoked by this document.",
            "- Source HLD is not modified by this document.",
            "- App code is not implemented by this document.",
            "",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def build_product_handoff(sync: Path) -> str:
    plan = _load_json(sync / "spec_build_plan.json")
    gate = _load_json(sync / "spec_build_plan_gate_decision.json")

    lines: list[str] = [
        "# Product Handoff",
        "",
        "made by AI",
        "",
        "## Purpose",
        "",
        "Consolidated product/spec handoff generated from HLDspec V2 sync artifacts.",
        "",
        "This document is a review aid. Source artifacts remain authoritative.",
        "",
        "## Source artifacts",
        "",
        *_artifact_status(
            sync,
            [
                "speckit_input_manifest.md",
                "speckit_invocation_queue.md",
                "target_spec_work_order.md",
                "spec_branch_queue.md",
                "speckit_prework_package.md",
                "speckit_prework_quality_review.md",
                "speckit_prework_quality_review.json",
                "speckit_proxy_dossier.md",
            ],
        ),
        "",
        "## Product / SpecKit readiness summary",
        "",
        *_quality_summary(plan, gate),
        "",
        "## Planned specs",
        "",
        *_planned_spec_lines(plan),
        "",
        "## Product correctness guard",
        "",
        "- A planned spec should represent a real capability, interface, data/state responsibility, processing behavior, or implementation-relevant constraint.",
        "- Planning/context sections should not become fake specs.",
        "- Database/storage API boundaries may remain specs when the review rationale says they are intentional critical boundaries.",
        "",
    ]

    lines.extend(_excerpt_block("SpecKit input manifest", _read_text(sync / "speckit_input_manifest.md")))
    lines.extend(_excerpt_block("SpecKit invocation queue", _read_text(sync / "speckit_invocation_queue.md")))
    lines.extend(_excerpt_block("Target spec work order", _read_text(sync / "target_spec_work_order.md")))
    lines.extend(_excerpt_block("SpecKit prework package", _read_text(sync / "speckit_prework_package.md")))

    lines.extend(
        [
            "## Safety",
            "",
            "- SpecKit is not invoked by this document.",
            "- Final specs are not written manually by this document.",
            "- App code is not implemented by this document.",
            "",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def write_handoff_docs(sync: Path) -> tuple[Path, Path]:
    sync.mkdir(parents=True, exist_ok=True)
    architecture = sync / ARCHITECTURE_HANDOFF
    product = sync / PRODUCT_HANDOFF

    architecture.write_text(build_architecture_handoff(sync), encoding="utf-8")
    product.write_text(build_product_handoff(sync), encoding="utf-8")

    return architecture, product
