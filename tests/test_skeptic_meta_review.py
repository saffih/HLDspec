from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunSkepticMetaReviewTests(unittest.TestCase):
    def test_meta_review_generates_many_cycles(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_skeptic_meta_review.py"),
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
            report = json.loads((out / "hldspec_skeptic_meta_review.json").read_text(encoding="utf-8"))
            self.assertGreaterEqual(report["summary"]["total_cycles"], 40)

            areas = {cycle["area"] for cycle in report["cycles"]}
            for expected in {
                "RunSkeptic",
                "canonical flow",
                "SpecKit boundary",
                "judge protocol",
                "constitution",
                "API decomposition",
                "safety",
                "tests",
            }:
                self.assertIn(expected, areas)

            md = (out / "hldspec_skeptic_meta_review.md").read_text(encoding="utf-8")
            self.assertIn("HLDspec RunSkeptic Meta Review", md)
            self.assertIn("Highest priority findings", md)


if __name__ == "__main__":
    unittest.main()
