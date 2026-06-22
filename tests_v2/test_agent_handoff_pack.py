"""Agent Handoff Pack (renamed from "mediator guidance") must be pointer-aware.

The handoff pack's control-plane artifacts (the packet and the prompt docs) and the
source-package paths it renders must resolve through the same control plane Journey 3
uses: target-local in default/no-pointer mode, under the controller when a
`.hldspec-run.json` pointer is present. Helper runtime (`.specify/source/`, `specs/`)
always stays target-local.

The ExternalMode regression lock below is the anti-drift guard: it fails if a
target-local `.hldspec/source_package/...` path ever reappears in the generated
handoff output (packet JSON or rendered docs) in external-controller mode. Do not
weaken it. It was confirmed RED against the pre-patch `write_mediator_guidance_artifacts`
(which built the adapter without `controller_root`, landing the packet in the target).
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec import agent_handoff_pack as ahp
from hldspec import hld_source_package as sp
from hldspec import run_state

_HLD = "# HLD\n\n## Intro\n\nSome requirement body text.\n"


def _build_package(target: Path) -> None:
    build = sp.build_source_package_content(
        target, _HLD, hld_source_ref=str(target / "SourceHLD.md"), layout="new"
    )
    assert build.ok, f"{build.validation.missing} {build.validation.hash_mismatches}"


class DefaultModeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-ahp-default-")
        self.root = Path(self._tmp.name).resolve()
        self.target = self.root / "target"
        self.target.mkdir()
        _build_package(self.target)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_writes_packet_and_prompts_target_local(self) -> None:
        result = ahp.write_agent_handoff_pack_artifacts(self.target)
        packet_path = self.target / ".hldspec" / "mediator" / "mediator_packet.json"
        start_path = self.target / "prompts" / "mediator" / "START_MEDIATOR.md"
        devin_path = self.target / "prompts" / "mediator" / "DEVIN_MEDIATOR_SKILL.md"
        direct_path = self.target / "prompts" / "mediator" / "CODEX_CLAUDE_MEDIATOR.md"

        self.assertTrue(packet_path.is_file())
        self.assertTrue(start_path.is_file())
        self.assertTrue(devin_path.is_file())
        self.assertTrue(direct_path.is_file())
        self.assertEqual(packet_path, result["paths"]["packet"])
        self.assertEqual([], ahp.validate_agent_handoff_packet(result["packet"]))
        self.assertEqual(
            [], ahp.validate_agent_handoff_packet(json.loads(packet_path.read_text(encoding="utf-8")))
        )

    def test_paths_resolve_target_local(self) -> None:
        packet = ahp.build_agent_handoff_packet(self.target)
        source_dir = self.target / ".hldspec" / "source_package"
        mirror_dir = self.target / ".specify" / "source"
        specs_dir = self.target / "specs"

        self.assertIn(str(source_dir / "engineering_guidelines.md"), packet["source_package_paths"])
        self.assertEqual(str(source_dir / "engineering_guidelines.md"), packet["engineering_guidance_path"])
        self.assertIn(f"{mirror_dir}/", packet["speckit_paths"])
        self.assertIn(f"{specs_dir}/", packet["speckit_paths"])
        for value in packet["slice_artifacts"].values():
            self.assertTrue(value.startswith(str(source_dir)), value)


class ExternalModeTests(unittest.TestCase):
    """Regression lock: source package follows the controller, helper runtime stays target-local."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-ahp-external-")
        self.root = Path(self._tmp.name).resolve()
        # Controller dir name deliberately avoids "target" so the negative
        # substring assertion below is meaningful.
        self.target = self.root / "workspace"
        self.controller = self.root / "controller"
        self.target.mkdir()
        self.controller.mkdir()
        source = self.target / "SourceHLD.md"
        source.write_text(_HLD, encoding="utf-8")
        run_state.write_pointer(
            self.target,
            controller_root=self.controller,
            source=source,
            source_hash="deadbeef",
            mode="external",
            agent="test",
            workflow_trigger="build_loop_ready",
            created_or_updated_at="2026-06-21T00:00:00+00:00",
        )
        # Drive the whole wired chain: build_source_package_content writes the
        # source package AND the handoff pack through the production path.
        _build_package(self.target)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_packet_written_under_controller(self) -> None:
        packet_path = self.controller / ".hldspec" / "mediator" / "mediator_packet.json"
        self.assertTrue(packet_path.is_file(), "handoff packet must live under the controller in external mode")
        self.assertEqual([], ahp.validate_agent_handoff_packet(json.loads(packet_path.read_text(encoding="utf-8"))))

    def test_no_control_plane_dir_in_target(self) -> None:
        self.assertFalse((self.target / ".hldspec" / "mediator").exists())
        self.assertFalse((self.target / ".hldspec" / "agent_handoff").exists())
        # Source package itself must not be in the target in external mode.
        self.assertFalse((self.target / ".hldspec" / "source_package").exists())
        # Prompts are a control artifact too (CONTROL_ARTIFACTS = .hldspec, prompts);
        # they must follow the controller, not leak target-local.
        self.assertFalse((self.target / "prompts" / "mediator").exists())
        self.assertTrue((self.controller / "prompts" / "mediator").exists())

    def test_no_target_local_source_package_paths_leak(self) -> None:
        packet_path = self.controller / ".hldspec" / "mediator" / "mediator_packet.json"
        prompt_dir = self.controller / "prompts" / "mediator"
        combined = packet_path.read_text(encoding="utf-8")
        for name in ("START_MEDIATOR.md", "DEVIN_MEDIATOR_SKILL.md", "CODEX_CLAUDE_MEDIATOR.md"):
            combined += (prompt_dir / name).read_text(encoding="utf-8")

        target_local_pkg = str(self.target / ".hldspec" / "source_package")
        controller_pkg = str(self.controller / ".hldspec" / "source_package")
        # The lock: no target-local control-plane source-package path may appear.
        self.assertNotIn(target_local_pkg, combined)
        # And the controller path MUST appear (proves the fix is real, not just absent).
        self.assertIn(controller_pkg, combined)

    def test_helper_runtime_stays_target_local(self) -> None:
        packet_path = self.controller / ".hldspec" / "mediator" / "mediator_packet.json"
        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        mirror_dir = self.target / ".specify" / "source"
        specs_dir = self.target / "specs"
        self.assertIn(f"{mirror_dir}/", packet["speckit_paths"])
        self.assertIn(f"{specs_dir}/", packet["speckit_paths"])


class TerminologyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-ahp-term-")
        self.root = Path(self._tmp.name).resolve()
        self.target = self.root / "target"
        self.target.mkdir()
        _build_package(self.target)
        self.packet = ahp.build_agent_handoff_packet(self.target)
        self.start = ahp.render_start_handoff_md(self.packet)
        self.devin = ahp.render_devin_handoff_md(self.packet)
        self.direct = ahp.render_direct_handoff_md(self.packet)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_new_concept_terminology_present(self) -> None:
        for text in (self.start, self.devin, self.direct):
            self.assertIn("Agent Handoff Pack", text)
            self.assertIn("Agent Handoff Packet", text)
            self.assertIn("Agent Handoff is not the Implementation Agent.", text)
            self.assertIn("Agent Handoff Pack is not approval state.", text)
            self.assertIn("Implementation Agent output is evidence only.", text)
            self.assertIn("Bridge is discovery only, not authority.", text)
            self.assertIn("User chat is authority.", text)
            self.assertIn("User chat / protected approval remains authority.", text)

    def test_does_not_title_itself_mediator_guidance(self) -> None:
        for text in (self.start, self.devin, self.direct):
            self.assertNotIn("# Journey 3 Mediator Guidance", text)
            self.assertIn("# Journey 3 Agent Handoff Pack", text)

    def test_implementation_run_section_content_locked(self) -> None:
        # Ported from the former test_mediator_guidance content lock so the
        # guidance sections cannot silently disappear in a future edit.
        for phrase in (
            "Journey 3 implementation run",
            "Read before prompting",
            "Current slice selection",
            "READY criteria",
            "NOT READY conditions",
            "Engineering Toolbox check",
            "Slice test policy check",
            "Failed-test handling",
            "Scope-expansion handling",
            "Evidence required before completion",
            "Next prompt construction",
            "Approval boundary",
            "identify current slice from implementation_slices.json",
            "do not skip earlier blocking slices",
            "required source-package artifacts are present",
            "engineering_guidelines.md was read",
            "slice_test_policy.md was read",
            "focused tests are named",
            "prior-slice regression tests are named",
            "stop conditions are named",
            "no human-owned decision is unresolved",
            "failed tests are blockers",
            "patch smallest real cause",
            "do not hide failed tests",
            "stop or reassess",
            "do not widen files, slices, feature scope, source truth, or architecture without approval",
            "Prompt ID",
            "Goal",
            "Current slice",
            "Current evidence",
            "Required action",
            "Allowed scope",
            "Forbidden scope",
            "Engineering Toolbox requirements",
            "Tests/checks to run",
            "Output required",
            "Stop condition",
            "Fallback if blocked",
            "commit requires explicit approval",
            "push requires explicit approval",
            "PR requires explicit approval",
            "destructive changes require explicit approval",
            "external effects require explicit approval",
            "the Agent Handoff Pack cannot approve completion alone",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, self.start)
        for text in (self.start, self.devin, self.direct):
            self.assertIn("HLDspec does not enforce runtime slices at runtime", text)

    def test_protected_control_contract_preserved(self) -> None:
        # These are locked across the suite + anti-drift docs; the rename must not weaken them.
        self.assertIn(
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            self.devin,
        )
        self.assertIn("`go`", self.devin)
        self.assertIn("`stop`", self.devin)
        self.assertIn("Stop now is not a valid Devin control word.", self.devin)
        self.assertIn("stop now is a direct-mode optional behavior only", self.direct)
        self.assertIn("Codex / Claude direct mediator mode", self.direct)
        self.assertNotIn("stop now is a valid Devin control word", self.devin)


class CompatShimTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-ahp-compat-")
        self.root = Path(self._tmp.name).resolve()
        self.target = self.root / "target"
        self.target.mkdir()
        _build_package(self.target)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_old_import_path_and_names_alias_new(self) -> None:
        from hldspec import mediator_guidance as mg

        self.assertIs(mg.build_mediator_packet, ahp.build_agent_handoff_packet)
        self.assertIs(mg.validate_mediator_packet, ahp.validate_agent_handoff_packet)
        self.assertIs(mg.write_mediator_guidance_artifacts, ahp.write_agent_handoff_pack_artifacts)
        self.assertIs(mg.render_start_mediator_md, ahp.render_start_handoff_md)
        self.assertIs(mg.render_devin_mediator_skill_md, ahp.render_devin_handoff_md)
        self.assertIs(mg.render_codex_claude_mediator_md, ahp.render_direct_handoff_md)

    def test_old_and_new_produce_identical_packet(self) -> None:
        from hldspec import mediator_guidance as mg

        new_packet = ahp.build_agent_handoff_packet(self.target)
        old_packet = mg.build_mediator_packet(self.target)
        self.assertEqual(new_packet, old_packet)
        self.assertEqual([], mg.validate_mediator_packet(old_packet))


class NoSubprocessTests(unittest.TestCase):
    def test_module_does_not_shell_out(self) -> None:
        source = Path(ahp.__file__).read_text(encoding="utf-8")
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)
        self.assertNotIn("os.popen", source)


if __name__ == "__main__":
    unittest.main()
