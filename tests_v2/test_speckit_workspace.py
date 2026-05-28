import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest import mock

from hldspec import speckit_workspace as sw

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hldspec_agent_session as facade  # noqa: E402


def _which_only(name: str):
    def inner(binary: str) -> Optional[str]:
        return f"/mock/{binary}" if binary == name else None

    return inner


class DetectInitCommandTests(unittest.TestCase):
    def test_detect_local_specify_command(self):
        commands = sw.detect_init_commands(which=_which_only("specify"))
        self.assertEqual(("specify", "init", "."), commands[0].argv)
        self.assertEqual("specify init .", commands[0].display)

    def test_detect_spec_kit_command(self):
        commands = sw.detect_init_commands(which=_which_only("spec-kit"))
        self.assertEqual(("spec-kit", "init", "."), commands[0].argv)

    def test_build_uvx_fallback_plan(self):
        commands = sw.detect_init_commands(which=_which_only("uvx"))
        self.assertEqual(
            (
                "uvx",
                "--from",
                sw.SPEC_KIT_UVX_SOURCE,
                "spec-kit",
                "init",
                ".",
            ),
            commands[0].argv,
        )

    def test_no_command_available_returns_blocker_when_not_initialized(self):
        result = sw.plan_or_init_workspace("/tmp/nowhere", which=lambda _: None)
        self.assertIn("No supported SpecKit init command is available", result.blocker or "")
        self.assertFalse(result.ok)


class WorkspaceStatusTests(unittest.TestCase):
    def test_inspect_reports_uninitialized_missing_specify(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = sw.inspect_workspace(Path(tmp))
        self.assertFalse(status.initialized)
        self.assertFalse(status.specify_dir_exists)
        self.assertIn("SpecKit init did not create", status.validation_error or "")

    def test_inspect_reports_source_mirror_without_memory_as_not_initialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".specify" / "source").mkdir(parents=True)
            status = sw.inspect_workspace(target)
        self.assertFalse(status.initialized)
        self.assertTrue(status.source_mirror_exists)
        self.assertIn("only the generated .specify/source/ mirror is present", status.validation_error or "")

    def test_inspect_accepts_real_speckit_memory_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".specify" / "memory").mkdir(parents=True)
            status = sw.inspect_workspace(target)
        self.assertTrue(status.initialized)
        self.assertIsNone(status.validation_error)
        self.assertTrue(status.metadata()["initialized"])


class InitPlanningTests(unittest.TestCase):
    def test_dry_run_does_not_execute(self):
        called = False

        def fake_run(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("run should not be called in dry-run mode")

        with tempfile.TemporaryDirectory() as tmp:
            result = sw.plan_or_init_workspace(
                tmp,
                execute=False,
                which=_which_only("specify"),
                run=fake_run,
            )
        self.assertFalse(called)
        self.assertFalse(result.executed)
        self.assertTrue(result.ok)
        self.assertFalse(result.initialized)

    def test_execute_requires_explicit_flag(self):
        called = False

        def fake_run(*args, **kwargs):
            nonlocal called
            called = True
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as tmp:
            sw.plan_or_init_workspace(tmp, which=_which_only("specify"), run=fake_run)
        self.assertFalse(called)

    def test_execute_does_not_rerun_init_when_workspace_already_initialized(self):
        called = False

        def fake_run(*args, **kwargs):
            nonlocal called
            called = True
            raise AssertionError("already initialized workspace must not rerun init")

        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".specify" / "memory").mkdir(parents=True)
            result = sw.plan_or_init_workspace(
                target,
                execute=True,
                which=lambda _: None,
                run=fake_run,
            )
        self.assertFalse(called)
        self.assertTrue(result.ok)
        self.assertTrue(result.initialized)
        self.assertEqual("already_initialized", result.skipped_reason)

    def test_existing_initialized_workspace_does_not_require_command_on_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".specify" / "memory").mkdir(parents=True)
            result = sw.plan_or_init_workspace(target, execute=False, which=lambda _: None)
        self.assertTrue(result.ok)
        self.assertTrue(result.initialized)
        self.assertIsNone(result.blocker)
        self.assertIsNone(result.selected)

    def test_validate_specify_exists_after_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)

            def fake_run(argv, cwd, text, capture_output, check):
                (Path(cwd) / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
                return SimpleNamespace(returncode=0, stdout="ok", stderr="")

            result = sw.plan_or_init_workspace(
                target,
                execute=True,
                which=_which_only("specify"),
                run=fake_run,
            )
        self.assertTrue(result.executed)
        self.assertTrue(result.initialized)
        self.assertIsNone(result.validation_error)
        self.assertEqual(0, result.returncode)
        self.assertEqual("ok", result.stdout)

    def test_execute_reports_missing_specify_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = sw.plan_or_init_workspace(
                tmp,
                execute=True,
                which=_which_only("specify"),
                run=lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="", stderr=""),
            )
        self.assertFalse(result.ok)
        self.assertIn(".specify", result.validation_error or "")

    def test_execute_reports_command_start_failure_without_faking_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = sw.plan_or_init_workspace(
                tmp,
                execute=True,
                which=_which_only("specify"),
                run=lambda *args, **kwargs: (_ for _ in ()).throw(OSError("boom")),
            )
        self.assertFalse(result.ok)
        self.assertIn("failed to start", result.blocker or "")
        self.assertEqual(127, result.returncode)
        self.assertFalse((Path(tmp) / ".specify").exists())

    def test_metadata_includes_workspace_status_and_command_display(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = sw.plan_or_init_workspace(tmp, execute=False, which=_which_only("uvx"))
            meta = result.metadata()
        self.assertIn("uvx --from", meta["selected_command_display"])
        self.assertIsInstance(meta["workspace_status"], dict)
        self.assertFalse(meta["workspace_status"]["initialized"])


class SpecifyLayoutValidationTests(unittest.TestCase):
    def test_validate_accepts_real_speckit_memory_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            (target / ".specify" / "memory").mkdir(parents=True)
            self.assertIsNone(sw.validate_initialized_workspace(target))

    def test_generated_mirror_alone_is_not_an_initialized_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            mirror = target / ".specify" / "source"
            mirror.mkdir(parents=True)
            (mirror / "HLD.md").write_text(
                "<!-- GENERATED by HLDspec -->\n# HLD\n", encoding="utf-8"
            )
            self.assertIsNotNone(sw.validate_initialized_workspace(target))
            result = sw.plan_or_init_workspace(target, which=_which_only("specify"))
            self.assertFalse(result.initialized)

    def test_init_preserves_hldspec_source_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)
            sp = target / ".hldspec" / "source_package"
            sp.mkdir(parents=True)
            sentinel = sp / "source_package.json"
            sentinel.write_text('{"owner":"hldspec"}', encoding="utf-8")

            def fake_run(argv, cwd, text, capture_output, check):
                (Path(cwd) / ".specify" / "memory").mkdir(parents=True, exist_ok=True)
                return SimpleNamespace(returncode=0, stdout="", stderr="")

            sw.plan_or_init_workspace(
                target, execute=True, which=_which_only("specify"), run=fake_run
            )
            self.assertTrue(sentinel.is_file())
            self.assertEqual('{"owner":"hldspec"}', sentinel.read_text(encoding="utf-8"))


class StartIntegrationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.source = self.root / "SourceHLD.md"
        self.source.write_text("# HLD\n\n## Intro\n\nText.\n", encoding="utf-8")
        self.target = self.root / "target"

    def tearDown(self):
        self._tmp.cleanup()

    def _run_start(self):
        fake_command = sw.InitCommand(
            label="specify",
            argv=("specify", "init", "."),
            source="local-binary",
        )
        with mock.patch.object(facade.sw, "detect_init_commands", return_value=(fake_command,)):
            rc = facade.main(
                [
                    "start",
                    "--source",
                    str(self.source),
                    "--target",
                    str(self.target),
                ]
            )
        self.assertEqual(0, rc)

    def test_selected_command_recorded_in_metadata_and_session_plan(self):
        self._run_start()
        agent_session = json.loads(
            (self.target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8")
        )
        session_plan = json.loads(
            (
                self.target
                / ".hldspec"
                / "source_package"
                / "session_plan.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            ["specify", "init", "."],
            agent_session["speckit_workspace_init"]["selected_command"],
        )
        self.assertEqual(
            ["specify", "init", "."],
            session_plan["speckit_workspace_init"]["selected_command"],
        )
        self.assertIn("workspace_status", agent_session["speckit_workspace_init"])

    def test_start_prompt_no_longer_defaults_legacy_bundle_outputs(self):
        self._run_start()
        prompt = (
            self.target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
        ).read_text(encoding="utf-8")
        self.assertNotIn("spec_packages", prompt)
        self.assertNotIn("feature_dependency_graph", prompt)
        self.assertNotIn("speckit_invocation_queue", prompt)
        self.assertIn("target/.specify/", prompt)
        self.assertIn("real SpecKit init only", prompt)

    def test_old_many_spec_flow_is_not_default(self):
        self._run_start()
        prompt = (
            self.target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
        ).read_text(encoding="utf-8")
        self.assertIn(".hldspec/source_package/source_package.json", prompt)
        self.assertIn(".hldspec/source_package/session_plan.json", prompt)
        self.assertIn("Default mode is dry-run planning only.", prompt)
        self.assertFalse((self.target / ".specify").exists())

    def test_start_on_existing_initialized_workspace_records_initialized_true(self):
        (self.target / ".specify" / "memory").mkdir(parents=True)
        with mock.patch.object(facade.sw, "detect_init_commands", return_value=()):
            rc = facade.main(
                [
                    "start",
                    "--source",
                    str(self.source),
                    "--target",
                    str(self.target),
                ]
            )
        self.assertEqual(0, rc)
        agent_session = json.loads(
            (self.target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8")
        )
        init = agent_session["speckit_workspace_init"]
        self.assertTrue(init["initialized"])
        self.assertEqual("already_initialized", init["skipped_reason"])
        self.assertIsNone(init["blocker"])


if __name__ == "__main__":
    unittest.main()
