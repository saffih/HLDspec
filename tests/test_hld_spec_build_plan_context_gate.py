from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class HldSpecBuildPlanContextGateTest(unittest.TestCase):
    def run_cmd(self, args: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )

    def test_context_only_sections_are_not_planned_specs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(
                textwrap.dedent(
                    """
                    # Example HLD

                    ## HLD-001 - Stakeholder Analysis

                    HLD-ID: HLD-001
                    HLD-ROLE: purpose
                    HLD-STATUS: active
                    HLD-RISK: LOW
                    HLD-SPECS: TBD
                    HLD-RESOURCES: TBD

                    Stakeholders describe who cares about the system.

                    ## HLD-002 - Session API

                    HLD-ID: HLD-002
                    HLD-ROLE: api
                    HLD-STATUS: active
                    HLD-RISK: MEDIUM
                    HLD-SPECS: TBD
                    HLD-RESOURCES: TBD

                    The system exposes a bounded API for creating, reading, and closing sessions.
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            self.run_cmd([
                sys.executable,
                str(ROOT / "scripts" / "classify_hld_sections.py"),
                str(hld_path),
                str(workspace),
            ])
            self.run_cmd([
                sys.executable,
                str(ROOT / "hld_spec_sync.py"),
                "--workspace",
                str(workspace),
                "--hld",
                "HLD.md",
                "--plan-specs",
            ])

            classification = json.loads(
                (workspace / ".specify" / "sync" / "hld_section_classification.json").read_text(
                    encoding="utf-8"
                )
            )
            classifications = {item["hld_id"]: item for item in classification["sections"]}
            self.assertEqual(classifications["HLD-001"]["section_kind"], "HLD_CONTEXT_ONLY")
            self.assertFalse(classifications["HLD-001"]["spec_candidate"])
            self.assertEqual(classifications["HLD-002"]["section_kind"], "SPEC_CANDIDATE")
            self.assertTrue(classifications["HLD-002"]["spec_candidate"])

            plan = json.loads(
                (workspace / ".specify" / "sync" / "spec_build_plan.json").read_text(
                    encoding="utf-8"
                )
            )
            planned_titles = {item["title"] for item in plan["planned_specs"]}
            planned_source_ids = {
                source_id
                for item in plan["planned_specs"]
                for source_id in item["source_hld_sections"]
            }
            context_ids = {item["hld_id"] for item in plan["context_hld_sections"]}

            self.assertNotIn("Stakeholder Analysis", planned_titles)
            self.assertNotIn("HLD-001", planned_source_ids)
            self.assertIn("HLD-001", context_ids)
            self.assertIn("Session API", planned_titles)
            self.assertIn("HLD-002", planned_source_ids)

    def test_clean_plan_quality_reports_pass_not_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(
                textwrap.dedent(
                    """
                    # Example HLD

                    ## HLD-001 - Session API

                    HLD-ID: HLD-001
                    HLD-ROLE: api
                    HLD-STATUS: active
                    HLD-RISK: MEDIUM
                    HLD-SPECS: TBD
                    HLD-RESOURCES: TBD

                    The system exposes a bounded API for session lifecycle operations.
                    """
                ).lstrip(),
                encoding="utf-8",
            )

            self.run_cmd([
                sys.executable,
                str(ROOT / "scripts" / "classify_hld_sections.py"),
                str(hld_path),
                str(workspace),
            ])
            self.run_cmd([
                sys.executable,
                str(ROOT / "hld_spec_sync.py"),
                "--workspace",
                str(workspace),
                "--hld",
                "HLD.md",
                "--plan-specs",
            ])

            plan = json.loads(
                (workspace / ".specify" / "sync" / "spec_build_plan.json").read_text(
                    encoding="utf-8"
                )
            )
            quality = plan["plan_quality"]
            self.assertEqual(quality["findings"], [])
            self.assertEqual(quality["conflicts"], [])
            self.assertEqual(quality["decision"], "PASS")
            self.assertEqual(quality["recommendation"], "KEEP_PLAN")


if __name__ == "__main__":
    unittest.main()
