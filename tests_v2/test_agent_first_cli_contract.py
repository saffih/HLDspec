from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AgentFirstCliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_agent_first_start_creates_target_session(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# High-Level Design\n\n## HLD-001 - Purpose\n\nHLD-ID: HLD-001\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--source",
                str(source),
                "--target",
                str(target),
                "--agent",
                "manual",
                "--comment",
                "test run",
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session_path = target / ".hldspec" / "agent_session.json"
        prompt_path = target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
        self.assertTrue(session_path.exists())
        self.assertTrue(prompt_path.exists())
        self.assertTrue((target / "targetHLD" / "raw" / "HLD.raw.md").exists())
        self.assertTrue((target / "targetHLD" / "HLD.md").exists())

        session = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual("manual", session["agent"])
        self.assertEqual("create", session["mode"])
        self.assertEqual(str(source.resolve()), session["source"]["path"])
        self.assertEqual(str(target.resolve() / ".hldspec" / "sync"), session["paths"]["hldspec_sync"])
        self.assertEqual(str(target.resolve() / ".hldspec" / "events.jsonl"), session["paths"]["events"])
        self.assertIn("start an agent session", result.stdout)
        prompt_text = prompt_path.read_text(encoding="utf-8")
        self.assertIn("scripts/hldspec continue --target", prompt_text)
        self.assertNotIn("target/.hldspec/firstrun/.specify/sync", prompt_text)

    def test_agent_first_diff_detects_unchanged_source(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")

        subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--source",
                str(source),
                "--target",
                str(target),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "diff",
                "--source",
                str(source),
                "--target",
                str(target),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode)
        self.assertIn("Diff status: unchanged", result.stdout)


if __name__ == "__main__":
    unittest.main()
