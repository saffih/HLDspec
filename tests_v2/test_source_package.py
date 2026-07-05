import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hldspec import gate_validator as gv
from hldspec import hld_coverage_scope as hcs
from hldspec import hld_source_package as sp
from hldspec import helper_registry as hr
from hldspec import journey2_hld_coverage_contracts as cov
from hldspec import spec_backlog as sb
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

    def test_helper_recommendations_in_authoritative_files(self):
        self.assertIn("helper_recommendations", sp.AUTHORITATIVE_FILES)
        self.assertEqual("helper_recommendations.json", sp.AUTHORITATIVE_FILES["helper_recommendations"])

    def test_helper_recommendations_not_in_required_files(self):
        # Advisory output — must not be required for package validity.
        self.assertNotIn(sp.AUTHORITATIVE_FILES["helper_recommendations"], sp.REQUIRED_FILES)

    def test_helper_recommendations_not_in_mirror_files(self):
        # J3 advisory guidance — must not be mirrored into .specify/source/ for the SpecKit runner.
        self.assertNotIn(sp.AUTHORITATIVE_FILES["helper_recommendations"], sp.MIRROR_FILES)

    def test_architecture_package_in_authoritative_files(self):
        self.assertIn("architecture_package", sp.AUTHORITATIVE_FILES)
        self.assertEqual("architecture_package.json", sp.AUTHORITATIVE_FILES["architecture_package"])

    def test_architecture_package_not_in_required_files(self):
        # Advisory typed slot — must not be required for package validity.
        self.assertNotIn(sp.AUTHORITATIVE_FILES["architecture_package"], sp.REQUIRED_FILES)

    def test_architecture_package_not_in_mirror_files(self):
        # J2 design-reasoning — must not be mirrored into .specify/source/ for the SpecKit runner.
        self.assertNotIn(sp.AUTHORITATIVE_FILES["architecture_package"], sp.MIRROR_FILES)

    def test_hld_coverage_ledger_in_authoritative_files(self):
        self.assertIn("hld_coverage_ledger", sp.AUTHORITATIVE_FILES)
        self.assertEqual("hld_coverage_ledger.json", sp.AUTHORITATIVE_FILES["hld_coverage_ledger"])

    def test_hld_coverage_ledger_not_required_yet(self):
        # Producer-only slice: future gates consume the ledger, but existing
        # package validation must not fail legacy or seeded packages without it.
        self.assertNotIn(sp.AUTHORITATIVE_FILES["hld_coverage_ledger"], sp.REQUIRED_FILES)

    def test_hld_coverage_ledger_not_mirrored(self):
        # Journey 2 completeness evidence, not SpecKit runner context.
        self.assertNotIn(sp.AUTHORITATIVE_FILES["hld_coverage_ledger"], sp.MIRROR_FILES)

    def test_spec_backlog_in_authoritative_files(self):
        self.assertIn("spec_backlog", sp.AUTHORITATIVE_FILES)
        self.assertEqual("spec_backlog.json", sp.AUTHORITATIVE_FILES["spec_backlog"])

    def test_spec_backlog_not_in_required_files(self):
        self.assertNotIn(sp.AUTHORITATIVE_FILES["spec_backlog"], sp.REQUIRED_FILES)

    def test_spec_backlog_not_in_mirror_files(self):
        self.assertNotIn(sp.AUTHORITATIVE_FILES["spec_backlog"], sp.MIRROR_FILES)

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

    def test_build_emits_advisory_architecture_package_artifact(self):
        import json

        from hldspec import journey2_architecture_package as j2ap

        build = sp.build_source_package_content(
            self.root,
            "# HLD\n\n## Intro\n\nText.\n",
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        # Advisory artifact does not affect package validity (excluded from REQUIRED_FILES).
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

        art_path = self.source_dir / sp.AUTHORITATIVE_FILES["architecture_package"]
        self.assertTrue(art_path.is_file(), msg="architecture_package.json must be emitted by the builder")
        artifact = json.loads(art_path.read_text(encoding="utf-8"))

        # All 14 required fields are present (the typed slot is materialized).
        for field in j2ap.REQUIRED_ARCHITECTURE_PACKAGE_FIELDS:
            self.assertIn(field, artifact)

        # Honest ACTION: human-owned fields are emitted empty, so the slot validates
        # ACTION until authored — it never promotes (and is not in REQUIRED_FILES).
        result = j2ap.validate_architecture_package(artifact)
        self.assertEqual(result["status"], "ACTION")
        self.assertEqual(artifact["validation"]["status"], "ACTION")

        # helper_recommendation is grounded from the registry-derived recommendations,
        # so it is NOT among the missing fields; the human-owned fields are.
        self.assertNotIn("helper_recommendation", result["missing_fields"])
        self.assertEqual(artifact["helper_recommendation"], sp.build_helper_recommendations())
        self.assertIn("architecture_intent", result["missing_fields"])

        # Manifest hashes it (drift detectable); it is NOT mirrored into .specify/source/.
        manifest = sp.compute_manifest(self.source_dir)
        self.assertTrue(manifest["architecture_package"]["present"])
        self.assertIsNotNone(manifest["architecture_package"]["sha256"])
        mirror_art = self.mirror_dir / sp.AUTHORITATIVE_FILES["architecture_package"]
        self.assertFalse(mirror_art.exists(), msg="architecture_package.json must not be mirrored")

    def test_build_emits_hld_coverage_ledger_from_reference_map_and_spec_input(self):
        import json

        hld_text = """# HLD

## HLD-001 - Covered

HLD-ID: HLD-001
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: covered behavior is testable

Covered behavior.

## HLD-002 - Uncovered

HLD-ID: HLD-002
HLD-ROLE: operations
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

Uncovered behavior.
"""
        spec_input = "# Single SpecKit Input\n\n## Requirements\n\n- (HLD-001) Covered behavior.\n"

        with patch("hldspec.single_spec_input.build_single_spec_input", return_value=spec_input):
            build = sp.build_source_package_content(
                self.root,
                hld_text,
                hld_source_ref=str(self.root / "SourceHLD.md"),
                layout="new",
            )

        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")
        ledger_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        cov.validate_coverage_ledger(ledger)

        self.assertEqual(["HLD-001", "HLD-002"], [item["hld_item_id"] for item in ledger])
        by_id = {item["hld_item_id"]: item for item in ledger}
        self.assertEqual(cov.STATUS_COVERED_IN_SDD, by_id["HLD-001"]["status"])
        self.assertEqual("speckit_single_spec_input.md", by_id["HLD-001"]["sdd_section"])
        self.assertEqual(cov.RISK_HIGH, by_id["HLD-001"]["risk"])
        self.assertEqual(cov.STATUS_NOT_COVERED, by_id["HLD-002"]["status"])
        self.assertIsNone(by_id["HLD-002"]["sdd_section"])
        self.assertEqual(cov.RISK_LOW, by_id["HLD-002"]["risk"])

    def test_hld_coverage_ledger_is_deterministic(self):
        ref_map = {
            "anchors": {
                "HLD-002": {"title": "Second", "risk": "LOW"},
                "HLD-001": {"title": "First", "risk": "HIGH"},
            }
        }
        spec_input = "- (HLD-001) First\n"

        first = sp.build_initial_hld_coverage_ledger(ref_map, spec_input)
        second = sp.build_initial_hld_coverage_ledger(ref_map, spec_input)

        self.assertEqual(first, second)
        self.assertEqual(["HLD-001", "HLD-002"], [item["hld_item_id"] for item in first])

    def test_manifest_tracks_hld_coverage_ledger(self):
        import json

        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )

        manifest_data = json.loads((self.source_dir / sp.SOURCE_MANIFEST_FILE).read_text(encoding="utf-8"))
        entry = manifest_data["files"].get("hld_coverage_ledger")
        self.assertIsNotNone(entry, "manifest must include hld_coverage_ledger entry")
        self.assertTrue(entry["present"])
        self.assertIsNotNone(entry["sha256"])

    def test_existing_validation_still_passes_without_hld_coverage_ledger(self):
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")

        result = sp.validate_source_package(self.source_dir)

        self.assertTrue(
            result.ok,
            msg=f"validation must not require producer-only hld_coverage_ledger: "
            f"{result.missing} {result.hash_mismatches}",
        )

    def test_absent_hld_coverage_ledger_preserves_legacy_gate_behavior(self):
        # Existing packages without a produced hld_coverage_ledger.json do not get
        # an invented coverage blocker.
        ctx = gv.GateContext(
            receipt_present=False,
            source_refs=[],
            runskeptic_status=gv.RUNSKEPTIC_NOT_RUN,
            consultant_status=gv.CONSULTANT_NOT_RUN,
            validation_ok=False,
            human_approved=False,
        )

        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)

        self.assertFalse(result.passed)
        self.assertFalse(any("coverage" in blocker.lower() for blocker in result.blockers))

    def test_build_emits_advisory_spec_backlog(self):
        import json

        hld_text = "# HLD\n\n## HLD-001 - Feature A\n\nHLD-ID: HLD-001\n\n## HLD-002 - Feature B\n\nHLD-ID: HLD-002\n"
        build = sp.build_source_package_content(
            self.root,
            hld_text,
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

        backlog_path = self.source_dir / sp.AUTHORITATIVE_FILES["spec_backlog"]
        self.assertTrue(backlog_path.is_file(), msg="spec_backlog.json must be emitted by the builder")
        backlog = json.loads(backlog_path.read_text(encoding="utf-8"))

        result = sb.validate_spec_backlog(backlog)
        self.assertTrue(result.ok, result.errors)

        self.assertIsNone(backlog["active_spec_id"])
        for spec in backlog["specs"]:
            self.assertEqual(spec["status"], "PLANNED")
            self.assertEqual(spec["target_materialization"], "NOT_MATERIALIZED")

        anchor_ids = [s["hld_anchor_ids"][0] for s in backlog["specs"]]
        self.assertIn("HLD-001", anchor_ids)
        self.assertIn("HLD-002", anchor_ids)

    def test_build_spec_backlog_deterministic_ordering(self):
        import json

        hld_text = "# HLD\n\n## HLD-003 - C\n\nHLD-ID: HLD-003\n\n## HLD-001 - A\n\nHLD-ID: HLD-001\n\n## HLD-002 - B\n\nHLD-ID: HLD-002\n"
        build = sp.build_source_package_content(
            self.root,
            hld_text,
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        backlog = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["spec_backlog"]).read_text(encoding="utf-8")
        )
        ids = [s["spec_id"] for s in backlog["specs"]]
        self.assertEqual(ids, [f"SPEC-{i:03d}" for i in range(1, len(ids) + 1)])

    def test_build_spec_backlog_preserves_source_refs(self):
        import json

        hld_text = "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n"
        ref = str(self.root / "SourceHLD.md")
        build = sp.build_source_package_content(
            self.root,
            hld_text,
            hld_source_ref=ref,
            layout="new",
        )
        backlog = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["spec_backlog"]).read_text(encoding="utf-8")
        )
        self.assertEqual(backlog["source_refs"], [ref])

    def test_manifest_tracks_spec_backlog(self):
        import json

        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        manifest_data = json.loads(
            (self.source_dir / sp.SOURCE_MANIFEST_FILE).read_text(encoding="utf-8")
        )
        entry = manifest_data["files"].get("spec_backlog")
        self.assertIsNotNone(entry, "manifest must include spec_backlog entry")
        self.assertTrue(entry["present"])
        self.assertIsNotNone(entry["sha256"])

    def test_spec_backlog_not_in_mirror(self):
        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        mirror_backlog = self.mirror_dir / sp.AUTHORITATIVE_FILES["spec_backlog"]
        self.assertFalse(
            mirror_backlog.exists(),
            "spec_backlog.json must not appear in the SpecKit runner mirror",
        )

    def test_existing_validation_still_passes_without_spec_backlog(self):
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(
            result.ok,
            msg=f"validation must not require advisory spec_backlog: "
            f"{result.missing} {result.hash_mismatches}",
        )

    def test_absent_spec_backlog_preserves_legacy_gate_behavior(self):
        ctx = gv.GateContext(
            receipt_present=False,
            source_refs=[],
            runskeptic_status=gv.RUNSKEPTIC_NOT_RUN,
            consultant_status=gv.CONSULTANT_NOT_RUN,
            validation_ok=False,
            human_approved=False,
        )
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertFalse(any("backlog" in blocker.lower() for blocker in result.blockers))


