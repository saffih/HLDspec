from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepoSyncContractTests(unittest.TestCase):
    def test_shell_wrappers_use_project_local_uv_cache(self) -> None:
        for rel in [
            "scripts/first_run_readonly.sh",
            "scripts/project_first_run.sh",
            "scripts/project_continue.sh",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("PYTHON_RUN=(uv run python)", text)
            self.assertIn('export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.hldspec-uv-cache}"', text)

    def test_project_continue_checkpoint_calls_are_indented_and_present(self) -> None:
        text = (ROOT / "scripts/project_continue.sh").read_text(encoding="utf-8")
        self.assertIn('    "${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_decision_log.py" "$WORK" --source-hld "$SOURCE_HLD"', text)
        self.assertIn('    "${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_source_update_queue.py" "$WORK" --source-hld "$SOURCE_HLD"', text)
        self.assertNotIn('\n"${PYTHON_RUN[@]}" "$ROOT/scripts/write_hld_source_update_queue.py"', text)

    def test_required_checkpoint_scripts_exist(self) -> None:
        for rel in [
            "scripts/write_beskeptic_cache.py",
            "scripts/write_hld_decision_log.py",
            "scripts/write_hld_source_update_queue.py",
            "scripts/build_spec_plan_decision_queue.py",
        ]:
            self.assertTrue((ROOT / rel).exists(), rel)

    def test_first_run_builds_spec_plan_decision_queue(self) -> None:
        text = (ROOT / "scripts/first_run_readonly.sh").read_text(encoding="utf-8")
        self.assertIn("build_spec_plan_decision_queue.py", text)
        self.assertIn("spec_build_plan_decision_queue.md", text)


if __name__ == "__main__":
    unittest.main()
