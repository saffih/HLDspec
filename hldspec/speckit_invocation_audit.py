"""SpecKit invocation audit log: canonical path, closed schema, deterministic serialization.

Implements Slice A of `docs/SPECKIT_INVOCATION_AUDIT_LOG_CONTRACT.md`: the
pointer-aware path helper and a closed schema-version-1 validator for
STARTED/FINISHED records, plus deterministic one-line NDJSON serialization.

Deliberately out of scope (later slices): no writer, no append/lock/flush/
fsync, no corruption-history or lifecycle-pair reading, no repair, no
`SpecKitInvoker`/`speckit_drive_loop.py` wiring, no filesystem inspection of
the target. `validate_invocation_record` is a pure structural check.
"""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any, Mapping

from . import control_paths
from .helper_registry import FORBIDDEN_AUTHORITY_LEVELS, VALID_AUTHORITY_LEVELS
from .speckit_invoker import ARTIFACT_PHASES, PHASE_SKILL

SCHEMA_VERSION = 1

RECORD_STARTED = "STARTED"
RECORD_FINISHED = "FINISHED"

VALID_RECORD_TYPES: frozenset[str] = frozenset({RECORD_STARTED, RECORD_FINISHED})
VALID_BINDING_STATUSES: frozenset[str] = frozenset(
    {"BOUND", "SYNTHETIC", "PARTIAL", "UNAVAILABLE"}
)
VALID_EXECUTION_PATHS: frozenset[str] = frozenset(
    {"speckit_invoker", "speckit_drive_loop"}
)
VALID_OUTCOMES: frozenset[str] = frozenset(
    {
        "SUCCESS",
        "COMMAND_FAILED",
        "HOLLOW_COMPLETION",
        "TIMEOUT",
        "INTERRUPTED",
        "UNEXPECTED_MUTATION",
    }
)

INVOCATION_AUDIT_RELATIVE_PATH = Path("audit") / "speckit_invocations.jsonl"

_HELPER_ID = "speckit"
_TOOLCHAIN = "SpecKit"

_COMMON_FIELDS: tuple[str, ...] = (
    "schema_version",
    "record_type",
    "invocation_id",
    "recorded_at_utc",
    "helper_id",
    "toolchain",
    "execution_path",
    "runtime",
    "phase",
    "skill",
    "model",
    "authority_level",
    "approval_ref",
    "target_binding",
    "command_identity",
)

_STARTED_FIELDS: tuple[str, ...] = ("started_at_utc", "git_signature_before_sha256")

_FINISHED_FIELDS: tuple[str, ...] = (
    "finished_at_utc",
    "duration_ms",
    "outcome",
    "returncode",
    "ok",
    "produced_artifacts",
    "verified",
    "git_branch_after",
    "git_head_after",
    "git_signature_after_sha256",
    "changed_paths",
    "changed_path_count",
    "changed_paths_truncated",
    "stdout_bytes",
    "stdout_sha256",
    "stderr_bytes",
    "stderr_sha256",
    "error_summary_redacted",
    "watchdog_triggered",
)

_TARGET_BINDING_FIELDS: tuple[str, ...] = (
    "target_path_sha256",
    "binding_status",
    "git_branch_before",
    "git_head_before",
    "remote_identity_sha256",
    "source_package_sha256",
    "feature_id",
    "spec_dir",
    "bundle_id",
)

_COMMAND_IDENTITY_FIELDS: tuple[str, ...] = (
    "agent_cmd",
    "argv_without_prompt",
    "prompt_sha256",
    "prompt_bytes",
    "skip_permissions",
)

_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$")
_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def resolve_invocation_audit_log_path(target: str | Path) -> Path:
    """Canonical pointer-aware audit log path. Creates nothing; touches nothing."""
    return control_paths.resolve_hldspec_dir(Path(target)) / INVOCATION_AUDIT_RELATIVE_PATH


# --- primitive checks --------------------------------------------------------

def _is_non_bool_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and value != ""


def _is_valid_timestamp(value: object) -> bool:
    return isinstance(value, str) and bool(_TIMESTAMP_RE.match(value))


