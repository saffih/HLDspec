from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class DevelopmentHandoffBacklogTests(unittest.TestCase):
    def test_agents_md_first_screen_points_to_handoff_and_backlog(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        first_screen = "\n".join((repo / "AGENTS.md").read_text(encoding="utf-8").splitlines()[:8])
        self.assertIn("HLDspec repo-development handoff:", first_screen)
        self.assertIn("docs/HLDSPEC_DEVELOPMENT_HANDOFF.md", first_screen)
        self.assertIn("docs/HLDSPEC_DEVELOPMENT_BACKLOG.md", first_screen)
        self.assertIn("source of truth", first_screen)

    def test_canonical_handoff_and_backlog_docs_exist(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        self.assertTrue((repo / "docs" / "HLDSPEC_DEVELOPMENT_HANDOFF.md").exists())
        self.assertTrue((repo / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md").exists())

    def test_handoff_generator_outputs_backlog_pointer(self) -> None:
        repo = Path(__file__).resolve().parents[1]
        with TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "handoff"
            result = subprocess.run(
                [
                    sys.executable,
                    str(repo / "scripts" / "hldspec_dev_handoff.py"),
                    "--repo",
                    str(repo),
                    "--out-dir",
                    str(out_dir),
                    "--from-agent",
                    "codex",
                    "--to-agent",
                    "claude",
                    "--model-tier",
                    "MODEL_STRONG",
                    "--focus",
                    "handoff backlog test",
                    "--open-action",
                    "TargetWorkspaceAdapter still needed",
                    "--runskeptic-status",
                    "ACTION: adapter still needed",
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            payload = json.loads((out_dir / "HANDOFF.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["canonical_handoff_protocol"], "docs/HLDSPEC_DEVELOPMENT_HANDOFF.md")
            self.assertEqual(payload["canonical_backlog"], "docs/HLDSPEC_DEVELOPMENT_BACKLOG.md")
            self.assertIn("docs/HLDSPEC_DEVELOPMENT_BACKLOG.md", payload["required_first_read"])
            self.assertIn("TargetWorkspaceAdapter still needed", payload["open_actions"])

            md = (out_dir / "HANDOFF.md").read_text(encoding="utf-8")
            self.assertIn("docs/HLDSPEC_DEVELOPMENT_HANDOFF.md", md)
            self.assertIn("docs/HLDSPEC_DEVELOPMENT_BACKLOG.md", md)
            self.assertIn("handoff backlog test", md)


if __name__ == "__main__":
    unittest.main()
