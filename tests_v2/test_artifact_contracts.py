import tempfile
import time
import unittest
from pathlib import Path

from hldspec.artifact_contracts import (
    ARTIFACT_CONTRACTS,
    SYNC_LOCAL,
    WORKSPACE_ROOT,
    ArtifactInput,
    stale_registered_artifacts,
    validate_contract,
    registered_artifacts,
)


class TestValidateContract(unittest.TestCase):
    def test_valid_spec_build_plan_returns_no_violations(self):
        result = validate_contract("spec_build_plan.json", {"plan_quality": {}, "planned_specs": []})
        self.assertEqual(result, [])

    def test_empty_spec_build_plan_returns_two_violations(self):
        result = validate_contract("spec_build_plan.json", {})
        self.assertEqual(len(result), 2)

    def test_unknown_artifact_returns_no_violations(self):
        result = validate_contract("unknown_artifact.json", {})
        self.assertEqual(result, [])

    def test_violation_message_names_field(self):
        result = validate_contract("spec_build_plan.json", {"plan_quality": {}})
        self.assertEqual(len(result), 1)
        self.assertIn("planned_specs", result[0])

    def test_violation_message_names_artifact(self):
        result = validate_contract("spec_build_plan.json", {})
        for v in result:
            self.assertIn("spec_build_plan.json", v)


class TestRegisteredArtifacts(unittest.TestCase):
    def test_contains_spec_build_plan(self):
        self.assertIn("spec_build_plan.json", registered_artifacts())

    def test_separates_speckit_machine_state_from_progress_assessment(self):
        self.assertIn("speckit_execution_state.json", registered_artifacts())
        self.assertIn("speckit_execution_assessment.json", registered_artifacts())
        self.assertEqual(
            "SpecKitExecutionMachine",
            ARTIFACT_CONTRACTS["speckit_execution_state.json"].producer,
        )
        self.assertEqual(
            "speckit_execution_state.py",
            ARTIFACT_CONTRACTS["speckit_execution_assessment.json"].producer,
        )

    def test_registers_hld_readiness_cross_examination_artifacts(self):
        self.assertIn("hld_cross_examination.json", registered_artifacts())
        self.assertIn("hld_readiness_check.json", registered_artifacts())

        cross = ARTIFACT_CONTRACTS["hld_cross_examination.json"]
        self.assertIn("examined_items", cross.required_fields)
        self.assertIn("grouped_questions", cross.required_fields)
        self.assertIn("polite_clarification_prompt", cross.optional_fields)
        self.assertIn("hld_readiness_check.json", cross.output_artifacts)
        self.assertIn("Auxiliary reason trail", cross.notes)

        readiness = ARTIFACT_CONTRACTS["hld_readiness_check.json"]
        self.assertIn("verdict", readiness.required_fields)
        self.assertIn("next_safe_action", readiness.required_fields)
        self.assertIn("hld_cross_examination.json", readiness.input_artifacts)
        self.assertIn("stop before full SpecKit Preparation", readiness.notes)

    def test_returns_list(self):
        self.assertIsInstance(registered_artifacts(), list)


class TestContractIntegrity(unittest.TestCase):
    def test_all_contracts_have_non_empty_artifact_name(self):
        for name, contract in ARTIFACT_CONTRACTS.items():
            self.assertTrue(contract.artifact_name, f"{name} has empty artifact_name")

    def test_all_contracts_have_producer_set(self):
        for name, contract in ARTIFACT_CONTRACTS.items():
            self.assertTrue(contract.producer, f"{name} has empty producer")

    def test_no_duplicate_artifact_names_in_registry(self):
        names = list(ARTIFACT_CONTRACTS.keys())
        self.assertEqual(len(names), len(set(names)))

    def test_artifact_name_matches_registry_key(self):
        for key, contract in ARTIFACT_CONTRACTS.items():
            self.assertEqual(key, contract.artifact_name)


