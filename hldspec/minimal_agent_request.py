from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MinimalAgentRequest:
    source_hld: str
    target_workspace: str
    mode: str
    runtime: str
    comment: str
    workflow_trigger: str | None = None


_RUNTIME_RE = re.compile(r"\bruntime:\s*(claude|codex|devin)\b|\bruntime\s+(claude|codex|devin)\b", re.I)


def _path_token(name: str) -> str:
    return (
        rf'(?:"(?P<{name}_dq>[^"]+)"|'
        rf"'(?P<{name}_sq>[^']+)'|"
        rf"(?P<{name}_bare>\S+))"
    )


_SOURCE_LABEL_RE = re.compile(r"source hld:\s*" + _path_token("source"), re.I)
_TARGET_LABEL_RE = re.compile(r"target project:\s*" + _path_token("target"), re.I)
_HLD_CREATE_RE = re.compile(
    r"^HLDspec\s+HLD:\s*" + _path_token("source") + r"\s+create\s+" + _path_token("target") + r"(.*)$",
    re.I,
)
_CREATE_FROM_RE = re.compile(
    r"^HLDspec\s+create\s+" + _path_token("target") + r"\s+from\s+" + _path_token("source") + r"(.*)$",
    re.I,
)
_HLD_TARGET_RE = re.compile(
    r"^HLDspec\s+HLD:\s*" + _path_token("source") + r"\s+target:\s*" + _path_token("target") + r"(.*)$",
    re.I,
)
_WORKFLOW_TRIGGER_PATTERNS = (
    ("check_hld", re.compile(r"\bcheck\s+hld\b", re.I)),
    ("build_loop_prereqs", re.compile(r"\bbuild\s+loop\s+prereqs\b", re.I)),
    ("build_loop_init", re.compile(r"\bbuild\s+loop\s+init\b", re.I)),
    ("build_loop_ready", re.compile(r"\bbuild\s+loop\s+ready\b", re.I)),
)
_NEGATED_TRIGGER_RE = re.compile(
    r"\b(?:do\s+not|don't|dont|not|without)\s+"
    r"(?:(?:do|doing|run|running|start|starting|use|using)\s+)?(?:the\s+)?"
    r"(?:check\s+hld|build\s+loop\s+prereqs|build\s+loop\s+init|build\s+loop\s+ready)\b",
    re.I,
)


def _detect_runtime(text: str) -> str:
    match = _RUNTIME_RE.search(text)
    if not match:
        return "claude"
    return (match.group(1) or match.group(2) or "claude").lower()


def detect_workflow_trigger(text: str) -> str | None:
    candidates = _workflow_trigger_candidates(text)
    if len(candidates) != 1:
        return None
    return candidates[0]


def _workflow_trigger_candidates(text: str) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for trigger, pattern in _WORKFLOW_TRIGGER_PATTERNS:
        for match in pattern.finditer(text):
            window = text[max(0, match.start() - 40) : match.end()]
            if _NEGATED_TRIGGER_RE.search(window):
                continue
            candidates.append((match.start(), trigger))
    if not candidates:
        return []
    ordered = [trigger for _, trigger in sorted(candidates)]
    return list(dict.fromkeys(ordered))
    return None


def _clean_token(value: str) -> str:
    return value.strip().rstrip(".,;:")


def _matched_path(match: re.Match[str], name: str) -> str:
    for suffix in ("dq", "sq", "bare"):
        value = match.group(f"{name}_{suffix}")
        if value:
            return _clean_token(value)
    return ""


def parse_minimal_agent_request(text: str) -> MinimalAgentRequest:
    raw = text.strip()
    if not raw:
        raise ValueError("minimal HLDspec request is empty")

    runtime = _detect_runtime(raw)
    workflow_candidates = _workflow_trigger_candidates(raw)
    if len(workflow_candidates) > 1:
        raise ValueError(
            "ambiguous HLDspec workflow trigger: "
            + ", ".join(workflow_candidates)
            + ". Ask for exactly one of: check HLD, Build Loop prereqs, Build Loop init, Build Loop ready."
        )
    workflow_trigger = detect_workflow_trigger(raw)

    for pattern in (
        _HLD_CREATE_RE,
        _CREATE_FROM_RE,
        _HLD_TARGET_RE,
    ):
        match = pattern.match(raw)
        if match:
            source = _matched_path(match, "source")
            target = _matched_path(match, "target")
            suffix = match.group(match.lastindex or 0).strip() if match.lastindex else ""
            comment = suffix or raw
            return MinimalAgentRequest(
                source_hld=source,
                target_workspace=target,
                mode="create",
                runtime=runtime,
                comment=comment,
                workflow_trigger=workflow_trigger,
            )

    source_match = _SOURCE_LABEL_RE.search(raw)
    target_match = _TARGET_LABEL_RE.search(raw)
    if source_match and target_match:
        return MinimalAgentRequest(
            source_hld=_matched_path(source_match, "source"),
            target_workspace=_matched_path(target_match, "target"),
            mode="create",
            runtime=runtime,
            comment=raw,
            workflow_trigger=workflow_trigger,
        )

    raise ValueError(f"unrecognized HLDspec minimal request: {raw}")
