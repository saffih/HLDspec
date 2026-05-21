from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


HLD = """# HLD

## HLD-001 - HTTP API

HLD-ID: HLD-001
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: API behavior is covered.

HTTP API behavior.

## HLD-002 - Lessons Learned

HLD-ID: HLD-002
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: Context is preserved.

Historical notes.

## HLD-003 - Milestones

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: Milestone context is preserved.

Milestone notes.

## HLD-004 - Database API

HLD-ID: HLD-004
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 007
HLD-RESOURCES: TBD
HLD-VERIFY: Explicit spec mapping is preserved.

Database API behavior.
"""


class HldSectionClassificationTests(unittest.TestCase):
    def test_classification_marks_context_sections_not_spec_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld = workspace / "HLD.md"
            hld.write_text(HLD, encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "classify_hld_sections.py"),
                    str(hld),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            data = json.loads((workspace / ".specify" / "sync" / "hld_section_classification.json").read_text(encoding="utf-8"))
            by_id = {item["hld_id"]: item for item in data["sections"]}
            self.assertTrue(by_id["HLD-001"]["spec_candidate"])
            self.assertFalse(by_id["HLD-002"]["spec_candidate"])
            self.assertFalse(by_id["HLD-003"]["spec_candidate"])
            self.assertTrue(by_id["HLD-004"]["spec_candidate"])
            self.assertEqual(["007"], by_id["HLD-004"]["explicit_hld_specs"])

    def test_spec_build_plan_skips_context_only_sections(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld = workspace / "HLD.md"
            hld.write_text(HLD, encoding="utf-8")

            classify = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "classify_hld_sections.py"),
                    str(hld),
                    str(workspace),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, classify.returncode, msg=classify.stderr)

            plan = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "hld_spec_sync.py"),
                    "--workspace",
                    str(workspace),
                    "--hld",
                    str(hld),
                    "--use-hld-map",
                    "--plan-specs",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, plan.returncode, msg=plan.stderr)

            plan_json = json.loads((workspace / ".specify" / "sync" / "spec_build_plan.json").read_text(encoding="utf-8"))
            planned_source_ids = {
                source
                for spec in plan_json["planned_specs"]
                for source in spec["source_hld_sections"]
            }
            self.assertIn("HLD-001", planned_source_ids)
            self.assertIn("HLD-004", planned_source_ids)
            self.assertNotIn("HLD-002", planned_source_ids)
            self.assertNotIn("HLD-003", planned_source_ids)
            context_ids = {item["hld_id"] for item in plan_json["context_hld_sections"]}
            self.assertIn("HLD-002", context_ids)
            self.assertIn("HLD-003", context_ids)


if __name__ == "__main__":
    unittest.main()