def _is_valid_uuid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        return str(uuid.UUID(value)) == value
    except (ValueError, AttributeError, TypeError):
        return False


def _is_hex64(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX64_RE.match(value))


def _is_git_head(value: object) -> bool:
    return isinstance(value, str) and bool(_HEX40_RE.match(value) or _HEX64_RE.match(value))


def _is_safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or value == "":
        return False
    if "\x00" in value:
        return False
    if value == ".":
        return False
    if value.startswith("/"):
        return False
    parts = value.split("/")
    if any(part in ("", "..") for part in parts):
        return False
    return True


# --- nested object validation -------------------------------------------------

def _validate_target_binding(binding: object, errors: list[str]) -> None:
    if not isinstance(binding, dict):
        errors.append("target_binding: must be an object")
        return

    for field in _TARGET_BINDING_FIELDS:
        if field not in binding:
            errors.append(f"target_binding.{field}: missing required field")
    for key in binding:
        if key not in _TARGET_BINDING_FIELDS:
            errors.append(f"target_binding.{key}: unknown field")

    if "target_path_sha256" in binding and not _is_hex64(binding["target_path_sha256"]):
        errors.append("target_binding.target_path_sha256: must be lowercase 64-char hex")

    if "binding_status" in binding and binding["binding_status"] not in VALID_BINDING_STATUSES:
        errors.append(
            f"target_binding.binding_status: must be one of {sorted(VALID_BINDING_STATUSES)}"
        )

    if "git_branch_before" in binding and "git_head_before" in binding:
        branch = binding["git_branch_before"]
        head = binding["git_head_before"]
        if branch is None and head is None:
            pass
        elif branch is not None and head is not None:
            if not _is_non_empty_str(branch):
                errors.append("target_binding.git_branch_before: must be a non-empty string")
            if not _is_git_head(head):
                errors.append(
                    "target_binding.git_head_before: must be lowercase hex of length 40 or 64"
                )
        else:
            errors.append(
                "target_binding.git_branch_before/git_head_before: must both be null "
                "or both be non-null"
            )

    for field in ("remote_identity_sha256", "source_package_sha256"):
        if field in binding and binding[field] is not None and not _is_hex64(binding[field]):
            errors.append(f"target_binding.{field}: must be null or lowercase 64-char hex")

    for field in ("feature_id", "bundle_id"):
        if field in binding and binding[field] is not None and not _is_non_empty_str(binding[field]):
            errors.append(f"target_binding.{field}: must be null or a non-empty string")

    if "spec_dir" in binding:
        spec_dir = binding["spec_dir"]
        if spec_dir is not None and not _is_safe_relative_path(spec_dir):
            errors.append("target_binding.spec_dir: must be null or a safe target-relative path")


