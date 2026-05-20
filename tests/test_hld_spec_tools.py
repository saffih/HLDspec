from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


SYNC = load_module("hld_spec_sync_under_test", REPO_ROOT / "hld_spec_sync.py")
DOWNSTREAM = load_module("hld_spec_downstream_under_test", REPO_ROOT / "hld_spec_downstream.py")


THINKER_TRACE = [
    {"thinker": "Charlie Munger (CH)", "found": "failure was unbounded", "changed": "bounded writes"},
    {"thinker": "Occam's Razor (OM)", "found": "boundary was unclear", "changed": "made one conflict file"},
    {"thinker": "Richard Feynman (FE)", "found": "claim needed proof", "changed": "added verification"},
    {"thinker": "Karl Popper (PO)", "found": "contract was unfalsifiable", "changed": "added required fields"},
    {"thinker": "Immanuel Kant (KT)", "found": "pattern would not universalize", "changed": "restricted fixes"},
    {"thinker": "Saffi (SH)", "found": "middle path needed boundary", "changed": "human loop for conflicts"},
]


def handled_skeptic_payload() -> dict[str, object]:
    return {
        "status": "HANDLED",
        "scope": "test",
        "thinker_trace": THINKER_TRACE,
        "actions": [
            {
                "id": "SK-ACTION-001",
                "status": "handled",
                "issue": "test gap",
                "action": "closed gap",
                "verification": "unit test",
                "evidence_level": "REPRODUCED",
            }
        ],
        "conflicts": [],
        "human_loop": "not_required",
    }


def conflict_skeptic_payload() -> dict[str, object]:
    return {
        "status": "CONFLICT",
        "scope": "test",
        "thinker_trace": THINKER_TRACE,
        "actions": [],
        "conflicts": [
            {
                "id": "SK-CONFLICT-001",
                "status": "unresolved",
                "issue": "choose source of truth",
                "thesis": "HLD dominates",
                "antithesis": "spec dominates",
                "tradeoffs": "drift control vs local precision",
                "blocking_unknowns": ["owner decision"],
                "missing_evidence": ["human intent"],
                "safe_recommendation": "pause conflicted area",
                "decision_needed": "pick HLD or spec",
            }
        ],
        "human_loop": "required",
    }


