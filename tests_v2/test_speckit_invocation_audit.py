import copy
import unittest
from pathlib import Path

from hldspec import speckit_invocation_audit as audit
from hldspec import helper_registry
from hldspec import speckit_invoker


VALID_UUID = "0d1f7f3e-6c8a-4b1a-9e2d-3a5b7c9d1e2f"
HEX64_A = "a" * 64
HEX64_B = "b" * 64
HEX64_C = "c" * 64
HEX64_D = "d" * 64
HEX64_E = "e" * 64
HEX40 = "f" * 40


def base_target_binding(**overrides):
    binding = {
        "target_path_sha256": HEX64_A,
        "binding_status": "BOUND",
        "git_branch_before": "main",
        "git_head_before": HEX40,
        "remote_identity_sha256": HEX64_B,
        "source_package_sha256": HEX64_C,
        "feature_id": "F-001",
        "spec_dir": "specs/001-feature",
        "bundle_id": "bundle-1",
    }
    binding.update(overrides)
    return binding


def base_command_identity(**overrides):
    identity = {
        "agent_cmd": "claude",
        "argv_without_prompt": ["claude", "--print", "--dangerously-skip-permissions", "--model", "haiku"],
        "prompt_sha256": HEX64_D,
        "prompt_bytes": 128,
        "skip_permissions": True,
    }
    identity.update(overrides)
    return identity


def base_started(**overrides):
    record = {
        "schema_version": 1,
        "record_type": audit.RECORD_STARTED,
        "invocation_id": VALID_UUID,
        "recorded_at_utc": "2026-07-11T18:00:00Z",
        "helper_id": "speckit",
        "toolchain": "SpecKit",
        "execution_path": "speckit_invoker",
        "runtime": "claude",
        "phase": "TASKS",
        "skill": "speckit-tasks",
        "model": "haiku",
        "authority_level": helper_registry.AUTHORITY_EXECUTE_WITH_APPROVAL,
        "approval_ref": "approval-123",
        "target_binding": base_target_binding(),
        "command_identity": base_command_identity(),
        "started_at_utc": "2026-07-11T18:00:00Z",
        "git_signature_before_sha256": HEX64_E,
    }
    record.update(overrides)
    return record


def base_finished(**overrides):
    record = base_started(record_type=audit.RECORD_FINISHED)
    del record["started_at_utc"]
    del record["git_signature_before_sha256"]
    record.update(
        {
            "finished_at_utc": "2026-07-11T18:00:05Z",
            "duration_ms": 5000,
            "outcome": "SUCCESS",
            "returncode": 0,
            "ok": True,
            "produced_artifacts": True,
            "verified": True,
            "git_branch_after": "main",
            "git_head_after": HEX40,
            "git_signature_after_sha256": HEX64_E,
            "changed_paths": ["specs/001-feature/tasks.md"],
            "changed_path_count": 1,
            "changed_paths_truncated": False,
            "stdout_bytes": 100,
            "stdout_sha256": HEX64_A,
            "stderr_bytes": 0,
            "stderr_sha256": HEX64_B,
            "error_summary_redacted": None,
            "watchdog_triggered": False,
        }
    )
    record.update(overrides)
    return record


class PathResolutionTests(unittest.TestCase):
    def test_normal_target_path(self):
        path = audit.resolve_invocation_audit_log_path("/tmp/some-target")
        self.assertEqual(
            Path("/tmp/some-target/.hldspec/audit/speckit_invocations.jsonl"), path
        )

    def test_relative_path_constant(self):
        self.assertEqual(
            Path("audit/speckit_invocations.jsonl"), audit.INVOCATION_AUDIT_RELATIVE_PATH
        )

    def test_no_path_creation(self, ):
        target = Path("/tmp/hldspec-audit-path-no-create-test-dir-xyz")
        if target.exists():
            self.skipTest("scratch path unexpectedly exists")
        path = audit.resolve_invocation_audit_log_path(target)
        self.assertFalse(path.exists())
        self.assertFalse(path.parent.exists())
        self.assertFalse(target.exists())

    def test_accepts_string_or_path(self):
        p1 = audit.resolve_invocation_audit_log_path("/tmp/x")
        p2 = audit.resolve_invocation_audit_log_path(Path("/tmp/x"))
        self.assertEqual(p1, p2)