def _validate_command_identity(
    identity: object, model: object, skill: str | None, errors: list[str]
) -> None:
    if not isinstance(identity, dict):
        errors.append("command_identity: must be an object")
        return

    for field in _COMMAND_IDENTITY_FIELDS:
        if field not in identity:
            errors.append(f"command_identity.{field}: missing required field")
    for key in identity:
        if key not in _COMMAND_IDENTITY_FIELDS:
            errors.append(f"command_identity.{key}: unknown field")

    agent_cmd = identity.get("agent_cmd")
    if "agent_cmd" in identity:
        if not _is_non_empty_str(agent_cmd) or "\x00" in agent_cmd or "\n" in agent_cmd or "\r" in agent_cmd:
            errors.append("command_identity.agent_cmd: must be a non-empty string with no NUL/line break")

    argv = identity.get("argv_without_prompt")
    if "argv_without_prompt" in identity:
        if not isinstance(argv, list) or not argv or not all(_is_non_empty_str(a) for a in argv):
            errors.append(
                "command_identity.argv_without_prompt: must be a non-empty list of non-empty strings"
            )
        else:
            if any(("\x00" in a or "\n" in a or "\r" in a) for a in argv):
                errors.append("command_identity.argv_without_prompt: must contain no NUL/line break")
            if _is_non_empty_str(agent_cmd) and argv[0] != agent_cmd:
                errors.append(
                    "command_identity.argv_without_prompt: first item must equal agent_cmd"
                )
            if skill and any(a.startswith(f"/{skill}") for a in argv):
                errors.append(
                    "command_identity.argv_without_prompt: must not contain the prompt "
                    "slash-command prefix"
                )
            model_flag_indices = [i for i, a in enumerate(argv) if a == "--model"]
            if len(model_flag_indices) != 1 or model_flag_indices[0] + 1 >= len(argv):
                errors.append(
                    "command_identity.argv_without_prompt: must contain exactly one "
                    "--model value matching model"
                )
            else:
                model_value = argv[model_flag_indices[0] + 1]
                if model_value != model:
                    errors.append(
                        "command_identity.argv_without_prompt: --model value must match model"
                    )
            has_skip_flag = "--dangerously-skip-permissions" in argv
            skip_permissions = identity.get("skip_permissions")
            if isinstance(skip_permissions, bool) and skip_permissions != has_skip_flag:
                errors.append(
                    "command_identity.skip_permissions: must agree with presence of "
                    "--dangerously-skip-permissions in argv_without_prompt"
                )

    if "prompt_sha256" in identity and not _is_hex64(identity["prompt_sha256"]):
        errors.append("command_identity.prompt_sha256: must be lowercase 64-char hex")

    if "prompt_bytes" in identity:
        value = identity["prompt_bytes"]
        if not _is_non_bool_int(value) or value < 0:
            errors.append("command_identity.prompt_bytes: must be a non-negative integer")

    if "skip_permissions" in identity and not isinstance(identity["skip_permissions"], bool):
        errors.append("command_identity.skip_permissions: must be a boolean")


