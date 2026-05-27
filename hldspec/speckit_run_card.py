from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
REQUIRED_JSON_FIELDS = (
    "schema_version",
    "package_id",
    "package_name",
    "phase",
    "dependency_position",
    "allowed_evidence",
    "forbidden_actions",
    "required_checkpoints",
    "runskeptic_checkpoints",
    "subagents",
    "stop_conditions",
    "expected_outputs",
    "report_contract",
    "reassessment_triggers",
)
REQUIRED_MD_SECTIONS = (
    "# SpecKit Run Card",
    "## Mission",
    "## Active Package",
    "## Current Phase",
    "## Dependency Position",
    "## Requires",
    "## Ensures",
    "## Approved Evidence",
    "## Forbidden Actions",
    "## Required SpecKit Sequence",
    "## Question Answering Policy",
    "## Required Subagents / Reviewers",
    "## RunSkeptic Checkpoints",
    "## How to run RunSkeptic",
    "## Human Approval Boundaries",
    "## Stop Conditions",
    "## Expected Outputs",
    "## Test Requirements",
    "## Report Back Format",
    "## Reassessment Triggers",
    "## Next Safe Action",
)
DEFAULT_PHASE = "specify"
DEFAULT_REPORT_CONTRACT = (
    "Phase run",
    "Files read",
    "Files changed",
    "Questions asked",
    "Questions answered from evidence",
    "Questions answered from approved defaults",
    "Questions escalated",
    "RunSkeptic status",
    "Tests run",
    "Failures",
    "Scope changes",
    "Reassessment triggers",
    "Next safe action",
    "Should HLDspec reassess? yes/no",
)
DEFAULT_REASSESSMENT_TRIGGERS = (
    "HLD changed",
    "generated prompt changed",
    "SpecKit output changed",
    "dependency graph changed",
    "invocation queue stale",
    "implementation changed files outside approved scope",
    "RunSkeptic ACTION or CONFLICT",
    "human-owned question appears",
    "tests fail",
    "architecture/product/governance assumption changes",
)
DEFAULT_STOP_CONDITIONS = (
    "required evidence is missing",
    "package order conflicts with dependency graph",
    "SpecKit asks a human-owned question",
    "RunSkeptic returns ACTION or CONFLICT",
    "tests fail",
    "implementation approval is missing",
    "existing code contradicts the HLD/spec package",
    "package scope expands beyond approved boundaries",
    "the agent needs to read outside allowed evidence",
    "the next action cannot be proven safe",
)
DEFAULT_SPEC_SEQUENCE = (
    "Constitution update if required and approved.",
    "/speckit.specify",
    "/speckit.clarify if questions exist.",
    "/speckit.plan",
    "/speckit.tasks",
    "/speckit.analyze if required.",
    "Implement only after explicit implementation approval.",
)
DEFAULT_RUNSKEPTIC_CHECKPOINTS = (
    "RunSkeptic before SpecKit starts",
    "RunSkeptic after specify",
    "RunSkeptic after plan",
    "RunSkeptic before tasks",
    "RunSkeptic before implementation",
    "RunSkeptic after implementation or completion report",
)
DEFAULT_REQUIRED_CHECKPOINTS = (
    "approved prework exists",
    "dependency graph and invocation queue are present",
    "allowed evidence exists",
    "RunSkeptic status has no unresolved ACTION or CONFLICT",
    "human approval gate is satisfied",
)
DEFAULT_SUBAGENTS = (
    "Architecture Reviewer when component boundaries, interfaces, dependencies, data ownership, or source of truth may change.",
    "Product Reviewer when scope, user/system behavior, feature boundary, or acceptance readiness is unclear.",
    "Governance Reviewer when approval status, constitution impact, or implementation permission is unclear.",
    "RunSkeptic Reviewer at every listed RunSkeptic checkpoint.",
)
DEFAULT_FORBIDDEN_ACTIONS = (
    "Do not modify the source HLD.",
    "Do not read outside the approved evidence list.",
    "Do not change dependency order.",
    "Do not answer human-owned architecture, source-of-truth, security, data ownership, feature split, or implementation approval decisions.",
    "Do not skip SpecKit phases.",
    "Do not implement before explicit implementation approval.",
    "Do not continue past unresolved ACTION or CONFLICT.",
    "Do not convert context-only material into specs.",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def load_json_dict(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json_dict(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _slug(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in cleaned:
        cleaned = cleaned.replace("--", "-")
    return cleaned.strip("-") or "run-card"


def _first_str(*values: Any, default: str = "") -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list, tuple, set)):
            text = str(value).strip()
            if text:
                return text
    return default


def _str_list(values: Any, fallback: tuple[str, ...] = ()) -> list[str]:
    out = [str(value) for value in as_list(values) if str(value).strip()]
    return out or list(fallback)


def select_control_dir(workspace: Path) -> Path:
    """Select the HLDspec control directory, preferring canonical target/.hldspec/sync."""
    canonical = workspace / ".hldspec" / "sync"
    legacy = workspace / ".specify" / "sync"
    markers = (
        "speckit_bundle_queue.json",
        "speckit_invocation_queue.json",
        "speckit_prework_approval.json",
        "speckit_prework_approval_decision.json",
    )
    if canonical.exists() or any((canonical / marker).exists() for marker in markers):
        canonical.mkdir(parents=True, exist_ok=True)
        return canonical
    if any((legacy / marker).exists() for marker in markers):
        return legacy
    canonical.mkdir(parents=True, exist_ok=True)
    return canonical


def approval_record(sync: Path) -> dict[str, Any]:
    for name in ("speckit_prework_approval.json", "speckit_prework_approval_decision.json"):
        record = load_json_dict(sync / name)
        if record:
            return record
    return {}


def is_approved(record: dict[str, Any]) -> bool:
    return str(record.get("status", "")).upper() == "APPROVED"


def load_bundle_queue(sync: Path) -> dict[str, Any]:
    for name in ("speckit_bundle_queue.json", "speckit_invocation_queue.json"):
        payload = load_json_dict(sync / name)
        if payload:
            return payload
    return {}


def bundles_from_queue(queue: dict[str, Any]) -> list[dict[str, Any]]:
    if isinstance(queue.get("bundles"), list):
        return [bundle for bundle in queue["bundles"] if isinstance(bundle, dict)]
    items = [item for item in as_list(queue.get("items")) if isinstance(item, dict)]
    bundles: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        feature_id = _first_str(item.get("feature_id"), item.get("spec_id"), item.get("id"), default=f"P{index:03d}")
        feature_name = _first_str(item.get("feature_name"), item.get("name"), item.get("title"), default=feature_id)
        bundles.append(
            {
                "bundle_id": feature_id,
                "bundle_name": feature_name,
                "bundle_slug": f"{feature_id.lower()}-{_slug(feature_name)}",
                "dependency_position": item.get("order", index),
                "dependencies": as_list(item.get("depends_on_features")) or as_list(item.get("depends_on")),
                "included_specs": [item],
                "allowed_evidence": as_list(item.get("allowed_evidence")),
                "runskeptic_checkpoints": as_list(item.get("runskeptic_checkpoints")),
                "expected_outputs": as_list(item.get("expected_outputs")),
                "tests_required": as_list(item.get("tests_required")),
                "human_checkpoint_rules": as_list(item.get("human_checkpoint_rules")),
            }
        )
    return bundles


@dataclass(frozen=True)
class RunCardPaths:
    package_id: str
    package_dir: Path
    json_path: Path
    markdown_path: Path


def _package_id(bundle: dict[str, Any]) -> str:
    return _first_str(bundle.get("bundle_id"), bundle.get("package_id"), bundle.get("feature_id"), default="package")


def _package_name(bundle: dict[str, Any]) -> str:
    return _first_str(bundle.get("bundle_name"), bundle.get("package_name"), bundle.get("feature_name"), default=_package_id(bundle))


def _package_slug(bundle: dict[str, Any]) -> str:
    return _first_str(bundle.get("bundle_slug"), default=f"{_package_id(bundle).lower()}-{_slug(_package_name(bundle))}")


def build_run_card_payload(
    bundle: dict[str, Any],
    *,
    workspace: Path,
    sync: Path,
    approved: bool,
    preview: bool = False,
) -> dict[str, Any]:
    package_id = _package_id(bundle)
    package_name = _package_name(bundle)
    allowed_evidence = _str_list(
        bundle.get("allowed_evidence"),
        fallback=(
            str((sync / "speckit_invocation_queue.json").relative_to(workspace)) if (sync / "speckit_invocation_queue.json").exists() else "target/.hldspec/sync/speckit_invocation_queue.json",
            str((sync / "feature_dependency_graph.json").relative_to(workspace)) if (sync / "feature_dependency_graph.json").exists() else "target/.hldspec/sync/feature_dependency_graph.json",
            str((sync / "speckit_prework_quality_review.json").relative_to(workspace)) if (sync / "speckit_prework_quality_review.json").exists() else "target/.hldspec/sync/speckit_prework_quality_review.json",
        ),
    )
    status = "APPROVED" if approved else "PREVIEW"
    phase = _first_str(bundle.get("phase"), default=DEFAULT_PHASE)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": status,
        "preview": bool(preview),
        "package_id": package_id,
        "package_name": package_name,
        "package_slug": _package_slug(bundle),
        "phase": phase,
        "dependency_position": _first_str(bundle.get("dependency_position"), default="unknown"),
        "dependencies": _str_list(bundle.get("dependencies")),
        "included_specs": as_list(bundle.get("included_specs")),
        "allowed_evidence": allowed_evidence,
        "forbidden_actions": _str_list(bundle.get("forbidden_actions"), DEFAULT_FORBIDDEN_ACTIONS),
        "required_checkpoints": _str_list(bundle.get("required_checkpoints"), DEFAULT_REQUIRED_CHECKPOINTS),
        "runskeptic_checkpoints": _str_list(bundle.get("runskeptic_checkpoints"), DEFAULT_RUNSKEPTIC_CHECKPOINTS),
        "subagents": _str_list(bundle.get("subagents"), DEFAULT_SUBAGENTS),
        "stop_conditions": _str_list(bundle.get("stop_conditions"), DEFAULT_STOP_CONDITIONS),
        "expected_outputs": _str_list(
            bundle.get("expected_outputs"),
            fallback=(
                "SpecKit phase output for the active package.",
                "Evidence-used list.",
                "RunSkeptic PASS/ACTION/CONFLICT status.",
                "Report-back record with next safe action.",
            ),
        ),
        "tests_required": _str_list(bundle.get("tests_required"), fallback=("Run generated or affected tests when available.", "Run git diff --check if files changed.")),
        "report_contract": _str_list(bundle.get("report_contract"), DEFAULT_REPORT_CONTRACT),
        "reassessment_triggers": _str_list(bundle.get("reassessment_triggers"), DEFAULT_REASSESSMENT_TRIGGERS),
        "requires": [
            "approved SpecKit prework" if approved else "preview mode explicitly enabled; not approved for execution",
            "dependency graph and invocation queue",
            "bounded approved evidence",
            "RunSkeptic status with no unresolved ACTION or CONFLICT",
        ],
        "ensures": [
            "one bounded SpecKit execution handoff",
            "explicit stop conditions",
            "explicit report-back format",
            "explicit reassessment triggers for HLDspec",
        ],
        "next_safe_action": "Give this Run Card to the external build/SpecKit agent only for the active package and phase; stop and return to HLDspec on any stop condition.",
    }
    return payload


def validate_run_card_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in REQUIRED_JSON_FIELDS:
        if field not in payload:
            errors.append(f"missing required field: {field}")
    for field in (
        "allowed_evidence",
        "forbidden_actions",
        "required_checkpoints",
        "runskeptic_checkpoints",
        "subagents",
        "stop_conditions",
        "expected_outputs",
        "report_contract",
        "reassessment_triggers",
    ):
        if field in payload and not as_list(payload.get(field)):
            errors.append(f"field must be a non-empty list: {field}")
    if payload.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not _first_str(payload.get("package_id")):
        errors.append("package_id is required")
    if str(payload.get("status", "")).upper() not in {"APPROVED", "PREVIEW"}:
        errors.append("status must be APPROVED or PREVIEW")
    return errors


def _bullet(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def _numbered(items: list[str]) -> list[str]:
    return [f"{idx}. {item}" for idx, item in enumerate(items, start=1)] if items else ["1. none"]




def runskeptic_operating_block(skeptic_path: str = "~/code/skeptic/skeptic.md") -> list[str]:
    return [
        "RunSkeptic is the required quality gate for this step.",
        "",
        "First, read the actual current framework file:",
        "",
        f"`{skeptic_path}`",
        "",
        "Do not rely on memory or a summary if the file is available.",
        "",
        "Apply this flow in order:",
        "",
        "`GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`",
        "",
        "For this Run Card, RunSkeptic is normally read-only unless this card explicitly authorizes a fix.",
        "",
        "Use only these result statuses:",
        "",
        "- `PASS`: no blocking finding is known; evidence is sufficient for this step.",
        "- `ACTION`: a fixable issue exists, such as missing evidence, stale artifact, invalid output, incomplete contract, weak testability, or unclear prompt/report content.",
        "- `CONFLICT`: a human-owned or architecture/product/source-of-truth decision is unresolved, or multiple valid designs exist and the evidence does not choose between them.",
        "",
        "Minimum checks:",
        "",
        "1. Gate: confirm the requested step is clear, bounded, and testable.",
        "2. Fundamental scan: check purpose, boundaries, ownership, source of truth, main flow, interfaces, dependencies, and high-risk assumptions.",
        "3. Map: list findings before deciding. Do not fix while mapping.",
        "4. Confidence: identify unknowns, skipped areas, and weak evidence.",
        "5. Stabilize: merge related findings and identify root cause.",
        "6. Evidence: mark each finding as `OBSERVED`, `REPRODUCED`, `HISTORICAL`, or `INFERRED RISK`.",
        "7. Decide: choose `PASS`, `ACTION`, or `CONFLICT`; do not promote if any ACTION or CONFLICT remains.",
        "8. Verify: if a fix was explicitly authorized, report the exact tests or checks run; otherwise report what verification would be required.",
        "",
        "Required RunSkeptic output:",
        "",
        "- `RunSkeptic status: PASS | ACTION | CONFLICT`",
        "- `Scope reviewed:`",
        "- `Evidence used:`",
        "- `Findings:`",
        "- `Unknowns:`",
        "- `Human decisions needed:`",
        "- `Verification performed:`",
        "- `Next safe action:`",
        "",
        "Stop immediately if RunSkeptic returns ACTION or CONFLICT, required evidence is missing, a human-owned decision appears, or the step would require reading outside approved evidence.",
        "",
        "If the framework file is unavailable, do not claim full RunSkeptic compliance. Use this embedded fallback and report: `RunSkeptic source: embedded fallback`; `Confidence: lower than full framework review`; `Missing evidence: actual skeptic.md was unavailable`.",
    ]

def render_run_card_md(payload: dict[str, Any]) -> str:
    errors = validate_run_card_payload(payload)
    if errors:
        raise ValueError("invalid run card payload: " + "; ".join(errors))
    lines = [
        "# SpecKit Run Card",
        "",
        f"Package: `{payload.get('package_id')}` — {payload.get('package_name')}",
        f"Status: `{payload.get('status')}`",
        f"Preview: `{payload.get('preview')}`",
        "",
        "## Mission",
        "",
        "Execute only this bounded SpecKit handoff. Use only approved evidence, enforce every checkpoint, and return to HLDspec at any stop condition or reassessment trigger.",
        "",
        "## Active Package",
        "",
        f"- package id: `{payload.get('package_id')}`",
        f"- package name: `{payload.get('package_name')}`",
        f"- package slug: `{payload.get('package_slug', '')}`",
        "",
        "## Current Phase",
        "",
        f"- `{payload.get('phase')}`",
        "",
        "## Dependency Position",
        "",
        f"- position: `{payload.get('dependency_position')}`",
        "- dependencies:",
        *_bullet([str(dep) for dep in as_list(payload.get("dependencies"))]),
        "",
        "## Requires",
        "",
        *_bullet([str(item) for item in as_list(payload.get("requires"))]),
        "",
        "## Ensures",
        "",
        *_bullet([str(item) for item in as_list(payload.get("ensures"))]),
        "",
        "## Approved Evidence",
        "",
        *_bullet([f"`{item}`" for item in as_list(payload.get("allowed_evidence"))]),
        "",
        "## Forbidden Actions",
        "",
        *_bullet([str(item) for item in as_list(payload.get("forbidden_actions"))]),
        "",
        "## Required SpecKit Sequence",
        "",
        *_numbered(list(DEFAULT_SPEC_SEQUENCE)),
        "",
        "## Question Answering Policy",
        "",
        "- **ANSWER_FROM_EVIDENCE**: directly supported by approved HLDspec artifacts.",
        "- **ANSWER_FROM_APPROVED_DEFAULT**: only safe, reversible defaults outside human-owned decision areas.",
        "- **ESCALATE_TO_HUMAN**: required for architecture, source of truth, constitution, API contract, security/privacy, data ownership, user-visible scope, dependency order, feature split/merge, or implementation approval.",
        "",
        "## Required Subagents / Reviewers",
        "",
        *_bullet([str(item) for item in as_list(payload.get("subagents"))]),
        "",
        "## RunSkeptic Checkpoints",
        "",
        *_bullet([str(item) for item in as_list(payload.get("runskeptic_checkpoints"))]),
        "",
        "Use only these statuses: `PASS`, `ACTION`, `CONFLICT`. Stop on unresolved `ACTION` or `CONFLICT`.",
        "",
        "## How to run RunSkeptic",
        "",
        *runskeptic_operating_block(),
        "",
        "## Human Approval Boundaries",
        "",
        "- Stop for architecture boundary, source-of-truth, constitution, API contract, security/privacy, data ownership, user-visible scope, dependency order, feature split/merge, and implementation approval decisions.",
        "- Implementation remains blocked unless explicit implementation approval exists.",
        "",
        "## Stop Conditions",
        "",
        *_bullet([str(item) for item in as_list(payload.get("stop_conditions"))]),
        "",
        "## Expected Outputs",
        "",
        *_bullet([str(item) for item in as_list(payload.get("expected_outputs"))]),
        "",
        "## Test Requirements",
        "",
        *_bullet([str(item) for item in as_list(payload.get("tests_required"))]),
        "",
        "## Report Back Format",
        "",
        *_bullet([str(item) for item in as_list(payload.get("report_contract"))]),
        "",
        "## Reassessment Triggers",
        "",
        *_bullet([str(item) for item in as_list(payload.get("reassessment_triggers"))]),
        "",
        "## Next Safe Action",
        "",
        str(payload.get("next_safe_action", "")),
        "",
    ]
    return "\n".join(lines)


def run_card_paths(workspace: Path, bundle: dict[str, Any]) -> RunCardPaths:
    package_id = _package_id(bundle)
    package_dir = workspace / "prompts" / "speckit" / _package_slug(bundle)
    return RunCardPaths(
        package_id=package_id,
        package_dir=package_dir,
        json_path=package_dir / "RUN_CARD.json",
        markdown_path=package_dir / "RUN_CARD.md",
    )


def render_index_md(index: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Run Cards",
        "",
        f"Status: `{index.get('status', '')}`",
        f"Run card count: `{index.get('run_card_count', 0)}`",
        "",
        "| Package | Status | Phase | Run Card |",
        "|---|---|---|---|",
    ]
    for card in as_list(index.get("run_cards")):
        if not isinstance(card, dict):
            continue
        lines.append(
            f"| `{card.get('package_id', '')}` {card.get('package_name', '')} | "
            f"`{card.get('status', '')}` | `{card.get('phase', '')}` | "
            f"`{card.get('markdown_path', '')}` |"
        )
    lines.append("")
    return "\n".join(lines)


def write_run_cards(workspace: Path, *, allow_unapproved_preview: bool = False) -> dict[str, Any]:
    workspace = workspace.resolve()
    sync = select_control_dir(workspace)
    approval = approval_record(sync)
    approved = is_approved(approval)
    if not approved and not allow_unapproved_preview:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "ACTION",
            "reason": "speckit_prework_approval.json status APPROVED is required before generating executable Run Cards",
            "sync_dir": str(sync),
            "required_action": "Record approved prework or rerun with --allow-unapproved-preview for a non-executable preview.",
        }

    queue = load_bundle_queue(sync)
    bundles = bundles_from_queue(queue)
    if not bundles:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "ACTION",
            "reason": "no bundles or invocation queue items found",
            "sync_dir": str(sync),
            "required_action": "Generate speckit_bundle_queue.json or speckit_invocation_queue.json first.",
        }

    output_root = workspace / "prompts" / "speckit"
    output_root.mkdir(parents=True, exist_ok=True)
    # Remove only generated run-card files under the canonical prompt root; keep other phase prompts intact.
    for old in output_root.glob("*/RUN_CARD.*"):
        old.unlink()
    for old in (output_root / "RUN_CARDS.json", output_root / "RUN_CARDS.md", output_root / "current_RUN_CARD.json", output_root / "current_RUN_CARD.md"):
        if old.exists():
            old.unlink()

    run_cards: list[dict[str, Any]] = []
    for bundle in bundles:
        payload = build_run_card_payload(bundle, workspace=workspace, sync=sync, approved=approved, preview=not approved)
        errors = validate_run_card_payload(payload)
        if errors:
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "ACTION",
                "reason": "invalid run card payload",
                "package_id": payload.get("package_id"),
                "errors": errors,
            }
        paths = run_card_paths(workspace, bundle)
        write_json_dict(paths.json_path, payload)
        paths.markdown_path.write_text(render_run_card_md(payload), encoding="utf-8")
        run_cards.append(
            {
                "package_id": payload["package_id"],
                "package_name": payload["package_name"],
                "phase": payload["phase"],
                "status": payload["status"],
                "json_path": str(paths.json_path.relative_to(workspace)),
                "markdown_path": str(paths.markdown_path.relative_to(workspace)),
            }
        )

    index = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "status": "PREVIEW" if not approved else "READY_FOR_EXECUTION_HANDOFF",
        "sync_dir": str(sync),
        "run_card_count": len(run_cards),
        "run_cards": run_cards,
    }
    write_json_dict(output_root / "RUN_CARDS.json", index)
    (output_root / "RUN_CARDS.md").write_text(render_index_md(index), encoding="utf-8")
    if run_cards:
        first = run_cards[0]
        first_json = workspace / first["json_path"]
        first_md = workspace / first["markdown_path"]
        shutil.copyfile(first_json, output_root / "current_RUN_CARD.json")
        shutil.copyfile(first_md, output_root / "current_RUN_CARD.md")
    return index
