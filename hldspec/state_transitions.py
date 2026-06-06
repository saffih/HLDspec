"""State transition vocabulary for the HLDspec project checkpoint flow.

Machines, state builders, and operator reports emit states represented here.
Docs and reviews may use this table as a compact map of the public checkpoint
vocabulary; executable behavior still lives in the machines and scripts.
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
        action="initialize workspace and prepare the working HLD copy",
        output_state="HLD_CONVERSION_DECISIONS",
        forbidden_actions=["Do not modify source HLD", "Do not invoke SpecKit"],
        required_artifacts=["targetHLD/raw/HLD.raw.md", "targetHLD/HLD.md"],
        notes="A missing workspace may also stop at NO_WORKSPACE until the target can be created.",
    ),
    StateTransition(
        from_state="NO_WORKSPACE",
        event="check_hld_missing",
        guard="check HLD was requested but the workspace HLD is missing",
        action="stop before full SpecKit Preparation",
        output_state="HLD_READINESS_HLD_MISSING",
        forbidden_actions=["Do not invoke SpecKit", "Do not initialize Build Loop"],
        required_artifacts=["targetHLD/HLD.md"],
    ),
    StateTransition(
        from_state="NO_WORKSPACE",
        event="check_hld_ready",
        guard="check HLD cross-examination has no blocking readiness questions",
        action="report HLD readiness only; full SpecKit Preparation has not run",
        output_state="HLD_READY",
        forbidden_actions=["Do not invoke SpecKit", "Do not initialize Build Loop"],
        required_artifacts=["hld_cross_examination.json", "hld_readiness_check.json"],
    ),
    StateTransition(
        from_state="NO_WORKSPACE",
        event="check_hld_ready_with_actions",
        guard="check HLD found accepted-risk actions that can move forward only with explicit follow-up",
        action="report readiness with actions; full SpecKit Preparation has not run",
        output_state="HLD_READY_WITH_ACTIONS",
        forbidden_actions=["Do not invoke SpecKit", "Do not initialize Build Loop"],
        required_artifacts=["hld_cross_examination.json", "hld_readiness_check.json"],
    ),
    StateTransition(
        from_state="NO_WORKSPACE",
        event="check_hld_blocked",
        guard="check HLD found unresolved or conflicting readiness decisions",
        action="stop for grouped HLD readiness questions",
        output_state="HLD_BLOCKED",
        forbidden_actions=["Do not invoke SpecKit", "Do not initialize Build Loop"],
        required_artifacts=["hld_cross_examination.json", "hld_readiness_check.json"],
    ),
    StateTransition(
        from_state="HLD_CONVERSION_DECISIONS",
        event="queue_missing",
        guard="working HLD is raw and hld_conversion_decision_queue.json is absent",
        action="block until the conversion decision queue exists",
        output_state="CONVERSION_QUEUE_MISSING",
        forbidden_actions=["Do not convert mechanically without a decision queue", "Do not invoke SpecKit"],
        required_artifacts=["hld_conversion_decision_queue.json"],
    ),
    StateTransition(
        from_state="HLD_CONVERSION_DECISIONS",
        event="open_questions",
        guard="blocking TBD questions exist in hld_conversion_decision_queue.json",
        action="stop for human conversion decisions",
        output_state="HLD_CONVERSION_DECISIONS",
        forbidden_actions=["Do not modify source HLD", "Do not invoke SpecKit"],
        required_artifacts=["hld_conversion_decision_queue.json", "hld_conversion_decision_queue.md"],
    ),
    StateTransition(
        from_state="HLD_CONVERSION_DECISIONS",
        event="legacy_open_questions",
        guard="legacy state builder found blocking TBD conversion decisions",
        action="stop at the legacy conversion checkpoint",
        output_state="CONVERSION_CHECKPOINT",
        forbidden_actions=["Do not modify source HLD", "Do not invoke SpecKit"],
        required_artifacts=["hld_conversion_decision_queue.json", "hld_conversion_decision_queue.md"],
    ),
    StateTransition(
        from_state="HLD_CONVERSION_DECISIONS",
        event="all_questions_answered",
        guard="no TBD questions in hld_conversion_decision_queue.json",
        action="apply conversion decisions to the workspace HLD only",
        output_state="WORKING_HLD_CONVERTED",
        forbidden_actions=["Do not modify source HLD"],
        required_artifacts=["hld_conversion_decision_queue.json"],
    ),
    StateTransition(
        from_state="CONVERSION_READY_TO_APPLY",
        event="conversion_applied",
        guard="raw HLD conversion decisions are answered",
        action="apply conversion decisions to the workspace HLD only",
        output_state="WORKING_HLD_CONVERTED",
        forbidden_actions=["Do not modify source HLD", "Do not invoke SpecKit"],
        required_artifacts=["hld_conversion_decision_queue.json"],
    ),
    StateTransition(
        from_state="WORKING_HLD_CONVERTED",
        event="first_run_complete",
        guard="spec_build_plan.json and spec_build_plan_review.md exist",
        action="review spec build plan quality",
        output_state="SPEC_BUILD_PLAN_GREEN",
        forbidden_actions=["Do not invoke SpecKit"],
        required_artifacts=["spec_build_plan.json", "spec_build_plan_review.md"],
    ),
    StateTransition(
        from_state="WORKING_HLD_CONVERTED",
        event="first_run_missing",
        guard="spec_build_plan.json or spec_build_plan_review.md is missing",
        action="run first_run_readonly.sh on the converted working HLD",
        output_state="FIRST_RUN_PENDING",
        forbidden_actions=["Do not invoke SpecKit"],
        required_artifacts=["targetHLD/HLD.md"],
    ),
    StateTransition(
        from_state="WORKING_HLD_CONVERTED",
        event="agent_session_prepared",
        guard="minimal HLDspec agent session was prepared and no bounded workflow trigger has run yet",
        action="continue the prepared HLDspec agent session",
        output_state="AGENT_SESSION_PREPARED",
        forbidden_actions=["Do not invoke SpecKit until Build Loop gates pass"],
        required_artifacts=[".hldspec/agent_session.json"],
    ),
    StateTransition(
        from_state="AGENT_SESSION_PREPARED",
        event="build_loop_prereqs_pass",
        guard="Build Loop prerequisite report is PASS",
        action="advance to real SpecKit init validation",
        output_state="INIT_PREREQS_READY",
        forbidden_actions=["Do not start specify before init and approval gates pass"],
        required_artifacts=["build_loop_prereqs_report.json"],
    ),
    StateTransition(
        from_state="AGENT_SESSION_PREPARED",
        event="build_loop_prereqs_blocked",
        guard="Build Loop prerequisite report is ACTION or CONFLICT",
        action="repair prerequisites before init",
        output_state="INIT_PREREQS_BLOCKED",
        forbidden_actions=["Do not run real SpecKit init"],
        required_artifacts=["build_loop_prereqs_report.json"],
    ),
    StateTransition(
        from_state="INIT_PREREQS_READY",
        event="speckit_init_validated",
        guard="real SpecKit workspace is initialized",
        action="validate initialized workspace and source mirror",
        output_state="WORKSPACE_INITIALIZED",
        forbidden_actions=["Do not start specify before post-init mirror sync"],
        required_artifacts=["build_loop_init_report.json", ".specify/memory/"],
    ),
    StateTransition(
        from_state="INIT_PREREQS_READY",
        event="speckit_init_blocked",
        guard="real SpecKit init validation failed",
        action="repair init command or workspace prerequisites",
        output_state="BUILD_LOOP_INIT_BLOCKED",
        forbidden_actions=["Do not start specify"],
        required_artifacts=["build_loop_init_report.json"],
    ),
    StateTransition(
        from_state="WORKSPACE_INITIALIZED",
        event="source_mirror_synced",
        guard="post-init `.specify/source/` mirror is current",
        action="prepare the readiness/operator state boundary",
        output_state="MIRROR_SYNCED",
        forbidden_actions=["Do not start specify before approval gate passes"],
        required_artifacts=[".specify/source/HLD.md"],
    ),
    StateTransition(
        from_state="MIRROR_SYNCED",
        event="source_freshness_blocked",
        guard="source HLD differs from the existing workspace HLD copy",
        action="reconcile the workspace HLD copy before Build Loop work",
        output_state="SOURCE_FRESHNESS_BLOCKED",
        forbidden_actions=["Do not promote derived artifacts"],
        required_artifacts=["source_freshness.json"],
    ),
    StateTransition(
        from_state="MIRROR_SYNCED",
        event="speckit_approval_missing",
        guard="operator is ready but SpecKit prework approval has not been recorded",
        action="stop until approval gate is satisfied",
        output_state="SPECKIT_APPROVAL_GATE_BLOCKED",
        forbidden_actions=["Do not start specify"],
        required_artifacts=["build_loop_ready_report.json"],
    ),
    StateTransition(
        from_state="WORKING_HLD_CONVERTED",
        event="plan_not_green",
        guard="spec build plan has conflicts, flagged specs, or missing required continue signal",
        action="stop for spec build plan decision",
        output_state="SPEC_BUILD_PLAN_CHECKPOINT",
        forbidden_actions=["Do not invoke SpecKit"],
        required_artifacts=["spec_build_plan.json", "spec_build_plan_review.md"],
    ),
    StateTransition(
        from_state="WORKING_HLD_CONVERTED",
        event="legacy_plan_not_green",
        guard="legacy state builder found a non-green spec build plan without an answerable queue",
        action="fix or decompose the spec build plan before prework",
        output_state="SPEC_BUILD_PLAN_BLOCKED",
        forbidden_actions=["Do not invoke SpecKit"],
        required_artifacts=["spec_build_plan.json", "spec_build_plan_review.md"],
    ),
    StateTransition(
        from_state="SPEC_BUILD_PLAN_GREEN",
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
        output_state="SPECKIT_PREWORK_READY_FOR_APPROVAL",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_quality_review.json", "speckit_prework_package.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="prework_rework_required",
        guard="quality review, RunSkeptic, engineering guidance, or freshness gate blocks promotion",
        action="rebuild or repair affected prework artifacts",
        output_state="SPECKIT_PREWORK_REWORK",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_quality_review.json", "speckit_prework_package.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="legacy_prework_rework_required",
        guard="legacy state builder found prework quality blockers",
        action="rebuild or repair affected prework artifacts",
        output_state="SPECKIT_PREWORK_REWORK_REQUIRED",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_quality_review.json", "speckit_prework_package.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="prework_runskeptic_rework",
        guard="RunSkeptic status is ACTION or CONFLICT",
        action="resolve RunSkeptic findings before invoking SpecKit",
        output_state="SPECKIT_PREWORK_RUNSKEPTIC_REWORK",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_quality_review.json", "speckit_prework_package.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="engineering_guidance_missing",
        guard="generated engineering_guidelines.md is missing",
        action="rebuild the HLDspec source package",
        output_state="SPECKIT_PREWORK_ENGINEERING_GUIDANCE_MISSING",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["engineering_guidelines.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="engineering_guidance_rework",
        guard="generated engineering_guidelines.md is invalid",
        action="repair the source package engineering guidance",
        output_state="SPECKIT_PREWORK_ENGINEERING_GUIDANCE_REWORK",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["engineering_guidelines.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_MISSING",
        event="prework_stale",
        guard="registered prework inputs are newer than generated outputs",
        action="rebuild stale prework artifacts",
        output_state="SPECKIT_PREWORK_STALE",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_quality_review.json", "speckit_prework_package.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_READY_FOR_APPROVAL",
        event="approval_required",
        guard="prework quality PASS and no rework blockers remain",
        action="stop for explicit human approval",
        output_state="SPECKIT_PREWORK_APPROVAL_GATE",
        forbidden_actions=["Do not invoke SpecKit until approval"],
        required_artifacts=["speckit_prework_package.md", "speckit_prework_quality_review.md"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_APPROVAL_GATE",
        event="human_approved",
        guard="prework quality PASS, no REWORK_REQUIRED",
        action="advance to SpecKit execution",
        output_state="SPECKIT_PREWORK_APPROVED",
        forbidden_actions=["Do not implement app code"],
        required_artifacts=["speckit_prework_approval.json"],
    ),
    StateTransition(
        from_state="SPECKIT_PREWORK_APPROVED",
        event="constitution_approved",
        guard="constitution_decision == APPROVED in execution state",
        action="begin first feature",
        output_state="READY_FOR_SPECIFY",
        forbidden_actions=["Do not skip dependency order"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="READY_FOR_SPECIFY",
        event="specify_started",
        guard="approved Run Card is available and all readiness gates remain PASS",
        action="run /speckit.specify through the approved proxy/run-card path",
        output_state="SPECIFY_ACTIVE",
        forbidden_actions=["Do not skip the approved Run Card"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="SPECIFY_ACTIVE",
        event="plan_started",
        guard="specify output is reviewed and accepted",
        action="run /speckit.plan through the approved proxy/run-card path",
        output_state="PLAN_ACTIVE",
        forbidden_actions=["Do not implement before tasks approved"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="PLAN_ACTIVE",
        event="tasks_started",
        guard="plan output is reviewed and accepted",
        action="run /speckit.tasks through the approved proxy/run-card path",
        output_state="TASKS_ACTIVE",
        forbidden_actions=["Do not implement app code before tasks approved"],
        required_artifacts=["speckit_execution_state.json"],
    ),
    StateTransition(
        from_state="TASKS_ACTIVE",
        event="tasks_complete",
        guard="tasks.md exists and task phase is reviewed",
        action="run /speckit.analyze before any implementation approval",
        output_state="ANALYZE_READY",
        forbidden_actions=["Do not implement app code before analyze and explicit approval"],
        required_artifacts=["speckit_execution_state.json", "tasks.md"],
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
