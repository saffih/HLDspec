from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def write_minimal_workspace(workspace: Path, *, hldspec: bool = False) -> Path:
    (workspace / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
    (workspace / ".specify" / "sync").mkdir(parents=True, exist_ok=True)
    (workspace / "specs" / "001-demo").mkdir(parents=True, exist_ok=True)

    (workspace / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
    (workspace / ".specify" / "sync" / "spec_index.json").write_text(json.dumps({"specs": []}), encoding="utf-8")
    (workspace / "specs" / "001-demo" / "spec.md").write_text("# Demo Spec\n", encoding="utf-8")

    if hldspec:
        hld = workspace / "HLD.md"
        hld.write_text(
            """# HLD

## HLD-001 - Demo

HLD-ID: HLD-001
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: 001
HLD-RESOURCES: TBD
HLD-VERIFY: downstream context can target this section

Demo body.
""",
            encoding="utf-8",
        )
        return hld

    hld = workspace / "HLD.md"
    hld.write_text("# Raw HLD\n\n## Demo\n\nDemo body.\n", encoding="utf-8")
    return hld


class DownstreamContextGuardTests(unittest.TestCase):
    def test_downstream_blocks_unbounded_full_hld_prompt_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld = write_minimal_workspace(workspace)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hld_spec_downstream.py"),
                    "--workspace",
                    str(workspace),
                    "--hld",
                    str(hld),
                    "--phase",
                    "analyze",
                    "--prompt-only",
                    "--agent",
                    "codex",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("Refusing to build an unbounded downstream prompt", result.stderr + result.stdout)

    def test_downstream_allows_explicit_hld_char_bound(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld = write_minimal_workspace(workspace)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hld_spec_downstream.py"),
                    "--workspace",
                    str(workspace),
                    "--hld",
                    str(hld),
                    "--phase",
                    "analyze",
                    "--prompt-only",
                    "--agent",
                    "codex",
                    "--max-hld-chars",
                    "30000",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("Prompt-only mode", result.stdout)

    def test_downstream_allows_hld_map_bounded_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld = write_minimal_workspace(workspace, hldspec=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hld_spec_downstream.py"),
                    "--workspace",
                    str(workspace),
                    "--hld",
                    str(hld),
                    "--use-hld-map",
                    "--target-hld",
                    "HLD-001",
                    "--phase",
                    "analyze",
                    "--prompt-only",
                    "--agent",
                    "codex",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("HLD map: True", result.stdout)

    def test_downstream_allows_explicit_full_hld_override(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld = write_minimal_workspace(workspace)

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hld_spec_downstream.py"),
                    "--workspace",
                    str(workspace),
                    "--hld",
                    str(hld),
                    "--phase",
                    "analyze",
                    "--prompt-only",
                    "--agent",
                    "codex",
                    "--allow-full-hld-context",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertIn("Prompt-only mode", result.stdout)


if __name__ == "__main__":
    unittest.main()
