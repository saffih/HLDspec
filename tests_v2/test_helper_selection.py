from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from hldspec import helper_registry, helper_selection as hsel
from hldspec.hld_source_package import build_helper_recommendations
from hldspec.workspace_adapter import TargetWorkspaceAdapter


class HelperSelectionWriteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-helper-selection-")
        self.target = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_write_operational_helper_succeeds(self) -> None:
        path = hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        self.assertEqual(hsel.selection_path(self.target), path)
        self.assertTrue(path.is_file())
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual("speckit", data["selected_helper_id"])
        self.assertEqual("human", data["selected_by"])
        self.assertEqual(hsel.SOURCE_EXPLICIT, data["source"])

    def test_write_planned_helper_is_rejected(self) -> None:
        for helper_id in helper_registry.PLANNED_HELPER_IDS:
            with self.assertRaises(hsel.InvalidHelperSelectionError):
                hsel.write_helper_selection(self.target, helper_id, selected_by="human")
        self.assertIsNone(hsel.read_helper_selection(self.target))

    def test_write_unknown_helper_is_rejected(self) -> None:
        with self.assertRaises(hsel.InvalidHelperSelectionError):
            hsel.write_helper_selection(self.target, "made-up-helper", selected_by="human")

    def test_invalid_source_is_rejected(self) -> None:
        with self.assertRaises(hsel.InvalidHelperSelectionError):
            hsel.write_helper_selection(self.target, "speckit", selected_by="human", source="bogus")

    def test_read_missing_selection_returns_none(self) -> None:
        self.assertIsNone(hsel.read_helper_selection(self.target))

    def test_selection_carries_registry_provenance(self) -> None:
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        data = hsel.read_helper_selection(self.target)
        self.assertEqual(
            helper_registry.registry_sha256(),
            data["registry_provenance"]["registry_sha256"],
        )


class RecommendationsCurrentTests(unittest.TestCase):
    def test_none_recommendations_is_not_current(self) -> None:
        self.assertFalse(hsel.recommendations_current(None))

    def test_fresh_recommendations_are_current(self) -> None:
        self.assertTrue(hsel.recommendations_current(build_helper_recommendations()))

    def test_stale_provenance_is_not_current(self) -> None:
        rec = build_helper_recommendations()
        rec["registry_provenance"]["registry_sha256"] = "deadbeef"
        self.assertFalse(hsel.recommendations_current(rec))


class ToolchainStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-helper-selection-")
        self.target = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.target, layout="new")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_no_recommendation_no_selection_defaults_to_registry(self) -> None:
        status = hsel.build_toolchain_status(self.target)
        self.assertEqual("ACTION", status["status"])
        self.assertEqual("speckit", status["recommended_helper_id"])
        self.assertEqual("speckit", status["effective_helper_id"])
        self.assertIsNone(status["selected_helper_id"])
        self.assertFalse(status["recommendations_present"])
        self.assertTrue(status["notes"])

    def test_recommendation_present_but_no_selection_is_action(self) -> None:
        self.adapter.source_package_dir.mkdir(parents=True, exist_ok=True)
        (self.adapter.source_package_dir / "helper_recommendations.json").write_text(
            json.dumps(build_helper_recommendations()), encoding="utf-8"
        )
        status = hsel.build_toolchain_status(self.target)
        self.assertEqual("ACTION", status["status"])
        self.assertTrue(status["recommendations_present"])
        self.assertTrue(status["recommendations_current"])

    def test_selection_present_is_pass(self) -> None:
        hsel.write_helper_selection(self.target, "speckit", selected_by="human")
        status = hsel.build_toolchain_status(self.target)
        self.assertEqual("PASS", status["status"])
        self.assertEqual("speckit", status["selected_helper_id"])
        self.assertEqual("speckit", status["effective_helper_id"])

    def test_stale_recommendation_is_noted(self) -> None:
        self.adapter.source_package_dir.mkdir(parents=True, exist_ok=True)
        rec = build_helper_recommendations()
        rec["registry_provenance"]["registry_sha256"] = "deadbeef"
        (self.adapter.source_package_dir / "helper_recommendations.json").write_text(
            json.dumps(rec), encoding="utf-8"
        )
        status = hsel.build_toolchain_status(self.target)
        self.assertFalse(status["recommendations_current"])
        self.assertTrue(any("stale" in note for note in status["notes"]))


if __name__ == "__main__":
    unittest.main()
