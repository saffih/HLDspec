from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


CLEAN_SEPARATED_HLD = """# Clean HLD

## HLD-001 - Governance Foundation

HLD-ID: HLD-001
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: governance
HLD-VERIFY: Governance rules are documented.

Governance and source of truth rules.

## HLD-002 - Data State Model

HLD-ID: HLD-002
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: data state
HLD-VERIFY: Data ownership is documented.

Owns persisted state only.

## HLD-003 - API Contract

HLD-ID: HLD-003
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: api contract
HLD-VERIFY: API request and response contract is documented.

Owns API contract only.

## HLD-004 - Processing Flow

HLD-ID: HLD-004
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: processing flow
HLD-VERIFY: Processing workflow is documented.

Owns processing behavior only.
"""


MIXED_HLD = """# Mixed HLD

## HLD-001 - API Data Processing Combined

HLD-ID: HLD-001
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: api data processing
HLD-VERIFY: Combined behavior is described.

This owns the API contract, data state, and processing workflow in one section.
"""


CONFLICT_HLD = """# Conflict HLD

## HLD-001 - API Contract

HLD-ID: HLD-001
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: api contract
HLD-VERIFY: API contract is documented.

CONFLICTS_WITH REF HLD-002

## HLD-002 - Competing API Contract

HLD-ID: HLD-002
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: api contract
HLD-VERIFY: Competing API contract is documented.

Conflicting contract.
"""


def run_first_run(hld_text: str) -> dict[str, object]:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        source = root / "HLD.md"
        workspace = root / "work"
        source.write_text(hld_text, encoding="utf-8")

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

        if result.returncode != 0:
            raise AssertionError(result.stderr + result.stdout)

        plan_path = workspace / ".specify" / "sync" / "spec_build_plan.json"
        return json.loads(plan_path.read_text(encoding="utf-8"))


class SpecBuildPlanQualityGateFixtureTests(unittest.TestCase):
    def test_clean_separated_hld_keeps_plan_without_flags(self) -> None:
        plan = run_first_run(CLEAN_SEPARATED_HLD)
        quality = plan["plan_quality"]

        self.assertEqual("FIX", quality["decision"])
        self.assertEqual("KEEP_PLAN", quality["recommendation"])

        flagged = [item for item in plan["planned_specs"] if item.get("quality_flags")]
        self.assertEqual([], flagged)

    def test_mixed_api_data_processing_hld_decomposes(self) -> None:
        plan = run_first_run(MIXED_HLD)
        quality = plan["plan_quality"]

        self.assertEqual("DECOMPOSE", quality["decision"])
        self.assertEqual("SPLIT_PLANNED_SPEC", quality["recommendation"])
        self.assertIn("mixed_responsibilities", plan["planned_specs"][0]["quality_flags"])

    def test_explicit_conflict_hld_blocks_as_conflict(self) -> None:
        plan = run_first_run(CONFLICT_HLD)
        quality = plan["plan_quality"]

        self.assertEqual("CONFLICT", quality["decision"])
        self.assertEqual("RESOLVE_CONFLICT", quality["recommendation"])
        self.assertTrue(quality["conflicts"])


if __name__ == "__main__":
    unittest.main()
