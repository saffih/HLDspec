from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict

SCHEMA_VERSION = 1
DEFAULT_MAX_BUNDLE_SIZE = 3
HARD_MAX_BUNDLE_SIZE = 5

THEMES: dict[str, tuple[str, ...]] = {
    "architecture": ("scope", "architecture", "overview", "integration", "definition", "foundation"),
    "data": ("database", "db", "data", "brain", "sync", "storage", "state", "model"),
    "api": ("api", "interface", "cli", "http", "command", "contract", "endpoint", "config", "session"),
    "flow": ("entity", "flow", "diagram", "transparency", "orchestration", "workflow"),
    "quality": ("security", "performance", "error", "reliability", "validation", "guard"),
    "ops": ("operational", "runbook", "environment", "staging", "technology", "stack"),
    "handoff": ("handoff", "implementation", "question", "contradiction", "failure", "approval"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    lowered = re.sub(r"-+", "-", lowered).strip("-")
    return lowered or "bundle"


def spec_id(item: dict[str, Any]) -> str:
    for key in ("feature_id", "spec_id", "planned_spec_id", "id"):
        value = item.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def spec_title(item: dict[str, Any]) -> str:
    for key in ("feature_name", "title", "name", "spec_name"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    sid = spec_id(item)
    return sid or "Untitled spec"


def spec_layer(item: dict[str, Any]) -> str:
    for container_key in ("architecture_context", "speckit_context", "product_context"):
        container = as_dict(item.get(container_key))
        value = container.get("layer")
        if isinstance(value, str) and value.strip():
            return value.strip()
    value = item.get("layer")
    return value.strip() if isinstance(value, str) and value.strip() else "unspecified"


def depends_on(item: dict[str, Any]) -> list[str]:
    deps = as_list(item.get("depends_on_features")) or as_list(item.get("depends_on_specs")) or as_list(item.get("depends_on"))
    return [str(dep) for dep in deps if str(dep)]


def _values_from_context(item: dict[str, Any], key: str) -> set[str]:
    values: set[str] = set()
    for container_key in ("architecture_context", "speckit_context", "product_context"):
        container = as_dict(item.get(container_key))
        for raw in as_list(container.get(key)):
            if isinstance(raw, dict):
                for candidate_key in ("name", "id", "contract", "object", "title"):
                    candidate = raw.get(candidate_key)
                    if candidate:
                        values.add(str(candidate).lower())
            elif raw:
                values.add(str(raw).lower())
    for raw in as_list(item.get(key)):
        if raw:
            values.add(str(raw).lower())
    return values


def contracts(item: dict[str, Any]) -> set[str]:
    return _values_from_context(item, "contracts") | _values_from_context(item, "api_contracts")


def data_objects(item: dict[str, Any]) -> set[str]:
    return _values_from_context(item, "data_objects") | _values_from_context(item, "data_source_of_truth_objects")


def infer_theme(item: dict[str, Any]) -> str:
    text = " ".join(
        str(part).lower()
        for part in (
            spec_title(item),
            item.get("summary", ""),
            item.get("description", ""),
            " ".join(str(flag) for flag in as_list(item.get("decomposition_flags"))),
        )
    )
    scores: dict[str, int] = {}
    for theme, words in THEMES.items():
        score = sum(1 for word in words if word in text)
        if score:
            scores[theme] = score
    if not scores:
        return "general"
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))[0][0]


def seam_score(left: dict[str, Any], right: dict[str, Any]) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []

    if spec_layer(left) != spec_layer(right):
        score += 3
        reasons.append("layer changes")

    left_contracts = contracts(left)
    right_contracts = contracts(right)
    if left_contracts or right_contracts:
        if not (left_contracts & right_contracts):
            score += 2
            reasons.append("no shared contracts")

    left_data = data_objects(left)
    right_data = data_objects(right)
    if left_data or right_data:
        if not (left_data & right_data):
            score += 1
            reasons.append("no shared data objects")

    left_theme = infer_theme(left)
    right_theme = infer_theme(right)
    if left_theme != right_theme:
        score += 2
        reasons.append(f"title theme changes from {left_theme} to {right_theme}")

    left_id = spec_id(left)
    right_id = spec_id(right)
    if left_id and right_id:
        right_deps = set(depends_on(right))
        if right_deps and left_id not in right_deps:
            score += 1
            reasons.append("adjacent spec is not directly dependent on previous spec")

    return score, reasons


def _bundle_reason(items: list[dict[str, Any]]) -> str:
    if len(items) == 1:
        return "Single spec bundle: no adjacent spec can be grouped safely without weakening boundaries."
    layers = sorted({spec_layer(item) for item in items})
    themes = sorted({infer_theme(item) for item in items})
    shared_contracts = set.intersection(*(contracts(item) for item in items)) if items and all(contracts(item) for item in items) else set()
    shared_data = set.intersection(*(data_objects(item) for item in items)) if items and all(data_objects(item) for item in items) else set()

    parts = [f"Grouped because specs are adjacent in dependency order and fit safe bundle size ({len(items)} specs)."]
    if len(layers) == 1:
        parts.append(f"Primary layer: {layers[0]}.")
    if themes:
        parts.append("Themes: " + ", ".join(themes) + ".")
    if shared_contracts:
        parts.append("Shared contracts: " + ", ".join(sorted(shared_contracts)) + ".")
    if shared_data:
        parts.append("Shared data objects: " + ", ".join(sorted(shared_data)) + ".")
    return " ".join(parts)


def _bundle_name(items: list[dict[str, Any]], bundle_id: str) -> str:
    themes = [infer_theme(item) for item in items]
    dominant = "general"
    if themes:
        dominant = sorted(set(themes), key=lambda theme: (-themes.count(theme), theme))[0]
    label = dominant.replace("_", " ").title()
    return f"{label} Bundle {bundle_id[1:]}"


def default_allowed_evidence(sync: Path) -> list[str]:
    candidates = [
        sync / "hldspec_state.md",
        sync / "hld_usecase_api_map.md",
        sync / "spec_build_plan.json",
        sync / "spec_build_plan.md",
        sync / "speckit_input_manifest.json",
        sync / "speckit_invocation_queue.json",
        sync / "constitution_update_plan.json",
        sync / "feature_dependency_graph.json",
        sync / "speckit_prework_quality_review.json",
        sync / "speckit_proxy_dossier.json",
        sync / "speckit_answer_dossier.md",
    ]
    evidence = [str(path.relative_to(sync.parent.parent)) for path in candidates if path.exists()]
    return evidence or [".specify/sync/speckit_invocation_queue.json"]


def default_forbidden_reads() -> list[str]:
    return [
        "Do not perform broad repository scans.",
        "Do not read files outside the allowed evidence list.",
        "Do not inspect source or implementation files unless the bundle prompt explicitly lists them.",
        "Do not infer missing architecture decisions from unrelated files.",
        "Escalate missing evidence instead of guessing.",
    ]


def _included_specs(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    included: list[dict[str, Any]] = []
    for order, item in enumerate(items, start=1):
        included.append(
            {
                "order": item.get("order", order),
                "feature_id": spec_id(item),
                "feature_name": spec_title(item),
                "short_name": str(item.get("short_name", slugify(spec_title(item)))),
                "layer": spec_layer(item),
                "depends_on_features": depends_on(item),
                "theme": infer_theme(item),
                "source_hld_sections": [str(value) for value in as_list(item.get("source_hld_sections"))],
                "architecture_context": as_dict(item.get("architecture_context")),
                "product_context": as_dict(item.get("product_context")),
                "speckit_context": as_dict(item.get("speckit_context")),
                "speckit_specify_input": str(item.get("speckit_specify_input", "")),
            }
        )
    return included


def plan_bundles_from_items(
    items: list[dict[str, Any]],
    *,
    default_max: int = DEFAULT_MAX_BUNDLE_SIZE,
    hard_max: int = HARD_MAX_BUNDLE_SIZE,
) -> list[dict[str, Any]]:
    if not items:
        return []

    raw_groups: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = [items[0]]

    for item in items[1:]:
        score, _reasons = seam_score(current[-1], item)
        cut = False
        if len(current) >= hard_max:
            cut = True
        elif score >= 5:
            cut = True
        elif score >= 3 and len(current) >= 2:
            cut = True
        elif len(current) >= default_max and score >= 2:
            cut = True

        if cut:
            raw_groups.append(current)
            current = [item]
        else:
            current.append(item)

    raw_groups.append(current)

    bundles: list[dict[str, Any]] = []
    for idx, group in enumerate(raw_groups, start=1):
        bundle_id = f"G{idx:02d}"
        bundle_name = _bundle_name(group, bundle_id)
        bundle_slug = f"{bundle_id.lower()}-{slugify(bundle_name)}"
        included = _included_specs(group)
        dependencies = sorted(
            {
                dep
                for spec in included
                for dep in spec.get("depends_on_features", [])
                if dep and dep not in {member["feature_id"] for member in included}
            }
        )
        bundles.append(
            {
                "bundle_id": bundle_id,
                "bundle_name": bundle_name,
                "bundle_slug": bundle_slug,
                "included_specs": included,
                "why_grouped": _bundle_reason(group),
                "dependency_position": idx,
                "dependencies": dependencies,
                "allowed_evidence": [],
                "forbidden_reads": default_forbidden_reads(),
                "model_runtime_recommendation": {
                    "orchestrator": "MODEL_CRITICAL",
                    "default_subagent": "MODEL_STRONG",
                    "clarification": "MODEL_MEDIUM",
                },
                "expected_outputs": [
                    "Per-spec SpecKit outputs for specify, clarify if needed, plan, research/data/contracts if needed, tasks, and verification.",
                    "Evidence used list for every spec.",
                    "RunSkeptic PASS/ACTION/CONFLICT status at each checkpoint.",
                    "Bundle completion summary and next safe action.",
                ],
                "tests_required": [
                    "Run generated or affected unit tests for each spec when available.",
                    "Run integration or contract tests for shared contracts/data objects when available.",
                    "Run git diff --check before completion if code or generated files changed.",
                ],
                "runskeptic_checkpoints": [
                    "unclear bundle boundary",
                    "evidence contradiction",
                    "forbidden-read pressure",
                    "post-specify",
                    "post-plan",
                    "post-tasks",
                    "pre-implementation",
                    "bundle completion",
                ],
                "human_checkpoint_rules": [
                    "Ask before changing bundle boundaries, dependency order, source of truth, or constitution rules.",
                    "Ask before implementation unless explicit implementation approval exists.",
                    "Stop on unresolved RunSkeptic ACTION or CONFLICT.",
                ],
                "stop_condition": "Stop when the bundle prompt reaches a human checkpoint, missing evidence, failed validation, RunSkeptic ACTION/CONFLICT, or completed bundle verification.",
                "implementation_allowed": False,
                "human_override_required": len(group) > hard_max,
                "prompt_paths": {},
            }
        )
    return bundles


def build_bundle_queue(workspace: Path) -> dict[str, Any]:
    sync = select_sync_dir(workspace, ("speckit_invocation_queue.json", "spec_build_plan.json"))
    queue = load_json_dict(sync / "speckit_invocation_queue.json")
    items = [item for item in as_list(queue.get("items")) if isinstance(item, dict)]
    bundles = plan_bundles_from_items(items)
    evidence = default_allowed_evidence(sync)
    for bundle in bundles:
        bundle["allowed_evidence"] = evidence

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "PENDING_HUMAN_REVIEW",
        "source_queue": str(sync / "speckit_invocation_queue.json"),
        "bundle_count": len(bundles),
        "spec_count": len(items),
        "rules": [
            "Bundles are derived from speckit_invocation_queue.json and do not mutate it.",
            "Bundles preserve dependency/order from the invocation queue.",
            "Bundles stay bite-size for safe agent execution.",
            "Each bundle gets one runtime-aware SpecKit orchestration prompt.",
        ],
        "bundles": bundles,
    }


def render_bundle_queue_md(payload: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Bundle Queue",
        "",
        f"Status: `{payload.get('status', '')}`",
        f"Spec count: `{payload.get('spec_count', 0)}`",
        f"Bundle count: `{payload.get('bundle_count', 0)}`",
        "",
        "## Rules",
        "",
    ]
    for rule in as_list(payload.get("rules")):
        lines.append(f"- {rule}")
    lines += [
        "",
        "## Bundles",
        "",
        "| Bundle | Specs | Why grouped | Dependencies | Prompt paths |",
        "|---|---:|---|---|---|",
    ]
    for bundle in as_list(payload.get("bundles")):
        if not isinstance(bundle, dict):
            continue
        prompt_paths = as_dict(bundle.get("prompt_paths"))
        prompt_text = "<br>".join(f"`{env}`: `{path}`" for env, path in sorted(prompt_paths.items())) or "pending"
        deps = ", ".join(str(dep) for dep in as_list(bundle.get("dependencies"))) or "none"
        lines.append(
            f"| `{bundle.get('bundle_id', '')}` {bundle.get('bundle_name', '')} | "
            f"{len(as_list(bundle.get('included_specs')))} | "
            f"{bundle.get('why_grouped', '')} | {deps} | {prompt_text} |"
        )
    return "\n".join(lines) + "\n"


def write_bundle_queue(workspace: Path) -> dict[str, Any]:
    sync = select_sync_dir(workspace, ("speckit_invocation_queue.json", "spec_build_plan.json"))
    payload = build_bundle_queue(workspace)
    write_json_dict(sync / "speckit_bundle_queue.json", payload)
    (sync / "speckit_bundle_queue.md").write_text(render_bundle_queue_md(payload), encoding="utf-8")
    return payload
