from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


state_mod = load_module("build_hldspec_state", "scripts/build_hldspec_state.py")


class HldspecStatePriorityTest(unittest.TestCase):
    def test_converted_hld_ignores_stale_conversion_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            converted_hld = (
                "# Converted HLD\n\n"
                "## HLD-001 - Foundation\n\n"
                "HLD-ID: HLD-001\n"
                "HLD-ROLE: API\n"
                "HLD-STATUS: Accepted\n"
                "HLD-RISK: Low\n"
                "HLD-SPECS: 001\n"
                "HLD-RESOURCES: TBD\n"
            )
            (workspace / "HLD.md").write_text(converted_hld, encoding="utf-8")
            (sync / "hld_conversion_decision_queue.json").write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "Q-001",
                                "blocking": True,
                                "human_decision": "TBD",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "hld_conversion_decision_queue.md").write_text("# stale\n", encoding="utf-8")

            state = state_mod.build_state(workspace, "/source/HLD.md")

            self.assertNotEqual(state["current_stage"], "CONVERSION_CHECKPOINT")
            self.assertNotEqual(state["current_checkpoint"], "hld_conversion_decisions")
            self.assertIn(
                "Ignored stale conversion queue because the working HLD is already in HLDspec format.",
                state["notes"],
            )

    def test_raw_hld_still_blocks_on_conversion_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)

            (workspace / "HLD.md").write_text("# Raw HLD\n\nNo HLDspec section markers yet.\n", encoding="utf-8")
            (sync / "hld_conversion_decision_queue.json").write_text(
                json.dumps(
                    {
                        "questions": [
                            {
                                "question_id": "Q-001",
                                "blocking": True,
                                "human_decision": "TBD",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            (sync / "hld_conversion_decision_queue.md").write_text("# queue\n", encoding="utf-8")

            state = state_mod.build_state(workspace, "/source/HLD.md")

            self.assertEqual(state["current_stage"], "CONVERSION_CHECKPOINT")
            self.assertEqual(state["current_checkpoint"], "hld_conversion_decisions")
            self.assertEqual(state["blocking_questions"][0]["open_question_count"], 1)


if __name__ == "__main__":
    unittest.main()
