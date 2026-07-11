"""Slice B tests: the durable append writer.

Slice A (`hldspec/speckit_invocation_audit.py`, done) provides the canonical
path helper and closed schema-version-1 validator/serializer. This file
specifies and exercises the Slice B public surface: an exclusive-lock append
writer with corruption detection and lifecycle-pair enforcement, per
`docs/SPECKIT_INVOCATION_AUDIT_LOG_CONTRACT.md` Sections 3, 4, 6, 7.

Until Slice B lands, only `SliceBApiPresenceTests` runs; every behavioral
class below is collected but skipped (`_SLICE_B_API_AVAILABLE` is False) so
the suite is genuinely RED for exactly one reason: the required public names
are absent from `hldspec.speckit_invocation_audit`.

`TimestampCalendarValidityRepairTests` targets `validate_invocation_record`
(Slice A, always available) and is not gated: it pins the bounded Slice A
timestamp-validator repair this Slice B work required (§9.7 of the CP2
authorization) — the shape regex alone accepted impossible calendar dates
such as `2026-99-99T25:61:61Z`.
"""
from __future__ import annotations

import copy
import errno
import fcntl
import json
import math
import multiprocessing
import os
import shutil
import stat
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

from hldspec import speckit_invocation_audit as audit
from hldspec import run_state
from tests_v2.test_speckit_invocation_audit import (
    base_command_identity,
    base_finished,
    base_started,
    base_target_binding,
)


_REQUIRED_SLICE_B_API = (
    "DEFAULT_LOCK_TIMEOUT_SECONDS",
    "InvocationAuditError",
    "InvocationAuditCorruptionError",
    "InvocationAuditLockTimeout",
    "append_invocation_record",
)

_SLICE_B_API_AVAILABLE = all(hasattr(audit, name) for name in _REQUIRED_SLICE_B_API)


# --- fixture helpers ----------------------------------------------------------

def _unique_record(builder, **overrides):
    record = copy.deepcopy(builder())
    record["invocation_id"] = str(uuid.uuid4())
    record.update(overrides)
    return record


def _matching_pair(invocation_id=None, **common_overrides):
    invocation_id = invocation_id or str(uuid.uuid4())
    started = base_started(invocation_id=invocation_id, **common_overrides)
    finished = base_finished(invocation_id=invocation_id, **common_overrides)
    return started, finished


def _write_raw_audit_bytes(target, data):
    path = audit.resolve_invocation_audit_log_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def _serialized_line(record):
    """Serialize a known-valid record via the Slice A serializer (always available)."""
    return audit.invocation_record_json_line(record).encode("utf-8")


# Module-level so they are picklable for `multiprocessing` under `spawn`.
# Slice B symbols are referenced only inside these bodies, never at import
# time, so they are safe to define even while Slice B is absent.

def _hold_flock_worker(path_str, hold_seconds, ready):
    import fcntl

    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        ready.set()
        time.sleep(hold_seconds)
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _append_worker(target_str, record, queue):
    from hldspec import speckit_invocation_audit as audit_mod

    try:
        audit_mod.append_invocation_record(target_str, record)
        queue.put(("ok", record["invocation_id"], None))
    except Exception as exc:  # noqa: BLE001 - report every failure to the parent
        queue.put(("error", record["invocation_id"], repr(exc)))


def _append_worker_expect_error(target_str, record, error_queue):
    """Used for hang-sensitive filesystem-safety cases: run the append in a
    child process so a misbehaving open (e.g. against a FIFO) cannot hang the
    parent test process; the child is join()-ed with a timeout and terminated
    if it does not return.
    """
    from hldspec import speckit_invocation_audit as audit_mod

    try:
        audit_mod.append_invocation_record(target_str, record)
        error_queue.put(("unexpected_success", None))
    except audit_mod.InvocationAuditError as exc:
        error_queue.put(("expected_error", repr(exc)))
    except Exception as exc:  # noqa: BLE001 - surface anything unexpected too
        error_queue.put(("unexpected_error", repr(exc)))


class SliceBApiPresenceTests(unittest.TestCase):
    def test_required_public_api_present(self):
        missing = [name for name in _REQUIRED_SLICE_B_API if not hasattr(audit, name)]
        self.assertEqual([], missing, f"Slice B public API not yet implemented: {missing}")


