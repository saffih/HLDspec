"""Gate alignment parity tests.

Enforce that all paths that check plan-green use hldspec.gates, not
their own reimplementation.
"""
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


class TestGateModuleUsage(unittest.TestCase):
    """Parity tests: every caller of plan-green must use hldspec.gates."""

    def _read(self, rel: str) -> str:
        return (_REPO_ROOT / rel).read_text(encoding="utf-8", errors="replace")

    def test_render_hldspec_checkpoint_uses_gates_module(self):
        content = self._read("scripts/render_hldspec_checkpoint.py")
        self.assertTrue(
            "from hldspec.gates import" in content or "hldspec.gates" in content,
            "render_hldspec_checkpoint.py must import from hldspec.gates",
        )

    def test_build_hldspec_state_uses_gates_module(self):
        content = self._read("scripts/build_hldspec_state.py")
        self.assertIn(
            "from hldspec.gates import",
            content,
            "build_hldspec_state.py must import from hldspec.gates",
        )

    def test_spec_build_plan_machine_uses_gates_module(self):
        content = self._read("hldspec/machines/spec_build_plan.py")
        self.assertIn(
            "from hldspec.gates import",
            content,
            "hldspec/machines/spec_build_plan.py must import from hldspec.gates",
        )


if __name__ == "__main__":
    unittest.main()
