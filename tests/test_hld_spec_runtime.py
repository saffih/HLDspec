from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import hld_map
import hld_spec_downstream
import hld_spec_sync


RUNTIME_HLD = '''# Runtime HLD

## HLD-001 - Target

HLD-ID: HLD-001
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: 001
HLD-RESOURCES: TBD

This section REF HLD-002 for related behavior.

## HLD-002 - Related

HLD-ID: HLD-002
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

Related context.
'''


class HldSpecRuntimeTests(unittest.TestCase):
    def test_sync_devin_uses_prompt_file(self) -> None:
        cmd = hld_spec_sync.build_agent_command(
            agent="devin",
            model="swe-1.6",
            prompt="large prompt",
            prompt_file=Path("logs/prompt.md"),
            custom_command=None,
            extra_args=[],
            stdin_prompt=False,
        )

        self.assertEqual(["devin", "--prompt-file", "logs/prompt.md", "--model", "swe-1.6"], cmd)

    def test_downstream_devin_uses_prompt_file(self) -> None:
        cmd = hld_spec_downstream.build_agent_command(
            agent="devin",
            model="swe-1.6",
            prompt="large prompt",
            prompt_file=Path("logs/prompt.md"),
            custom_command=None,
            extra_args=[],
            stdin_prompt=False,
        )

        self.assertEqual(["devin", "--prompt-file", "logs/prompt.md", "--model", "swe-1.6"], cmd)

    def test_hld_map_only_outputs_can_be_written(self) -> None:
        parsed = hld_map.parse_hld_text(RUNTIME_HLD, source_path="HLD.md")
        self.assertEqual([], parsed.validation_errors)

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            outputs = hld_map.write_hld_map_outputs(parsed, workspace)

            self.assertTrue((workspace / outputs["map"]).exists())
            self.assertTrue((workspace / outputs["index"]).exists())
            self.assertTrue((workspace / outputs["sections"]["HLD-001"]).exists())

    def test_sync_target_mode_loads_normal_ref(self) -> None:
        parsed = hld_map.parse_hld_text(RUNTIME_HLD, source_path="HLD.md")
        self.assertEqual([], parsed.validation_errors)

        with tempfile.TemporaryDirectory() as td:
            context, report = hld_spec_sync.select_hld_context(
                parsed_map=parsed,
                workspace=Path(td),
                target_hld="HLD-001",
                max_chars=0,
                max_spec_chars=1000,
            )

        loaded = {item["id"] for item in report["loaded_sections"]}
        self.assertIn("HLD-001", loaded)
        self.assertIn("HLD-002", loaded)
        self.assertIn("--- HLD SECTION HLD-002", context)

    def test_downstream_target_mode_loads_normal_ref(self) -> None:
        parsed = hld_map.parse_hld_text(RUNTIME_HLD, source_path="HLD.md")
        self.assertEqual([], parsed.validation_errors)

        context, report = hld_spec_downstream.target_hld_context(parsed, "HLD-001")

        loaded = {item["id"] for item in report["loaded_sections"]}
        self.assertIn("HLD-001", loaded)
        self.assertIn("HLD-002", loaded)
        self.assertIn("--- HLD SECTION HLD-002", context)
        self.assertEqual(["001"], report["target_specs"])

    def test_sync_staged_validation_failure_leaves_real_files_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            sync_dir = workspace / ".specify" / "sync"
            sync_dir.mkdir(parents=True)

            real_report = sync_dir / "sync_report.md"
            real_report.write_text("original\n", encoding="utf-8")

            log_path = workspace / "agent.log"
            log_path.write_text(
                "WRITE FILE: .specify/sync/sync_report.md\n"
                "CONTENT:\n"
                "changed\n",
                encoding="utf-8",
            )

            staging = hld_spec_sync.stage_write_blocks(log_path, workspace, run_id="test")
            tmp_holder = hld_spec_sync.copy_validation_workspace(workspace)
            try:
                tmp_workspace = Path(tmp_holder.name) / "workspace"
                hld_spec_sync.apply_staged_writes_to_workspace(
                    staging_workspace=workspace,
                    target_workspace=tmp_workspace,
                    staging_info=staging,
                    allow_constitution=False,
                    allow_specs=False,
                )
                staged_errors = hld_spec_sync.validate_outputs(
                    tmp_workspace,
                    require_constitution=False,
                    require_specs=False,
                )
                self.assertTrue(staged_errors)
            finally:
                tmp_holder.cleanup()

            self.assertEqual("original\n", real_report.read_text(encoding="utf-8"))
            self.assertTrue((workspace / staging["proposed_writes"]).exists())

    def test_sync_resume_invalidates_when_normal_ref_changes(self) -> None:
        original = hld_map.parse_hld_text(RUNTIME_HLD, source_path="HLD.md")
        self.assertEqual([], original.validation_errors)

        changed_hld = RUNTIME_HLD.replace("Related context.", "Changed related context.")
        changed = hld_map.parse_hld_text(changed_hld, source_path="HLD.md")
        self.assertEqual([], changed.validation_errors)

        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)

            # Simulate a completed previous target run whose prompt context loaded
            # both the target section and its normal REF section.
            state: dict[str, object] = {"sections": {}}
            sections_state = state["sections"]
            assert isinstance(sections_state, dict)
            for section_id in hld_spec_sync.target_required_section_ids(original, "HLD-001"):
                section = original.section_by_id()[section_id]
                current = hld_spec_sync.section_state(section)
                current.update(
                    {
                        "status": "done",
                        "prompt_path": "logs/hld_spec_sync/old/prompt.md",
                        "log_path": "logs/hld_spec_sync/old/agent.log",
                        "staged_output_path": None,
                    }
                )
                sections_state[section_id] = current
            hld_spec_sync.write_run_state(workspace, state)

            self.assertIn("HLD-002", hld_spec_sync.target_required_section_ids(original, "HLD-001"))
            self.assertIsNone(hld_spec_sync.resume_skip_reason(workspace, changed, "HLD-001"))


if __name__ == "__main__":
    unittest.main()
