"""Session descriptor fields + receipt-template guidance must be pointer-aware.

PR #33 routed the *executable* role commands through the pointer-aware resolver
(`hld_source_package.source_package_paths`) so they point at the controller packet
path in external mode. The non-executable descriptor fields (`packet_file`,
`prompt_file`) and the Context Receipt required-read checklist still hardcoded
target-relative `.hldspec/source_package/...`, which does not exist in the target in
external mode. This closes that follow-up: descriptors and the receipt checklist's
source-package lines resolve under the same resolved source-package dir.

Boundary preserved (the resolver's Option C contract): the SpecKit mirror always
lives in the target, so the `.specify/memory/constitution.md` checklist line stays
target-relative even in external mode — only `.hldspec/source_package/...` moves.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import hld_source_package, run_state
from hldspec import session_control as sc

_SOURCE_PKG_PROMPTS = {
    sc.BASEPACK: "speckit_runbook.md",
    sc.RUNNER: "runner_prompt.md",
    sc.CONSULTANT: "consultant_prompt.md",
}
_ROLE_PACKET = {
    sc.BASEPACK: "basepack_packet.md",
    sc.RUNNER: "runner_packet.md",
    sc.CONSULTANT: "consultant_packet.md",
}


def _write_pointer(target: Path, controller: Path) -> None:
    (controller / ".hldspec").mkdir(parents=True, exist_ok=True)
    source = target / "HLD.md"
    source.write_text("# HLD\n", encoding="utf-8")
    run_state.write_pointer(
        target,
        controller_root=controller,
        source=source,
        source_hash="deadbeef",
        mode="external",
        agent="test",
        workflow_trigger="build_loop_ready",
        created_or_updated_at="2026-06-21T00:00:00+00:00",
    )


class SessionDescriptorFieldTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-descfields-")
        self.root = Path(self._tmp.name).resolve()  # immune to /var -> /private/var
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _plan(self) -> dict:
        return sc.build_session_plan(self.target, self.root / "hldspec")

    # 1. Legacy no-pointer: descriptor fields point at the in-target source package.
    def test_legacy_descriptors_point_in_target(self) -> None:
        roles = self._plan()["roles"]
        base = f"{self.target}/.hldspec/source_package"
        for role, prompt in _SOURCE_PKG_PROMPTS.items():
            self.assertEqual(roles[role]["prompt_file"], f"{base}/{prompt}")
        for role, packet in _ROLE_PACKET.items():
            self.assertEqual(roles[role]["packet_file"], f"{base}/subagent_packets/{packet}")

    # 2. HEADLINE — external mode: descriptor fields point at the controller.
    def test_external_descriptors_point_to_controller(self) -> None:
        _write_pointer(self.target, self.controller)
        roles = self._plan()["roles"]
        base = f"{self.controller}/.hldspec/source_package"
        for role, prompt in _SOURCE_PKG_PROMPTS.items():
            self.assertEqual(roles[role]["prompt_file"], f"{base}/{prompt}")
        for role, packet in _ROLE_PACKET.items():
            self.assertEqual(roles[role]["packet_file"], f"{base}/subagent_packets/{packet}")

    # 3. External mode: descriptor fields must NOT reference the in-target source package.
    def test_external_descriptors_do_not_reference_in_target(self) -> None:
        _write_pointer(self.target, self.controller)
        roles = self._plan()["roles"]
        in_target = f"{self.target}/.hldspec/source_package"
        for role in _SOURCE_PKG_PROMPTS:
            self.assertNotIn(in_target, roles[role]["prompt_file"], f"prompt_file role={role}")
        for role in _ROLE_PACKET:
            self.assertNotIn(in_target, roles[role]["packet_file"], f"packet_file role={role}")

    # 4/7. Descriptor paths agree with where write_session_artifacts writes.
    def test_descriptors_match_written_artifacts(self) -> None:
        _write_pointer(self.target, self.controller)
        plan = self._plan()
        written = sc.write_session_artifacts(self.target, plan)
        roles = plan["roles"]
        for role, packet in _ROLE_PACKET.items():
            self.assertEqual(roles[role]["packet_file"], str(written[packet]))
        self.assertEqual(roles[sc.RUNNER]["prompt_file"], str(written["runner_prompt.md"]))
        self.assertEqual(roles[sc.CONSULTANT]["prompt_file"], str(written["consultant_prompt.md"]))
        self.assertEqual(roles[sc.BASEPACK]["prompt_file"], str(written["speckit_runbook.md"]))

    # 9. Deterministic / idempotent rendering.
    def test_idempotent_rendering(self) -> None:
        _write_pointer(self.target, self.controller)
        a = self._plan()["roles"]
        b = self._plan()["roles"]
        self.assertEqual(
            {r: (e["prompt_file"], e["packet_file"]) for r, e in a.items()},
            {r: (e["prompt_file"], e["packet_file"]) for r, e in b.items()},
        )


class ReceiptTemplateGuidanceTests(unittest.TestCase):
    """The Context Receipt required-read checklist embedded in the written prompts
    must point operators at the resolved source package, while keeping the SpecKit
    mirror line (`.specify/...`) target-relative."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-receipt-")
        self.root = Path(self._tmp.name).resolve()
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _written_prompts(self) -> tuple[str, str]:
        plan = sc.build_session_plan(self.target, self.root / "hldspec")
        written = sc.write_session_artifacts(self.target, plan)
        runner = written["runner_prompt.md"].read_text(encoding="utf-8")
        consultant = written["consultant_prompt.md"].read_text(encoding="utf-8")
        return runner, consultant

    # Legacy renderer default is byte-identical to the relative checklist shape.
    def test_default_template_is_relative(self) -> None:
        self.assertEqual(sc.render_context_receipt_template(), sc.CONTEXT_RECEIPT_TEMPLATE)
        self.assertIn(".hldspec/source_package/source_package.json", sc.CONTEXT_RECEIPT_TEMPLATE)

    # External mode: source-package checklist lines resolve under the controller.
    def test_external_checklist_points_to_controller(self) -> None:
        _write_pointer(self.target, self.controller)
        ctrl = f"{self.controller}/.hldspec/source_package"
        for prompt in self._written_prompts():
            self.assertIn(f"{ctrl}/source_package.json", prompt)
            self.assertIn(f"{ctrl}/session_plan.json", prompt)
            self.assertNotIn(f"{self.target}/.hldspec/source_package", prompt)
            self.assertNotIn("[ ] .hldspec/source_package/", prompt)

    # External mode: the SpecKit mirror line stays target-relative (Option C boundary).
    def test_external_specify_line_stays_target_relative(self) -> None:
        _write_pointer(self.target, self.controller)
        for prompt in self._written_prompts():
            self.assertIn(".specify/memory/constitution.md", prompt)
            self.assertNotIn(f"{self.controller}/.specify", prompt)

    # Legacy no-pointer: checklist points at the in-target source package.
    def test_legacy_checklist_points_in_target(self) -> None:
        target_pkg = f"{self.target}/.hldspec/source_package"
        for prompt in self._written_prompts():
            self.assertIn(f"{target_pkg}/source_package.json", prompt)
            self.assertIn(".specify/memory/constitution.md", prompt)


