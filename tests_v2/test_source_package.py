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
    (source_dir / sp.AUTHORITATIVE_FILES["engineering_guidelines"]).write_text(
        "# Engineering Guidelines\n", encoding="utf-8"
    )


class SourcePackageContractTests(unittest.TestCase):
    def test_required_files_are_subset_of_authoritative(self):
        for filename in sp.REQUIRED_FILES:
            self.assertIn(filename, sp.AUTHORITATIVE_FILES.values())

    def test_engineering_guidelines_are_required_and_mirrored(self):
        filename = sp.AUTHORITATIVE_FILES["engineering_guidelines"]
        self.assertIn(filename, sp.AUTHORITATIVE_FILES.values())
        self.assertIn(filename, sp.MIRROR_FILES)
        self.assertIn(filename, sp.REQUIRED_FILES)

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
        self.mirror_dir = self.adapter.specify_source_mirror_dir
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
        # engineering_guidelines is seeded -> present with a hash.
        self.assertTrue(manifest["engineering_guidelines"]["present"])
        self.assertIsNotNone(manifest["engineering_guidelines"]["sha256"])
        # constitution proposal is not seeded -> absent, no hash.
        self.assertFalse(manifest["constitution_proposal"]["present"])
        self.assertIsNone(manifest["constitution_proposal"]["sha256"])

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

    def test_write_source_package_round_trips_binding_fields(self):
        import json

        sp.write_source_package(
            self.source_dir,
            hld_source_ref="/src/HLD.md",
            state="SOURCE_PACKAGE_IMPORTED",
            target_root=self.root,
            source_sha256="a" * 64,
        )
        meta = json.loads((self.source_dir / sp.SOURCE_PACKAGE_FILE).read_text(encoding="utf-8"))
        self.assertEqual("HLDspec", meta["created_by"])
        self.assertTrue(meta["created_at"])
        self.assertEqual(sp.BINDING_SCHEMA_VERSION, meta["binding_schema_version"])
        self.assertEqual(sp.normalized_target_path(self.root), meta["target_path"])
        self.assertEqual(sp.path_sha256(meta["target_path"]), meta["target_path_sha256"])
        self.assertEqual("/src/HLD.md", meta["source_ref"])
        self.assertEqual("a" * 64, meta["source_sha256"])

    def test_write_source_package_without_target_is_unbound(self):
        import json

        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")
        meta = json.loads((self.source_dir / sp.SOURCE_PACKAGE_FILE).read_text(encoding="utf-8"))
        for field in sp.BINDING_FIELDS:
            self.assertNotIn(field, meta)

    def test_build_content_stamps_binding_and_discovery_trusts_it(self):
        import json

        from hldspec import target_discovery as td

        source_hld = self.root / "SourceHLD.md"
        source_hld.write_text("# HLD\n\n## HLD-001 - Demo\n\nHLD-ID: HLD-001\n", encoding="utf-8")
        build = sp.build_source_package_content(
            self.root,
            source_hld.read_text(encoding="utf-8"),
            hld_source_ref=str(source_hld),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")
        meta = json.loads((self.source_dir / sp.SOURCE_PACKAGE_FILE).read_text(encoding="utf-8"))
        self.assertEqual(sp.normalized_target_path(self.root), meta["target_path"])
        # Source content is available at the ref, so its hash is recorded.
        self.assertEqual(sp._sha256(source_hld), meta["source_sha256"])

        report = td.build_target_discovery(self.root)
        self.assertTrue(report["trusted_hldspec_lineage"])
        self.assertEqual(td.BINDING_BOUND_MATCH, report["source_package_binding"]["state"])

    def test_build_generates_engineering_guidelines_and_mirrors_it(self):
        from hldspec import engineering_selection as es

        build = sp.build_source_package_content(
            self.root,
            "# HLD\n\n## Intro\n\nText.\n",
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")
        engineering_guidelines = self.source_dir / sp.AUTHORITATIVE_FILES["engineering_guidelines"]
        mirror_guidelines = self.mirror_dir / sp.AUTHORITATIVE_FILES["engineering_guidelines"]
        self.assertTrue(
            engineering_guidelines.exists(),
            msg="engineering_guidelines.md must be generated for a real source package build",
        )
        self.assertTrue(
            mirror_guidelines.exists(),
            msg="engineering_guidelines.md must be mirrored into .specify/source",
        )
        # Generated content is real selected guidance, not a stub.
        self.assertEqual([], es.validate_engineering_guidelines(engineering_guidelines.read_text(encoding="utf-8")))
        # Manifest tracks it as present with a hash.
        manifest = sp.compute_manifest(self.source_dir)
        self.assertTrue(manifest["engineering_guidelines"]["present"])
        self.assertIsNotNone(manifest["engineering_guidelines"]["sha256"])


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
        orphan = sp.AUTHORITATIVE_FILES["runbook"]
        self.assertNotIn(orphan, sp.REQUIRED_FILES)  # not seeded -> absent in source
        (self.mirror_dir / orphan).write_text("stale runbook\n", encoding="utf-8")
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
