"""End-to-end smoke test: synthetic HLD → constitution → invoke prompt → clarify lookup.

Does NOT invoke real SpecKit. Validates every component up to the invocation boundary.
"""
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


SYNTHETIC_HLD = """## HLD-001 - Database API Interface

<!-- HLD-ID: HLD-001 -->
<!-- HLD-ROLE: spec_candidate -->
<!-- HLD-STATUS: active -->
<!-- HLD-RISK: high -->
<!-- HLD-SPECS: database-api -->
<!-- HLD-RESOURCES: none -->
<!-- HLD-VERIFY: tests -->

The Flow Core Database API is the only permitted path to the SQLite database.
All components MUST use this API. Direct SQLite access is FORBIDDEN.

The API provides methods for task CRUD, WIP lifecycle, session state, and configuration.
Source of truth: SQLite database. Markdown files are read-only projections.

TASK_OFFER, TASK_ACK, and TASK_NACK are delivered via Unix socket to the AI session.

## HLD-002 - CLI Protocol

<!-- HLD-ID: HLD-002 -->
<!-- HLD-ROLE: spec_candidate -->
<!-- HLD-STATUS: active -->
<!-- HLD-RISK: medium -->
<!-- HLD-SPECS: cli-protocol -->
<!-- HLD-RESOURCES: none -->
<!-- HLD-VERIFY: tests -->

The CLI provides the interface between the Brain (core.md) and the Flow system.
The Brain MUST communicate through the CLI only. Direct imports are forbidden.

CLI commands: flow start, flow stop, flow status, flow wip, flow notify.
"""

SYNTHETIC_SPEC_BUILD_PLAN = {
    "schema_version": 1,
    "planned_specs": [
        {
            "planned_spec_id": "001",
            "title": "Database API Interface",
            "source_hld_sections": ["HLD-001"],
            "depends_on_specs": [],
            "quality_flags": [],
        },
        {
            "planned_spec_id": "002",
            "title": "CLI Protocol",
            "source_hld_sections": ["HLD-002"],
            "depends_on_specs": ["001"],
            "quality_flags": [],
        },
    ],
    "plan_quality": {
        "decision": "PASS",
        "recommendation": "KEEP_PLAN",
        "conflicts": [],
        "findings": [],
    },
}


def _setup_workspace(tmp: str) -> Path:
    ws = Path(tmp)
    sync = ws / ".specify" / "sync"
    sync.mkdir(parents=True, exist_ok=True)

    (ws / "HLD.md").write_text(SYNTHETIC_HLD, encoding="utf-8")
    write_json(sync / "spec_build_plan.json", SYNTHETIC_SPEC_BUILD_PLAN)
    return ws


