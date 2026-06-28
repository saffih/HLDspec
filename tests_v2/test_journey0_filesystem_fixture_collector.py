"""Tests for the controlled filesystem Journey 0 fixture collector."""
from __future__ import annotations

import tempfile
import unittest
from collections.abc import Mapping
from pathlib import Path

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_filesystem_fixture_collector as collector


def _put(root: Path, relative_name: str, text: str) -> None:
    fixture_file = root / relative_name
    fixture_file.parent.mkdir(parents=True, exist_ok=True)
    fixture_file.write_bytes(text.encode("utf-8"))


def _snapshot(root: Path) -> dict[str, bytes]:
    def visit(directory: Path, prefix: str = "") -> dict[str, bytes]:
        items: dict[str, bytes] = {}
        for child in sorted(directory.iterdir(), key=lambda p: p.name):
            relative_name = f"{prefix}{child.name}"
            if child.is_symlink():
                items[relative_name] = f"SYMLINK:{child.readlink()}".encode("utf-8")
            elif child.is_dir():
                items.update(visit(child, f"{relative_name}/"))
            else:
                items[relative_name] = child.read_bytes()
        return items

    return visit(root)


def _collect(root: Path):
    before = _snapshot(root)
    artifacts = collector.collect_filesystem_fixture_evidence(root)
    result = collector.evaluate_filesystem_fixture(root)
    after = _snapshot(root)
    return before, after, artifacts, result


class FilesystemFixtureCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_clean_fixture_reaches_ready_to_draft_hld(self) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: product intent marker\n")
        _put(self.tmp_path, "specs/workflow.md", "OBSERVED: workflow marker\n")
        _put(self.tmp_path, "src/app.py", "OBSERVED: implementation marker\n")

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertEqual(len(j0.accepted_facts(artifacts.evidence_pack)), 3)
        self.assertEqual(
            set(artifacts.files_read),
            {"README.md", "specs/workflow.md", "src/app.py"},
        )

    def test_product_decision_fixture_blocks_hld_draftability(self) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: product exists\n")
        _put(self.tmp_path, "hld.md", "PRODUCT_DECISION: source_of_truth_ownership\n")

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED)
        self.assertEqual(
            artifacts.product_decision_register[0]["id"],
            "source_of_truth_ownership",
        )

    def test_conflict_fixture_blocks_hld_draftability(self) -> None:
        _put(self.tmp_path, "hld.md", "OBSERVED: external controller owns run state\n")
        _put(
            self.tmp_path,
            "specs/state.md",
            "CONFLICT: local SQLite/session state owns lifecycle\n",
        )
        _put(self.tmp_path, "src/core.py", "REPO_STATE_CONFLICT: true\n")

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(result.verdict, j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT)
        self.assertTrue(artifacts.gap_report["repo_state_conflict"])
        self.assertTrue(
            any(
                item["label"] == j0.EVIDENCE_CONFLICT
                for item in artifacts.evidence_pack["evidence"]
            )
        )

    def test_insufficient_evidence_fixture_stays_insufficient(self) -> None:
        _put(self.tmp_path, "README.md", "UNKNOWN: product intent is missing\n")
        _put(
            self.tmp_path,
            "state.json",
            '{"evidence": [{"label": "INFERRED", "statement": "resume may exist"}]}',
        )

        before, after, _artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertEqual(result.accepted_fact_count, 0)

    def test_unknown_backed_requirement_is_not_ready(self) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: run records exist\n")
        _put(self.tmp_path, "hld.md", "REQUIREMENT_UNKNOWN: REQ-agent-can-resume\n")

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertNotEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertEqual(result.verdict, j0.VERDICT_INSUFFICIENT_EVIDENCE)
        self.assertEqual(
            artifacts.candidate_requirements[0]["evidence_label"],
            j0.EVIDENCE_UNKNOWN,
        )

    def test_safety_authority_fixture_blocks_and_grants_no_authority(self) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: blocked runs exist\n")
        _put(
            self.tmp_path,
            "state.json",
            '{"safety_authority_gaps": ["unclear agent approval authority"]}',
        )

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(
            result.verdict, j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
        )
        self.assertIn("unclear agent approval authority", result.blockers[0])
        self.assertFalse(result.grants_approval_authority)
        self.assertFalse(result.authorizes_implementation)
        self.assertFalse(result.authorizes_work_orders)
        self.assertFalse(artifacts.authority["grants_approval_authority"])
        self.assertFalse(artifacts.authority["authorizes_implementation"])
        self.assertFalse(artifacts.authority["authorizes_work_orders"])

    def test_read_only_proof_detects_no_content_or_file_set_changes(self) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: product intent marker\n")
        _put(self.tmp_path, "specs/workflow.md", "OBSERVED: workflow marker\n")
        _put(self.tmp_path, "src/app.py", "OBSERVED: implementation marker\n")

        before, after, _artifacts, result = _collect(self.tmp_path)

        self.assertEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertEqual(before, after)

    def test_narrow_scope_ignores_unrelated_files_without_broad_scanning(
        self,
    ) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: product intent marker\n")
        _put(self.tmp_path, "specs/workflow.md", "OBSERVED: workflow marker\n")
        _put(self.tmp_path, "src/app.py", "OBSERVED: implementation marker\n")
        _put(
            self.tmp_path,
            "notes/random.md",
            "CONFLICT: should not be collected\n",
        )
        _put(
            self.tmp_path,
            "deep/nested/file.py",
            "PRODUCT_DECISION: should_not_be_seen\n",
        )

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(result.verdict, j0.VERDICT_READY_TO_DRAFT_HLD)
        self.assertEqual(artifacts.ignored_files, ["deep", "notes"])
        self.assertNotIn("notes/random.md", artifacts.files_read)
        self.assertNotIn("deep/nested/file.py", artifacts.files_read)
        self.assertTrue(
            all(
                "should not be collected" not in item["statement"]
                for item in artifacts.evidence_pack["evidence"]
            )
        )

    def test_state_json_can_supply_full_artifact_inputs(self) -> None:
        _put(
            self.tmp_path,
            "state.json",
            """
            {
              "evidence": [{"label": "OBSERVED", "statement": "state JSON evidence"}],
              "open_questions": ["confirm copy"],
              "candidate_requirements": [
                {"id": "REQ-copy", "evidence_label": "OBSERVED", "statement": "copy exists"}
              ],
              "repo_state_conflict": false
            }
            """,
        )

        before, after, artifacts, result = _collect(self.tmp_path)

        self.assertEqual(before, after)
        self.assertEqual(result.verdict, j0.VERDICT_READY_WITH_OPEN_QUESTIONS)
        self.assertEqual(artifacts.candidate_requirements[0]["id"], "REQ-copy")
        self.assertEqual(artifacts.open_questions, ["confirm copy"])

    def test_invalid_state_json_fails_without_mutating_fixture(self) -> None:
        _put(self.tmp_path, "state.json", "{not json")
        before = _snapshot(self.tmp_path)

        with self.assertRaises(j0.InvalidJourney0ArtifactError):
            collector.collect_filesystem_fixture_evidence(self.tmp_path)

        self.assertEqual(before, _snapshot(self.tmp_path))

    def test_allowlisted_symlink_escape_is_rejected_without_mutation(self) -> None:
        outside = self.tmp_path.parent / f"{self.tmp_path.name}-outside.md"
        outside.write_bytes(b"OBSERVED: outside fixture content\n")
        (self.tmp_path / "README.md").symlink_to(outside)
        before = _snapshot(self.tmp_path)

        with self.assertRaises(j0.InvalidJourney0ArtifactError) as ctx:
            collector.collect_filesystem_fixture_evidence(self.tmp_path)
        self.assertIn("symlink", str(ctx.exception))

        self.assertEqual(before, _snapshot(self.tmp_path))

    def test_broken_allowlisted_symlink_is_rejected_without_mutation(self) -> None:
        (self.tmp_path / "README.md").symlink_to(self.tmp_path / "missing.md")
        before = _snapshot(self.tmp_path)

        with self.assertRaises(j0.InvalidJourney0ArtifactError) as ctx:
            collector.collect_filesystem_fixture_evidence(self.tmp_path)
        self.assertIn("symlink", str(ctx.exception))

        self.assertEqual(before, _snapshot(self.tmp_path))

    def test_artifact_payload_has_no_authority_grants(self) -> None:
        _put(self.tmp_path, "README.md", "OBSERVED: product intent marker\n")

        _before, _after, artifacts, result = _collect(self.tmp_path)
        payload: Mapping[str, object] = artifacts.to_dict()

        self.assertEqual(result.handoff_kind, j0.HANDOFF_EVIDENCE_AND_GAP_INPUT)
        self.assertTrue(result.journey1_input_only)
        self.assertFalse(payload["authority"]["grants_approval_authority"])
        self.assertFalse(payload["authority"]["authorizes_implementation"])
        self.assertFalse(payload["authority"]["authorizes_work_orders"])


if __name__ == "__main__":
    unittest.main()
