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


if __name__ == "__main__":
    unittest.main()
