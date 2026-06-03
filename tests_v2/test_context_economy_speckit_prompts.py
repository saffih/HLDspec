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
    EXPECTED_PHASE_TIERS = {
        "01-specify": "MODEL_STRONG",
        "02-clarify": "MODEL_STRONG",
        "03-plan": "MODEL_CRITICAL",
        "04-research-data-contracts": "MODEL_CRITICAL",
        "05-tasks": "MODEL_STRONG",
        "06-implement": "MODEL_STRONG",
        "07-verify-runskeptic": "MODEL_CRITICAL",
    }

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

    def build_prompts(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "build_speckit_context_prompts.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def validate_target(self, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "validate_hldspec_target.py"), str(target)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_generator_creates_context_artifacts_and_all_phase_prompts(self) -> None:
        target = self.make_target()
        result = self.build_prompts(target)
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

    def test_generated_prompts_use_canonical_phase_model_tiers(self) -> None:
        target = self.make_target()
        result = self.build_prompts(target)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        prompt_dir = target / "prompts" / "speckit" / "001-api-foundation"
        for phase_id, expected_tier in self.EXPECTED_PHASE_TIERS.items():
            prompt = prompt_dir / f"{phase_id}.md"
            text = prompt.read_text(encoding="utf-8")
            model_section = text.split("## Model tier", 1)[1].split("## ", 1)[0]
            self.assertIn(expected_tier, model_section, f"{phase_id} should use {expected_tier}")

    def test_validate_only_fails_when_prompt_missing_allowed_evidence(self) -> None:
        target = self.make_target()
        self.assertEqual(0, self.build_prompts(target).returncode)
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
        self.assertEqual(0, self.build_prompts(target).returncode)
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
        result = self.build_prompts(target)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
        self.assertEqual(before, source.read_text(encoding="utf-8"))

    def test_validator_passes_on_generated_context_prompts(self) -> None:
        target = self.make_target()
        source = target / "targetHLD" / "HLD.md"
        before = source.read_text(encoding="utf-8")
        self.assertEqual(0, self.build_prompts(target).returncode)

        result = self.validate_target(target)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        report = json.loads((target / ".hldspec" / "validation" / "context_prompt_validation.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", report["status"])
        self.assertEqual([], report["findings"])
        self.assertEqual(before, source.read_text(encoding="utf-8"))

    def test_validator_fails_when_allowed_evidence_is_missing(self) -> None:
        target = self.make_target()
        self.assertEqual(0, self.build_prompts(target).returncode)
        (target / ".hldspec" / "allowed_evidence.json").unlink()

        result = self.validate_target(target)
        self.assertEqual(result.returncode, 2)

        report = json.loads((target / ".hldspec" / "validation" / "context_prompt_validation.json").read_text(encoding="utf-8"))
        self.assertEqual("ACTION", report["status"])
        self.assertTrue(any(item["check"] == "allowed_evidence" for item in report["findings"]))

    def test_validator_fails_when_prompt_has_broad_read_phrase(self) -> None:
        target = self.make_target()
        self.assertEqual(0, self.build_prompts(target).returncode)
        prompt = target / "prompts" / "speckit" / "001-api-foundation" / "03-plan.md"
        prompt.write_text(prompt.read_text(encoding="utf-8") + "\nPlease read the whole repo before planning.\n", encoding="utf-8")

        result = self.validate_target(target)
        self.assertEqual(result.returncode, 2)

        report = json.loads((target / ".hldspec" / "validation" / "context_prompt_validation.json").read_text(encoding="utf-8"))
        self.assertTrue(any(item["check"] == "forbidden_broad_read" for item in report["findings"]))

    def test_validator_fails_when_implement_prompt_lacks_human_approval_guard(self) -> None:
        target = self.make_target()
        self.assertEqual(0, self.build_prompts(target).returncode)
        prompt = target / "prompts" / "speckit" / "001-api-foundation" / "06-implement.md"
        text = prompt.read_text(encoding="utf-8")
        text = text.replace("human approval", "maintainer review").replace("APPROVED", "accepted")
        prompt.write_text(text, encoding="utf-8")

        result = self.validate_target(target)
        self.assertEqual(result.returncode, 2)

        report = json.loads((target / ".hldspec" / "validation" / "context_prompt_validation.json").read_text(encoding="utf-8"))
        self.assertTrue(any(item["check"] == "implement_human_approval" for item in report["findings"]))

    def test_validator_writes_json_and_markdown_reports(self) -> None:
        target = self.make_target()
        self.assertEqual(0, self.build_prompts(target).returncode)
        result = self.validate_target(target)
        self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

        json_report = target / ".hldspec" / "validation" / "context_prompt_validation.json"
        md_report = target / ".hldspec" / "validation" / "context_prompt_validation.md"
        self.assertTrue(json_report.exists())
        self.assertTrue(md_report.exists())
        self.assertIn("Status: `PASS`", md_report.read_text(encoding="utf-8"))

    def test_validator_rejects_legacy_model_tier_names(self) -> None:
        target = self.make_target()
        self.assertEqual(0, self.build_prompts(target).returncode)
        prompt = target / "prompts" / "speckit" / "001-api-foundation" / "02-clarify.md"
        text = prompt.read_text(encoding="utf-8").replace("MODEL_STRONG", "MODEL_MEDIUM")
        prompt.write_text(text, encoding="utf-8")

        result = self.validate_target(target)
        self.assertEqual(result.returncode, 2)

        report = json.loads((target / ".hldspec" / "validation" / "context_prompt_validation.json").read_text(encoding="utf-8"))
        self.assertTrue(any(item["check"] == "model_tier" for item in report["findings"]))


if __name__ == "__main__":
    unittest.main()
