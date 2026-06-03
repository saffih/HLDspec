from __future__ import annotations

import json
import stat
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.project import ProjectMachine
from hldspec.state_machine import MachineContext, MachineStatus


class ProjectMachineV2Tests(unittest.TestCase):
    def make_fake_repo(self) -> Path:
        repo = Path(tempfile.mkdtemp())
        scripts = repo / "scripts"
        scripts.mkdir()

        (scripts / "project_first_run.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\nsrc=\"$1\"; work=\"$2\"\nmkdir -p \"$work/.specify/sync\"\ncp \"$src\" \"$work/HLD.md\"\ncat > \"$work/.specify/sync/hld_conversion_decision_queue.json\" <<'JSON'\n{\"questions\":[{\"question_id\":\"Q-003\",\"source_candidate_id\":\"HLD-019\",\"title\":\"Milestones\",\"question\":\"Keep or split?\",\"options\":[\"KEEP_AS_ONE\",\"SPLIT\"],\"human_decision\":\"TBD\",\"blocking\":true}]}\nJSON\nexit 2\n",
            encoding="utf-8",
        )

        (scripts / "apply_hld_conversion_decisions.py").write_text(
            "from pathlib import Path\nimport sys\nhld=Path(sys.argv[1])\nhld.write_text('# HLD\\n\\n## HLD-019 - Milestones\\n\\nConverted.\\n', encoding='utf-8')\n",
            encoding="utf-8",
        )

        (scripts / "first_run_readonly.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\nout=\"$2\"\nmkdir -p \"$out/.specify/sync\"\ncat > \"$out/.specify/sync/spec_build_plan_review.md\" <<'MD'\nContinue to SpecKit prework: `true`\nMD\ncat > \"$out/.specify/sync/spec_build_plan.json\" <<'JSON'\n{\"plan_quality\":{\"decision\":\"PASS\",\"recommendation\":\"KEEP_PLAN\",\"conflicts\":[]},\"planned_specs\":[]}\nJSON\ncat > \"$out/.specify/sync/speckit_prework_quality_review.json\" <<'JSON'\n{\"status\":\"PASS\",\"findings\":[]}\nJSON\ntouch \"$out/.specify/sync/speckit_prework_package.md\"\ntouch \"$out/.specify/sync/speckit_prework_quality_review.md\"\ntouch \"$out/.specify/sync/speckit_proxy_dossier.md\"\ntouch \"$out/.specify/sync/hldspec_state.md\"\n",
            encoding="utf-8",
        )

        for file in scripts.iterdir():
            file.chmod(file.stat().st_mode | stat.S_IEXEC)

        return repo

    def test_project_machine_initial_run_stops_at_conversion_checkpoint(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        result = ProjectMachine().run(
            MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(workspace))
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("HLD_CONVERSION_DECISIONS", result.state)
        assert result.checkpoint is not None
        self.assertTrue(result.checkpoint.has_open_questions())

    def test_project_machine_reaches_prework_approval_after_answered_conversion(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        # First run creates queue and checkpoint.
        ProjectMachine().run(MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(workspace)))

        queue = workspace / ".specify" / "sync" / "hld_conversion_decision_queue.json"
        data = json.loads(queue.read_text(encoding="utf-8"))
        data["questions"][0]["human_decision"] = "KEEP_AS_ONE"
        queue.write_text(json.dumps(data), encoding="utf-8")

        result = ProjectMachine().run(
            MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(workspace))
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("SPECKIT_PREWORK_APPROVAL_GATE", result.state)
        assert result.checkpoint is not None
        self.assertFalse(result.checkpoint.has_open_questions())
        self.assertIn("Do not invoke SpecKit until the human approves this gate.", result.checkpoint.forbidden_actions)
        self.assertEqual("# Raw HLD\n\n## Milestones\n\nBody.\n", source.read_text(encoding="utf-8"))

    def test_project_machine_blocks_when_required_scripts_are_missing(self) -> None:
        repo = Path(tempfile.mkdtemp())
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        result = ProjectMachine().run(
            MachineContext(repo_root=str(repo), source_hld=str(source), workspace=str(workspace))
        )

        self.assertEqual(MachineStatus.ERROR, result.status)
        self.assertEqual("FIRST_RUN_FAILED", result.state)

    def test_agent_first_new_layout_uses_target_hld_and_hldspec_events(self) -> None:
        repo = Path(tempfile.mkdtemp())
        scripts = repo / "scripts"
        scripts.mkdir()
        (scripts / "first_run_readonly.sh").write_text(
            "#!/usr/bin/env bash\nset -euo pipefail\nhld=\"$1\"; out=\"$2\"\n"
            'mkdir -p "$out/.specify/sync"\n'
            'printf "%s\\n" "$hld" > "$out/.specify/sync/received_hld_path.txt"\n'
            "cat > \"$out/.specify/sync/hld_conversion_decision_queue.json\" <<'JSON'\n"
            '{"questions":[{"question_id":"Q-001","source_candidate_id":"HLD-001",'
            '"title":"Test","question":"Keep?","options":["KEEP","SPLIT"],'
            '"human_decision":"TBD","blocking":true}]}\n'
            "JSON\n"
            "exit 2\n",
            encoding="utf-8",
        )
        for file in scripts.iterdir():
            file.chmod(file.stat().st_mode | stat.S_IEXEC)

        source = repo / "Source-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        target = repo / "target"

        result = ProjectMachine().run(
            MachineContext(
                repo_root=str(repo),
                source_hld=str(source),
                workspace=str(target),
                metadata={"workspace_layout": "new"},
            )
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        self.assertEqual("HLD_CONVERSION_DECISIONS", result.state)
        self.assertTrue((target / "targetHLD" / "HLD.md").exists())
        self.assertTrue((target / ".hldspec" / "sync" / "hld_conversion_decision_queue.json").exists())
        self.assertFalse((target / ".specify" / "sync" / "hld_conversion_decision_queue.json").exists())
        received = target / ".hldspec" / "sync" / "received_hld_path.txt"
        self.assertEqual(str(target / "targetHLD" / "HLD.md"), received.read_text(encoding="utf-8").strip())
        self.assertTrue((target / ".hldspec" / "events.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
