from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.project import ProjectMachine
from hldspec.state_machine import MachineContext, MachineStatus


ROOT = Path(__file__).resolve().parents[1]


class ProjectMachineV2Tests(unittest.TestCase):
    def make_workspace(self) -> Path:
        return Path(tempfile.mkdtemp())

    def test_project_machine_wraps_raw_hld_checkpoint(self) -> None:
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "Q-003",
                            "source_candidate_id": "HLD-019",
                            "title": "Milestones",
                            "question": "Keep or split?",
                            "options": ["KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"],
                            "human_decision": "TBD",
                            "blocking": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = ProjectMachine().run(
            MachineContext(repo_root=str(ROOT), source_hld="Flow-System-HLD.md", workspace=str(work))
        )

        self.assertEqual("ProjectMachine", result.machine)
        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("HLD_CONVERSION_DECISIONS", result.state)
        self.assertIn("RawHldConversionMachine:STOP_CHECKPOINT", result.actions_run)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_project_machine_continues_when_raw_conversion_decisions_are_answered(self) -> None:
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "Q-003",
                            "source_candidate_id": "HLD-019",
                            "title": "Milestones",
                            "question": "Keep or split?",
                            "options": ["KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"],
                            "human_decision": "KEEP_AS_ONE",
                            "blocking": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = ProjectMachine().run(
            MachineContext(repo_root=str(ROOT), source_hld="Flow-System-HLD.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("RAW_HLD_CONVERSION_READY_TO_APPLY", result.state)
        self.assertIn("RawHldConversionMachine:HLD_CONVERSION_DECISIONS_ANSWERED", result.actions_run)

    def test_project_machine_continues_when_working_hld_is_already_converted(self) -> None:
        work = self.make_workspace()
        (work / "HLD.md").write_text("# HLD\n\n## HLD-001 - Demo\n\nBody.\n", encoding="utf-8")

        result = ProjectMachine().run(
            MachineContext(repo_root=str(ROOT), source_hld="Flow-System-HLD.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("RAW_HLD_CONVERSION_COMPLETE", result.state)
        self.assertIn("RawHldConversionMachine:WORKING_HLD_CONVERTED", result.actions_run)

    def test_hldspec_v2_cli_renders_machine_result_and_preserves_exit_code(self) -> None:
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        source = work / "Flow-System-HLD.md"
        source.write_text("# Source HLD\n", encoding="utf-8")
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "Q-003",
                            "source_candidate_id": "HLD-019",
                            "title": "Milestones",
                            "question": "Keep or split?",
                            "options": ["KEEP_AS_ONE", "SPLIT", "MODIFY_SPLIT"],
                            "human_decision": "TBD",
                            "blocking": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_v2.py"),
                str(source),
                str(work),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(2, result.returncode, msg=result.stderr)
        self.assertIn("Machine: ProjectMachine", result.stdout)
        self.assertIn("Status: STOP_CHECKPOINT", result.stdout)
        self.assertIn("Current checkpoint: HLD_CONVERSION_DECISIONS", result.stdout)
        self.assertIn("Human decision needed:", result.stdout)

    def test_project_machine_doc_exists(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_PROJECT_MACHINE_V2.md").read_text(encoding="utf-8")
        self.assertIn("ProjectMachine", text)
        self.assertIn("RawHldConversionMachine", text)
        self.assertIn("hldspec_v2.py", text)


if __name__ == "__main__":
    unittest.main()
