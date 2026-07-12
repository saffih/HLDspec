"""SpecKit invocation audit log: canonical path, closed schema, durable writer.

Implements Slices A and B of `docs/SPECKIT_INVOCATION_AUDIT_LOG_CONTRACT.md`:
the pointer-aware path helper, a closed schema-version-1 validator for
STARTED/FINISHED records, deterministic one-line NDJSON serialization
(Slice A), and a durable exclusive-lock append writer with corruption and
lifecycle-pair detection (Slice B, `append_invocation_record`).

Deliberately out of scope (later slices): no reader, no repair, no
`SpecKitInvoker`/`speckit_drive_loop.py` wiring. `validate_invocation_record`
remains a pure structural check with no filesystem access;
`append_invocation_record` is the only function in this module that touches
the filesystem.
"""
from __future__ import annotations

import datetime
import errno
import fcntl
import json
import math
import os
import re
import stat
import sys
import time
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


def _parse_utc_timestamp(value: str) -> datetime.datetime:
    """Parse an already shape-validated RFC3339 UTC timestamp into a real datetime.

    Callers must first confirm `_TIMESTAMP_RE` matches; this only performs the
    calendar-validity parse (rejecting e.g. month 99, hour 25) that the regex
    shape check alone cannot express. Raises `ValueError` on an impossible
    calendar date/time.
    """
    body = value[:-1]  # strip the mandatory trailing "Z"
    base, _, frac = body.partition(".")
    parsed = datetime.datetime.strptime(base, "%Y-%m-%dT%H:%M:%S")
    if frac:
        parsed = parsed.replace(microsecond=int(f"{frac:0<6.6}"))
    return parsed.replace(tzinfo=datetime.timezone.utc)


def _is_valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not _TIMESTAMP_RE.match(value):
        return False
    try:
        _parse_utc_timestamp(value)
    except ValueError:
        return False
    return True


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


# --- Slice B: durable append writer ------------------------------------------
#
# Implements docs/SPECKIT_INVOCATION_AUDIT_LOG_CONTRACT.md Sections 3, 4, 6, 7.
# Deliberately out of scope: no reader, no repair, no SpecKitInvoker wiring.

DEFAULT_LOCK_TIMEOUT_SECONDS = 10.0


