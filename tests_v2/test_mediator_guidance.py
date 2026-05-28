from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec import hld_source_package as sp
from hldspec import mediator_guidance as mg


class MediatorGuidanceTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-mediator-guidance-")
        self.root = Path(self._tmp.name)
        build = sp.build_source_package_content(
            self.root,
            "# HLD\n\n## Intro\n\nText.\n",
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_write_artifacts_creates_packet_and_prompts(self) -> None:
        result = mg.write_mediator_guidance_artifacts(self.root)
        packet_path = self.root / ".hldspec" / "mediator" / "mediator_packet.json"
        start_path = self.root / "prompts" / "mediator" / "START_MEDIATOR.md"
        devin_path = self.root / "prompts" / "mediator" / "DEVIN_MEDIATOR_SKILL.md"
        direct_path = self.root / "prompts" / "mediator" / "CODEX_CLAUDE_MEDIATOR.md"

        self.assertTrue(packet_path.is_file())
        self.assertTrue(start_path.is_file())
        self.assertTrue(devin_path.is_file())
        self.assertTrue(direct_path.is_file())
        self.assertEqual(packet_path, result["paths"]["packet"])
        self.assertEqual([], mg.validate_mediator_packet(result["packet"]))
        self.assertEqual([], mg.validate_mediator_packet(json.loads(packet_path.read_text(encoding="utf-8"))))

    def test_packet_validates_and_missing_fields_fail(self) -> None:
        packet = mg.build_mediator_packet(self.root)
        self.assertEqual([], mg.validate_mediator_packet(packet))

        for field in mg.REQUIRED_PACKET_FIELDS:
            with self.subTest(field=field):
                broken = dict(packet)
                broken.pop(field)
                errors = mg.validate_mediator_packet(broken)
                self.assertTrue(any(field in error for error in errors), msg=errors)

    def test_rendered_prompts_preserve_journey3_boundaries(self) -> None:
        packet = mg.build_mediator_packet(self.root)
        start = mg.render_start_mediator_md(packet)
        devin = mg.render_devin_mediator_skill_md(packet)
        direct = mg.render_codex_claude_mediator_md(packet)

        for text in (start, devin, direct):
            with self.subTest(text="shared"):
                self.assertIn("go", text)
                self.assertIn("stop", text)
                self.assertIn("stop now", text)
                self.assertIn("clarify", text)
                self.assertIn("rerun tests", text)
                self.assertIn("reassess", text)
                self.assertIn("Agent Mediator is not the Implementation Agent", text)
                self.assertIn("tmux/session output is visibility only, not approval state", text)
                self.assertIn("missing evidence is not pass", text.lower())
                self.assertIn("scope expansion requires stop or reassess", text.lower())
                self.assertNotIn("hard-enforces runtime slices", text)

        self.assertIn("create agent on {path} as {session-name} using model {model} [permission-mode {mode}]", devin)
        self.assertIn("Devin mediator skill", devin)
        self.assertIn("target/.hldspec/source_package/engineering_guidelines.md", devin)
        self.assertIn("target/.hldspec/source_package/implementation_slices.json", devin)
        self.assertIn("target/.hldspec/source_package/slice_test_policy.md", devin)
        self.assertIn("target/.hldspec/source_package/speckit_slice_execution_prompt.md", devin)

        self.assertIn("Codex / Claude direct mediator mode", direct)
        self.assertIn("User != Agent Mediator != Implementation Agent", direct)
        self.assertIn("target/.hldspec/source_package/engineering_guidelines.md", direct)
        self.assertIn("target/.hldspec/source_package/implementation_slices.json", direct)
        self.assertIn("target/.hldspec/source_package/slice_test_policy.md", direct)
        self.assertIn("target/.hldspec/source_package/speckit_slice_execution_prompt.md", direct)

        self.assertIn("HLDspec does not enforce runtime slices at runtime", start)
        self.assertIn("HLDspec does not enforce runtime slices at runtime", devin)
        self.assertIn("HLDspec does not enforce runtime slices at runtime", direct)

        self.assertIn("target/.hldspec/source_package/engineering_guidelines.md", start)
        self.assertIn("target/.hldspec/source_package/implementation_slices.json", start)
        self.assertIn("target/.hldspec/source_package/slice_test_policy.md", start)
        self.assertIn("target/.hldspec/source_package/speckit_slice_execution_prompt.md", start)


if __name__ == "__main__":
    unittest.main()
