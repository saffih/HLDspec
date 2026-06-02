from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_speckit_constitution_from_hld_verify.py"


def load_module():
    spec = importlib.util.spec_from_file_location("build_speckit_constitution_from_hld_verify", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _hld_section(section_id: str, title: str, specs: str, verify: str, desc: str = "") -> str:
    desc_line = f"HLD-DESC: {desc}\n" if desc else ""
    verify_line = f"HLD-VERIFY: {verify}\n" if verify else ""
    return (
        f"## {section_id} - {title}\n\n"
        f"HLD-ID: {section_id}\n"
        f"{desc_line}"
        f"HLD-ROLE: architecture\n"
        f"HLD-STATUS: active\n"
        f"HLD-RISK: HIGH\n"
        f"HLD-SPECS: {specs}\n"
        f"HLD-RESOURCES: flow.py\n"
        f"{verify_line}"
        "\nSection prose.\n"
    )


def _setup_workspace(tmp: Path, hld_text: str, existing_rules: list | None = None) -> None:
    sync = tmp / ".specify" / "sync"
    sync.mkdir(parents=True)
    plan = {"required_rules": existing_rules or [], "schema_version": 1}
    (sync / "constitution_update_plan.json").write_text(json.dumps(plan))
    (tmp / "HLD.md").write_text(hld_text)


def _read_rules(ws: Path) -> list:
    return json.loads(
        (ws / ".specify" / "sync" / "constitution_update_plan.json").read_text()
    )["required_rules"]


class ConstitutionFromHldVerifyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = load_module()

    def test_constitution_section_with_verify_produces_rule(self):
        hld = _hld_section(
            "HLD-003", "Core model", "constitution",
            "SQLite is truth; markdown is one-way.",
            desc='HLD-003 is in-scope governance at high risk, touching data; "SQLite is the single source of truth".',
        )
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _setup_workspace(ws, hld)
            result = self.mod.augment(ws)
            rules = _read_rules(ws)

        self.assertEqual(result["rules_added"], 1)
        self.assertEqual(result["skipped_no_verify"], [])
        self.assertEqual(len(rules), 1)
        r = rules[0]
        self.assertEqual(r["rule_id"], "HLD-003")
        self.assertEqual(r["name"], "Core model")
        self.assertEqual(r["rule"], "SQLite is truth; markdown is one-way.")
        self.assertIn("single source of truth", r["rationale"])

    def test_constitution_section_without_verify_is_skipped(self):
        hld = _hld_section("HLD-004", "Lifecycle", "constitution", verify="")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _setup_workspace(ws, hld)
            result = self.mod.augment(ws)

        self.assertEqual(result["rules_added"], 0)
        self.assertIn("HLD-004", result["skipped_no_verify"])

    def test_non_constitution_section_is_ignored(self):
        hld = _hld_section("HLD-006", "Escalation", "TBD", "some invariant here")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _setup_workspace(ws, hld)
            result = self.mod.augment(ws)

        self.assertEqual(result["rules_added"], 0)
        self.assertEqual(result["skipped_no_verify"], [])

    def test_rerun_does_not_duplicate_existing_rule(self):
        hld = _hld_section("HLD-003", "Core model", "constitution", "SQLite is truth.")
        existing = [{"rule_id": "HLD-003", "name": "Core model", "rule": "SQLite is truth.", "rationale": "x"}]
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _setup_workspace(ws, hld, existing_rules=existing)
            result = self.mod.augment(ws)
            rules = _read_rules(ws)

        self.assertEqual(result["rules_added"], 0)
        self.assertEqual(result["status"], "NO_NEW_RULES")
        self.assertEqual(len(rules), 1)

    def test_multiple_constitution_sections_all_extracted(self):
        hld = (
            _hld_section("HLD-003", "Core model", "constitution", "SQLite is truth.")
            + _hld_section("HLD-004", "Lifecycle", "constitution", "Only four states exist.")
            + _hld_section("HLD-006", "Escalation", "TBD", "escalation prose")
        )
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _setup_workspace(ws, hld)
            result = self.mod.augment(ws)
            rules = _read_rules(ws)

        self.assertEqual(result["rules_added"], 2)
        rule_ids = {r["rule_id"] for r in rules}
        self.assertIn("HLD-003", rule_ids)
        self.assertIn("HLD-004", rule_ids)
        self.assertNotIn("HLD-006", rule_ids)

    def test_rationale_falls_back_to_title_when_no_desc(self):
        hld = _hld_section("HLD-005", "Wait model", "constitution", "escalate == split.")
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            _setup_workspace(ws, hld)
            self.mod.augment(ws)
            rules = _read_rules(ws)

        self.assertEqual(rules[0]["rationale"], "Wait model")


if __name__ == "__main__":
    unittest.main()
