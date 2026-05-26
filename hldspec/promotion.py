"""Promotion status and target readiness gates."""
from __future__ import annotations
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class PromotionStatus(str, Enum):
    PROPOSED         = "PROPOSED"          # Artifact exists but not yet reviewed
    REVIEW_REQUIRED  = "REVIEW_REQUIRED"   # Needs human or gate review before use
    REWORK_REQUIRED  = "REWORK_REQUIRED"   # Gate failed; must be rebuilt
    APPROVAL_READY   = "APPROVAL_READY"    # Gate passed; awaiting human approval
    APPROVED         = "APPROVED"          # Human approved; may proceed
    BLOCKED          = "BLOCKED"           # Cannot proceed; dependency or gate failure
    STALE            = "STALE"             # Inputs changed after this artifact was produced
    SUPERSEDED       = "SUPERSEDED"        # Replaced by a newer version

    @classmethod
    def terminal_states(cls) -> frozenset["PromotionStatus"]:
        return frozenset({cls.APPROVED, cls.SUPERSEDED})

    @classmethod
    def blocking_states(cls) -> frozenset["PromotionStatus"]:
        return frozenset({cls.REWORK_REQUIRED, cls.BLOCKED, cls.STALE})

    def can_promote_to_approved(self) -> bool:
        return self == PromotionStatus.APPROVAL_READY

    def is_blocking(self) -> bool:
        return self in self.blocking_states()


class DeprecationStatus(str, Enum):
    ACTIVE             = "ACTIVE"            # In use; maintained
    COMPATIBILITY_ONLY = "COMPATIBILITY_ONLY"# Kept for backward compat; no new uses
    DEPRECATED         = "DEPRECATED"        # Will be removed; migration required
    ARCHIVED           = "ARCHIVED"          # Moved to archive; not in active flow
    REMOVED            = "REMOVED"           # Deleted; references are errors

    def is_active_control_signal(self) -> bool:
        """Return True if this status allows a term/artifact to control active flow."""
        return self == DeprecationStatus.ACTIVE

    @classmethod
    def legacy_states(cls) -> frozenset["DeprecationStatus"]:
        return frozenset({cls.COMPATIBILITY_ONLY, cls.DEPRECATED, cls.ARCHIVED, cls.REMOVED})


PROMOTION_GATE_SCHEMA_VERSION = "1.0"
BLOCKING_STATUSES = {"ACTION", "CONFLICT"}


@dataclass(frozen=True)
class PromotionGateFinding:
    severity: str
    check: str
    path: str
    message: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(target: Path, severity: str, check: str, path: Path, message: str) -> PromotionGateFinding:
    return PromotionGateFinding(severity=severity, check=check, path=relpath(path, target), message=message)


def _status_from_findings(findings: list[PromotionGateFinding]) -> str:
    if any(item.severity == "CONFLICT" for item in findings):
        return "CONFLICT"
    if findings:
        return "ACTION"
    return "PASS"


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# HLDspec Promotion Gate",
        "",
        f"Status: `{report['status']}`",
        f"Target: `{report['target']}`",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Inputs Read",
        "",
    ]
    inputs = report.get("inputs_read", [])
    if inputs:
        lines.extend(f"- `{item}`" for item in inputs)
    else:
        lines.append("- none")
    lines.extend(["", "## Findings", ""])
    findings = report["findings"]
    if not findings:
        lines.append("No ACTION or CONFLICT findings.")
    else:
        for item in findings:
            lines.append(f"- `{item['severity']}` `{item['check']}` `{item['path']}` - {item['message']}")
    return "\n".join(lines) + "\n"


def _read_optional_json(target: Path, path: Path, findings: list[PromotionGateFinding], inputs_read: list[str]) -> Any:
    if not path.exists():
        return None
    inputs_read.append(relpath(path, target))
    try:
        return read_json(path)
    except Exception as exc:
        findings.append(_finding(target, "ACTION", "json_parse", path, f"invalid JSON: {exc}"))
        return None


