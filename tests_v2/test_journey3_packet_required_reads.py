"""Packet `required_reads` must be pointer-aware for source-package artifacts.

PR #33 fixed executable role commands; PR #34 fixed session descriptor fields and the
receipt checklist. The subagent packet builders still embedded target-relative
`.hldspec/source_package/...` paths in their rendered `required_reads` sections, which
do not exist in the target in external/controller mode. This routes those reads through
the same resolved source-package dir (`hld_source_package.source_package_paths()`):
controller in external mode, target-local in legacy.

Scope boundary (Option C): `required_reads` are source-package *control-plane* reads and
move with the resolved dir. The `allowed_files`/`forbidden_files` scope-policy globs and
the `.specify/...` references in packet prose are NOT read-paths and stay target-relative
— asserted here so the rewrite cannot over-reach into policy/prose. The packet files
themselves are never mirrored into `.specify/source/`, so nothing here can leak a
controller path into the target mirror (the PR #34 F1 concern does not apply).
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import hld_source_package, run_state
from hldspec import session_control as sc

_SOURCE_PKG_BASENAMES = (
    "source_package.json",
    "source_manifest.json",
    "session_plan.json",
    "speckit_runbook.md",
)
_ROLE_PACKET_FILE = {
    sc.BASEPACK: "basepack_packet.md",
    sc.RUNNER: "runner_packet.md",
    sc.CONSULTANT: "consultant_packet.md",
}
_ROLE_PROMPT = {sc.RUNNER: "runner_prompt.md", sc.CONSULTANT: "consultant_prompt.md"}


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


class RequiredReadsHelperTests(unittest.TestCase):
    """The single basename list + renderer, and the byte-identical legacy default."""

    def test_default_required_reads_for_is_relative(self) -> None:
        self.assertEqual(
            sc.required_reads_for(),
            [f".hldspec/source_package/{n}" for n in _SOURCE_PKG_BASENAMES],
        )

    def test_REQUIRED_READS_constant_unchanged(self) -> None:
        # Legacy callers (test receipts, etc.) depend on the relative tuple form.
        self.assertEqual(
            sc.REQUIRED_READS,
            tuple(f".hldspec/source_package/{n}" for n in _SOURCE_PKG_BASENAMES),
        )

    def test_required_reads_for_resolves_under_prefix(self) -> None:
        base = "/ctrl/.hldspec/source_package"
        self.assertEqual(
            sc.required_reads_for(base),
            [f"{base}/{n}" for n in _SOURCE_PKG_BASENAMES],
        )

    def test_default_builders_byte_identical(self) -> None:
        # Target-agnostic default calls (all_packets, build_session_plan) unchanged.
        self.assertEqual(
            sc.build_basepack_packet().required_reads, list(sc.REQUIRED_READS)
        )
        self.assertEqual(
            sc.build_runner_packet().required_reads,
            list(sc.REQUIRED_READS) + [".hldspec/source_package/runner_prompt.md"],
        )
        self.assertEqual(
            sc.build_consultant_packet().required_reads,
            list(sc.REQUIRED_READS) + [".hldspec/source_package/consultant_prompt.md"],
        )

    def test_builders_accept_resolved_prefix(self) -> None:
        base = "/ctrl/.hldspec/source_package"
        self.assertEqual(
            sc.build_basepack_packet(source_pkg_dir=base).required_reads,
            sc.required_reads_for(base),
        )
        self.assertEqual(
            sc.build_runner_packet(source_pkg_dir=base).required_reads,
            sc.required_reads_for(base) + [f"{base}/runner_prompt.md"],
        )
        self.assertEqual(
            sc.build_consultant_packet(source_pkg_dir=base).required_reads,
            sc.required_reads_for(base) + [f"{base}/consultant_prompt.md"],
        )


class WrittenPacketRequiredReadsTests(unittest.TestCase):
    """End-to-end: rendered/written packets carry pointer-aware required reads."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-pktreads-")
        self.root = Path(self._tmp.name).resolve()  # immune to /var -> /private/var
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self) -> dict[str, Path]:
        plan = sc.build_session_plan(self.target, self.root / "hldspec")
        return sc.write_session_artifacts(self.target, plan)

    def _packet_text(self, written: dict[str, Path], role: str) -> str:
        return written[_ROLE_PACKET_FILE[role]].read_text(encoding="utf-8")

    # 1. Legacy no-pointer: required_reads point at the in-target source package.
    def test_legacy_required_reads_target_local(self) -> None:
        written = self._write()
        base = f"{self.target}/.hldspec/source_package"
        for role in _ROLE_PACKET_FILE:
            text = self._packet_text(written, role)
            for name in _SOURCE_PKG_BASENAMES:
                self.assertIn(f"- {base}/{name}", text, f"{role}:{name}")

    # 2. HEADLINE — external mode: required_reads point at the controller.
    def test_external_required_reads_controller(self) -> None:
        _write_pointer(self.target, self.controller)
        written = self._write()
        base = f"{self.controller}/.hldspec/source_package"
        for role in _ROLE_PACKET_FILE:
            text = self._packet_text(written, role)
            for name in _SOURCE_PKG_BASENAMES:
                self.assertIn(f"- {base}/{name}", text, f"{role}:{name}")
        for role, prompt in _ROLE_PROMPT.items():
            self.assertIn(f"- {base}/{prompt}", self._packet_text(written, role))

    # 3. External mode: required_reads must NOT reference the in-target source package.
    def test_external_no_in_target_source_package(self) -> None:
        _write_pointer(self.target, self.controller)
        written = self._write()
        in_target = f"{self.target}/.hldspec/source_package"
        for role in _ROLE_PACKET_FILE:
            text = self._packet_text(written, role)
            reads_block = text.split("ALLOWED FILES:")[0]  # required reads precede it
            self.assertNotIn(in_target, reads_block, role)
            self.assertNotIn("- .hldspec/source_package/", reads_block, role)

    # 4. Scope boundary: .specify prose + scope-policy globs stay target-relative
    #    (no entry in required_reads is a .specify path; the rewrite must not touch them).
    def test_specify_and_policy_paths_stay_relative(self) -> None:
        _write_pointer(self.target, self.controller)
        written = self._write()
        basepack = self._packet_text(written, sc.BASEPACK)
        # basepack prose names the derived mirror; it must remain target-relative.
        self.assertIn(".specify/source/", basepack)
        self.assertNotIn(f"{self.controller}/.specify", basepack)
        self.assertNotIn(f"{self.controller}/.hldspec/source_package/**", basepack)
        # forbidden/allowed scope-policy globs are unchanged (relative).
        self.assertIn(".specify/**", basepack)
        runner = self._packet_text(written, sc.RUNNER)
        self.assertIn(".hldspec/source_package/** (read-only for the runner)", runner)

    # 5. Required-read source-package path agrees with where the packet was written.
    def test_required_reads_agree_with_written_location(self) -> None:
        _write_pointer(self.target, self.controller)
        written = self._write()
        source_dir = written[sc.SESSION_PLAN_FILE].parent  # actual write location
        runner = self._packet_text(written, sc.RUNNER)
        self.assertIn(f"- {source_dir}/source_package.json", runner)
        self.assertIn(f"- {source_dir}/runner_prompt.md", runner)

    # F1 boundary: packet files are never mirrored, so no controller path reaches
    #    the target mirror (cleaner than the PR #34 prompt-file case).
    def test_packets_not_mirrored(self) -> None:
        _write_pointer(self.target, self.controller)
        self._write()
        source_dir, mirror_dir = hld_source_package.source_package_paths(self.target)
        hld_source_package.materialize_specify_mirror(source_dir, mirror_dir)
        for fname in _ROLE_PACKET_FILE.values():
            self.assertNotIn(fname, hld_source_package.MIRROR_FILES)
            self.assertFalse((mirror_dir / fname).exists(), fname)
            self.assertFalse((mirror_dir / "subagent_packets").exists())

    # 11. Deterministic rendering.
    def test_idempotent_rendering(self) -> None:
        _write_pointer(self.target, self.controller)
        first = self._write_packet_texts()
        second = self._write_packet_texts()
        self.assertEqual(first, second)

    def _write_packet_texts(self) -> dict[str, str]:
        written = self._write()
        return {r: self._packet_text(written, r) for r in _ROLE_PACKET_FILE}


if __name__ == "__main__":
    unittest.main()