class ValidRecordTests(unittest.TestCase):
    def test_valid_started_record(self):
        self.assertEqual([], audit.validate_invocation_record(base_started()))

    def test_valid_finished_record(self):
        self.assertEqual([], audit.validate_invocation_record(base_finished()))

    def test_valid_hollow_completion_on_artifact_phase(self):
        record = base_finished(
            outcome="HOLLOW_COMPLETION",
            returncode=0,
            ok=True,
            produced_artifacts=False,
            verified=False,
        )
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_valid_non_artifact_phase_success(self):
        record = base_finished(
            phase="CLARIFY",
            skill="speckit-clarify",
            outcome="SUCCESS",
            returncode=0,
            ok=True,
            produced_artifacts=False,
            verified=True,
        )
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_valid_null_approval_ref(self):
        self.assertEqual([], audit.validate_invocation_record(base_started(approval_ref=None)))

    def test_valid_null_target_binding_optionals(self):
        record = base_started(
            target_binding=base_target_binding(
                git_branch_before=None,
                git_head_before=None,
                remote_identity_sha256=None,
                source_package_sha256=None,
                feature_id=None,
                spec_dir=None,
                bundle_id=None,
            )
        )
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_valid_reserved_drive_loop_execution_path(self):
        record = base_started(execution_path="speckit_drive_loop")
        self.assertEqual([], audit.validate_invocation_record(record))


class DeterministicSerializationTests(unittest.TestCase):
    def test_produces_single_line_ending_in_newline(self):
        line = audit.invocation_record_json_line(base_started())
        self.assertTrue(line.endswith("\n"))
        self.assertEqual(1, line.count("\n"))
        self.assertNotIn("\n", line[:-1])

    def test_deterministic_across_calls(self):
        record = base_started()
        line1 = audit.invocation_record_json_line(record)
        line2 = audit.invocation_record_json_line(copy.deepcopy(record))
        self.assertEqual(line1, line2)

    def test_sorted_keys(self):
        import json

        line = audit.invocation_record_json_line(base_started())
        obj_text = line.rstrip("\n")
        parsed = json.loads(obj_text)
        # Reconstruct with sort_keys and compare compact separators.
        expected = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        self.assertEqual(expected, obj_text)

    def test_does_not_mutate_input(self):
        record = base_started()
        original = copy.deepcopy(record)
        audit.invocation_record_json_line(record)
        self.assertEqual(original, record)

    def test_raises_valueerror_on_invalid_record(self):
        record = base_started()
        del record["helper_id"]
        with self.assertRaises(ValueError):
            audit.invocation_record_json_line(record)

    def test_no_unicode_escaping_of_valid_text(self):
        record = base_started(runtime="claude-é")
        line = audit.invocation_record_json_line(record)
        self.assertIn("é", line)


class SchemaClosureTests(unittest.TestCase):
    def test_rejects_unknown_top_level_key(self):
        record = base_started(extra_field="nope")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("extra_field" in e for e in errors))

    def test_rejects_unknown_target_binding_key(self):
        record = base_started(
            target_binding=base_target_binding(unexpected="x")
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("unexpected" in e for e in errors))

    def test_rejects_unknown_command_identity_key(self):
        record = base_started(
            command_identity=base_command_identity(unexpected="x")
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("unexpected" in e for e in errors))

    def test_started_rejects_finished_only_fields(self):
        record = base_started(outcome="SUCCESS")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("outcome" in e for e in errors))

    def test_finished_rejects_started_only_fields(self):
        record = base_finished(started_at_utc="2026-07-11T18:00:00Z")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_rejects_raw_prompt_field(self):
        record = base_started()
        record["prompt"] = "do the thing"
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("prompt" in e for e in errors))

    def test_rejects_raw_stdout_field(self):
        record = base_finished()
        record["stdout"] = "output text"
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("stdout" in e for e in errors))

    def test_missing_required_common_field(self):
        for field in (
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
        ):
            with self.subTest(field=field):
                record = base_started()
                del record[field]
                errors = audit.validate_invocation_record(record)
                self.assertTrue(any(field in e for e in errors), errors)