class TestE2EHldToSpecify(unittest.TestCase):

    def test_answer_dossier_extracts_contracts(self):
        """build_hld_answer_dossier.build() finds contracts from synthetic HLD."""
        mod = load_module("build_hld_answer_dossier", SCRIPTS / "build_hld_answer_dossier.py")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            result = mod.build(ws)
            contracts = result.get("contracts", 0)
            # Synthetic HLD mentions database, CLI, socket — expect at least 1 contract
            self.assertGreaterEqual(contracts, 1, f"Expected ≥1 contract, got {contracts}")

    def test_constitution_augmented_from_contracts(self):
        """After dossier + augment, constitution has ≥ 4 ARCH + ≥1 CONTRACT rule."""
        dossier_mod = load_module("build_hld_answer_dossier", SCRIPTS / "build_hld_answer_dossier.py")
        augment_mod = load_module(
            "build_speckit_constitution_from_contracts",
            SCRIPTS / "build_speckit_constitution_from_contracts.py",
        )
        prework_mod = load_module("build_speckit_prework_plan", SCRIPTS / "build_speckit_prework_plan.py")

        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            sync = ws / ".specify" / "sync"

            # Build constitution (ARCH rules only)
            plan = json.loads((sync / "spec_build_plan.json").read_text())
            artifacts = prework_mod.build_artifacts(plan, sync / "spec_build_plan.json")
            for name, data in artifacts.items():
                write_json(sync / f"{name}.json", data)

            # Build dossier (creates interface_contract_map.json)
            dossier_mod.build(ws)

            # Augment constitution
            result = augment_mod.augment(ws)
            updated = json.loads((sync / "constitution_update_plan.json").read_text())
            rules = updated["required_rules"]

            arch_rules = [r for r in rules if r["rule_id"].startswith("ARCH-")]
            contract_rules = [r for r in rules if r["rule_id"].startswith("CONTRACT-") or r["rule_id"].startswith("DATA-")]

            self.assertEqual(len(arch_rules), 4)
            self.assertGreaterEqual(len(contract_rules), 1,
                f"Expected ≥1 CONTRACT/DATA rule, got {len(contract_rules)}. Total rules: {len(rules)}")
            self.assertGreaterEqual(result["total_rules"], 5)

    def test_approve_blocked_by_blocker_finding(self):
        """approve_prework refuses when BLOCKER finding present."""
        approve_mod = load_module("approve_hldspec_prework", SCRIPTS / "approve_hldspec_prework.py")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            sync = ws / ".specify" / "sync"
            write_json(sync / "speckit_prework_package.json", {
                "human_checkpoint": {
                    "options": ["APPROVE_PLAN"],
                    "human_decision": "TBD",
                },
            })
            write_json(sync / "speckit_prework_quality_review.json", {
                "findings": [{"id": "QG-015", "severity": "BLOCKER", "finding": "no contracts"}],
            })
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            with self.assertRaises(ValueError):
                approve_mod.approve_prework(ws, "APPROVE_PLAN")

    def test_approve_succeeds_with_clean_reviews(self):
        """approve_prework writes approval when no BLOCKER findings."""
        approve_mod = load_module("approve_hldspec_prework", SCRIPTS / "approve_hldspec_prework.py")
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            sync = ws / ".specify" / "sync"
            write_json(sync / "speckit_prework_package.json", {
                "human_checkpoint": {
                    "options": ["APPROVE_PLAN"],
                    "human_decision": "TBD",
                },
            })
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            write_json(sync / "hld_answer_dossier_quality_review.json", {"findings": []})
            record = approve_mod.approve_prework(ws, "APPROVE_PLAN")
            self.assertEqual(record["status"], "APPROVED")

    def test_invoke_prompt_generated_with_required_fields(self):
        """hldspec_invoke_speckit_feature produces a prompt with constitution rules and specify input."""
        invoke_mod = load_module(
            "hldspec_invoke_speckit_feature",
            SCRIPTS / "hldspec_invoke_speckit_feature.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            sync = ws / ".specify" / "sync"

            write_json(sync / "speckit_prework_approval.json", {"status": "APPROVED"})
            write_json(sync / "speckit_prework_quality_review.json", {"findings": []})
            write_json(sync / "speckit_invocation_queue.json", {
                "items": [{
                    "order": 1,
                    "feature_id": "001",
                    "feature_name": "Database API Interface",
                    "short_name": "database-api",
                    "speckit_specify_input": "Build the Flow Core Database API.",
                    "depends_on_features": [],
                    "source_hld_sections": ["HLD-001"],
                    "status": "PENDING_HUMAN_PLAN_REVIEW",
                }],
            })
            write_json(sync / "speckit_answer_dossier.json", {
                "specs": [{
                    "planned_spec_id": "001",
                    "capability_name": "Database API Interface",
                    "provides": ["Database API Contract"],
                    "owns": ["tasks", "wip"],
                    "source_of_truth_or_TBD": "SQLite",
                    "pm_value": "Enables task tracking",
                    "failure_fallbacks": ["Retry on connection error"],
                    "interfaces": [],
                    "integration_paths": [],
                }],
            })
            write_json(sync / "constitution_update_plan.json", {
                "required_rules": [
                    {"rule_id": "ARCH-001", "name": "HLD Source", "rule": "HLD is canonical."},
                    {"rule_id": "CONTRACT-001", "name": "Database API Contract",
                     "rule": "All data access via Database API; direct SQLite forbidden."},
                ],
            })

            result = invoke_mod.build_prompt(ws)
            self.assertEqual(result["feature_id"], "001")
            prompt_path = Path(result["prompt_path"])
            self.assertTrue(prompt_path.exists())
            prompt_text = prompt_path.read_text(encoding="utf-8")
            self.assertIn("Build the Flow Core Database API.", prompt_text)
            self.assertIn("CONTRACT-001", prompt_text)
            self.assertIn("direct SQLite forbidden", prompt_text)
            self.assertIn("/speckit.specify", prompt_text)
            self.assertIn("ESCALATE_TO_HUMAN", prompt_text)

    def test_clarify_lookup_known_contract(self):
        """lookup returns ANSWER_FROM_EVIDENCE for a question matching a known contract."""
        lookup_mod = load_module(
            "lookup_speckit_clarify_answer",
            SCRIPTS / "lookup_speckit_clarify_answer.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            sync = ws / ".specify" / "sync"
            write_json(sync / "interface_contract_map.json", {
                "contracts": [{
                    "contract_id": "DATABASE_API_CONTRACT",
                    "contract_name": "Database API Contract",
                    "provider": "Flow Core Database API",
                    "consumer": "All Components",
                    "evidence": ["All data access must go through the Database API."],
                    "source_hld_sections": ["HLD-001"],
                }],
            })
            write_json(sync / "data_ownership_map.json", {"data_objects": []})
            write_json(sync / "open_questions_tbd_map.json", {"items": []})

            result = lookup_mod.lookup(ws, "How should a spec access the database?")
            self.assertEqual(result["classification"], "ANSWER_FROM_EVIDENCE")
            self.assertIn("interface_contract_map.json", result["evidence_source"])

    def test_clarify_lookup_unknown_escalates(self):
        """lookup returns ESCALATE_TO_HUMAN when question matches nothing."""
        lookup_mod = load_module(
            "lookup_speckit_clarify_answer",
            SCRIPTS / "lookup_speckit_clarify_answer.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            ws = _setup_workspace(tmp)
            sync = ws / ".specify" / "sync"
            write_json(sync / "interface_contract_map.json", {"contracts": []})
            write_json(sync / "data_ownership_map.json", {"data_objects": []})
            write_json(sync / "open_questions_tbd_map.json", {"items": []})

            result = lookup_mod.lookup(ws, "What is the preferred font size for the UI?")
            self.assertEqual(result["classification"], "ESCALATE_TO_HUMAN")


if __name__ == "__main__":
    unittest.main()
