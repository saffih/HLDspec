from __future__ import annotations

import json
import os
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

    def run_start(self, source: Path, target: Path, comment: str = "create target", env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
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
            env=merged_env,
        )

    def run_start_request(self, request: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "hldspec_agent_session.py"),
                "start",
                "--request",
                request,
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
            env=merged_env,
        )

    def run_facade(self, command: str, target: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
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
            env=merged_env,
        )

    def write_fake_build_loop_bin(self) -> dict[str, str]:
        bin_dir = self.tmp_path / "bin"
        bin_dir.mkdir()
        specify = bin_dir / "specify"
        specify.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [ \"$1\" = \"init\" ] && [ \"${2:-}\" = \"--help\" ]; then\n"
            "  echo '--force'\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"init\" ]; then\n"
            "  mkdir -p .specify/memory .specify/source\n"
            "  printf 'before_specify: true\\n' > .specify/extensions.yml\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"--help\" ] || [ \"$1\" = \"--version\" ]; then\n"
            "  echo ok\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n",
            encoding="utf-8",
        )
        git = bin_dir / "git"
        git.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "if [ \"$1\" = \"-C\" ]; then\n"
            "  repo=\"$2\"\n"
            "  shift 2\n"
            "else\n"
            "  repo=\"$PWD\"\n"
            "fi\n"
            "if [ \"$1\" = \"rev-parse\" ] && [ \"$2\" = \"--show-toplevel\" ]; then\n"
            "  printf '%s\\n' \"$repo\"\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"branch\" ] && [ \"$2\" = \"--show-current\" ]; then\n"
            "  printf 'main\\n'\n"
            "  exit 0\n"
            "fi\n"
            "if [ \"$1\" = \"status\" ] && [ \"$2\" = \"--porcelain\" ]; then\n"
            "  exit 0\n"
            "fi\n"
            "exit 1\n",
            encoding="utf-8",
        )
        specify.chmod(0o755)
        git.chmod(0o755)
        return {"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"}

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

        self.assertNotEqual(0, result.returncode)
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
        self.assertIn("Initialize or point HLDspec at a git workspace", result.stdout)

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
        self.assertIn("Promotion gate: ACTION", result.stdout)
        self.assertIn("Initialize or point HLDspec at a git workspace", result.stdout)

    def test_start_detects_check_hld_workflow_trigger(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        result = self.run_start(source, target, comment="check HLD before preparation")

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual("check_hld", session["workflow_trigger"])
        self.assertIn("HLD readiness check", session["next_action"])

        prompt = (target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").read_text(encoding="utf-8")
        self.assertIn("Workflow trigger: `check_hld`", prompt)
        self.assertIn("routes to check HLD readiness", prompt)
        self.assertIn("Stop after the HLD readiness verdict", prompt)

    def test_start_accepts_minimal_hldspec_request(self) -> None:
        source = self.tmp_path / "Flow-HLD.md"
        target = self.tmp_path / "target-request"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        result = self.run_start_request(
            f"HLDspec HLD: {source} create {target} Build Loop init runtime codex"
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual(str(source.resolve()), session["source"]["path"])
        self.assertEqual("build_loop_init", session["workflow_trigger"])
        self.assertEqual("codex", session["requested_runtime"])
        self.assertEqual("codex", session["agent"])
        self.assertIn("Build Loop init", session["comment"])
        prompt = (target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").read_text(encoding="utf-8")
        self.assertIn("This `Build Loop init` trigger is an explicit request", prompt)
        self.assertNotIn("Execute init only with explicit `--execute`", prompt)

    def test_start_accepts_copy_ready_one_liner_request(self) -> None:
        source = self.tmp_path / "Flow-HLD.md"
        target = self.tmp_path / "target-copy-ready"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        result = self.run_start_request(
            "Use HLDspec with source HLD: "
            f"{source} and target project: {target}. "
            "Prepare the target, check SpecKit readiness, and report STATUS, blockers, evidence, and next safe action. "
            "Do not implement or run SpecKit unless HLDspec says it is safe."
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual(str(source.resolve()), session["source"]["path"])
        self.assertEqual(str(target.resolve()), session["target"])
        self.assertEqual("claude", session["requested_runtime"])
        self.assertEqual("claude", session["agent"])
        self.assertEqual("default", session.get("workflow_trigger") or "default")

    def test_start_request_negated_check_hld_does_not_trigger_workflow(self) -> None:
        source = self.tmp_path / "Flow-HLD.md"
        target = self.tmp_path / "target-no-check"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        result = self.run_start_request(
            f"HLDspec HLD: {source} create {target} do not check HLD yet runtime claude"
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual("default", session.get("workflow_trigger") or "default")

    def test_start_rejects_ambiguous_direct_comment_workflow_trigger(self) -> None:
        source = self.tmp_path / "Flow-HLD.md"
        target = self.tmp_path / "target-ambiguous-comment"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        result = self.run_start(source, target, comment="Build Loop ready after check HLD")

        self.assertEqual(2, result.returncode)
        self.assertIn("ambiguous HLDspec workflow trigger", result.stderr)
        self.assertFalse((target / ".hldspec" / "agent_session.json").exists())

    def test_start_request_accepts_quoted_paths_with_spaces(self) -> None:
        source = self.tmp_path / "Flow HLD.md"
        target = self.tmp_path / "target with spaces"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        result = self.run_start_request(
            f'HLDspec HLD: "{source}" create "{target}" check HLD runtime claude'
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual(str(source.resolve()), session["source"]["path"])
        self.assertEqual(str(target.resolve()), session["target"])
        self.assertEqual("check_hld", session["workflow_trigger"])

    def test_request_path_reaches_bounded_checkpoints_for_all_supported_triggers(self) -> None:
        check_source = self.tmp_path / "check-hld.md"
        check_target = self.tmp_path / "target-check-hld"
        check_source.write_text(
            "# HLD\n\n"
            "## HLD-001 - API Boundary\n\n"
            "HLD-ID: HLD-001\n"
            "HLD-ROLE: api\n"
            "HLD-STATUS: draft\n"
            "HLD-RISK: HIGH\n"
            "HLD-SPECS: TBD\n"
            "HLD-RESOURCES: TBD\n"
            "HLD-VERIFY: TBD\n\n"
            "The API boundary is not fully decided yet.\n",
            encoding="utf-8",
        )
        result = self.run_start_request(
            f"HLDspec HLD: {check_source} create {check_target} check HLD runtime claude"
        )
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        cont = self.run_facade("continue", check_target)
        self.assertEqual(2, cont.returncode, cont.stderr + cont.stdout)
        self.assertIn("Current checkpoint: HLD_READINESS_CHECK", cont.stdout)

        env = self.write_fake_build_loop_bin()
        build_source = self.tmp_path / "build-loop.md"
        build_source.write_text("# HLD\n\n## HLD-001 - Purpose\n\nHLD-ID: HLD-001\n", encoding="utf-8")
        cases = [
            ("Build Loop prereqs", "target-build-loop-prereqs", "BUILD_LOOP_PREREQS"),
            ("Build Loop init", "target-build-loop-init", "BUILD_LOOP_INIT"),
            ("Build Loop ready", "target-build-loop-ready", "BUILD_LOOP_READY"),
        ]
        for trigger_phrase, target_name, checkpoint in cases:
            target = self.tmp_path / target_name
            result = self.run_start_request(
                f"HLDspec HLD: {build_source} create {target} {trigger_phrase} runtime codex",
                env=env,
            )
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            cont = self.run_facade("continue", target, env=env)
            self.assertEqual(2, cont.returncode, cont.stderr + cont.stdout)
            self.assertIn(f"Current checkpoint: {checkpoint}", cont.stdout)

    def test_start_detects_build_loop_workflow_triggers(self) -> None:
        source = self.tmp_path / "HLD.md"
        source.write_text("# HLD\n\n## Boundary\n\nDraft.\n", encoding="utf-8")

        cases = [
            ("build loop prereqs before specify", "build_loop_prereqs", "Build Loop prerequisite report"),
            ("build loop init", "build_loop_init", "real SpecKit init validation"),
            ("build loop ready", "build_loop_ready", "READY_FOR_SPECIFY"),
        ]
        for idx, (comment, trigger, phrase) in enumerate(cases, start=1):
            target = self.tmp_path / f"target-{idx}"
            result = self.run_start(source, target, comment=comment)
            self.assertEqual(0, result.returncode, result.stderr + result.stdout)
            session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
            self.assertEqual(trigger, session["workflow_trigger"])
            self.assertIn("Run hldspec continue", session["next_action"])
            prompt = (target / "prompts" / "agent" / "START_HLDSPEC_AGENT.md").read_text(encoding="utf-8")
            self.assertIn(f"Workflow trigger: `{trigger}`", prompt)
            self.assertIn(phrase, prompt)

    def test_continue_routes_check_hld_trigger_to_readiness_machine(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text(
            "# HLD\n\n"
            "## HLD-001 - API Boundary\n\n"
            "HLD-ID: HLD-001\n"
            "HLD-ROLE: api\n"
            "HLD-STATUS: draft\n"
            "HLD-RISK: HIGH\n"
            "HLD-SPECS: TBD\n"
            "HLD-RESOURCES: TBD\n"
            "HLD-VERIFY: TBD\n\n"
            "The API boundary is not fully decided yet.\n",
            encoding="utf-8",
        )
        start = self.run_start(source, target, comment="check HLD")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("continue", target)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("Machine: ProjectMachine", result.stdout)
        self.assertIn("State: HLD_BLOCKED", result.stdout)
        self.assertIn("HldReadinessMachine:STOP_CHECKPOINT", result.stdout)
        self.assertTrue((target / ".hldspec" / "sync" / "hld_cross_examination.json").exists())
        self.assertTrue((target / ".hldspec" / "sync" / "hld_readiness_check.md").exists())
        state = json.loads((target / ".hldspec" / "sync" / "hldspec_state.json").read_text(encoding="utf-8"))
        self.assertEqual("HLD_BLOCKED", state["current_stage"])
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual("ProjectMachine", session["last_machine"])
        self.assertEqual("HLD_BLOCKED", session["last_state"])
        self.assertEqual("HLD_READINESS_CHECK", session["last_checkpoint_kind"])

    def test_status_and_review_surface_check_hld_artifacts(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target"
        source.write_text(
            "# HLD\n\n"
            "## HLD-001 - API Boundary\n\n"
            "HLD-ID: HLD-001\n"
            "HLD-ROLE: api\n"
            "HLD-STATUS: draft\n"
            "HLD-RISK: HIGH\n"
            "HLD-SPECS: TBD\n"
            "HLD-RESOURCES: TBD\n"
            "HLD-VERIFY: TBD\n\n"
            "The API boundary is not fully decided yet.\n",
            encoding="utf-8",
        )
        start = self.run_start(source, target, comment="check HLD")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        cont = self.run_facade("continue", target)
        self.assertEqual(2, cont.returncode, cont.stderr + cont.stdout)

        status = self.run_facade("status", target)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Workflow trigger: check_hld", status.stdout)
        self.assertIn("Answer grouped readiness questions or provide external evidence", status.stdout)
        self.assertIn("Current state: HLD_BLOCKED / HLD_READINESS_CHECK", status.stdout)

        review = self.run_facade("review", target)
        self.assertEqual(0, review.returncode, review.stderr + review.stdout)
        self.assertIn(str(target / ".hldspec" / "sync" / "hld_cross_examination.md"), review.stdout)
        self.assertIn(str(target / ".hldspec" / "sync" / "hld_readiness_check.md"), review.stdout)

    def test_continue_routes_build_loop_prereqs_trigger(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-prereqs"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop prereqs")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("continue", target)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("Machine: BuildLoopWorkflow", result.stdout)
        self.assertIn("Current checkpoint: BUILD_LOOP_PREREQS", result.stdout)
        self.assertTrue((target / ".hldspec" / "sync" / "build_loop_prereqs_report.json").exists())
        state = json.loads((target / ".hldspec" / "sync" / "hldspec_state.json").read_text(encoding="utf-8"))
        self.assertEqual("BUILD_LOOP_PREREQS", state["current_checkpoint"])
        self.assertEqual("INIT_PREREQS_BLOCKED", state["current_stage"])

    def test_continue_routes_build_loop_init_trigger(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-init"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop init")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("continue", target)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("Machine: BuildLoopWorkflow", result.stdout)
        self.assertIn("Current checkpoint: BUILD_LOOP_INIT", result.stdout)
        self.assertTrue((target / ".hldspec" / "sync" / "build_loop_init_report.md").exists())
        state = json.loads((target / ".hldspec" / "sync" / "hldspec_state.json").read_text(encoding="utf-8"))
        self.assertEqual("BUILD_LOOP_INIT", state["current_checkpoint"])

    def test_continue_routes_build_loop_ready_trigger(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-ready"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop ready")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("continue", target)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("Machine: BuildLoopWorkflow", result.stdout)
        self.assertIn("Current checkpoint: BUILD_LOOP_READY", result.stdout)
        self.assertTrue((target / ".hldspec" / "sync" / "build_loop_ready_report.md").exists())
        state = json.loads((target / ".hldspec" / "sync" / "hldspec_state.json").read_text(encoding="utf-8"))
        self.assertEqual("BUILD_LOOP_READY", state["current_checkpoint"])

    def test_build_loop_ready_blocks_ready_for_specify_until_approval_gate_passes(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-build-loop-ready"
        env = self.write_fake_build_loop_bin()
        source.write_text("# HLD\n\n## HLD-001 - Purpose\n\nHLD-ID: HLD-001\n", encoding="utf-8")

        start = self.run_start(source, target, comment="Build Loop ready", env=env)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = self.run_facade("continue", target, env=env)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("Machine: BuildLoopWorkflow", result.stdout)
        self.assertIn("State: SPECKIT_APPROVAL_GATE_BLOCKED", result.stdout)
        self.assertIn("Current checkpoint: BUILD_LOOP_READY", result.stdout)
        report = json.loads((target / ".hldspec" / "sync" / "build_loop_ready_report.json").read_text(encoding="utf-8"))
        self.assertEqual("ACTION", report["status"])
        self.assertEqual("SPECKIT_APPROVAL_GATE_BLOCKED", report["state"])
        self.assertFalse(report["approval_preflight"]["allowed"])
        self.assertTrue(report["approval_preflight"]["gated"])
        state = json.loads((target / ".hldspec" / "sync" / "hldspec_state.json").read_text(encoding="utf-8"))
        self.assertEqual("SPECKIT_APPROVAL_GATE_BLOCKED", state["current_stage"])
        session = json.loads((target / ".hldspec" / "agent_session.json").read_text(encoding="utf-8"))
        self.assertEqual("SPECKIT_APPROVAL_GATE_BLOCKED", session["last_state"])

        status = self.run_facade("status", target, env=env)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Workflow report: ACTION (SPECKIT_APPROVAL_GATE_BLOCKED)", status.stdout)
        self.assertIn("missing RunSkeptic PASS", status.stdout)

    def test_start_warns_when_source_changes_but_working_hld_copy_exists(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-source-freshness"
        source.write_text("# HLD\n\nv1\n", encoding="utf-8")
        first = self.run_start(source, target)
        self.assertEqual(0, first.returncode, first.stderr + first.stdout)

        source.write_text("# HLD\n\nv2\n", encoding="utf-8")
        second = self.run_start(source, target)
        self.assertEqual(0, second.returncode, second.stderr + second.stdout)

        freshness = json.loads((target / ".hldspec" / "source_freshness.json").read_text(encoding="utf-8"))
        self.assertTrue(freshness["working_hld_differs_from_source"])
        self.assertTrue(freshness["warnings"])
        self.assertEqual("# HLD\n\nv1\n", (target / "targetHLD" / "HLD.md").read_text(encoding="utf-8"))

    def test_build_loop_blocks_when_source_changes_but_working_hld_copy_is_stale(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-stale-build-loop"
        env = self.write_fake_build_loop_bin()
        source.write_text("# HLD\n\nv1\n", encoding="utf-8")
        first = self.run_start(source, target, comment="Build Loop ready", env=env)
        self.assertEqual(0, first.returncode, first.stderr + first.stdout)
        source.write_text("# HLD\n\nv2\n", encoding="utf-8")
        second = self.run_start(source, target, comment="Build Loop ready", env=env)
        self.assertEqual(0, second.returncode, second.stderr + second.stdout)

        result = self.run_facade("continue", target, env=env)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("State: SOURCE_FRESHNESS_BLOCKED", result.stdout)
        self.assertFalse((target / ".specify" / "memory").exists())
        state = json.loads((target / ".hldspec" / "sync" / "hldspec_state.json").read_text(encoding="utf-8"))
        self.assertEqual("SOURCE_FRESHNESS_BLOCKED", state["current_stage"])
        self.assertFalse(state["source_hld_modified"])
        self.assertTrue(state["working_hld_modified"])

        status = self.run_facade("status", target, env=env)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Source freshness:", status.stdout)
        self.assertIn("SOURCE_FRESHNESS_BLOCKED", status.stdout)

    def test_build_loop_recomputes_freshness_when_source_changes_after_start(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-live-freshness"
        env = self.write_fake_build_loop_bin()
        source.write_text("# HLD\n\nv1\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop ready", env=env)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        source.write_text("# HLD\n\nv2\n", encoding="utf-8")

        result = self.run_facade("continue", target, env=env)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("State: SOURCE_FRESHNESS_BLOCKED", result.stdout)
        status = self.run_facade("status", target, env=env)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Source freshness:", status.stdout)
        operator_state = self.run_facade("operator-state", target, env=env)
        self.assertNotEqual(0, operator_state.returncode)
        self.assertIn("State: SOURCE_FRESHNESS_BLOCKED", operator_state.stdout)

    def test_invalid_source_freshness_metadata_blocks_without_crashing(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-invalid-freshness"
        source.write_text("# HLD\n\nv1\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop prereqs")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        (target / ".hldspec" / "source_freshness.json").write_text("{not-json\n", encoding="utf-8")

        status = self.run_facade("status", target)
        doctor = self.run_facade("doctor", target)
        result = self.run_facade("continue", target)

        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Invalid source freshness metadata", status.stdout)
        self.assertNotEqual(0, doctor.returncode)
        self.assertIn("Invalid source freshness metadata", doctor.stdout)
        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("SOURCE_FRESHNESS_BLOCKED", result.stdout)

    def test_build_loop_blocks_when_source_freshness_metadata_is_missing(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-missing-freshness"
        env = self.write_fake_build_loop_bin()
        source.write_text("# HLD\n\nv1\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop init", env=env)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        (target / ".hldspec" / "source_freshness.json").unlink()
        source.unlink()

        result = self.run_facade("continue", target, env=env)

        self.assertEqual(2, result.returncode, result.stderr + result.stdout)
        self.assertIn("State: SOURCE_FRESHNESS_BLOCKED", result.stdout)
        self.assertFalse((target / ".specify" / "memory").exists())

        status = self.run_facade("status", target, env=env)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Source HLD is missing or unreadable", status.stdout)

    def test_status_and_doctor_surface_operator_state_blockers(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-operator-parity"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        status = self.run_facade("status", target)
        doctor = self.run_facade("doctor", target)
        operator_state = self.run_facade("operator-state", target)

        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Operator state: ACTION", status.stdout)
        self.assertNotEqual(0, doctor.returncode)
        self.assertIn("Operator state: ACTION", doctor.stdout)
        self.assertNotEqual(0, operator_state.returncode)

    def test_legacy_state_builder_does_not_report_no_workspace_for_new_layout_target(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-state-builder"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target)
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)

        result = subprocess.run(
            [
                sys.executable,
                str(self.repo / "scripts" / "build_hldspec_state.py"),
                str(target),
                "--source-hld",
                str(source),
            ],
            cwd=self.repo,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        state_path = target / ".hldspec" / "sync" / "hldspec_state.json"
        self.assertTrue(state_path.exists())
        state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertNotEqual("NO_WORKSPACE", state["current_stage"])

    def test_status_and_review_surface_build_loop_trigger_artifacts(self) -> None:
        source = self.tmp_path / "HLD.md"
        target = self.tmp_path / "target-build-loop"
        source.write_text("# HLD\n", encoding="utf-8")
        start = self.run_start(source, target, comment="Build Loop prereqs")
        self.assertEqual(0, start.returncode, start.stderr + start.stdout)
        cont = self.run_facade("continue", target)
        self.assertEqual(2, cont.returncode, cont.stderr + cont.stdout)

        status = self.run_facade("status", target)
        self.assertEqual(0, status.returncode, status.stderr + status.stdout)
        self.assertIn("Workflow trigger: build_loop_prereqs", status.stdout)
        self.assertIn("Current state: INIT_PREREQS_BLOCKED / BUILD_LOOP_PREREQS", status.stdout)

        review = self.run_facade("review", target)
        self.assertEqual(0, review.returncode, review.stderr + review.stdout)
        self.assertIn(str(target / ".hldspec" / "sync" / "build_loop_prereqs_report.md"), review.stdout)

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

        self.assertNotEqual(0, result.returncode)
        self.assertIn("## Final Summary", result.stdout)
        self.assertIn("## SpecKit Readiness", result.stdout)
        self.assertIn("Real SpecKit init means `.specify/memory/` exists; `.specify/source/` alone is only the HLDspec mirror.", result.stdout)
        self.assertIn("Summary: ACTION", result.stdout)

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
            if command == "doctor":
                self.assertNotEqual(0, result.returncode)
            else:
                self.assertEqual(0, result.returncode, command + result.stderr + result.stdout)

        self.assertEqual(source_text, source.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
