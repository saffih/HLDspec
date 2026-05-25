from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from hldspec.prework_contracts import stale_prework_artifacts

PLAN = "spec_build_plan.json"
PREWORK = "speckit_prework_package.md"
QUEUE = "speckit_invocation_queue.json"

T_OLD = 1_000_000.0
T_NEW = 2_000_000.0


def _write(path: Path, mtime: float) -> None:
    path.write_text("x", encoding="utf-8")
    os.utime(path, (mtime, mtime))


class StalePreworkDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.mkdtemp()
        self.sync = Path(self._tmp)

    # ------------------------------------------------------------------ #
    # No-block cases                                                       #
    # ------------------------------------------------------------------ #

    def test_both_artifacts_missing_returns_empty(self) -> None:
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(result, [])

    def test_plan_missing_prework_present_returns_empty(self) -> None:
        _write(self.sync / PREWORK, T_OLD)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(result, [])

    def test_prework_missing_plan_present_returns_empty(self) -> None:
        _write(self.sync / PLAN, T_NEW)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(result, [])

    def test_prework_newer_than_plan_returns_empty(self) -> None:
        _write(self.sync / PLAN, T_OLD)
        _write(self.sync / PREWORK, T_NEW)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(result, [])

    def test_prework_same_mtime_as_plan_returns_empty(self) -> None:
        _write(self.sync / PLAN, T_OLD)
        _write(self.sync / PREWORK, T_OLD)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(result, [])

    # ------------------------------------------------------------------ #
    # Block cases                                                          #
    # ------------------------------------------------------------------ #

    def test_plan_newer_than_prework_returns_blocker(self) -> None:
        _write(self.sync / PLAN, T_NEW)
        _write(self.sync / PREWORK, T_OLD)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(len(result), 1)
        self.assertIn(PREWORK, result[0])

    def test_plan_newer_than_queue_returns_blocker(self) -> None:
        _write(self.sync / PLAN, T_NEW)
        _write(self.sync / QUEUE, T_OLD)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(len(result), 1)
        self.assertIn(QUEUE, result[0])

    def test_plan_newer_than_both_returns_two_blockers(self) -> None:
        _write(self.sync / PLAN, T_NEW)
        _write(self.sync / PREWORK, T_OLD)
        _write(self.sync / QUEUE, T_OLD)
        result = stale_prework_artifacts(self.sync)
        self.assertEqual(len(result), 2)
        artifact_names = " ".join(result)
        self.assertIn(PREWORK, artifact_names)
        self.assertIn(QUEUE, artifact_names)


if __name__ == "__main__":
    unittest.main()
