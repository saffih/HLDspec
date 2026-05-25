"""Tests for check_architecture_fitness.py."""
import importlib.util
import sys
import unittest
from pathlib import Path

# Load the script as a module without requiring it on sys.path
_REPO_ROOT = Path(__file__).parent.parent
_SCRIPT_PATH = _REPO_ROOT / "scripts" / "check_architecture_fitness.py"

_MOD_NAME = "check_architecture_fitness"
spec = importlib.util.spec_from_file_location(_MOD_NAME, _SCRIPT_PATH)
_mod = importlib.util.module_from_spec(spec)
sys.modules[_MOD_NAME] = _mod
spec.loader.exec_module(_mod)

check_machine_forbidden_imports = _mod.check_machine_forbidden_imports
check_deprecated_terms = _mod.check_deprecated_terms
check_skeptic_finding_fields = _mod.check_skeptic_finding_fields


class TestMachinesForbiddenImports(unittest.TestCase):
    """Check 3: machines must not import subprocess or requests directly."""

    def test_no_forbidden_imports_in_machines(self):
        results = check_machine_forbidden_imports(_REPO_ROOT)
        failures = [r for r in results if r.level == "FAIL"]
        self.assertEqual(
            failures,
            [],
            f"Forbidden imports found in machines: {[r.message for r in failures]}",
        )

    def test_check_passes_with_pass_result(self):
        results = check_machine_forbidden_imports(_REPO_ROOT)
        levels = {r.level for r in results}
        self.assertIn("PASS", levels)
        self.assertNotIn("FAIL", levels)


class TestDeprecatedTermsInMachines(unittest.TestCase):
    """Check 4: deprecated terms must not appear in active control logic."""

    def test_no_deprecated_terms_in_machines(self):
        results = check_deprecated_terms(_REPO_ROOT)
        failures = [r for r in results if r.level == "FAIL"]
        self.assertEqual(
            failures,
            [],
            f"Deprecated terms found in machines: {[r.message for r in failures]}",
        )

    def test_check_passes_with_pass_result(self):
        results = check_deprecated_terms(_REPO_ROOT)
        levels = {r.level for r in results}
        self.assertIn("PASS", levels)
        self.assertNotIn("FAIL", levels)


class TestSkepticFindingFields(unittest.TestCase):
    """Check 5: SkepticFinding required fields match REQUIRED_FINDING_FIELDS."""

    def test_skeptic_finding_fields_match(self):
        results = check_skeptic_finding_fields(_REPO_ROOT)
        failures = [r for r in results if r.level == "FAIL"]
        self.assertEqual(
            failures,
            [],
            f"SkepticFinding field mismatch: {[r.message for r in failures]}",
        )

    def test_check_passes(self):
        results = check_skeptic_finding_fields(_REPO_ROOT)
        levels = {r.level for r in results}
        self.assertIn("PASS", levels)
        self.assertNotIn("FAIL", levels)


if __name__ == "__main__":
    unittest.main()
