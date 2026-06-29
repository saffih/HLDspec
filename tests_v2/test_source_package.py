import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from hldspec import gate_validator as gv
from hldspec import hld_source_package as sp
from hldspec import helper_registry as hr
from hldspec import journey2_hld_coverage_contracts as cov
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

    def test_hld_coverage_ledger_does_not_change_gate_behavior(self):
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


if __name__ == "__main__":
    unittest.main()
