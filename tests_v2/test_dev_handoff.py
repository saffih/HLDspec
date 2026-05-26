from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


class DevHandoffTests(unittest.TestCase):
    def test_generates_markdown_and_json_handoff(self) -> None:
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
                    "development handoff test",
                    "--tests-run",
                    "python3 -m py_compile scripts/hldspec_dev_handoff.py",
                    "--runskeptic-status",
                    "PASS: unit test scope",
                    "--open-action",
                    "wire into docs index",
                    "--next-safe-step",
                    "run tests",
                ],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            md = out_dir / "HANDOFF.md"
            js = out_dir / "HANDOFF.json"
            self.assertTrue(md.exists())
            self.assertTrue(js.exists())

            payload = json.loads(js.read_text(encoding="utf-8"))
            self.assertEqual(payload["from_actor"], "codex")
            self.assertEqual(payload["to_actor"], "claude")
            self.assertEqual(payload["model_tier"], "MODEL_STRONG")
            self.assertIn("CLAUDE.md", payload["required_first_read"])
            self.assertIn("Source HLD is read-only. Workspace copy only.", payload["invariants"])
            self.assertIn("wire into docs index", payload["open_actions"])

            text = md.read_text(encoding="utf-8")
            self.assertIn("# HLDspec Development Handoff", text)
            self.assertIn("development handoff test", text)
            self.assertIn("## Do not do", text)


if __name__ == "__main__":
    unittest.main()