class HldCoverageScopeContractTests(unittest.TestCase):
    def test_hld_coverage_scope_in_authoritative_files(self):
        self.assertIn("hld_coverage_scope", sp.AUTHORITATIVE_FILES)
        self.assertEqual("hld_coverage_scope.json", sp.AUTHORITATIVE_FILES["hld_coverage_scope"])

    def test_hld_coverage_scope_not_in_required_files(self):
        self.assertNotIn(sp.AUTHORITATIVE_FILES["hld_coverage_scope"], sp.REQUIRED_FILES)

    def test_hld_coverage_scope_not_in_mirror_files(self):
        self.assertNotIn(sp.AUTHORITATIVE_FILES["hld_coverage_scope"], sp.MIRROR_FILES)


class HldCoverageScopeEmissionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_build_emits_hld_coverage_scope(self):
        import json

        hld_text = "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n"
        build = sp.build_source_package_content(
            self.root,
            hld_text,
            hld_source_ref=str(self.root / "SourceHLD.md"),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

        scope_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        self.assertTrue(scope_path.is_file(), msg="hld_coverage_scope.json must be emitted by the builder")
        scope = json.loads(scope_path.read_text(encoding="utf-8"))

        result = hcs.validate_hld_coverage_scope(scope)
        self.assertTrue(result.ok, result.errors)

    def test_emitted_coverage_scope_is_full_hld(self):
        import json

        build = sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(scope["coverage_scope"], "FULL_HLD")

    def test_emitted_active_spec_id_is_none(self):
        import json

        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertIsNone(scope["active_spec_id"])

    def test_emitted_sidecar_does_not_change_ledger_shape(self):
        import json

        hld_text = "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n"
        sp.build_source_package_content(
            self.root,
            hld_text,
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        self.assertIsInstance(ledger, list)
        cov.validate_coverage_ledger(ledger)

    def test_hld_coverage_scope_not_in_mirror(self):
        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        mirror_scope = self.mirror_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        self.assertFalse(
            mirror_scope.exists(),
            "hld_coverage_scope.json must not appear in the SpecKit runner mirror",
        )

    def test_manifest_tracks_hld_coverage_scope(self):
        import json

        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        manifest_data = json.loads(
            (self.source_dir / sp.SOURCE_MANIFEST_FILE).read_text(encoding="utf-8")
        )
        entry = manifest_data["files"].get("hld_coverage_scope")
        self.assertIsNotNone(entry, "manifest must include hld_coverage_scope entry")
        self.assertTrue(entry["present"])
        self.assertIsNotNone(entry["sha256"])

    def test_existing_validation_still_passes_without_hld_coverage_scope(self):
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(
            result.ok,
            msg=f"validation must not require advisory hld_coverage_scope: "
            f"{result.missing} {result.hash_mismatches}",
        )

    def test_absent_hld_coverage_scope_preserves_legacy_gate_behavior(self):
        ctx = gv.GateContext(
            receipt_present=False,
            source_refs=[],
            runskeptic_status=gv.RUNSKEPTIC_NOT_RUN,
            consultant_status=gv.CONSULTANT_NOT_RUN,
            validation_ok=False,
            human_approved=False,
        )
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(result.passed)
        self.assertFalse(any("coverage_scope" in blocker.lower() for blocker in result.blockers))


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

    def test_fresh_mirror_has_no_freshness_blockers(self):
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        self.assertEqual(sp.mirror_freshness_blockers(self.source_dir, self.mirror_dir), [])

    def test_stale_mirror_file_blocks(self):
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        filename = sp.AUTHORITATIVE_FILES["single_spec_input"]
        (self.mirror_dir / filename).write_text("edited by hand\n", encoding="utf-8")
        blockers = sp.mirror_freshness_blockers(self.source_dir, self.mirror_dir)
        self.assertTrue(any(filename in b and "stale" in b for b in blockers), blockers)

    def test_missing_mirror_file_blocks(self):
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        filename = sp.AUTHORITATIVE_FILES["hld"]
        (self.mirror_dir / filename).unlink()
        blockers = sp.mirror_freshness_blockers(self.source_dir, self.mirror_dir)
        self.assertTrue(any("missing" in b and filename in b for b in blockers), blockers)

    def test_unrelated_mirror_file_is_not_judged(self):
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        (self.mirror_dir / "user_notes.md").write_text("human notes\n", encoding="utf-8")
        self.assertEqual(sp.mirror_freshness_blockers(self.source_dir, self.mirror_dir), [])

    def test_orphan_managed_file_blocks(self):
        sp.materialize_specify_mirror(self.source_dir, self.mirror_dir)
        # Managed name that is never part of the mirror set -> orphan if present.
        (self.mirror_dir / sp.CONSTITUTION_PROPOSAL_FILE).write_text("stale\n", encoding="utf-8")
        blockers = sp.mirror_freshness_blockers(self.source_dir, self.mirror_dir)
        self.assertTrue(
            any("orphan" in b and sp.CONSTITUTION_PROPOSAL_FILE in b for b in blockers), blockers
        )


class HelperRecommendationsTests(unittest.TestCase):
    """Tests for the Journey 2 → Journey 3 advisory seam."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_schema_shape(self):
        rec = sp.build_helper_recommendations()
        for key in ("schema_version", "default_helper", "recommended_helpers",
                    "unsupported_helpers", "human_override_allowed", "notes"):
            self.assertIn(key, rec, msg=f"missing key: {key}")
        self.assertEqual(1, rec["schema_version"])

    def test_default_helper_is_speckit(self):
        self.assertEqual("speckit", sp.build_helper_recommendations()["default_helper"])

    def test_speckit_is_implemented(self):
        recs = sp.build_helper_recommendations()["recommended_helpers"]
        speckit = next((h for h in recs if h["helper_id"] == "speckit"), None)
        self.assertIsNotNone(speckit, "speckit must be in recommended_helpers")
        self.assertEqual("implemented", speckit["status"])
        self.assertIn("GUIDE_ONLY", speckit["authority_levels"])
        self.assertIn("PROPOSE_COMMAND", speckit["authority_levels"])

    def test_unsupported_helpers_not_implemented(self):
        unsupported = sp.build_helper_recommendations()["unsupported_helpers"]
        ids = {h["helper_id"] for h in unsupported}
        for helper_id in ("claude-code", "codex", "devin", "manual"):
            self.assertIn(helper_id, ids, msg=f"{helper_id} must be listed as unsupported")
        for h in unsupported:
            self.assertEqual("not_implemented", h["status"],
                             msg=f"{h['helper_id']} must be not_implemented")

    def test_human_override_allowed(self):
        self.assertTrue(sp.build_helper_recommendations()["human_override_allowed"])

    def test_build_content_emits_helper_recommendations(self):
        build = sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")
        rec_path = self.source_dir / sp.AUTHORITATIVE_FILES["helper_recommendations"]
        self.assertTrue(rec_path.is_file(), "helper_recommendations.json must be emitted by build")

    def test_helper_recommendations_not_in_mirror(self):
        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        mirror_dir = self.adapter.specify_source_mirror_dir
        mirror_rec = mirror_dir / sp.AUTHORITATIVE_FILES["helper_recommendations"]
        self.assertFalse(mirror_rec.exists(),
                         "helper_recommendations.json must not appear in the SpecKit runner mirror")

    def test_manifest_tracks_helper_recommendations(self):
        import json
        sp.build_source_package_content(
            self.root,
            "# HLD\n\n## HLD-001 - Feature\n\nHLD-ID: HLD-001\n",
            hld_source_ref=str(self.root / "src.md"),
            layout="new",
        )
        manifest_data = json.loads((self.source_dir / sp.SOURCE_MANIFEST_FILE).read_text(encoding="utf-8"))
        entry = manifest_data["files"].get("helper_recommendations")
        self.assertIsNotNone(entry, "manifest must include helper_recommendations entry")
        self.assertTrue(entry["present"])
        self.assertIsNotNone(entry["sha256"])

    def test_existing_validation_still_passes_without_helper_recommendations(self):
        # A seeded package (no helper_recommendations.json) must still validate OK
        # since the file is advisory (not in REQUIRED_FILES).
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(result.ok,
                        msg=f"validation must not require advisory helper_recommendations: "
                            f"{result.missing} {result.hash_mismatches}")

    # --- Registry-derivation / de-duplication --------------------------------

    def test_recommended_helper_ids_exist_in_registry(self):
        rec = sp.build_helper_recommendations()
        registry = hr.build_registry()
        for entry in rec["recommended_helpers"]:
            self.assertIsNotNone(
                hr.get_helper(registry, entry["helper_id"]),
                msg=f"recommended helper {entry['helper_id']} is not in the registry",
            )

    def test_speckit_facts_are_derived_from_registry(self):
        # status and authority_levels must match the registry exactly (not an
        # independently maintained copy).
        rec = sp.build_helper_recommendations()
        speckit_rec = next(h for h in rec["recommended_helpers"] if h["helper_id"] == "speckit")
        speckit_reg = hr.get_helper(hr.build_registry(), "speckit")
        self.assertEqual(speckit_reg["status"], speckit_rec["status"])
        self.assertEqual(list(speckit_reg["authority_levels"]), speckit_rec["authority_levels"])

    def test_recommendations_reflect_registry_authority_not_hardcoded(self):
        # Falsifiable de-dup test: if the builder hardcoded speckit authority levels
        # instead of deriving from the registry, this would fail.
        registry = hr.build_registry()
        hr.get_helper(registry, "speckit")["authority_levels"] = ["GUIDE_ONLY"]
        rec = sp.build_helper_recommendations(registry=registry)
        speckit_rec = next(h for h in rec["recommended_helpers"] if h["helper_id"] == "speckit")
        self.assertEqual(["GUIDE_ONLY"], speckit_rec["authority_levels"])

    def test_recommendations_reflect_registry_status_not_hardcoded(self):
        # If status were hardcoded, demoting speckit in the registry would not drop
        # it from the implemented/recommended set. Derivation makes it drop.
        registry = hr.build_registry()
        hr.get_helper(registry, "speckit")["status"] = "experimental"
        rec = sp.build_helper_recommendations(registry=registry)
        ids = [h["helper_id"] for h in rec["recommended_helpers"]]
        self.assertNotIn("speckit", ids)
        self.assertIsNone(rec["default_helper"])

    def test_default_helper_derived_from_registry(self):
        self.assertEqual(
            hr.default_helper_id(hr.build_registry()),
            sp.build_helper_recommendations()["default_helper"],
        )

    def test_unsupported_helpers_come_from_registry_planned_ids(self):
        rec = sp.build_helper_recommendations()
        ids = [h["helper_id"] for h in rec["unsupported_helpers"]]
        self.assertEqual(list(hr.PLANNED_HELPER_IDS), ids)

    def test_unsupported_helper_not_in_implemented_set(self):
        # A not-implemented helper must never also appear as an implemented/operational one.
        rec = sp.build_helper_recommendations()
        implemented_ids = {h["helper_id"] for h in hr.implemented_helpers(hr.build_registry())}
        for entry in rec["unsupported_helpers"]:
            self.assertNotIn(entry["helper_id"], implemented_ids)

    def test_no_selected_helper_in_recommendations(self):
        rec = sp.build_helper_recommendations()
        self.assertNotIn("selected_helper", rec)
        self.assertNotIn("helper_selection", rec)

    def test_registry_provenance_present(self):
        rec = sp.build_helper_recommendations()
        prov = rec.get("registry_provenance")
        self.assertIsNotNone(prov)
        self.assertEqual(hr.SCHEMA_VERSION, prov["schema_version"])
        self.assertEqual(hr.registry_sha256(), prov["registry_sha256"])

    def test_recommendations_deterministic(self):
        self.assertEqual(sp.build_helper_recommendations(), sp.build_helper_recommendations())

    def test_runtime_manifest_has_no_selected_helper(self):
        # Runtime MANIFEST is provenance only; selection must never live there.
        from hldspec import runtime_vendor
        manifest = runtime_vendor.build_manifest({})
        self.assertNotIn("selected_helper", manifest)
        self.assertNotIn("helper_selection", manifest)
        self.assertEqual(
            {"runtime_version", "generated_by", "source_commit", "helper_id", "toolchain", "files"},
            set(manifest.keys()),
        )


def _selected_backlog(**overrides) -> dict:
    """A valid spec backlog with one SELECTED active spec."""
    base = {
        "schema_version": 1,
        "created_at": "2026-07-01T00:00:00Z",
        "updated_at": "2026-07-01T00:00:00Z",
        "source_refs": ["docs/hld.md"],
        "active_spec_id": "SPEC-001",
        "specs": [
            {
                "spec_id": "SPEC-001",
                "title": "Auth Module",
                "hld_anchor_ids": ["HLD-001"],
                "capability": "Authentication",
                "status": "SELECTED",
                "size_class": "BOUNDED_DELIVERABLE",
                "dependencies": [],
                "validation_strategy": ["integration_tests"],
                "target_materialization": "NOT_MATERIALIZED",
                "source_refs": ["docs/hld.md"],
            },
            {
                "spec_id": "SPEC-002",
                "title": "Logging Module",
                "hld_anchor_ids": ["HLD-002"],
                "capability": "Observability",
                "status": "PLANNED",
                "size_class": "BOUNDED_DELIVERABLE",
                "dependencies": [],
                "validation_strategy": ["unit_tests"],
                "target_materialization": "NOT_MATERIALIZED",
            },
        ],
    }
    base.update(overrides)
    return base


_MULTI_ANCHOR_HLD = (
    "# HLD\n\n"
    "## HLD-001 - Auth\n\nHLD-ID: HLD-001\n\nAuth module.\n\n"
    "## HLD-002 - Logging\n\nHLD-ID: HLD-002\n\nLogging module.\n"
)


class ActiveSpecSourcePackageDefaultCompatibilityTests(unittest.TestCase):
    """Default (no active_spec_backlog) must be fully behavior-compatible."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_build_emits_full_hld_coverage_scope(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(scope["coverage_scope"], "FULL_HLD")
        self.assertIsNone(scope["active_spec_id"])

    def test_default_build_single_spec_input_is_full_hld(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        text = (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).read_text(encoding="utf-8")
        self.assertNotIn("# Active Spec Input", text)

    def test_default_build_does_not_require_active_spec_backlog(self):
        build = sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

    def test_default_build_preserves_bare_list_ledger(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        self.assertIsInstance(ledger, list)
        cov.validate_coverage_ledger(ledger)


class ActiveSpecSourcePackageModeTests(unittest.TestCase):
    """Explicit ACTIVE_SPEC mode via active_spec_backlog parameter."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_active_spec_single_spec_input_starts_with_header(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        text = (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).read_text(encoding="utf-8")
        self.assertTrue(text.startswith("# Active Spec Input"))

    def test_active_spec_input_includes_selected_spec_details(self):
        backlog = _selected_backlog()
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=backlog,
        )
        text = (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).read_text(encoding="utf-8")
        self.assertIn("SPEC-001", text)
        self.assertIn("Auth Module", text)
        self.assertIn("HLD-001", text)

    def test_active_spec_input_excludes_non_selected_specs(self):
        backlog = _selected_backlog()
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=backlog,
        )
        text = (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).read_text(encoding="utf-8")
        self.assertNotIn("SPEC-002", text)
        self.assertNotIn("Logging Module", text)

    def test_active_spec_coverage_scope_is_active_spec(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(scope["coverage_scope"], "ACTIVE_SPEC")

    def test_active_spec_coverage_scope_has_matching_spec_id(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(scope["active_spec_id"], "SPEC-001")

    def test_active_spec_selected_anchors_match_spec(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(scope["selected_hld_anchor_ids"], ["HLD-001"])

    def test_active_spec_coverage_scope_validates(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        result = hcs.validate_hld_coverage_scope(scope)
        self.assertTrue(result.ok, result.errors)

    def test_active_spec_ledger_remains_bare_list(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        self.assertIsInstance(ledger, list)
        cov.validate_coverage_ledger(ledger)

    def test_active_spec_ledger_evaluates_written_input(self):
        """Ledger must be built from active-spec input, not full-HLD input."""
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        text = (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).read_text(encoding="utf-8")
        self.assertIn("(HLD-001)", text)
        self.assertNotIn("(HLD-002)", text)

        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        self.assertIsInstance(ledger, list)

        hld001_row = next((item for item in ledger if item["hld_item_id"] == "HLD-001"), None)
        hld002_row = next((item for item in ledger if item["hld_item_id"] == "HLD-002"), None)
        self.assertIsNotNone(hld001_row)
        self.assertIsNotNone(hld002_row)
        self.assertEqual(hld001_row["status"], "COVERED_IN_SDD")
        self.assertEqual(hld002_row["status"], "NOT_COVERED")

    def test_active_spec_interpretation_classifies_non_selected_as_out_of_scope(self):
        """NOT_COVERED anchors outside selected scope must appear in out_of_scope_items."""
        import json
        from hldspec.hld_coverage_scope_interpretation import interpret_coverage_ledger_for_scope

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )

        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger,
            coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.blocking_items, [])
        hld002_out = [item for item in result.out_of_scope_items if item["hld_item_id"] == "HLD-002"]
        self.assertEqual(len(hld002_out), 1)

    def test_active_spec_mirrored_single_spec_input_is_active(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        mirrored = (self.mirror_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).read_text(encoding="utf-8")
        self.assertIn("# Active Spec Input", mirrored)

    def test_active_spec_sidecar_not_mirrored(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        self.assertFalse(
            (self.mirror_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).exists(),
        )

    def test_no_new_gate_blockers(self):
        ctx = gv.GateContext(
            receipt_present=False,
            source_refs=[],
            runskeptic_status=gv.RUNSKEPTIC_NOT_RUN,
            consultant_status=gv.CONSULTANT_NOT_RUN,
            validation_ok=False,
            human_approved=False,
        )
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(any("active_spec" in b.lower() for b in result.blockers))


class ActiveSpecSourcePackageInvalidInputTests(unittest.TestCase):
    """Invalid explicit ACTIVE_SPEC input must fail fast, never fall back."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_invalid_backlog_raises(self):
        with self.assertRaises(ValueError) as cm:
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog={"bad": "data"},
            )
        self.assertIn("invalid", str(cm.exception).lower())

    def test_missing_active_spec_id_raises(self):
        backlog = _selected_backlog(active_spec_id=None)
        backlog["specs"][0]["status"] = "PLANNED"
        with self.assertRaises(ValueError) as cm:
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=backlog,
            )
        self.assertIn("active_spec_id", str(cm.exception))

    def test_active_spec_not_found_raises(self):
        backlog = _selected_backlog(active_spec_id="SPEC-999")
        with self.assertRaises(ValueError):
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=backlog,
            )

    def test_active_spec_not_selected_raises(self):
        backlog = _selected_backlog()
        backlog["specs"][0]["status"] = "PLANNED"
        with self.assertRaises(ValueError):
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=backlog,
            )

    def test_materialized_spec_raises(self):
        backlog = _selected_backlog()
        backlog["specs"][0]["target_materialization"] = "SUPERSEDED_IN_TARGET"
        with self.assertRaises(ValueError) as cm:
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=backlog,
            )
        self.assertIn("materialized", str(cm.exception).lower())

    def test_no_silent_fallback_to_full_hld(self):
        """Invalid active_spec_backlog must raise, never silently produce FULL_HLD."""
        with self.assertRaises(ValueError):
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog={"not": "valid"},
            )
        scope_path = (
            TargetWorkspaceAdapter(target_root=self.root, layout="new").source_package_dir
            / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        )
        self.assertFalse(scope_path.exists(), "must not write scope on invalid input")


