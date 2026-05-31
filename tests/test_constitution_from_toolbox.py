"""Tests for build_speckit_constitution_from_toolbox.py (the Link-1 wire)."""
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

# An HLD with enough surfaces to trigger CLI/API/persistence/UI cards.
HLD_TEXT = (
    "The product exposes an HTTP API and a CLI over a SQLite database, "
    "plus a user-visible UI with forms and navigation."
)


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


class TestConstitutionFromToolbox(unittest.TestCase):
    def setUp(self):
        self.mod = load_module(
            "build_speckit_constitution_from_toolbox",
            SCRIPTS / "build_speckit_constitution_from_toolbox.py",
        )

    def _make_workspace(self, tmp: str) -> Path:
        ws = Path(tmp)
        sync = ws / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        write_json(sync / "constitution_update_plan.json", {
            "schema_version": 1,
            "required_rules": [
                {"rule_id": "ARCH-001", "name": "HLD", "rule": "r", "rationale": "g"},
            ],
        })
        (ws / "HLD.md").write_text(HLD_TEXT, encoding="utf-8")
        return ws

    def test_wires_toolbox_candidates_into_required_rules(self):
        """The core Link-1 assertion: candidate cards reach the update plan."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            sync = ws / ".specify" / "sync"

            result = self.mod.augment(ws)

            updated = json.loads((sync / "constitution_update_plan.json").read_text())
            rules = updated["required_rules"]
            eng_rules = [r for r in rules if r["rule_id"].startswith("ENG-")]

            self.assertGreater(result["toolbox_rules_added"], 0)
            self.assertGreater(len(eng_rules), 0)
            # Original ARCH rule is preserved.
            self.assertTrue(any(r["rule_id"] == "ARCH-001" for r in rules))
            # Traceability marker present for dedup.
            self.assertTrue(any("engineering_toolbox:" in r.get("rationale", "") for r in eng_rules))

    def test_fully_tested_axiom_is_present_and_strict(self):
        """design_for_testability must ride in as the strict, surface-agnostic axiom."""
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            sync = ws / ".specify" / "sync"

            self.mod.augment(ws)
            rules = json.loads((sync / "constitution_update_plan.json").read_text())["required_rules"]

            axiom = next(
                (r for r in rules if "testing.design_for_testability" in r.get("rationale", "")),
                None,
            )
            self.assertIsNotNone(axiom, "fully-tested axiom card did not reach the plan")
            text = axiom["rule"].lower()
            # Strict, not light: executed-and-green, every surface incl. UI, block-if-no-harness.
            self.assertIn("fully tested", text)
            self.assertIn("execute and pass", text)
            self.assertIn("browser", text)  # real UI/browser discriminator, not "ui" inside "require"
            self.assertTrue("block" in text or "waiver" in text)

    def test_idempotent_no_duplicate_eng_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = self._make_workspace(tmp)
            sync = ws / ".specify" / "sync"

            self.mod.augment(ws)  # first run
            first = json.loads((sync / "constitution_update_plan.json").read_text())["required_rules"]
            eng_first = sorted(r["rule_id"] for r in first if r["rule_id"].startswith("ENG-"))

            self.mod.augment(ws)  # second run
            second = json.loads((sync / "constitution_update_plan.json").read_text())["required_rules"]
            eng_second = sorted(r["rule_id"] for r in second if r["rule_id"].startswith("ENG-"))

            self.assertEqual(eng_first, eng_second, "Duplicate ENG rules after second run")

    def test_uses_source_hld_arg_when_workspace_has_no_hld(self):
        with tempfile.TemporaryDirectory() as tmp:
            ws = Path(tmp)
            sync = ws / ".specify" / "sync"
            sync.mkdir(parents=True, exist_ok=True)
            write_json(sync / "constitution_update_plan.json", {"required_rules": []})
            hld = ws / "elsewhere" / "HLD.md"
            hld.parent.mkdir(parents=True, exist_ok=True)
            hld.write_text(HLD_TEXT, encoding="utf-8")

            result = self.mod.augment(ws, source_hld=str(hld))
            self.assertGreater(result["toolbox_rules_added"], 0)


if __name__ == "__main__":
    unittest.main()
