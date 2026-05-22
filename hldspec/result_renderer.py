from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from hldspec.state_machine import (
    ArtifactRef,
    Checkpoint,
    HumanQuestion,
    MachineResult,
    MachineStatus,
)


STANDARD_SECTIONS = (
    "Current checkpoint:",
    "Blocking reason:",
    "Human decision needed:",
    "Controlling artifacts:",
    "Continuation protocol:",
    "What is not modified / not invoked:",
)


DEFAULT_FORBIDDEN_ACTIONS = (
    "Do not modify the source HLD unless explicitly approved.",
    "Do not invoke SpecKit unless the approval gate is approved.",
    "Do not implement app code at this checkpoint.",
)


def _artifact_lines(artifacts: Iterable[ArtifactRef]) -> list[str]:
    lines: list[str] = []
    for artifact in artifacts:
        required = "required" if artifact.required else "optional"
        lines.append(f"- {artifact.path} ({artifact.role}, {required})")
    return lines or ["- none"]


def _question_lines(questions: Iterable[HumanQuestion]) -> tuple[list[str], list[str]]:
    open_lines: list[str] = []
    answered_lines: list[str] = []

    for question in questions:
        target = open_lines if question.blocking and question.current_decision == "TBD" else answered_lines
        if target is open_lines:
            target.extend(
                [
                    f"{question.question_id} - {question.title}",
                    f"Question: {question.question}",
                    "Options: " + ", ".join(question.options),
                    "Current human decision: TBD",
                    "",
                ]
            )
        else:
            target.append(f"- {question.question_id} - {question.title} -> {question.current_decision}")

    return open_lines, answered_lines


def render_checkpoint(checkpoint: Checkpoint | None) -> str:
    if checkpoint is None:
        return "\n".join(
            [
                "Current checkpoint: none",
                "",
                "Blocking reason:",
                "- none",
                "",
                "Human decision needed:",
                "- none",
                "",
                "Controlling artifacts:",
                "- none",
                "",
                "Continuation protocol:",
                "- none",
                "",
                "What is not modified / not invoked:",
                *[f"- {item}" for item in DEFAULT_FORBIDDEN_ACTIONS],
            ]
        )

    open_questions, answered_questions = _question_lines(checkpoint.human_questions)
    forbidden = checkpoint.forbidden_actions or DEFAULT_FORBIDDEN_ACTIONS

    lines = [
        f"Current checkpoint: {checkpoint.kind.value}",
        "",
        "Blocking reason:",
        f"- {checkpoint.blocking_reason}",
        "",
        "Human decision needed:",
    ]

    if open_questions:
        lines.extend(open_questions)
        lines.extend(
            [
                "Answer format:",
                "- Pick one listed option for each open question.",
                "- Do not answer generic OK/continue.",
            ]
        )
    else:
        lines.append("- none")

    if answered_questions:
        lines.extend(["", "Already answered decisions:"])
        lines.extend(answered_questions)

    lines.extend(
        [
            "",
            "Controlling artifacts:",
            *_artifact_lines(checkpoint.controlling_artifacts),
            "",
            "Continuation protocol:",
            f"- {checkpoint.next_action or 'none'}",
            "",
            "What is not modified / not invoked:",
            *[f"- {item}" for item in forbidden],
        ]
    )

    return "\n".join(lines)


def render_machine_result(result: MachineResult) -> str:
    lines = [
        f"Machine: {result.machine}",
        f"State: {result.state}",
        f"Status: {result.status.value}",
        f"Exit code: {int(result.exit_code())}",
        "",
    ]

    if result.actions_run:
        lines.extend(["Actions run:", *[f"- {item}" for item in result.actions_run], ""])

    if result.artifacts_written:
        lines.extend(["Artifacts written:", *_artifact_lines(result.artifacts_written), ""])

    if result.errors:
        lines.extend(["Errors:", *[f"- {item}" for item in result.errors], ""])

    lines.append(render_checkpoint(result.checkpoint))
    return "\n".join(lines).rstrip() + "\n"


def machine_result_to_dict(result: MachineResult) -> dict[str, object]:
    data = asdict(result)
    data["status"] = result.status.value
    data["exit_code"] = int(result.exit_code())
    data["requires_human"] = result.requires_human()

    checkpoint = result.checkpoint
    if checkpoint is not None:
        data["checkpoint"]["kind"] = checkpoint.kind.value

    return data
