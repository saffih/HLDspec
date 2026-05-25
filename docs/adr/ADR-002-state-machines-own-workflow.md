# ADR-002: State machines own workflow

**Status:** ACCEPTED  
**Date:** 2026-05-25  

## Context

Before the V2 refactor, shell scripts contained control flow logic — they checked artifact state, made gate decisions, and branched on quality conditions. This meant product policy was encoded in shell, making it untestable without running shell processes, hard to reason about in isolation, and invisible to static analysis. Adding a new gate meant editing a shell script, not a typed Python function.

The mixing of adapter responsibilities (launching processes, passing arguments) with policy responsibilities (is this artifact good enough to proceed?) is the core problem. Shell is excellent at the former and poor at the latter.

## Decision

All workflow transitions live in Python machines in `hldspec/machines/`. Shell scripts are adapters only: they launch commands, pass arguments, and print results. They do not evaluate artifact quality, make gate decisions, or encode any workflow policy.

Each machine is a self-contained Python class with a typed `run()` method that takes a workspace path and returns a `MachineResult`. The full pipeline chain is orchestrated by `ProjectMachine`. Every gate condition is expressible as a Python unittest.

## Consequences

- Every gate is testable without spawning a shell process. The `tests_v2/` suite validates machine behavior in isolation.
- Shell wrappers (`scripts/*.sh`) may only call machines and render results. Any policy that migrates into a shell script is a bug.
- New gates must be added as machines, not as shell conditionals.
- The pipeline chain is canonical in `ProjectMachine` — no other location may define execution order.