def _read_events(target: Path, path: Path, findings: list[PromotionGateFinding], inputs_read: list[str]) -> None:
    if not path.exists():
        return
    inputs_read.append(relpath(path, target))
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        findings.append(_finding(target, "ACTION", "events", path, f"cannot read events: {exc}"))
        return
    for idx, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception as exc:
            findings.append(_finding(target, "ACTION", "events", path, f"invalid JSON on line {idx}: {exc}"))
            continue
        text = json.dumps(event, sort_keys=True).lower()
        if "stop_checkpoint" in text or "unresolved" in text:
            findings.append(_finding(target, "CONFLICT", "unresolved_human_checkpoint", path, f"event line {idx} indicates an unresolved checkpoint"))


def _check_validation_reports(target: Path, validation_dir: Path, findings: list[PromotionGateFinding], inputs_read: list[str]) -> None:
    if not validation_dir.exists():
        return
    for path in sorted(validation_dir.glob("*.json")):
        if path.name == "promotion_gate.json":
            continue
        data = _read_optional_json(target, path, findings, inputs_read)
        if not isinstance(data, dict):
            continue
        status = str(data.get("status", "")).upper()
        if status in BLOCKING_STATUSES:
            findings.append(_finding(target, status, "validator_report", path, f"validator report status is {status}"))
        raw_findings = data.get("findings")
        if isinstance(raw_findings, list):
            for item in raw_findings:
                if not isinstance(item, dict):
                    continue
                severity = str(item.get("severity", "")).upper()
                if severity in BLOCKING_STATUSES:
                    findings.append(
                        _finding(
                            target,
                            severity,
                            "validator_finding",
                            path,
                            f"{item.get('check', 'unknown')}: {item.get('message', 'blocking validator finding')}",
                        )
                    )


def _check_context_prompt_validation_presence(target: Path, findings: list[PromotionGateFinding]) -> None:
    prompt_root = target / "prompts" / "speckit"
    prompts = sorted(prompt_root.glob("*/*.md")) if prompt_root.exists() else []
    context_report = target / ".hldspec" / "validation" / "context_prompt_validation.json"
    if prompts and not context_report.exists():
        findings.append(
            _finding(
                target,
                "ACTION",
                "context_prompt_validation",
                context_report,
                "generated SpecKit prompts exist but context prompt validation report is missing",
            )
        )


def _check_implementation_prompt_guard(target: Path, findings: list[PromotionGateFinding]) -> None:
    prompt_root = target / "prompts" / "speckit"
    prompts = sorted(prompt_root.glob("*/06-implement.md")) if prompt_root.exists() else []
    for prompt in prompts:
        text = prompt.read_text(encoding="utf-8").lower()
        if "human approval" not in text or "approved" not in text:
            findings.append(
                _finding(
                    target,
                    "ACTION",
                    "implementation_approval_guard",
                    prompt,
                    "implementation-phase prompt does not require explicit human approval",
                )
            )