class InvocationAuditError(RuntimeError):
    """Base class for Slice B writer operational failures.

    Optional attributes are populated where known and left `None` otherwise;
    never include complete raw record content in `message` or these fields.
    """

    def __init__(
        self,
        message: str,
        *,
        path: Path | None = None,
        line_number: int | None = None,
        reason: str | None = None,
        invocation_id: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.path = path
        self.line_number = line_number
        self.reason = reason
        self.invocation_id = invocation_id
        self.timeout_seconds = timeout_seconds


class InvocationAuditCorruptionError(InvocationAuditError):
    """Existing audit history failed strict validation; nothing was written."""


class InvocationAuditLockTimeout(InvocationAuditError):
    """The exclusive audit-log lock could not be acquired before the deadline."""


_LOCK_POLL_SECONDS = 0.05
_READ_CHUNK_BYTES = 65536

_PAIR_IDENTITY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "invocation_id",
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


def _validate_lock_timeout(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("lock_timeout_seconds: must be a non-boolean int or float")
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("lock_timeout_seconds: must be finite")
    if value <= 0:
        raise ValueError("lock_timeout_seconds: must be positive")
    return value


# --- CP3B: hardened ancestor traversal + narrow Darwin root-alias policy ---
#
# CP3A opened the resolved audit root in one shot
# (`os.open(str(root_path), O_NOFOLLOW)`): the kernel resolves every
# intermediate path component through its normal lookup and only the final,
# already-resolved component is checked for O_NOFOLLOW -- so an
# attacker-controlled symlink anywhere in `root_path`'s ancestry was followed
# silently. `_open_root_fd` instead walks `root_path` one real component at a
# time from a fixed anchor fd (`/` for an absolute path, `.` for a relative
# one), opening every component with `O_NOFOLLOW`, so no ancestor symlink can
# be followed regardless of position.
#
# The sole exception, per explicit owner authorization, is the first
# component of an absolute path when it is exactly one of the two stock
# Darwin root aliases (`/var -> private/var`, `/tmp -> private/tmp`):
# `_darwin_alias_translation` decides whether to trust it (root-owned,
# non-writable anchor directory; root-owned symlink entry; exact `readlink`
# target) and, if trusted, `_open_root_fd` substitutes the real
# `private/var` or `private/tmp` components -- themselves opened with
# `O_NOFOLLOW` like every other component -- instead of following the alias.
# No other symlink, alias, or generic `resolve()`/`realpath()` is permitted
# anywhere in this traversal.

_DARWIN_ROOT_ALIASES: dict[str, tuple[str, ...]] = {
    "var": ("private", "var"),
    "tmp": ("private", "tmp"),
}

_DARWIN_ALIAS_READLINK_TARGETS: dict[str, frozenset[str]] = {
    "var": frozenset({"private/var", "/private/var"}),
    "tmp": frozenset({"private/tmp", "/private/tmp"}),
}

_TRAVERSAL_DIR_FLAGS = os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW
if hasattr(os, "O_CLOEXEC"):
    _TRAVERSAL_DIR_FLAGS |= os.O_CLOEXEC


def _darwin_alias_translation(
    name: str,
    *,
    platform: str,
    anchor_owner_uid: int,
    anchor_mode: int,
    entry_is_symlink: bool,
    entry_owner_uid: int,
    entry_target: str,
) -> tuple[str, ...] | None:
    """Pure trust decision for one first-absolute-component alias candidate.

    Takes already-observed filesystem facts rather than a path or fd, so it
    has no filesystem access of its own and runs identically on every
    platform -- callers gate the real `os.stat`/`os.readlink` probing (and
    the Darwin-only applicability) behind `_resolve_darwin_alias`. Returns
    the real path components to substitute for `name`, or `None` if any
    trust condition fails.
    """
    if platform != "darwin":
        return None
    real_components = _DARWIN_ROOT_ALIASES.get(name)
    if real_components is None:
        return None
    if anchor_owner_uid != 0:
        return None
    if anchor_mode & (stat.S_IWGRP | stat.S_IWOTH):
        return None
    if not entry_is_symlink:
        return None
    if entry_owner_uid != 0:
        return None
    if entry_target not in _DARWIN_ALIAS_READLINK_TARGETS[name]:
        return None
    return real_components


def _resolve_darwin_alias(anchor_fd: int, name: str) -> tuple[str, ...] | None:
    """Inspect (never follow) `name` under `anchor_fd` and apply
    `_darwin_alias_translation`. `anchor_fd` is the already-open directory
    fd the candidate alias entry lives in (the root anchor, for the first
    absolute component); this never opens or dereferences the alias itself.
    """
    if sys.platform != "darwin" or name not in _DARWIN_ROOT_ALIASES:
        return None
    try:
        anchor_stat = os.fstat(anchor_fd)
        entry_stat = os.stat(name, dir_fd=anchor_fd, follow_symlinks=False)
    except OSError:
        return None
    entry_is_symlink = stat.S_ISLNK(entry_stat.st_mode)
    entry_target = ""
    if entry_is_symlink:
        try:
            entry_target = os.readlink(name, dir_fd=anchor_fd)
        except OSError:
            return None
    return _darwin_alias_translation(
        name,
        platform=sys.platform,
        anchor_owner_uid=anchor_stat.st_uid,
        anchor_mode=stat.S_IMODE(anchor_stat.st_mode),
        entry_is_symlink=entry_is_symlink,
        entry_owner_uid=entry_stat.st_uid,
        entry_target=entry_target,
    )


def _open_traversal_anchor(is_absolute: bool, root_path: Path) -> int:
    anchor_name = "/" if is_absolute else "."
    try:
        return os.open(anchor_name, _TRAVERSAL_DIR_FLAGS)
    except OSError as exc:
        raise InvocationAuditError(
            "unable to open resolved audit root traversal anchor", path=root_path
        ) from exc


def _open_traversal_component(parent_fd: int, name: str, root_path: Path) -> int:
    try:
        return os.open(name, _TRAVERSAL_DIR_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError as exc:
        raise InvocationAuditError(
            "resolved audit root does not exist", path=root_path
        ) from exc
    except NotADirectoryError as exc:
        raise InvocationAuditError(
            "resolved audit root is not a directory", path=root_path
        ) from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise InvocationAuditError(
                "resolved audit root traversal must not follow a symlink",
                path=root_path,
            ) from exc
        raise InvocationAuditError(
            "unable to open resolved audit root traversal component", path=root_path
        ) from exc


def _close_quietly(fd: int) -> None:
    """Best-effort cleanup close: a close that is itself cleaning up after
    another failure must never replace that failure's exception, and a
    close that already reported failure must never be retried, so any
    `OSError` raised here is swallowed rather than propagated.
    """
    try:
        os.close(fd)
    except OSError:
        pass


def _open_root_fd(root_path: Path) -> int:
    """Open the full `root_path` directory chain component-by-component,
    rejecting every symlink except the two owner-authorized Darwin root
    aliases (see module notes above). Returns exactly one open directory fd
    owning `root_path` itself; the caller owns and must close it. Never
    creates anything -- `root_path` and every component in it must already
    exist.
    """
    is_absolute = root_path.is_absolute()
    remaining = list(root_path.parts[1:]) if is_absolute else list(root_path.parts)

    current_fd = _open_traversal_anchor(is_absolute, root_path)
    for index, component in enumerate(remaining):
        # The entire per-component step -- including alias resolution, which
        # itself performs filesystem calls against `current_fd` -- is one
        # failure unit: any exception here must close the fd `_open_root_fd`
        # currently owns before propagating, not only a failure from the
        # final `os.open`. Ownership of `next_fd` transfers to `current_fd`
        # immediately on open, before the old fd's close is even attempted,
        # so a failing old-fd close can never strand `next_fd` unreachable
        # from the `except` handler below -- and that old-fd close is never
        # retried, since a close that already reported failure leaves the
        # fd's real state platform-dependent.
        try:
            real_components: tuple[str, ...] = (component,)
            if is_absolute and index == 0:
                translated = _resolve_darwin_alias(current_fd, component)
                if translated is not None:
                    real_components = translated
            for real_component in real_components:
                next_fd = _open_traversal_component(current_fd, real_component, root_path)
                old_fd = current_fd
                current_fd = next_fd
                os.close(old_fd)
        except BaseException:
            _close_quietly(current_fd)
            raise
    return current_fd


def _open_or_create_dir_component(parent_fd: int, name: str, context_path: Path) -> tuple[int, bool]:
    created = False
    try:
        os.mkdir(name, 0o700, dir_fd=parent_fd)
        created = True
    except FileExistsError:
        pass
    except OSError as exc:
        raise InvocationAuditError(
            f"unable to create audit path component {name!r}", path=context_path
        ) from exc

    try:
        fd = os.open(name, os.O_DIRECTORY | os.O_NOFOLLOW | os.O_RDONLY, dir_fd=parent_fd)
    except NotADirectoryError as exc:
        raise InvocationAuditError(
            f"audit path component {name!r} is not a directory", path=context_path
        ) from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise InvocationAuditError(
                f"audit path component {name!r} must not be a symlink", path=context_path
            ) from exc
        raise InvocationAuditError(
            f"unable to open audit path component {name!r}", path=context_path
        ) from exc
    return fd, created


def _open_or_create_audit_file(parent_fd: int, name: str, context_path: Path) -> tuple[int, bool]:
    flags = os.O_RDWR | os.O_APPEND | os.O_NOFOLLOW | os.O_NONBLOCK
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC

    created = False
    try:
        fd = os.open(name, flags | os.O_CREAT | os.O_EXCL, 0o600, dir_fd=parent_fd)
        created = True
    except FileExistsError:
        try:
            fd = os.open(name, flags, dir_fd=parent_fd)
        except OSError as exc:
            if exc.errno == errno.ELOOP:
                raise InvocationAuditError(
                    f"audit file {name!r} must not be a symlink", path=context_path
                ) from exc
            raise InvocationAuditError(
                f"unable to open audit file {name!r}", path=context_path
            ) from exc
    except OSError as exc:
        if exc.errno == errno.ELOOP:
            raise InvocationAuditError(
                f"audit file {name!r} must not be a symlink", path=context_path
            ) from exc
        raise InvocationAuditError(
            f"unable to create audit file {name!r}", path=context_path
        ) from exc

    try:
        file_stat = os.fstat(fd)
        if not stat.S_ISREG(file_stat.st_mode):
            raise InvocationAuditError(
                f"audit file {name!r} is not a regular file", path=context_path
            )
    except BaseException:
        os.close(fd)
        raise
    return fd, created


def _acquire_exclusive_lock(fd: int, timeout_seconds: float, path: Path) -> None:
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                raise InvocationAuditLockTimeout(
                    "timed out waiting for the exclusive audit log lock",
                    path=path,
                    timeout_seconds=timeout_seconds,
                )
            time.sleep(_LOCK_POLL_SECONDS)


def _release_lock(fd: int) -> None:
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: set[str] = set()
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON key: {key!r}")
        seen.add(key)
        result[key] = value
    return result


def _reject_non_finite_constant(token: str) -> None:
    raise ValueError(f"non-finite JSON constant: {token}")


def _iter_existing_lines(fd: int, path: Path):
    """Yield `(line_number, raw_line_bytes)` for each complete existing line.

    Reads in bounded chunks, so multi-line history is processed
    incrementally and the entire log is not normally loaded into memory at
    once. This is not a bounded-memory guarantee for every input shape: the
    current line is buffered in full until its terminating newline is found,
    so one extremely large or unterminated line can still consume memory
    proportional to that line's length. No total record-size limit is
    currently ratified.

    Raises `InvocationAuditCorruptionError` if trailing bytes exist with no
    terminating newline (covers both a literally missing final newline and a
    partial/interrupted trailing write left over from a prior failure).
    """
    os.lseek(fd, 0, os.SEEK_SET)
    buffer = b""
    line_number = 0
    while True:
        chunk = os.read(fd, _READ_CHUNK_BYTES)
        if not chunk:
            break
        buffer += chunk
        while True:
            idx = buffer.find(b"\n")
            if idx == -1:
                break
            raw_line = buffer[:idx]
            buffer = buffer[idx + 1:]
            line_number += 1
            yield line_number, raw_line
    if buffer:
        line_number += 1
        raise InvocationAuditCorruptionError(
            "existing audit history has a trailing line with no final newline",
            path=path,
            line_number=line_number,
            reason="missing_final_newline",
        )


def _decode_and_parse_existing_line(raw_line: bytes, path: Path, line_number: int) -> dict[str, Any]:
    if raw_line == b"":
        raise InvocationAuditCorruptionError(
            "existing audit history contains a blank line",
            path=path,
            line_number=line_number,
            reason="blank_line",
        )

    # Decode/parse failures are deliberately *not* re-raised with `from exc`:
    # the underlying `UnicodeDecodeError`/`json.JSONDecodeError`/`ValueError`
    # carry the raw offending bytes/text (or, for a duplicate-key rejection,
    # the literal key name) in their own attributes. Chaining would leave
    # that content reachable via `__cause__`/`__context__` even though this
    # function's own message and `reason` are deliberately generic -- so the
    # corruption exception is constructed and raised only after fully exiting
    # the `except` block, which leaves both `__cause__` and `__context__` None.
    decode_failed = False
    try:
        text = raw_line.decode("utf-8")
    except UnicodeDecodeError:
        decode_failed = True
    if decode_failed:
        raise InvocationAuditCorruptionError(
            "existing audit history contains invalid UTF-8",
            path=path,
            line_number=line_number,
            reason="invalid_utf8",
        )

    parse_failed = False
    parsed = None
    try:
        parsed = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_non_finite_constant,
        )
    except (json.JSONDecodeError, ValueError):
        parse_failed = True
    if parse_failed:
        raise InvocationAuditCorruptionError(
            "existing audit history contains malformed JSON",
            path=path,
            line_number=line_number,
            reason="malformed_json",
        )
    if not isinstance(parsed, dict):
        raise InvocationAuditCorruptionError(
            "existing audit history line is not a JSON object",
            path=path,
            line_number=line_number,
            reason="non_object_json",
        )
    if validate_invocation_record(parsed):
        # Deliberately generic: Slice A's per-field messages echo field
        # values (e.g. `phase`), which would leak existing line content.
        raise InvocationAuditCorruptionError(
            "existing audit history line fails schema validation",
            path=path,
            line_number=line_number,
            reason="schema_invalid_record",
        )
    return parsed


def _identity_subset(record: Mapping[str, Any]) -> dict[str, Any]:
    return {field: record.get(field) for field in _PAIR_IDENTITY_FIELDS}


def _lifecycle_violation(
    existing: bool, message: str, *, path: Path, line_number: int | None, invocation_id: object
) -> InvocationAuditError:
    invocation_id = invocation_id if isinstance(invocation_id, str) else None
    if existing:
        return InvocationAuditCorruptionError(
            message,
            path=path,
            line_number=line_number,
            reason="lifecycle_violation",
            invocation_id=invocation_id,
        )
    return InvocationAuditError(message, path=path, invocation_id=invocation_id)


def _apply_lifecycle_transition(
    lifecycle: dict[str, dict[str, Any]],
    record: Mapping[str, Any],
    *,
    path: Path,
    line_number: int | None,
    existing: bool,
) -> None:
    invocation_id = record.get("invocation_id")
    entry = lifecycle.setdefault(invocation_id, {"started": None, "finished": None})
    record_type = record.get("record_type")

    if record_type == RECORD_STARTED:
        if entry["started"] is not None:
            raise _lifecycle_violation(
                existing,
                "STARTED is a duplicate or follows an already-completed invocation",
                path=path,
                line_number=line_number,
                invocation_id=invocation_id,
            )
        entry["started"] = record
        return

    if record_type == RECORD_FINISHED:
        started = entry["started"]
        if started is None:
            raise _lifecycle_violation(
                existing,
                "FINISHED has no matching STARTED",
                path=path,
                line_number=line_number,
                invocation_id=invocation_id,
            )
        if entry["finished"] is not None:
            raise _lifecycle_violation(
                existing,
                "FINISHED is a duplicate for this invocation_id",
                path=path,
                line_number=line_number,
                invocation_id=invocation_id,
            )
        if _identity_subset(started) != _identity_subset(record):
            raise _lifecycle_violation(
                existing,
                "STARTED/FINISHED identity fields do not match",
                path=path,
                line_number=line_number,
                invocation_id=invocation_id,
            )
        if _parse_utc_timestamp(record["finished_at_utc"]) < _parse_utc_timestamp(
            started["started_at_utc"]
        ):
            raise _lifecycle_violation(
                existing,
                "finished_at_utc precedes started_at_utc",
                path=path,
                line_number=line_number,
                invocation_id=invocation_id,
            )
        entry["finished"] = record


def _write_all(fd: int, data: bytes, path: Path) -> None:
    view = memoryview(data)
    total = len(data)
    written = 0
    while written < total:
        try:
            n = os.write(fd, view[written:])
        except InterruptedError:
            if written == 0:
                continue
            raise InvocationAuditError(
                "audit record write was interrupted after partial progress; "
                "not retried",
                path=path,
            ) from None
        except OSError as exc:
            raise InvocationAuditError("audit record write failed", path=path) from exc
        if n == 0:
            raise InvocationAuditError(
                "audit record write returned zero bytes", path=path
            )
        written += n


def _fsync_fd(fd: int, path: Path) -> None:
    try:
        os.fsync(fd)
    except OSError as exc:
        raise InvocationAuditError("fsync failed", path=path) from exc


def append_invocation_record(
    target: str | Path,
    record: Mapping[str, Any],
    *,
    lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> Path:
    """Durably append one validated record to the canonical audit log.

    Raises `ValueError` for invalid `record`/`lock_timeout_seconds` (checked
    before any filesystem mutation), `InvocationAuditLockTimeout` if the
    exclusive lock cannot be acquired in time, `InvocationAuditCorruptionError`
    if existing history fails strict validation, and `InvocationAuditError`
    for any other operational/lifecycle/durability failure.
    """
    timeout = _validate_lock_timeout(lock_timeout_seconds)
    line_bytes = invocation_record_json_line(record).encode("utf-8")

    audit_log_path = resolve_invocation_audit_log_path(target)
    audit_dir_path = audit_log_path.parent
    hldspec_dir_path = audit_dir_path.parent
    root_path = hldspec_dir_path.parent

    opened_fds: list[int] = []
    try:
        root_fd = _open_root_fd(root_path)
        opened_fds.append(root_fd)

        hldspec_fd, _hldspec_created = _open_or_create_dir_component(
            root_fd, hldspec_dir_path.name, audit_log_path
        )
        opened_fds.append(hldspec_fd)

        audit_dir_fd, _audit_dir_created = _open_or_create_dir_component(
            hldspec_fd, audit_dir_path.name, audit_log_path
        )
        opened_fds.append(audit_dir_fd)

        file_fd, _file_created = _open_or_create_audit_file(
            audit_dir_fd, audit_log_path.name, audit_log_path
        )
        opened_fds.append(file_fd)

        _acquire_exclusive_lock(file_fd, timeout, audit_log_path)
        try:
            lifecycle: dict[str, dict[str, Any]] = {}
            for line_number, raw_line in _iter_existing_lines(file_fd, audit_log_path):
                parsed = _decode_and_parse_existing_line(raw_line, audit_log_path, line_number)
                _apply_lifecycle_transition(
                    lifecycle, parsed, path=audit_log_path, line_number=line_number, existing=True
                )

            _apply_lifecycle_transition(
                lifecycle, dict(record), path=audit_log_path, line_number=None, existing=False
            )

            _write_all(file_fd, line_bytes, audit_log_path)
            _fsync_fd(file_fd, audit_log_path)
            # Every successful append fsyncs the complete parent-directory
            # chain, regardless of which process (if any) created each
            # component: a concurrent writer that observed every component
            # as already existing still needs independent proof that the
            # path entries it relied on are durable, not just proof that
            # *its own* creation was durable.
            _fsync_fd(audit_dir_fd, audit_log_path)
            _fsync_fd(hldspec_fd, audit_log_path)
            _fsync_fd(root_fd, audit_log_path)
        finally:
            _release_lock(file_fd)
    finally:
        for fd in reversed(opened_fds):
            try:
                os.close(fd)
            except OSError:
                pass

    return audit_log_path
