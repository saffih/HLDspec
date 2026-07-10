from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.engineering_selection import render_engineering_guidelines_md
from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import MachineContext, MachineStatus


def _pointer(target: Path, controller: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    (target / ".hldspec-run.json").write_text(
        json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
    )


def _write_prework_artifacts(sync: Path, source_package: Path) -> None:
    sync.mkdir(parents=True, exist_ok=True)
    source_package.mkdir(parents=True, exist_ok=True)
    (source_package / "engineering_guidelines.md").write_text(
        render_engineering_guidelines_md("# HLD\n\nA service with business rules.\n"),
        encoding="utf-8",
    )
    (sync / "speckit_prework_package.md").write_text("prework package\n", encoding="utf-8")
    (sync / "speckit_prework_quality_review.md").write_text("review report\n", encoding="utf-8")
    (sync / "speckit_prework_quality_review.json").write_text(
        json.dumps({"status": "PASS", "runskeptic_status": "PASS", "findings": []}, indent=2) + "\n",
        encoding="utf-8",
    )


class SpeckitPreworkControlSyncPathResolutionTests(unittest.TestCase):
    """A3.2c-family follow-up: SpeckitPreworkMachine's engineering_guidelines
    gate must resolve source_package_dir the same pointer-aware way its sync
    reads do, or it wrongly reports guidance missing when a controller-root
    source package already exists (a live writer/reader split, since the
    writer -- hld_source_package.build_source_package_content -- is already
    controller-aware).
    """

    def test_external_controller_mode_finds_controller_root_source_package(self) -> None:
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        controller_sync = controller / ".hldspec" / "sync"
        controller_source_package = controller / ".hldspec" / "source_package"
        _write_prework_artifacts(controller_sync, controller_source_package)

        result = SpeckitPreworkMachine().run(
            MachineContext(
                repo_root=str(ws), workspace=str(ws), metadata={"workspace_layout": "new"}
            )
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECKIT_PREWORK_READY_FOR_APPROVAL", result.state)
        self.assertFalse((ws / ".hldspec").exists())

    def test_legacy_layout_sync_unaffected_but_source_package_dir_is_controller_aware(self) -> None:
        """sync_dir has a legacy branch (stays target-local); source_package_dir
        does not (it's hldspec_dir-derived unconditionally), so once a
        controller pointer exists it must resolve to the controller root even
        under legacy layout -- proving the fix doesn't just mirror the sync_dir
        legacy no-op, it correctly follows source_package_dir's own contract.
        """
        ws = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        _pointer(ws, controller)
        legacy_sync = ws / "firstrun" / ".specify" / "sync"
        controller_source_package = controller / ".hldspec" / "source_package"
        _write_prework_artifacts(legacy_sync, controller_source_package)

        result = SpeckitPreworkMachine().run(
            MachineContext(repo_root=str(ws), workspace=str(ws))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECKIT_PREWORK_READY_FOR_APPROVAL", result.state)


if __name__ == "__main__":
    unittest.main()