class TestArtifactInput(unittest.TestCase):
    def test_default_location_is_sync_local(self):
        ai = ArtifactInput(name="foo.json")
        self.assertEqual(SYNC_LOCAL, ai.location)

    def test_workspace_root_location(self):
        ai = ArtifactInput(name="HLD.raw.md", location=WORKSPACE_ROOT)
        self.assertEqual(WORKSPACE_ROOT, ai.location)

    def test_hld_conversion_queue_uses_workspace_root_for_hld_raw(self):
        contract = ARTIFACT_CONTRACTS["hld_conversion_decision_queue.json"]
        hld_raw_spec = next(
            (s for s in contract.input_specs if s.name == "HLD.raw.md"), None
        )
        self.assertIsNotNone(hld_raw_spec, "HLD.raw.md must be in input_specs")
        self.assertEqual(WORKSPACE_ROOT, hld_raw_spec.location)

    def test_hld_cross_examination_uses_workspace_hld_input(self):
        contract = ARTIFACT_CONTRACTS["hld_cross_examination.json"]
        hld_spec = next((s for s in contract.input_specs if s.name == "HLD.md"), None)
        self.assertIsNotNone(hld_spec, "HLD.md must be in input_specs")
        self.assertEqual(WORKSPACE_ROOT, hld_spec.location)


class TestStaleRegisteredArtifacts(unittest.TestCase):

    def _make_dirs(self, tmpdir: Path):
        sync = tmpdir / ".specify" / "sync"
        sync.mkdir(parents=True)
        workspace = tmpdir
        return sync, workspace

    def test_no_artifacts_no_staleness(self):
        with tempfile.TemporaryDirectory() as d:
            sync, workspace = self._make_dirs(Path(d))
            result = stale_registered_artifacts(sync, workspace=workspace)
            self.assertEqual([], result)

    def test_sync_local_input_newer_than_output_is_stale(self):
        with tempfile.TemporaryDirectory() as d:
            sync, workspace = self._make_dirs(Path(d))
            output = sync / "spec_build_plan.json"
            output.write_text("{}", encoding="utf-8")
            time.sleep(0.02)
            inp = sync / "hld_usecase_api_map.json"
            inp.write_text("{}", encoding="utf-8")
            result = stale_registered_artifacts(sync, workspace=workspace)
            self.assertTrue(any("spec_build_plan.json" in r for r in result))

    def test_workspace_root_input_newer_than_output_is_stale(self):
        """HLD.raw.md at workspace root should trigger staleness."""
        with tempfile.TemporaryDirectory() as d:
            sync, workspace = self._make_dirs(Path(d))
            output = sync / "hld_conversion_decision_queue.json"
            output.write_text("{}", encoding="utf-8")
            time.sleep(0.02)
            hld_raw = workspace / "HLD.raw.md"
            hld_raw.write_text("# raw hld", encoding="utf-8")
            result = stale_registered_artifacts(sync, workspace=workspace)
            self.assertTrue(
                any("hld_conversion_decision_queue.json" in r for r in result),
                f"Expected staleness for hld_conversion_decision_queue.json, got: {result}",
            )

    def test_workspace_root_staleness_not_detected_without_workspace_arg(self):
        """Without workspace arg, WORKSPACE_ROOT inputs are skipped (no false positives)."""
        with tempfile.TemporaryDirectory() as d:
            sync, workspace = self._make_dirs(Path(d))
            output = sync / "hld_conversion_decision_queue.json"
            output.write_text("{}", encoding="utf-8")
            time.sleep(0.02)
            (workspace / "HLD.raw.md").write_text("# raw", encoding="utf-8")
            result = stale_registered_artifacts(sync)  # no workspace arg
            self.assertFalse(
                any("hld_conversion_decision_queue.json" in r for r in result),
                "Should not flag workspace-root staleness without workspace arg",
            )

    def test_output_missing_is_not_stale(self):
        """An artifact that hasn't been generated yet is not 'stale'."""
        with tempfile.TemporaryDirectory() as d:
            sync, workspace = self._make_dirs(Path(d))
            (sync / "hld_usecase_api_map.json").write_text("{}", encoding="utf-8")
            result = stale_registered_artifacts(sync, workspace=workspace)
            self.assertFalse(
                any("spec_build_plan.json" in r for r in result),
                "Missing output should not be reported as stale",
            )


if __name__ == "__main__":
    unittest.main()
