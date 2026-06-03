from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hldspec.context_economy import FORBIDDEN_BROAD_READ_PATTERNS, SCHEMA_VERSION, validate_prompt_file

VALID_MODEL_TIERS = frozenset({"MODEL_ROUTINE", "MODEL_DEFAULT", "MODEL_STRONG", "MODEL_CRITICAL"})


@dataclass(frozen=True)
class ValidationFinding:
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


def _finding(target: Path, check: str, path: Path, message: str, severity: str = "ACTION") -> ValidationFinding:
    return ValidationFinding(severity=severity, check=check, path=relpath(path, target), message=message)


def _section(text: str, marker: str) -> str:
    if marker not in text:
        return ""
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def _model_tier(text: str) -> str | None:
    section = _section(text, "## Model tier")
    match = re.search(r"\bMODEL_[A-Z]+\b", section)
    return match.group(0) if match else None


def _prompt_findings(target: Path, prompt: Path) -> list[ValidationFinding]:
    findings: list[ValidationFinding] = []
    for error in validate_prompt_file(prompt):
        findings.append(_finding(target, "prompt_context_economy", prompt, error))
    if not prompt.exists():
        return findings

    text = prompt.read_text(encoding="utf-8")
    lowered = text.lower()
    if "## runskeptic triggers" not in lowered:
        findings.append(_finding(target, "runskeptic_triggers", prompt, "missing RunSkeptic trigger section"))
    elif "runskeptic" not in _section(text, "## RunSkeptic triggers").lower():
        findings.append(_finding(target, "runskeptic_triggers", prompt, "RunSkeptic trigger section must mention RunSkeptic"))

    model_tier = _model_tier(text)
    if model_tier not in VALID_MODEL_TIERS:
        findings.append(
            _finding(
                target,
                "model_tier",
                prompt,
                f"missing or invalid model tier; expected one of {', '.join(sorted(VALID_MODEL_TIERS))}",
            )
        )

    for phrase in FORBIDDEN_BROAD_READ_PATTERNS:
        if phrase in lowered:
            findings.append(_finding(target, "forbidden_broad_read", prompt, f"prompt includes broad-read phrase: {phrase}"))

    if prompt.name == "06-implement.md":
        if "human approval" not in lowered or "approved" not in lowered:
            findings.append(
                _finding(
                    target,
                    "implement_human_approval",
                    prompt,
                    "implement-phase prompt must require explicit human approval before code-changing work",
                )
            )
    return findings


def _markdown_report(report: dict[str, Any]) -> str:
    lines = [
        "# Context Prompt Validation",
        "",
        f"Status: `{report['status']}`",
        f"Target: `{report['target']}`",
        f"Generated at: `{report['generated_at']}`",
        "",
        "## Findings",
        "",
    ]
    findings = report["findings"]
    if not findings:
        lines.append("No ACTION or CONFLICT findings.")
    else:
        for item in findings:
            lines.append(f"- `{item['severity']}` `{item['check']}` `{item['path']}` - {item['message']}")
    return "\n".join(lines) + "\n"


def validate_hldspec_target(target: Path) -> dict[str, Any]:
    target = target.expanduser().resolve()
    if not target.exists() or not target.is_dir():
        raise ValueError(f"target must be an existing directory: {target}")

    hldspec_dir = target / ".hldspec"
    findings: list[ValidationFinding] = []

    allowed_evidence = hldspec_dir / "allowed_evidence.json"
    if not allowed_evidence.exists():
        findings.append(_finding(target, "allowed_evidence", allowed_evidence, "missing target/.hldspec/allowed_evidence.json"))
    else:
        try:
            read_json(allowed_evidence)
        except Exception as exc:
            findings.append(_finding(target, "allowed_evidence", allowed_evidence, f"invalid JSON: {exc}"))

    forbidden_reads = hldspec_dir / "forbidden_reads.md"
    if not forbidden_reads.exists():
        findings.append(_finding(target, "forbidden_reads", forbidden_reads, "missing target/.hldspec/forbidden_reads.md"))

    context_root = hldspec_dir / "context_packs"
    context_packs = sorted(context_root.glob("*/context_pack.json")) if context_root.exists() else []
    if not context_packs:
        findings.append(_finding(target, "context_pack", context_root, "missing target/.hldspec/context_packs/*/context_pack.json"))
    for context_pack in context_packs:
        try:
            read_json(context_pack)
        except Exception as exc:
            findings.append(_finding(target, "context_pack", context_pack, f"invalid JSON: {exc}"))

    prompt_root = target / "prompts" / "speckit"
    prompts = sorted(prompt_root.glob("*/*.md")) if prompt_root.exists() else []
    if not prompts:
        findings.append(_finding(target, "speckit_prompts", prompt_root, "missing generated prompts under target/prompts/speckit/*/*.md"))
    for prompt in prompts:
        findings.extend(_prompt_findings(target, prompt))

    status = "PASS" if not findings else "ACTION"
    report: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "status": status,
        "findings": [asdict(item) for item in findings],
    }
    validation_dir = hldspec_dir / "validation"
    write_json(validation_dir / "context_prompt_validation.json", report)
    (validation_dir / "context_prompt_validation.md").write_text(_markdown_report(report), encoding="utf-8")
    return report
