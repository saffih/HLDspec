from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


RAW_HLD = """# Raw

## Parent

intro

### A

a body

### B

b body

## Milestones

milestone body
"""


def write_plan_and_queue(workspace: Path, *, answered: bool) -> tuple[Path, Path, Path]:
    hld = workspace / "HLD.md"
    hld.write_text(RAW_HLD, encoding="utf-8")
    sync = workspace / ".specify" / "sync"
    sync.mkdir(parents=True)
    plan = {
        "candidates": [
            {
                "proposed_hld_id": "HLD-001",
                "title": "Parent",
                "source_line_start": 3,
                "source_line_end": 13,
                "proposed_role": "architecture",
                "proposed_risk": "MEDIUM",
                "metadata_skeleton": {"HLD-SPECS": "TBD", "HLD-RESOURCES": "TBD"},
            },
            {
                "proposed_hld_id": "HLD-002",
                "title": "Milestones",
                "source_line_start": 15,
                "source_line_end": 17,
                "proposed_role": "processing",
                "proposed_risk": "LOW",
                "metadata_skeleton": {"HLD-SPECS": "TBD", "HLD-RESOURCES": "TBD"},
            },
        ]
    }
    queue = {
        "plan_path": str(sync / "hld_conversion_plan.json"),
        "questions": [
            {
                "question_id": "Q-001",
                "source_candidate_id": "HLD-001",
                "human_decision": "SPLIT_AS_PROPOSED" if answered else "TBD",
                "default_proposal": {
                    "proposed_split_plan": [
                        {"proposed_hld_id": "HLD-001A", "title": "A", "source_line_start": 7, "source_line_end": 10},
                        {"proposed_hld_id": "HLD-001B", "title": "B", "source_line_start": 11, "source_line_end": 13},
                    ]
                },
            },
            {
                "question_id": "Q-002",
                "source_candidate_id": "HLD-002",
                "human_decision": "KEEP_AS_ONE" if answered else "TBD",
                "approved_keep_reason": "large but cohesive" if answered else "",
            },
        ],
    }
    plan_path = sync / "hld_conversion_plan.json"
    queue_path = sync / "hld_conversion_decision_queue.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    queue_path.write_text(json.dumps(queue), encoding="utf-8")
    return hld, plan_path, queue_path


class ApplyHldConversionDecisionsTests(unittest.TestCase):
    def test_refuses_tbd_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld, _plan, queue = write_plan_and_queue(workspace, answered=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "apply_hld_conversion_decisions.py"),
                    str(hld),
                    str(queue),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("human_decision is TBD", result.stdout)

    def test_applies_split_and_keep_decisions_preserving_content(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld, _plan, queue = write_plan_and_queue(workspace, answered=True)
            result = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "apply_hld_conversion_decisions.py"),
                    str(hld),
                    str(queue),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(0, result.returncode, msg=result.stderr)
            converted = hld.read_text(encoding="utf-8")
            self.assertIn("## HLD-001A - A", converted)
            self.assertIn("## HLD-001B - B", converted)
            self.assertIn("## HLD-002 - Milestones", converted)
            self.assertIn("## Parent", converted)
            self.assertIn("### A", converted)
            self.assertIn("### B", converted)
            self.assertTrue(hld.with_suffix(".md.pre-hldspec.bak").exists())


if __name__ == "__main__":
    unittest.main()
