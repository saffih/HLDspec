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


class TestHasFirstRunArtifacts(unittest.TestCase):
    def setUp(self):
        self.mod = load_module("build_hldspec_state", SCRIPTS / "build_hldspec_state.py")

    def _sync(self, tmp: str) -> Path:
        sync = Path(tmp) / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        return sync

    def test_missing_one_file_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            write_text(sync / "spec_build_plan_review.md", "review")
            write_json(sync / "speckit_prework_quality_review.json", {"status": "ok"})
            # speckit_prework_package.md is missing
            self.assertFalse(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_invalid_json_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            write_text(sync / "spec_build_plan_review.md", "review")
            (sync / "speckit_prework_quality_review.json").write_text("not valid json{{{", encoding="utf-8")
            write_text(sync / "speckit_prework_package.md", "package")
            self.assertFalse(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_all_present_and_valid_returns_true(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            write_text(sync / "spec_build_plan_review.md", "review")
            write_json(sync / "speckit_prework_quality_review.json", {"status": "ok"})
            write_text(sync / "speckit_prework_package.md", "package")
            self.assertTrue(self.mod.has_first_run_artifacts(Path(tmp)))

    def test_only_one_of_four_files_returns_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            sync = self._sync(tmp)
            write_json(sync / "spec_build_plan.json", {"ok": True})
            # other 3 missing
            self.assertFalse(self.mod.has_first_run_artifacts(Path(tmp)))


if __name__ == "__main__":
    unittest.main()
