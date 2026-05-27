"""Real SpecKit invocation layer.

HLDspec's value is preparing ordered, bite-sized, gap-filled inputs. This
module is what finally *spends* them: it drives the GitHub SpecKit slash
commands through a headless `claude` agent in the implementation project,
turning HLDspec's prework into actual specs, plans, tasks, and code.

The phase -> skill map mirrors SpecKit's own ritual:

    CONSTITUTION -> /speckit-constitution
    SPECIFY      -> /speckit-specify     (creates the feature branch + spec)
    PLAN         -> /speckit-plan
    TASKS        -> /speckit-tasks
    IMPLEMENT    -> /speckit-implement   (writes code)

The runner is injectable so the wiring can be tested without spawning a
real agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from hldspec.command_runner import CommandResult, CommandRunner

# HLDspec phase -> SpecKit skill name. Covers SpecKit's full toolchain, not
# just the core four: clarify de-risks ambiguity before planning; checklist and
# analyze are quality gates around tasks.
PHASE_SKILL = {
    "CONSTITUTION": "speckit-constitution",
    "SPECIFY": "speckit-specify",
    "CLARIFY": "speckit-clarify",
    "PLAN": "speckit-plan",
    "CHECKLIST": "speckit-checklist",
    "TASKS": "speckit-tasks",
    "ANALYZE": "speckit-analyze",
    "IMPLEMENT": "speckit-implement",
}

# Per-phase model routing (weakest sufficient model per operation), keyed to the
# AGENTS.md tiers. Pick the right agent for each operation so end-to-end driving
# is cost-worthy: mechanical phases run cheap, reasoning/code/governance run strong.
#   CONSTITUTION -> CRITICAL (Opus)   governs architecture/contracts
#   SPECIFY      -> DEFAULT  (Sonnet) spec drafting
#   CLARIFY      -> DEFAULT  (Sonnet) structured ambiguity questions
#   PLAN         -> DEFAULT  (Sonnet) implementation planning
#   CHECKLIST    -> ROUTINE  (Haiku)  mechanical checklist generation
#   TASKS        -> ROUTINE  (Haiku)  mechanical task breakdown
#   ANALYZE      -> CRITICAL (Opus)   cross-artifact consistency verdict
#   IMPLEMENT    -> STRONG   (Sonnet) bounded module work + tests
PHASE_MODEL = {
    "CONSTITUTION": "opus",
    "SPECIFY": "sonnet",
    "CLARIFY": "sonnet",
    "PLAN": "sonnet",
    "CHECKLIST": "haiku",
    "TASKS": "haiku",
    "ANALYZE": "opus",
    "IMPLEMENT": "sonnet",
}


# Phases expected to produce on-disk artifacts (spec/plan/checklist/tasks/code).
# CLARIFY and ANALYZE are reasoning/Q&A steps that legitimately may change
# nothing, so they are NOT required to produce artifacts.
ARTIFACT_PHASES = frozenset({"CONSTITUTION", "SPECIFY", "PLAN", "CHECKLIST", "TASKS", "IMPLEMENT"})


@dataclass(frozen=True)
class InvocationResult:
    phase: str
    skill: str
    returncode: int
    ok: bool
    stdout: str
    stderr: str
    produced_artifacts: bool = False  # did the project tree actually change?

    @property
    def verified(self) -> bool:
        """True only if the command succeeded AND (for artifact phases) it
        actually changed the project. This is the anti-hollow-completion gate:
        exit code 0 is necessary but not sufficient."""
        if not self.ok:
            return False
        if self.phase in ARTIFACT_PHASES:
            return self.produced_artifacts
        return True


def _git_signature(project_dir: Path, runner: CommandRunner) -> str:
    """A cheap fingerprint of the project's committed + working-tree state.

    Changes if SpecKit commits (HEAD moves) or leaves uncommitted edits
    (porcelain status differs). Used to detect whether a phase did anything.
    """
    head = runner.run(["git", "rev-parse", "HEAD"], cwd=project_dir, capture=True)
    status = runner.run(["git", "status", "--porcelain"], cwd=project_dir, capture=True)
    return f"{head.stdout.strip()}|{status.stdout.strip()}"


class SpecKitInvoker:
    """Drives SpecKit slash commands via a headless claude agent."""

    def __init__(
        self,
        project_dir: str | Path,
        *,
        runner: Optional[CommandRunner] = None,
        agent_cmd: str = "claude",
        skip_permissions: bool = True,
        extra_args: Optional[list[str]] = None,
        phase_models: Optional[dict[str, str]] = None,
        route_models: bool = True,
        change_detector: Optional[Any] = None,
    ) -> None:
        self.project_dir = Path(project_dir)
        self.runner = runner or CommandRunner()
        self.agent_cmd = agent_cmd
        self.skip_permissions = skip_permissions
        self.extra_args = list(extra_args or [])
        self.phase_models = {**PHASE_MODEL, **(phase_models or {})}
        self.route_models = route_models
        # change_detector(project_dir) -> signature string. Default: git state.
        self.change_detector = change_detector or (
            lambda d: _git_signature(d, self.runner)
        )

    def _command(self, skill: str, prompt: str, model: Optional[str]) -> list[str]:
        cmd = [self.agent_cmd, "--print"]
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        if model:
            cmd.extend(["--model", model])
        cmd.extend(self.extra_args)
        cmd.append(f"/{skill} {prompt}")
        return cmd

    def invoke(self, phase: str, prompt: str) -> InvocationResult:
        skill = PHASE_SKILL.get(phase)
        if skill is None:
            return InvocationResult(phase, "", 2, False, "", f"no SpecKit skill for phase {phase}")
        model = self.phase_models.get(phase) if self.route_models else None

        before = self._safe_signature()
        result: CommandResult = self.runner.run(
            self._command(skill, prompt, model), cwd=self.project_dir, capture=True
        )
        after = self._safe_signature()

        return InvocationResult(
            phase=phase,
            skill=skill,
            returncode=result.returncode,
            ok=result.returncode == 0,
            stdout=result.stdout,
            stderr=result.stderr,
            produced_artifacts=(before is not None and after is not None and before != after),
        )

    def _safe_signature(self) -> Optional[str]:
        try:
            return self.change_detector(self.project_dir)
        except Exception:
            return None


def build_prompt(phase: str, feature: dict[str, Any], constitution_summary: str = "") -> str:
    """Compose a rich, self-contained SpecKit prompt from HLDspec prework.

    Deliberately does NOT reference the source HLD: once HLDspec has run, the
    HLD is consumed and SpecKit works only from these prepared artifacts.
    """
    feature_id = str(feature.get("feature_id", "")).strip()
    feature_name = str(feature.get("feature_name", feature_id)).strip()
    base = (feature.get("speckit_specify_input") or f"Build {feature_name}.").strip()

    lines = [base, ""]

    arch = feature.get("architecture_context") or {}
    contracts = arch.get("contracts") or []
    interfaces = arch.get("interfaces") or []
    data_objects = arch.get("data_objects") or []
    if contracts or interfaces or data_objects:
        lines.append("Architecture context (from HLDspec extraction):")
        for c in contracts[:6]:
            lines.append(
                f"- Contract {c.get('contract_id', '')}: {c.get('provider', '?')} provides "
                f"'{c.get('contract_name', '')}' to {c.get('consumer', '?')}; "
                f"source of truth: {c.get('source_of_truth', 'n/a')}."
            )
        for d in data_objects[:6]:
            lines.append(
                f"- Data object '{d.get('data_object', '')}' owned by {d.get('owner', '?')} "
                f"(SoT: {d.get('source_of_truth', 'n/a')})."
            )
        lines.append("")

    product = feature.get("product_context") or {}
    stories = product.get("user_stories") or product.get("stories") or []
    if stories:
        lines.append("Product context:")
        for s in stories[:5]:
            lines.append(f"- {s if isinstance(s, str) else s.get('story', s)}")
        lines.append("")

    if constitution_summary:
        lines.append("Constitution constraints that govern this work:")
        lines.append(constitution_summary.strip())
        lines.append("")

    if phase == "IMPLEMENT":
        lines.append(
            "Implement against the existing project code; keep changes surgical, "
            "match existing style, and add tests."
        )

    return "\n".join(lines).strip() + "\n"
