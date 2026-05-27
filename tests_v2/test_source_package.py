import tempfile
import unittest
from pathlib import Path

from hldspec import hld_source_package as sp
from hldspec.workspace_adapter import TargetWorkspaceAdapter


def _seed_min_package(source_dir: Path) -> None:
    """Write the minimal required content files."""
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / sp.AUTHORITATIVE_FILES["hld"]).write_text("# HLD\n", encoding="utf-8")
    (source_dir / sp.AUTHORITATIVE_FILES["marked_hld"]).write_text(
        "# HLD\n<!-- a:intro -->\n", encoding="utf-8"
    )
    (source_dir / sp.AUTHORITATIVE_FILES["reference_map"]).write_text(
        '{"a:intro": {}}\n', encoding="utf-8"
    )
    (source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).write_text(
        "# Single spec input\n", encoding="utf-8"
    )


class SourcePackageContractTests(unittest.TestCase):
    def test_required_files_are_subset_of_authoritative(self):
        for filename in sp.REQUIRED_FILES:
            self.assertIn(filename, sp.AUTHORITATIVE_FILES.values())

    def test_constitution_proposal_not_mirrored(self):
        self.assertNotIn(sp.CONSTITUTION_PROPOSAL_FILE, sp.MIRROR_FILES)

    def test_manifest_excludes_itself(self):
        # The manifest must not try to hash source_manifest.json/source_package.json.
        self.assertNotIn(sp.SOURCE_MANIFEST_FILE, sp.AUTHORITATIVE_FILES.values())
        self.assertNotIn(sp.SOURCE_PACKAGE_FILE, sp.AUTHORITATIVE_FILES.values())


class SourcePackageBuildTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        _seed_min_package(self.source_dir)

    def tearDown(self):
        self._tmp.cleanup()

    def test_adapter_paths(self):
        self.assertEqual(self.source_dir, self.root / ".hldspec" / "source_package")
        self.assertEqual(
            self.adapter.specify_source_mirror_dir, self.root / ".specify" / "source"
        )
        self.assertEqual(
            self.adapter.specify_memory_dir, self.root / ".specify" / "memory"
        )

    def test_manifest_hashes_present_marks_missing(self):
        manifest = sp.compute_manifest(self.source_dir)
        self.assertTrue(manifest["hld"]["present"])
        self.assertIsNotNone(manifest["hld"]["sha256"])
        # engineering_guidelines not seeded -> absent, no hash.
        self.assertFalse(manifest["engineering_guidelines"]["present"])
        self.assertIsNone(manifest["engineering_guidelines"]["sha256"])

    def test_source_package_metadata_keys(self):
        meta = sp.write_source_package(
            self.source_dir, hld_source_ref="/src/HLD.md", state="SOURCE_PACKAGE_IMPORTED"
        )
        for key in (
            "schema_version",
            "hld_source_ref",
            "state",
            "manifest_file",
            "mirror_files",
            "required_files",
        ):
            self.assertIn(key, meta)
        self.assertEqual(meta["schema_version"], sp.SCHEMA_VERSION)
        self.assertTrue((self.source_dir / sp.SOURCE_PACKAGE_FILE).is_file())
        self.assertTrue((self.source_dir / sp.SOURCE_MANIFEST_FILE).is_file())

    def test_validation_passes_when_complete(self):
        sp.write_source_package(
            self.source_dir, hld_source_ref="/src/HLD.md", state="x"
        )
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(result.ok, msg=f"{result.missing} {result.hash_mismatches}")

    def test_validation_flags_missing_required(self):
        (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).unlink()
        result = sp.validate_source_package(self.source_dir)
        self.assertFalse(result.ok)
        self.assertIn(sp.AUTHORITATIVE_FILES["single_spec_input"], result.missing)

    def test_validation_flags_tampered_file(self):
        sp.write_source_package(
            self.source_dir, hld_source_ref="/src/HLD.md", state="x"
        )
        # Tamper with a hashed file after the manifest was written.
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld"]).write_text(
            "# HLD changed\n", encoding="utf-8"
        )
        result = sp.validate_source_package(self.source_dir)
        self.assertFalse(result.ok)
        self.assertIn(sp.AUTHORITATIVE_FILES["hld"], result.hash_mismatches)


class SpecifyMirrorTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")

    def tearDown(self):
        self._tmp.cleanup()

    def test_mirror_copies_runner_files(self):
        written = sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        self.assertIn(sp.AUTHORITATIVE_FILES["hld"], written)
        self.assertIn(sp.SOURCE_MANIFEST_FILE, written)
        self.assertTrue((self.mirror_dir / sp.AUTHORITATIVE_FILES["hld"]).is_file())

    def test_mirror_marks_markdown_generated(self):
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        text = (self.mirror_dir / sp.AUTHORITATIVE_FILES["hld"]).read_text(encoding="utf-8")
        self.assertIn("GENERATED by HLDspec", text)

    def test_mirror_excludes_constitution_proposal(self):
        (self.source_dir / sp.CONSTITUTION_PROPOSAL_FILE).write_text(
            "# Constitution proposal\n", encoding="utf-8"
        )
        # A stale proposal in the mirror must be removed on re-materialise.
        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        (self.mirror_dir / sp.CONSTITUTION_PROPOSAL_FILE).write_text("stale\n", encoding="utf-8")
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        self.assertFalse((self.mirror_dir / sp.CONSTITUTION_PROPOSAL_FILE).exists())

    def test_mirror_is_idempotent(self):
        first = sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        second = sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        self.assertEqual(first, second)

    def test_mirror_removes_orphan_managed_file(self):
        # A managed file present in the mirror but absent from the source package
        # must be removed on re-materialise (no stale orphans).
        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        orphan = sp.AUTHORITATIVE_FILES["engineering_guidelines"]
        self.assertNotIn(orphan, sp.REQUIRED_FILES)  # not seeded -> absent in source
        (self.mirror_dir / orphan).write_text("stale guidelines\n", encoding="utf-8")
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        self.assertFalse((self.mirror_dir / orphan).exists())

    def test_mirror_preserves_non_hldspec_content(self):
        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        keep = self.mirror_dir / "user_notes.md"
        keep.write_text("human notes\n", encoding="utf-8")
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        self.assertTrue(keep.is_file())
        self.assertEqual(keep.read_text(encoding="utf-8"), "human notes\n")


if __name__ == "__main__":
    unittest.main()