class MirrorReceiptTemplatePropertyTests(unittest.TestCase):
    """F1 (review finding) — characterize the materialized-mirror property.

    `runner_prompt.md` / `consultant_prompt.md` are MIRROR_FILES that embed the
    receipt template, so once it renders absolute controller source-package paths
    (external mode), those paths can land inside the target-delivered
    `.specify/source/` mirror. This is the FIRST slice with that property:
    PR #33's absolute paths live in `session_plan.json`, which is not mirrored.
    The behavior is guidance text only (no IO consumer), but it is locked here so a
    future change to the relative-vs-controller posture cannot pass silently.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-mirror-")
        self.root = Path(self._tmp.name).resolve()
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _materialize_external_mirror(self) -> Path:
        _write_pointer(self.target, self.controller)
        plan = sc.build_session_plan(self.target, self.root / "hldspec")
        sc.write_session_artifacts(self.target, plan)  # prompts -> controller source dir
        source_dir, mirror_dir = hld_source_package.source_package_paths(self.target)
        hld_source_package.materialize_specify_mirror(source_dir, mirror_dir)
        self.assertTrue(str(mirror_dir).startswith(str(self.target)), "mirror dir stays in-target")
        return mirror_dir

    # The two template-bearing prompts carry controller paths into the in-target mirror.
    def test_mirrored_prompts_carry_controller_paths(self) -> None:
        mirror_dir = self._materialize_external_mirror()
        ctrl = f"{self.controller}/.hldspec/source_package"
        for name in ("runner_prompt.md", "consultant_prompt.md"):
            text = (mirror_dir / name).read_text(encoding="utf-8")
            self.assertIn(f"{ctrl}/source_package.json", text, name)
            self.assertNotIn("[ ] .hldspec/source_package/", text, name)

    # The mirror must NOT relocate the SpecKit `.specify/` line to the controller.
    def test_mirror_keeps_specify_line_target_relative(self) -> None:
        mirror_dir = self._materialize_external_mirror()
        for name in ("runner_prompt.md", "consultant_prompt.md"):
            text = (mirror_dir / name).read_text(encoding="utf-8")
            self.assertIn(".specify/memory/constitution.md", text, name)
            self.assertNotIn(f"{self.controller}/.specify", text, name)

    # speckit_runbook.md is mirrored but does not embed the receipt template.
    def test_runbook_mirrored_without_receipt_template(self) -> None:
        mirror_dir = self._materialize_external_mirror()
        self.assertIn("speckit_runbook.md", hld_source_package.MIRROR_FILES)
        text = (mirror_dir / "speckit_runbook.md").read_text(encoding="utf-8")
        self.assertNotIn("CONTEXT RECEIPT", text)
        self.assertNotIn(f"{self.controller}/.hldspec/source_package", text)

    # session_plan.json is not a mirrored file — PR #33's paths never reach the target.
    def test_session_plan_not_mirrored(self) -> None:
        self.assertNotIn("session_plan.json", hld_source_package.MIRROR_FILES)
        mirror_dir = self._materialize_external_mirror()
        self.assertFalse((mirror_dir / "session_plan.json").exists())


if __name__ == "__main__":
    unittest.main()
