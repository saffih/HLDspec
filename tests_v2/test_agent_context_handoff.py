from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec.agent_context_handoff import MARKER_BEGIN, write_agent_context_handoff


class AgentContextHandoffTests(unittest.TestCase):
    def make_workspace(self) -> Path:
        workspace = Path(tempfile.mkdtemp()) / "workspace"
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True)
        (workspace / ".hldspec-run").mkdir(parents=True)

        queue = {
            "schema_version": 1,
            "bundles": [
                {
                    "bundle_id": "bundle-a",
                    "bundle_name": "Bundle A",
                    "bundle_slug": "bundle-a",
                    "prompt_paths": {
                        "claude": ".specify/sync/speckit_bundle_prompts/claude/bundle-a/prompt.md",
                        "devin": ".specify/sync/speckit_bundle_prompts/devin/bundle-a/prompt.md",
                    },
                }
            ],
        }
        (sync / "speckit_bundle_queue.json").write_text(json.dumps(queue), encoding="utf-8")

        for relpath in (
            ".specify/sync/speckit_bundle_prompts/claude/bundle-a/prompt.md",
            ".specify/sync/speckit_bundle_prompts/devin/bundle-a/prompt.md",
        ):
            path = workspace / relpath
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# prompt\n", encoding="utf-8")

        (workspace / "CLAUDE.md").write_text(
            "# Claude Launch Shim\n\n<!-- HLDSPEC-AGENT-CONTEXT:BEGIN -->\nold marker\n<!-- HLDSPEC-AGENT-CONTEXT:END -->\n",
            encoding="utf-8",
        )
        (workspace / ".devin").mkdir(parents=True, exist_ok=True)
        (workspace / ".devin" / "instructions.md").write_text(
            "# Devin Launch Shim\n\n<!-- HLDSPEC-AGENT-CONTEXT:BEGIN -->\nold marker\n<!-- HLDSPEC-AGENT-CONTEXT:END -->\n",
            encoding="utf-8",
        )
        (workspace / "AGENTS.md").write_text("# Universal Agent Instructions\n", encoding="utf-8")
        return workspace

    def test_write_agent_context_handoff_updates_only_active_runtime_files(self) -> None:
        workspace = self.make_workspace()
        before_agents = (workspace / "AGENTS.md").read_text(encoding="utf-8")

        result = write_agent_context_handoff(workspace)

        self.assertEqual("PASS", result["status"])
        self.assertEqual(["claude", "devin"], result["active_runtimes"])
        self.assertEqual(before_agents, (workspace / "AGENTS.md").read_text(encoding="utf-8"))

        handoff = workspace / ".hldspec-run" / "hldspec-gap-agent-context-handoff.md"
        self.assertTrue(handoff.exists())
        handoff_text = handoff.read_text(encoding="utf-8")
        self.assertIn("## Problem", handoff_text)
        self.assertIn("## Root cause", handoff_text)
        self.assertIn("## Required change", handoff_text)
        self.assertIn("## Idempotency", handoff_text)
        self.assertIn("## SPECKIT zone protection", handoff_text)
        self.assertIn("## Acceptance criteria", handoff_text)
        self.assertIn("## Secondary gap", handoff_text)
        self.assertIn("## Build Loop", handoff_text)

        claude = (workspace / "CLAUDE.md").read_text(encoding="utf-8")
        devin = (workspace / ".devin" / "instructions.md").read_text(encoding="utf-8")
        self.assertIn("## Build Loop", claude)
        self.assertIn("## Build Loop", devin)
        self.assertLess(claude.index("## Build Loop"), claude.index(MARKER_BEGIN))
        self.assertLess(devin.index("## Build Loop"), devin.index(MARKER_BEGIN))
        self.assertEqual(1, claude.count("## Build Loop"))
        self.assertEqual(1, devin.count("## Build Loop"))

    def test_write_agent_context_handoff_is_idempotent(self) -> None:
        workspace = self.make_workspace()

        first = write_agent_context_handoff(workspace)
        second = write_agent_context_handoff(workspace)

        self.assertEqual("PASS", first["status"])
        self.assertEqual("PASS", second["status"])
        self.assertEqual(1, (workspace / "CLAUDE.md").read_text(encoding="utf-8").count("## Build Loop"))
        self.assertEqual(1, (workspace / ".devin" / "instructions.md").read_text(encoding="utf-8").count("## Build Loop"))


if __name__ == "__main__":
    unittest.main()
