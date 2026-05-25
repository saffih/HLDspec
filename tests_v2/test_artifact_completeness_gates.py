from __future__ import annotations

import unittest

from hldspec.prework_contracts import (
    REQUIRED_ARCHITECT_PACK_KEYS,
    REQUIRED_DOSSIER_FIELDS,
    REQUIRED_PM_PACK_KEYS,
    missing_architect_pack_keys,
    missing_pm_pack_keys,
    shallow_dossier_fields,
)


def _full_pm_pack() -> dict:
    return {
        "users": ["user_a"],
        "jobs_to_be_done": ["job_1"],
        "user_journeys": ["journey_1"],
        "use_cases": ["use_case_1"],
        "user_stories": ["story_1"],
        "acceptance_criteria": ["criterion_1"],
    }


def _full_architect_pack() -> dict:
    return {
        "constitution_rules": ["rule_1"],
        "component_boundaries": ["boundary_1"],
        "interface_contracts": ["contract_1"],
        "dependency_order": ["dep_1"],
        "technical_risks": ["risk_1"],
    }


def _full_dossier() -> dict:
    return {
        "named_capabilities": ["cap_1"],
        "interface_contracts": ["contract_1"],
        "data_ownership": ["owner_1"],
        "integration_paths": ["path_1"],
        "dependency_reasons": ["reason_1"],
        "acceptance_criteria": ["criterion_1"],
    }


class TestMissingPmPackKeys(unittest.TestCase):
    def test_all_present_returns_empty(self) -> None:
        self.assertEqual([], missing_pm_pack_keys(_full_pm_pack()))

    def test_one_key_missing(self) -> None:
        pack = _full_pm_pack()
        del pack["users"]
        self.assertEqual(["users"], missing_pm_pack_keys(pack))

    def test_one_key_empty_list(self) -> None:
        pack = _full_pm_pack()
        pack["jobs_to_be_done"] = []
        self.assertEqual(["jobs_to_be_done"], missing_pm_pack_keys(pack))

    def test_one_key_empty_string(self) -> None:
        pack = _full_pm_pack()
        pack["user_journeys"] = ""
        self.assertEqual(["user_journeys"], missing_pm_pack_keys(pack))

    def test_empty_dict_returns_all_required_keys(self) -> None:
        self.assertEqual(REQUIRED_PM_PACK_KEYS, missing_pm_pack_keys({}))


class TestMissingArchitectPackKeys(unittest.TestCase):
    def test_all_present_returns_empty(self) -> None:
        self.assertEqual([], missing_architect_pack_keys(_full_architect_pack()))

    def test_one_key_missing(self) -> None:
        pack = _full_architect_pack()
        del pack["constitution_rules"]
        self.assertEqual(["constitution_rules"], missing_architect_pack_keys(pack))

    def test_one_key_empty_list(self) -> None:
        pack = _full_architect_pack()
        pack["component_boundaries"] = []
        self.assertEqual(["component_boundaries"], missing_architect_pack_keys(pack))

    def test_one_key_empty_string(self) -> None:
        pack = _full_architect_pack()
        pack["interface_contracts"] = ""
        self.assertEqual(["interface_contracts"], missing_architect_pack_keys(pack))

    def test_empty_dict_returns_all_required_keys(self) -> None:
        self.assertEqual(REQUIRED_ARCHITECT_PACK_KEYS, missing_architect_pack_keys({}))


class TestShallowDossierFields(unittest.TestCase):
    def test_all_present_returns_empty(self) -> None:
        self.assertEqual([], shallow_dossier_fields(_full_dossier()))

    def test_one_key_missing(self) -> None:
        dossier = _full_dossier()
        del dossier["named_capabilities"]
        self.assertEqual(["named_capabilities"], shallow_dossier_fields(dossier))

    def test_one_key_empty_list(self) -> None:
        dossier = _full_dossier()
        dossier["data_ownership"] = []
        self.assertEqual(["data_ownership"], shallow_dossier_fields(dossier))

    def test_one_key_empty_string(self) -> None:
        dossier = _full_dossier()
        dossier["integration_paths"] = ""
        self.assertEqual(["integration_paths"], shallow_dossier_fields(dossier))

    def test_empty_dict_returns_all_required_keys(self) -> None:
        self.assertEqual(REQUIRED_DOSSIER_FIELDS, shallow_dossier_fields({}))


if __name__ == "__main__":
    unittest.main()
