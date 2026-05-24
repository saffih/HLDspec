from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import MachineContext, MachineStatus


class SpeckitPreworkTest(unittest.TestCase):
    def test_prework_blocks_when_package_missing(self) -> None:
        workspace = Path(tempfile.mkdtemp())
        result = SpeckitPreworkMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(workspace)))

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual("SPECKIT_PREWORK_MISSING", result.state)
        self.assertIsNotNone(result.checkpoint)
        self.assertIn("Do not invoke SpecKit.", result.checkpoint.forbidden_actions)

    def test_prework_blocks_on_quality_blocker(self) -> None:
        workspace = Path(tempfile.mkdtemp())
        sync = workspace / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_prework_package.md").write_text("# Package\n", encoding="utf-8")
        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "REWORK_REQUIRED", "findings": [{"severity": "BLOCKER"}]}),
            encoding="utf-8",
        )

        result = SpeckitPreworkMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(workspace)))

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual("SPECKIT_PREWORK_REWORK", result.state)


if __name__ == "__main__":
    unittest.main()
