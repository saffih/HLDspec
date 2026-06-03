from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec.machines.spec_build_plan import SpecBuildPlanMachine
from hldspec.state_machine import MachineContext, MachineStatus


ROOT = Path(__file__).resolve().parents[1]


class SpecBuildPlanGateDecisionTests(unittest.TestCase):
    def make_workspace_with_flagged_plan(self) -> tuple[Path, Path]:
        work = Path(tempfile.mkdtemp())
        sync = work / "firstrun" / ".specify" / "sync"
        sync.mkdir(parents=True)
        (sync / "spec_build_plan_review.md").write_text("Continue to SpecKit prework: `false`\n", encoding="utf-8")
        (sync / "spec_build_plan.json").write_text(
            json.dumps(
                {
                    "plan_quality": {
                        "decision": "DECOMPOSE",
                        "recommendation": "SPLIT_PLANNED_SPEC",
                        "conflicts": [],
                    },
                    "planned_specs": [
                        {
                            "planned_spec_id": "010",
                            "title": "Flow Core Database API",
                            "quality_flags": ["data_api_boundary_needs_review"],
                            "requires_user_review": True,
                            "recommendation": "KEEP_SPEC",
                        },
                        {
                            "planned_spec_id": "019",
                            "title": "Database API Interface",
                            "quality_flags": ["data_api_boundary_needs_review"],
                            "requires_user_review": True,
                            "recommendation": "KEEP_SPEC",
                        },
                    ],
                }
            ),
            encoding="utf-8",
        )
        return work, sync

    def test_accept_with_rationale_allows_non_green_plan_to_continue(self) -> None:
        work, sync = self.make_workspace_with_flagged_plan()
        (sync / "spec_build_plan_gate_decision.json").write_text(
            json.dumps(
                {
                    "decision_id": "SPEC-BUILD-PLAN-001",
                    "decision": "ACCEPT_WITH_RATIONALE",
                    "rationale": "Both flagged specs are intentional critical API boundaries.",
                    "accepted_flagged_specs": ["010", "019"],
                }
            ),
            encoding="utf-8",
        )

        result = SpecBuildPlanMachine().run(
            MachineContext(repo_root=str(ROOT), source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.CONTINUE, result.status)
        self.assertEqual("SPEC_BUILD_PLAN_ACCEPTED_WITH_RATIONALE", result.state)

    def test_accept_missing_flagged_spec_stays_checkpoint(self) -> None:
        work, sync = self.make_workspace_with_flagged_plan()
        (sync / "spec_build_plan_gate_decision.json").write_text(
            json.dumps(
                {
                    "decision_id": "SPEC-BUILD-PLAN-001",
                    "decision": "ACCEPT_WITH_RATIONALE",
                    "rationale": "Only one accepted.",
                    "accepted_flagged_specs": ["010"],
                }
            ),
            encoding="utf-8",
        )

        result = SpecBuildPlanMachine().run(
            MachineContext(repo_root=str(ROOT), source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.STOP_CHECKPOINT, result.status)
        assert result.checkpoint is not None
        self.assertIn("Missing: 019", result.checkpoint.blocking_reason)

    def test_helper_writes_decision_file(self) -> None:
        _, sync = self.make_workspace_with_flagged_plan()

        result = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "hldspec_v2_answer_spec_plan_gate.py"),
                str(sync),
                "--decision",
                "ACCEPT_WITH_RATIONALE",
                "--rationale",
                "Intentional critical interface specs.",
                "--accept-flagged-spec",
                "010",
                "--accept-flagged-spec",
                "019",
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        self.assertEqual(0, result.returncode, msg=result.stderr + result.stdout)
        data = json.loads((sync / "spec_build_plan_gate_decision.json").read_text(encoding="utf-8"))
        self.assertEqual("ACCEPT_WITH_RATIONALE", data["decision"])
        self.assertEqual(["010", "019"], data["accepted_flagged_specs"])


if __name__ == "__main__":
    unittest.main()
