"""Compatibility shim coverage for the deprecated ``mediator_guidance`` name.

The implementation moved to :mod:`hldspec.agent_handoff_pack` (the Agent Handoff
Pack). ``hldspec.mediator_guidance`` remains a thin alias. The pointer-aware path
behavior and the full terminology contract are locked in
``tests_v2/test_agent_handoff_pack.py``; this file only proves the legacy import
path and legacy function names still work and still emit the protected control
contract.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec import hld_source_package as sp
from hldspec import mediator_guidance as mg


class MediatorGuidanceShimTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-mediator-shim-")
        self.root = Path(self._tmp.name).resolve()
        build = sp.build_source_package_content(
            self.root,
            "# HLD\n\n## Intro\n\nText.\n",
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_legacy_write_creates_packet_and_prompts(self) -> None:
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
        self.assertEqual(
            [], mg.validate_mediator_packet(json.loads(packet_path.read_text(encoding="utf-8")))
        )

    def test_legacy_packet_validates_and_missing_fields_fail(self) -> None:
        packet = mg.build_mediator_packet(self.root)
        self.assertEqual([], mg.validate_mediator_packet(packet))
        for field in mg.REQUIRED_PACKET_FIELDS:
            with self.subTest(field=field):
                broken = dict(packet)
                broken.pop(field)
                errors = mg.validate_mediator_packet(broken)
                self.assertTrue(any(field in error for error in errors), msg=errors)

    def test_legacy_renders_preserve_protected_contract(self) -> None:
        packet = mg.build_mediator_packet(self.root)
        start = mg.render_start_mediator_md(packet)
        devin = mg.render_devin_mediator_skill_md(packet)
        direct = mg.render_codex_claude_mediator_md(packet)

        # New concept name is present via the legacy render entrypoints.
        for text in (start, devin, direct):
            self.assertIn("Agent Handoff Pack", text)

        # Protected Devin/direct control contract survives the rename.
        self.assertIn(
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            devin,
        )
        self.assertIn("Stop now is not a valid Devin control word.", devin)
        self.assertIn("stop now is a direct-mode optional behavior only", direct)
        self.assertIn("Codex / Claude direct mediator mode", direct)
        self.assertNotIn("stop now is a valid Devin control word", devin)


if __name__ == "__main__":
    unittest.main()
