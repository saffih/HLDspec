# HLDspec Agent-First Entrypoint Gap RunSkeptic Review

made by AI

Date: 2026-05-23

## Goal

Consolidate the current product state and define the next missing layer: a simple agent-first trigger.

Desired user-facing trigger:

```text
HLDspec /absolute/path/to/HLD.md
```

The human should not need to know the internal CLI sequence. The agent should own process guidance, use tools internally, and ask only real checkpoint questions.

## GATE

DONE is testable:

- TODO reflects actual current repo/product state.
- Current real smoke blocker is recorded as conversion checkpoint.
- Next gap is explicit: agent-first entrypoint.
- No real SpecKit execution is introduced.
- No source HLD mutation is introduced.

Decision: FIX allowed for docs/context only.

## FUNDAMENTAL SCAN

Current architecture shape:

```text
Human
-> future HLDspec Orchestrator Agent
   -> internal CLI/tools
   -> junior bounded question/extraction helpers
   -> senior Product/Architect synthesis
   -> judge promotion gates
   -> one-phase SpecKit proxy dry-run
```

Current problem:

```text
Engine exists.
User-facing agent-start trigger does not.
```

Current real smoke blocker:

```text
CONVERSION_CHECKPOINT -> hld_conversion_decisions
```

The later PM/Architect/answer-pack/proxy artifacts are correctly absent until conversion passes.

## MAP

- Charlie Munger (CH): downstream PM/Architect/SpecKit artifacts depend on converted HLD input; proceeding before conversion guarantees failure.
- Occam's Razor (OM): the user-facing interface should be one trigger, not a long command sequence.
- Richard Feynman (FE): state must explain simply why artifacts are missing: conversion checkpoint blocks later stages.
- Karl Popper (PO): falsifiable next test is whether `HLDspec /path/to/HLD.md` can generate a catch-up prompt/state and stop at the correct gate.
- Immanuel Kant (KT): every project should use the same simple start pattern; internal commands should remain internal.
- Saffi (SH): speed vs. safety; simple trigger gives speed, but judge gates preserve safety.

## STABILIZED ISSUES

### Issue 1 - TODO/context regressed and obscured current state

Root cause: later product layers exist, but TODO/context can be overwritten by stale patches.

Action: restore a full context anchor.

Evidence level: OBSERVED from repo history and current TODO diff.

Verification: doc diff plus full test discovery when available.

### Issue 2 - user-facing trigger is missing

Root cause: HLDspec has internal scripts but no agent-start wrapper/contract.

Action: mark as next patch, not implemented in this patch.

Evidence level: OBSERVED by repo search and current workflow.

Verification for next patch: `hldspec_agent_start.sh` and prompt-builder tests.

### Issue 3 - current real smoke is blocked earlier than PM/Architect/proxy

Root cause: source HLD is raw and conversion decisions are still open.

Action: record conversion checkpoint as immediate current gate.

Evidence level: REPRODUCED by real smoke output supplied by user.

Verification: question guide + interview + conversion + rerun first_readonly.

## DECIDE

HANDLED for this docs/context patch.

Do not implement real SpecKit execution.

Next implementation should be:

```text
agent-first entrypoint:
HLDspec /absolute/path/to/HLD.md
```

## HANDLED

- TODO restored as context anchor.
- Agent-first UX gap documented.
- Current conversion checkpoint recorded.
- Next patch scope is explicit.
- Real execution remains blocked.

## CONFLICTS

### Should the next patch be a real orchestrator command or just an agent prompt?

Thesis:

```text
A command wrapper gives repeatable behavior and tests.
```

Antithesis:

```text
The actual user experience is agent-first; too much CLI can become the wrong product surface.
```

Safe recommendation:

```text
Add both:
- docs/HLDSPEC_AGENT_ORCHESTRATOR_CONTRACT.md
- scripts/build_hldspec_agent_start_prompt.py
- scripts/hldspec_agent_start.sh as a prompt/context generator, not as autonomous executor
```

Decision needed:

```text
Approve next patch as agent-start prompt/context generator, not real execution.
```
