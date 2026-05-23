from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build_hldspec_state = load_module("build_hldspec_state", "scripts/build_hldspec_state.py")
alignment = load_module("run_hldspec_alignment_review", "scripts/run_hldspec_alignment_review.py")


class HldspecStatusAndAlignmentTest(unittest.TestCase):
    def test_pass_keep_plan_reaches_prework_approval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / "firstrun" / ".specify" / "sync"
            sync.mkdir(parents=True)

            hld_text = "\n".join(
                [
                    "## HLD-001 - Session API Interface",
                    "",
                    "HLD-ID: HLD-001",
                    "HLD-ROLE: api",
                    "HLD-STATUS: active",
                    "HLD-RISK: LOW",
                    "HLD-SPECS: TBD",
                    "HLD-RESOURCES: TBD",
                    "",
                ]
            )
            (workspace / "HLD.md").write_text(hld_text, encoding="utf-8")

            (sync / "spec_build_plan_review.md").write_text(
                "Continue to target-spec generation: `true`\n",
                encoding="utf-8",
            )
            (sync / "spec_build_plan.json").write_text(
                json.dumps(
                    {
                        "planned_specs": [
                            {
                                "planned_spec_id": "001",
                                "title": "Session API Interface",
                                "quality_flags": [],
                                "requires_user_review": False,
                            }
                        ],
                        "plan_quality": {
                            "decision": "PASS",
                            "recommendation": "KEEP_PLAN",
                            "conflicts": [],
                            "findings": [],
                        },
                    }
                ),
                encoding="utf-8",
            )
            (sync / "spec_build_plan_decision_queue.json").write_text(
                json.dumps({"questions": []}),
                encoding="utf-8",
            )
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps({"status": "APPROVAL_READY", "findings": []}),
                encoding="utf-8",
            )

            state = build_hldspec_state.build_state(workspace, "source.md")
            self.assertEqual(state["current_stage"], "SPECKIT_PREWORK_APPROVAL_GATE")
            self.assertEqual(state["current_checkpoint"], "human_approves_speckit_prework")

    def test_product_alignment_review_passes_without_blockers(self) -> None:
        review = alignment.run_alignment_review(ROOT)
        blockers = [item for item in review["findings"] if item["severity"] == "BLOCKER"]
        self.assertEqual(blockers, [], msg=json.dumps(review["findings"], indent=2, sort_keys=True))
        self.assertEqual(review["status"], "PASS_WITH_DEFERRED_ITEMS")


if __name__ == "__main__":
    unittest.main()
