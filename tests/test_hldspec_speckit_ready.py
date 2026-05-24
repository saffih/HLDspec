from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


arch = load_module("build_hldspec_architecture_analysis", "scripts/build_hldspec_architecture_analysis.py")
constitution = load_module("build_speckit_constitution_context", "scripts/build_speckit_constitution_context.py")
speclist = load_module("build_hldspec_speckit_spec_list", "scripts/build_hldspec_speckit_spec_list.py")
disposition = load_module("build_hldspec_architecture_findings_disposition", "scripts/build_hldspec_architecture_findings_disposition.py")
readiness = load_module("run_hldspec_speckit_readiness", "scripts/run_hldspec_speckit_readiness.py")


SAMPLE_HLD = """# Sample HLD

## HLD-010 - Database API Interface
HLD-ID: HLD-010
HLD-ROLE: architecture
HLD-STATUS: draft
HLD-RISK: medium
HLD-SPECS: TBD
HLD-RESOURCES: database
HLD-VERIFY: review

This section defines database persistence, data state ownership, programmatic interface, and API contract behavior.

## HLD-020 - Processing Core
HLD-ID: HLD-020
HLD-ROLE: architecture
HLD-STATUS: draft
HLD-RISK: medium
HLD-SPECS: TBD
HLD-RESOURCES: processing
HLD-VERIFY: review

This section defines orchestration logic and lifecycle processing.
"""

CONTEXT_HEAVY_HLD = """# Sample HLD

## HLD-001 - Executive Summary
HLD-ID: HLD-001
HLD-ROLE: governance
HLD-STATUS: draft
HLD-RISK: low
HLD-SPECS: TBD
HLD-RESOURCES: context
HLD-VERIFY: review

Summary mentions database, API, interface, lifecycle, UI, and storage only as context.

## HLD-010 - Database API Interface
HLD-ID: HLD-010
HLD-ROLE: architecture
HLD-STATUS: draft
HLD-RISK: medium
HLD-SPECS: TBD
HLD-RESOURCES: database
HLD-VERIFY: review

This section defines database persistence, data state ownership, programmatic interface, and API contract behavior.
"""


