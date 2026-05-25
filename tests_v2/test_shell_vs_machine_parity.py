"""Shell-vs-machine parity tests.

Enforce that no script in scripts/ reimplements plan-green semantics
independently, in particular the old bug pattern of accepting "FIX" or
"HANDLED" as green decisions alongside "PASS".
"""
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"


def _all_py_script_contents() -> list[tuple[str, str]]:
    """Return (filename, content) for all .py files in scripts/."""
    result = []
    for path in sorted(_SCRIPTS_DIR.glob("*.py")):
        result.append((path.name, path.read_text(encoding="utf-8", errors="replace")))
    return result


class TestNoReimplementedGateLogic(unittest.TestCase):
    """No script may contain the old plan-green bug pattern."""

    def test_no_script_hardcodes_fix_as_green_decision(self):
        """The old bug: treating "FIX" as an acceptable green decision alongside "PASS"."""
        offenders = []
        for filename, content in _all_py_script_contents():
            if '"PASS"' in content and '"FIX"' in content:
                # Check for the set pattern: both in a set/in-expression as gate decisions
                # Flag if they appear in a set literal together or in an in-expression
                if '{"PASS", "FIX"' in content or '"FIX", "PASS"' in content:
                    offenders.append(filename)
                elif '"PASS", "FIX", "HANDLED"' in content or '"FIX", "HANDLED"' in content:
                    offenders.append(filename)
        self.assertEqual(
            offenders,
            [],
            f"Scripts hardcode FIX as green decision (old bug): {offenders}",
        )

    def test_no_script_hardcodes_handled_as_green_decision(self):
        """The old bug: treating "HANDLED" as an acceptable green decision alongside "PASS"."""
        offenders = []
        for filename, content in _all_py_script_contents():
            if '"PASS"' in content and '"HANDLED"' in content:
                if '{"PASS", "HANDLED"' in content or '"HANDLED", "PASS"' in content:
                    offenders.append(filename)
                elif 'in {"PASS", ' in content and '"HANDLED"' in content:
                    # Narrower check: the decision check pattern with HANDLED in same set
                    lines = content.splitlines()
                    for line in lines:
                        if '"HANDLED"' in line and '"PASS"' in line and ("in {" in line or "in {" in line):
                            offenders.append(filename)
                            break
        self.assertEqual(
            offenders,
            [],
            f"Scripts hardcode HANDLED as green decision (old bug): {offenders}",
        )

    def test_gate_module_is_importable(self):
        """The gates module must be importable."""
        from hldspec.gates import plan_gate_status, prework_gate_status  # noqa: F401
        self.assertTrue(callable(plan_gate_status))
        self.assertTrue(callable(prework_gate_status))


if __name__ == "__main__":
    unittest.main()
