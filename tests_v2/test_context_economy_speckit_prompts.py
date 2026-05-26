from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec.context_economy import PHASES, validate_prompt_file

ROOT = Path(__file__).resolve().parents[1]


class ContextEconomySpecKitPromptTests(unittest.TestCase):
    def make_target(self) -> Path:
        tmp = Path(tempfile.mkdtemp())
        target = tmp / "target"
        (target / "targetHLD").mkdir(parents=True)
        (target / "targetHLD" / "HLD.md").write_text("# HLD\n\n## HLD-001 - API\n\nBody.\n", encoding="utf-8")
        (target / ".hldspec").mkdir(parents=True)
        (target / ".hldspec" / "spec_packages.json").write_text(
            json.dumps(
                {
                    "packages": [
                        {
                            "package_id": "001-api-foundation",
                            "package_name": "API foundation",
                            "description": "First bounded package.",
                        }
                    ]
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return target

    def test_generator_creates_context_artifacts_and_all_phase_prompts(self) -> None:
        target = self.make_target()
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        allowed = target / ".hldspec" / "allowed_evidence.json"
        forbidden = target / ".hldspec" / "forbidden_reads.md"
        context_pack = target / ".hldspec" / "context_packs" / "001-api-foundation" / "context_pack.json"
        prompt_dir = target / "prompts" / "speckit" / "001-api-foundation"

        self.assertTrue(allowed.exists())
        self.assertTrue(forbidden.exists())
        self.assertTrue(context_pack.exists())
        payload = json.loads(allowed.read_text(encoding="utf-8"))
        self.assertEqual("1.0", payload["schema_version"])
        self.assertEqual("001-api-foundation", payload["packages"][0]["package_id"])
        self.assertIn("targetHLD/HLD.md", payload["packages"][0]["allowed_evidence"])

        for phase_id, _phase_name, _model_tier in PHASES:
            prompt = prompt_dir / f"{phase_id}.md"
            self.assertTrue(prompt.exists(), prompt)
            text = prompt.read_text(encoding="utf-8")
            self.assertIn("## Allowed evidence", text)
            self.assertIn("## Forbidden reads", text)
            self.assertIn("## Model tier", text)
            self.assertIn("## Stop condition", text)
            self.assertIn("## RunSkeptic triggers", text)
            self.assertEqual([], validate_prompt_file(prompt))

    def test_validate_only_fails_when_prompt_missing_allowed_evidence(self) -> None:
        target = self.make_target()
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        prompt = target / "prompts" / "speckit" / "001-api-foundation" / "01-specify.md"
        text = prompt.read_text(encoding="utf-8")
        prompt.write_text(text.replace("## Allowed evidence", "## Evidence"), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target), "--validate-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Allowed evidence", result.stdout)

    def test_validate_only_fails_when_prompt_missing_runskeptic_trigger(self) -> None:
        target = self.make_target()
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        prompt = target / "prompts" / "speckit" / "001-api-foundation" / "07-verify-runskeptic.md"
        text = prompt.read_text(encoding="utf-8")
        prompt.write_text(text.replace("## RunSkeptic triggers", "## Review triggers"), encoding="utf-8")

        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target), "--validate-only"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("RunSkeptic triggers", result.stdout)

    def test_generator_does_not_modify_source_hld(self) -> None:
        target = self.make_target()
        source = target / "targetHLD" / "HLD.md"
        before = source.read_text(encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(before, source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