class HldSpecToolTests(unittest.TestCase):
    def test_sync_rejects_implementation_write(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            log_path = workspace / "agent.log"
            log_path.write_text("WRITE FILE: src/unsafe.py\nCONTENT:\nprint('bad')\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "disallowed sync write target"):
                SYNC.validate_write_targets(
                    log_path,
                    workspace,
                    allow_constitution=True,
                    allow_specs=True,
                )

    def test_sync_ignores_echoed_prompt_write_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            log_path = workspace / "agent.log"
            prompt = "WRITE FILE: src/unsafe.py\nCONTENT:\nprint('bad')\n"
            log_path.write_text(
                "codex header\nuser\n"
                + prompt
                + "\nWRITE FILE: .specify/sync/sync_report.md\n"
                + "CONTENT:\n# Real Sync Report\n",
                encoding="utf-8",
            )

            SYNC.validate_write_targets(
                log_path,
                workspace,
                allow_constitution=True,
                allow_specs=True,
                echoed_prompt=prompt,
            )
            writes = SYNC.apply_write_blocks(
                log_path,
                workspace,
                allow_constitution=True,
                allow_specs=True,
                echoed_prompt=prompt,
            )

            self.assertEqual(1, writes)
            self.assertFalse((workspace / "src" / "unsafe.py").exists())
            self.assertEqual("# Real Sync Report\n", (workspace / ".specify" / "sync" / "sync_report.md").read_text())

    def test_sync_accepts_complete_skeptic_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            report = workspace / SYNC.SYNC_SKEPTIC_REPORT_REL
            conflicts = workspace / SYNC.SYNC_SKEPTIC_CONFLICTS_REL
            report.parent.mkdir(parents=True)
            report.write_text("# Skeptic Report\n", encoding="utf-8")
            conflicts.write_text(json.dumps(handled_skeptic_payload()), encoding="utf-8")

            errors: list[str] = []
            unresolved = SYNC.evaluate_skeptic_outputs(
                workspace,
                report_rel=SYNC.SYNC_SKEPTIC_REPORT_REL,
                conflicts_rel=SYNC.SYNC_SKEPTIC_CONFLICTS_REL,
                errors=errors,
            )

            self.assertEqual([], errors)
            self.assertEqual([], unresolved)

    def test_sync_rejects_incomplete_skeptic_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            report = workspace / SYNC.SYNC_SKEPTIC_REPORT_REL
            conflicts = workspace / SYNC.SYNC_SKEPTIC_CONFLICTS_REL
            report.parent.mkdir(parents=True)
            report.write_text("# Skeptic Report\n", encoding="utf-8")
            conflicts.write_text(json.dumps({"status": "DONE", "thinker_trace": []}), encoding="utf-8")

            errors: list[str] = []
            SYNC.evaluate_skeptic_outputs(
                workspace,
                report_rel=SYNC.SYNC_SKEPTIC_REPORT_REL,
                conflicts_rel=SYNC.SYNC_SKEPTIC_CONFLICTS_REL,
                errors=errors,
            )

            self.assertTrue(any("invalid skeptic status" in error for error in errors))
            self.assertTrue(any("invalid skeptic thinker_trace" in error for error in errors))

    def test_sync_rejects_legacy_array_skeptic_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            report = workspace / SYNC.SYNC_SKEPTIC_REPORT_REL
            conflicts = workspace / SYNC.SYNC_SKEPTIC_CONFLICTS_REL
            report.parent.mkdir(parents=True)
            report.write_text("# Skeptic Report\n", encoding="utf-8")
            conflicts.write_text(json.dumps([]), encoding="utf-8")

            errors: list[str] = []
            SYNC.evaluate_skeptic_outputs(
                workspace,
                report_rel=SYNC.SYNC_SKEPTIC_REPORT_REL,
                conflicts_rel=SYNC.SYNC_SKEPTIC_CONFLICTS_REL,
                errors=errors,
            )

            self.assertTrue(any("expected object" in error for error in errors))

    def test_downstream_phase_policy_lists_skeptic_artifacts(self) -> None:
        policy = DOWNSTREAM.phase_write_policy("all", skeptic=True)
        self.assertIn(".specify/sync/downstream/skeptic_report.md", policy)
        self.assertIn(".specify/sync/downstream/skeptic_conflicts.json", policy)

    def test_downstream_unknown_target_fails_strict_resolution(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / "specs" / "001-alpha").mkdir(parents=True)
            (workspace / "specs" / "001-alpha" / "spec.md").write_text("# Spec\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Unknown target"):
                DOWNSTREAM.resolve_spec_dirs(workspace, ["999"], strict=True)

    def test_downstream_ignores_echoed_prompt_write_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            log_path = workspace / "agent.log"
            prompt = "WRITE FILE: src/unsafe.py\nCONTENT:\nprint('bad')\n"
            log_path.write_text(
                "codex header\nuser\n"
                + prompt
                + "\nWRITE FILE: .specify/sync/downstream/downstream_analysis.md\n"
                + "CONTENT:\n# Real Downstream Analysis\n",
                encoding="utf-8",
            )

            DOWNSTREAM.validate_write_targets(
                log_path,
                workspace,
                phase="analyze",
                allow_implementation=False,
                implementation_roots=[],
                echoed_prompt=prompt,
            )
            writes = DOWNSTREAM.apply_write_blocks(
                log_path,
                workspace,
                phase="analyze",
                allow_implementation=False,
                implementation_roots=[],
                echoed_prompt=prompt,
            )

            self.assertEqual(1, writes)
            self.assertFalse((workspace / "src" / "unsafe.py").exists())
            self.assertEqual(
                "# Real Downstream Analysis\n",
                (workspace / ".specify" / "sync" / "downstream" / "downstream_analysis.md").read_text(),
            )

    def test_downstream_conflict_contract_returns_unresolved(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            report = workspace / DOWNSTREAM.DOWNSTREAM_SKEPTIC_REPORT_REL
            conflicts = workspace / DOWNSTREAM.DOWNSTREAM_SKEPTIC_CONFLICTS_REL
            report.parent.mkdir(parents=True)
            report.write_text("# Skeptic Report\n", encoding="utf-8")
            conflicts.write_text(json.dumps(conflict_skeptic_payload()), encoding="utf-8")

            errors: list[str] = []
            unresolved = DOWNSTREAM.evaluate_skeptic_outputs(
                workspace,
                report_rel=DOWNSTREAM.DOWNSTREAM_SKEPTIC_REPORT_REL,
                conflicts_rel=DOWNSTREAM.DOWNSTREAM_SKEPTIC_CONFLICTS_REL,
                errors=errors,
            )

            self.assertEqual([], errors)
            self.assertEqual(1, len(unresolved))
            self.assertEqual("pick HLD or spec", unresolved[0]["decision_needed"])

    def test_downstream_main_returns_conflict_code(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "hld.md"
            hld_path.write_text("# HLD\n", encoding="utf-8")
            (workspace / ".specify" / "memory").mkdir(parents=True)
            (workspace / ".specify" / "sync").mkdir(parents=True)
            (workspace / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
            (workspace / ".specify" / "sync" / "spec_index.json").write_text("[]\n", encoding="utf-8")
            (workspace / "specs" / "001-alpha").mkdir(parents=True)
            (workspace / "specs" / "001-alpha" / "spec.md").write_text("# Spec\n", encoding="utf-8")

            def fake_run_agent(**kwargs):
                Path(kwargs["log_path"]).write_text(
                    "WRITE FILE: .specify/sync/downstream/downstream_analysis.md\n"
                    "CONTENT:\n# Downstream Analysis\n\n"
                    "WRITE FILE: .specify/sync/downstream/gap_closure_plan.md\n"
                    "CONTENT:\n# Gap Closure Plan\n\n"
                    "WRITE FILE: .specify/sync/downstream/skeptic_report.md\n"
                    "CONTENT:\n# Skeptic Report\n\n"
                    "WRITE FILE: .specify/sync/downstream/skeptic_conflicts.json\n"
                    f"CONTENT:\n{json.dumps(conflict_skeptic_payload())}\n",
                    encoding="utf-8",
                )
                return 0

            old_run_agent = DOWNSTREAM.run_agent
            old_argv = sys.argv
            DOWNSTREAM.run_agent = fake_run_agent
            sys.argv = [
                "hld_spec_downstream.py",
                "--hld",
                str(hld_path),
                "--workspace",
                str(workspace),
                "--phase",
                "analyze",
                "--agent",
                "custom",
                "--agent-command",
                "fake",
                "--skeptic",
            ]
            try:
                rc = DOWNSTREAM.main()
            finally:
                DOWNSTREAM.run_agent = old_run_agent
                sys.argv = old_argv

            self.assertEqual(DOWNSTREAM.CONFLICT_RETURN_CODE, rc)


if __name__ == "__main__":
    unittest.main()
