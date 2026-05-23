from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


HLD_TEXT = """# Test HLD

## HLD-001 - Stakeholder Analysis

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: context informs planning only

Users and stakeholders need the system to stay simple.

## HLD-002 - Session API Interface

HLD-ID: HLD-002
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: API contract can be tested with request and response examples

The system exposes a CLI command and API interface for starting a session. It records state in JSON artifacts.

## HLD-003 - Processing Workflow

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: workflow can be tested from input HLD to output artifacts

The workflow processes the session after the API contract exists. DEPENDS REF HLD-002

## HLD-004 - Decision Log

HLD-ID: HLD-004
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: decisions remain visible

Decision log for architecture tradeoffs.
"""


class HldUsecaseApiMapTest(unittest.TestCase):
    def test_map_separates_context_and_buildable_features(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(HLD_TEXT, encoding="utf-8")

            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "classify_hld_sections.py"), str(hld_path), str(workspace)],
                check=True,
                cwd=ROOT,
            )
            subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "build_hld_usecase_api_map.py"), str(hld_path), str(workspace)],
                check=True,
                cwd=ROOT,
            )

            data = json.loads((workspace / ".specify" / "sync" / "hld_usecase_api_map.json").read_text(encoding="utf-8"))
            self.assertEqual(data["status"], "ready")

            feature_ids = {item["hld_id"] for item in data["feature_candidates"]}
            context_ids = {item["hld_id"] for item in data["context_only_sections"]}

            self.assertIn("HLD-001", context_ids)
            self.assertIn("HLD-004", context_ids)
            self.assertNotIn("HLD-001", feature_ids)
            self.assertIn("HLD-002", feature_ids)
            self.assertIn("HLD-003", feature_ids)
            self.assertEqual(data["first_buildable_feature"]["hld_id"], "HLD-002")
            self.assertGreaterEqual(len(data["api_interface_surfaces"]), 1)
            self.assertGreaterEqual(len(data["data_source_of_truth_objects"]), 1)


if __name__ == "__main__":
    unittest.main()
