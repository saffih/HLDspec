# HLDspec Agent-Start Entrypoint RunSkeptic Review

## Goal

Add a simple user-facing start layer:

```text
HLDspec /absolute/path/to/HLD.md
```

The implementation is a prompt/context generator, not an autonomous executor.

## GATE

DONE is testable:

- source HLD path is accepted
- workspace is created
- source HLD is copied to workspace copies
- source HLD remains read-only
- prompt/context files are generated
- current state is detected if already present
- conversion checkpoint produces a question-guide command
- prompt forbids SpecKit, final specs, implementation, silent answers, and source mutation

Decision: FIX allowed.

## FUNDAMENTAL SCAN

The product should be agent-first, but the CLI remains the internal engine.

The start layer must not bypass judge gates. It only gives the agent enough context to run the process safely.

## MAP

- Munger: a simple trigger reduces user error, but only if it preserves gates.
- Occam: one trigger is simpler than asking users to remember many scripts.
- Feynman: the prompt must explain source, workspace, stage, and next safe action.
- Popper: tests must prove conversion checkpoint prompts include question-guide flow.
- Kant: the same trigger should work for every HLD.
- Saffi: speed comes from the simple trigger; safety comes from read-only source and stop conditions.

## DECISION

HANDLED.

Real SpecKit execution remains deferred.
