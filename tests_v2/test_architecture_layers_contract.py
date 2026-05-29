"""Architecture layer-map and repo-migration contract.

Protects the canonical product/layer map (docs/ARCHITECTURE_LAYERS.md) and the
phased repository migration plan (docs/REPO_MIGRATION_PLAN.md) against drift.

These are architecture-intent contracts, not just file-existence checks:

* Positive: the layer map must state the product purpose, the three journeys,
  the implementation modes as a *separate axis*, the seven product layers, the
  Operator/Doctor/Mediator boundaries, generated-vs-source separation, and the
  current/intended/future honesty (SpecKit Preparation = core; HLD Authoring and
  Implementation Guidance qualified; production = NO).
* Negative/stale-behavior: fail if the map implies users normally run scripts,
  collapses journeys and modes, claims all journeys equally implemented, marks
  production-ready YES, calls V1/compatibility active V2 core, or calls target
  artifacts repo source.
* Migration plan: phased, no broad moves first, tests-before-move, top-level
  classification, rollback guidance.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
LAYERS = DOCS / "ARCHITECTURE_LAYERS.md"
MIGRATION = DOCS / "REPO_MIGRATION_PLAN.md"
DOCS_INDEX = DOCS / "DOCS_INDEX.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ArchitectureLayersExistenceTests(unittest.TestCase):
    def test_layers_doc_exists(self) -> None:
        self.assertTrue(LAYERS.is_file(), f"missing {LAYERS}")

    def test_migration_doc_exists(self) -> None:
        self.assertTrue(MIGRATION.is_file(), f"missing {MIGRATION}")

    def test_docs_index_links_both_new_docs(self) -> None:
        text = _read(DOCS_INDEX)
        self.assertIn("ARCHITECTURE_LAYERS.md", text)
        self.assertIn("REPO_MIGRATION_PLAN.md", text)


class ArchitectureLayersContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _read(LAYERS)
        self.lower = self.text.lower()

    # --- public UX vs tool surface ---------------------------------------

    def test_public_ux_is_agent_one_liner_first(self) -> None:
        self.assertIn("agent one-liner first", self.lower)
        # The actual copy-ready instruction is present, not just the phrase.
        self.assertIn("Use HLDspec with source HLD:", self.text)

    def test_scripts_are_internal_tool_surface_not_human_ux(self) -> None:
        self.assertIn("internal/manual/debug/fallback", self.lower)
        self.assertIn("not the normal human ux", self.lower)

    # --- journeys ---------------------------------------------------------

    def test_defines_three_journeys(self) -> None:
        for journey in ("HLD Authoring", "SpecKit Preparation", "Implementation Guidance"):
            with self.subTest(journey=journey):
                self.assertIn(journey, self.text)

    def test_distinguishes_journeys_from_modes(self) -> None:
        self.assertIn("different axes", self.lower)
        for mode in ("Manual", "Agent-assisted", "Mediator-assisted"):
            with self.subTest(mode=mode):
                self.assertIn(mode, self.text)

    def test_speckit_preparation_is_core(self) -> None:
        self.assertIn("SpecKit Preparation is the core product", self.text)

    def test_hld_authoring_is_precondition_helper_qualified(self) -> None:
        self.assertIn("HLD Authoring is a precondition/helper", self.text)
        self.assertIn("unless current evidence and tests prove deeper support", self.text)

    def test_implementation_guidance_is_extension_qualified(self) -> None:
        self.assertIn("Implementation Guidance is an extension", self.text)

    # --- product boundaries ----------------------------------------------

    def test_does_not_implement_or_replace(self) -> None:
        self.assertIn("HLDspec does not implement the product", self.text)
        self.assertIn("HLDspec does not replace SpecKit", self.text)

    def test_doctor_is_readiness_only_not_whole_operator(self) -> None:
        self.assertIn("readiness/preflight only", self.lower)
        self.assertIn("not the whole operator", self.lower)

    def test_mediator_boundaries(self) -> None:
        self.assertIn("Agent Mediator is not the Implementation Agent", self.text)
        self.assertIn("Devin Mediator is Devin-specific", self.text)

    # --- layer separation -------------------------------------------------

    def test_target_artifacts_are_not_repo_source(self) -> None:
        self.assertIn("are not repo source", self.lower)

    def test_v1_compatibility_is_not_active_v2_core(self) -> None:
        self.assertIn("not active v2 core", self.lower)

    def test_production_ready_remains_no(self) -> None:
        self.assertIn("Production-ready remains NO", self.text)

    # --- negative / stale-behavior ---------------------------------------

    def test_does_not_make_scripts_the_normal_user_path(self) -> None:
        self.assertNotIn("public facade is one script", self.text)
        self.assertNotIn("users normally run scripts", self.lower)
        self.assertNotIn("normally run scripts directly", self.lower)

    def test_does_not_collapse_journeys_and_modes(self) -> None:
        self.assertNotIn("journeys and modes are the same", self.lower)
        self.assertNotIn("journey and mode are the same", self.lower)

    def test_does_not_claim_all_journeys_equally_implemented(self) -> None:
        self.assertNotIn("all three journeys are fully implemented", self.lower)
        self.assertNotIn("all three journeys are equally implemented", self.lower)
        # A qualifier must be present.
        self.assertIn("not equally implemented", self.lower)

    def test_does_not_claim_production_ready(self) -> None:
        self.assertNotIn("Production-ready: YES", self.text)
        self.assertNotIn("production-ready remains yes", self.lower)

    def test_does_not_call_v1_active_v2_core(self) -> None:
        self.assertNotIn("v1 pipeline is active v2 core", self.lower)

    def test_does_not_call_target_artifacts_repo_source(self) -> None:
        self.assertNotIn("target artifacts are repo source", self.lower)


class RepoMigrationPlanContentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.text = _read(MIGRATION)
        self.lower = self.text.lower()

    def test_has_all_phases(self) -> None:
        for n in range(7):
            with self.subTest(phase=n):
                self.assertIn(f"Phase {n}", self.text)

    def test_no_broad_moves_in_first_phase(self) -> None:
        self.assertIn("no broad file moves", self.lower)

    def test_requires_tests_before_moving(self) -> None:
        self.assertIn("Tests required before", self.text)

    def test_classifies_top_level_files_and_dirs(self) -> None:
        # The plan must classify the real tracked top-level entries, not just
        # talk about migration in the abstract.
        for token in (
            "hldspec/",
            "scripts/",
            "hld_map.py",
            "hld_spec_sync.py",
            "hld_spec_downstream.py",
            "tests_v2/",
            "tests_legacy/",
            "templates/",
            "poc/",
            "Dev",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.text)

    def test_includes_rollback_guidance(self) -> None:
        self.assertIn("Rollback", self.text)
        self.assertIn("revert", self.lower)


if __name__ == "__main__":
    unittest.main()