class TimestampCalendarValidityRepairTests(unittest.TestCase):
    """Slice A repair (§9.7): shape-valid but calendar-impossible timestamps
    must be rejected. Not gated on Slice B: exercises `validate_invocation_record`
    directly, which is always available.
    """

    def test_impossible_calendar_started_at_utc_rejected(self):
        record = base_started(started_at_utc="2026-99-99T25:61:61Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_impossible_calendar_recorded_at_utc_rejected(self):
        record = base_started(recorded_at_utc="2026-99-99T25:61:61Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("recorded_at_utc" in e for e in errors))

    def test_impossible_calendar_finished_at_utc_rejected(self):
        record = base_finished(finished_at_utc="2026-99-99T25:61:61Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("finished_at_utc" in e for e in errors))

    def test_month_13_rejected(self):
        record = base_started(started_at_utc="2026-13-01T00:00:00Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_hour_24_rejected(self):
        record = base_started(started_at_utc="2026-07-11T24:00:00Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_non_leap_year_feb29_rejected(self):
        record = base_started(started_at_utc="2026-02-29T12:00:00Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_leap_year_feb29_accepted(self):
        record = base_started(started_at_utc="2028-02-29T12:00:00Z")
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_missing_z_suffix_still_rejected_by_shape(self):
        # Regression guard: the calendar check must not replace the shape/Z
        # check. `datetime.fromisoformat` alone would accept "+00:00".
        record = base_started(started_at_utc="2026-07-11T18:00:00+00:00")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_fractional_seconds_still_accepted(self):
        record = base_started(started_at_utc="2026-07-11T18:00:00.123456Z")
        self.assertEqual([], audit.validate_invocation_record(record))


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class _TempTargetTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="hldspec-audit-writer-test-")
        self.target = Path(self._tmp) / "target"
        self.target.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self._tmp, ignore_errors=True)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class ApiArgumentTests(_TempTargetTestCase):
    def test_error_classes_are_related(self):
        self.assertTrue(issubclass(audit.InvocationAuditCorruptionError, audit.InvocationAuditError))
        self.assertTrue(issubclass(audit.InvocationAuditLockTimeout, audit.InvocationAuditError))

    def test_default_timeout_is_positive_and_finite(self):
        timeout = audit.DEFAULT_LOCK_TIMEOUT_SECONDS
        self.assertIsInstance(timeout, (int, float))
        self.assertNotIsInstance(timeout, bool)
        self.assertGreater(timeout, 0)
        self.assertTrue(math.isfinite(timeout))

    def test_invalid_record_creates_no_audit_directory_or_file(self):
        # §9.1: invalid caller record/schema is a caller-input error (ValueError),
        # not an operational InvocationAuditError -- it must never be produced by
        # attempting (and failing) some filesystem operation.
        with self.assertRaises(ValueError):
            audit.append_invocation_record(self.target, {})
        self.assertFalse((self.target / ".hldspec").exists())

    def test_invalid_record_is_not_operational_error(self):
        with self.assertRaises(ValueError) as ctx:
            audit.append_invocation_record(self.target, {})
        self.assertNotIsInstance(ctx.exception, audit.InvocationAuditError)

    def test_invalid_timeout_values_rejected_and_create_nothing(self):
        # §9.1/§13: invalid `lock_timeout_seconds` is caller-input (ValueError),
        # checked before any filesystem mutation.
        invalid_timeouts = (True, False, 0, -1, float("nan"), float("inf"), float("-inf"))
        for bad_timeout in invalid_timeouts:
            with self.subTest(timeout=bad_timeout):
                record = _unique_record(base_started)
                with self.assertRaises(ValueError):
                    audit.append_invocation_record(
                        self.target, record, lock_timeout_seconds=bad_timeout
                    )
                self.assertFalse((self.target / ".hldspec").exists())

    def test_invalid_timeout_is_not_operational_error(self):
        record = _unique_record(base_started)
        with self.assertRaises(ValueError) as ctx:
            audit.append_invocation_record(self.target, record, lock_timeout_seconds=0)
        self.assertNotIsInstance(ctx.exception, audit.InvocationAuditError)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class BasicAppendBehaviorTests(_TempTargetTestCase):
    def test_first_started_append_creates_canonical_file(self):
        record = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record)
        self.assertEqual(audit.resolve_invocation_audit_log_path(self.target), path)
        self.assertTrue(path.is_file())

    def test_first_file_bytes_match_deterministic_serialization(self):
        record = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record)
        expected = audit.invocation_record_json_line(record).encode("utf-8")
        self.assertEqual(expected, path.read_bytes())

    def test_second_append_preserves_first_record_byte_for_byte(self):
        record1 = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record1)
        first_bytes = path.read_bytes()

        record2 = _unique_record(base_started)
        audit.append_invocation_record(self.target, record2)
        combined = path.read_bytes()

        self.assertTrue(combined.startswith(first_bytes))
        expected_line2 = audit.invocation_record_json_line(record2).encode("utf-8")
        self.assertEqual(first_bytes + expected_line2, combined)

    def test_started_finished_pair_produces_exactly_two_lines(self):
        started, finished = _matching_pair()
        path = audit.append_invocation_record(self.target, started)
        audit.append_invocation_record(self.target, finished)

        content = path.read_bytes()
        self.assertTrue(content.endswith(b"\n"))
        self.assertNotIn(b"\n\n", content)
        lines = content.decode("utf-8").splitlines()
        self.assertEqual(2, len(lines))
        for line in lines:
            parsed = _parse_ndjson_line(line)
            self.assertEqual([], audit.validate_invocation_record(parsed))

    def test_normal_target_placement(self):
        record = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record)
        self.assertEqual(
            self.target / ".hldspec" / "audit" / "speckit_invocations.jsonl", path
        )

    def test_external_controller_placement(self):
        controller_root = Path(self._tmp) / "controller"
        controller_root.mkdir()
        run_state.write_pointer(
            self.target,
            controller_root=controller_root,
            source=self.target,
            source_hash="0" * 64,
            mode="external",
            agent="test",
            workflow_trigger="test",
            created_or_updated_at="2026-07-11T00:00:00Z",
        )
        record = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record)
        # `run_state.write_pointer` stores `controller_root.resolve()`; on
        # macOS `/tmp`/`/var` are themselves symlinks, so the expected path
        # must be resolved the same way to compare equal.
        self.assertEqual(
            controller_root.resolve() / ".hldspec" / "audit" / "speckit_invocations.jsonl",
            path,
        )
        self.assertTrue(path.is_file())
        self.assertFalse(
            (self.target / ".hldspec" / "audit" / "speckit_invocations.jsonl").exists()
        )

    def test_valid_unmatched_started_remains_accepted(self):
        record = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record)
        lines = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(1, len(lines))


