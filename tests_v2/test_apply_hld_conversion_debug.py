from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.apply_hld_conversion import ApplyHldConversionMachine
from hldspec.state_machine import MachineContext, MachineStatus


class ApplyHldConversionDebugTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        return Path(tempfile.mkdtemp())

    def make_repo_with_apply_script(self, body: str) -> Path:
        repo = Path(tempfile.mkdtemp())
        scripts = repo / "scripts"
        scripts.mkdir()
        script = scripts / "apply_hld_conversion_decisions.py"
        script.write_text(body, encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IEXEC)
        return repo

    def test_rc2_apply_refusal_is_blocked_and_writes_debug_logs(self) -> None:
        repo = self.make_repo_with_apply_script(
            "import sys\n"
            "print('Refusing to apply conversion decisions:')\n"
            "print('- Q-003 HLD-019: KEEP_AS_ONE requires approved_keep_reason')\n"
            "sys.exit(2)\n"
        )
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        source = work / "Flow-System-HLD.md"
        source.write_text("# Source\n", encoding="utf-8")
        (work / "HLD.md").write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(
            json.dumps(
                {
                    "questions": [
                        {
                            "question_id": "Q-003",
                            "source_candidate_id": "HLD-019",
                            "human_decision": "KEEP_AS_ONE",
                            "blocking": True,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        result = ApplyHldConversionMachine().run(
            MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(work))
        )

        self.assertEqual(MachineStatus.BLOCKED, result.status)
        self.assertEqual("APPLY_REFUSED", result.state)
        self.assertIn("KEEP_AS_ONE requires approved_keep_reason", "\n".join(result.errors))
        self.assertTrue((sync / "apply_hld_conversion_command.json").exists())
        self.assertTrue((sync / "apply_hld_conversion_command.md").exists())

        debug = json.loads((sync / "apply_hld_conversion_command.json").read_text(encoding="utf-8"))
        self.assertEqual(2, debug["returncode"])
        self.assertIn("KEEP_AS_ONE requires approved_keep_reason", debug["stdout"])

    def test_successful_apply_writes_debug_logs(self) -> None:
        repo = self.make_repo_with_apply_script(
            "from pathlib import Path\n"
            "import sys\n"
            "hld = Path(sys.argv[1])\n"
            "hld.write_text('# HLD\\n\\n## HLD-001 - Demo\\n\\nConverted.\\n', encoding='utf-8')\n"
            "print('Applied HLD conversion decisions.')\n"
        )
        work = self.make_workspace()
        sync = work / ".specify" / "sync"
        sync.mkdir(parents=True)
        source = work / "Flow-System-HLD.md"
        source.write_text("# Source\n", encoding="utf-8")
        (work / "HLD.md").write_text("# Raw HLD\n\n## Demo\n\nBody.\n", encoding="utf-8")
        (sync / "hld_conversion_decision_queue.json").write_text(
            json.dumps({"questions": []}),
            encoding="utf-8",
        )

        result = ApplyHldConversionMachine().run(
            MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(work))
        )

        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("WORKING_HLD_CONVERTED", result.state)
        self.assertTrue((sync / "apply_hld_conversion_command.json").exists())


if __name__ == "__main__":
    unittest.main()