class TypeValidationTests(unittest.TestCase):
    def test_schema_version_bool_rejected(self):
        record = base_started(schema_version=True)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_schema_version_float_rejected(self):
        # 1.0 == 1 in Python; a plain != check would silently accept this.
        record = base_started(schema_version=1.0)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("schema_version" in e for e in errors))

    def test_returncode_bool_rejected(self):
        record = base_finished(returncode=False)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("returncode" in e for e in errors))

    def test_prompt_bytes_bool_rejected(self):
        record = base_started(
            command_identity=base_command_identity(prompt_bytes=True)
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("prompt_bytes" in e for e in errors))

    def test_duration_ms_bool_rejected(self):
        record = base_finished(duration_ms=True)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("duration_ms" in e for e in errors))

    def test_changed_path_count_bool_rejected(self):
        record = base_finished(changed_path_count=False)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_path_count" in e for e in errors))

    def test_stdout_bytes_bool_rejected(self):
        record = base_finished(stdout_bytes=True)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("stdout_bytes" in e for e in errors))

    def test_stderr_bytes_bool_rejected(self):
        record = base_finished(stderr_bytes=False)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("stderr_bytes" in e for e in errors))

    def test_negative_duration_rejected(self):
        record = base_finished(duration_ms=-1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("duration_ms" in e for e in errors))

    def test_record_type_invalid_value(self):
        record = base_started(record_type="BOGUS")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("record_type" in e for e in errors))

    def test_schema_version_not_1(self):
        record = base_started(schema_version=2)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("schema_version" in e for e in errors))


class UuidValidationTests(unittest.TestCase):
    def test_invalid_uuid_rejected(self):
        record = base_started(invocation_id="not-a-uuid")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("invocation_id" in e for e in errors))

    def test_uppercase_uuid_rejected(self):
        record = base_started(invocation_id=VALID_UUID.upper())
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("invocation_id" in e for e in errors))

    def test_braced_uuid_rejected(self):
        record = base_started(invocation_id="{" + VALID_UUID + "}")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("invocation_id" in e for e in errors))


class TimestampValidationTests(unittest.TestCase):
    def test_missing_z_suffix_rejected(self):
        record = base_started(recorded_at_utc="2026-07-11T18:00:00+00:00")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("recorded_at_utc" in e for e in errors))

    def test_invalid_timestamp_text_rejected(self):
        record = base_started(recorded_at_utc="not-a-timestamp")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("recorded_at_utc" in e for e in errors))

    def test_started_at_utc_validated(self):
        record = base_started(started_at_utc="bogus")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("started_at_utc" in e for e in errors))

    def test_finished_at_utc_validated(self):
        record = base_finished(finished_at_utc="bogus")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("finished_at_utc" in e for e in errors))


class HashValidationTests(unittest.TestCase):
    def test_invalid_hex_length_rejected(self):
        record = base_started(git_signature_before_sha256="abc123")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("git_signature_before_sha256" in e for e in errors))

    def test_uppercase_hex_rejected(self):
        record = base_started(git_signature_before_sha256=HEX64_A.upper())
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("git_signature_before_sha256" in e for e in errors))

    def test_prompt_sha256_invalid_rejected(self):
        record = base_started(
            command_identity=base_command_identity(prompt_sha256="short")
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("prompt_sha256" in e for e in errors))

    def test_stdout_sha256_invalid_rejected(self):
        record = base_finished(stdout_sha256="short")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("stdout_sha256" in e for e in errors))


class PhaseSkillConsistencyTests(unittest.TestCase):
    def test_unknown_phase_rejected(self):
        record = base_started(phase="NOT_A_PHASE", skill="speckit-tasks")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("phase" in e for e in errors))

    def test_skill_mismatch_rejected(self):
        record = base_started(phase="TASKS", skill="speckit-plan")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("skill" in e for e in errors))

    def test_all_known_phases_valid_with_matching_skill(self):
        for phase, skill in speckit_invoker.PHASE_SKILL.items():
            with self.subTest(phase=phase):
                record = base_started(phase=phase, skill=skill)
                self.assertEqual([], audit.validate_invocation_record(record))


