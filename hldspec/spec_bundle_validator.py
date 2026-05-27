from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict
from hldspec.spec_bundle_prompts import validate_prompt_text
from hldspec.spec_bundles import HARD_MAX_BUNDLE_SIZE, as_dict, as_list, spec_id, utc_now

REQUIRED_BUNDLE_FIELDS: tuple[str, ...] = (
    "bundle_id",
    "bundle_name",
    "bundle_slug",
    "included_specs",
    "why_grouped",
    "dependency_position",
    "dependencies",
    "allowed_evidence",
    "forbidden_reads",
    "model_runtime_recommendation",
    "expected_outputs",
    "tests_required",
    "runskeptic_checkpoints",
    "human_checkpoint_rules",
    "stop_condition",
    "implementation_allowed",
    "prompt_paths",
)


@dataclass(frozen=True)
class BundleValidationFinding:
    severity: str
    check: str
    path: str
    message: str


def _finding(check: str, path: str, message: str, severity: str = "ACTION") -> BundleValidationFinding:
    return BundleValidationFinding(severity=severity, check=check, path=path, message=message)


def validate_bundle_queue(queue: dict[str, Any], invocation_queue: dict[str, Any] | None = None, *, workspace: Path | None = None) -> list[BundleValidationFinding]:
    findings: list[BundleValidationFinding] = []
    bundles = [bundle for bundle in as_list(queue.get("bundles")) if isinstance(bundle, dict)]

    if not bundles and as_list(as_dict(invocation_queue or {}).get("items")):
        findings.append(_finding("bundle_count", "speckit_bundle_queue.json", "invocation queue has items but bundle queue is empty"))

    expected_ids = [spec_id(item) for item in as_list(as_dict(invocation_queue or {}).get("items")) if isinstance(item, dict)]
    actual_ids: list[str] = []

    for bundle_index, bundle in enumerate(bundles, start=1):
        bundle_path = f"bundle[{bundle_index}]"
        for field in REQUIRED_BUNDLE_FIELDS:
            if field not in bundle:
                findings.append(_finding("bundle_schema", bundle_path, f"missing required field: {field}"))

        included = [spec for spec in as_list(bundle.get("included_specs")) if isinstance(spec, dict)]
        actual_ids.extend(str(spec.get("feature_id", "")) for spec in included if str(spec.get("feature_id", "")))

        if len(included) > HARD_MAX_BUNDLE_SIZE and not bundle.get("human_override_required"):
            findings.append(_finding("bundle_size", bundle_path, f"bundle exceeds hard max size {HARD_MAX_BUNDLE_SIZE} without human override"))

        if len(included) > 3 and not str(bundle.get("why_grouped", "")).strip():
            findings.append(_finding("why_grouped", bundle_path, "bundle above default size requires why_grouped"))

        for field in ("allowed_evidence", "forbidden_reads", "expected_outputs", "tests_required", "runskeptic_checkpoints", "human_checkpoint_rules"):
            if not as_list(bundle.get(field)):
                findings.append(_finding(field, bundle_path, f"{field} must be non-empty"))

        if not str(bundle.get("stop_condition", "")).strip():
            findings.append(_finding("stop_condition", bundle_path, "stop_condition must be non-empty"))

        deps = set(str(dep) for dep in as_list(bundle.get("dependencies")))
        bundle_spec_ids = {str(spec.get("feature_id", "")) for spec in included}
        prior_ids = set(actual_ids) - bundle_spec_ids
        for dep in deps:
            if expected_ids and dep in expected_ids and dep not in prior_ids and dep not in bundle_spec_ids:
                findings.append(_finding("forward_dependency", bundle_path, f"dependency points forward or outside prior bundles: {dep}"))

        prompt_paths = as_dict(bundle.get("prompt_paths"))
        if workspace is not None and prompt_paths:
            for runtime, relpath in prompt_paths.items():
                prompt_path = workspace / str(relpath)
                if not prompt_path.exists():
                    findings.append(_finding("prompt_path", str(prompt_path), f"missing generated prompt for runtime {runtime}"))
                    continue
                for error in validate_prompt_text(prompt_path.read_text(encoding="utf-8")):
                    findings.append(_finding("prompt_content", str(prompt_path), error))

    if expected_ids:
        if actual_ids != expected_ids:
            findings.append(
                _finding(
                    "bundle_order",
                    "speckit_bundle_queue.json",
                    f"bundle spec order must match invocation order exactly; expected {expected_ids}, got {actual_ids}",
                )
            )
        duplicates = sorted({item for item in actual_ids if actual_ids.count(item) > 1})
        if duplicates:
            findings.append(_finding("duplicate_spec", "speckit_bundle_queue.json", "duplicate specs: " + ", ".join(duplicates)))
        missing = [item for item in expected_ids if item not in actual_ids]
        if missing:
            findings.append(_finding("missing_spec", "speckit_bundle_queue.json", "missing specs: " + ", ".join(missing)))

    return findings


def render_validation_md(report: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Bundle Validation",
        "",
        f"Status: `{report.get('status', '')}`",
        f"Generated at: `{report.get('generated_at', '')}`",
        "",
        "## Findings",
        "",
    ]
    findings = as_list(report.get("findings"))
    if not findings:
        lines.append("No ACTION or CONFLICT findings.")
    for item in findings:
        if isinstance(item, dict):
            lines.append(f"- `{item.get('severity', '')}` `{item.get('check', '')}` `{item.get('path', '')}` - {item.get('message', '')}")
    return "\n".join(lines) + "\n"


def validate_workspace_bundles(workspace: Path) -> dict[str, Any]:
    sync = select_sync_dir(workspace, ("speckit_bundle_queue.json", "speckit_invocation_queue.json"))
    queue = load_json_dict(sync / "speckit_bundle_queue.json")
    invocation_queue = load_json_dict(sync / "speckit_invocation_queue.json")
    findings = validate_bundle_queue(queue, invocation_queue, workspace=workspace)
    status = "PASS" if not findings else ("CONFLICT" if any(item.severity == "CONFLICT" for item in findings) else "ACTION")
    report = {
        "schema_version": 1,
        "generated_at": utc_now(),
        "status": status,
        "findings": [asdict(item) for item in findings],
    }
    validation_dir = sync / "validation"
    write_json_dict(validation_dir / "speckit_bundle_validation.json", report)
    (validation_dir / "speckit_bundle_validation.md").write_text(render_validation_md(report), encoding="utf-8")
    return report
