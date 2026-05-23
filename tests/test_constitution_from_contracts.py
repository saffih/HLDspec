"""Tests for build_speckit_constitution_from_contracts.py"""
import importlib.util
import json
import sys
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


class TestConstitutionFromContracts(unittest.TestCase):
    def setUp(self):
        self.mod = load_module(
            "build_speckit_constitution_from_contracts",
            SCRIPTS / "build_speckit_constitution_from_contracts.py",
        )

    def _make_workspace(self, tmp: str) -> Path:
        ws = Path(tmp)
        sync = ws / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        return ws

    def test_adds_contract_rules_from_interface_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            sync = ws / ".specify" / "sync"

            write_json(sync / "constitution_update_plan.json", {
                "schema_version": 1,
                "required_rules": [
                    {"rule_id": "ARCH-001", "name": "HLD Source of Truth", "rule": "HLD is canonical.", "rationale": "governance"},
                    {"rule_id": "ARCH-002", "name": "API Separation", "rule": "Separate API from processing.", "rationale": "governance"},
                    {"rule_id": "ARCH-003", "name": "Foundation First", "rule": "Common before dependent.", "rationale": "governance"},
                    {"rule_id": "ARCH-004", "name": "SpecKit Boundary", "rule": "SpecKit owns spec/plan/tasks.", "rationale": "governance"},
                ],
                "human_checkpoint": {"human_decision": "TBD"},
            })

            write_json(sync / "interface_contract_map.json", {
                "schema_version": 1,
                "contracts": [
                    {
                        "contract_id": "DATABASE_API_CONTRACT",
                        "contract_name": "Database API Contract",
                        "provider": "Flow Core Database API",
                        "consumer": "All Components",
                        "source_hld_sections": ["HLD-010B"],
                        "evidence": ["All data access must go through the Database API layer."],
                    },
                    {
                        "contract_id": "WIP_SOURCE_OF_TRUTH_CONTRACT",
                        "contract_name": "WIP Source-of-Truth Contract",
                        "provider": "Database",
                        "consumer": "WIP readers",
                        "source_hld_sections": ["HLD-009H"],
                        "evidence": ["Database is authoritative; markdown is projection."],
                    },
                    {
                        "contract_id": "CLI_PROTOCOL_CONTRACT",
                        "contract_name": "CLI Protocol Contract",
                        "provider": "Flow CLI",
                        "consumer": "core.md / AI session",
                        "source_hld_sections": ["HLD-009D"],
                        "evidence": [],
                    },
                ],
            })

            write_json(sync / "data_ownership_map.json", {"schema_version": 1, "data_objects": []})

            result = self.mod.augment(ws)

            updated = json.loads((sync / "constitution_update_plan.json").read_text())
            rules = updated["required_rules"]

            # Should have 4 original + 3 new CONTRACT rules = 7
            self.assertGreaterEqual(len(rules), 7)

            # Verify CONTRACT rules exist
            contract_ids = [r["rule_id"] for r in rules if r["rule_id"].startswith("CONTRACT-")]
            self.assertEqual(len(contract_ids), 3)

            # Verify traceability in rationale
            rationales = [r.get("rationale", "") for r in rules]
            self.assertTrue(any("interface_contract_map.json:DATABASE_API_CONTRACT" in r for r in rationales))

            # Verify status
            self.assertEqual(result["contract_rules_added"], 3)

    def test_adds_data_rules_when_source_of_truth_known(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            sync = ws / ".specify" / "sync"

            write_json(sync / "constitution_update_plan.json", {
                "required_rules": [
                    {"rule_id": "ARCH-001", "name": "HLD", "rule": "r", "rationale": "g"},
                ],
            })
            write_json(sync / "interface_contract_map.json", {"contracts": []})
            write_json(sync / "data_ownership_map.json", {
                "data_objects": [
                    {
                        "data_object": "tasks",
                        "owner": "Flow Core Database API",
                        "source_of_truth": "SQLite via Database API",
                        "update_timing": "Event-driven after writes",
                        "source_hld_sections": ["HLD-010B"],
                    },
                    {
                        "data_object": "config",
                        "owner": "TBD",
                        "source_of_truth": "TBD",  # TBD — should NOT produce a rule
                        "update_timing": "TBD",
                        "source_hld_sections": [],
                    },
                ],
            })

            result = self.mod.augment(ws)
            updated = json.loads((sync / "constitution_update_plan.json").read_text())
            rules = updated["required_rules"]

            data_rules = [r for r in rules if r["rule_id"].startswith("DATA-")]
            self.assertEqual(len(data_rules), 1)
            self.assertIn("tasks", data_rules[0]["rule"])
            self.assertEqual(result["data_rules_added"], 1)

    def test_idempotent_no_duplicate_rules(self):
        """Running augment twice must not duplicate CONTRACT rules."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            sync = ws / ".specify" / "sync"

            base_constitution = {
                "required_rules": [
                    {"rule_id": "ARCH-001", "name": "HLD", "rule": "r", "rationale": "g"},
                ],
            }
            contracts = {
                "contracts": [
                    {
                        "contract_id": "DATABASE_API_CONTRACT",
                        "contract_name": "Database API Contract",
                        "provider": "Flow Core Database API",
                        "consumer": "All Components",
                        "source_hld_sections": [],
                        "evidence": [],
                    },
                ],
            }

            write_json(sync / "constitution_update_plan.json", base_constitution)
            write_json(sync / "interface_contract_map.json", contracts)
            write_json(sync / "data_ownership_map.json", {"data_objects": []})

            self.mod.augment(ws)  # first run
            self.mod.augment(ws)  # second run

            updated = json.loads((sync / "constitution_update_plan.json").read_text())
            contract_rules = [r for r in updated["required_rules"] if r["rule_id"].startswith("CONTRACT-")]
            self.assertEqual(len(contract_rules), 1, "Duplicate CONTRACT rules found after second run")


if __name__ == "__main__":
    unittest.main()
