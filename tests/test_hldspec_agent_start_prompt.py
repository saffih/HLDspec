from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent_start = load_module("build_hldspec_agent_start_prompt", "scripts/build_hldspec_agent_start_prompt.py")


class HldspecAgentStartPromptTest(unittest.TestCase):
    def test_start_prompt_prepares_workspace_copy_and_forbids_speckit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "HLD.md"
            workspace = root / "workspace"
            source.write_text("# Raw HLD\n\nContent\n", encoding="utf-8")

            context = agent_start.build_context(source, workspace, ROOT, force=False)
            json_path, md_path, trigger_path = agent_start.write_outputs(context, Path(context["workspace"]))
            prompt = md_path.read_text(encoding="utf-8")

            self.assertTrue((workspace / "HLD.raw.md").exists())
            self.assertTrue((workspace / "HLD.md").exists())
            self.assertEqual(context["current_stage"], "NOT_STARTED")
            self.assertIn("Do not invoke SpecKit", prompt)
            self.assertIn(str(source.resolve()), prompt)
            self.assertTrue(json_path.exists())
            self.assertTrue(trigger_path.exists())

    def test_minimal_trigger_is_short_and_not_full_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "HLD.md"
            workspace = root / "workspace"
            source.write_text("# Raw HLD\n\nContent\n", encoding="utf-8")

            context = agent_start.build_context(source, workspace, ROOT, force=False)
            _, _, trigger_path = agent_start.write_outputs(context, Path(context["workspace"]))
            trigger = trigger_path.read_text(encoding="utf-8").strip()

            self.assertEqual(trigger, f"HLDspec {source.resolve()} --workspace {workspace.resolve()}")
            self.assertLess(len(trigger), 240)
            self.assertNotIn("Forbidden actions", trigger)
            self.assertNotIn("Do not invoke SpecKit", trigger)

    def test_start_prompt_detects_conversion_checkpoint_and_adds_guide_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "HLD.md"
            workspace = root / "workspace"
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            source.write_text("# Raw HLD\n\nContent\n", encoding="utf-8")
            (sync / "hldspec_state.json").write_text(
                json.dumps(
                    {
                        "current_stage": "CONVERSION_CHECKPOINT",
                        "current_checkpoint": "hld_conversion_decisions",
                        "controlling_artifacts": [str(sync / "hld_conversion_decision_queue.md")],
                        "blocking_questions": [
                            {
                                "artifact": str(sync / "hld_conversion_decision_queue.json"),
                                "open_question_count": 1,
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            context = agent_start.build_context(source, workspace, ROOT, force=False)
            prompt = agent_start.render_prompt(context)

            self.assertEqual(context["current_stage"], "CONVERSION_CHECKPOINT")
            self.assertIn("hldspec_question_guide.sh", "\n".join(context["allowed_internal_commands"]))
            self.assertIn("CONVERSION_CHECKPOINT", prompt)
            self.assertIn("Run the question guide", prompt)

    def test_wrapper_default_output_is_not_full_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "HLD.md"
            workspace = root / "workspace"
            source.write_text("# Raw HLD\n\nContent\n", encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "hldspec_agent_start.sh"),
                    str(source),
                    "--workspace",
                    str(workspace),
                ],
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("HLDspec minimal agent trigger:", result.stdout)
            self.assertIn(f"HLDspec {source.resolve()} --workspace {workspace.resolve()}", result.stdout)
            self.assertNotIn("## Forbidden actions", result.stdout)
            self.assertNotIn("## Rules", result.stdout)


if __name__ == "__main__":
    unittest.main()
