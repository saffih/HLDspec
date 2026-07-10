from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from hldspec import next_feature_readiness as nfr
from hldspec.machines.hld_readiness import HldReadinessMachine
from hldspec.state_machine import MachineContext, MachineStatus

_HLD_BODY = "# Demo HLD\n\n## Section 1\n\nBody text.\n"


class HldReadinessControlSyncPathResolutionTests(unittest.TestCase):
    """A3.2c-family: HldReadinessMachine must resolve its sync dir the same
    pointer-aware way SpecKitExecutionMachine does (PR #147) so external-
    controller mode can't split writer/reader state.
    """

    def test_external_controller_mode_writes_controller_sync(self) -> None:
        work = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (work / "targetHLD").mkdir(parents=True)
        (work / "targetHLD" / "HLD.md").write_text(_HLD_BODY, encoding="utf-8")

        result = HldReadinessMachine().run(
            MachineContext(
                repo_root=".", source_hld="source.md", workspace=str(work), metadata={"workspace_layout": "new"}
            )
        )

        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("HLD_READY", result.state)
        controller_sync = controller / ".hldspec" / "sync"
        self.assertTrue((controller_sync / "hld_readiness_check.json").exists())
        self.assertFalse((work / ".hldspec").exists())

    def test_legacy_layout_default_unaffected_by_controller_pointer(self) -> None:
        work = Path(tempfile.mkdtemp())
        controller = Path(tempfile.mkdtemp())
        (work / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        (work / "HLD.md").write_text(_HLD_BODY, encoding="utf-8")

        result = HldReadinessMachine().run(
            MachineContext(repo_root=".", source_hld="source.md", workspace=str(work))
        )

        self.assertEqual(MachineStatus.DONE, result.status)
        self.assertEqual("HLD_READY", result.state)
        legacy_sync = work / "firstrun" / ".specify" / "sync"
        self.assertTrue((legacy_sync / "hld_readiness_check.json").exists())


class _GitStub:
    def __init__(self, *, root: Path, branch: str) -> None:
        self.root = root
        self.branch = branch

    def __call__(self, argv, cwd, text, capture_output, check):
        argv = list(argv)
        if not argv or argv[0] != "git":
            return SimpleNamespace(returncode=1, stdout="", stderr="")
        if "rev-parse" in argv and "--show-toplevel" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.root}\n", stderr="")
        if "branch" in argv and "--show-current" in argv:
            return SimpleNamespace(returncode=0, stdout=f"{self.branch}\n", stderr="")
        if "rev-parse" in argv and "HEAD" in argv:
            return SimpleNamespace(returncode=0, stdout="abc123\n", stderr="")
        if "symbolic-ref" in argv:
            return SimpleNamespace(returncode=0, stdout="origin/main\n", stderr="")
        if "status" in argv:
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return SimpleNamespace(returncode=1, stdout="", stderr="")


class ExecutionEvidenceControlSyncResolutionTests(unittest.TestCase):
    """Recorded analyze-completion execution evidence must resolve through the
    same pointer-aware control-sync dir as every other reader (PR #147
    family): controller-root evidence is recognized in external-controller
    mode, stale target-local files cannot override it, and the no-pointer
    default stays target-local.
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-evidence-sync-")
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _speckit_target(self) -> Path:
        target = self.root / "target"
        (target / ".specify" / "memory").mkdir(parents=True)
        (target / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
        (target / ".specify" / "extensions.yml").write_text("before_specify: true\n", encoding="utf-8")
        spec_dir = target / "specs" / "001-feature"
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
        (spec_dir / "plan.md").write_text("plan body", encoding="utf-8")
        (spec_dir / "tasks.md").write_text("tasks body", encoding="utf-8")
        return target

    def _point_at_controller(self, target: Path) -> Path:
        controller = self.root / "controller"
        controller.mkdir(parents=True)
        (target / ".hldspec-run.json").write_text(
            json.dumps({"schema_version": 1, "controller_root": str(controller)}), encoding="utf-8"
        )
        return controller

    def _write_evidence(self, root: Path) -> None:
        sync = root / ".hldspec" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / nfr.EXECUTION_EVIDENCE_FILE).write_text(
            json.dumps({
                "status": nfr.EVIDENCE_ANALYZE_COMPLETED,
                "branch": "001-feature",
                "spec_dir": "specs/001-feature",
                "commit_sha": "abc123",
            }), encoding="utf-8"
        )

    @patch("hldspec.next_feature_readiness._is_commit_reachable", return_value=True)
    def test_external_controller_evidence_is_recognized(self, _mock_reachable) -> None:
        target = self._speckit_target()
        controller = self._point_at_controller(target)
        self._write_evidence(controller)

        report = nfr.write_next_feature_readiness_report(target, run=_GitStub(root=target, branch="001-feature"))

        self.assertEqual(nfr.PHASE_READY_FOR_IMPLEMENT, report["phase"])

    @patch("hldspec.next_feature_readiness._is_commit_reachable", return_value=True)
    def test_stale_target_local_evidence_cannot_override_controller_state(self, _mock_reachable) -> None:
        target = self._speckit_target()
        self._point_at_controller(target)
        self._write_evidence(target)

        report = nfr.write_next_feature_readiness_report(target, run=_GitStub(root=target, branch="001-feature"))

        self.assertEqual(nfr.PHASE_READY_FOR_ANALYZE, report["phase"])

    @patch("hldspec.next_feature_readiness._is_commit_reachable", return_value=True)
    def test_no_pointer_target_local_evidence_is_recognized(self, _mock_reachable) -> None:
        target = self._speckit_target()
        self._write_evidence(target)

        report = nfr.write_next_feature_readiness_report(target, run=_GitStub(root=target, branch="001-feature"))

        self.assertEqual(nfr.PHASE_READY_FOR_IMPLEMENT, report["phase"])


if __name__ == "__main__":
    unittest.main()
