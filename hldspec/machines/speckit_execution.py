"""SpecKit execution machine.

Drives the post-approval SpecKit workflow in strict dependency order:

  constitution → feature[0] → clarify → plan → tasks
               → feature[1] → clarify → plan → tasks
               → ...
               → ALL_COMPLETE

State is persisted in speckit_execution_state.json so runs can be
continued across sessions. The machine never invokes SpecKit itself —
it gates and orders; the human/orchestrator invokes SpecKit per
the instructions in each checkpoint.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hldspec.state_machine import (
    ArtifactRef,
    CheckpointKind,
    HumanQuestion,
    MachineContext,
    MachineResult,
    blocked_result,
    continue_result,
    done_result,
    error_result,
    human_checkpoint,
)

_STATE_FILE = "speckit_execution_state.json"

PHASE_CONSTITUTION = "CONSTITUTION"
PHASE_SPECIFY = "SPECIFY"
PHASE_CLARIFY = "CLARIFY"
PHASE_PLAN = "PLAN"
PHASE_CHECKLIST = "CHECKLIST"
PHASE_TASKS = "TASKS"
PHASE_ANALYZE = "ANALYZE"
PHASE_IMPLEMENT = "IMPLEMENT"
PHASE_DONE = "DONE"

# SpecKit's full per-feature ritual, making best use of the whole toolchain:
#   specify  -> create the spec (+ feature branch)
#   clarify  -> de-risk ambiguity before planning
#   plan     -> implementation plan
#   checklist-> quality checklist over the plan
#   tasks    -> actionable task breakdown
#   analyze  -> cross-artifact consistency gate before code
#   implement-> write the code
# Replaces the earlier [CLARIFY, PLAN, TASKS] order, which was missing SPECIFY
# (the entry step) and IMPLEMENT (the only step that produces code).
PHASE_ORDER = [
    PHASE_SPECIFY,
    PHASE_CLARIFY,
    PHASE_PLAN,
    PHASE_CHECKLIST,
    PHASE_TASKS,
    PHASE_ANALYZE,
    PHASE_IMPLEMENT,
    PHASE_DONE,
]
FIRST_PHASE = PHASE_SPECIFY

VALID_PHASE_DECISIONS = {"COMPLETE", "REWORK", "SKIP"}

# Bumped when the state schema / phase model changes. A live run refuses to
# trust state written under a different version (e.g. a simulated run that
# pre-filled decisions and all_complete), so stale state can't short-circuit
# real SpecKit invocation to a hollow "done".
STATE_VERSION = 2


class SpecKitExecutionMachine:
    """Drives post-approval SpecKit execution in dependency order.

    Two modes:
    - **gated** (``invoker=None``, default): returns a human checkpoint per
      phase and advances only when a decision is recorded in state. Used by
      tests and by human-in-the-loop runs.
    - **live** (``invoker`` provided): actually invokes SpecKit per phase via
      the injected :class:`SpecKitInvoker`, deriving phase completion from the
      invocation result. This is what turns prework into real specs and code.
    """

    name = "SpecKitExecutionMachine"

    def __init__(self, invoker: Any = None, constitution_summary: str = "") -> None:
        self.invoker = invoker
        self.constitution_summary = constitution_summary

    def run(self, context: MachineContext) -> MachineResult:
        if not context.workspace:
            return error_result(
                machine=self.name,
                state="NO_WORKSPACE",
                message="workspace is required",
            )

        sync = Path(context.workspace) / "firstrun" / ".specify" / "sync"
        queue_path = sync / "speckit_invocation_queue.json"
        state_path = sync / _STATE_FILE
        constitution_path = sync / "constitution_update_plan.json"

        if not queue_path.exists():
            return blocked_result(
                machine=self.name,
                state="QUEUE_MISSING",
                kind=CheckpointKind.SPECKIT_PREWORK_MISSING,
                blocking_reason="speckit_invocation_queue.json is missing. Run prework before SpecKit execution.",
                controlling_artifacts=(
                    ArtifactRef(path=str(queue_path), role="speckit_invocation_queue"),
                ),
                forbidden_actions=("Do not invoke SpecKit.", "Do not implement app code."),
            )

        queue = self._load_json(queue_path)
        features = queue.get("items", [])
        if not isinstance(features, list):
            return error_result(
                machine=self.name,
                state="QUEUE_INVALID",
                message="speckit_invocation_queue.json has no valid items list",
            )

        state = self._load_state(state_path)

        # Live mode refuses to trust state from a different schema version (e.g.
        # a prior simulated run that pre-filled decisions / all_complete). This
        # prevents stale state from short-circuiting real invocation.
        if self.invoker is not None and state.get("state_version") != STATE_VERSION:
            state = {}

        # --- Constitution phase ---
        if not state.get("constitution_approved"):
            return self._constitution_checkpoint(sync, constitution_path, state_path, state)

        # --- Feature phases ---
        active_index = state.get("active_feature_index", 0)

        if active_index >= len(features):
            self._write_state(state_path, {**state, "all_complete": True})
            return done_result(
                machine=self.name,
                state="ALL_FEATURES_COMPLETE",
                actions_run=("all features complete",),
            )

        feature = features[active_index]
        if not isinstance(feature, dict):
            return error_result(
                machine=self.name,
                state="FEATURE_INVALID",
                message=f"feature at index {active_index} is not a dict",
            )

        active_phase = state.get("active_phase", FIRST_PHASE)
        feature_id = str(feature.get("feature_id", f"feature-{active_index}"))
        feature_name = str(feature.get("feature_name", feature_id))

        if active_phase == PHASE_DONE:
            # Advance to next feature
            new_state = {
                **state,
                "active_feature_index": active_index + 1,
                "active_phase": FIRST_PHASE,
            }
            self._write_state(state_path, new_state)
            return continue_result(
                machine=self.name,
                state="FEATURE_ADVANCED",
                actions_run=(f"advanced past {feature_id}",),
            )

        return self._feature_phase_checkpoint(
            sync=sync,
            state_path=state_path,
            state=state,
            feature=feature,
            feature_id=feature_id,
            feature_name=feature_name,
            active_index=active_index,
            active_phase=active_phase,
            total_features=len(features),
        )

    def _constitution_checkpoint(
        self,
        sync: Path,
        constitution_path: Path,
        state_path: Path,
        state: dict[str, Any],
    ) -> MachineResult:
        question_id = "SPECKIT-CONSTITUTION-001"
        existing_state = state.get("constitution_decision", "TBD")

        if existing_state == "APPROVED":
            new_state = {**state, "constitution_approved": True}
            self._write_state(state_path, new_state)
            return continue_result(
                machine=self.name,
                state="CONSTITUTION_APPROVED",
                actions_run=("constitution approved",),
            )

        # Live mode: actually run /speckit-constitution.
        if self.invoker is not None:
            result = self.invoker.invoke("CONSTITUTION", self.constitution_summary or "Establish the project constitution from the prepared rules.")
            if result.verified:
                self._write_state(state_path, {**state, "constitution_approved": True, "constitution_decision": "APPROVED"})
                return continue_result(
                    machine=self.name,
                    state="CONSTITUTION_APPROVED",
                    actions_run=(f"invoked {result.skill}",),
                )
            reason = (
                f"/{result.skill} ran but produced no constitution artifact (hollow completion guard)."
                if result.ok
                else f"/{result.skill} failed (rc={result.returncode}): {result.stderr[-400:]}"
            )
            return blocked_result(
                machine=self.name,
                state="CONSTITUTION_INVOCATION_FAILED",
                kind=CheckpointKind.SPECKIT_PREWORK_APPROVAL_GATE,
                blocking_reason=reason,
                controlling_artifacts=(
                    ArtifactRef(path=str(constitution_path), role="constitution_update_plan", required=False),
                ),
                forbidden_actions=("Do not proceed to features until the constitution is established.",),
            )

        return human_checkpoint(
            machine=self.name,
            state="CONSTITUTION_PENDING",
            kind=CheckpointKind.SPECKIT_PREWORK_APPROVAL_GATE,
            blocking_reason=(
                "Constitution must be reviewed and applied before SpecKit is invoked for any feature. "
                "Review constitution_update_plan.json and apply the required rules to "
                ".specify/memory/constitution.md, then approve."
            ),
            questions=(
                HumanQuestion(
                    question_id=question_id,
                    title="Constitution ready for SpecKit",
                    question="Has the constitution been reviewed and applied to .specify/memory/constitution.md?",
                    options=("APPROVED", "NEEDS_REVIEW", "NEEDS_CHANGES"),
                    current_decision=existing_state,
                    blocking=True,
                ),
            ),
            controlling_artifacts=(
                ArtifactRef(path=str(constitution_path), role="constitution_update_plan", required=False),
            ),
            next_action=(
                "Apply constitution rules to .specify/memory/constitution.md, "
                f"then write {_STATE_FILE} with constitution_decision=APPROVED."
            ),
            forbidden_actions=(
                "Do not invoke SpecKit until constitution is approved.",
                "Do not implement app code.",
            ),
        )

    def _feature_phase_checkpoint(
        self,
        *,
        sync: Path,
        state_path: Path,
        state: dict[str, Any],
        feature: dict[str, Any],
        feature_id: str,
        feature_name: str,
        active_index: int,
        active_phase: str,
        total_features: int,
    ) -> MachineResult:
        question_id = f"SPECKIT-{feature_id}-{active_phase}-001"
        existing_decision = state.get(f"{feature_id}_{active_phase}_decision", "TBD")

        if existing_decision == "COMPLETE":
            next_phase = self._next_phase(active_phase)
            new_state = {**state, "active_phase": next_phase}
            self._write_state(state_path, new_state)
            return continue_result(
                machine=self.name,
                state=f"{active_phase}_COMPLETE",
                actions_run=(f"{feature_id} {active_phase} marked complete",),
            )

        # Live mode: actually invoke SpecKit for this phase.
        if self.invoker is not None:
            from hldspec.speckit_invoker import build_prompt

            prompt = build_prompt(active_phase, feature, self.constitution_summary)
            result = self.invoker.invoke(active_phase, prompt)
            if result.verified:
                next_phase = self._next_phase(active_phase)
                self._write_state(
                    state_path,
                    {**state, f"{feature_id}_{active_phase}_decision": "COMPLETE", "active_phase": next_phase},
                )
                return continue_result(
                    machine=self.name,
                    state=f"{active_phase}_COMPLETE",
                    actions_run=(f"invoked {result.skill} for {feature_id}",),
                )
            reason = (
                f"/{result.skill} ran for {feature_id} but produced no artifact "
                f"(hollow completion guard — exit 0 is not enough)."
                if result.ok
                else f"/{result.skill} failed for {feature_id} (rc={result.returncode}): {result.stderr[-400:]}"
            )
            return blocked_result(
                machine=self.name,
                state=f"{active_phase}_INVOCATION_FAILED",
                kind=CheckpointKind.SPECKIT_PREWORK_APPROVAL_GATE,
                blocking_reason=reason,
                controlling_artifacts=(
                    ArtifactRef(path=str(sync / _STATE_FILE), role="speckit_execution_state", required=False),
                ),
                forbidden_actions=("Do not advance past a failed SpecKit phase.",),
            )

        depends_on = feature.get("depends_on_features", [])
        source_sections = feature.get("source_hld_sections", [])
        position = f"{active_index + 1}/{total_features}"

        speckit_instruction = self._phase_instruction(
            active_phase, feature_id, feature_name,
            feature.get("speckit_specify_input", ""),
        )

        return human_checkpoint(
            machine=self.name,
            state=f"{active_phase}_PENDING",
            kind=CheckpointKind.SPECKIT_PREWORK_APPROVAL_GATE,
            blocking_reason=(
                f"Feature {position}: {feature_name} [{feature_id}] — phase {active_phase}.\n"
                + (f"Depends on: {', '.join(str(d) for d in depends_on)}.\n" if depends_on else "")
                + (f"Source HLD sections: {', '.join(str(s) for s in source_sections)}.\n" if source_sections else "")
                + speckit_instruction
            ),
            questions=(
                HumanQuestion(
                    question_id=question_id,
                    title=f"{feature_id} {active_phase}",
                    question=f"Is the {active_phase} phase for {feature_name} complete and approved?",
                    options=("COMPLETE", "REWORK", "SKIP"),
                    current_decision=existing_decision,
                    blocking=True,
                ),
            ),
            controlling_artifacts=(
                ArtifactRef(
                    path=str(sync / "speckit_invocation_queue.json"),
                    role="speckit_invocation_queue",
                ),
                ArtifactRef(
                    path=str(sync / _STATE_FILE),
                    role="speckit_execution_state",
                    required=False,
                ),
            ),
            next_action=(
                f"Run SpecKit for {active_phase} phase of {feature_name}, then "
                f"write {_STATE_FILE} with {feature_id}_{active_phase}_decision=COMPLETE."
            ),
            forbidden_actions=(
                f"Do not advance to {self._next_phase(active_phase)} before {active_phase} is approved.",
                "Do not implement app code before tasks are approved.",
                "Do not skip dependency order.",
            ),
        )

    @staticmethod
    def _next_phase(current: str) -> str:
        try:
            idx = PHASE_ORDER.index(current)
            return PHASE_ORDER[idx + 1] if idx + 1 < len(PHASE_ORDER) else PHASE_DONE
        except ValueError:
            return PHASE_DONE

    @staticmethod
    def _phase_instruction(phase: str, feature_id: str, feature_name: str, speckit_input: str) -> str:
        skill = {
            PHASE_SPECIFY: "speckit-specify",
            PHASE_CLARIFY: "speckit-clarify",
            PHASE_PLAN: "speckit-plan",
            PHASE_CHECKLIST: "speckit-checklist",
            PHASE_TASKS: "speckit-tasks",
            PHASE_ANALYZE: "speckit-analyze",
            PHASE_IMPLEMENT: "speckit-implement",
        }.get(phase)
        if skill:
            cmd = f"/{skill} {speckit_input or feature_id}"
            return f"Run SpecKit {phase.lower()}: `{cmd}`"
        return f"Complete {phase} for {feature_name}."

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_state(self, path: Path) -> dict[str, Any]:
        return self._load_json(path)

    @staticmethod
    def _write_state(path: Path, state: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        stamped = {**state, "state_version": STATE_VERSION}
        path.write_text(json.dumps(stamped, indent=2, sort_keys=True) + "\n", encoding="utf-8")
