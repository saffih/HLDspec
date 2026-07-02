"""Tests for Journey 0 read-only evidence collectors."""
from __future__ import annotations

import inspect
import tempfile
import unittest
from pathlib import Path

from hldspec import journey0_collectors as collectors
from hldspec.journey0_artifacts import BrownfieldEvidencePack, EvidenceLabel


def _put(root: Path, rel: str, text: str = "observed\n") -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _snapshot(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


class Journey0CollectorTests(unittest.TestCase):
    def test_collector_returns_brownfield_evidence_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "README.md", "# Product")

            pack = collectors.collect_journey0_observed_evidence(root)

        self.assertIsInstance(pack, BrownfieldEvidencePack)
        self.assertEqual(len(pack.evidence), 1)

    def test_observed_files_become_observed_evidence_items(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "src/app.py", "print('hi')\n")
            _put(root, "tests/test_app.py", "def test_app(): pass\n")

            pack = collectors.collect_journey0_observed_evidence(root)

        self.assertEqual(
            [item.label for item in pack.evidence],
            [EvidenceLabel.OBSERVED, EvidenceLabel.OBSERVED],
        )
        self.assertEqual(
            [item.source_type for item in pack.evidence],
            ["code_file", "test_file"],
        )

    def test_source_ref_and_source_location_are_populated(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "docs/notes.md", "# Notes\n")

            item = collectors.collect_journey0_observed_evidence(root).evidence[0]

        self.assertEqual(item.source_ref, "docs/notes.md")
        self.assertEqual(item.source_location, "docs/notes.md:1")
        self.assertIn("docs/notes.md", item.summary)

    def test_collector_is_read_only_for_fixture_tree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "README.md", "# Product\n")
            _put(root, ".specify/spec.md", "# Old spec\n")
            before = _snapshot(root)

            collectors.collect_journey0_observed_evidence(root)

            self.assertEqual(_snapshot(root), before)

    def test_heavy_vendor_cache_directories_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "README.md", "# Product\n")
            _put(root, "node_modules/pkg/index.js", "ignored\n")
            _put(root, ".venv/lib/site.py", "ignored\n")
            _put(root, "__pycache__/mod.py", "ignored\n")
            _put(root, "." + "g" + "it/config", "ignored\n")

            pack = collectors.collect_journey0_observed_evidence(root)

        self.assertEqual([item.source_ref for item in pack.evidence], ["README.md"])

    def test_deterministic_ordering_and_ids_for_same_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "b.md", "b\n")
            _put(root, "a.md", "a\n")
            _put(root, "src/c.py", "c\n")

            first = collectors.collect_journey0_observed_evidence(root).to_dict()
            second = collectors.collect_journey0_observed_evidence(root).to_dict()

        self.assertEqual(first, second)
        self.assertEqual(
            [item["evidence_id"] for item in first["evidence"]],
            ["EVIDENCE-001", "EVIDENCE-002", "EVIDENCE-003"],
        )
        self.assertEqual(
            [item["source_ref"] for item in first["evidence"]],
            ["a.md", "b.md", "src/c.py"],
        )

    def test_old_spec_files_are_observed_only_not_backlog_or_authority(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, ".specify/spec.md", "# Old requirements\n")

            item = collectors.collect_journey0_observed_evidence(root).evidence[0]
            serialized = item.to_dict()

        self.assertEqual(item.label, EvidenceLabel.OBSERVED)
        self.assertEqual(item.source_type, "old_spec_state")
        self.assertFalse(item.is_authority)
        self.assertNotIn("backlog", serialized)
        self.assertNotIn("status", serialized)

    def test_no_verdict_gap_decision_plan_handoff_or_toolchain_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _put(root, "README.md", "# Product\n")

            result = collectors.collect_journey0_observed_evidence(root)
            serialized = result.to_dict()

        self.assertEqual(serialized["artifact"], "brownfield_evidence_pack")
        for forbidden_key in (
            "verdict",
            "gaps",
            "decisions",
            "hld_sections_to_create_or_update",
            "handoff",
            "toolchain",
        ):
            self.assertNotIn(forbidden_key, serialized)

    def test_boundary_tokens_do_not_appear_in_collector_module(self) -> None:
        source = inspect.getsource(collectors)

        forbidden_tokens = (
            "subprocess",
            "argparse",
            "click",
            "SpecKit",
            "speckit",
            "write_text",
            "open(",
            "classify_",
            "compute_verdict",
            "draftability",
            "backlog",
        )
        for token in forbidden_tokens:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
