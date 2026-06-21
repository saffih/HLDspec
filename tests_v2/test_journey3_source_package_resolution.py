"""Journey 3 source-package resolution must be pointer-aware and unified.

Closes the dogfood PACKAGE_GAP: the driver read the source package in-target while
build/discovery resolved through the controller pointer. After this slice, driver
read and build/write resolve through the SAME pointer-aware resolver
(`hld_source_package.source_package_paths`), external mode resolves at the
controller, legacy in-target still works, and a controller-vs-in-target split-brain
fails closed instead of being silently picked or repaired.
"""
from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from hldspec import control_paths, hld_source_package, journey3_driver, run_state, target_discovery

_HLD = "# HLD\n\n## Section One\n\nSome requirement body text.\n"


def _write_pointer(target: Path, controller: Path) -> None:
    (controller / ".hldspec").mkdir(parents=True, exist_ok=True)
    source = target / "HLD.md"
    source.write_text(_HLD, encoding="utf-8")
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


def _build_package(target: Path) -> Path:
    """Build a real package through the production write path; returns its source dir."""
    build = hld_source_package.build_source_package_content(
        target, _HLD, hld_source_ref="test-ref", project_name="demo"
    )
    return build.source_dir


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file() and ".git" not in p.parts
    }


class SourcePackageResolutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-j3-pkg-")
        # Resolve up front so comparisons are immune to macOS /var -> /private/var.
        self.root = Path(self._tmp.name).resolve()
        self.target = self.root / "target"
        self.controller = self.root / "controller"
        self.target.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _seed_controller_package(self) -> Path:
        """Place a valid package ONLY at the controller (in-target stays empty), so a
        non-pointer-aware driver read genuinely fails to find it."""
        seed = self.root / "seed"
        seed.mkdir()
        build = hld_source_package.build_source_package_content(seed, _HLD, hld_source_ref="ref")
        dest = self.controller / ".hldspec" / "source_package"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(build.source_dir, dest)
        return dest

    # 1. Legacy in-target package still validates/discovers.
    def test_legacy_in_target_package_discovered(self) -> None:
        source_dir = _build_package(self.target)
        self.assertEqual(source_dir, self.target / ".hldspec" / "source_package")
        report = journey3_driver.build_journey3_status(self.target)
        self.assertTrue(report["source_package_present"])
        self.assertTrue(report["source_package_validation"]["ok"])

    # 2. External controller package is discovered by the Journey 3 driver
    #    (package ONLY at the controller; a non-pointer-aware read misses it).
    def test_external_controller_package_discovered_by_driver(self) -> None:
        self._seed_controller_package()
        _write_pointer(self.target, self.controller)
        self.assertFalse((self.target / ".hldspec" / "source_package").exists())
        report = journey3_driver.build_journey3_status(self.target)
        self.assertTrue(
            report["source_package_present"],
            "driver must read the source package from the controller root in external mode",
        )

    # 3. Build/write uses controller root when external state is configured.
    def test_build_writes_to_controller_when_external(self) -> None:
        _write_pointer(self.target, self.controller)
        source_dir = _build_package(self.target)
        self.assertEqual(source_dir, self.controller / ".hldspec" / "source_package")
        self.assertTrue((source_dir / hld_source_package.SOURCE_PACKAGE_FILE).is_file())
        self.assertFalse(
            (self.target / ".hldspec" / "source_package").exists(),
            "external build must not write the authoritative package into the target",
        )

    # 4. Driver/read and build/write agree on the same source dir (the controller one).
    def test_read_and_write_agree_on_controller_dir(self) -> None:
        _write_pointer(self.target, self.controller)
        written = _build_package(self.target)
        read_dir, _mirror = hld_source_package.source_package_paths(self.target)
        resolved = control_paths.resolve_hldspec_dir(self.target) / "source_package"
        self.assertEqual(written, read_dir)
        self.assertEqual(written, resolved)
        self.assertEqual(written, self.controller / ".hldspec" / "source_package")

    # 4b. External build binds to the TARGET, not the controller it physically
    #     lives in — discovery must still see BOUND_MATCH (no P1-011 regression).
    def test_external_build_binds_to_target_not_controller(self) -> None:
        _write_pointer(self.target, self.controller)
        source_dir = _build_package(self.target)
        metadata = json.loads((source_dir / hld_source_package.SOURCE_PACKAGE_FILE).read_text())
        self.assertEqual(
            Path(metadata["target_path"]).resolve(), self.target.resolve(),
            "binding must record the real target, not the controller location",
        )
        binding = target_discovery.build_target_discovery(self.target)["source_package_binding"]
        self.assertEqual(binding["state"], target_discovery.BINDING_BOUND_MATCH)

    # 5. Split-brain (controller AND in-target package) fails closed.
    def test_split_brain_fails_closed(self) -> None:
        _write_pointer(self.target, self.controller)
        _build_package(self.target)  # writes to controller
        # Forge a stale in-target authoritative package.
        in_target = self.target / ".hldspec" / "source_package"
        in_target.mkdir(parents=True, exist_ok=True)
        (in_target / hld_source_package.SOURCE_PACKAGE_FILE).write_text("{}", encoding="utf-8")

        self.assertEqual(
            hld_source_package.source_package_split_brain(self.target), in_target
        )
        report = journey3_driver.build_journey3_status(self.target)
        self.assertEqual(report["driver_status"], journey3_driver.STATUS_BLOCKED)
        self.assertTrue(
            any("split-brain" in b.lower() for b in report["blockers"]),
            f"expected an explicit split-brain blocker, got {report['blockers']}",
        )

    # 6. Missing package still BLOCKED / PACKAGE_GAP.
    def test_missing_package_blocked(self) -> None:
        report = journey3_driver.build_journey3_status(self.target)
        self.assertEqual(report["driver_status"], journey3_driver.STATUS_BLOCKED)
        self.assertFalse(report["source_package_present"])
        self.assertTrue(any("Source package missing" in b for b in report["blockers"]))

    # 7. Driver run mutates neither product code nor .specify/.
    def test_driver_read_only_no_mutation(self) -> None:
        _write_pointer(self.target, self.controller)
        _build_package(self.target)
        (self.target / "app.py").write_text("print('product')\n", encoding="utf-8")
        (self.target / ".specify" / "memory").mkdir(parents=True)
        (self.target / ".specify" / "memory" / "constitution.md").write_text(
            "# Constitution\n", encoding="utf-8"
        )
        before = _snapshot(self.target)
        before_ctrl = _snapshot(self.controller)

        journey3_driver.build_journey3_status(self.target)

        self.assertEqual(before, _snapshot(self.target), "driver must not mutate the target")
        self.assertEqual(before_ctrl, _snapshot(self.controller), "driver must not mutate the controller")

    # 9. Driver executes nothing and self-attests read-only.
    def test_driver_executes_nothing(self) -> None:
        _write_pointer(self.target, self.controller)
        _build_package(self.target)
        report = journey3_driver.build_journey3_status(self.target)
        self.assertFalse(report["executed_anything"])
        self.assertFalse(report["mutated_target"])

    # No-pointer resolution is byte-identical to legacy (resolver degrades cleanly).
    def test_no_pointer_resolves_in_target(self) -> None:
        read_dir, _mirror = hld_source_package.source_package_paths(self.target)
        self.assertEqual(read_dir, self.target / ".hldspec" / "source_package")
        self.assertIsNone(hld_source_package.source_package_split_brain(self.target))


if __name__ == "__main__":
    unittest.main()
