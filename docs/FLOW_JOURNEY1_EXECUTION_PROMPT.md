# Flow Journey 1 Execution Prompt

## Status

Prepared prompt document only.

This document records the approved prompt shape for a future scoped Journey 1
HLD authoring/hardening run for `/Users/saffi/code/flow`.

It does not execute Journey 1. It does not authorize this PR to write final
authoritative HLD content, invoke SpecKit, wire commands, mutate
`/Users/saffi/code/flow`, create backlog, or create implementation scope.

## Approval Basis

- **Approval decision:** `APPROVE_PREPARING_J1_EXECUTION_PROMPT: yes`
- **Human approver:** Hadas / project owner
- **Target:** `/Users/saffi/code/flow`
- **Evidence basis:** PRs #111 through #117
- **Allowed output in this slice:** Journey 1 execution prompt document only
- **Allowed purpose:** prepare a scoped HLD authoring/hardening prompt from
  confirmed/corrected declared evidence

Not authorized:

- execute Journey 1 in this slice
- invoke SpecKit
- wire commands
- mutate `/Users/saffi/code/flow`
- create backlog or implementation scope
- write final authoritative HLD
- close J0-12 globally

## Evidence Basis To Carry Forward

The future Journey 1 runner must treat the following as the bounded source
context:

- `docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md`
- `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md`
- `docs/FLOW_JOURNEY1_PLANNING_JUSTIFICATION.md`
- `docs/FLOW_JOURNEY1_PLANNING_SCOPE.md`
- `docs/FLOW_DECLARED_EVIDENCE_CONFIRMATION.md`
- `docs/journey0_real_target_dry_runs/flow-journey0-corrected-declared-evidence-dry-run.md`
- `docs/FLOW_J0_12_J0_17_UNBLOCK_REVIEW.md`
- `docs/JOURNEY1_SDD_READY_GATE.md`

Evidence summary:

- RT-1 proved generic file/doc evidence alone produces ACTION, not PASS.
- RT-2 proved explicit declared product-surface evidence can make PASS
  reachable, but the original declared set required human review.
- PR #115 confirmed seven declared items, amended `DECLARED-005` and
  `DECLARED-009`, and rejected old `DECLARED-010`.
- PR #116 proved the corrected declared set produces PASS with no mutation,
  5/5 product-surface source types, no gaps, and no product decisions.
- PR #117 accepted a scoped flow provenance basis for Journey 1 planning and
  marked the flow Journey 1 execution prompt ready for human approval.

## Provenance Caveat

J0-12 remains globally open.

For `flow` only, the scoped status is:

`SCOPED_FLOW_PROVENANCE_ACCEPTED_FOR_J1_PLANNING`

The future runner must carry this caveat forward:

> Corrected declared evidence is human-declared Journey 0 evidence for `flow`.
> It is accepted as scoped input for Journey 1 planning/hardening, but it is not
> automatically validated global product truth and must not be generalized to
> other targets.

## Execution Prompt For A Future Run

Use the following prompt only in a separate, explicitly approved Journey 1 run:

```text
You are Codex working in /Users/saffi/code/HLDspec.

Task: execute Journey 1 HLD authoring/hardening for the flow target using the
scoped Journey 0 evidence basis approved for prompt preparation.

Target:
/Users/saffi/code/flow

Purpose:
Create or harden the flow HLD until it can be assessed against
docs/JOURNEY1_SDD_READY_GATE.md.

Required source context:
- docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md
- docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md
- docs/FLOW_JOURNEY1_PLANNING_JUSTIFICATION.md
- docs/FLOW_JOURNEY1_PLANNING_SCOPE.md
- docs/FLOW_DECLARED_EVIDENCE_CONFIRMATION.md
- docs/journey0_real_target_dry_runs/flow-journey0-corrected-declared-evidence-dry-run.md
- docs/FLOW_J0_12_J0_17_UNBLOCK_REVIEW.md
- docs/JOURNEY1_SDD_READY_GATE.md

Allowed actions:
- Read only the required source context first.
- Read the flow target HLD/source files only after confirming exact allowed
  target paths with the human/project owner.
- Draft Journey 1 HLD hardening output in the approved workspace/output path
  chosen for the execution run.
- Produce a Journey 1 readiness report with PASS/ACTION/BLOCKED status per
  docs/JOURNEY1_SDD_READY_GATE.md.
- Preserve evidence references to the Journey 0 declared evidence and corrected
  evidence reports.

Forbidden actions:
- Do not invoke SpecKit.
- Do not start Journey 2 or Journey 3.
- Do not wire command surface.
- Do not mutate /Users/saffi/code/flow unless a later prompt explicitly
  authorizes a workspace copy or exact target write path.
- Do not create backlog or implementation scope.
- Do not treat generic file/doc evidence as product truth.
- Do not treat declared evidence as global product truth.
- Do not close J0-12 globally.
- Do not promote unresolved or unaudited HLD content to Journey 2.

Required evidence handling:
- Use the seven PR #115 confirmed items unchanged.
- Use amended DECLARED-005 only with the corrected meaning:
  SQLite is implementation detail; markdown projections are product surface.
- Use amended DECLARED-009 only with the corrected meaning:
  the one-open-escalation invariant is stale design residue; multiple open
  escalations may exist if references, ownership, reply routing, task state, and
  context integrity remain clear.
- Do not reuse old rejected DECLARED-010.
- Use replacement DECLARED-010 as the scoped product limit:
  interface and infrastructure expansion is allowed when it supports baton and
  context management, but must not weaken baton/context integrity, durable task
  state, stable IDs, explicit references, escalation traceability, session/log
  links, copy-pasteable context, or human authority over decisions.

Stop conditions:
- Any requested action would invoke SpecKit.
- Any requested action would mutate /Users/saffi/code/flow without explicit
  target/path authorization.
- Any requested action would create backlog or implementation scope.
- Any output starts Journey 2 or Journey 3.
- Any generic file evidence is treated as authoritative product truth.
- Any declared evidence is generalized beyond scoped flow planning/hardening.
- Any product conflict, authority question, or provenance gap cannot be resolved
  from the approved source context.

Expected outputs:
- HLD hardening draft or patch plan, depending on the execution approval.
- Journey 1 readiness report with PASS/ACTION/BLOCKED verdict.
- Explicit list of unresolved questions, provisional assumptions, and evidence
  references.
- Explicit statement that SpecKit, Journey 2, Journey 3, backlog, and
  implementation remain out of scope unless separately approved.
```

## What This Document Does Not Authorize

- It does not execute the prompt above.
- It does not mutate `/Users/saffi/code/flow`.
- It does not write final authoritative HLD content.
- It does not invoke SpecKit.
- It does not wire Journey 0 or Journey 1 into command surface.
- It does not create backlog or implementation scope.
- It does not close J0-12 globally.

## Next Action

Review this prompt document. If accepted, issue a separate explicit prompt that
authorizes the Journey 1 execution run and defines the exact target/read/write
paths for that run.
