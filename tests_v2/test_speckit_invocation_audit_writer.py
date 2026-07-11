"""RED contract tests for Slice B: the durable append writer.

Slice A (`hldspec/speckit_invocation_audit.py`, done) provides the canonical
path helper and closed schema-version-1 validator/serializer. This file
specifies the still-unimplemented Slice B public surface: an exclusive-lock
append writer with corruption detection and lifecycle-pair enforcement, per
`docs/SPECKIT_INVOCATION_AUDIT_LOG_CONTRACT.md` Sections 3, 4, 6, 7.

Until Slice B lands, only `SliceBApiPresenceTests` runs; every behavioral
class below is collected but skipped (`_SLICE_B_API_AVAILABLE` is False) so
this suite is genuinely RED for exactly one reason: the required public names
are absent from `hldspec.speckit_invocation_audit`.

Deliberately deferred to CP2 (not covered here; do not treat their absence as
a gap in this file):
- short write handling
- interrupted write handling where applicable
- file fsync failure
- directory fsync failure
- lock release after scan/write/fsync exceptions
- file-descriptor cleanup
- partial-write aftermath detection beyond the black-box case tested here
- symlink race review against the selected open strategy
"""
from __future__ import annotations

import copy
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


class SliceBApiPresenceTests(unittest.TestCase):
    def test_required_public_api_present(self):
        missing = [name for name in _REQUIRED_SLICE_B_API if not hasattr(audit, name)]
        self.assertEqual([], missing, f"Slice B public API not yet implemented: {missing}")


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
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, {})
        self.assertFalse((self.target / ".hldspec").exists())

    def test_invalid_timeout_values_rejected_and_create_nothing(self):
        invalid_timeouts = (True, False, 0, -1, float("nan"), float("inf"), float("-inf"))
        for bad_timeout in invalid_timeouts:
            with self.subTest(timeout=bad_timeout):
                record = _unique_record(base_started)
                with self.assertRaises(audit.InvocationAuditError):
                    audit.append_invocation_record(
                        self.target, record, lock_timeout_seconds=bad_timeout
                    )
                self.assertFalse((self.target / ".hldspec").exists())


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
        self.assertEqual(
            controller_root / ".hldspec" / "audit" / "speckit_invocations.jsonl", path
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
    import json

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
            for proc in procs:
                proc.join(timeout=15)

            results = []
            while not queue.empty():
                results.append(queue.get_nowait())

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

    def test_non_directory_audit_path_rejected(self):
        hldspec_dir = self.target / ".hldspec"
        hldspec_dir.mkdir()
        (hldspec_dir / "audit").write_bytes(b"not a directory")

        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, record)

    def test_non_regular_audit_file_rejected(self):
        if not hasattr(os, "mkfifo"):
            self.skipTest("os.mkfifo unavailable on this platform")
        audit_dir = self.target / ".hldspec" / "audit"
        audit_dir.mkdir(parents=True)
        os.mkfifo(audit_dir / "speckit_invocations.jsonl")

        record = _unique_record(base_started)
        with self.assertRaises(audit.InvocationAuditError):
            audit.append_invocation_record(self.target, record)

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


if __name__ == "__main__":
    unittest.main()