class CommandModelConsistencyTests(unittest.TestCase):
    def test_argv_missing_model_flag_rejected(self):
        record = base_started(
            command_identity=base_command_identity(
                argv_without_prompt=["claude", "--print"]
            )
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("model" in e for e in errors))

    def test_argv_model_mismatch_rejected(self):
        record = base_started(
            model="haiku",
            command_identity=base_command_identity(
                argv_without_prompt=["claude", "--print", "--model", "opus"]
            ),
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("model" in e for e in errors))

    def test_argv_duplicate_model_flag_rejected(self):
        record = base_started(
            command_identity=base_command_identity(
                argv_without_prompt=[
                    "claude", "--print", "--model", "haiku", "--model", "haiku",
                ]
            )
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("model" in e for e in errors))

    def test_model_need_not_match_phase_default(self):
        # 3D: model is NOT required to equal PHASE_MODEL[phase]; only argv agreement matters.
        record = base_started(
            phase="TASKS",  # PHASE_MODEL["TASKS"] == "haiku"
            model="opus",
            command_identity=base_command_identity(
                argv_without_prompt=["claude", "--print", "--model", "opus"],
                skip_permissions=False,
            ),
        )
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_argv_first_item_must_equal_agent_cmd(self):
        record = base_started(
            command_identity=base_command_identity(
                agent_cmd="claude",
                argv_without_prompt=["not-claude", "--print", "--model", "haiku"],
            )
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("argv_without_prompt" in e for e in errors))

    def test_argv_containing_slash_skill_prefix_rejected(self):
        record = base_started(
            phase="TASKS",
            command_identity=base_command_identity(
                argv_without_prompt=[
                    "claude", "--print", "--model", "haiku", "/speckit-tasks do the thing",
                ]
            ),
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("argv_without_prompt" in e for e in errors))


class PermissionFlagConsistencyTests(unittest.TestCase):
    def test_flag_present_but_skip_permissions_false_rejected(self):
        record = base_started(
            command_identity=base_command_identity(
                skip_permissions=False,
                argv_without_prompt=[
                    "claude", "--print", "--dangerously-skip-permissions", "--model", "haiku",
                ],
            )
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("skip_permissions" in e for e in errors))

    def test_flag_absent_but_skip_permissions_true_rejected(self):
        record = base_started(
            command_identity=base_command_identity(
                skip_permissions=True,
                argv_without_prompt=["claude", "--print", "--model", "haiku"],
            )
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("skip_permissions" in e for e in errors))


class AuthorityLevelTests(unittest.TestCase):
    def test_unknown_authority_level_rejected(self):
        record = base_started(authority_level="BOGUS_LEVEL")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("authority_level" in e for e in errors))

    def test_forbidden_authority_level_rejected(self):
        record = base_started(
            authority_level=helper_registry.AUTHORITY_AUTONOMOUS_WITH_GUARDS
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("authority_level" in e for e in errors))

    def test_all_non_forbidden_authority_levels_accepted(self):
        for level in helper_registry.VALID_AUTHORITY_LEVELS - helper_registry.FORBIDDEN_AUTHORITY_LEVELS:
            with self.subTest(level=level):
                record = base_started(authority_level=level)
                self.assertEqual([], audit.validate_invocation_record(record))


class TargetBindingValidationTests(unittest.TestCase):
    def test_invalid_binding_status_rejected(self):
        record = base_started(target_binding=base_target_binding(binding_status="BOGUS"))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("binding_status" in e for e in errors))

    def test_target_path_sha256_wrong_length_rejected(self):
        record = base_started(target_binding=base_target_binding(target_path_sha256="short"))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("target_path_sha256" in e for e in errors))

    def test_git_branch_without_head_rejected(self):
        record = base_started(
            target_binding=base_target_binding(git_branch_before="main", git_head_before=None)
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("git_branch_before" in e or "git_head_before" in e for e in errors))

    def test_git_head_without_branch_rejected(self):
        record = base_started(
            target_binding=base_target_binding(git_branch_before=None, git_head_before=HEX40)
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("git_branch_before" in e or "git_head_before" in e for e in errors))

    def test_git_head_64_hex_also_valid(self):
        record = base_started(
            target_binding=base_target_binding(git_head_before=HEX64_A)
        )
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_git_head_bad_length_rejected(self):
        record = base_started(
            target_binding=base_target_binding(git_head_before="abc123")
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("git_head_before" in e for e in errors))

    def test_absolute_spec_dir_rejected(self):
        record = base_started(target_binding=base_target_binding(spec_dir="/etc/passwd"))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("spec_dir" in e for e in errors))

    def test_traversal_spec_dir_rejected(self):
        record = base_started(target_binding=base_target_binding(spec_dir="../../etc/passwd"))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("spec_dir" in e for e in errors))

    def test_nul_byte_spec_dir_rejected(self):
        record = base_started(target_binding=base_target_binding(spec_dir="specs/foo\x00bar"))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("spec_dir" in e for e in errors))

    def test_missing_target_binding_key(self):
        for field in (
            "target_path_sha256",
            "binding_status",
            "git_branch_before",
            "git_head_before",
            "remote_identity_sha256",
            "source_package_sha256",
            "feature_id",
            "spec_dir",
            "bundle_id",
        ):
            with self.subTest(field=field):
                binding = base_target_binding()
                del binding[field]
                record = base_started(target_binding=binding)
                errors = audit.validate_invocation_record(record)
                self.assertTrue(any(field in e for e in errors), errors)


