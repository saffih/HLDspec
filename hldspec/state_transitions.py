"""State transition table — the canonical source of truth for machine states.

Machines implement these transitions; docs are generated from this table.
"""
from __future__ import annotations
from dataclasses import dataclass, field


@dataclass
class StateTransition:
    from_state: str
    event: str
    guard: str             # precondition that must be true
    action: str            # what the machine does
    output_state: str
    forbidden_actions: list[str] = field(default_factory=list)
    required_artifacts: list[str] = field(default_factory=list)
    notes: str = ""


# Canonical HLDspec state transitions
TRANSITIONS: list[StateTransition] = [
    StateTransition(
        from_state="NO_WORKSPACE",
        event="run",
        guard="workspace directory exists",
        action="initialize workspace, run first_run_readonly.sh",
        output_state="HLD_CONVERSION_DECISIONS",
        forbidden_actions=["Do not modify source HLD", "Do not invoke SpecKit"],
        required_artifacts=["HLD.raw.md"],
    ),
    StateTransition(
        from_state="HLD_CONVERSION_DECISIONS",
        event="all_questions_answered",
        guard="no TBD questions in hld_conversion_decision_queue.json",
        action="apply conversion decisions to workspace HLD",
        output_state="FIRST_RUN_PENDING",
        forbidden_actions=["Do not modify source HLD"],
        required_artifacts=["hld_conversion_decision_queue.json"],
    ),
    StateTransition(
        from_state="FIRST_RUN_PENDING",
        event="first_run_complete",
        guard="spec_build_plan.json and spec_build_plan_review.md exist",
        action="review spec build plan quality",
        output_state="SPEC_BUILD_PLAN_GATE",
        forbidden_actions=["Do not invoke SpecKit"],
        required_artifacts=["spec_build_plan.json", "spec_build_plan_review.md"],
    ),
    StateTransition(
        from_state="SPEC_BUILD_PLAN_GATE",
        event="plan_green",
        guard="plan_quality.decision == PASS, KEEP_PLAN, no conflicts, continue_true",
        action="proceed to prework generation",
        output_state="SPECKIT_PREWORK_MISSING",
        forbidden_actions=["Do not invoke SpecKit"],
        required_artifacts=["spec_build_plan.json"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="prework_generated",
        guard="speckit_prework_quality_review.json exists",
        action="run prework quality gate",
        output_state="SPECKIT_PREWORK_APPROVAL_GATE",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_quality_review.json", "speckit_prework_package.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_APPROVAL_GATE",
        event="human_approved",
        guard="prework quality PASS, no REWORK_REQUIRED",
        action="advance to SpecKit execution",
        output_state="SPECKIT_EXECUTION",
        forbidden_actions=["Do not implement app code"],
        required_artifacts=["speckit_invocation_queue.json"],
    ),
    StateTransition(
        from_state="SPECKIT_EXECUTION",
        event="constitution_approved",
        guard="constitution_decision == APPROVED in execution state",
        action="begin first feature",
        output_state="FEATURE_CLARIFY",
        forbidden_actions=["Do not skip dependency order"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="FEATURE_CLARIFY",
        event="clarify_complete",
        guard="feature clarify phase approved",
        action="advance to plan phase",
        output_state="FEATURE_PLAN",
        forbidden_actions=["Do not start plan before clarify complete"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="FEATURE_PLAN",
        event="plan_complete",
        guard="feature plan phase approved",
        action="advance to tasks phase",
        output_state="FEATURE_TASKS",
        forbidden_actions=["Do not implement before tasks approved"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="FEATURE_TASKS",
        event="tasks_complete",
        guard="feature tasks phase approved",
        action="advance to next feature or done",
        output_state="FEATURE_DONE",
        forbidden_actions=["Do not implement app code before tasks approved"],
        required_artifacts=["speckit_execution_state.json"],
    ),
]


def transitions_from(state: str) -> list[StateTransition]:
    return [t for t in TRANSITIONS if t.from_state == state]


def all_states() -> list[str]:
    states = set()
    for t in TRANSITIONS:
        states.add(t.from_state)
        states.add(t.output_state)
    return sorted(states)