def _parse_ndjson_line(line):
    return json.loads(line)


_CORRUPTION_CASES = {
    "invalid_utf8": b"\xff\xfe\x00\x01\n",
    "blank_line": b"\n",
    "malformed_json": b'{"schema_version": }\n',
    "json_scalar": b"42\n",
    "json_array": b"[1, 2, 3]\n",
    "duplicate_top_level_key": b'{"schema_version":1,"schema_version":2}\n',
    "duplicate_nested_key": (
        b'{"schema_version":1,"record_type":"STARTED",'
        b'"target_binding":{"feature_id":"F-001","feature_id":"F-002"}}\n'
    ),
    "nan_literal": b'{"schema_version": NaN}\n',
    "positive_infinity": b'{"schema_version": Infinity}\n',
    "negative_infinity": b'{"schema_version": -Infinity}\n',
    "schema_invalid_record": b"{}\n",
}


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class ExistingHistoryCorruptionTests(_TempTargetTestCase):
    def test_corrupt_history_rejected_and_preserved(self):
        cases = dict(_CORRUPTION_CASES)
        cases["missing_final_newline"] = audit.invocation_record_json_line(
            base_started()
        ).encode("utf-8")[:-1]

        for name, raw_bytes in cases.items():
            with self.subTest(case=name):
                tmp = tempfile.mkdtemp(prefix="hldspec-audit-corrupt-")
                try:
                    target = Path(tmp) / "target"
                    target.mkdir(parents=True)
                    path = _write_raw_audit_bytes(target, raw_bytes)
                    record = _unique_record(base_started)
                    with self.assertRaises(audit.InvocationAuditCorruptionError):
                        audit.append_invocation_record(target, record)
                    self.assertEqual(raw_bytes, path.read_bytes())
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class ExistingLifecycleCorruptionTests(_TempTargetTestCase):
    """§9.6: lifecycle violations already present in existing (schema-valid,
    individually well-formed) history must raise InvocationAuditCorruptionError,
    distinct from a lifecycle violation introduced only by the new record
    (covered in `LifecycleBehaviorTests`, which raises generic InvocationAuditError).
    """

    def test_orphan_finished_in_existing_history_is_corruption(self):
        _, finished = _matching_pair()
        _write_raw_audit_bytes(self.target, _serialized_line(finished))
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)

    def test_duplicate_started_in_existing_history_is_corruption(self):
        started, _ = _matching_pair()
        raw = _serialized_line(started) + _serialized_line(started)
        _write_raw_audit_bytes(self.target, raw)
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)

    def test_duplicate_finished_in_existing_history_is_corruption(self):
        started, finished = _matching_pair()
        raw = _serialized_line(started) + _serialized_line(finished) + _serialized_line(finished)
        _write_raw_audit_bytes(self.target, raw)
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)

    def test_incompatible_started_finished_identity_in_existing_history_is_corruption(self):
        invocation_id = str(uuid.uuid4())
        started = base_started(invocation_id=invocation_id)
        finished = base_finished(
            invocation_id=invocation_id,
            phase="CLARIFY",
            skill="speckit-clarify",
        )
        raw = _serialized_line(started) + _serialized_line(finished)
        _write_raw_audit_bytes(self.target, raw)
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)

    def test_finished_before_started_in_existing_history_is_corruption(self):
        invocation_id = str(uuid.uuid4())
        started = base_started(
            invocation_id=invocation_id, started_at_utc="2026-07-11T18:10:00Z"
        )
        finished = base_finished(
            invocation_id=invocation_id, finished_at_utc="2026-07-11T18:00:00Z"
        )
        raw = _serialized_line(started) + _serialized_line(finished)
        _write_raw_audit_bytes(self.target, raw)
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)

    def test_existing_corruption_preserves_file_unchanged(self):
        _, finished = _matching_pair()
        raw = _serialized_line(finished)
        path = _write_raw_audit_bytes(self.target, raw)
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)
        self.assertEqual(raw, path.read_bytes())


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class LifecycleBehaviorTests(_TempTargetTestCase):
    def test_finished_without_prior_started_rejected(self):
        _, finished = _matching_pair()
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, finished)

    def test_duplicate_started_rejected(self):
        started, _ = _matching_pair()
        audit.append_invocation_record(self.target, started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, copy.deepcopy(started))

    def test_duplicate_finished_rejected(self):
        started, finished = _matching_pair()
        audit.append_invocation_record(self.target, started)
        audit.append_invocation_record(self.target, finished)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, copy.deepcopy(finished))

    def test_pair_identity_mismatch_rejected(self):
        started, base = _matching_pair()
        audit.append_invocation_record(self.target, started)

        mismatches = {
            "phase_or_skill": {"phase": "CLARIFY", "skill": "speckit-clarify"},
            "model": {
                "model": "opus",
                "command_identity": base_command_identity(
                    argv_without_prompt=[
                        "claude", "--print", "--dangerously-skip-permissions",
                        "--model", "opus",
                    ]
                ),
            },
            "target_binding": {
                "target_binding": base_target_binding(feature_id="F-002")
            },
            "command_identity": {
                "command_identity": base_command_identity(prompt_sha256="1" * 64)
            },
            "approval_ref": {"approval_ref": "approval-999"},
        }
        for label, overrides in mismatches.items():
            with self.subTest(field=label):
                mismatched = copy.deepcopy(base)
                mismatched.update(overrides)
                with self.assertRaises(audit.InvocationAuditError):
                    audit.append_invocation_record(self.target, mismatched)

    def test_finished_timestamp_before_started_rejected(self):
        # Mutate started_at_utc directly on `started` only: passing it through
        # `_matching_pair`'s common_overrides would also reach `base_finished`,
        # which re-adds the STARTED-only field to `finished` via its trailing
        # `record.update(overrides)` and makes the append fail on an unrelated
        # schema violation instead of the timestamp-ordering check under test.
        started, finished = _matching_pair()
        started["started_at_utc"] = "2026-07-11T18:10:00Z"
        finished["finished_at_utc"] = "2026-07-11T18:00:00Z"
        audit.append_invocation_record(self.target, started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, finished)

    def test_matching_pair_accepted(self):
        started, finished = _matching_pair()
        audit.append_invocation_record(self.target, started)
        audit.append_invocation_record(self.target, finished)
        path = audit.resolve_invocation_audit_log_path(self.target)
        self.assertEqual(2, len(path.read_text(encoding="utf-8").splitlines()))

    def test_unrelated_invocation_ids_need_not_be_timestamp_ordered(self):
        # Same direct-mutation reasoning as test_finished_timestamp_before_started_rejected.
        started_a, finished_a = _matching_pair()
        started_a["started_at_utc"] = "2026-07-11T18:10:00Z"
        finished_a["finished_at_utc"] = "2026-07-11T18:10:05Z"
        started_b, finished_b = _matching_pair()
        started_b["started_at_utc"] = "2026-07-11T18:00:00Z"
        finished_b["finished_at_utc"] = "2026-07-11T18:00:05Z"

        audit.append_invocation_record(self.target, started_a)
        audit.append_invocation_record(self.target, finished_a)
        audit.append_invocation_record(self.target, started_b)
        audit.append_invocation_record(self.target, finished_b)

        path = audit.resolve_invocation_audit_log_path(self.target)
        self.assertEqual(4, len(path.read_text(encoding="utf-8").splitlines()))

    def test_rejected_append_leaves_previous_file_unchanged(self):
        started, _ = _matching_pair()
        path = audit.append_invocation_record(self.target, started)
        before = path.read_bytes()
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, copy.deepcopy(started))
        self.assertEqual(before, path.read_bytes())

    def test_new_record_lifecycle_violation_is_not_corruption(self):
        # §9.6: a violation introduced only by the new record is the generic
        # operational error, not the existing-history corruption class.
        _, finished = _matching_pair()
        with self.assertRaises(audit.InvocationAuditError) as ctx:
            audit.append_invocation_record(self.target, finished)
        self.assertNotIsInstance(ctx.exception, audit.InvocationAuditCorruptionError)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class LockingConcurrencyTests(_TempTargetTestCase):
    def test_lock_timeout_from_external_holder(self):
        log_path = audit.resolve_invocation_audit_log_path(self.target)
        ready = multiprocessing.Event()
        holder = multiprocessing.Process(
            target=_hold_flock_worker, args=(str(log_path), 2.0, ready)
        )
        holder.start()
        try:
            self.assertTrue(ready.wait(timeout=5), "lock holder did not signal ready")
            record = _unique_record(base_started)
            start = time.monotonic()
            with self.assertRaises(audit.InvocationAuditLockTimeout):
                audit.append_invocation_record(
                    self.target, record, lock_timeout_seconds=0.3
                )
            self.assertLess(time.monotonic() - start, 2.0)
        finally:
            holder.join(timeout=5)
            if holder.is_alive():
                holder.terminate()
                holder.join(timeout=5)

    def test_concurrent_unique_appends_produce_clean_log(self):
        # §9.2: bounded deterministic result collection instead of queue.empty(),
        # which races against workers still enqueuing their result.
        n = 5
        records = [_unique_record(base_started) for _ in range(n)]
        queue = multiprocessing.Queue()
        procs = [
            multiprocessing.Process(
                target=_append_worker, args=(str(self.target), record, queue)
            )
            for record in records
        ]
        try:
            for proc in procs:
                proc.start()

            results = [queue.get(timeout=15) for _ in range(n)]

            for proc in procs:
                proc.join(timeout=15)

            for proc in procs:
                self.assertFalse(proc.is_alive(), "worker process did not terminate")
                self.assertEqual(0, proc.exitcode, "worker process exited non-zero")

            self.assertTrue(queue.empty(), "worker(s) produced more results than expected")

            errors = [r for r in results if r[0] == "error"]
            self.assertEqual([], errors)
            self.assertEqual(n, len(results))

            path = audit.resolve_invocation_audit_log_path(self.target)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(n, len(lines))

            seen_ids = set()
            for line in lines:
                parsed = _parse_ndjson_line(line)
                self.assertEqual([], audit.validate_invocation_record(parsed))
                seen_ids.add(parsed["invocation_id"])
            self.assertEqual(n, len(seen_ids))
        finally:
            for proc in procs:
                if proc.is_alive():
                    proc.terminate()
                proc.join(timeout=5)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class FilesystemSafetyTests(_TempTargetTestCase):
    def test_audit_directory_symlink_rejected(self):
        outside = Path(self._tmp) / "outside_dir"
        outside.mkdir()
        hldspec_dir = self.target / ".hldspec"
        hldspec_dir.mkdir()
        (hldspec_dir / "audit").symlink_to(outside, target_is_directory=True)

        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, record)
        self.assertEqual([], list(outside.iterdir()))

    def test_audit_file_symlink_rejected(self):
        outside_file = Path(self._tmp) / "outside_file.jsonl"
        outside_file.write_bytes(b"")
        audit_dir = self.target / ".hldspec" / "audit"
        audit_dir.mkdir(parents=True)
        (audit_dir / "speckit_invocations.jsonl").symlink_to(outside_file)

        original = outside_file.read_bytes()
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, record)
        self.assertEqual(original, outside_file.read_bytes())

    def test_resolved_root_symlink_rejected(self):
        # The resolved root (target, or controller root in external mode) must
        # be rejected when it is itself a symlink, consistent with the
        # symlink rejection already required for `.hldspec`, `audit`, and the
        # audit file -- otherwise the writer would silently follow it and
        # write outside the validated tree.
        real_dir = Path(self._tmp) / "real_target"
        real_dir.mkdir()
        symlinked_target = Path(self._tmp) / "symlinked_target"
        symlinked_target.symlink_to(real_dir, target_is_directory=True)

        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(symlinked_target, record)
        self.assertEqual([], list(real_dir.iterdir()))

    def test_non_directory_audit_path_rejected(self):
        hldspec_dir = self.target / ".hldspec"
        hldspec_dir.mkdir()
        (hldspec_dir / "audit").write_bytes(b"not a directory")

        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, record)

    def test_non_regular_audit_file_rejected(self):
        # §9.3: run the append attempt in a child process so a non-regular
        # target (FIFO) cannot hang the parent test process even in the
        # worst case; require bounded completion and an expected error.
        if not hasattr(os, "mkfifo"):
            self.skipTest("os.mkfifo unavailable on this platform")
        audit_dir = self.target / ".hldspec" / "audit"
        audit_dir.mkdir(parents=True)
        os.mkfifo(audit_dir / "speckit_invocations.jsonl")

        record = _unique_record(base_started)
        queue = multiprocessing.Queue()
        proc = multiprocessing.Process(
            target=_append_worker_expect_error, args=(str(self.target), record, queue)
        )
        proc.start()
        try:
            proc.join(timeout=10)
            self.assertFalse(proc.is_alive(), "append against a FIFO hung the child process")
            result = queue.get_nowait()
            self.assertEqual("expected_error", result[0], result)
        finally:
            if proc.is_alive():
                proc.terminate()
                proc.join(timeout=5)

    def test_new_directory_permission_not_broader_than_0700(self):
        record = _unique_record(base_started)
        audit.append_invocation_record(self.target, record)
        audit_dir = audit.resolve_invocation_audit_log_path(self.target).parent
        mode = stat.S_IMODE(audit_dir.stat().st_mode)
        self.assertEqual(0, mode & 0o077)

    def test_new_file_permission_not_broader_than_0600(self):
        record = _unique_record(base_started)
        path = audit.append_invocation_record(self.target, record)
        mode = stat.S_IMODE(path.stat().st_mode)
        self.assertEqual(0, mode & 0o077)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class NoRepairBehaviorTests(_TempTargetTestCase):
    def test_partial_final_record_not_truncated(self):
        valid_line = audit.invocation_record_json_line(base_started()).encode("utf-8")
        partial = valid_line + b'{"schema_versio'
        path = _write_raw_audit_bytes(self.target, partial)

        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)
        self.assertEqual(partial, path.read_bytes())

    def test_no_extra_files_created_on_rejection(self):
        path = _write_raw_audit_bytes(self.target, b"not json\n")
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)
        siblings = sorted(p.name for p in path.parent.iterdir())
        self.assertEqual([path.name], siblings)


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class ErrorMetadataAndPrivacyTests(_TempTargetTestCase):
    """§9.5: operational errors expose bounded structured data where known,
    and never leak raw record/prompt/stdout content.
    """

    def test_corruption_error_exposes_bounded_metadata(self):
        _write_raw_audit_bytes(self.target, b"not json\n")
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError) as ctx:
            audit.append_invocation_record(self.target, record)
        exc = ctx.exception
        self.assertIsNotNone(exc.path)
        self.assertEqual(1, exc.line_number)
        self.assertIsNotNone(exc.reason)

    def test_lock_timeout_exposes_bounded_metadata(self):
        log_path = audit.resolve_invocation_audit_log_path(self.target)
        ready = multiprocessing.Event()
        holder = multiprocessing.Process(
            target=_hold_flock_worker, args=(str(log_path), 2.0, ready)
        )
        holder.start()
        try:
            self.assertTrue(ready.wait(timeout=5))
            record = _unique_record(base_started)
            with self.assertRaises(audit.InvocationAuditLockTimeout) as ctx:
                audit.append_invocation_record(
                    self.target, record, lock_timeout_seconds=0.3
                )
            exc = ctx.exception
            self.assertEqual(log_path, exc.path)
            self.assertEqual(0.3, exc.timeout_seconds)
        finally:
            holder.join(timeout=5)
            if holder.is_alive():
                holder.terminate()
                holder.join(timeout=5)

    def test_corruption_error_does_not_leak_existing_line_content(self):
        secret_marker = "SECRET-MARKER-DO-NOT-LEAK-0f3a9c"
        bad_line = ('{"phase":"' + secret_marker + '"').encode("utf-8")  # malformed: no closing brace
        _write_raw_audit_bytes(self.target, bad_line + b"\n")
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError) as ctx:
            audit.append_invocation_record(self.target, record)
        self.assertNotIn(secret_marker, str(ctx.exception))
        self.assertNotIn(secret_marker, repr(ctx.exception.reason))
        # The scrubbed message is not enough on its own: the underlying
        # decode/parse exception (UnicodeDecodeError / JSONDecodeError, whose
        # own attributes carry the raw offending text) must not be reachable
        # through Python's implicit exception chaining either -- a future
        # consumer that surfaces `__cause__`/`__context__` (default traceback
        # printing, `logging.exception`, a diagnostics/support-bundle export)
        # must not re-leak what the message/reason scrubbing already hides.
        self.assertIsNone(ctx.exception.__cause__)
        self.assertIsNone(ctx.exception.__context__)

    def test_corruption_error_from_malformed_json_does_not_chain_raw_content(self):
        secret_marker = "SECRET-MALFORMED-JSON-MARKER-b41e9a"
        bad_line = f'{{"schema_version": {secret_marker}}}'.encode("utf-8")
        _write_raw_audit_bytes(self.target, bad_line + b"\n")
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError) as ctx:
            audit.append_invocation_record(self.target, record)
        self.assertIsNone(ctx.exception.__cause__)
        self.assertIsNone(ctx.exception.__context__)
        full_traceback = "".join(
            __import__("traceback").format_exception(
                type(ctx.exception), ctx.exception, ctx.exception.__traceback__
            )
        )
        self.assertNotIn(secret_marker, full_traceback)

    def test_corruption_error_from_invalid_utf8_does_not_chain_raw_content(self):
        # The invalid bytes themselves aren't a printable "secret" (that's
        # the point of them being invalid UTF-8), but `UnicodeDecodeError`
        # retains the complete raw line in its `.object` attribute; chaining
        # would still make the full existing line reachable.
        bad_line = b"\xff\xfe\x00\x01SECRET-BYTES-MARKER"
        _write_raw_audit_bytes(self.target, bad_line + b"\n")
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError) as ctx:
            audit.append_invocation_record(self.target, record)
        self.assertIsNone(ctx.exception.__cause__)
        self.assertIsNone(ctx.exception.__context__)

    def test_corruption_error_does_not_leak_schema_invalid_field_values(self):
        # A schema-invalid but well-formed JSON existing line: Slice A's
        # `validate_invocation_record` messages echo field values (e.g. `phase`),
        # so the corruption reason must stay generic rather than embedding them.
        secret_marker = "SECRET-PHASE-VALUE-7e21bd"
        bad_record = {"schema_version": 1, "record_type": "STARTED", "phase": secret_marker}
        raw = (json.dumps(bad_record) + "\n").encode("utf-8")
        _write_raw_audit_bytes(self.target, raw)
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError) as ctx:
            audit.append_invocation_record(self.target, record)
        self.assertNotIn(secret_marker, str(ctx.exception))

    def test_invalid_record_valueerror_does_not_dump_complete_record(self):
        record = _unique_record(base_started)
        record["prompt"] = "raw-prompt-marker-must-not-be-serialized-whole-3d81f"
        with self.assertRaises(ValueError) as ctx:
            audit.append_invocation_record(self.target, record)
        full_dump = json.dumps(record, sort_keys=True)
        self.assertNotIn(full_dump, str(ctx.exception))


