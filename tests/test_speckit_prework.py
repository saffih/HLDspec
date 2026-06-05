from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.engineering_selection import render_engineering_guidelines_md
from hldspec.machines.speckit_prework import SpeckitPreworkMachine
from hldspec.state_machine import MachineContext, MachineStatus


class SpeckitPreworkTest(unittest.TestCase):
    def write_engineering_guidelines(self, workspace: Path) -> Path:
        source_package = workspace / ".hldspec" / "source_package"
        source_package.mkdir(parents=True)
        path = source_package / "engineering_guidelines.md"
        path.write_text(render_engineering_guidelines_md("# HLD\n\nA service with business rules.\n"), encoding="utf-8")
        return path

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

    def test_prework_blocks_when_engineering_guidance_missing(self) -> None:
        workspace = Path(tempfile.mkdtemp())
        sync = workspace / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_prework_package.md").write_text("# Package\n", encoding="utf-8")
        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "PASS", "findings": []}),
            encoding="utf-8",
        )

        result = SpeckitPreworkMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(workspace)))

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual("SPECKIT_PREWORK_ENGINEERING_GUIDANCE_MISSING", result.state)
        self.assertIsNotNone(result.checkpoint)
        assert result.checkpoint is not None
        self.assertIn("engineering_guidelines.md is missing", result.checkpoint.blocking_reason)

    def test_prework_blocks_when_engineering_guidance_invalid(self) -> None:
        workspace = Path(tempfile.mkdtemp())
        sync = workspace / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_prework_package.md").write_text("# Package\n", encoding="utf-8")
        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "PASS", "findings": []}),
            encoding="utf-8",
        )
        source_package = workspace / ".hldspec" / "source_package"
        source_package.mkdir(parents=True)
        (source_package / "engineering_guidelines.md").write_text("# Engineering Guidelines\n\n(todo)\n", encoding="utf-8")

        result = SpeckitPreworkMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(workspace)))

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual("SPECKIT_PREWORK_ENGINEERING_GUIDANCE_REWORK", result.state)
        self.assertIsNotNone(result.checkpoint)
        assert result.checkpoint is not None
        self.assertIn("missing required marker", result.checkpoint.blocking_reason)

    def test_prework_allows_valid_engineering_guidance(self) -> None:
        workspace = Path(tempfile.mkdtemp())
        sync = workspace / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "speckit_prework_package.md").write_text("# Package\n", encoding="utf-8")
        (sync / "speckit_prework_quality_review.json").write_text(
            json.dumps({"status": "PASS", "findings": []}),
            encoding="utf-8",
        )
        self.write_engineering_guidelines(workspace)

        result = SpeckitPreworkMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(workspace)))

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPECKIT_PREWORK_READY_FOR_APPROVAL", result.state)


if __name__ == "__main__":
    unittest.main()
