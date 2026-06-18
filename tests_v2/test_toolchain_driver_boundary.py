from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from hldspec import toolchain_driver_boundary as tdb


class ClassifyPathTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-driver-boundary-")
        self.target = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_hldspec_dir_is_owned(self) -> None:
        self.assertEqual(
            tdb.ZONE_HLDSPEC_OWNED,
            tdb.classify_path(self.target, self.target / ".hldspec" / "helper_selection.json"),
        )

    def test_specify_source_is_adapter_mirror(self) -> None:
        self.assertEqual(
            tdb.ZONE_ADAPTER_MIRROR,
            tdb.classify_path(self.target, self.target / ".specify" / "source" / "speckit_single_spec_input.md"),
        )

    def test_specify_memory_is_read_only_evidence(self) -> None:
        self.assertEqual(
            tdb.ZONE_READ_ONLY_EVIDENCE,
            tdb.classify_path(self.target, self.target / ".specify" / "memory" / "constitution.md"),
        )

    def test_specs_dir_is_read_only_evidence(self) -> None:
        self.assertEqual(
            tdb.ZONE_READ_ONLY_EVIDENCE,
            tdb.classify_path(self.target, self.target / "specs" / "001-foo" / "spec.md"),
        )

    def test_other_specify_paths_are_tool_owned_forbidden(self) -> None:
        self.assertEqual(
            tdb.ZONE_TOOL_OWNED_FORBIDDEN,
            tdb.classify_path(self.target, self.target / ".specify" / "templates" / "spec-template.md"),
        )

    def test_unknown_path_escalates_by_default(self) -> None:
        self.assertEqual(
            tdb.ZONE_AMBIGUOUS_ESCALATE,
            tdb.classify_path(self.target, self.target / "src" / "app.py"),
        )

    def test_absolute_path_outside_target_escalates(self) -> None:
        outside = self.target.parent / "elsewhere" / "file.txt"
        self.assertEqual(tdb.ZONE_AMBIGUOUS_ESCALATE, tdb.classify_path(self.target, outside))

    def test_relative_path_input_is_supported(self) -> None:
        self.assertEqual(
            tdb.ZONE_HLDSPEC_OWNED,
            tdb.classify_path(self.target, Path(".hldspec/helper_selection.json")),
        )


class ApprovedWriteSeamTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="hldspec-driver-boundary-")
        self.target = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_hldspec_owned_is_approved(self) -> None:
        path = self.target / ".hldspec" / "x.json"
        self.assertTrue(tdb.is_approved_write_seam(self.target, path))
        self.assertFalse(tdb.is_forbidden_write(self.target, path))

    def test_adapter_mirror_is_approved(self) -> None:
        path = self.target / ".specify" / "source" / "x.md"
        self.assertTrue(tdb.is_approved_write_seam(self.target, path))
        self.assertFalse(tdb.is_forbidden_write(self.target, path))

    def test_read_only_evidence_is_forbidden_to_write(self) -> None:
        path = self.target / "specs" / "001-foo" / "spec.md"
        self.assertFalse(tdb.is_approved_write_seam(self.target, path))
        self.assertTrue(tdb.is_forbidden_write(self.target, path))

    def test_tool_owned_forbidden_is_forbidden_to_write(self) -> None:
        path = self.target / ".specify" / "templates" / "x.md"
        self.assertTrue(tdb.is_forbidden_write(self.target, path))

    def test_ambiguous_is_forbidden_to_write(self) -> None:
        path = self.target / "src" / "app.py"
        self.assertTrue(tdb.is_forbidden_write(self.target, path))


if __name__ == "__main__":
    unittest.main()
