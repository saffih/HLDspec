import unittest

from hldspec.artifact_contracts import ARTIFACT_CONTRACTS, validate_contract, registered_artifacts


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


if __name__ == "__main__":
    unittest.main()
