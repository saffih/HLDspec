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

    def test_open_questions_only_for_genuine_gaps(self) -> None:
        # Detectors must not mint human checkpoint questions the HLD already answers:
        # a descriptive/low-risk TBD field and a rhetorical "?" are not questions; a
        # clean single HLD-ROLE already declares the API/processing boundary. Only a
        # HIGH-risk spec-candidate with a TBD governing spec is a real gap.
        hld = """# Detector HLD

## HLD-001 - What it is

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

Does this system stay simple? Yes. It is a descriptive purpose section.

## HLD-002 - The CLI contract

HLD-ID: HLD-002
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: constitution
HLD-RESOURCES: flow.py

The CLI command interface exposes verbs. It processes each request and runs the workflow that records state.

## HLD-003 - Core engine

HLD-ID: HLD-003
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: engine.py
HLD-VERIFY: the engine processes the queue and stores state in the database

The engine processes the API request and persists state to the database.
"""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(hld, encoding="utf-8")
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

            types = {q["type"] for q in data["open_questions"]}
            tbd_sections = {
                str(s) for q in data["open_questions"] if q["type"] == "metadata_tbd"
                for s in q["source_hld_sections"]
            }
            # A rhetorical "?" never mints a question.
            self.assertNotIn("question_mark_in_hld", types)
            # Descriptive low-risk TBD is not a gap; HIGH-risk spec-candidate TBD is.
            self.assertNotIn("HLD-001", tbd_sections)
            self.assertIn("HLD-003", tbd_sections)
            # A clean single HLD-ROLE declares the boundary -> no api/processing split.
            risks = {tuple(a["source_hld_sections"]): a["contract_risk"] for a in data["api_interface_surfaces"]}
            self.assertEqual(risks.get(("HLD-002",)), "normal")


if __name__ == "__main__":
    unittest.main()