@unittest.skipUnless(_SLICE_B_API_AVAILABLE, "Slice B public API is not implemented yet")
class FaultInjectionTests(_TempTargetTestCase):
    """§10: deferred CP2 fault-injection coverage. Patches private
    module-level OS calls (`os.write`, `os.fsync`) after the implementation
    architecture (single write call site, single-or-double fsync call site
    per append) was selected; never adds public test hooks.

    `mock.patch.object(audit.os, ...)` patches the process-wide `os` module
    (`audit.os is os`), not a private copy -- under `python3 -m unittest
    discover`, background machinery from earlier tests in this same file
    (`multiprocessing.Queue`'s internal feeder thread writes to an IPC pipe
    via `os.write` from a background thread) can call the patched function
    concurrently and get miscounted or have a fault injected into unrelated
    IPC, producing flaky failures that only reproduce under full-suite runs.
    Every wrapper below therefore ignores calls on a non-regular-file fd
    (pipes, sockets) before counting or injecting anything, so only the
    writer's own regular-file audit-log fd is ever affected.
    """

    @staticmethod
    def _is_regular_fd(fd):
        try:
            return stat.S_ISREG(os.fstat(fd).st_mode)
        except OSError:
            return False

    def test_short_write_completes_via_continuation(self):
        record = _unique_record(base_started)
        expected = audit.invocation_record_json_line(record).encode("utf-8")
        real_write = os.write
        calls = []

        def flaky_write(fd, data):
            if self._is_regular_fd(fd):
                calls.append(bytes(data))
                if len(calls) == 1 and len(data) > 4:
                    return real_write(fd, data[:4])  # short write: only first 4 bytes
            return real_write(fd, data)

        with mock.patch.object(audit.os, "write", side_effect=flaky_write):
            path = audit.append_invocation_record(self.target, record)
        self.assertGreater(len(calls), 1, "short write did not force a continuation call")
        self.assertEqual(expected, path.read_bytes())

    def test_interrupted_write_before_progress_is_retried(self):
        record = _unique_record(base_started)
        expected = audit.invocation_record_json_line(record).encode("utf-8")
        real_write = os.write
        state = {"raised": False}

        def flaky_write(fd, data):
            if self._is_regular_fd(fd) and not state["raised"]:
                state["raised"] = True
                raise InterruptedError()
            return real_write(fd, data)

        with mock.patch.object(audit.os, "write", side_effect=flaky_write):
            path = audit.append_invocation_record(self.target, record)
        self.assertEqual(expected, path.read_bytes())

    def test_interrupted_write_after_progress_is_not_retried(self):
        record = _unique_record(base_started)
        real_write = os.write
        calls = {"count": 0}

        def flaky_write(fd, data):
            if not self._is_regular_fd(fd):
                return real_write(fd, data)
            calls["count"] += 1
            if calls["count"] == 1:
                return real_write(fd, data[:4])  # positive partial progress
            raise InterruptedError()  # then fail: must not retry the whole record

        with mock.patch.object(audit.os, "write", side_effect=flaky_write):
            with self.assertRaises(audit.InvocationAuditError) as ctx:
                audit.append_invocation_record(self.target, record)
        self.assertNotIsInstance(ctx.exception, audit.InvocationAuditCorruptionError)
        self.assertEqual(2, calls["count"], "write was retried after partial progress")
        path = audit.resolve_invocation_audit_log_path(self.target)
        self.assertEqual(4, len(path.read_bytes()))  # partial bytes left in place, untouched

    def test_zero_byte_write_is_an_error(self):
        record = _unique_record(base_started)
        real_write = os.write

        def zero_write(fd, data):
            if self._is_regular_fd(fd):
                return 0
            return real_write(fd, data)

        with mock.patch.object(audit.os, "write", side_effect=zero_write):
            with self.assertRaises(audit.InvocationAuditError):
                audit.append_invocation_record(self.target, record)

    def test_file_fsync_failure_raises_and_does_not_retry_write(self):
        # Pre-create the file/dir structure with an unmocked append first, so
        # the mocked failure below is isolated to the (only) fsync call this
        # append performs -- the file-data fsync -- rather than also hitting
        # the directory-creation fsyncs that would otherwise run first.
        audit.append_invocation_record(self.target, _unique_record(base_started))

        record = _unique_record(base_started)
        real_write = os.write
        real_fsync = os.fsync
        write_calls = {"count": 0}

        def counting_write(fd, data):
            if self._is_regular_fd(fd):
                write_calls["count"] += 1
            return real_write(fd, data)

        def failing_fsync(fd):
            if self._is_regular_fd(fd):
                raise OSError(errno.EIO, "simulated fsync failure")
            return real_fsync(fd)

        with mock.patch.object(audit.os, "write", side_effect=counting_write), \
                mock.patch.object(audit.os, "fsync", side_effect=failing_fsync):
            with self.assertRaises(audit.InvocationAuditError) as ctx:
                audit.append_invocation_record(self.target, record)
        self.assertNotIsInstance(ctx.exception, audit.InvocationAuditCorruptionError)
        self.assertEqual(1, write_calls["count"], "write was retried after an fsync failure")

    def test_directory_fsync_failure_on_new_file_raises(self):
        # Only reachable when the audit file itself is newly created, so the
        # directory fsync (deferred until after the data fsync) actually runs.
        # Pre-create the `.hldspec`/`audit` directory chain (but not the file)
        # so the mocked failures below land on the file-data fsync (call 1,
        # allowed to succeed) and then the new-file directory-entry fsync
        # (call 2, made to fail) specifically -- not the directory *creation*
        # fsyncs, which would otherwise run first on a fully fresh target and
        # make this test pass without ever exercising the property it claims
        # to cover. Filters out non-regular, non-directory fds (e.g. IPC
        # pipes from other tests' background threads) so only fsync calls the
        # writer itself makes are counted.
        audit_log_path = audit.resolve_invocation_audit_log_path(self.target)
        audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        record = _unique_record(base_started)
        real_fsync = os.fsync
        fsync_calls = []

        def _is_relevant_fd(fd):
            try:
                mode = os.fstat(fd).st_mode
            except OSError:
                return False
            return stat.S_ISREG(mode) or stat.S_ISDIR(mode)

        def selective_fsync(fd):
            if not _is_relevant_fd(fd):
                return real_fsync(fd)
            fsync_calls.append(fd)
            if len(fsync_calls) == 1:
                return real_fsync(fd)  # let the file-data fsync succeed
            raise OSError(errno.EIO, "simulated directory fsync failure")

        with mock.patch.object(audit.os, "fsync", side_effect=selective_fsync):
            with self.assertRaises(audit.InvocationAuditError):
                audit.append_invocation_record(self.target, record)
        self.assertEqual(2, len(fsync_calls))
        # The first (file-data) fsync succeeded before the second (directory
        # entry) fsync failed: the file must exist with its data durably
        # written, even though the overall append still raised.
        expected = audit.invocation_record_json_line(record).encode("utf-8")
        self.assertEqual(expected, audit_log_path.read_bytes())

    def test_lock_released_after_scan_corruption_failure(self):
        _write_raw_audit_bytes(self.target, b"not json\n")
        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record)
        # If the lock leaked, this would time out instead of raising the
        # (unrelated) corruption error again -- prove the lock is free by
        # re-acquiring it directly with a short timeout.
        log_path = audit.resolve_invocation_audit_log_path(self.target)
        fd = os.open(str(log_path), os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def test_lock_released_after_write_failure(self):
        record = _unique_record(base_started)
        real_write = os.write

        def failing_write(fd, data):
            if self._is_regular_fd(fd):
                raise OSError(errno.EIO, "simulated write failure")
            return real_write(fd, data)

        with mock.patch.object(audit.os, "write", side_effect=failing_write):
            with self.assertRaises(audit.InvocationAuditError):
                audit.append_invocation_record(self.target, record)

        log_path = audit.resolve_invocation_audit_log_path(self.target)
        fd = os.open(str(log_path), os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def test_lock_released_after_fsync_failure(self):
        # Pre-create the file/dir structure first (see rationale in
        # `test_file_fsync_failure_raises_and_does_not_retry_write`) so the
        # audit file actually exists afterward for the lock re-acquisition
        # check below.
        audit.append_invocation_record(self.target, _unique_record(base_started))

        record = _unique_record(base_started)
        real_fsync = os.fsync

        def failing_fsync(fd):
            if self._is_regular_fd(fd):
                raise OSError(errno.EIO, "simulated fsync failure")
            return real_fsync(fd)

        with mock.patch.object(audit.os, "fsync", side_effect=failing_fsync):
            with self.assertRaises(audit.InvocationAuditError):
                audit.append_invocation_record(self.target, record)

        log_path = audit.resolve_invocation_audit_log_path(self.target)
        fd = os.open(str(log_path), os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    def test_no_fd_leak_across_repeated_failures(self):
        # Every fd the writer successfully obtains via os.open must be
        # balanced by an os.close, even on exception paths (corruption, lock
        # timeout, write failure). The writer's create-or-open strategy makes
        # an expected-to-fail `os.open(..., O_CREAT|O_EXCL)` probe when a
        # directory/file component already exists (caught as FileExistsError,
        # no fd produced) -- only count calls that actually return an fd.
        real_open = os.open
        real_close = os.close
        open_count = {"n": 0}
        close_count = {"n": 0}

        def counting_open(*args, **kwargs):
            fd = real_open(*args, **kwargs)
            open_count["n"] += 1
            return fd

        def counting_close(fd):
            close_count["n"] += 1
            return real_close(fd)

        with mock.patch.object(audit.os, "open", side_effect=counting_open), \
                mock.patch.object(audit.os, "close", side_effect=counting_close):
            # 1) corruption path
            _write_raw_audit_bytes(self.target, b"not json\n")
            with self.assertRaises(audit.InvocationAuditCorruptionError):
                audit.append_invocation_record(self.target, _unique_record(base_started))
            self.assertEqual(open_count["n"], close_count["n"], "fd leak after corruption")

            # reset to a clean target for the next failure mode
            shutil.rmtree(self.target)
            self.target.mkdir(parents=True)
            open_count["n"] = 0
            close_count["n"] = 0

            # 2) write-failure path
            def failing_write(fd, data):
                raise OSError(errno.EIO, "simulated write failure")

            with mock.patch.object(audit.os, "write", side_effect=failing_write):
                with self.assertRaises(audit.InvocationAuditError):
                    audit.append_invocation_record(self.target, _unique_record(base_started))
            self.assertEqual(open_count["n"], close_count["n"], "fd leak after write failure")

    def test_later_append_detects_prior_partial_write_as_corruption(self):
        # A partial write left on disk by one (failed) append must be detected
        # as corruption by the *next* append attempt -- not silently repaired
        # or ignored.
        record1 = _unique_record(base_started)
        real_write = os.write
        calls = {"count": 0}

        def truncating_write(fd, data):
            calls["count"] += 1
            if calls["count"] == 1:
                return real_write(fd, data[:4])  # partial progress, then fail
            raise OSError(errno.EIO, "simulated failure after partial write")

        with mock.patch.object(audit.os, "write", side_effect=truncating_write):
            with self.assertRaises(audit.InvocationAuditError):
                audit.append_invocation_record(self.target, record1)

        record2 = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditCorruptionError):
            audit.append_invocation_record(self.target, record2)


if __name__ == "__main__":
    unittest.main()
