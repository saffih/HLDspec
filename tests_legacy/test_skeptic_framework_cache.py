from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RunSkepticFrameworkCacheTests(unittest.TestCase):
    def test_skeptic_framework_cache_declares_real_skeptic_source(self) -> None:
        cache = json.loads((ROOT / "docs" / "skeptic_framework_cache.json").read_text(encoding="utf-8"))
        self.assertEqual("saffih/skeptic", cache["authoritative_source"]["repository"])
        self.assertEqual("skeptic.md", cache["authoritative_source"]["path"])
        self.assertEqual(
            "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
            cache["phase_flow_text"],
        )
        self.assertIn("SH", cache["thinkers"])
        self.assertIn("INFERRED_RISK", cache["evidence_levels"])

    def test_writer_copies_cache_to_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "write_skeptic_cache.py"),
                    td,
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            workspace_cache = Path(td) / ".specify" / "sync" / "skeptic_framework_cache.json"
            self.assertTrue(workspace_cache.exists())
            data = json.loads(workspace_cache.read_text(encoding="utf-8"))
            self.assertEqual("saffih/skeptic", data["authoritative_source"]["repository"])

    def test_first_run_writes_RunSkeptic_cache_and_cycles_reference_framework(self) -> None:
        hld = '''# HLD

## HLD-001 - API

HLD-ID: HLD-001
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: api
HLD-VERIFY: API behavior is covered.

API body.
'''
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td) / "work"
            source = Path(td) / "HLD.md"
            source.write_text(hld, encoding="utf-8")

            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts" / "first_run_readonly.sh"),
                    str(source),
                    str(workspace),
                    "--force",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stderr + result.stdout)

            cache_path = workspace / ".specify" / "sync" / "skeptic_framework_cache.json"
            self.assertTrue(cache_path.exists())
            plan = json.loads((workspace / ".specify" / "sync" / "spec_build_plan.json").read_text(encoding="utf-8"))
            cycles = plan["plan_quality"]["RunSkeptic_cycles"]
            self.assertTrue(cycles)
            self.assertEqual("saffih/skeptic", cycles[0]["framework"]["source"]["repository"])
            self.assertEqual(
                "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
                cycles[0]["framework"]["phase_flow_text"],
            )

    def test_RunSkeptic_cache_includes_companion_question_bank(self) -> None:
        cache = json.loads((ROOT / "docs" / "skeptic_framework_cache.json").read_text(encoding="utf-8"))
        companion_paths = [item["path"] for item in cache.get("companion_sources", [])]
        self.assertIn("skeptic-questions.md", companion_paths)
        bank = cache["domain_question_bank"]
        self.assertEqual("saffih/skeptic/skeptic-questions.md", bank["source"])
        self.assertIn("SEC", bank["questions"])
        self.assertIn("DAT", bank["questions"])
        self.assertIn("ARC", bank["questions"])
        self.assertGreaterEqual(len(bank["questions"]["SEC"]), 8)
        self.assertIn("ACTION", bank["finding_classification"])


if __name__ == "__main__":
    unittest.main()