class ChangedPathsTests(unittest.TestCase):
    def test_absolute_changed_path_rejected(self):
        record = base_finished(changed_paths=["/etc/passwd"], changed_path_count=1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths" in e for e in errors))

    def test_traversal_changed_path_rejected(self):
        record = base_finished(changed_paths=["../secret"], changed_path_count=1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths" in e for e in errors))

    def test_dot_changed_path_rejected(self):
        record = base_finished(changed_paths=["."], changed_path_count=1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths" in e for e in errors))

    def test_empty_changed_path_rejected(self):
        record = base_finished(changed_paths=[""], changed_path_count=1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths" in e for e in errors))

    def test_duplicate_changed_paths_rejected(self):
        record = base_finished(
            changed_paths=["a.md", "a.md"], changed_path_count=2
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths" in e for e in errors))

    def test_unsorted_changed_paths_rejected(self):
        record = base_finished(
            changed_paths=["b.md", "a.md"], changed_path_count=2
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths" in e for e in errors))

    def test_count_mismatch_when_not_truncated_rejected(self):
        record = base_finished(
            changed_paths=["a.md"], changed_path_count=2, changed_paths_truncated=False
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_path_count" in e for e in errors))

    def test_count_below_len_when_truncated_rejected(self):
        record = base_finished(
            changed_paths=["a.md", "b.md"], changed_path_count=1, changed_paths_truncated=True
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_path_count" in e for e in errors))

    def test_count_at_or_above_len_when_truncated_accepted(self):
        record = base_finished(
            changed_paths=["a.md", "b.md"], changed_path_count=5, changed_paths_truncated=True
        )
        self.assertEqual([], audit.validate_invocation_record(record))


class OutcomeVerifiedSemanticsTests(unittest.TestCase):
    def test_success_requires_verified_true(self):
        record = base_finished(outcome="SUCCESS", verified=False)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("verified" in e or "outcome" in e for e in errors))

    def test_command_failed_requires_nonzero_returncode(self):
        record = base_finished(
            outcome="COMMAND_FAILED", returncode=0, ok=False, produced_artifacts=False, verified=False
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("returncode" in e or "outcome" in e for e in errors))

    def test_command_failed_requires_verified_false(self):
        record = base_finished(
            outcome="COMMAND_FAILED", returncode=1, ok=False, produced_artifacts=False, verified=True
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("verified" in e or "outcome" in e for e in errors))

    def test_hollow_completion_requires_zero_returncode(self):
        record = base_finished(
            outcome="HOLLOW_COMPLETION", returncode=1, ok=True, produced_artifacts=False, verified=False
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("returncode" in e or "outcome" in e for e in errors))

    def test_hollow_completion_requires_produced_artifacts_false(self):
        record = base_finished(
            outcome="HOLLOW_COMPLETION", returncode=0, ok=True, produced_artifacts=True, verified=False
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("produced_artifacts" in e or "outcome" in e for e in errors))

    def test_hollow_completion_on_non_artifact_phase_rejected(self):
        # CLARIFY is not in ARTIFACT_PHASES; verified is always ok-driven there,
        # so a claimed HOLLOW_COMPLETION (verified=false, ok=true) is self-inconsistent.
        record = base_finished(
            phase="CLARIFY",
            skill="speckit-clarify",
            outcome="HOLLOW_COMPLETION",
            returncode=0,
            ok=True,
            produced_artifacts=False,
            verified=False,
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("verified" in e or "outcome" in e for e in errors))

    def test_ok_returncode_mismatch_rejected(self):
        record = base_finished(returncode=1, ok=True)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("ok" in e for e in errors))

    def test_invalid_outcome_value_rejected(self):
        record = base_finished(outcome="BOGUS_OUTCOME")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("outcome" in e for e in errors))


class ErrorSummaryTests(unittest.TestCase):
    def test_none_error_summary_accepted(self):
        record = base_finished(error_summary_redacted=None)
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_oversized_error_summary_rejected(self):
        record = base_finished(error_summary_redacted="x" * 1025)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("error_summary_redacted" in e for e in errors))

    def test_exactly_1024_bytes_accepted(self):
        record = base_finished(error_summary_redacted="x" * 1024)
        self.assertEqual([], audit.validate_invocation_record(record))

    def test_control_character_rejected(self):
        record = base_finished(error_summary_redacted="bad\x00text")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("error_summary_redacted" in e for e in errors))

    def test_newline_rejected(self):
        record = base_finished(error_summary_redacted="line1\nline2")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("error_summary_redacted" in e for e in errors))


class ErrorOrderingTests(unittest.TestCase):
    def test_error_order_is_deterministic(self):
        record = base_started()
        del record["helper_id"]
        del record["toolchain"]
        errors1 = audit.validate_invocation_record(record)
        errors2 = audit.validate_invocation_record(copy.deepcopy(record))
        self.assertEqual(errors1, errors2)


class ExactValueAndEmptyStringTests(unittest.TestCase):
    def test_helper_id_wrong_value_rejected(self):
        record = base_started(helper_id="not-speckit")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("helper_id" in e for e in errors))

    def test_toolchain_wrong_value_rejected(self):
        record = base_started(toolchain="NotSpecKit")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("toolchain" in e for e in errors))

    def test_execution_path_invalid_value_rejected(self):
        record = base_started(execution_path="bogus_path")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("execution_path" in e for e in errors))

    def test_runtime_empty_string_rejected(self):
        record = base_started(runtime="")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("runtime" in e for e in errors))

    def test_approval_ref_empty_string_rejected(self):
        record = base_started(approval_ref="")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("approval_ref" in e for e in errors))

    def test_feature_id_empty_string_rejected(self):
        record = base_started(target_binding=base_target_binding(feature_id=""))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("feature_id" in e for e in errors))

    def test_bundle_id_empty_string_rejected(self):
        record = base_started(target_binding=base_target_binding(bundle_id=""))
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("bundle_id" in e for e in errors))

    def test_remote_identity_sha256_malformed_rejected(self):
        record = base_started(
            target_binding=base_target_binding(remote_identity_sha256="not-hex")
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("remote_identity_sha256" in e for e in errors))

    def test_source_package_sha256_malformed_rejected(self):
        record = base_started(
            target_binding=base_target_binding(source_package_sha256="not-hex")
        )
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("source_package_sha256" in e for e in errors))

    def test_git_signature_after_sha256_malformed_rejected(self):
        record = base_finished(git_signature_after_sha256="not-hex")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("git_signature_after_sha256" in e for e in errors))

    def test_ok_non_bool_rejected(self):
        record = base_finished(ok=1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("ok" in e for e in errors))

    def test_produced_artifacts_non_bool_rejected(self):
        record = base_finished(produced_artifacts=1)
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("produced_artifacts" in e for e in errors))


class WatchdogAndBooleanFieldTests(unittest.TestCase):
    def test_watchdog_triggered_non_bool_rejected(self):
        record = base_finished(watchdog_triggered="yes")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("watchdog_triggered" in e for e in errors))

    def test_verified_non_bool_rejected(self):
        record = base_finished(verified="true")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("verified" in e for e in errors))

    def test_changed_paths_truncated_non_bool_rejected(self):
        record = base_finished(changed_paths_truncated="no")
        errors = audit.validate_invocation_record(record)
        self.assertTrue(any("changed_paths_truncated" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
