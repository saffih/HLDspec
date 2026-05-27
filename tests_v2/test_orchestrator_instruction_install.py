from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class OrchestratorInstructionInstallTests(unittest.TestCase):
    def test_installs_universal_agents_md_and_default_shims(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()

            result = subprocess.run(
                [
                    "bash",
                    str(repo / "scripts" / "install_orchestrator_instructions.sh"),
                    "--workspace",
                    str(workspace),
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")
            claude = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
            devin = (workspace / ".devin" / "instructions.md").read_text(encoding="utf-8")

            self.assertIn("Universal Agent Instructions", agents)
            self.assertIn("Codex, Claude, or Devin", agents)
            self.assertIn("follow `AGENTS.md`", claude)
            self.assertIn("follow `../AGENTS.md`", devin)

    def test_codex_only_still_installs_agents_without_shims(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "workspace"
            workspace.mkdir()

            result = subprocess.run(
                [
                    "bash",
                    str(repo / "scripts" / "install_orchestrator_instructions.sh"),
                    "--workspace",
                    str(workspace),
                    "--orchestrators",
                    "codex",
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertTrue((workspace / "AGENTS.md").exists())
            self.assertFalse((workspace / "CLAUDE.md").exists())
            self.assertFalse((workspace / ".devin" / "instructions.md").exists())


if __name__ == "__main__":
    unittest.main()
