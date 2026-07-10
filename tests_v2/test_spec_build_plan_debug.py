from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.spec_build_plan import SpecBuildPlanMachine
from hldspec.state_machine import MachineContext, MachineStatus


class SpecBuildPlanDebugTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        return Path(tempfile.mkdtemp())

    def test_non_green_plan_lists_flagged_specs_and_writes_debug(self) -> None:
        work = self.make_workspace()
        sync = work / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)

        (sync / "spec_build_plan_review.md").write_text(
            "Continue to SpecKit prework: `false`\n",
            encoding="utf-8",
        )
        (sync / "spec_build_plan.json").write_text(
            json.dumps(
                {
                    "plan_quality": {
                        "decision": "DECOMPOSE",
                        "recommendation": "SPLIT_PLANNED_SPEC",
                        "conflicts": [],
                    },
                    "planned_specs": [
                        {
                            "planned_spec_id": "PS-001",
                            "title": "Mixed planning and interface",
                            "source_hld_ids": ["HLD-019"],
                            "quality_flags": ["mixed_responsibilities"],
                            "requires_user_review": True,
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = SpecBuildPlanMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_CHECKPOINT", result.state)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())
        self.assertIn("PS-001", result.checkpoint.blocking_reason)
        self.assertIn("mixed_responsibilities", result.checkpoint.blocking_reason)
        self.assertTrue((sync / "spec_build_plan_quality_debug.json").exists())
        self.assertTrue((sync / "spec_build_plan_quality_debug.md").exists())
        self.assertIn("FIX_PLAN", (sync / "spec_build_plan_quality_debug.md").read_text(encoding="utf-8"))

    def test_green_plan_continues(self) -> None:
        work = self.make_workspace()
        sync = work / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)

        (sync / "spec_build_plan_review.md").write_text(
            "Continue to SpecKit prework: `true`\n",
            encoding="utf-8",
        )
        (sync / "spec_build_plan.json").write_text(
            json.dumps(
                {
                    "plan_quality": {
                        "decision": "PASS",
                        "recommendation": "KEEP_PLAN",
                        "conflicts": [],
                    },
                    "planned_specs": [],
                }
            ),
            encoding="utf-8",
        )

        result = SpecBuildPlanMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_GREEN", result.state)

    def _write_green_plan(self, sync: Path) -> None:
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "spec_build_plan_review.md").write_text(
            "Continue to SpecKit prework: `true`\n", encoding="utf-8"
        )
        (sync / "spec_build_plan.json").write_text(
            json.dumps(
                {
                    "plan_quality": {"decision": "PASS", "recommendation": "KEEP_PLAN", "conflicts": []},
                    "planned_specs": [],
                }
            ),
            encoding="utf-8",
        )

    def test_external_controller_mode_reads_controller_sync(self) -> None:
        work = self.make_workspace()
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        controller_sync = controller / ".hldspec" / "sync"
        self._write_green_plan(controller_sync)

        result = SpecBuildPlanMachine().run(
            MachineContext(
                repo_root=".", source_hld="source.md", workspace=str(work), metadata={"workspace_layout": "new"}
            )
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_GREEN", result.state)
        self.assertFalse((work / ".hldspec").exists())

    def test_legacy_layout_default_unaffected_by_controller_pointer(self) -> None:
        work = self.make_workspace()
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        sync = work / "firstrun" / ".specify" / "sync"
        self._write_green_plan(sync)

        result = SpecBuildPlanMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_GREEN", result.state)


if __name__ == "__main__":
    unittest.main()