class ActiveSpecSourcePackageScopeTests(unittest.TestCase):
    """Ensure no mutation, no auto-selection, no target/gate/driver leakage."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_input_backlog_not_mutated(self):
        import copy

        backlog = _selected_backlog()
        frozen = copy.deepcopy(backlog)
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=backlog,
        )
        self.assertEqual(frozen, backlog)

    def test_select_active_spec_not_called(self):
        with patch("hldspec.spec_backlog.select_active_spec") as mock_select:
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=_selected_backlog(),
            )
            mock_select.assert_not_called()

    def test_no_unexpected_write_locations_vs_default(self):
        """Active-spec mode adds only the receipt file vs default."""
        import tempfile

        default_tmp = tempfile.TemporaryDirectory()
        default_root = Path(default_tmp.name)
        try:
            sp.build_source_package_content(
                default_root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
            )
            default_paths = sorted(
                p.relative_to(default_root) for p in default_root.rglob("*") if p.is_file()
            )
        finally:
            default_tmp.cleanup()

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        active_paths = sorted(
            p.relative_to(self.root) for p in self.root.rglob("*") if p.is_file()
        )
        receipt_rel = Path(".hldspec/source_package") / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertEqual(sorted(default_paths + [receipt_rel]), active_paths)


class ActiveSpecReceiptEmissionTests(unittest.TestCase):
    """Receipt is emitted in ACTIVE_SPEC mode with correct schema."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir

    def tearDown(self):
        self._tmp.cleanup()

    def _build_active(self, **overrides):
        import json
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(**overrides),
        )
        path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        return json.loads(path.read_text(encoding="utf-8"))

    def test_receipt_emitted_in_active_spec_mode(self):
        self._build_active()
        path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertTrue(path.is_file())

    def test_receipt_schema_version(self):
        receipt = self._build_active()
        self.assertEqual(receipt["schema_version"], 1)

    def test_receipt_type(self):
        receipt = self._build_active()
        self.assertEqual(receipt["receipt_type"], "ACTIVE_SPEC_SOURCE_PACKAGE_RENDER")

    def test_receipt_active_spec_id_matches(self):
        receipt = self._build_active()
        self.assertEqual(receipt["active_spec_id"], "SPEC-001")

    def test_receipt_title_matches(self):
        receipt = self._build_active()
        self.assertEqual(receipt["active_spec_title"], "Auth Module")

    def test_receipt_coverage_scope(self):
        receipt = self._build_active()
        self.assertEqual(receipt["coverage_scope"], "ACTIVE_SPEC")

    def test_receipt_selected_hld_anchor_ids(self):
        receipt = self._build_active()
        self.assertEqual(receipt["selected_hld_anchor_ids"], ["HLD-001"])

    def test_receipt_target_materialization(self):
        receipt = self._build_active()
        self.assertEqual(receipt["target_materialization"], "NOT_MATERIALIZED")

    def test_receipt_rendered_file(self):
        receipt = self._build_active()
        self.assertEqual(receipt["rendered_file"], "speckit_single_spec_input.md")

    def test_receipt_coverage_scope_file(self):
        receipt = self._build_active()
        self.assertEqual(receipt["coverage_scope_file"], "hld_coverage_scope.json")

    def test_receipt_coverage_ledger_file(self):
        receipt = self._build_active()
        self.assertEqual(receipt["coverage_ledger_file"], "hld_coverage_ledger.json")

    def test_receipt_source_refs(self):
        receipt = self._build_active()
        self.assertEqual(receipt["source_refs"], ["src.md"])

    def test_receipt_created_at_present(self):
        receipt = self._build_active()
        self.assertIsInstance(receipt["created_at"], str)
        self.assertTrue(len(receipt["created_at"]) > 0)

    def test_receipt_notes_no_target_no_backlog(self):
        receipt = self._build_active()
        notes_text = " ".join(receipt["notes"]).lower()
        self.assertIn("does not mark target materialization", notes_text)
        self.assertIn("does not", notes_text)
        self.assertIn("backlog", notes_text)


