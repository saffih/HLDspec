# SpecKitInvoker TASKS/Haiku Live Invocation Proof

**Status:** supporting architectural evidence record. This document records one
owner-authorized, synthetic, live proof of the real `SpecKitInvoker` headless
path without promoting it into a general execution claim.

**Date:** 2026-07-11.

**Related:** [`docs/FIRST_LIVE_E2E_PROOF.md`](FIRST_LIVE_E2E_PROOF.md) proved a
different, narrower claim earlier (Opus, `IMPLEMENT` phase, calculator
fixture at `/tmp/proof-target`). This record proves a different phase, model,
and fixture; it does not supersede or extend that record's scope.

## Exact Claim Tested

Given a valid synthetic code-feature `TASKS` context, the real HLDspec
`SpecKitInvoker` (`hldspec/speckit_invoker.py`):

1. builds and executes a real `claude --print` command,
2. routes the `TASKS` phase to the configured `haiku` model alias,
3. invokes the actual `speckit-tasks` skill,
4. returns a real `InvocationResult`,
5. detects the actual Git-state change,
6. reports `verified` consistently with the observed result.

## Not Proven

This single invocation does **not** prove:

- `hldspec/speckit_drive_loop.py` (a separate direct-command path that does
  not call `SpecKitInvoker`);
- `SpecKitExecutionMachine`;
- any SpecKit phase other than `TASKS`;
- production Flow execution or any Flow mutation (Flow was never touched by
  this proof);
- `DRIVER_OBSERVED` evidence, a readiness-evidence writer, or an evidence
  provenance schema;
- `MANUAL_ATTESTED` evidence;
- a durable invocation-log or development-receipt implementation;
- weak-model reliability beyond this one successful run;
- arbitrary brownfield repository support.

## Owner Authorization

The owner authorized exactly one live external headless invocation through
the real `SpecKitInvoker`, against a disposable synthetic Git repository,
using the `TASKS` phase, with no injected runner, mock subprocess, fake
output, or custom change detector, and with one point-in-time proof record
committed to HLDspec. No implementation, drive-loop, readiness-evidence
writer, provenance schema, durable log, or code/test fix was authorized or
performed as part of this proof.

## Code Contract Verified (pre-invocation)

At `PROOF_CODE_SHA = 07aa33ed5bbbb938d6eff0e927804f400cb2ce48` (main, merged
via PR #153):

- `PHASE_SKILL["TASKS"] == "speckit-tasks"`
- `PHASE_MODEL["TASKS"] == "haiku"`
- `"TASKS"` is in `ARTIFACT_PHASES`
- `SpecKitInvoker._command()` builds
  `["claude", "--print", "--dangerously-skip-permissions", "--model", "haiku", "/speckit-tasks <prompt>"]`
- `invoke()` uses the default real `CommandRunner` (no injected runner)
- `produced_artifacts` is derived from a before/after `git rev-parse HEAD` +
  `git status --porcelain` signature comparison
- `InvocationResult.verified` requires both a zero return code and
  `produced_artifacts` for artifact phases (the anti-hollow-completion gate)

Focused regression (`tests_v2.test_speckit_invoker`, 14 tests) passed at this
SHA before the live invocation.

## Synthetic Target

- Created via `mktemp -d` under `/tmp`, scaffolded with `specify init --here
  --integration claude` (canonical local `spec-kit` v0.8.11 installer,
  bundled assets — no Flow content copied or read to derive the fixture).
- Git-initialized locally (local-only `user.name`/`user.email`, no remote, no
  symlinks), branch `001-live-invoker-proof`.
- Feature: a trivial standard-library-only Python utility
  (`is_palindrome(s: str) -> bool`), described in
  `specs/001-live-invoker-proof/spec.md` and `specs/001-live-invoker-proof/plan.md`.
  No `tasks.md` existed before invocation.
- A scope-locking synthetic `CLAUDE.md` confined the headless agent to this
  repository and the single `TASKS` operation.
- Baseline commit: `1f356db98e635d16d8f818d4e63394954492a5b5`.
- Removed after the proof completed; raw evidence preserved outside this
  repository at `~/speckit-invoker-proof-evidence-2026-07-11/`
  (`speckit_proof_result.json`, `speckit_proof_stdout.txt`,
  `speckit_proof_stderr.txt`, `speckit_proof_supervisor_evidence.txt`,
  `speckit-proof-manifest.txt`).

## Invocation

Driven by an untracked one-shot script (not part of this repository) that
imported the real `SpecKitInvoker` and `build_prompt` from this worktree,
constructed the invoker with no injected `runner`, `agent_cmd`, `extra_args`,
`phase_models`, `route_models`, or `change_detector`, and called
`invoker.invoke("TASKS", prompt)` exactly once under an external
process-group watchdog (900s bound; not needed — the call completed in ~80s).

Computed command (via the invoker's own `_command` builder, not
hand-reconstructed):

```
claude --print --dangerously-skip-permissions --model haiku "/speckit-tasks <prompt>"
```

## Result

- `returncode = 0`, `ok = True`
- `produced_artifacts = True`, `verified = True`
- Independently confirmed: `specs/001-live-invoker-proof/tasks.md` was
  created (143 lines, non-empty, structurally a valid SpecKit tasks
  breakdown — 13 tasks across setup/user-story/polish phases), registering
  as the sole untracked change in `git status --porcelain` in the synthetic
  target. No other path was touched. No second invocation occurred. No
  residual `claude` process remained after completion (confirmed by the
  external watchdog).
- `InvocationResult` fields agreed with independently observed Git state in
  every respect checked.

**Verdict: PASS.**

## Authority Boundary

This proof harness is a one-shot, owner-authorized sandbox proof against a
disposable synthetic target only. It is not Journey 3 default authority, not
a production execution channel, and not autonomous execution. It does not
establish permission for a second live invocation, for driving any other
SpecKit phase, or for executing against Flow or any other real target.
