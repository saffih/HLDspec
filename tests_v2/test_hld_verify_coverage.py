from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "hld_verify_coverage.py"

HLD = """# Test HLD

## HLD-001 - Critical Thing

HLD-ID: HLD-001
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: the critical thing holds

### Purpose

Body.

## HLD-002 - Minor Thing

HLD-ID: HLD-002
HLD-ROLE: reference
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

### Purpose

Body.
"""


class HldVerifyCoverageTest(unittest.TestCase):
    def _run(self, hld: Path, tests_dir: Path, *extra: str):
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--hld", str(hld),
             "--tests", str(tests_dir), "--strict", *extra],
            capture_output=True, text=True,
        )

    def test_pass_when_high_risk_anchor_is_cited(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hld = root / "HLD.md"
            hld.write_text(HLD)
            (root / "test_x.py").write_text("# covers HLD-001\ndef test_x():\n    pass\n")
            r = self._run(hld, root)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("PASS", r.stdout)

    def test_fail_when_high_risk_anchor_uncited(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hld = root / "HLD.md"
            hld.write_text(HLD)
            (root / "test_x.py").write_text("def test_x():\n    pass\n")  # no citation
            r = self._run(hld, root)
            self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
            self.assertIn("HLD-001", r.stdout)
            # LOW-risk anchors are never required.
            self.assertNotIn("HLD-002", r.stdout)

    def test_waive_suppresses_failure(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            hld = root / "HLD.md"
            hld.write_text(HLD)
            (root / "test_x.py").write_text("def test_x():\n    pass\n")
            r = self._run(hld, root, "--waive", "HLD-001")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
