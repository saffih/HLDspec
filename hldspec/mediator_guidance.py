"""Backward-compatible alias for :mod:`hldspec.agent_handoff_pack`.

Deprecated name: ``mediator_guidance`` ("Journey 3 mediator guidance").
Preferred name: ``agent_handoff_pack`` (the Agent Handoff Pack).

This shim preserves the old import path and the old public function names so
existing consumers keep working while the concept is renamed. New code should
import :mod:`hldspec.agent_handoff_pack` directly. The shim is scheduled for
removal once all consumers migrate (backlog P1-018).
"""
from __future__ import annotations

from .agent_handoff_pack import (  # noqa: F401
    CODEX_CLAUDE_MEDIATOR_FILE,
    DEFAULT_HANDOFF_BOUNDARIES,
    DEFAULT_LIFECYCLE_MODE,
    DEFAULT_MODEL,
    DEFAULT_NEXT_SAFE_ACTION_OPTIONS,
    DEFAULT_PERMISSION_MODE,
    DEFAULT_SESSION_NAME,
    DEFAULT_STOP_CONDITIONS,
    DEVIN_ACTIVATION_TEMPLATE,
    DEVIN_CONTROL_WORDS,
    DEVIN_MEDIATOR_SKILL_FILE,
    DEVIN_NEXT_SAFE_ACTION_OPTIONS,
    DIRECT_CONTROL_WORDS,
    ENGINEERING_GUIDELINES_NOTE,
    MEDIATOR_DIR_NAME,
    PACKET_FILE,
    REQUIRED_PACKET_FIELDS,
    REQUIRED_SLICE_ARTIFACT_KEYS,
    SCHEMA_VERSION,
    START_MEDIATOR_FILE,
    build_agent_handoff_packet,
    render_devin_handoff_md,
    render_direct_handoff_md,
    render_start_handoff_md,
    validate_agent_handoff_packet,
    write_agent_handoff_pack_artifacts,
)

# Legacy public-name aliases (old API surface).
DEFAULT_MEDIATOR_BOUNDARIES = DEFAULT_HANDOFF_BOUNDARIES
build_mediator_packet = build_agent_handoff_packet
validate_mediator_packet = validate_agent_handoff_packet
write_mediator_guidance_artifacts = write_agent_handoff_pack_artifacts
render_start_mediator_md = render_start_handoff_md
render_devin_mediator_skill_md = render_devin_handoff_md
render_codex_claude_mediator_md = render_direct_handoff_md
