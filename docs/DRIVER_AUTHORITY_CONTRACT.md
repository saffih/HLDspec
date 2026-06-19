# Driver Authority Contract (v0)

This documents and hardens the authority boundaries of the **General Toolchain
Driver** (`hldspec/toolchain_driver.py`). It is the binding contract for what a
driver may do at each authority level. It is a contract over the existing
read-only driver, not a new mechanism. See `docs/TOOLCHAIN_DRIVER_CONTRACT.md`
for the driver/helper split this builds on.

## Core rule

> An automatic (system) driver **may** replace the human **operator**.
> An automatic driver **must not** automatically replace the human
> **approver / owner**.

This reduces to one load-bearing invariant: `approver_replacement_allowed` is
`False` for **every** v0 (actor, authority) mode, and the owner-only boundaries
below are always reported and never granted.

## Driver vs Helper

- **Helper**: a toolchain-specific map/rules/evidence set (`helper_registry.py`,
  `helper_selection.py`). Only `speckit` is operational today.
- **Driver**: the process navigator -- human or system -- that watches state,
  reality-checks evidence, and proposes the next safe step. It never silently
  runs a toolchain step.

## Operator vs Approver / Owner

| Operator (the driver may fill this role) | Approver / Owner (the driver may not) |
|---|---|
| inspects, checks, runs read-only validations | approves a helper; marks it OPERATIONAL |
| gathers evidence; compares expected vs actual | approves mutation, commit, push, merge |
| reports mismatch; proposes the next safe action | accepts unresolved risk |
| executes **bounded** safe actions only if authority allows | overrides a BLOCKED/ACTION gate |
| | authorizes policy/contract changes (SourceBinding, ISG, NextActionPacket/READY) |

A **system** driver may stand in for the operator. A **human** driver *is* the
operator, so there is nothing to replace (`operator_replacement_allowed` is
`False` for a human driver, `True` for a system driver).

## Authority ladder

| Authority | May | May not |
|---|---|---|
| `GUIDE_ONLY` | observe and recommend | execute commands |
| `PROPOSE_COMMAND` | produce exact commands/prompts | execute them (the human/operator runs them) |
| `EXECUTE_WITH_APPROVAL` | execute only after explicit approval for that action/scope | act without approval |
| `AUTONOMOUS_WITH_GUARDS` | (future/highest) act as process operator inside declared safe bounds | self-approve protected transitions; bypass owner approval |

v0 **does not implement autonomous execution**. `AUTONOMOUS_WITH_GUARDS` is
reported as future-only and resolves to `BLOCKED`. Even for
`EXECUTE_WITH_APPROVAL`, v0 executes and mutates **nothing**:
`execution_allowed` and `mutation_allowed` are always `False`. The
`mutation_posture` field records the *contracted* gate
(`approval_gated` vs `not_allowed`), not current capability.

## Observation vs mutation

The driver may observe any process evidence needed to determine whether reality
matches the intended journey state -- even outside the selected toolchain:

- git status, worktree ownership, branch / PR / merge state
- test result evidence (when available)
- helper recommendation / selection / effective helper
- installed runtime manifest / helper identity
- generated/owned artifact boundary checks
- journey phase evidence

Observation and confirmation are always allowed. Mutation and execution remain
governed by authority level and approval.

> **Watch broadly. Touch narrowly.**

## Protected approval boundaries

The driver must never self-approve any of these; they belong to the human
approver/owner and are always reported, never granted:

- approve a new helper; mark a helper OPERATIONAL
- change SourceBinding; change ISG Governance; change NextActionPacket/READY policy
- mutate product/application code; mutate toolchain-owned or generated artifacts
- commit; push; merge; delete a branch
- accept unresolved risk; override a BLOCKED or ACTION gate

A requested self-approval or protected transition surfaces as `BLOCKED`/`ACTION`,
never a silent `PASS`. v0 has no execution channel, so these are satisfied
structurally: the contract never grants them.
