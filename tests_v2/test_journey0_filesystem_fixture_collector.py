"""Tests for the controlled filesystem Journey 0 fixture collector."""
from __future__ import annotations

from collections.abc import Mapping

from hldspec import journey0_artifact_contracts as j0
from hldspec import journey0_filesystem_fixture_collector as collector


def _put(root, relative_name: str, text: str) -> None:
    fixture_file = root / relative_name
    fixture_file.parent.mkdir(parents=True, exist_ok=True)
    fixture_file.write_bytes(text.encode("utf-8"))


def _snapshot(root) -> dict[str, bytes]:
    def visit(directory, prefix: str = "") -> dict[str, bytes]:
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


def _collect(root):
    before = _snapshot(root)
    artifacts = collector.collect_filesystem_fixture_evidence(root)
    result = collector.evaluate_filesystem_fixture(root)
    after = _snapshot(root)
    return before, after, artifacts, result


def test_clean_fixture_reaches_ready_to_draft_hld(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: product intent marker\n")
    _put(tmp_path, "specs/workflow.md", "OBSERVED: workflow marker\n")
    _put(tmp_path, "src/app.py", "OBSERVED: implementation marker\n")

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_READY_TO_DRAFT_HLD
    assert len(j0.accepted_facts(artifacts.evidence_pack)) == 3
    assert set(artifacts.files_read) == {"README.md", "specs/workflow.md", "src/app.py"}


def test_product_decision_fixture_blocks_hld_draftability(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: product exists\n")
    _put(tmp_path, "hld.md", "PRODUCT_DECISION: source_of_truth_ownership\n")

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
    assert artifacts.product_decision_register[0]["id"] == "source_of_truth_ownership"


def test_conflict_fixture_blocks_hld_draftability(tmp_path) -> None:
    _put(tmp_path, "hld.md", "OBSERVED: external controller owns run state\n")
    _put(tmp_path, "specs/state.md", "CONFLICT: local SQLite/session state owns lifecycle\n")
    _put(tmp_path, "src/core.py", "REPO_STATE_CONFLICT: true\n")

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_BLOCKED_REPO_STATE_CONFLICT
    assert artifacts.gap_report["repo_state_conflict"] is True
    assert any(
        item["label"] == j0.EVIDENCE_CONFLICT
        for item in artifacts.evidence_pack["evidence"]
    )


def test_insufficient_evidence_fixture_stays_insufficient(tmp_path) -> None:
    _put(tmp_path, "README.md", "UNKNOWN: product intent is missing\n")
    _put(tmp_path, "state.json", '{"evidence": [{"label": "INFERRED", "statement": "resume may exist"}]}')

    before, after, _artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_INSUFFICIENT_EVIDENCE
    assert result.accepted_fact_count == 0


def test_unknown_backed_requirement_is_not_ready(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: run records exist\n")
    _put(tmp_path, "hld.md", "REQUIREMENT_UNKNOWN: REQ-agent-can-resume\n")

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict != j0.VERDICT_READY_TO_DRAFT_HLD
    assert result.verdict == j0.VERDICT_INSUFFICIENT_EVIDENCE
    assert artifacts.candidate_requirements[0]["evidence_label"] == j0.EVIDENCE_UNKNOWN


def test_safety_authority_fixture_blocks_and_grants_no_authority(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: blocked runs exist\n")
    _put(tmp_path, "state.json", '{"safety_authority_gaps": ["unclear agent approval authority"]}')

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_BLOCKED_PRODUCT_DECISIONS_REQUIRED
    assert "unclear agent approval authority" in result.blockers[0]
    assert result.grants_approval_authority is False
    assert result.authorizes_implementation is False
    assert result.authorizes_work_orders is False
    assert artifacts.authority["grants_approval_authority"] is False
    assert artifacts.authority["authorizes_implementation"] is False
    assert artifacts.authority["authorizes_work_orders"] is False


def test_read_only_proof_detects_no_content_or_file_set_changes(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: product intent marker\n")
    _put(tmp_path, "specs/workflow.md", "OBSERVED: workflow marker\n")
    _put(tmp_path, "src/app.py", "OBSERVED: implementation marker\n")

    before, after, _artifacts, result = _collect(tmp_path)

    assert result.verdict == j0.VERDICT_READY_TO_DRAFT_HLD
    assert before == after


def test_narrow_scope_ignores_unrelated_files_without_broad_scanning(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: product intent marker\n")
    _put(tmp_path, "specs/workflow.md", "OBSERVED: workflow marker\n")
    _put(tmp_path, "src/app.py", "OBSERVED: implementation marker\n")
    _put(tmp_path, "notes/random.md", "CONFLICT: should not be collected\n")
    _put(tmp_path, "deep/nested/file.py", "PRODUCT_DECISION: should_not_be_seen\n")

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_READY_TO_DRAFT_HLD
    assert artifacts.ignored_files == ["deep", "notes"]
    assert "notes/random.md" not in artifacts.files_read
    assert "deep/nested/file.py" not in artifacts.files_read
    assert all(
        "should not be collected" not in item["statement"]
        for item in artifacts.evidence_pack["evidence"]
    )


def test_state_json_can_supply_full_artifact_inputs(tmp_path) -> None:
    _put(
        tmp_path,
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

    before, after, artifacts, result = _collect(tmp_path)

    assert before == after
    assert result.verdict == j0.VERDICT_READY_WITH_OPEN_QUESTIONS
    assert artifacts.candidate_requirements[0]["id"] == "REQ-copy"
    assert artifacts.open_questions == ["confirm copy"]


def test_invalid_state_json_fails_without_mutating_fixture(tmp_path) -> None:
    _put(tmp_path, "state.json", "{not json")
    before = _snapshot(tmp_path)

    try:
        collector.collect_filesystem_fixture_evidence(tmp_path)
    except j0.InvalidJourney0ArtifactError:
        pass
    else:
        raise AssertionError("invalid state JSON should fail")

    assert before == _snapshot(tmp_path)


def test_allowlisted_symlink_escape_is_rejected_without_mutation(tmp_path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_bytes(b"OBSERVED: outside fixture content\n")
    (tmp_path / "README.md").symlink_to(outside)
    before = _snapshot(tmp_path)

    try:
        collector.collect_filesystem_fixture_evidence(tmp_path)
    except j0.InvalidJourney0ArtifactError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("allowlisted symlink should be rejected")

    assert before == _snapshot(tmp_path)


def test_broken_allowlisted_symlink_is_rejected_without_mutation(tmp_path) -> None:
    (tmp_path / "README.md").symlink_to(tmp_path / "missing.md")
    before = _snapshot(tmp_path)

    try:
        collector.collect_filesystem_fixture_evidence(tmp_path)
    except j0.InvalidJourney0ArtifactError as exc:
        assert "symlink" in str(exc)
    else:
        raise AssertionError("broken allowlisted symlink should be rejected")

    assert before == _snapshot(tmp_path)


def test_artifact_payload_has_no_authority_grants(tmp_path) -> None:
    _put(tmp_path, "README.md", "OBSERVED: product intent marker\n")

    _before, _after, artifacts, result = _collect(tmp_path)
    payload: Mapping[str, object] = artifacts.to_dict()

    assert result.handoff_kind == j0.HANDOFF_EVIDENCE_AND_GAP_INPUT
    assert result.journey1_input_only is True
    assert payload["authority"]["grants_approval_authority"] is False
    assert payload["authority"]["authorizes_implementation"] is False
    assert payload["authority"]["authorizes_work_orders"] is False
