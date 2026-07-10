from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.hld_readiness import HldReadinessMachine
from hldspec.state_machine import MachineContext, MachineStatus

_HLD_BODY = "# Demo HLD\n\n## Section 1\n\nBody text.\n"


class HldReadinessControlSyncPathResolutionTests(unittest.TestCase):
    """A3.2c-family: HldReadinessMachine must resolve its sync dir the same
    pointer-aware way SpecKitExecutionMachine does (PR #147) so external-
    controller mode can't split writer/reader state.
    """

    def test_external_controller_mode_writes_controller_sync(self) -> None:
        work = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (work / "targetHLD").mkdir(parents=True)
        (work / "targetHLD" / "HLD.md").write_text(_HLD_BODY, encoding="utf-8")

        result = HldReadinessMachine().run(
            MachineContext(
                repo_root=".", source_hld="source.md", workspace=str(work), metadata={"workspace_layout": "new"}
            )
        )

        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("HLD_READY", result.state)
        controller_sync = controller / ".hldspec" / "sync"
        self.assertTrue((controller_sync / "hld_readiness_check.json").exists())
        self.assertFalse((work / ".hldspec").exists())

    def test_legacy_layout_default_unaffected_by_controller_pointer(self) -> None:
        work = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (work / "HLD.md").write_text(_HLD_BODY, encoding="utf-8")

        result = HldReadinessMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("HLD_READY", result.state)
        legacy_sync = work / "firstrun" / ".specify" / "sync"
        self.assertTrue((legacy_sync / "hld_readiness_check.json").exists())


if __name__ == "__main__":
    unittest.main()
