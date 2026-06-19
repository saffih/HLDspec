from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from hldspec import refresh_target as rt
from hldspec import next_feature_agents_md as nfa

_CLI_PATH = Path(__file__).resolve().parents[1] / "scripts" / "hldspec_refresh_target.py"


def _load_cli():
    spec = importlib.util.spec_from_file_location("hldspec_refresh_target_cli", _CLI_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(target: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target), *argv],
        text=True,
        capture_output=True,
        check=True,
    )


class RefreshTargetTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-refresh-target-")
        self.target = Path(self._tmp.name)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _agents_md_path(self) -> Path:
        sync = rt.control_paths.resolve_control_sync_dir(self.target, create=False)
        return sync / nfa.BOOTSTRAP_FILE

    def _constitution_path(self) -> Path:
        return self.target / rt.CONSTITUTION_RELPATH

    # 1. dry-run makes no writes.
    def test_dry_run_makes_no_writes(self) -> None:
        plan = rt.refresh_target(self.target, apply=False)
        self.assertEqual(plan["mode"], "DRY_RUN")
        self.assertFalse(self._agents_md_path().exists())
        self.assertFalse(self._constitution_path().exists())
        self.assertGreater(len(plan["planned_updates"]), 0)

    # 2. apply creates missing HLDspec helper file.
    def test_apply_creates_missing_agents_md(self) -> None:
        result = rt.refresh_target(self.target, apply=True)
        self.assertEqual(result["mode"], "APPLIED")
        path = self._agents_md_path()
        self.assertTrue(path.is_file())
        self.assertIn(str(path.relative_to(self.target)), result["written_files"])

    # 3. apply updates HLDspec-owned helper file.
    def test_apply_updates_existing_agents_md(self) -> None:
        rt.refresh_target(self.target, apply=True)
        path = self._agents_md_path()
        path.write_text("stale content", encoding="utf-8")

        result = rt.refresh_target(self.target, apply=True)

        self.assertIn(str(path.relative_to(self.target)), result["written_files"])
        self.assertNotEqual(path.read_text(encoding="utf-8"), "stale content")
        self.assertIn("Next feature", path.read_text(encoding="utf-8"))

    # 4. missing constitution can be created safely.
    def test_apply_creates_missing_constitution(self) -> None:
        result = rt.refresh_target(self.target, apply=True)

        path = self._constitution_path()
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn(rt.MANAGED_BEGIN, text)
        self.assertIn(rt.MANAGED_END, text)
        self.assertIn(str(rt.CONSTITUTION_RELPATH), result["written_files"])
        self.assertEqual(result["constitution_status"]["classification"], rt.MISSING_CAN_CREATE)

    # 5. unchanged/managed constitution can be updated safely.
    def test_apply_refreshes_managed_constitution_preserving_project_rules(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        project_rule = "## Project-Specific Rules\n\n- Always use widgets, never gadgets.\n"
        path.write_text(f"# Project Constitution\n\n{rt.managed_block()}\n\n{project_rule}", encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)
        self.assertEqual(plan["constitution_status"]["classification"], rt.OWNED_BY_SPECKIT_SAFE_TO_REFRESH)

        result = rt.refresh_target(self.target, apply=True)

        text = path.read_text(encoding="utf-8")
        self.assertIn("Always use widgets, never gadgets.", text)
        self.assertIn(rt.MANAGED_BEGIN, text)
        self.assertIn(rt.MANAGED_END, text)
        backup = path.with_name(path.name + rt.CONSTITUTION_BACKUP_SUFFIX)
        self.assertTrue(backup.is_file())
        self.assertIn(str(backup.relative_to(self.target)), result["backup_files"])

        # Re-running is idempotent: project rules still preserved, still classified safe-to-refresh.
        plan2 = rt.build_refresh_plan(self.target)
        self.assertEqual(plan2["constitution_status"]["classification"], rt.OWNED_BY_SPECKIT_SAFE_TO_REFRESH)
        rt.refresh_target(self.target, apply=True)
        self.assertIn("Always use widgets, never gadgets.", path.read_text(encoding="utf-8"))

    # 6. edited constitution is not overwritten and is reported as review-required.
    def test_unmanaged_constitution_is_not_overwritten(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        custom_text = "# Our Project Constitution\n\nHand-written rules, no HLDspec markers here.\n"
        path.write_text(custom_text, encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)
        self.assertEqual(plan["constitution_status"]["classification"], rt.EXISTS_WITH_LOCAL_CHANGES_REQUIRES_REVIEW)
        self.assertEqual(len(plan["conflict_files"]), 1)

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(path.read_text(encoding="utf-8"), custom_text)
        self.assertNotIn(str(rt.CONSTITUTION_RELPATH), result["written_files"])
        self.assertTrue(result["review_files"])
        review_path = self.target / result["review_files"][0]
        self.assertTrue(review_path.is_file())
        self.assertIn(rt.MANAGED_BEGIN, review_path.read_text(encoding="utf-8"))

    # 7. existing unowned file is not overwritten.
    def test_unowned_file_is_left_untouched(self) -> None:
        sync = rt.control_paths.resolve_control_sync_dir(self.target, create=True)
        other = sync / "some_other_file.md"
        other.write_text("do not touch", encoding="utf-8")

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(other.read_text(encoding="utf-8"), "do not touch")
        self.assertNotIn(str(other.relative_to(self.target)), result["written_files"])

    # 8. existing specs/<branch>/spec.md, plan.md, tasks.md are not modified.
    def test_spec_progress_artifacts_are_not_modified(self) -> None:
        spec_dir = self.target / "specs" / "001-feature"
        spec_dir.mkdir(parents=True)
        artifacts = {}
        for name in ("spec.md", "plan.md", "tasks.md"):
            text = f"# {name}\n\noriginal content\n"
            (spec_dir / name).write_text(text, encoding="utf-8")
            artifacts[name] = text

        rt.refresh_target(self.target, apply=True)

        for name, text in artifacts.items():
            self.assertEqual((spec_dir / name).read_text(encoding="utf-8"), text)

    # 9. dirty target repo is not reset/stashed/cleaned.
    def test_dirty_target_is_not_reset_or_cleaned(self) -> None:
        dirty_file = self.target / "src_file.txt"
        dirty_file.write_text("work in progress", encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)
        self.assertTrue(plan["git_dirty"])

        rt.refresh_target(self.target, apply=True)

        self.assertEqual(dirty_file.read_text(encoding="utf-8"), "work in progress")
        status = _git(self.target, "status", "--porcelain").stdout
        self.assertIn("src_file.txt", status)

    # 10. product files are never touched.
    def test_product_files_are_never_touched(self) -> None:
        product_file = self.target / "src" / "app.py"
        product_file.parent.mkdir(parents=True)
        product_text = "def main():\n    pass\n"
        product_file.write_text(product_text, encoding="utf-8")

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(product_file.read_text(encoding="utf-8"), product_text)
        self.assertNotIn(str(product_file.relative_to(self.target)), result["written_files"])

    # 11. refresh output reports skipped/conflict files.
    def test_output_reports_skipped_and_conflict_files(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Hand-written constitution, no markers\n", encoding="utf-8")

        plan = rt.build_refresh_plan(self.target)

        self.assertIn("skipped_files", plan)
        self.assertIn("conflict_files", plan)
        self.assertEqual(len(plan["conflict_files"]), 1)
        self.assertEqual(plan["conflict_files"][0]["path"], str(rt.CONSTITUTION_RELPATH))

    # 12. "speckit status" wording maps to full run card/gap evaluation.
    def test_run_card_pointer_points_to_status_driver(self) -> None:
        plan = rt.build_refresh_plan(self.target)
        pointer = plan["run_card_pointer"]
        self.assertIn("speckit status", pointer)
        self.assertIn("SpecKit run card", pointer)
        self.assertIn("next_feature_readiness_report.py", pointer)

    # ------------------------------------------------------------------
    # Target-local run-card wrapper (self-guiding helper)
    # ------------------------------------------------------------------

    def _run_card_path(self) -> Path:
        return self.target / rt.RUN_CARD_RELPATH

    # 13. apply installs the read-only run-card wrapper, executable.
    def test_apply_installs_run_card_wrapper(self) -> None:
        result = rt.refresh_target(self.target, apply=True)

        path = self._run_card_path()
        self.assertTrue(path.is_file())
        self.assertIn(str(rt.RUN_CARD_RELPATH), result["written_files"])
        # Executable bit set so `.hldspec/bin/run-card` runs directly.
        self.assertTrue(path.stat().st_mode & 0o111)

    # 14. the wrapper is read-only and runs the vendored runtime (no checkout path).
    def test_run_card_wrapper_is_read_only_and_self_contained(self) -> None:
        rt.refresh_target(self.target, apply=True)
        text = self._run_card_path().read_text(encoding="utf-8")

        self.assertIn("READ-ONLY", text)
        self.assertIn("runtime/run_card_main.py", text)
        # Self-contained: the wrapper never USES $HLDSPEC_HOME and bakes in no checkout path.
        self.assertNotIn("$HLDSPEC_HOME", text)
        self.assertNotIn("HLDSPEC_HOME=", text)
        hldspec_checkout = str(Path(rt.__file__).resolve().parents[1])
        self.assertNotIn(hldspec_checkout, text)
        # Must not run any generation/mutation itself.
        for forbidden in ("/speckit", "git commit", "git push", "git checkout", "specify init"):
            self.assertNotIn(forbidden, text)

    # 15. wrapper derives the target root from its own location, fails clearly if runtime missing.
    def test_run_card_wrapper_self_locates_and_errors_on_missing_runtime(self) -> None:
        rt.refresh_target(self.target, apply=True)
        text = self._run_card_path().read_text(encoding="utf-8")

        self.assertIn("BASH_SOURCE", text)
        self.assertIn("vendored runtime missing", text)
        self.assertIn("refresh-target --apply", text)

    # 16. regenerating the wrapper is idempotent and re-marks it executable.
    def test_run_card_wrapper_regenerates_idempotently(self) -> None:
        rt.refresh_target(self.target, apply=True)
        path = self._run_card_path()
        path.write_text("stale\n", encoding="utf-8")
        path.chmod(0o644)

        plan = rt.build_refresh_plan(self.target)
        item = next(i for i in plan["items"] if i["path"] == str(rt.RUN_CARD_RELPATH))
        self.assertEqual(item["classification"], rt.OWNED_BY_HLDSPEC_SAFE_TO_UPDATE)

        rt.refresh_target(self.target, apply=True)
        self.assertNotIn("stale", path.read_text(encoding="utf-8"))
        self.assertIn("READ-ONLY", path.read_text(encoding="utf-8"))
        self.assertTrue(path.stat().st_mode & 0o111)

    # ------------------------------------------------------------------
    # Vendored self-contained runtime
    # ------------------------------------------------------------------

    def _runtime_dir(self) -> Path:
        return self.target / rt.RUNTIME_RELDIR

    # 1 + 2. apply writes run-card wrapper and the vendored runtime.
    def test_apply_installs_vendored_runtime(self) -> None:
        result = rt.refresh_target(self.target, apply=True)

        self.assertIn(str(rt.RUN_CARD_RELPATH), result["written_files"])
        runtime = self._runtime_dir()
        self.assertTrue((runtime / "run_card_main.py").is_file())
        self.assertTrue((runtime / "MANIFEST.json").is_file())
        self.assertTrue((runtime / "VERSION").is_file())
        self.assertTrue((runtime / "hldspec" / "next_feature_readiness.py").is_file())
        # The runtime bundle is reported as written.
        self.assertIn(str(rt.RUNTIME_RELDIR / "run_card_main.py"), result["written_files"])

    # 3. runtime files are classified OWNED_BY_HLDSPEC_SAFE_TO_UPDATE once present.
    def test_runtime_classified_owned_by_hldspec(self) -> None:
        rt.refresh_target(self.target, apply=True)
        plan = rt.build_refresh_plan(self.target)
        item = next(i for i in plan["items"] if i["path"] == str(rt.RUNTIME_RELDIR))
        self.assertEqual(item["classification"], rt.OWNED_BY_HLDSPEC_SAFE_TO_UPDATE)

    # 4. the vendored runtime does not import from the HLDspec checkout.
    def test_vendored_runtime_has_no_checkout_import(self) -> None:
        rt.refresh_target(self.target, apply=True)
        checkout = str(Path(rt.__file__).resolve().parents[1])
        for path in self._runtime_dir().rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn(checkout, text, path)
            # No env-var lookup of HLDSPEC_HOME anywhere in the vendored runtime.
            self.assertNotIn('"HLDSPEC_HOME"', text, path)
            self.assertNotIn("'HLDSPEC_HOME'", text, path)

    # 5 + 6. the vendored runtime produces the key report fields, using only .hldspec/runtime.
    def test_vendored_runtime_produces_key_fields_self_contained(self) -> None:
        (self.target / ".specify" / "memory").mkdir(parents=True)
        rt.refresh_target(self.target, apply=True)
        import os

        env = {k: v for k, v in os.environ.items() if k not in ("HLDSPEC_HOME", "PYTHONPATH")}
        # Drive the entry directly (not via the wrapper) to assert no checkout on sys.path.
        completed = subprocess.run(
            ["python3", str(self._runtime_dir() / "run_card_main.py"), "--target", str(self.target)],
            cwd="/",  # run from / to prove no implicit checkout on the path
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        for field in (
            "## Phase",
            "## Setup readiness",
            "## Next safe action",
            "## Recommended model",
            "## Agent / model guidance",
            "## Blockers",
            "## Do not run yet",
        ):
            self.assertIn(field, completed.stdout)

    # 7. missing runtime gives a clear error from the wrapper.
    def test_missing_runtime_wrapper_errors_clearly(self) -> None:
        rt.refresh_target(self.target, apply=True)
        # Remove the vendored entry to simulate a missing/corrupt runtime.
        (self._runtime_dir() / "run_card_main.py").unlink()
        completed = subprocess.run(
            ["bash", str(self._run_card_path())],
            cwd=str(self.target),
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("vendored runtime missing", completed.stderr)
        self.assertIn("refresh-target --apply", completed.stderr)

    # 8. runtime execution is read-only: no git mutation, no specs/product writes.
    def test_runtime_execution_is_read_only(self) -> None:
        (self.target / ".specify" / "memory").mkdir(parents=True)
        product = self.target / "src" / "app.py"
        product.parent.mkdir(parents=True)
        product.write_text("x = 1\n", encoding="utf-8")
        rt.refresh_target(self.target, apply=True)

        subprocess.run(
            ["bash", str(self._run_card_path())],
            cwd=str(self.target), text=True, capture_output=True,
        )
        # Product untouched; no commits/branches created by the read-only runtime.
        self.assertEqual(product.read_text(encoding="utf-8"), "x = 1\n")
        branch = _git(self.target, "branch", "--show-current").stdout.strip()
        self.assertNotIn("-", branch)

    # Minimality: the installer (runtime_vendor) and unrelated modules are NOT vendored.
    def test_vendored_runtime_is_minimal(self) -> None:
        rt.refresh_target(self.target, apply=True)
        vendored = {p.stem for p in (self._runtime_dir() / "hldspec").glob("*.py")}
        self.assertIn("next_feature_readiness", vendored)
        self.assertNotIn("runtime_vendor", vendored)  # installer never ships
        # Unrelated core modules not on the run-card path stay out.
        for unrelated in ("result_renderer", "reply_parser", "prework_contracts", "handoff_docs"):
            self.assertNotIn(unrelated, vendored)

    # MANIFEST records version + source commit + the file list.
    def test_runtime_manifest_shape(self) -> None:
        rt.refresh_target(self.target, apply=True)
        manifest = json.loads((self._runtime_dir() / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["generated_by"], "hldspec refresh-target")
        self.assertIn("runtime_version", manifest)
        self.assertIn("source_commit", manifest)
        self.assertIn(str(rt.RUNTIME_RELDIR / "run_card_main.py"), manifest["files"])

    # MANIFEST records the identity of the helper/toolchain this runtime is.
    def test_runtime_manifest_records_helper_identity(self) -> None:
        rt.refresh_target(self.target, apply=True)
        manifest = json.loads((self._runtime_dir() / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["helper_id"], "speckit")
        self.assertEqual(manifest["toolchain"], "SpecKit")

    # Legacy manifests without helper identity must not crash the footer.
    def test_runtime_footer_handles_legacy_manifest_without_helper_identity(self) -> None:
        (self.target / ".specify" / "memory").mkdir(parents=True)
        rt.refresh_target(self.target, apply=True)
        manifest_path = self._runtime_dir() / "MANIFEST.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("helper_id", None)
        manifest.pop("toolchain", None)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        completed = subprocess.run(
            ["bash", str(self._run_card_path())],
            cwd=str(self.target),
            text=True,
            capture_output=True,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("Vendored run-card runtime", completed.stdout)
        self.assertNotIn("helper speckit", completed.stdout)

    # ------------------------------------------------------------------
    # Explicit constitution managed-block adoption
    # ------------------------------------------------------------------

    _UNMARKED = (
        "# Our Project Constitution\n\n"
        "## ARCH-001 Hexagonal\n\nPorts and adapters.\n\n"
        "## ENG-002 Testing\n\nBusiness logic coverage required.\n\n"
        "## Governance\n\nMaintainers approve changes.\n"
    )

    def _write_unmarked_constitution(self, text: str | None = None) -> Path:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text is not None else self._UNMARKED, encoding="utf-8")
        return path

    # 1. unmarked + normal dry-run does not modify constitution.
    def test_adopt_unmarked_dry_run_does_not_modify(self) -> None:
        path = self._write_unmarked_constitution()

        plan = rt.refresh_target(self.target, apply=False)

        self.assertEqual(path.read_text(encoding="utf-8"), self._UNMARKED)
        self.assertEqual(plan["constitution_status"]["classification"], rt.EXISTS_WITH_LOCAL_CHANGES_REQUIRES_REVIEW)
        self.assertTrue(plan["constitution_adoption"]["available"])
        self.assertIn(rt.ADOPT_FLAG, plan["constitution_adoption"]["command"])

    # 2. unmarked + --apply alone still does not modify constitution.
    def test_adopt_unmarked_apply_alone_does_not_modify(self) -> None:
        path = self._write_unmarked_constitution()

        result = rt.refresh_target(self.target, apply=True)

        self.assertEqual(path.read_text(encoding="utf-8"), self._UNMARKED)
        self.assertNotIn(str(rt.CONSTITUTION_RELPATH), result["written_files"])

    # 3 + 4 + 5 + 6. adoption: backup, exactly one block, byte-for-byte preserved, no project rules moved.
    def test_adoption_backs_up_inserts_one_block_and_preserves_content(self) -> None:
        path = self._write_unmarked_constitution()

        result = rt.refresh_target(self.target, adopt=True)

        self.assertEqual(result["mode"], "ADOPTED")
        self.assertEqual(result["adoption"]["state"], rt.ADOPTION_PERFORMED)
        # backup created with original bytes.
        backup = path.with_name(path.name + rt.CONSTITUTION_BACKUP_SUFFIX)
        self.assertTrue(backup.is_file())
        self.assertEqual(backup.read_text(encoding="utf-8"), self._UNMARKED)
        self.assertIn(str(backup.relative_to(self.target)), result["backup_files"])
        # exactly one managed block.
        new_text = path.read_text(encoding="utf-8")
        self.assertEqual(new_text.count(rt.MANAGED_BEGIN), 1)
        self.assertEqual(new_text.count(rt.MANAGED_END), 1)
        # managed block at top, blank line, then original content byte-for-byte.
        self.assertTrue(new_text.startswith(rt.managed_block() + "\n\n"))
        self.assertTrue(new_text.endswith(self._UNMARKED))
        self.assertEqual(new_text, rt.managed_block() + "\n\n" + self._UNMARKED)
        # project-owned sections are NOT inside the managed block.
        before, _block, after = new_text.partition(rt.MANAGED_END)
        for marker in ("ARCH-001", "ENG-002", "Governance"):
            self.assertNotIn(marker, before)
            self.assertIn(marker, after)

    # 7. adoption then dry-run reports OWNED_BY_SPECKIT_SAFE_TO_REFRESH.
    def test_adoption_then_dry_run_is_owned_safe_to_refresh(self) -> None:
        self._write_unmarked_constitution()
        rt.refresh_target(self.target, adopt=True)

        plan = rt.refresh_target(self.target, apply=False)

        self.assertEqual(plan["constitution_status"]["classification"], rt.OWNED_BY_SPECKIT_SAFE_TO_REFRESH)
        self.assertFalse(plan["constitution_adoption"]["available"])

    # 8. adoption then apply only updates content between markers.
    def test_adoption_then_apply_only_updates_managed_block(self) -> None:
        path = self._write_unmarked_constitution()
        rt.refresh_target(self.target, adopt=True)

        rt.refresh_target(self.target, apply=True)

        text = path.read_text(encoding="utf-8")
        # Original project sections untouched after a managed --apply.
        self.assertIn("## ARCH-001 Hexagonal", text)
        self.assertIn("Business logic coverage required.", text)
        self.assertIn("## Governance", text)
        self.assertEqual(text.count(rt.MANAGED_BEGIN), 1)

    # 9. partial marker state blocks adoption.
    def test_partial_markers_block_adoption(self) -> None:
        path = self._write_unmarked_constitution(
            f"# C\n\n{rt.MANAGED_BEGIN}\n\norphan begin only, no end marker.\n"
        )

        plan = rt.refresh_target(self.target, apply=False)
        self.assertEqual(plan["constitution_status"]["classification"], rt.CONFLICT_REQUIRES_HUMAN)

        result = rt.refresh_target(self.target, adopt=True)
        self.assertEqual(result["adoption"]["state"], rt.ADOPTION_PARTIAL_MARKERS_CONFLICT)
        self.assertFalse(result["adoption"]["performed"])
        # Unchanged and no backup written.
        self.assertNotIn(rt.MANAGED_END, path.read_text(encoding="utf-8"))
        self.assertFalse(path.with_name(path.name + rt.CONSTITUTION_BACKUP_SUFFIX).exists())

    # 10. already-marked constitution does not get a duplicate block.
    def test_already_marked_adoption_is_noop(self) -> None:
        path = self._constitution_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# C\n\n{rt.managed_block()}\n\n## Project rules\n", encoding="utf-8")
        before = path.read_text(encoding="utf-8")

        result = rt.refresh_target(self.target, adopt=True)

        self.assertEqual(result["adoption"]["state"], rt.ADOPTION_ALREADY_MANAGED)
        self.assertFalse(result["adoption"]["performed"])
        self.assertEqual(path.read_text(encoding="utf-8"), before)
        self.assertEqual(path.read_text(encoding="utf-8").count(rt.MANAGED_BEGIN), 1)

    # 11. missing constitution still follows the create path (adoption is a no-op/declined).
    def test_missing_constitution_adoption_declined_create_path_intact(self) -> None:
        result = rt.refresh_target(self.target, adopt=True)
        self.assertEqual(result["adoption"]["state"], rt.ADOPTION_MISSING_CONSTITUTION)
        self.assertFalse(self._constitution_path().exists())

        # Normal --apply still creates a fresh managed constitution.
        rt.refresh_target(self.target, apply=True)
        text = self._constitution_path().read_text(encoding="utf-8")
        self.assertIn(rt.MANAGED_BEGIN, text)
        self.assertIn(rt.MANAGED_END, text)

    # 12. adoption never touches product code or specs/.
    def test_adoption_does_not_touch_product_or_specs(self) -> None:
        self._write_unmarked_constitution()
        product = self.target / "src" / "app.py"
        product.parent.mkdir(parents=True)
        product.write_text("def main():\n    pass\n", encoding="utf-8")
        spec_dir = self.target / "specs" / "001-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# spec\noriginal\n", encoding="utf-8")

        result = rt.refresh_target(self.target, adopt=True)

        self.assertEqual(product.read_text(encoding="utf-8"), "def main():\n    pass\n")
        self.assertEqual((spec_dir / "spec.md").read_text(encoding="utf-8"), "# spec\noriginal\n")
        self.assertEqual(result["written_files"], [str(rt.CONSTITUTION_RELPATH)])

    # 14. JSON-shaped result includes adoption state/result.
    def test_adoption_result_includes_adoption_state(self) -> None:
        self._write_unmarked_constitution()
        result = rt.refresh_target(self.target, adopt=True)
        self.assertIn("adoption", result)
        self.assertIn(result["adoption"]["state"], (rt.ADOPTION_PERFORMED,))
        self.assertEqual(result["adoption"]["marker_lines"]["begin"], 1)
        self.assertGreater(result["adoption"]["marker_lines"]["end"], 1)

    # 17. the generated wrapper produces a run card WITHOUT HLDSPEC_HOME or the checkout.
    def test_run_card_wrapper_executes_self_contained(self) -> None:
        # Make this a real SpecKit-initialised repo so the driver returns a phase.
        (self.target / ".specify" / "memory").mkdir(parents=True)
        rt.refresh_target(self.target, apply=True)

        import os

        # Strip HLDSPEC_HOME and PYTHONPATH so nothing can leak the HLDspec checkout.
        env = {k: v for k, v in os.environ.items() if k not in ("HLDSPEC_HOME", "PYTHONPATH")}
        completed = subprocess.run(
            ["bash", str(self._run_card_path())],
            cwd=str(self.target),
            text=True,
            capture_output=True,
            env=env,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("SpecKit Run Card", completed.stdout)
        self.assertIn("Vendored run-card runtime", completed.stdout)  # footer present
        self.assertIn("helper speckit", completed.stdout)  # footer surfaces helper identity
        self.assertIn("toolchain SpecKit", completed.stdout)
        # Read-only execution must not create a feature branch in the target repo.
        branch = _git(self.target, "branch", "--show-current").stdout.strip()
        self.assertNotIn("-", branch)  # no SpecKit-style NNN-feature branch was created


class RefreshTargetCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-refresh-cli-")
        self.target = Path(self._tmp.name)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")
        self.cli = _load_cli()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _constitution(self) -> Path:
        return self.target / rt.CONSTITUTION_RELPATH

    def _write_unmarked(self) -> None:
        path = self._constitution()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Hand-written\n\n## ARCH-1\nrule\n", encoding="utf-8")

    # 13. CLI accepts explicit --dry-run as a no-op alias.
    def test_cli_dry_run_is_noop(self) -> None:
        self._write_unmarked()
        rc = self.cli.main(["--target", str(self.target), "--dry-run"])
        self.assertEqual(rc, 1)  # review-required constitution -> conflict exit
        self.assertNotIn(rt.MANAGED_BEGIN, self._constitution().read_text(encoding="utf-8"))

    # --apply alone must not adopt an unmarked constitution.
    def test_cli_apply_alone_does_not_adopt(self) -> None:
        self._write_unmarked()
        self.cli.main(["--target", str(self.target), "--apply"])
        self.assertNotIn(rt.MANAGED_BEGIN, self._constitution().read_text(encoding="utf-8"))

    # adoption flag performs adoption.
    def test_cli_adopt_flag_adopts(self) -> None:
        self._write_unmarked()
        rc = self.cli.main(["--target", str(self.target), "--adopt-constitution-managed-block"])
        self.assertEqual(rc, 0)
        text = self._constitution().read_text(encoding="utf-8")
        self.assertIn(rt.MANAGED_BEGIN, text)
        self.assertIn("## ARCH-1", text)

    # 14. JSON output includes adoption state/result.
    def test_cli_json_includes_adoption(self) -> None:
        self._write_unmarked()
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.cli.main(["--target", str(self.target), "--adopt-constitution-managed-block", "--json"])
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["mode"], "ADOPTED")
        self.assertEqual(payload["adoption"]["state"], rt.ADOPTION_PERFORMED)

    # --adopt combined with --apply is rejected (adoption is standalone).
    def test_cli_adopt_with_apply_is_rejected(self) -> None:
        self._write_unmarked()
        with self.assertRaises(SystemExit):
            self.cli.main(["--target", str(self.target), "--apply", "--adopt-constitution-managed-block"])
        self.assertNotIn(rt.MANAGED_BEGIN, self._constitution().read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
