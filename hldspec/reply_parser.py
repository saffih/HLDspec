from __future__ import annotations

import json

from hldspec.state_machine import Checkpoint

_CONTINUE_SHORTHANDS = {"next", "ok", "continue"}


def _is_accept_option(option: str) -> bool:
    upper = option.upper()
    return "ACCEPT" in upper or "APPROVE" in upper


def parse_reply(reply: str, checkpoint: Checkpoint) -> str | None:
    normalised = reply.strip().lower()
    open_questions = checkpoint.open_questions()

    if normalised in _CONTINUE_SHORTHANDS:
        return "CONTINUE" if not open_questions else None

    if normalised == "accept all":
        mapping: dict[str, str] = {}
        for question in open_questions:
            match = next((opt for opt in question.options if _is_accept_option(opt)), None)
            if match is None:
                return None
            mapping[question.question_id] = match
        return json.dumps(mapping)

    # Exact option match (case-insensitive) on a single open question
    if len(open_questions) == 1:
        for opt in open_questions[0].options:
            if reply.strip().lower() == opt.lower():
                return opt

    return None