class ActiveSpecReceiptDefaultModeTests(unittest.TestCase):
    """Default FULL_HLD mode must NOT emit receipt."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_mode_no_receipt(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertFalse(path.exists())

    def test_default_source_package_still_validates(self):
        build = sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        self.assertTrue(build.ok, msg=f"{build.validation.missing} {build.validation.hash_mismatches}")

    def test_default_mirror_behavior_unchanged(self):
        build = sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        self.assertIn(sp.AUTHORITATIVE_FILES["hld"], build.mirrored)
        receipt_mirror = self.mirror_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertFalse(receipt_mirror.exists())


class ActiveSpecReceiptScopeTests(unittest.TestCase):
    """Receipt scope: not mirrored, not required, no gate/backlog/selection leakage."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir
        self.mirror_dir = self.adapter.specify_source_mirror_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_receipt_not_mirrored(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        mirror_receipt = self.mirror_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertFalse(mirror_receipt.exists())

    def test_receipt_not_in_required_files(self):
        self.assertNotIn(
            sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"],
            sp.REQUIRED_FILES,
        )

    def test_invalid_backlog_does_not_emit_receipt(self):
        with self.assertRaises(ValueError):
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog={"bad": "data"},
            )
        path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertFalse(path.exists())

    def test_input_backlog_not_mutated_with_receipt(self):
        import copy

        backlog = _selected_backlog()
        frozen = copy.deepcopy(backlog)
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=backlog,
        )
        self.assertEqual(frozen, backlog)

    def test_select_active_spec_not_called_with_receipt(self):
        with patch("hldspec.spec_backlog.select_active_spec") as mock_select:
            sp.build_source_package_content(
                self.root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=_selected_backlog(),
            )
            mock_select.assert_not_called()

    def test_active_spec_still_emits_active_spec_coverage_scope(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(scope["coverage_scope"], "ACTIVE_SPEC")

    def test_active_spec_ledger_still_evaluates_written_input(self):
        import json

        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        by_id = {item["hld_item_id"]: item for item in ledger}
        self.assertEqual(by_id["HLD-001"]["status"], "COVERED_IN_SDD")
        self.assertEqual(by_id["HLD-002"]["status"], "NOT_COVERED")

    def test_no_new_gate_blockers_from_receipt(self):
        ctx = gv.GateContext(
            receipt_present=False,
            source_refs=[],
            runskeptic_status=gv.RUNSKEPTIC_NOT_RUN,
            consultant_status=gv.CONSULTANT_NOT_RUN,
            validation_ok=False,
            human_approved=False,
        )
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(any("materialization_receipt" in b.lower() for b in result.blockers))

    def test_receipt_in_authoritative_not_in_mirror_files(self):
        self.assertIn("active_spec_materialization_receipt", sp.AUTHORITATIVE_FILES)
        self.assertNotIn(
            sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"],
            sp.MIRROR_FILES,
        )


class ActiveSpecReceiptValidationCompatibilityTests(unittest.TestCase):
    """Default / FULL_HLD packages validate OK without receipt — no regression."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir

    def tearDown(self):
        self._tmp.cleanup()

    def test_default_full_hld_no_receipt_no_semantic_errors(self):
        build = sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        self.assertTrue(build.ok)
        self.assertEqual(build.validation.semantic_errors, [])

    def test_seeded_package_no_scope_no_receipt_no_semantic_errors(self):
        _seed_min_package(self.source_dir)
        sp.write_source_package(self.source_dir, hld_source_ref="/src/HLD.md", state="x")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(result.ok)
        self.assertEqual(result.semantic_errors, [])

    def test_default_build_does_not_emit_receipt(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        receipt_path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        self.assertFalse(receipt_path.exists())

    def test_default_mirror_unchanged(self):
        build = sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
        )
        self.assertIn(sp.AUTHORITATIVE_FILES["hld"], build.mirrored)


class ActiveSpecReceiptValidationPositiveTests(unittest.TestCase):
    """ACTIVE_SPEC packages must validate receipt successfully."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir

    def tearDown(self):
        self._tmp.cleanup()

    def _build_active(self):
        return sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )

    def test_valid_active_spec_ok_no_semantic_errors(self):
        build = self._build_active()
        self.assertTrue(build.ok)
        self.assertEqual(build.validation.semantic_errors, [])

    def test_receipt_manifest_entry_present_with_sha256(self):
        import json

        self._build_active()
        manifest = json.loads(
            (self.source_dir / sp.SOURCE_MANIFEST_FILE).read_text(encoding="utf-8")
        )
        entry = manifest["files"].get("active_spec_materialization_receipt")
        self.assertIsNotNone(entry)
        self.assertTrue(entry["present"])
        self.assertIsNotNone(entry["sha256"])

    def test_receipt_scope_active_spec_id_match(self):
        import json

        self._build_active()
        receipt = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).read_text(encoding="utf-8")
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["active_spec_id"], scope["active_spec_id"])

    def test_receipt_scope_selected_anchors_match(self):
        import json

        self._build_active()
        receipt = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).read_text(encoding="utf-8")
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        self.assertEqual(receipt["selected_hld_anchor_ids"], scope["selected_hld_anchor_ids"])

    def test_receipt_file_refs_exist(self):
        import json

        self._build_active()
        receipt = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).read_text(encoding="utf-8")
        )
        self.assertTrue((self.source_dir / receipt["rendered_file"]).is_file())
        self.assertTrue((self.source_dir / receipt["coverage_scope_file"]).is_file())
        self.assertTrue((self.source_dir / receipt["coverage_ledger_file"]).is_file())

    def test_selected_anchors_covered_via_interpretation(self):
        import json
        from hldspec.hld_coverage_scope_interpretation import interpret_coverage_ledger_for_scope

        self._build_active()
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        self.assertTrue(result.ok)
        self.assertEqual(result.blocking_items, [])

    def test_non_selected_not_covered_is_out_of_scope(self):
        import json
        from hldspec.hld_coverage_scope_interpretation import interpret_coverage_ledger_for_scope

        self._build_active()
        ledger = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]).read_text(encoding="utf-8")
        )
        scope = json.loads(
            (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).read_text(encoding="utf-8")
        )
        result = interpret_coverage_ledger_for_scope(
            coverage_ledger=ledger, coverage_scope=scope,
        )
        hld002_out = [i for i in result.out_of_scope_items if i["hld_item_id"] == "HLD-002"]
        self.assertEqual(len(hld002_out), 1)


