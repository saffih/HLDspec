from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecV2FullSliceTests(unittest.TestCase):
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
            "#!/usr/bin/env bash\nset -euo pipefail\nhld=\"$1\"; out=\"$2\"\nmkdir -p \"$out/.specify/sync\"\ncat > \"$out/.specify/sync/spec_build_plan_review.md\" <<'MD'\nContinue to target-spec generation: `true`\nMD\ncat > \"$out/.specify/sync/spec_build_plan.json\" <<'JSON'\n{\"plan_quality\":{\"decision\":\"FIX\",\"recommendation\":\"KEEP_PLAN\",\"conflicts\":[]},\"planned_specs\":[]}\nJSON\ncat > \"$out/.specify/sync/speckit_prework_quality_review.json\" <<'JSON'\n{\"status\":\"PASS\",\"findings\":[]}\nJSON\ntouch \"$out/.specify/sync/speckit_prework_package.md\"\ntouch \"$out/.specify/sync/speckit_prework_quality_review.md\"\ntouch \"$out/.specify/sync/speckit_proxy_dossier.md\"\ntouch \"$out/.specify/sync/hldspec_state.md\"\n",
            encoding="utf-8",
        )

        for f in scripts.iterdir():
            f.chmod(f.stat().st_mode | stat.S_IEXEC)
        return repo

    def test_v2_cli_initial_run_stops_at_conversion_checkpoint(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        code = (
            "import sys;"
            f"sys.path.insert(0, {str(ROOT)!r});"
            "from hldspec.machines.project import ProjectMachine;"
            "from hldspec.result_renderer import render_machine_result;"
            "from hldspec.state_machine import MachineContext;"
            f"r=ProjectMachine().run(MachineContext(repo_root={str(repo)!r}, source_hld={str(source)!r}, workspace={str(workspace)!r}));"
            "print(render_machine_result(r), end='');"
            "sys.exit(int(r.exit_code()))"
        )
        result = subprocess.run([sys.executable, "-c", code], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(2, result.returncode, msg=result.stderr + result.stdout)
        self.assertIn("Current checkpoint: HLD_CONVERSION_DECISIONS", result.stdout)
        self.assertIn("Human decision needed:", result.stdout)
        self.assertTrue((workspace / "HLD.md").exists())

    def test_v2_project_machine_reaches_prework_approval_after_answer(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        # First run creates queue.
        code = (
            "import sys;"
            f"sys.path.insert(0, {str(ROOT)!r});"
            "from hldspec.machines.project import ProjectMachine;"
            "from hldspec.state_machine import MachineContext;"
            f"r=ProjectMachine().run(MachineContext(repo_root={str(repo)!r}, source_hld={str(source)!r}, workspace={str(workspace)!r}));"
            "sys.exit(int(r.exit_code()))"
        )
        subprocess.run([sys.executable, "-c", code], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)

        queue = workspace / ".specify" / "sync" / "hld_conversion_decision_queue.json"
        data = json.loads(queue.read_text(encoding="utf-8"))
        data["questions"][0]["human_decision"] = "KEEP_AS_ONE"
        queue.write_text(json.dumps(data), encoding="utf-8")

        code2 = (
            "import sys;"
            f"sys.path.insert(0, {str(ROOT)!r});"
            "from hldspec.machines.project import ProjectMachine;"
            "from hldspec.result_renderer import render_machine_result;"
            "from hldspec.state_machine import MachineContext;"
            f"r=ProjectMachine().run(MachineContext(repo_root={str(repo)!r}, source_hld={str(source)!r}, workspace={str(workspace)!r}));"
            "print(render_machine_result(r), end='');"
            "sys.exit(int(r.exit_code()))"
        )
        result = subprocess.run([sys.executable, "-c", code2], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        self.assertEqual(2, result.returncode, msg=result.stderr + result.stdout)
        self.assertIn("Current checkpoint: SPECKIT_PREWORK_APPROVAL_GATE", result.stdout)
        self.assertIn("Do not invoke SpecKit until the human approves this gate.", result.stdout)
        self.assertIn("## HLD-019 - Milestones", (workspace / "HLD.md").read_text(encoding="utf-8"))
        self.assertEqual("# Raw HLD\n\n## Milestones\n\nBody.\n", source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
