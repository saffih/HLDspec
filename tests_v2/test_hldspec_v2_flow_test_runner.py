from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecV2FlowTestRunnerTests(unittest.TestCase):
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
            "#!/usr/bin/env bash\nset -euo pipefail\nout=\"$2\"\nmkdir -p \"$out/.specify/sync\"\ncat > \"$out/.specify/sync/spec_build_plan_review.md\" <<'MD'\nContinue to target-spec generation: `true`\nMD\ncat > \"$out/.specify/sync/spec_build_plan.json\" <<'JSON'\n{\"plan_quality\":{\"decision\":\"FIX\",\"recommendation\":\"KEEP_PLAN\",\"conflicts\":[]},\"planned_specs\":[]}\nJSON\ncat > \"$out/.specify/sync/speckit_prework_quality_review.json\" <<'JSON'\n{\"status\":\"PASS\",\"findings\":[]}\nJSON\ntouch \"$out/.specify/sync/speckit_prework_package.md\"\ntouch \"$out/.specify/sync/speckit_prework_quality_review.md\"\ntouch \"$out/.specify/sync/speckit_proxy_dossier.md\"\ntouch \"$out/.specify/sync/hldspec_state.md\"\n",
            encoding="utf-8",
        )

        for file in scripts.iterdir():
            file.chmod(file.stat().st_mode | stat.S_IEXEC)
        return repo

    def test_flow_test_runner_writes_artifacts_and_treats_checkpoint_as_valid(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")
        out = repo / ".hldspec-v2-flow-test"
        workspace = out / "workspace"

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_v2_flow_test.py"),
                str(source),
                "--repo",
                str(repo),
                "--workspace",
                str(workspace),
                "--output-dir",
                str(out),
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr + result.stdout)
        self.assertIn("HLDspec V2 Flow Test: CHECKPOINT_REACHED", result.stdout)
        self.assertTrue((out / "machine_result.json").exists())
        self.assertTrue((out / "machine_result.md").exists())
        self.assertTrue((out / "flow_test_summary.json").exists())
        self.assertTrue((out / "flow_test_summary.md").exists())

        summary = json.loads((out / "flow_test_summary.json").read_text(encoding="utf-8"))
        self.assertEqual("CHECKPOINT_REACHED", summary["flow_test_status"])
        self.assertEqual("HLD_CONVERSION_DECISIONS", summary["checkpoint_kind"])
        self.assertEqual(1, summary["open_question_count"])
        self.assertTrue(summary["valid_for_flow_testing"])
        self.assertFalse(summary["specKit_invoked"])
        self.assertFalse(summary["source_hld_modified_by_runner"])

    def test_flow_test_runner_can_exit_with_machine_result_code(self) -> None:
        repo = self.make_fake_repo()
        source = repo / "Flow-System-HLD.md"
        source.write_text("# Raw HLD\n\n## Milestones\n\nBody.\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_v2_flow_test.py"),
                str(source),
                "--repo",
                str(repo),
                "--exit-with-result-code",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(2, result.returncode, msg=result.stderr + result.stdout)


if __name__ == "__main__":
    unittest.main()
