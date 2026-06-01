from __future__ import annotations

import importlib.util
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


arch = load_module("build_hldspec_architecture_analysis", "scripts/build_hldspec_architecture_analysis.py")


HLD_TEXT = """# Scope-aware analysis fixture

## HLD-001 - Excluded Surface

HLD-ID: HLD-001
HLD-DESC: HLD-001 is out-of-scope governance at low risk, touching none; "HTTP API stripped".

This section mentions an HTTP API endpoint that must stay excluded from analysis.

## HLD-002 - In Scope API Surface

HLD-ID: HLD-002
HLD-DESC: HLD-002 is in-scope api at high risk, touching api; "the service exposes an HTTP API endpoint".

This section defines the public HTTP API endpoint and its request/response contract.
"""


class ArchAnalysisScopeAwareTests(unittest.TestCase):
    def test_excluded_sections_skip_keyword_classification(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(HLD_TEXT, encoding="utf-8")

            result = arch.build_analysis(workspace, explicit_hld=str(hld_path))

            excluded = next(section for section in result["sections"] if section["hld_id"] == "HLD-001")
            self.assertEqual(excluded["layer"], "governance")
            self.assertFalse(excluded["spec_candidate"])
            self.assertFalse(excluded["requires_layered_split"])
            self.assertEqual(excluded["findings"], [])
            self.assertFalse(any(f["hld_id"] == "HLD-001" for f in result["findings"]))


if __name__ == "__main__":
    unittest.main()
