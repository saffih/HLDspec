from __future__ import annotations

import json
import os
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
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "src=\"$1\"; work=\"$2\"\n"
            "mkdir -p \"$work/.specify/sync\"\n"
            "cp \"$src\" \"$work/HLD.md\"\n"
            "cat > \"$work/.specify/sync/hld_conversion_decision_queue.json\" <<'JSON'\n"
            "{\"questions\":[{\"question_id\":\"Q-003\",\"source_candidate_id\":\"HLD-019\",\"title\":\"Milestones\",\"question\":\"Keep or split?\",\"options\":[\"KEEP_AS_ONE\",\"SPLIT\"],\"human_decision\":\"TBD\",\"blocking\":true}]}\n"
            "JSON\n"
            "exit 2\n",
            encoding="utf-8",
        )

        (scripts / "apply_hld_conversion_decisions.py").write_text(
            "from pathlib import Path\n"
            "import sys\n"
            "hld = Path(sys.argv[1])\n"
            "hld.write_text('# HLD\\n\\n## HLD-019 - Milestones\\n\\nConverted.\\n', encoding='utf-8')\n",
            encoding="utf-8",
        )

        (scripts / "first_run_readonly.sh").write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "out=\"$2\"\n"
            "mkdir -p \"$out/.specify/sync\"\n"
            "cat > \"$out/.specify/sync/spec_build_plan_review.md\" <<'MD'\n"
            "Continue to SpecKit prework: `true`\n"
            "MD\n"
            "cat > \"$out/.specify/sync/spec_build_plan.json\" <<'JSON'\n"
            "{\"plan_quality\":{\"decision\":\"PASS\",\"recommendation\":\"KEEP_PLAN\",\"conflicts\":[]},\"planned_specs\":[]}\n"
            "JSON\n"
            "cat > \"$out/.specify/sync/speckit_prework_quality_review.json\" <<'JSON'\n"
            "{\"status\":\"PASS\",\"findings\":[]}\n"
            "JSON\n"
            "touch \"$out/.specify/sync/speckit_prework_package.md\"\n"
            "touch \"$out/.specify/sync/speckit_prework_quality_review.md\"\n"
            "touch \"$out/.specify/sync/speckit_proxy_dossier.md\"\n"
            "touch \"$out/.specify/sync/hldspec_state.md\"\n",
            encoding="utf-8",
        )

        for file in scripts.iterdir():
            file.chmod(file.stat().st_mode | stat.S_IEXEC)

        return repo

    def run_project_machine(self, repo: Path, source: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
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
        env = os.environ.copy()
        env["HLDSPEC_ROLE_REVIEWS"] = "local"
        return subprocess.run(
            [sys.executable, "-c", code],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )

    def test_v2_cli_initial_run_stops_at_conversion_checkpoint(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        result = self.run_project_machine(repo, source, workspace)

        self.assertEqual(2, result.returncode, msg=result.stderr + result.stdout)
        self.assertIn("Current checkpoint: HLD_CONVERSION_DECISIONS", result.stdout)
        self.assertIn("Human decision needed:", result.stdout)
        self.assertTrue((workspace / "HLD.md").exists())

    def test_v2_project_machine_reaches_prework_approval_after_answer(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        workspace = repo / ".hldspec-v2-run"

        first = self.run_project_machine(repo, source, workspace)
        self.assertEqual(2, first.returncode, msg=first.stderr + first.stdout)

        queue = workspace / ".specify" / "sync" / "hld_conversion_decision_queue.json"
        data = json.loads(queue.read_text(encoding="utf-8"))
        data["questions"][0]["human_decision"] = "KEEP_AS_ONE"
        data["questions"][0]["approved_keep_reason"] = "Milestones are planning context in this fixture."
        queue.write_text(json.dumps(data), encoding="utf-8")

        second = self.run_project_machine(repo, source, workspace)

        self.assertEqual(2, second.returncode, msg=second.stderr + second.stdout)
        self.assertIn("Current checkpoint: SPECKIT_PREWORK_APPROVAL_GATE", second.stdout)
        self.assertIn("Do not invoke SpecKit until", second.stdout)
        self.assertIn("## HLD-019 - Milestones", (workspace / "HLD.md").read_text(encoding="utf-8"))
        self.assertTrue((workspace / ".hldspec" / "source_package" / "engineering_guidelines.md").exists())
        self.assertEqual("# Raw HLD\n\n## Milestones\n\nBody.\n", source.read_text(encoding="utf-8"))

        sync = workspace / "firstrun" / ".specify" / "sync"
        self.assertTrue((sync / "raw_hld_chunks.jsonl").exists())
        self.assertTrue((sync / "raw_hld_scan_findings.jsonl").exists())
        self.assertTrue((sync / "architecture_review.md").exists())
        self.assertTrue((sync / "product_review.md").exists())
        self.assertTrue((sync / "governance_review.md").exists())
        self.assertTrue((sync / "role_review_summary.md").exists())


if __name__ == "__main__":
    unittest.main()
