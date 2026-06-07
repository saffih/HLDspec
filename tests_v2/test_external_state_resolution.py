"""Guard tests: in external state-location mode, control-state reads must resolve
the controller root (via the .hldspec-run.json pointer), not target/.hldspec.

These cover the external-mode resolution regressions: a runner in external mode
keeps only the pointer in the target, so any code reading target/.hldspec directly
silently misses the real state.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hldspec_agent_session as facade  # noqa: E402
from hldspec import run_state  # noqa: E402


def _make_external(tmp: str) -> tuple[Path, Path]:
    """A target with only the pointer; real .hldspec lives under the controller root."""
    target = Path(tmp) / "target"
    controller = Path(tmp) / "controller"
    target.mkdir()
    (controller / ".hldspec").mkdir(parents=True)
    source = target / "HLD.md"
    source.write_text("# HLD\n", encoding="utf-8")
    run_state.write_pointer(
        target,
        controller_root=controller,
        source=source,
        source_hash="deadbeef",
        mode="update",
        agent="test",
        workflow_trigger="build_loop_ready",
        created_or_updated_at="2026-06-07T00:00:00+00:00",
    )
    return target, controller


class ExternalStateResolutionTests(unittest.TestCase):
    def test_resolver_points_at_controller_in_external_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            self.assertEqual(
                facade._resolve_hldspec_dir(target).resolve(),
                (controller / ".hldspec").resolve(),
            )

    def test_open_questions_resolved_from_controller(self):
        # P1b: unresolved checkpoints stored in the controller must not be hidden.
        with tempfile.TemporaryDirectory() as tmp:
            target, controller = _make_external(tmp)
            (controller / ".hldspec" / "interview_answers.json").write_text(
                json.dumps({"open_questions": ["Q-EXT: confirm scope"]}),
                encoding="utf-8",
            )
            qs = facade.collect_open_questions(target)
            # Pre-fix this read target/.hldspec (absent) and returned [].
            self.assertIn("Q-EXT: confirm scope", qs)

    def test_non_external_mode_unchanged(self):
        # No pointer -> resolver and open-questions behave exactly as before.
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "t"
            (target / ".hldspec").mkdir(parents=True)
            self.assertEqual(facade._resolve_hldspec_dir(target), target / ".hldspec")
            (target / ".hldspec" / "interview_answers.json").write_text(
                json.dumps({"open_questions": ["Q-LOCAL"]}), encoding="utf-8"
            )
            self.assertIn("Q-LOCAL", facade.collect_open_questions(target))


if __name__ == "__main__":
    unittest.main()
