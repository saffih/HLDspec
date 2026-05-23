from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RAW = """# Demo HLD

## IMPORTANT: Single Source of Truth

This HLD is authoritative.

## Component Deep-Dive

### 1. Core Data Model

Defines data ownership.

### 2. HTTP API

Defines endpoint contracts.

## Component Interface Definitions

### Database API Interface

Database contract.

### CLI Command Interface

CLI contract.
"""


class ConvertHldToHldspecTests(unittest.TestCase):
    def test_converts_raw_hld_with_default_flow_splits(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            raw = work / "HLD.md"
            out = work / "HLD.hldspec.md"
            idx = work / "index.md"
            raw.write_text(RAW, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "convert_hld_to_hldspec.py"),
                    str(raw),
                    "--output",
                    str(out),
                    "--index-output",
                    str(idx),
                    "--default-flow-splits",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            text = out.read_text(encoding="utf-8")

            self.assertIn("## HLD-001 - IMPORTANT: Single Source of Truth", text)
            self.assertIn("## HLD-002 - Core Data Model", text)
            self.assertIn("## HLD-003 - HTTP API", text)
            self.assertIn("## HLD-004 - Database API Interface", text)
            self.assertIn("HLD-ID: HLD-001", text)
            self.assertIn("HLD-ROLE:", text)
            self.assertIn("HLD-VERIFY:", text)
            self.assertNotIn("## Component Deep-Dive", text)
            self.assertNotIn("## Component Interface Definitions", text)
            self.assertIn("Original parent section: Component Deep-Dive", text)

            index = idx.read_text(encoding="utf-8")
            self.assertIn("Converted sections: 5", index)
            self.assertIn("HLD-005", index)

    def test_refuses_to_overwrite_without_flag(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            raw = work / "HLD.md"
            out = work / "HLD.hldspec.md"
            raw.write_text(RAW, encoding="utf-8")
            out.write_text("existing", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "convert_hld_to_hldspec.py"),
                    str(raw),
                    "--output",
                    str(out),
                    "--default-flow-splits",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertNotEqual(0, result.returncode)
            self.assertIn("output already exists", result.stderr)


if __name__ == "__main__":
    unittest.main()