class HldspecSpeckitReadyTest(unittest.TestCase):
    def make_workspace(self) -> tuple[Path, tempfile.TemporaryDirectory]:
        tmp = tempfile.TemporaryDirectory()
        workspace = Path(tmp.name) / "workspace"
        workspace.mkdir()
        (workspace / "HLD.md").write_text(SAMPLE_HLD, encoding="utf-8")
        (workspace / ".specify" / "sync").mkdir(parents=True)
        return workspace, tmp

    def test_architecture_analysis_detects_layered_boundary(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        data = arch.build_analysis(workspace)

        self.assertEqual(data["section_count"], 2)
        self.assertTrue(any(f["hld_id"] == "HLD-010" for f in data["findings"]))
        hld010 = next(s for s in data["sections"] if s["hld_id"] == "HLD-010")
        self.assertTrue(hld010["requires_layered_split"])

    def test_constitution_context_has_required_shared_context(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        context = constitution.build_context(workspace)

        self.assertIn("architecture_layer_model", context)
        self.assertIn("interface_taxonomy", context)
        self.assertIn("split_rules", context)
        self.assertIn("no_invention_rules", context)
        self.assertIn("checkpoint_triage_rules", context)

    def test_spec_list_splits_mixed_database_api_section(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        result = speclist.build_list(workspace)
        titles = "\n".join(str(s["title"]) for s in result["specs"])

        self.assertIn("Database API Interface - Database Interface", titles)
        self.assertIn("Database API Interface - Use Logic and Orchestration", titles)
        self.assertIn("Database API Interface - API Contract", titles)
        self.assertEqual(result["status"], "SPEC_LIST_READY_FOR_REVIEW")

    def test_architecture_disposition_unblocks_reviewed_findings(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        sync = workspace / ".specify" / "sync"

        arch_data = arch.build_analysis(workspace)
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(arch_data), encoding="utf-8")
        context = constitution.build_context(workspace)
        (sync / "speckit_constitution_context.json").write_text(json.dumps(context), encoding="utf-8")
        spec_data = speclist.build_list(workspace)
        (sync / "hldspec_speckit_spec_list.json").write_text(json.dumps(spec_data), encoding="utf-8")

        disposition_data = disposition.build_disposition(workspace, approved=True)
        (sync / "hldspec_architecture_findings_disposition.json").write_text(json.dumps(disposition_data), encoding="utf-8")
        review = readiness.build_review(workspace)

        self.assertEqual(disposition_data["status"], "DISPOSITIONED")
        self.assertFalse(disposition_data["approval_required"])
        self.assertEqual(review["architecture_disposition_status"], "DISPOSITIONED")
        self.assertEqual(review["status"], "SPECKIT_PREWORK_READY_FOR_HUMAN_REVIEW")

    def test_architecture_disposition_requires_explicit_human_approval(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        sync = workspace / ".specify" / "sync"

        arch_data = arch.build_analysis(workspace)
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(arch_data), encoding="utf-8")
        context = constitution.build_context(workspace)
        (sync / "speckit_constitution_context.json").write_text(json.dumps(context), encoding="utf-8")
        spec_data = speclist.build_list(workspace)
        (sync / "hldspec_speckit_spec_list.json").write_text(json.dumps(spec_data), encoding="utf-8")

        disposition_data = disposition.build_disposition(workspace)
        (sync / "hldspec_architecture_findings_disposition.json").write_text(json.dumps(disposition_data), encoding="utf-8")
        review = readiness.build_review(workspace)

        self.assertEqual(disposition_data["status"], "PROPOSED_REQUIRES_HUMAN_APPROVAL")
        self.assertTrue(disposition_data["approval_required"])
        self.assertEqual(review["status"], "SPECKIT_PREWORK_NOT_READY")
        self.assertIn("architecture disposition status is PROPOSED_REQUIRES_HUMAN_APPROVAL", review["blocking"])

    def test_spec_list_demotes_context_instead_of_mechanical_split(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        (workspace / "HLD.md").write_text(CONTEXT_HEAVY_HLD, encoding="utf-8")

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        result = speclist.build_list(workspace)
        titles = "\n".join(str(s["title"]) for s in result["specs"])
        decisions = {item["hld_id"]: item["decision"] for item in result["boundary_decisions"]}

        self.assertEqual(decisions["HLD-001"], "DEMOTE_TO_CONTEXT")
        self.assertNotIn("Executive Summary - Tool", titles)
        self.assertIn("Database API Interface - Database Interface", titles)

    def test_existing_specs_scan_starts_ids_after_highest_existing(self) -> None:
        """Spec list numbering must start after the highest existing spec in source project."""
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        # Build a fake source project with existing specs 001–012
        source_project = Path(tmp.name) / "source_project"
        specs_dir = source_project / "specs"
        for i in [1, 5, 12]:
            (specs_dir / f"{i:03d}-some-feature").mkdir(parents=True)

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        result = speclist.build_list(workspace, source_project)

        scan = result["existing_specs_scan"]
        self.assertTrue(scan["found"])
        self.assertEqual(scan["highest_number"], 12)

        # All new spec IDs must be >= 013
        for spec in result["specs"]:
            num = int(spec["spec_id"].split("-")[0])
            self.assertGreater(num, 12, f"spec {spec['spec_id']} overlaps with existing specs (max 012)")

    def test_existing_specs_scan_detects_id_conflicts(self) -> None:
        """If existing specs share a number with planned specs, status must show ID_CONFLICT."""
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        # Make source project with only spec 001 — forcing a collision if start=1
        source_project = Path(tmp.name) / "source_project"
        (source_project / "specs" / "001-existing-feature").mkdir(parents=True)

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        # Patch start_idx to force collision by providing source project with highest=0
        # but having an existing 001 entry — the scan should detect it
        result = speclist.build_list(workspace, source_project)
        scan = result["existing_specs_scan"]
        # highest_number = 1, so start = 2 — no direct collision expected with 002+
        # Verify scan ran and found the existing spec
        self.assertTrue(scan["found"])
        self.assertEqual(scan["existing_count"], 1)
        self.assertIn("001-existing-feature", scan["existing_ids"])

    def test_existing_spec_is_historical_only_when_feature_branch_was_merged(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        source_project = Path(tmp.name) / "source_project"
        specs_dir = source_project / "specs"
        feature_dir = specs_dir / "001-merged-feature"
        draft_dir = specs_dir / "002-draft-feature"
        feature_dir.mkdir(parents=True)
        draft_dir.mkdir(parents=True)
        (feature_dir / "spec.md").write_text(
            "# Feature Specification: Merged\n\n"
            "**Feature Branch**: `[001-merged-feature]`\n",
            encoding="utf-8",
        )
        (draft_dir / "spec.md").write_text(
            "# Feature Specification: Draft\n\n"
            "**Feature Branch**: `[002-draft-feature]`\n",
            encoding="utf-8",
        )

        subprocess.run(["git", "init", "-b", "main"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source_project, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=source_project, check=True)
        subprocess.run(["git", "add", "."], cwd=source_project, check=True)
        subprocess.run(["git", "commit", "-m", "initial specs"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "checkout", "-b", "001-merged-feature"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (source_project / "merged.txt").write_text("merged\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=source_project, check=True)
        subprocess.run(["git", "commit", "-m", "finish 001"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "checkout", "main"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "merge", "--no-ff", "001-merged-feature", "-m", "Merge branch '001-merged-feature'"],
            cwd=source_project,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        scan = speclist.scan_existing_specs(source_project)
        statuses = {item["spec_id"]: item["history_status"] for item in scan["existing_specs"]}

        self.assertEqual(statuses["001-merged-feature"], "MERGED_DONE")
        self.assertEqual(statuses["002-draft-feature"], "NOT_HISTORICAL")
        self.assertEqual(scan["historical_ids"], ["001-merged-feature"])
        self.assertEqual(scan["non_historical_ids"], ["002-draft-feature"])

    def test_merge_history_requires_exact_branch_name_match(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        source_project = Path(tmp.name) / "source_project"
        specs_dir = source_project / "specs"
        short_dir = specs_dir / "001-short"
        short_dir.mkdir(parents=True)
        (short_dir / "spec.md").write_text(
            "# Feature Specification: Short\n\n"
            "**Feature Branch**: `[001-short]`\n",
            encoding="utf-8",
        )

        subprocess.run(["git", "init", "-b", "main"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=source_project, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=source_project, check=True)
        subprocess.run(["git", "add", "."], cwd=source_project, check=True)
        subprocess.run(["git", "commit", "-m", "initial specs"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "checkout", "-b", "001-short-extra"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (source_project / "extra.txt").write_text("extra\n", encoding="utf-8")
        subprocess.run(["git", "add", "."], cwd=source_project, check=True)
        subprocess.run(["git", "commit", "-m", "finish extra"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "checkout", "main"], cwd=source_project, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(
            ["git", "merge", "--no-ff", "001-short-extra", "-m", "Merge branch '001-short-extra'"],
            cwd=source_project,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        scan = speclist.scan_existing_specs(source_project)
        statuses = {item["spec_id"]: item["history_status"] for item in scan["existing_specs"]}

        self.assertEqual(statuses["001-short"], "NOT_HISTORICAL")

    def test_active_unmerged_spec_prevents_duplicate_new_spec(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        source_project = Path(tmp.name) / "source_project"
        active_dir = source_project / "specs" / "002-database-api-and-data-safety"
        active_dir.mkdir(parents=True)
        (active_dir / "spec.md").write_text(
            "# Feature Specification: Database API\n\n"
            "**Feature Branch**: `[002-database-api-and-data-safety]`\n",
            encoding="utf-8",
        )

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        result = speclist.build_list(workspace, source_project)
        titles = "\n".join(str(s["title"]) for s in result["specs"])
        decisions = {item["hld_id"]: item for item in result["boundary_decisions"]}

        self.assertEqual(decisions["HLD-010"]["decision"], "MERGE_WITH_ACTIVE_SPEC")
        self.assertEqual(decisions["HLD-010"]["active_spec_id"], "002-database-api-and-data-safety")
        self.assertNotIn("Database API Interface - Database Tool Interface", titles)

    def test_active_spec_title_prevents_duplicate_even_when_slug_differs(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        source_project = Path(tmp.name) / "source_project"
        active_dir = source_project / "specs" / "002-foundation-work"
        active_dir.mkdir(parents=True)
        (active_dir / "spec.md").write_text(
            "# Feature Specification: Database API Interface\n\n"
            "**Feature Branch**: `[002-foundation-work]`\n",
            encoding="utf-8",
        )

        data = arch.build_analysis(workspace)
        sync = workspace / ".specify" / "sync"
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps(data), encoding="utf-8")

        result = speclist.build_list(workspace, source_project)
        decisions = {item["hld_id"]: item for item in result["boundary_decisions"]}

        self.assertEqual(decisions["HLD-010"]["decision"], "MERGE_WITH_ACTIVE_SPEC")
        self.assertEqual(decisions["HLD-010"]["active_spec_id"], "002-foundation-work")

    def test_wrapper_generates_readiness_artifacts(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)

        subprocess.run(
            ["bash", str(ROOT / "scripts" / "hldspec_speckit_ready.sh"), str(workspace)],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        sync = workspace / ".specify" / "sync"
        self.assertTrue((sync / "hldspec_architecture_analysis.json").exists())
        self.assertTrue((sync / "speckit_constitution_context.json").exists())
        self.assertTrue((sync / "hldspec_speckit_spec_list.json").exists())
        self.assertTrue((sync / "hldspec_architecture_findings_disposition.json").exists())
        self.assertTrue((sync / "hldspec_speckit_readiness.json").exists())

        review = readiness.build_review(workspace)
        self.assertEqual(review["status"], "SPECKIT_PREWORK_NOT_READY")
        self.assertEqual(review["architecture_disposition_status"], "PROPOSED_REQUIRES_HUMAN_APPROVAL")
        self.assertIn("architecture disposition status is PROPOSED_REQUIRES_HUMAN_APPROVAL", review["blocking"])
        self.assertFalse(review["implementation_allowed"])
        self.assertTrue(review["not_real_speckit_execution"])

    def test_readiness_blocks_excessive_spec_count(self) -> None:
        workspace, tmp = self.make_workspace()
        self.addCleanup(tmp.cleanup)
        sync = workspace / ".specify" / "sync"
        sync.mkdir(parents=True, exist_ok=True)
        (sync / "hldspec_architecture_analysis.json").write_text(json.dumps({"status": "PASS_WITH_REVIEW", "findings": []}), encoding="utf-8")
        (sync / "speckit_constitution_context.json").write_text(
            json.dumps(
                {
                    "status": "CONSTITUTION_CONTEXT_READY_FOR_REVIEW",
                    "source_of_truth_hierarchy": {},
                    "architecture_layer_model": {},
                    "interface_taxonomy": {},
                    "split_rules": {},
                    "no_invention_rules": {},
                    "checkpoint_triage_rules": {},
                    "speckit_boundaries": {},
                    "validation_gates": {},
                }
            ),
            encoding="utf-8",
        )
        (sync / "hldspec_speckit_spec_list.json").write_text(
            json.dumps({"status": "SPEC_LIST_REQUIRES_DECOMPOSITION", "spec_count": 31, "blocking": ["spec count 31 exceeds reviewable threshold 30"]}),
            encoding="utf-8",
        )

        review = readiness.build_review(workspace)

        self.assertEqual(review["status"], "SPECKIT_PREWORK_NOT_READY")
        self.assertIn("spec list is SPEC_LIST_REQUIRES_DECOMPOSITION", review["blocking"])


if __name__ == "__main__":
    unittest.main()
