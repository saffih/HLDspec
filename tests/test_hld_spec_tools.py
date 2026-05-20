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


VALID_HLD = """# HLD

## HLD-001 - Governance

HLD-ID: HLD-001
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: constitution
HLD-RESOURCES: .specify/memory/constitution.md
HLD-VERIFY: preserve source of truth

## HLD-002 - Sync Engine

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: 001
HLD-RESOURCES: hld_spec_sync.py

This section DEPENDS REF HLD-001.
"""


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
    def test_devin_uses_prompt_file_transport(self) -> None:
        cmd = SYNC.build_agent_command(
            agent="devin",
            model="swe-1.6",
            prompt="large prompt",
            prompt_file=Path("/tmp/prompt.md"),
            custom_command=None,
            extra_args=[],
            stdin_prompt=False,
        )

        self.assertEqual(["devin", "--prompt-file", "/tmp/prompt.md", "--model", "swe-1.6"], cmd)
        self.assertNotIn("-p", cmd)
        self.assertNotIn("large prompt", cmd)

    def test_claude_and_codex_transport_unchanged(self) -> None:
        claude_cmd = SYNC.build_agent_command(
            agent="claude",
            model="opus-4.6",
            prompt="prompt",
            prompt_file=Path("/tmp/prompt.md"),
            custom_command=None,
            extra_args=[],
            stdin_prompt=False,
        )
        codex_cmd = SYNC.build_agent_command(
            agent="codex",
            model="gpt-5.5",
            prompt="prompt",
            prompt_file=Path("/tmp/prompt.md"),
            custom_command=None,
            extra_args=[],
            stdin_prompt=False,
        )

        self.assertEqual(["claude", "-p", "prompt", "--model", "opus-4.6"], claude_cmd)
        self.assertEqual(["codex", "exec", "--model", "gpt-5.5", "prompt"], codex_cmd)

    def test_downstream_devin_uses_prompt_file_transport(self) -> None:
        cmd = DOWNSTREAM.build_agent_command(
            agent="devin",
            model="swe-1.6",
            prompt="large prompt",
            prompt_file=Path("/tmp/prompt.md"),
            custom_command=None,
            extra_args=[],
            stdin_prompt=False,
        )

        self.assertEqual(["devin", "--prompt-file", "/tmp/prompt.md", "--model", "swe-1.6"], cmd)

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

    def test_sync_hld_map_only_generates_artifacts_without_agent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
            old_argv = sys.argv
            sys.argv = [
                "hld_spec_sync.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--hld-map-only",
            ]
            try:
                rc = SYNC.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(0, rc)
            self.assertTrue((workspace / ".specify" / "sync" / "hld_ref_map.json").exists())
            self.assertTrue((workspace / ".specify" / "sync" / "hld_index.md").exists())
            self.assertEqual(
                "## HLD-002 - Sync Engine",
                (workspace / ".specify" / "sync" / "hld_sections" / "HLD-002.md").read_text().splitlines()[0],
            )

    def test_sync_map_prompt_only_uses_bounded_context(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(
                VALID_HLD
                + """
## HLD-003 - Not Selected

HLD-ID: HLD-003
HLD-ROLE: operations
HLD-STATUS: planned
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This should not appear.
""",
                encoding="utf-8",
            )
            old_argv = sys.argv
            sys.argv = [
                "hld_spec_sync.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--use-hld-map",
                "--target-hld",
                "HLD-002",
                "--prompt-only",
            ]
            try:
                rc = SYNC.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(0, rc)
            prompt_paths = list((workspace / "logs" / "hld_spec_sync").glob("*/prompt.md"))
            self.assertEqual(1, len(prompt_paths))
            prompt = prompt_paths[0].read_text(encoding="utf-8")
            self.assertIn("BOUNDED HLD MAP CONTEXT", prompt)
            self.assertIn("HLD SECTION HLD-002", prompt)
            self.assertIn("HLD SECTION HLD-001", prompt)
            self.assertNotIn("This should not appear", prompt)
            report_paths = list((workspace / "logs" / "hld_spec_sync").glob("*/context_selection.json"))
            self.assertEqual(1, len(report_paths))

    def test_sync_target_loads_normal_refs(self) -> None:
        hld_text = """## HLD-001 - A

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section REF HLD-002.

## HLD-002 - B

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
"""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            parsed = SYNC.hld_map.parse_hld_text(hld_text)

            _context, report = SYNC.select_hld_context(
                parsed_map=parsed,
                workspace=workspace,
                target_hld="HLD-001",
                max_chars=20000,
                max_spec_chars=1000,
            )

            loaded_ids = [section["id"] for section in report["loaded_sections"]]
            self.assertIn("HLD-002", loaded_ids)

    def test_sync_target_reports_normal_refs_when_budget_exceeded(self) -> None:
        hld_text = """## HLD-001 - A

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section REF HLD-002.

## HLD-002 - B

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

Budget-heavy optional context.
"""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            parsed = SYNC.hld_map.parse_hld_text(hld_text)

            _context, report = SYNC.select_hld_context(
                parsed_map=parsed,
                workspace=workspace,
                target_hld="HLD-001",
                max_chars=1,
                max_spec_chars=1000,
            )

            self.assertTrue(
                any(
                    item.get("section") == "HLD-002"
                    and item.get("reason") == "prompt-budget-exceeded"
                    and item.get("ref_kind") == "REF"
                    for item in report["skipped_refs"]
                )
            )

    def test_sync_required_refs_are_loaded_before_optional_refs(self) -> None:
        hld_text = """## HLD-001 - A

HLD-ID: HLD-001
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

This section REF HLD-002.
This section DEPENDS REF HLD-003.

## HLD-002 - Optional

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD

## HLD-003 - Required

HLD-ID: HLD-003
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
"""
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            parsed = SYNC.hld_map.parse_hld_text(hld_text)

            _context, report = SYNC.select_hld_context(
                parsed_map=parsed,
                workspace=workspace,
                target_hld="HLD-001",
                max_chars=20000,
                max_spec_chars=1000,
            )

            loaded_ids = [section["id"] for section in report["loaded_sections"]]
            self.assertLess(loaded_ids.index("HLD-003"), loaded_ids.index("HLD-002"))

    def test_sync_map_mode_stages_writes_before_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")

            def fake_run_agent(**kwargs):
                Path(kwargs["log_path"]).write_text(
                    "WRITE FILE: .specify/sync/sync_report.md\n"
                    "CONTENT:\n# Sync Report\n\n"
                    "WRITE FILE: .specify/sync/analyze_report.md\n"
                    "CONTENT:\n# Analyze Report\n\n"
                    "WRITE FILE: .specify/sync/constitution_change_report.md\n"
                    "CONTENT:\n# Constitution Change Report\n\n"
                    "WRITE FILE: .specify/sync/spec_index.json\n"
                    "CONTENT:\n[]\n\n"
                    "WRITE FILE: .specify/sync/feature_graph.json\n"
                    "CONTENT:\n{\"nodes\": [], \"edges\": [], \"recommended_order\": []}\n\n"
                    "WRITE FILE: .specify/sync/missing_report.json\n"
                    "CONTENT:\n[]\n\n"
                    "WRITE FILE: .specify/sync/duplicate_report.json\n"
                    "CONTENT:\n[]\n\n"
                    "WRITE FILE: .specify/sync/drift_report.json\n"
                    "CONTENT:\n[]\n",
                    encoding="utf-8",
                )
                return 0

            old_run_agent = SYNC.run_agent
            old_argv = sys.argv
            SYNC.run_agent = fake_run_agent
            sys.argv = [
                "hld_spec_sync.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--use-hld-map",
                "--target-hld",
                "HLD-002",
                "--report-only",
                "--agent",
                "custom",
                "--agent-command",
                "fake",
            ]
            try:
                rc = SYNC.main()
            finally:
                SYNC.run_agent = old_run_agent
                sys.argv = old_argv

            self.assertEqual(0, rc)
            staged_manifests = list((workspace / ".specify" / "sync" / "staged").glob("*/write_manifest.json"))
            self.assertEqual(1, len(staged_manifests))
            self.assertTrue((workspace / ".specify" / "sync" / "sync_report.md").exists())

    def test_sync_map_mode_failed_staged_validation_does_not_modify_final_files(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
            (workspace / ".specify" / "sync").mkdir(parents=True)
            (workspace / ".specify" / "sync" / "spec_index.json").write_text("[]\n", encoding="utf-8")

            def fake_run_agent(**kwargs):
                Path(kwargs["log_path"]).write_text(
                    "WRITE FILE: .specify/sync/sync_report.md\n"
                    "CONTENT:\n# Sync Report\n\n"
                    "WRITE FILE: .specify/sync/analyze_report.md\n"
                    "CONTENT:\n# Analyze Report\n\n"
                    "WRITE FILE: .specify/sync/constitution_change_report.md\n"
                    "CONTENT:\n# Constitution Change Report\n\n"
                    "WRITE FILE: .specify/sync/spec_index.json\n"
                    "CONTENT:\nnot json\n\n"
                    "WRITE FILE: .specify/sync/feature_graph.json\n"
                    "CONTENT:\n{\"nodes\": [], \"edges\": [], \"recommended_order\": []}\n\n"
                    "WRITE FILE: .specify/sync/missing_report.json\n"
                    "CONTENT:\n[]\n\n"
                    "WRITE FILE: .specify/sync/duplicate_report.json\n"
                    "CONTENT:\n[]\n\n"
                    "WRITE FILE: .specify/sync/drift_report.json\n"
                    "CONTENT:\n[]\n",
                    encoding="utf-8",
                )
                return 0

            old_run_agent = SYNC.run_agent
            old_argv = sys.argv
            SYNC.run_agent = fake_run_agent
            sys.argv = [
                "hld_spec_sync.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--use-hld-map",
                "--target-hld",
                "HLD-002",
                "--report-only",
                "--agent",
                "custom",
                "--agent-command",
                "fake",
            ]
            try:
                rc = SYNC.main()
            finally:
                SYNC.run_agent = old_run_agent
                sys.argv = old_argv

            self.assertEqual(1, rc)
            staged_manifests = list((workspace / ".specify" / "sync" / "staged").glob("*/write_manifest.json"))
            self.assertEqual(1, len(staged_manifests))
            self.assertEqual("[]\n", (workspace / ".specify" / "sync" / "spec_index.json").read_text(encoding="utf-8"))
            self.assertFalse((workspace / ".specify" / "sync" / "sync_report.md").exists())

    def test_sync_map_consolidation_catches_duplicate_risk(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / ".specify" / "sync").mkdir(parents=True)
            (workspace / ".specify" / "sync" / "duplicate_report.json").write_text(
                '[{"status": "DUPLICATE_RISK", "specs": ["001", "002"]}]\n',
                encoding="utf-8",
            )
            parsed = SYNC.hld_map.parse_hld_text(VALID_HLD)

            errors = SYNC.validate_map_consolidation(workspace, parsed)

            self.assertTrue(any("duplicate spec risk" in error for error in errors))

    def test_sync_map_consolidation_catches_missing_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            (workspace / ".specify" / "sync").mkdir(parents=True)
            (workspace / ".specify" / "sync" / "missing_report.json").write_text(
                '[{"recommended_action": "create_spec"}]\n',
                encoding="utf-8",
            )
            parsed = SYNC.hld_map.parse_hld_text(VALID_HLD)

            errors = SYNC.validate_map_consolidation(workspace, parsed)

            self.assertTrue(any("missing HLD coverage" in error for error in errors))

    def test_sync_resume_skips_unchanged_completed_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
            parsed = SYNC.hld_map.parse_hld_file(hld_path)
            prompt_path = workspace / "logs" / "hld_spec_sync" / "run" / "prompt.md"
            log_path = workspace / "logs" / "hld_spec_sync" / "run" / "agent.log"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("prompt", encoding="utf-8")
            log_path.write_text("log", encoding="utf-8")
            SYNC.update_run_state(
                workspace,
                parsed,
                "HLD-002",
                status="done",
                prompt_path=prompt_path,
                log_path=log_path,
                staged_output_path=None,
            )

            reason = SYNC.resume_skip_reason(workspace, parsed, "HLD-002")

            self.assertIsNotNone(reason)

    def test_sync_resume_required_ref_change_invalidates_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
            parsed = SYNC.hld_map.parse_hld_file(hld_path)
            prompt_path = workspace / "logs" / "hld_spec_sync" / "run" / "prompt.md"
            log_path = workspace / "logs" / "hld_spec_sync" / "run" / "agent.log"
            prompt_path.parent.mkdir(parents=True)
            prompt_path.write_text("prompt", encoding="utf-8")
            log_path.write_text("log", encoding="utf-8")
            SYNC.update_run_state(
                workspace,
                parsed,
                "HLD-002",
                status="done",
                prompt_path=prompt_path,
                log_path=log_path,
                staged_output_path=None,
            )
            hld_path.write_text(VALID_HLD.replace("preserve source of truth", "preserve changed truth"), encoding="utf-8")
            changed = SYNC.hld_map.parse_hld_file(hld_path)

            reason = SYNC.resume_skip_reason(workspace, changed, "HLD-002")

            self.assertIsNone(reason)

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

    def test_downstream_hld_map_prompt_only_uses_target_specs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
            (workspace / ".specify" / "memory").mkdir(parents=True)
            (workspace / ".specify" / "sync").mkdir(parents=True)
            (workspace / ".specify" / "memory" / "constitution.md").write_text("# Constitution\n", encoding="utf-8")
            (workspace / ".specify" / "sync" / "spec_index.json").write_text("[]\n", encoding="utf-8")
            (workspace / "specs" / "001-alpha").mkdir(parents=True)
            (workspace / "specs" / "001-alpha" / "spec.md").write_text("# Spec\n", encoding="utf-8")

            old_argv = sys.argv
            sys.argv = [
                "hld_spec_downstream.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--use-hld-map",
                "--target-hld",
                "HLD-002",
                "--phase",
                "plan",
                "--prompt-only",
            ]
            try:
                rc = DOWNSTREAM.main()
            finally:
                sys.argv = old_argv

            self.assertEqual(0, rc)
            prompt_paths = list((workspace / "logs" / "hld_spec_downstream").glob("*/prompt.md"))
            self.assertEqual(1, len(prompt_paths))
            prompt = prompt_paths[0].read_text(encoding="utf-8")
            self.assertIn("BOUNDED HLD MAP CONTEXT", prompt)
            self.assertIn("HLD SECTION HLD-002", prompt)
            self.assertIn("SELECTED SPEC", prompt)

    def test_downstream_target_hld_rejects_inconsistent_spec_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
            (workspace / "specs" / "001-alpha").mkdir(parents=True)
            (workspace / "specs" / "001-alpha" / "spec.md").write_text("# Spec 1\n", encoding="utf-8")
            (workspace / "specs" / "002-beta").mkdir(parents=True)
            (workspace / "specs" / "002-beta" / "spec.md").write_text("# Spec 2\n", encoding="utf-8")

            old_argv = sys.argv
            sys.argv = [
                "hld_spec_downstream.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--use-hld-map",
                "--target-hld",
                "HLD-002",
                "--target",
                "002",
                "--prompt-only",
            ]
            try:
                with self.assertRaisesRegex(SystemExit, "inconsistent --target"):
                    DOWNSTREAM.main()
            finally:
                sys.argv = old_argv

    def test_downstream_map_mode_stages_writes_before_apply(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            workspace = Path(td)
            hld_path = workspace / "HLD.md"
            hld_path.write_text(VALID_HLD, encoding="utf-8")
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
                    "CONTENT:\n# Gap Closure Plan\n",
                    encoding="utf-8",
                )
                return 0

            old_run_agent = DOWNSTREAM.run_agent
            old_argv = sys.argv
            DOWNSTREAM.run_agent = fake_run_agent
            sys.argv = [
                "hld_spec_downstream.py",
                "--workspace",
                str(workspace),
                "--hld",
                str(hld_path),
                "--use-hld-map",
                "--target-hld",
                "HLD-002",
                "--phase",
                "analyze",
                "--agent",
                "custom",
                "--agent-command",
                "fake",
            ]
            try:
                rc = DOWNSTREAM.main()
            finally:
                DOWNSTREAM.run_agent = old_run_agent
                sys.argv = old_argv

            self.assertEqual(0, rc)
            staged_manifests = list((workspace / ".specify" / "sync" / "staged").glob("*/write_manifest.json"))
            self.assertEqual(1, len(staged_manifests))
            self.assertTrue((workspace / ".specify" / "sync" / "downstream" / "downstream_analysis.md").exists())

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