def _is_unresolved_checkpoint(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    checkpoint = data.get("human_checkpoint")
    if isinstance(checkpoint, dict):
        decision = str(checkpoint.get("human_decision", checkpoint.get("decision", "TBD"))).strip().upper()
        if decision in {"", "TBD", "UNKNOWN", "PENDING", "UNRESOLVED"}:
            return True
    checkpoint = data.get("checkpoint")
    if isinstance(checkpoint, dict):
        open_questions = checkpoint.get("open_question_count")
        if isinstance(open_questions, int) and open_questions > 0:
            return True
        if checkpoint.get("allowed_to_convert") is False or checkpoint.get("allowed_to_generate_target_specs") is False:
            return True
    status = str(data.get("status", "")).strip().upper()
    return status in {"STOP_CHECKPOINT", "PENDING_HUMAN_REVIEW", "UNRESOLVED"}


def _check_human_checkpoints(target: Path, findings: list[PromotionGateFinding], inputs_read: list[str]) -> None:
    hldspec_dir = target / ".hldspec"
    if not hldspec_dir.exists():
        return
    for path in sorted(hldspec_dir.rglob("*.json")):
        if "/validation/" in str(path):
            continue
        try:
            data = read_json(path)
        except Exception:
            continue
        if _is_unresolved_checkpoint(data):
            inputs_read.append(relpath(path, target))
            findings.append(_finding(target, "CONFLICT", "unresolved_human_checkpoint", path, "unresolved human checkpoint blocks promotion"))


def _extract_mark(data: dict[str, Any]) -> int | None:
    for key in ("readiness_mark", "overall_mark", "current_mark", "mark"):
        value = data.get(key)
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            match = re.search(r"\d+", value)
            if match:
                return int(match.group(0))
    return None


def _has_tests_or_evidence(data: dict[str, Any]) -> bool:
    for key in ("tests", "test_evidence", "evidence", "reproduced_evidence"):
        value = data.get(key)
        if isinstance(value, list) and value:
            return True
        if isinstance(value, dict) and value:
            return True
        if isinstance(value, str) and value.strip():
            return True
    return False


def _check_readiness_mark(target: Path, findings: list[PromotionGateFinding], inputs_read: list[str]) -> None:
    for path in [
        target / ".hldspec" / "readiness_scorecard.json",
        target / ".hldspec" / "promotion_scorecard.json",
    ]:
        data = _read_optional_json(target, path, findings, inputs_read)
        if not isinstance(data, dict):
            continue
        mark = _extract_mark(data)
        if mark is not None and mark > 7 and not _has_tests_or_evidence(data):
            findings.append(_finding(target, "ACTION", "readiness_evidence", path, "readiness mark above 7 requires tests or reproduced evidence"))


def _check_promoted_capability_runskeptic(target: Path, findings: list[PromotionGateFinding], inputs_read: list[str]) -> None:
    path = target / ".hldspec" / "promoted_capabilities.json"
    data = _read_optional_json(target, path, findings, inputs_read)
    if not isinstance(data, dict):
        return
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list):
        return
    for idx, item in enumerate(capabilities, start=1):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", f"capability-{idx}"))
        status = str(item.get("runskeptic_status", "")).upper()
        if status not in {"PASS", "ACTION", "CONFLICT"}:
            findings.append(_finding(target, "ACTION", "runskeptic_status", path, f"promoted capability {name} is missing RunSkeptic status"))


def evaluate_promotion_gate(target: Path) -> dict[str, Any]:
    target = target.expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise ValueError(f"target must be an existing directory: {target}")

    findings: list[PromotionGateFinding] = []
    inputs_read: list[str] = []
    hldspec_dir = target / ".hldspec"
    validation_dir = hldspec_dir / "validation"

    _check_validation_reports(target, validation_dir, findings, inputs_read)
    _read_events(target, hldspec_dir / "events.jsonl", findings, inputs_read)
    _read_optional_json(target, hldspec_dir / "agent_session.json", findings, inputs_read)
    _read_optional_json(target, hldspec_dir / "allowed_evidence.json", findings, inputs_read)
    context_packs = hldspec_dir / "context_packs"
    if context_packs.exists():
        inputs_read.append(relpath(context_packs, target))
    _check_context_prompt_validation_presence(target, findings)
    _check_implementation_prompt_guard(target, findings)
    _check_human_checkpoints(target, findings, inputs_read)
    _check_readiness_mark(target, findings, inputs_read)
    _check_promoted_capability_runskeptic(target, findings, inputs_read)

    status = _status_from_findings(findings)
    report: dict[str, Any] = {
        "schema_version": PROMOTION_GATE_SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "status": status,
        "inputs_read": sorted(dict.fromkeys(inputs_read)),
        "findings": [asdict(item) for item in findings],
    }
    write_json(validation_dir / "promotion_gate.json", report)
    (validation_dir / "promotion_gate.md").write_text(_markdown_report(report), encoding="utf-8")
    return report
