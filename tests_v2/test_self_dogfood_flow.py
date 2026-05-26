from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class SelfDogfoodFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_hldspec(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(self.repo / "scripts" / "hldspec"), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_python_script(self, script: str, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(self.repo / "scripts" / script), *args],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_minimal_spec_packages(self, target: Path) -> None:
        path = target / ".hldspec" / "spec_packages.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "packages": [
                        {
                            "package_id": "001-hldspec-self-dogfood",
                            "package_name": "HLDspec self dogfood",
                            "description": "Smoke package for running HLDspec on its own backlog evidence.",
                        }
                    ]
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    def test_hldspec_can_run_self_dogfood_smoke_flow(self) -> None:
        source = self.repo / "docs" / "HLDSPEC_DEVELOPMENT_BACKLOG.md"
        target = self.tmp_path / "self-dogfood-target"
        before = source.read_text(encoding="utf-8")

        start = self.run_hldspec(
            "start",
            "--source",
            str(source),
            "--target",
            str(target),
            "--comment",
            "self dogfood smoke test; do not invoke SpecKit",
        )
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        status_before = self.run_hldspec("status", "--target", str(target))
        self.assertEqual(0, status_before.returncode, status_before.stderr + status_before.stdout)
        self.assertIn("## Next Safe Action", status_before.stdout)

        review = self.run_hldspec("review", "--target", str(target))
        self.assertEqual(0, review.returncode, review.stderr + review.stdout)
        self.assertIn("## Blocking Review Files", review.stdout)
        self.assertIn("## Optional Context Files", review.stdout)
        self.assertIn("## Next Safe Action", review.stdout)

        doctor_before = self.run_hldspec("doctor", "--target", str(target))
        self.assertEqual(0, doctor_before.returncode, doctor_before.stderr + doctor_before.stdout)
        self.assertIn("## Final Summary", doctor_before.stdout)

        self.write_minimal_spec_packages(target)

        build = self.run_python_script("build_speckit_context_prompts.py", str(target))
        self.assertEqual(0, build.returncode, build.stderr + build.stdout)

        validate = self.run_python_script("validate_hldspec_target.py", str(target))
        self.assertEqual(0, validate.returncode, validate.stderr + validate.stdout)

        promote = self.run_python_script("check_hldspec_promotion_gate.py", str(target))
        self.assertEqual(0, promote.returncode, promote.stderr + promote.stdout)

        status_after = self.run_hldspec("status", "--target", str(target))
        self.assertEqual(0, status_after.returncode, status_after.stderr + status_after.stdout)
        self.assertIn("Validation status: PASS", status_after.stdout)
        self.assertIn("Promotion gate status: PASS", status_after.stdout)

        self.assertEqual(before, source.read_text(encoding="utf-8"))

        required_paths = [
            target / ".hldspec" / "agent_session.json",
            target / ".hldspec" / "interview_answers.json",
            target / ".hldspec" / "interview_answers.md",
            target / ".hldspec" / "allowed_evidence.json",
            target / ".hldspec" / "forbidden_reads.md",
            target / ".hldspec" / "context_packs" / "001-hldspec-self-dogfood" / "context_pack.json",
            target / ".hldspec" / "validation" / "context_prompt_validation.json",
            target / ".hldspec" / "validation" / "context_prompt_validation.md",
            target / ".hldspec" / "validation" / "promotion_gate.json",
            target / ".hldspec" / "validation" / "promotion_gate.md",
            target / "prompts" / "speckit" / "001-hldspec-self-dogfood" / "01-specify.md",
            target / "prompts" / "speckit" / "001-hldspec-self-dogfood" / "07-verify-runskeptic.md",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), path)

        validation_report = json.loads(
            (target / ".hldspec" / "validation" / "context_prompt_validation.json").read_text(encoding="utf-8")
        )
        promotion_report = json.loads(
            (target / ".hldspec" / "validation" / "promotion_gate.json").read_text(encoding="utf-8")
        )
        self.assertEqual("PASS", validation_report["status"])
        self.assertEqual("PASS", promotion_report["status"])


if __name__ == "__main__":
    unittest.main()
