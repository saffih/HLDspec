# ADR-005: Shell scripts are adapters only

**Status:** ACCEPTED  
**Date:** 2026-05-25  

## Context

Shell scripts like `first_run_readonly.sh`, `project_continue.sh`, and `project_first_run.sh` historically encoded product decisions: they evaluated conditions, branched on artifact state, and in some cases determined whether to continue or halt the workflow. This was natural as the system evolved incrementally, but it produced a codebase where workflow policy was split across Python and shell with no clear boundary.

Shell scripts are difficult to unit-test, produce hard-to-parse error messages, and do not benefit from the type system or the machine abstraction. When a gate decision lives in shell, it cannot be validated by the `tests_v2/` suite. When a product decision is embedded in a shell branch, it is invisible to code review tooling.

## Decision

Shell scripts may: launch commands, pass arguments, capture and print results. They may not: evaluate artifact quality, make gate decisions, or encode any workflow policy.

Concretely: a shell script may call `python3 -m hldspec run ...` and print its output. It may not parse that output to decide whether to call a second command based on quality conditions. Any such decision must live in a Python machine.

## Consequences

- All policy moves to Python. Shell-only failures are adapter failures, not domain failures.
- Shell scripts become thin wrappers: the only logic they contain is argument handling and output formatting.
- Any shell script that currently contains a gate decision must have that decision extracted into a machine before the script is considered compliant.
- New shell scripts added to `scripts/*.sh` must be reviewed against this rule: if they branch on artifact content, they are out of scope and must be refactored.
- The test suite can achieve full policy coverage without executing any shell script.