def _validate_changed_paths(value: object, errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append("changed_paths: must be a list")
        return
    for item in value:
        if not _is_safe_relative_path(item):
            errors.append(f"changed_paths: unsafe or invalid path entry {item!r}")
    if all(isinstance(item, str) for item in value):
        if len(set(value)) != len(value):
            errors.append("changed_paths: must not contain duplicate paths")
        if value != sorted(value):
            errors.append("changed_paths: must be sorted")


def validate_invocation_record(record: Mapping[str, Any]) -> list[str]:
    """Return schema-version-1 violations for one record. Empty == valid.

    Pure structural check: no filesystem access, no mutation of `record`.
    Errors are returned in a stable field order for deterministic output.
    """
    errors: list[str] = []

    record_type = record.get("record_type")
    if record_type == RECORD_STARTED:
        type_fields = _STARTED_FIELDS
    elif record_type == RECORD_FINISHED:
        type_fields = _FINISHED_FIELDS
    else:
        type_fields = _STARTED_FIELDS + _FINISHED_FIELDS

    allowed_fields = frozenset(_COMMON_FIELDS) | frozenset(type_fields)

    for field in _COMMON_FIELDS:
        if field not in record:
            errors.append(f"{field}: missing required field")
    if record_type in VALID_RECORD_TYPES:
        for field in type_fields:
            if field not in record:
                errors.append(f"{field}: missing required field")

    for key in record:
        if key not in allowed_fields:
            errors.append(f"{key}: unknown field")

    if "schema_version" in record:
        schema_version = record["schema_version"]
        if not _is_non_bool_int(schema_version) or schema_version != SCHEMA_VERSION:
            errors.append(f"schema_version: must be integer {SCHEMA_VERSION}")

    if "record_type" in record and record_type not in VALID_RECORD_TYPES:
        errors.append(f"record_type: must be one of {sorted(VALID_RECORD_TYPES)}")

    if "invocation_id" in record and not _is_valid_uuid(record["invocation_id"]):
        errors.append("invocation_id: must be a canonical lowercase hyphenated UUID string")

    if "recorded_at_utc" in record and not _is_valid_timestamp(record["recorded_at_utc"]):
        errors.append("recorded_at_utc: must be an RFC3339 UTC timestamp ending in Z")

    if "helper_id" in record and record["helper_id"] != _HELPER_ID:
        errors.append(f"helper_id: must equal {_HELPER_ID!r}")

    if "toolchain" in record and record["toolchain"] != _TOOLCHAIN:
        errors.append(f"toolchain: must equal {_TOOLCHAIN!r}")

    if "execution_path" in record and record["execution_path"] not in VALID_EXECUTION_PATHS:
        errors.append(f"execution_path: must be one of {sorted(VALID_EXECUTION_PATHS)}")

    if "runtime" in record and not _is_non_empty_str(record["runtime"]):
        errors.append("runtime: must be a non-empty string")

    phase = record.get("phase")
    if "phase" in record and phase not in PHASE_SKILL:
        errors.append(f"phase: must be a current PHASE_SKILL phase, got {phase!r}")

    skill = record.get("skill")
    if "skill" in record:
        if not _is_non_empty_str(skill):
            errors.append("skill: must be a non-empty string")
        elif phase in PHASE_SKILL and skill != PHASE_SKILL[phase]:
            errors.append(
                f"skill: must equal PHASE_SKILL[phase] ({PHASE_SKILL.get(phase)!r}), got {skill!r}"
            )

    model = record.get("model")
    if "model" in record and not _is_non_empty_str(model):
        errors.append("model: must be a non-empty string")

    if "authority_level" in record:
        level = record["authority_level"]
        if level not in VALID_AUTHORITY_LEVELS or level in FORBIDDEN_AUTHORITY_LEVELS:
            errors.append(
                "authority_level: must be a known, non-forbidden helper_registry authority level"
            )

    if "approval_ref" in record:
        approval_ref = record["approval_ref"]
        if approval_ref is not None and not _is_non_empty_str(approval_ref):
            errors.append("approval_ref: must be null or a non-empty string")

    skill_hint = skill if _is_non_empty_str(skill) else None
    if "target_binding" in record:
        _validate_target_binding(record["target_binding"], errors)
    if "command_identity" in record:
        _validate_command_identity(record["command_identity"], model, skill_hint, errors)

    if record_type == RECORD_STARTED:
        _validate_started_fields(record, errors)
    elif record_type == RECORD_FINISHED:
        _validate_finished_fields(record, phase, errors)

    return errors


def _validate_started_fields(record: Mapping[str, Any], errors: list[str]) -> None:
    if "started_at_utc" in record and not _is_valid_timestamp(record["started_at_utc"]):
        errors.append("started_at_utc: must be an RFC3339 UTC timestamp ending in Z")
    if "git_signature_before_sha256" in record and not _is_hex64(
        record["git_signature_before_sha256"]
    ):
        errors.append("git_signature_before_sha256: must be lowercase 64-char hex")


def _validate_finished_fields(
    record: Mapping[str, Any], phase: object, errors: list[str]
) -> None:
    if "finished_at_utc" in record and not _is_valid_timestamp(record["finished_at_utc"]):
        errors.append("finished_at_utc: must be an RFC3339 UTC timestamp ending in Z")

    if "duration_ms" in record:
        value = record["duration_ms"]
        if not _is_non_bool_int(value) or value < 0:
            errors.append("duration_ms: must be a non-negative integer")

    if "outcome" in record and record["outcome"] not in VALID_OUTCOMES:
        errors.append(f"outcome: must be one of {sorted(VALID_OUTCOMES)}")

    if "returncode" in record and not _is_non_bool_int(record["returncode"]):
        errors.append("returncode: must be an integer")

    for field in ("ok", "produced_artifacts", "watchdog_triggered", "changed_paths_truncated"):
        if field in record and not isinstance(record[field], bool):
            errors.append(f"{field}: must be a boolean")

    if "verified" in record and not isinstance(record["verified"], bool):
        errors.append("verified: must be a boolean")

    ok = record.get("ok")
    returncode = record.get("returncode")
    if (
        "ok" in record
        and "returncode" in record
        and isinstance(ok, bool)
        and _is_non_bool_int(returncode)
        and ok != (returncode == 0)
    ):
        errors.append("ok: must equal (returncode == 0)")

    produced_artifacts = record.get("produced_artifacts")
    verified = record.get("verified")
    if (
        isinstance(ok, bool)
        and isinstance(produced_artifacts, bool)
        and isinstance(verified, bool)
        and phase in PHASE_SKILL
    ):
        if not ok:
            expected_verified = False
        elif phase in ARTIFACT_PHASES:
            expected_verified = produced_artifacts
        else:
            expected_verified = True
        if verified != expected_verified:
            errors.append(
                f"verified: must equal {expected_verified} given ok={ok}, "
                f"produced_artifacts={produced_artifacts}, phase={phase!r}"
            )

    outcome = record.get("outcome")
    if outcome in VALID_OUTCOMES and isinstance(ok, bool) and _is_non_bool_int(returncode):
        if outcome == "SUCCESS" and (not isinstance(verified, bool) or verified is not True):
            errors.append("outcome: SUCCESS requires verified == true")
        if outcome == "COMMAND_FAILED" and (
            returncode == 0 or (isinstance(verified, bool) and verified is not False)
        ):
            errors.append(
                "outcome: COMMAND_FAILED requires a nonzero returncode and verified == false"
            )
        if outcome == "HOLLOW_COMPLETION" and not (
            returncode == 0
            and ok is True
            and isinstance(produced_artifacts, bool)
            and produced_artifacts is False
            and isinstance(verified, bool)
            and verified is False
        ):
            errors.append(
                "outcome: HOLLOW_COMPLETION requires returncode == 0, ok == true, "
                "produced_artifacts == false, verified == false"
            )

    if "git_branch_after" in record and "git_head_after" in record:
        branch = record["git_branch_after"]
        head = record["git_head_after"]
        if branch is None and head is None:
            pass
        elif branch is not None and head is not None:
            if not _is_non_empty_str(branch):
                errors.append("git_branch_after: must be a non-empty string")
            if not _is_git_head(head):
                errors.append("git_head_after: must be lowercase hex of length 40 or 64")
        else:
            errors.append(
                "git_branch_after/git_head_after: must both be null or both be non-null"
            )

    if "git_signature_after_sha256" in record and not _is_hex64(
        record["git_signature_after_sha256"]
    ):
        errors.append("git_signature_after_sha256: must be lowercase 64-char hex")

    if "changed_paths" in record:
        _validate_changed_paths(record["changed_paths"], errors)

    changed_paths = record.get("changed_paths")
    changed_path_count = record.get("changed_path_count")
    truncated = record.get("changed_paths_truncated")
    if "changed_path_count" in record:
        if not _is_non_bool_int(changed_path_count) or changed_path_count < 0:
            errors.append("changed_path_count: must be a non-negative integer")
        elif isinstance(changed_paths, list) and isinstance(truncated, bool):
            if not truncated and changed_path_count != len(changed_paths):
                errors.append(
                    "changed_path_count: must equal len(changed_paths) when not truncated"
                )
            elif truncated and changed_path_count < len(changed_paths):
                errors.append(
                    "changed_path_count: must be >= len(changed_paths) when truncated"
                )

    for field in ("stdout_bytes", "stderr_bytes"):
        if field in record:
            value = record[field]
            if not _is_non_bool_int(value) or value < 0:
                errors.append(f"{field}: must be a non-negative integer")

    for field in ("stdout_sha256", "stderr_sha256"):
        if field in record and not _is_hex64(record[field]):
            errors.append(f"{field}: must be lowercase 64-char hex")

    if "error_summary_redacted" in record:
        summary = record["error_summary_redacted"]
        if summary is not None:
            if not isinstance(summary, str):
                errors.append("error_summary_redacted: must be null or a string")
            else:
                if len(summary.encode("utf-8")) > 1024:
                    errors.append(
                        "error_summary_redacted: must be no larger than 1024 bytes"
                    )
                if _CONTROL_CHAR_RE.search(summary) or "\n" in summary or "\r" in summary:
                    errors.append(
                        "error_summary_redacted: must not contain NUL, CR, LF, or other "
                        "disallowed control characters"
                    )


def invocation_record_json_line(record: Mapping[str, Any]) -> str:
    """Validate and serialize `record` to one deterministic NDJSON line.

    Raises `ValueError` if the record is invalid. Never mutates `record`,
    performs no file I/O.
    """
    errors = validate_invocation_record(record)
    if errors:
        raise ValueError("; ".join(errors))
    return json.dumps(dict(record), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