class ActiveSpecReceiptValidationNegativeTests(unittest.TestCase):
    """Negative tests: deterministic semantic errors on bad receipt state."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.adapter = TargetWorkspaceAdapter(target_root=self.root, layout="new")
        self.source_dir = self.adapter.source_package_dir

    def tearDown(self):
        self._tmp.cleanup()

    def _build_active_then_validate(self):
        sp.build_source_package_content(
            self.root, _MULTI_ANCHOR_HLD,
            hld_source_ref="src.md", layout="new",
            active_spec_backlog=_selected_backlog(),
        )

    def _mutate_receipt(self, **overrides):
        """Mutate receipt fields then recompute manifest so hash stays valid."""
        import json

        receipt_path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt.update(overrides)
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)

    def _mutate_scope(self, **overrides):
        """Mutate scope fields then recompute manifest."""
        import json

        scope_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
        scope.update(overrides)
        scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)

    def test_active_spec_scope_but_receipt_missing(self):
        self._build_active_then_validate()
        (self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]).unlink()
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("requires" in e for e in result.semantic_errors))

    def test_receipt_present_but_scope_missing(self):
        self._build_active_then_validate()
        (self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]).unlink()
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("missing" in e.lower() for e in result.semantic_errors))

    def test_receipt_in_full_hld_mode(self):
        self._build_active_then_validate()
        self._mutate_scope(coverage_scope="FULL_HLD", active_spec_id=None)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("FULL_HLD" in e for e in result.semantic_errors))

    def test_wrong_receipt_type(self):
        self._build_active_then_validate()
        self._mutate_receipt(receipt_type="WRONG_TYPE")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("receipt_type" in e for e in result.semantic_errors))

    def test_wrong_schema_version(self):
        self._build_active_then_validate()
        self._mutate_receipt(schema_version=99)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("schema_version" in e for e in result.semantic_errors))

    def test_wrong_receipt_coverage_scope(self):
        self._build_active_then_validate()
        self._mutate_receipt(coverage_scope="FULL_HLD")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("coverage_scope" in e for e in result.semantic_errors))

    def test_receipt_spec_id_differs_from_scope(self):
        self._build_active_then_validate()
        self._mutate_receipt(active_spec_id="SPEC-WRONG")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("active_spec_id" in e and "differs" in e for e in result.semantic_errors))

    def test_receipt_anchors_differ_from_scope(self):
        self._build_active_then_validate()
        self._mutate_receipt(selected_hld_anchor_ids=["HLD-999"])
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("selected_hld_anchor_ids" in e for e in result.semantic_errors))

    def test_receipt_wrong_target_materialization(self):
        self._build_active_then_validate()
        self._mutate_receipt(target_materialization="SUPERSEDED_IN_TARGET")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("target_materialization" in e for e in result.semantic_errors))

    def test_receipt_rendered_file_ref_missing(self):
        self._build_active_then_validate()
        (self.source_dir / sp.AUTHORITATIVE_FILES["single_spec_input"]).unlink()
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("rendered_file" in e and "missing" in e for e in result.semantic_errors))

    def test_receipt_rendered_file_ref_wrong(self):
        self._build_active_then_validate()
        self._mutate_receipt(rendered_file="HLD.md")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("rendered_file" in e for e in result.semantic_errors))

    def test_receipt_coverage_scope_file_ref_wrong(self):
        self._build_active_then_validate()
        self._mutate_receipt(coverage_scope_file="HLD.md")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("coverage_scope_file" in e for e in result.semantic_errors))

    def test_receipt_coverage_ledger_file_ref_wrong(self):
        self._build_active_then_validate()
        self._mutate_receipt(coverage_ledger_file="HLD.md")
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("coverage_ledger_file" in e for e in result.semantic_errors))

    def test_selected_anchor_not_covered_in_ledger(self):
        """A selected anchor that is NOT_COVERED must produce a semantic error."""
        import json

        self._build_active_then_validate()
        ledger_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]
        ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        for item in ledger:
            if item["hld_item_id"] == "HLD-001":
                item["status"] = "NOT_COVERED"
                item["sdd_section"] = None
        ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("not covered" in e.lower() for e in result.semantic_errors))

    def test_receipt_tampering_causes_hash_mismatch(self):
        """Mutating receipt after manifest → existing hash validation catches it."""
        import json

        self._build_active_then_validate()
        receipt_path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        receipt["active_spec_id"] = "TAMPERED"
        receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        result = sp.validate_source_package(self.source_dir)
        self.assertIn(
            sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"],
            result.hash_mismatches,
        )

    def test_malformed_receipt_json(self):
        self._build_active_then_validate()
        receipt_path = self.source_dir / sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"]
        receipt_path.write_text("not json{{{", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("malformed" in e.lower() for e in result.semantic_errors))

    def test_malformed_scope_json(self):
        self._build_active_then_validate()
        scope_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        scope_path.write_text("{bad json", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("malformed" in e.lower() for e in result.semantic_errors))

    def test_invalid_coverage_scope_mode(self):
        import json

        self._build_active_then_validate()
        scope_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
        scope["coverage_scope"] = "ACTIVE_SPCE"
        scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("FULL_HLD or ACTIVE_SPEC" in e for e in result.semantic_errors))

    def test_receipt_present_with_invalid_scope_mode(self):
        import json

        self._build_active_then_validate()
        scope_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_scope"]
        scope = json.loads(scope_path.read_text(encoding="utf-8"))
        scope["coverage_scope"] = "INVALID"
        scope_path.write_text(json.dumps(scope, indent=2) + "\n", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("coverage_scope" in e for e in result.semantic_errors))

    def test_malformed_ledger_json_in_active_spec(self):
        self._build_active_then_validate()
        ledger_path = self.source_dir / sp.AUTHORITATIVE_FILES["hld_coverage_ledger"]
        ledger_path.write_text("not json{{{", encoding="utf-8")
        sp.write_source_manifest(self.source_dir)
        result = sp.validate_source_package(self.source_dir)
        self.assertTrue(any("ledger" in e.lower() and "malformed" in e.lower() for e in result.semantic_errors))


class ActiveSpecReceiptValidationScopeTests(unittest.TestCase):
    """Validation scope: no gate/driver/readiness, no backlog mutation."""

    def test_receipt_not_in_required_files(self):
        self.assertNotIn(
            sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"],
            sp.REQUIRED_FILES,
        )

    def test_receipt_not_mirrored(self):
        self.assertNotIn(
            sp.AUTHORITATIVE_FILES["active_spec_materialization_receipt"],
            sp.MIRROR_FILES,
        )

    def test_no_new_gate_blockers(self):
        ctx = gv.GateContext(
            receipt_present=False,
            source_refs=[],
            runskeptic_status=gv.RUNSKEPTIC_NOT_RUN,
            consultant_status=gv.CONSULTANT_NOT_RUN,
            validation_ok=False,
            human_approved=False,
        )
        result = gv.validate_gate(gv.SOURCE_PACKAGE_APPROVAL_GATE, ctx)
        self.assertFalse(any("materialization_receipt" in b.lower() for b in result.blockers))

    def test_semantic_errors_not_in_ok(self):
        """semantic_errors must NOT affect .ok — prevents driver behavior change."""
        v = sp.SourcePackageValidation(semantic_errors=["some error"])
        self.assertTrue(v.ok)

    def test_input_backlog_not_mutated_after_validation(self):
        import copy
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        try:
            backlog = _selected_backlog()
            frozen = copy.deepcopy(backlog)
            sp.build_source_package_content(
                root, _MULTI_ANCHOR_HLD,
                hld_source_ref="src.md", layout="new",
                active_spec_backlog=backlog,
            )
            self.assertEqual(frozen, backlog)
        finally:
            tmp.cleanup()

    def test_select_active_spec_not_called_during_validation(self):
        import tempfile

        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        try:
            with patch("hldspec.spec_backlog.select_active_spec") as mock_select:
                sp.build_source_package_content(
                    root, _MULTI_ANCHOR_HLD,
                    hld_source_ref="src.md", layout="new",
                    active_spec_backlog=_selected_backlog(),
                )
                mock_select.assert_not_called()
        finally:
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
