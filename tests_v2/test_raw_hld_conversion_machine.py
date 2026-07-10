from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.raw_hld_conversion import RawHldConversionMachine
from hldspec.state_machine import MachineContext, MachineStatus


class RawHldConversionMachineV2Tests(unittest.TestCase):
    def make_workspace(self) -> Path:
        return Path(tempfile.mkdtemp())

    def test_open_queue_stops_at_human_checkpoint(self) -> None:
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(json.dumps({"questions": [{"question_id": "Q-003", "source_candidate_id": "HLD-019", "title": "Milestones", "question": "Keep or split?", "options": ["KEEP_AS_ONE", "SPLIT"], "human_decision": "TBD", "blocking": True}]}), encoding="utf-8")
        result = RawHldConversionMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(work)))
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_answered_queue_can_continue(self) -> None:
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(json.dumps({"questions": [{"question_id": "Q-003", "source_candidate_id": "HLD-019", "title": "Milestones", "question": "Keep or split?", "options": ["KEEP_AS_ONE", "SPLIT"], "human_decision": "KEEP_AS_ONE", "blocking": True}]}), encoding="utf-8")
        result = RawHldConversionMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(work)))
        self.assertEqual(MachineStatus.CONTINUE, result.status)

    def _answered_queue(self) -> str:
        return json.dumps(
            {
                "questions": [
                    {
                        "question_id": "Q-003",
                        "source_candidate_id": "HLD-019",
                        "title": "Milestones",
                        "question": "Keep or split?",
                        "options": ["KEEP_AS_ONE", "SPLIT"],
                        "human_decision": "KEEP_AS_ONE",
                        "blocking": True,
                    }
                ]
            }
        )

    def test_external_controller_mode_reads_controller_sync(self) -> None:
        work = self.make_workspace()
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (work / "targetHLD").mkdir(parents=True)
        (work / "targetHLD" / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        controller_sync = controller / ".hldspec" / "sync"
        controller_sync.mkdir(parents=True)
        (controller_sync / "hld_conversion_decision_queue.json").write_text(self._answered_queue(), encoding="utf-8")

        result = RawHldConversionMachine().run(
            MachineContext(
                repo_root=".", source_hld="source.md", workspace=str(work), metadata={"workspace_layout": "new"}
            )
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertFalse((work / ".hldspec").exists())

    def test_legacy_layout_default_unaffected_by_controller_pointer(self) -> None:
        work = self.make_workspace()
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(self._answered_queue(), encoding="utf-8")

        result = RawHldConversionMachine().run(MachineContext(repo_root=".", source_hld="source.md", workspace=str(work)))
        self.assertEqual(MachineStatus.CONTINUE, result.status)


if __name__ == "__main__":
    unittest.main()
