"""Agent-first user-interface contract.

The public HLDspec interface is a one-line instruction to an agent, not direct
script execution. The agent uses HLDspec's command/tool surface internally and
reports STATUS, blockers, evidence, and the next safe action.

Two kinds of checks:

* Negative/stale-behavior: these fail on the pre-patch README wording
  ("The public facade is one script", "needs only two commands", script paths
  presented as the main workflow). They exist so the drift cannot return.
* Positive-contract: the agent one-liner is the primary entry point; scripts are
  documented as internal/manual/debug/fallback tooling; the canonical command
  surface is described as an internal tool surface, not the primary human UX.

Placement is checked, not just substrings: the "Main user workflow" section body
must lead with the agent one-liner and contain no script paths.
"""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
USER_RUN_MODEL = ROOT / "docs" / "USER_RUN_MODEL.md"
TERMINOLOGY = ROOT / "docs" / "HLDSPEC_TERMINOLOGY_AND_FLOW.md"
SCORECARD = ROOT / "docs" / "PRODUCT_READINESS.md"

# The single copy-ready instruction a user gives an agent. Must appear verbatim
# in README and USER_RUN_MODEL.
AGENT_ONE_LINER = (
    "Use HLDspec with source HLD: <path-to-HLD.md> and target project: "
    "<path-to-target>. Prepare the target, check SpecKit readiness, and report "
    "STATUS, blockers, evidence, and next safe action. Do not implement or run "
    "SpecKit unless HLDspec says it is safe."
)

MAIN_WORKFLOW_HEADER = "## Main user workflow"
INTERNAL_SURFACE_HEADER = "### Internal command/tool surface"

# Tokens that must never appear in the primary user path. Bare "script" is fine
# (prose), but an actual invocation path is not.
SCRIPT_PATH_TOKENS = ("python3 scripts/", "scripts/hldspec_agent_session.py")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _section_body(text: str, header: str) -> str:
    """Body lines between `header` and the next markdown ## or ### header."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith(header):
            start = i + 1
            break
    if start is None:
        raise AssertionError(f"header not found: {header!r}")
    body: list[str] = []
    for ln in lines[start:]:
        if ln.startswith("## ") or ln.startswith("### "):
            break
        body.append(ln)
    return "\n".join(body)


class AgentFirstInterfaceTests(unittest.TestCase):
    # --- Negative / stale-behavior (fail on pre-patch README) -------------

    def test_readme_drops_public_facade_is_one_script(self) -> None:
        self.assertNotIn(
            "public facade is one script",
            _read(README),
            "README must not call a single script the public facade",
        )

    def test_user_run_model_has_no_one_script_facade(self) -> None:
        self.assertNotIn("public facade is one script", _read(USER_RUN_MODEL))

    def test_readme_drops_two_commands_claim(self) -> None:
        readme = _read(README)
        self.assertNotIn(
            "needs only two commands",
            readme,
            "README must not present 'two commands' as the user entry point",
        )
        self.assertNotIn("only two commands", readme)

    def test_main_workflow_body_has_no_script_paths(self) -> None:
        # Placement check: script invocations must not sit in the primary path.
        body = _section_body(_read(README), MAIN_WORKFLOW_HEADER)
        for token in SCRIPT_PATH_TOKENS:
            with self.subTest(token=token):
                self.assertNotIn(
                    token,
                    body,
                    f"{token!r} must not appear under '{MAIN_WORKFLOW_HEADER}'",
                )

    # --- Positive contract -------------------------------------------------

    def test_main_workflow_leads_with_agent_one_liner(self) -> None:
        body = _section_body(_read(README), MAIN_WORKFLOW_HEADER)
        self.assertIn(
            AGENT_ONE_LINER,
            body,
            "the agent one-liner must be the primary user entry point",
        )

    def test_readme_marks_scripts_as_internal_fallback(self) -> None:
        readme = _read(README)
        self.assertIn(INTERNAL_SURFACE_HEADER, readme)
        lower = readme.lower()
        self.assertIn("internal", lower)
        self.assertIn("fallback", lower)

    def test_script_commands_live_under_internal_surface(self) -> None:
        # The script invocation surface must live under the internal/fallback
        # section, not the main workflow.
        internal_body = _section_body(_read(README), INTERNAL_SURFACE_HEADER)
        self.assertIn("scripts/hldspec_agent_session.py", internal_body)

    def test_user_run_model_public_ux_is_agent_first(self) -> None:
        text = _read(USER_RUN_MODEL)
        self.assertIn(AGENT_ONE_LINER, text)
        lower = text.lower()
        self.assertIn("agent-first", lower)
        self.assertIn("one-line instruction", lower)

    def test_terminology_distinguishes_public_interface_from_command_surface(self) -> None:
        text = _read(TERMINOLOGY)
        self.assertIn("Public HLDspec Interface", text)
        self.assertIn("not the primary human UX", text)
        # The canonical command list stays, described as a tool surface.
        self.assertIn("HLDspec Product Facade", text)
        self.assertIn("command/tool surface", text.lower())

    def test_scorecard_ties_standalone_to_agent_one_liner(self) -> None:
        text = _read(SCORECARD)
        self.assertIn("agent one-liner", text.lower())
        # Do not weaken the production honesty.
        self.assertIn("Production-ready: NO", text)


if __name__ == "__main__":
    unittest.main()
