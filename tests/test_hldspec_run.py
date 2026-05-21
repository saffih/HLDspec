from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecRunTests(unittest.TestCase):
    def test_hldspec_run_raw_hld_stops_at_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            project = Path(td)
            hld = project / "Flow-System-HLD.md"
            hld.write_text("# Flow HLD\n\n## Architecture\n\nBody.\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "hldspec_run.sh"),
                    str(hld),
                    str(project / ".hldspec-first-run"),
                ],
                cwd=project,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(2, result.returncode, msg=result.stderr)
            self.assertIn("Project first-run wrapper summary", result.stdout)
            self.assertTrue((project / ".hldspec-first-run" / "HLD_CONVERSION_PROMPT.md").exists())

    def test_project_continue_script_contains_state_machine_guards(self) -> None:
        script = (ROOT / "scripts" / "project_continue.sh").read_text(encoding="utf-8")
        self.assertIn("Conversion decisions are still TBD", script)
        self.assertIn("apply_hld_conversion_decisions.py", script)
        self.assertIn("first_run_readonly.sh", script)
        self.assertIn("Continue to target-spec generation", script)
        self.assertIn("PYTHON_RUN=(uv run python)", script)

    def test_default_invocation_contract_exists(self) -> None:
        doc = (ROOT / "docs" / "HLD_AGENT_CATCHUP.md").read_text(encoding="utf-8")
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Every project-level HLDspec invocation uses the judge/orchestrator role by default", doc)
        self.assertIn("HLDspec ./Flow-System-HLD.md", doc)
        self.assertIn("hldspec_run.sh", doc)
        self.assertIn("Do not modify the source HLD", doc)
        self.assertIn("Default HLDspec invocation contract", agents)


if __name__ == "__main__":
    unittest.main()
