from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from hldspec import mediator_guidance as mg


class AgentFirstCliContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = Path(__file__).resolve().parents[1]
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_start(self, source: Path, target: Path, comment: str = "create target") -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--source",
                str(source),
                "--target",
                str(target),
                "--comment",
                comment,
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def run_facade(self, command: str, target: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                command,
                "--target",
                str(target),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_agent_first_start_creates_target_session(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source_text = "# High-Level Design\n\n## HLD-001 - Purpose\n\nHLD-ID: HLD-001\n"
        source.write_text(source_text, encoding="utf-8")
        before_entries = {path.relative_to(self.tmp_path) for path in self.tmp_path.rglob("*")}

        result = subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--source",
                str(source),
                "--target",
                str(target),
                "--agent",
                "manual",
                "--comment",
                "test run",
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session_path = target / ".hldspec" / "agent_session.json"
        interview_json_path = target / ".hldspec" / "interview_answers.json"
        interview_md_path = target / ".hldspec" / "interview_answers.md"
        prompt_path = target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md"
        self.assertTrue(session_path.exists())
        self.assertTrue(interview_json_path.exists())
        self.assertTrue(interview_md_path.exists())
        self.assertTrue(prompt_path.exists())
        self.assertTrue((target / "targetHLD" / "raw" / "HLD.raw.md").exists())
        self.assertTrue((target / "targetHLD" / "HLD.md").exists())
        packet_path = target / ".hldspec" / "mediator" / "mediator_packet.json"
        start_prompt = target / "prompts" / "mediator" / "START_MEDIATOR.md"
        devin_prompt = target / "prompts" / "mediator" / "DEVIN_MEDIATOR_SKILL.md"
        direct_prompt = target / "prompts" / "mediator" / "CODEX_CLAUDE_MEDIATOR.md"
        self.assertTrue(packet_path.exists())
        self.assertTrue(start_prompt.exists())
        self.assertTrue(devin_prompt.exists())
        self.assertTrue(direct_prompt.exists())

        packet = json.loads(packet_path.read_text(encoding="utf-8"))
        self.assertEqual([], mg.validate_mediator_packet(packet))
        devin_text = devin_prompt.read_text(encoding="utf-8")
        direct_text = direct_prompt.read_text(encoding="utf-8")
        self.assertIn("create agent on {path} as {session-name} using model {model} [permission-mode {mode}]", devin_text)
        self.assertIn("`go`", devin_text)
        self.assertIn("`stop`", devin_text)
        self.assertIn("Stop now is not a valid Devin control word.", devin_text)
        self.assertNotIn("stop now is a valid Devin control word", devin_text)
        self.assertIn("stop now is a direct-mode optional behavior only", direct_text)
        self.assertIn("Codex / Claude direct mediator mode", direct_text)
        self.assertEqual(source_text, source.read_text(encoding="utf-8"))

        session = json.loads(session_path.read_text(encoding="utf-8"))
        self.assertEqual("manual", session["agent"])
        self.assertEqual("create", session["mode"])
        self.assertEqual(str(source.resolve()), session["source"]["path"])
        self.assertEqual(str(target.resolve() / ".hldspec" / "sync"), session["paths"]["hldspec_sync"])
        self.assertEqual(str(target.resolve() / ".hldspec" / "events.jsonl"), session["paths"]["events"])
        self.assertIn("start an agent session", result.stdout)
        self.assertIn("Interview answers:", result.stdout)
        self.assertIn("Mediator guidance:", result.stdout)
        self.assertIn(".hldspec/mediator/mediator_packet.json", result.stdout)
        self.assertIn("prompts/mediator/START_MEDIATOR.md", result.stdout)
        self.assertIn("prompts/mediator/DEVIN_MEDIATOR_SKILL.md", result.stdout)
        self.assertIn("prompts/mediator/CODEX_CLAUDE_MEDIATOR.md", result.stdout)
        self.assertIn(
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            result.stdout,
        )
        self.assertIn(
            "HLDspec generates mediator guidance only; it does not create live Devin/tmux sessions.",
            result.stdout,
        )

        interview = json.loads(interview_json_path.read_text(encoding="utf-8"))
        self.assertEqual(str(source.resolve()), interview["source"]["path"])
        self.assertEqual(session["source"]["sha256"], interview["source"]["sha256"])
        self.assertEqual(str(target.resolve()), interview["target"])
        self.assertEqual("create", interview["mode"])
        self.assertEqual("manual", interview["agent"])
        self.assertEqual("test run", interview["comment"])
        self.assertEqual("CREATE", interview["intent_classification"])
        self.assertEqual("UNKNOWN", interview["approval_expectations"])
        self.assertEqual([], interview["constraints"])
        self.assertEqual([], interview["open_questions"])
        self.assertIn("# HLDspec Interview Answers", interview_md_path.read_text(encoding="utf-8"))

        prompt_text = prompt_path.read_text(encoding="utf-8")
        self.assertIn("scripts/hldspec continue --target", prompt_text)
        self.assertNotIn("target/.hldspec/firstrun/.specify/sync", prompt_text)
        self.assertIn(".hldspec/mediator/mediator_packet.json", prompt_text)
        self.assertIn("prompts/mediator/START_MEDIATOR.md", prompt_text)
        self.assertIn("prompts/mediator/DEVIN_MEDIATOR_SKILL.md", prompt_text)
        self.assertIn("prompts/mediator/CODEX_CLAUDE_MEDIATOR.md", prompt_text)
        self.assertIn(
            "create agent on {path} as {session-name} using model {model} [permission-mode {mode}]",
            prompt_text,
        )
        self.assertIn(
            "HLDspec generates mediator guidance only; it does not create live Devin/tmux sessions.",
            prompt_text,
        )

        after_entries = {path.relative_to(self.tmp_path) for path in self.tmp_path.rglob("*")}
        created_entries = after_entries - before_entries
        self.assertTrue(created_entries)
        for entry in created_entries:
            self.assertEqual("target", entry.parts[0], f"start created durable artifact outside target: {entry}")

    def test_doctor_checks_interview_artifacts_when_target_is_provided(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")

        result = self.run_start(source, target)
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)

        result = self.run_facade("doctor", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn(str(target / ".hldspec" / "interview_answers.json"), result.stdout)
        self.assertIn(str(target / ".hldspec" / "interview_answers.md"), result.stdout)

    def test_agent_first_diff_detects_unchanged_source(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")

        subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--source",
                str(source),
                "--target",
                str(target),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=True,
        )

        result = subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "diff",
                "--source",
                str(source),
                "--target",
                str(target),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode)
        self.assertIn("Diff status: unchanged", result.stdout)

    def test_status_includes_next_safe_action(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("status", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("## Next Safe Action", result.stdout)
        self.assertIn("Open prompts/agent/START_HLDSPEC_AGENT.md", result.stdout)

    def test_status_reports_validation_status_when_validation_report_exists(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        validation = target / ".hldspec" / "validation" / "context_prompt_validation.json"
        validation.parent.mkdir(parents=True, exist_ok=True)
        validation.write_text(json.dumps({"status": "PASS"}, indent=2) + "\n", encoding="utf-8")

        result = self.run_facade("status", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("Validation status: PASS", result.stdout)
        self.assertIn(str(validation), result.stdout)

    def test_status_reports_promotion_gate_status_when_promotion_report_exists(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        promotion = target / ".hldspec" / "validation" / "promotion_gate.json"
        promotion.parent.mkdir(parents=True, exist_ok=True)
        promotion.write_text(json.dumps({"status": "ACTION"}, indent=2) + "\n", encoding="utf-8")

        result = self.run_facade("status", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("Promotion gate status: ACTION", result.stdout)
        self.assertIn("Resolve ACTION/CONFLICT blockers", result.stdout)

    def test_review_separates_blocking_and_optional_files(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        blocking = target / ".hldspec" / "constitution_update_plan.md"
        optional = target / ".hldspec" / "backend_technology_recommendation.md"
        blocking.write_text("# Constitution\n", encoding="utf-8")
        optional.write_text("# Backend\n", encoding="utf-8")

        result = self.run_facade("review", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("## Blocking Review Files", result.stdout)
        self.assertIn(str(blocking), result.stdout)
        self.assertIn("## Optional Context Files", result.stdout)
        self.assertIn(str(optional), result.stdout)
        self.assertIn("## Missing Blocking Files", result.stdout)
        self.assertIn("## Missing Non-Blocking Files", result.stdout)

    def test_doctor_reports_final_summary(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("doctor", target)

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn("## Final Summary", result.stdout)
        self.assertIn("## SpecKit Readiness", result.stdout)
        self.assertIn("Real SpecKit init means `.specify/memory/` exists; `.specify/source/` alone is only the HLDspec mirror.", result.stdout)
        self.assertIn("Summary: PASS", result.stdout)

    def test_doctor_exits_nonzero_when_final_summary_is_action(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        promotion = target / ".hldspec" / "validation" / "promotion_gate.json"
        promotion.parent.mkdir(parents=True, exist_ok=True)
        promotion.write_text(json.dumps({"status": "ACTION"}, indent=2) + "\n", encoding="utf-8")

        result = self.run_facade("doctor", target)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("Summary: ACTION", result.stdout)
        self.assertIn("Resolve listed ACTION/CONFLICT items", result.stdout)

    def test_speckit_doctor_reports_readiness(self) -> None:
        target = self.tmp_path / "target"
        target.mkdir()

        result = self.run_facade("speckit-doctor", target)

        self.assertNotEqual(0, result.returncode)
        self.assertIn("STATUS:", result.stdout)
        self.assertIn("Next actions:", result.stdout)
        self.assertIn("Workspace initialized:", result.stdout)
        self.assertIn("Branch hook/manual branch path ready:", result.stdout)
        self.assertIn("Real SpecKit init means `.specify/memory/` exists; `.specify/source/` alone is only the HLDspec mirror.", result.stdout)

    def test_output_docs_exist_and_mention_exit_code_semantics(self) -> None:
        output_contract = self.repo / "docs" / "HLDSPEC_OUTPUT_CONTRACT.md"
        quality_requirements = self.repo / "docs" / "HLDSPEC_QUALITY_REQUIREMENTS.md"

        self.assertTrue(output_contract.exists())
        self.assertTrue(quality_requirements.exists())
        self.assertIn("Exit Code Semantics", output_contract.read_text(encoding="utf-8"))
        self.assertIn("promotion/readiness", quality_requirements.read_text(encoding="utf-8").lower())

    def test_status_review_doctor_do_not_modify_source_hld(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source_text = "# HLD\n\nKeep me unchanged.\n"
        source.write_text(source_text, encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        for command in ("status", "review", "doctor"):
            result = self.run_facade(command, target)
            self.assertEqual(0, result.returncode, command + result.stderr + result.stdout)

        self.assertEqual(source_text, source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
