"""Tests for gate enforcement in approve_hldspec_prework.py and build_hldspec_state.py."""
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SCRIPTS = Path(__file__).parent.parent / "scripts"


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_prework_package(sync: Path) -> None:
    write_json(sync / "speckit_prework_package.json", {
        "schema_version": 1,
        "human_checkpoint": {
            "options": ["APPROVE_PLAN", "MODIFY_PLAN", "DECOMPOSE_MORE", "FIX_CONSTITUTION", "REBUILD_DEPENDENCY_GRAPH"],
            "human_decision": "TBD",
        },
    })


class TestApproveEnforcement(unittest.TestCase):
    def setUp(self):
        self.mod = load_module("approve_hldspec_prework", SCRIPTS / "approve_hldspec_prework.py")

    def _sync(self, tmp: str) -> Path:
        sync = Path(tmp) / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        return sync

    def test_blocker_in_prework_quality_review_blocks_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            write_json(sync / "speckit_prework_quality_review.json", {
                "findings": [
                    {"id": "QG-015", "severity": "BLOCKER", "finding": "No contract rules."},
                ],
            })
            with self.assertRaises(ValueError) as ctx:
                self.mod.approve_prework(Path(tmp), "APPROVE_PLAN")
            self.assertIn("QG-015", str(ctx.exception))

    def test_blocker_in_dossier_quality_review_blocks_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {
                "findings": [
                    {"id": "ADQ-002", "severity": "BLOCKER", "finding": "No contracts."},
                ],
            })
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            with self.assertRaises(ValueError) as ctx:
                self.mod.approve_prework(Path(tmp), "APPROVE_PLAN")
            self.assertIn("ADQ-002", str(ctx.exception))

    def test_no_blockers_allows_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {
                "findings": [{"id": "ADQ-014", "severity": "ACTION", "finding": "action only"}],
            })
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            record = self.mod.approve_prework(Path(tmp), "APPROVE_PLAN")
            self.assertEqual(record["status"], "APPROVED")

    def test_missing_dossier_quality_review_blocks_approval(self):
        # Absent evidence is not the same as clean evidence — gate must fail closed.
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            # hld_answer_dossier_quality_review.json deliberately not written
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            with self.assertRaises(ValueError) as ctx:
                self.mod.approve_prework(Path(tmp), "APPROVE_PLAN")
            self.assertIn("MISSING_hld_answer_dossier_quality_review.json", str(ctx.exception))

    def test_missing_prework_quality_review_blocks_approval(self):
        # Both review files are required; absent prework review must also block.
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            # speckit_prework_quality_review.json deliberately not written
            with self.assertRaises(ValueError) as ctx:
                self.mod.approve_prework(Path(tmp), "APPROVE_PLAN")
            self.assertIn("MISSING_speckit_prework_quality_review.json", str(ctx.exception))

    def test_action_only_does_not_block_approval(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            write_json(sync / "speckit_prework_quality_review.json", {
                "findings": [
                    {"id": "QG-004", "severity": "ACTION", "finding": "decomposition suggestion"},
                    {"id": "QG-016", "severity": "ACTION", "finding": "one contract uncovered"},
                ],
            })
            record = self.mod.approve_prework(Path(tmp), "APPROVE_PLAN")
            self.assertEqual(record["status"], "APPROVED")

    def test_agent_actor_produces_warning(self):
        """Actor=agent approval is allowed but must carry a warning."""
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            record = self.mod.approve_prework(Path(tmp), "APPROVE_PLAN", actor="agent")
            self.assertEqual(record["status"], "APPROVED")
            self.assertEqual(record["actor"], "agent")
            self.assertTrue(len(record["warnings"]) > 0, "agent approval must carry a warning")
            self.assertIn("actor", record["warnings"][0])

    def test_human_actor_produces_no_warning(self):
        """Actor=human approval must produce zero warnings."""
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            _minimal_prework_package(sync)
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            record = self.mod.approve_prework(Path(tmp), "APPROVE_PLAN", actor="human")
            self.assertEqual(record["actor"], "human")
            self.assertEqual(record["warnings"], [], "human approval must have no warnings")


class TestHasFirstRunArtifacts(unittest.TestCase):
    def setUp(self):
        self.mod = load_module("build_hldspec_state", SCRIPTS / "build_hldspec_state.py")

    def _sync(self, tmp: str) -> Path:
        sync = Path(tmp) / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        return sync

    def test_partial_artifacts_are_detected(self):
        # Three of four files: still a first-run workspace (mid-flight checkpoint).
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            write_text(sync / "spec_build_plan_review.md", "review")
            write_json(sync / "speckit_prework_quality_review.json", {"status": "ok"})
            # speckit_prework_package.md is absent — prework not yet generated
            self.assertTrue(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_invalid_json_does_not_block_detection(self):
        # All four files are present; JSON validity is not part of detection.
        # A temporarily-corrupt JSON must not misroute build_state to workspace/firstrun.
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            write_text(sync / "spec_build_plan_review.md", "review")
            (sync / "speckit_prework_quality_review.json").write_text("not valid json{{{", encoding="utf-8")
            write_text(sync / "speckit_prework_package.md", "package")
            self.assertTrue(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_all_present_and_valid_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            write_text(sync / "spec_build_plan_review.md", "review")
            write_json(sync / "speckit_prework_quality_review.json", {"status": "ok"})
            write_text(sync / "speckit_prework_package.md", "package")
            self.assertTrue(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_single_artifact_is_detected(self):
        # Even one known first-run file is enough to identify the workspace.
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            # other 3 not yet written
            self.assertTrue(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_no_artifacts_returns_false(self):
        # Empty sync dir: not a first-run workspace at all.
        with tempfile.TemporaryDirectory() as tmp:
            self._sync(tmp)  # creates dir, writes nothing
            self.assertFalse(self.mod.has_first_run_artifacts(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
