from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class HldspecArchitectureReviewTests(unittest.TestCase):
    def test_architecture_review_script_outputs_runskeptic_evidence_fields(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "review_hldspec_architecture.py"),
                    "--repo",
                    str(ROOT),
                    "--output-dir",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((out / "hldspec_architecture_review.json").read_text(encoding="utf-8"))

            self.assertIn(data["status"], {"PASS", "ACTION"})
            self.assertIn("summary", data)
            self.assertIn("findings", data)

            required = {
                "observed_evidence",
                "evidence_level",
                "confidence",
                "unknowns",
                "verification",
                "residual_risk",
            }
            for finding in data["findings"]:
                self.assertTrue(required.issubset(finding.keys()))

    def test_architecture_review_detects_shell_embedded_python(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td)
            scripts = repo / "scripts"
            tests = repo / "tests"
            scripts.mkdir()
            tests.mkdir()
            (scripts / "mixed.sh").write_text(
                "#!/usr/bin/env bash\npython3 - <<'PY'\nprint('mixed')\nPY\n",
                encoding="utf-8",
            )
            (tests / "test_mixed.py").write_text("def test_mixed():\n    assert True\n", encoding="utf-8")

            out = repo / "out"
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "review_hldspec_architecture.py"),
                    "--repo",
                    str(repo),
                    "--output-dir",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((out / "hldspec_architecture_review.json").read_text(encoding="utf-8"))
            issues = "\n".join(finding["issue"] for finding in data["findings"])
            self.assertIn("Shell script embeds Python logic.", issues)

    def test_architecture_doc_exists(self) -> None:
        text = (ROOT / "docs" / "HLDSPEC_ARCHITECTURE_REVIEW.md").read_text(encoding="utf-8")
        self.assertIn("Uncle Bob", text)
        self.assertIn("SRP", text)
        self.assertIn("RunSkeptic", text)
        self.assertIn("Fix one seam per patch", text)


if __name__ == "__main__":
    unittest.main()
