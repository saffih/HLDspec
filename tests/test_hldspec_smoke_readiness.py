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


readiness = load_module("run_hldspec_readiness_review", "scripts/run_hldspec_readiness_review.py")


class HldspecSmokeReadinessTest(unittest.TestCase):
    def test_missing_foundation_artifacts_requires_rework(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            review = readiness.build_review(workspace)
            self.assertEqual(review["status"], "REWORK_REQUIRED")
            self.assertTrue(review["missing_foundation_artifacts"])
            self.assertTrue(review["blockers"])

    def test_ready_after_approval_and_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            sync = workspace / ".specify" / "sync"
            sync.mkdir(parents=True)
            for rel in readiness.REQUIRED_FOUNDATION_ARTIFACTS:
                path = sync / rel.removeprefix(".specify/sync/")
                if path.suffix == ".json":
                    path.write_text(json.dumps({}), encoding="utf-8")
                else:
                    path.write_text("\n", encoding="utf-8")

            (sync / "hldspec_state.json").write_text(
                json.dumps({"current_stage": "SPECKIT_PREWORK_APPROVAL_GATE", "current_checkpoint": "human_approves_speckit_prework"}),
                encoding="utf-8",
            )
            (sync / "speckit_prework_quality_review.json").write_text(
                json.dumps({"status": "APPROVAL_READY", "findings": []}),
                encoding="utf-8",
            )
            (sync / "speckit_prework_package.json").write_text(
                json.dumps({"human_checkpoint": {"human_decision": "APPROVE_PLAN"}}),
                encoding="utf-8",
            )
            (sync / "speckit_proxy_dry_run.json").write_text(
                json.dumps({"status": "DRY_RUN_READY", "refusal_reasons": []}),
                encoding="utf-8",
            )

            review = readiness.build_review(workspace)
            self.assertEqual(review["status"], "READY_FOR_DRY_RUN_REVIEW")
            self.assertEqual(review["blockers"], [])


if __name__ == "__main__":
    unittest.main()
