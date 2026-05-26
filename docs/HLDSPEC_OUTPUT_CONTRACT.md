# HLDspec Output Contract

## Purpose

HLDspec command output must help a user or agent decide what is safe to do next.
Output should not be only a list of files.

## Stable Command Sections

Public commands should prefer stable, titled sections:

- `HLDspec Status`
- `Validation`
- `Blockers`
- `Open Questions`
- `Next Safe Action`
- `HLDspec Review`
- `Blocking Review Files`
- `Optional Context Files`
- `Missing Blocking Files`
- `Missing Non-Blocking Files`
- `Repo Checks`
- `Target Layout Checks`
- `Session Checks`
- `Interview Checks`
- `Validation Reports`
- `Final Summary`

Section names are part of the user and agent contract. Add sections only when
they make decisions clearer.

## PASS, ACTION, CONFLICT

Use these words consistently:

- `PASS`: no blocking finding is known.
- `ACTION`: fixable missing, stale, invalid, or incomplete artifact.
- `CONFLICT`: unresolved design, source-of-truth, or human-owned decision.

Do not present an unresolved ACTION or CONFLICT as ready.

## Blocker Display

Blockers must be explicit bullets. Each blocker should include:

- severity when known
- affected artifact or report path
- short reason

If there are no blockers, print `none`.

## Next Safe Action

Every decision-oriented command must show `Next Safe Action`.

The next safe action must be conservative:

- If blockers exist, resolve them before continuing.
- If open questions exist, answer them before continuing.
- If no blockers exist, point to the next facade command or agent prompt.

## Report Paths

When reports are available, output should include their paths:

- `target/.hldspec/validation/context_prompt_validation.json`
- `target/.hldspec/validation/context_prompt_validation.md`
- `target/.hldspec/validation/promotion_gate.json`
- `target/.hldspec/validation/promotion_gate.md`

Missing optional reports should be shown as `not present`, not as a failure,
unless a gate says they are required for the current target state.

## Exit Code Semantics

Public facade commands use stable exit codes:

- `0`: command completed and no required facade check failed.
- `1`: changed/different result for comparison-style commands such as `diff`.
- `2`: missing required input, missing required target/session artifact, or a human checkpoint.
- `3`: blocked machine state.
- Other nonzero values are errors from malformed input or internal failures.

Scripts used as maintainer/debug tools may return `2` for ACTION or CONFLICT
findings when their specific contract defines that behavior.
