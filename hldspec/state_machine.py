from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class MachineStatus(str, Enum):
    CONTINUE = "CONTINUE"
    STOP_CHECKPOINT = "STOP_CHECKPOINT"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    ERROR = "ERROR"


class CheckpointKind(str, Enum):
    HLD_CONVERSION_DECISIONS = "HLD_CONVERSION_DECISIONS"
    SPEC_BUILD_PLAN_CHECKPOINT = "SPEC_BUILD_PLAN_CHECKPOINT"
    SPECKIT_PREWORK_MISSING = "SPECKIT_PREWORK_MISSING"
    SPECKIT_PREWORK_REWORK = "SPECKIT_PREWORK_REWORK"
    SPECKIT_PREWORK_APPROVAL_GATE = "SPECKIT_PREWORK_APPROVAL_GATE"
    SOURCE_UPDATE_APPROVAL = "SOURCE_UPDATE_APPROVAL"


class ExitCode(int, Enum):
    OK = 0
    TOOL_ERROR = 1
    HUMAN_CHECKPOINT_REQUIRED = 2
    GATE_BLOCKED = 3
    UNSAFE_ACTION = 4


@dataclass(frozen=True)
class ArtifactRef:
    path: str
    role: str
    required: bool = True


@dataclass(frozen=True)
class RunSkepticStatus:
    status: str = "NOT_RUN"  # PASS | ACTION | CONFLICT | NOT_RUN
    evidence: tuple[ArtifactRef, ...] = ()
    next_safe_action: str = ""


@dataclass(frozen=True)
class HumanQuestion:
    question_id: str
    title: str
    question: str
    options: tuple[str, ...]
    current_decision: str = "TBD"
    blocking: bool = True


@dataclass(frozen=True)
class Checkpoint:
    kind: CheckpointKind
    blocking_reason: str
    human_questions: tuple[HumanQuestion, ...] = ()
    controlling_artifacts: tuple[ArtifactRef, ...] = ()
    next_action: str = ""
    forbidden_actions: tuple[str, ...] = ()

    def open_questions(self) -> tuple[HumanQuestion, ...]:
        return tuple(
            question
            for question in self.human_questions
            if question.blocking and question.current_decision == "TBD"
        )

    def answered_questions(self) -> tuple[HumanQuestion, ...]:
        return tuple(
            question
            for question in self.human_questions
            if question.current_decision != "TBD"
        )

    def has_open_questions(self) -> bool:
        return bool(self.open_questions())


@dataclass(frozen=True)
class MachineResult:
    machine: str
    state: str
    status: MachineStatus
    checkpoint: Checkpoint | None = None
    actions_run: tuple[str, ...] = ()
    artifacts_written: tuple[ArtifactRef, ...] = ()
    errors: tuple[str, ...] = ()
    runskeptic: RunSkepticStatus = field(default_factory=RunSkepticStatus)

    def exit_code(self) -> ExitCode:
        if self.status in {MachineStatus.DONE, MachineStatus.CONTINUE}:
            return ExitCode.OK
        if self.status == MachineStatus.STOP_CHECKPOINT:
            return ExitCode.HUMAN_CHECKPOINT_REQUIRED
        if self.status == MachineStatus.BLOCKED:
            return ExitCode.GATE_BLOCKED
        if self.status == MachineStatus.ERROR:
            return ExitCode.TOOL_ERROR
        return ExitCode.TOOL_ERROR

    def requires_human(self) -> bool:
        return self.status == MachineStatus.STOP_CHECKPOINT


@dataclass(frozen=True)
class MachineContext:
    repo_root: str
    source_hld: str | None = None
    workspace: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)


class StateMachine(Protocol):
    name: str

    def run(self, context: MachineContext) -> MachineResult:
        ...


def human_checkpoint(
    *,
    machine: str,
    state: str,
    kind: CheckpointKind,
    blocking_reason: str,
    questions: tuple[HumanQuestion, ...],
    controlling_artifacts: tuple[ArtifactRef, ...],
    next_action: str,
    forbidden_actions: tuple[str, ...],
    actions_run: tuple[str, ...] = (),
    artifacts_written: tuple[ArtifactRef, ...] = (),
    runskeptic: RunSkepticStatus | None = None,
) -> MachineResult:
    return MachineResult(
        machine=machine,
        state=state,
        status=MachineStatus.STOP_CHECKPOINT,
        checkpoint=Checkpoint(
            kind=kind,
            blocking_reason=blocking_reason,
            human_questions=questions,
            controlling_artifacts=controlling_artifacts,
            next_action=next_action,
            forbidden_actions=forbidden_actions,
        ),
        actions_run=actions_run,
        artifacts_written=artifacts_written,
        runskeptic=runskeptic or RunSkepticStatus(),
    )


def blocked_result(
    *,
    machine: str,
    state: str,
    kind: CheckpointKind,
    blocking_reason: str,
    controlling_artifacts: tuple[ArtifactRef, ...] = (),
    forbidden_actions: tuple[str, ...] = (),
    errors: tuple[str, ...] = (),
    runskeptic: RunSkepticStatus | None = None,
) -> MachineResult:
    return MachineResult(
        machine=machine,
        state=state,
        status=MachineStatus.BLOCKED,
        checkpoint=Checkpoint(
            kind=kind,
            blocking_reason=blocking_reason,
            controlling_artifacts=controlling_artifacts,
            forbidden_actions=forbidden_actions,
        ),
        errors=errors,
        runskeptic=runskeptic or RunSkepticStatus(),
    )


def continue_result(
    *,
    machine: str,
    state: str,
    actions_run: tuple[str, ...] = (),
    artifacts_written: tuple[ArtifactRef, ...] = (),
    runskeptic: RunSkepticStatus | None = None,
) -> MachineResult:
    return MachineResult(
        machine=machine,
        state=state,
        status=MachineStatus.CONTINUE,
        actions_run=actions_run,
        artifacts_written=artifacts_written,
        runskeptic=runskeptic or RunSkepticStatus(),
    )


def done_result(
    *,
    machine: str,
    state: str,
    actions_run: tuple[str, ...] = (),
    artifacts_written: tuple[ArtifactRef, ...] = (),
    runskeptic: RunSkepticStatus | None = None,
) -> MachineResult:
    return MachineResult(
        machine=machine,
        state=state,
        status=MachineStatus.DONE,
        actions_run=actions_run,
        artifacts_written=artifacts_written,
        runskeptic=runskeptic or RunSkepticStatus(),
    )


def error_result(
    *,
    machine: str,
    state: str,
    message: str,
    runskeptic: RunSkepticStatus | None = None,
) -> MachineResult:
    return MachineResult(
        machine=machine,
        state=state,
        status=MachineStatus.ERROR,
        errors=(message,),
        runskeptic=runskeptic or RunSkepticStatus(),
    )
