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


if __name__ == "__main__":
    unittest.main()
