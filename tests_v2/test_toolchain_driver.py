from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from hldspec import helper_selection as hsel
from hldspec import refresh_target as rt
from hldspec import run_state
from hldspec import runtime_vendor
from hldspec import toolchain_driver as tcd


def _git(target: Path, *argv: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(target), *argv], text=True, capture_output=True, check=True)


class ToolchainDriverReportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-toolchain-driver-")
        self.target = Path(self._tmp.name)
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _manifest_path(self) -> Path:
        return self.target / ".hldspec" / "runtime" / "MANIFEST.json"

    # 1. Normal target: selected helper + matching installed runtime -> PASS.
    def test_normal_target_is_pass_with_identity_match(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")

        report = tcd.build_driver_report(self.target)
        self.assertEqual(report["driver_status"], "PASS")
        self.assertEqual(report["effective_helper_id"], "speckit")
        self.assertEqual(report["installed_runtime_helper_id"], "speckit")
        self.assertEqual(report["installed_runtime_toolchain"], "SpecKit")
        self.assertTrue(report["identity_match"])
        self.assertEqual(report["driver_actor"], "human")
        self.assertEqual(report["driver_authority"], "GUIDE_ONLY")
        self.assertTrue(report["authority_allowed"])

    # 2. Missing runtime manifest -> ACTION, points at refresh-target, no crash.
    def test_missing_runtime_manifest_is_action(self) -> None:
        report = tcd.build_driver_report(self.target)
        self.assertEqual(report["driver_status"], "ACTION")
        self.assertIsNone(report["installed_runtime_helper_id"])
        self.assertFalse(report["identity_match"])
        self.assertIn("refresh-target --apply", report["next_safe_action"])

    # 3. Mismatched installed runtime helper identity -> ACTION, note mentions mismatch.
    def test_mismatched_runtime_helper_identity_is_action(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        manifest_path = self._manifest_path()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["helper_id"] = "not-speckit"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = tcd.build_driver_report(self.target)
        self.assertEqual(report["driver_status"], "ACTION")
        self.assertFalse(report["identity_match"])
        self.assertTrue(any("mismatch" in note.lower() for note in report["reality_check_notes"]))

    # 4. Legacy manifest lacking helper identity -> ACTION, not a crash.
    def test_legacy_manifest_without_helper_identity_is_action(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        manifest_path = self._manifest_path()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest.pop("helper_id", None)
        manifest.pop("toolchain", None)
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        report = tcd.build_driver_report(self.target)
        self.assertEqual(report["driver_status"], "ACTION")
        self.assertIsNone(report["installed_runtime_helper_id"])
        self.assertFalse(report["identity_match"])

    # Autonomous authority is future-only: not allowed, never silently PASS.
    def test_autonomous_authority_is_blocked(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")

        report = tcd.build_driver_report(self.target, authority="AUTONOMOUS_WITH_GUARDS")
        self.assertEqual(report["driver_status"], "BLOCKED")
        self.assertFalse(report["authority_allowed"])

    # EXECUTE_WITH_APPROVAL is declarable but this v0 driver never executes.
    def test_execute_with_approval_is_declared_but_inert(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        before = sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*"))

        report = tcd.build_driver_report(self.target, authority="EXECUTE_WITH_APPROVAL")
        self.assertTrue(report["authority_allowed"])
        self.assertEqual(report["driver_status"], "PASS")
        # No SpecKit invocation or file mutation occurred as a side effect of
        # building the report -- declaring EXECUTE_WITH_APPROVAL does not execute.
        after = sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*"))
        self.assertEqual(before, after)

    def test_unknown_actor_is_rejected(self) -> None:
        with self.assertRaises(tcd.InvalidDriverInputError):
            tcd.build_driver_report(self.target, actor="robot")

    def test_unknown_authority_is_rejected(self) -> None:
        with self.assertRaises(tcd.InvalidDriverInputError):
            tcd.build_driver_report(self.target, authority="bogus")

    # Forbidden actions always include the v0 read-only boundary.
    def test_forbidden_actions_present(self) -> None:
        report = tcd.build_driver_report(self.target)
        joined = " ".join(report["forbidden_actions"]).lower()
        self.assertIn("commit", joined)
        self.assertIn("silently", joined)
        self.assertIn("product", joined)

    # System + EXECUTE_WITH_APPROVAL: operator-replacing, approval-gated, but the
    # v0 report still executes/mutates nothing while being built.
    def test_system_execute_with_approval_report_is_gated_and_inert(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        before = sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*"))

        report = tcd.build_driver_report(
            self.target, actor="system", authority="EXECUTE_WITH_APPROVAL"
        )
        self.assertTrue(report["operator_replacement_allowed"])
        self.assertFalse(report["approver_replacement_allowed"])
        self.assertEqual(report["execution_posture"], "approval_gated")
        self.assertEqual(report["mutation_posture"], "approval_gated")
        self.assertFalse(report["execution_allowed"])
        self.assertFalse(report["mutation_allowed"])

        after = sorted(str(p.relative_to(self.target)) for p in self.target.rglob("*"))
        self.assertEqual(before, after)

    # Autonomous mode stays BLOCKED yet still reports owner protections intact.
    def test_autonomous_report_keeps_owner_protections(self) -> None:
        rt.refresh_target(self.target, apply=True)
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")

        report = tcd.build_driver_report(
            self.target, actor="system", authority="AUTONOMOUS_WITH_GUARDS"
        )
        self.assertEqual(report["driver_status"], "BLOCKED")
        self.assertFalse(report["approver_replacement_allowed"])
        self.assertEqual(report["mutation_posture"], "not_allowed")
        self.assertFalse(report["execution_allowed"])
        self.assertTrue(report["protected_approval_boundaries"])

    # The full report carries the authority-contract fields.
    def test_report_includes_authority_contract_fields(self) -> None:
        report = tcd.build_driver_report(self.target)
        for field in (
            "operator_replacement_allowed",
            "approver_replacement_allowed",
            "observation_allowed",
            "mutation_allowed",
            "execution_allowed",
            "execution_posture",
            "mutation_posture",
            "protected_approval_boundaries",
            "allowed_observations",
            "forbidden_without_approval",
        ):
            self.assertIn(field, report)


class DriverAuthorityProfileTests(unittest.TestCase):
    """Pure authority-contract view -- no filesystem. Encodes the product rule:
    a system driver may replace the human operator; no v0 mode may replace the
    human approver/owner."""

    # 1. Default human + GUIDE_ONLY: observe only, owner protections intact.
    def test_default_human_guide_only(self) -> None:
        p = tcd.build_authority_profile("human", "GUIDE_ONLY")
        self.assertTrue(p["observation_allowed"])
        self.assertFalse(p["approver_replacement_allowed"])
        self.assertFalse(p["operator_replacement_allowed"])
        self.assertFalse(p["mutation_allowed"])
        self.assertFalse(p["execution_allowed"])
        self.assertEqual(p["execution_posture"], "not_allowed")
        self.assertEqual(p["mutation_posture"], "not_allowed")
        self.assertTrue(p["protected_approval_boundaries"])

    # 2. System + PROPOSE_COMMAND: may replace operator; proposes, never executes.
    def test_system_propose_command(self) -> None:
        p = tcd.build_authority_profile("system", "PROPOSE_COMMAND")
        self.assertTrue(p["operator_replacement_allowed"])
        self.assertFalse(p["approver_replacement_allowed"])
        self.assertFalse(p["execution_allowed"])
        self.assertEqual(p["execution_posture"], "not_allowed")
        self.assertEqual(p["mutation_posture"], "not_allowed")
        self.assertTrue(p["protected_approval_boundaries"])

    # 3. System + EXECUTE_WITH_APPROVAL: operator-replacing, execution approval-gated.
    def test_system_execute_with_approval(self) -> None:
        p = tcd.build_authority_profile("system", "EXECUTE_WITH_APPROVAL")
        self.assertTrue(p["operator_replacement_allowed"])
        self.assertFalse(p["approver_replacement_allowed"])
        self.assertEqual(p["execution_posture"], "approval_gated")
        self.assertEqual(p["mutation_posture"], "approval_gated")
        # The gate is contracted/declared, not v0 capability -- nothing executes.
        self.assertFalse(p["execution_allowed"])
        self.assertFalse(p["mutation_allowed"])

    # 4. AUTONOMOUS_WITH_GUARDS never grants owner authority or v0 execution.
    def test_autonomous_with_guards(self) -> None:
        p = tcd.build_authority_profile("system", "AUTONOMOUS_WITH_GUARDS")
        self.assertFalse(p["approver_replacement_allowed"])
        self.assertEqual(p["execution_posture"], "not_allowed")
        self.assertEqual(p["mutation_posture"], "not_allowed")
        self.assertFalse(p["execution_allowed"])
        self.assertFalse(p["mutation_allowed"])
        self.assertTrue(p["protected_approval_boundaries"])

    # 5. Invalid actor/authority raises -- no silent unsafe fall-back.
    def test_unknown_actor_rejected(self) -> None:
        with self.assertRaises(tcd.InvalidDriverInputError):
            tcd.build_authority_profile("robot", "GUIDE_ONLY")

    def test_unknown_authority_rejected(self) -> None:
        with self.assertRaises(tcd.InvalidDriverInputError):
            tcd.build_authority_profile("human", "bogus")

    # 6. Reality-check: broad observation allowed; observation implies no mutation.
    def test_allowed_observations_cover_reality_check_categories(self) -> None:
        p = tcd.build_authority_profile("system", "GUIDE_ONLY")
        joined = " ".join(p["allowed_observations"]).lower()
        for needle in (
            "git",
            "worktree",
            "branch",
            "test",
            "helper recommendation",
            "helper selection",
            "runtime",
            "artifact",
            "journey phase",
        ):
            self.assertIn(needle, joined)
        self.assertTrue(p["observation_allowed"])
        self.assertFalse(p["mutation_allowed"])

    # The v0 invariants, asserted across every (actor, authority) combination.
    def test_invariants_hold_across_all_modes(self) -> None:
        actors = ("human", "system")
        authorities = (
            "GUIDE_ONLY",
            "PROPOSE_COMMAND",
            "EXECUTE_WITH_APPROVAL",
            "AUTONOMOUS_WITH_GUARDS",
        )
        for actor in actors:
            for authority in authorities:
                with self.subTest(actor=actor, authority=authority):
                    p = tcd.build_authority_profile(actor, authority)
                    # The driver never replaces the approver/owner, in any mode.
                    self.assertFalse(p["approver_replacement_allowed"])
                    # Operator replacement is allowed only for a system driver.
                    self.assertEqual(p["operator_replacement_allowed"], actor == "system")
                    # v0 never executes or mutates, regardless of authority.
                    self.assertFalse(p["execution_allowed"])
                    self.assertFalse(p["mutation_allowed"])
                    # Owner-only boundaries are always present (never unlocked).
                    self.assertTrue(p["protected_approval_boundaries"])
                    # Execution and mutation postures move together.
                    self.assertEqual(p["execution_posture"], p["mutation_posture"])

    # Protected boundaries cover the owner-only transitions the rule names.
    def test_protected_boundaries_cover_owner_only_transitions(self) -> None:
        joined = " ".join(tcd.PROTECTED_APPROVAL_BOUNDARIES).lower()
        for needle in (
            "commit",
            "push",
            "merge",
            "delete a branch",
            "approve a new helper",
            "operational",
            "accept unresolved risk",
            "override a blocked",
        ):
            self.assertIn(needle, joined)


class ToolchainDriverExternalStateTests(unittest.TestCase):
    """External-state mode: target carries only the `.hldspec-run.json`
    pointer; real control state (selection + runtime manifest) lives under
    the controller root. The driver report must read controller state and
    never leak/duplicate it into the target."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-toolchain-driver-external-")
        root = Path(self._tmp.name)
        self.target = root / "target"
        self.controller = root / "controller"
        self.target.mkdir()
        self.controller.mkdir()
        _git(self.target, "init", "-q")
        _git(self.target, "config", "user.email", "test@example.com")
        _git(self.target, "config", "user.name", "Test")
        source = self.target / "HLD.md"
        source.write_text("# HLD\n", encoding="utf-8")
        run_state.write_pointer(
            self.target,
            controller_root=self.controller,
            source=source,
            source_hash="deadbeef",
            mode="update",
            agent="test",
            workflow_trigger="build_loop_ready",
            created_or_updated_at="2026-06-07T00:00:00+00:00",
        )

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_driver_reads_controller_runtime_and_selection(self) -> None:
        # Representative tool-owned content the driver must never touch.
        specify_memory = self.target / ".specify" / "memory" / "constitution.md"
        specify_memory.parent.mkdir(parents=True)
        specify_memory.write_text("# Constitution\noriginal\n", encoding="utf-8")
        spec_file = self.target / "specs" / "001-foo" / "spec.md"
        spec_file.parent.mkdir(parents=True)
        spec_file.write_text("# Spec\noriginal\n", encoding="utf-8")

        # Seed the controller's runtime manifest directly (real installed-runtime
        # identity evidence), since the controller already has real `.hldspec`.
        manifest_path = self.controller / ".hldspec" / "runtime" / "MANIFEST.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(runtime_vendor.build_manifest({})), encoding="utf-8")
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")

        git_status_before = _git(self.target, "status", "--porcelain").stdout

        report = tcd.build_driver_report(self.target)

        self.assertEqual(report["driver_status"], "PASS")
        self.assertTrue(report["identity_match"])
        self.assertEqual(report["installed_runtime_helper_id"], "speckit")

        # Control state lands only under the controller root, never the target.
        self.assertTrue((self.controller / ".hldspec" / "runtime" / "MANIFEST.json").is_file())
        self.assertTrue((self.controller / ".hldspec" / "helper_selection.json").is_file())
        self.assertFalse((self.target / ".hldspec" / "runtime" / "MANIFEST.json").exists())
        self.assertFalse((self.target / ".hldspec" / "helper_selection.json").exists())

        # Seeded tool-owned bytes are untouched.
        self.assertEqual(specify_memory.read_text(encoding="utf-8"), "# Constitution\noriginal\n")
        self.assertEqual(spec_file.read_text(encoding="utf-8"), "# Spec\noriginal\n")

        # No git mutation in the product target repo from building the report.
        git_status_after = _git(self.target, "status", "--porcelain").stdout
        self.assertEqual(git_status_before, git_status_after)


if __name__ == "__main__":
    unittest.main()
