# Flow HLD Hardening Draft

## Status

Reviewable HLDspec-side draft output only. This is the Journey 1
authoring/hardening draft package for the `flow` target, produced under
`FLOW_JOURNEY_1_EXECUTION_APPROVAL` (approver: Hadas / project owner,
2026-07-03).

- This is reviewable HLDspec-side draft output only.
- This does not modify `/Users/saffi/code/flow/HLD.md`.
- This does not write final authoritative HLD content.
- This does not invoke SpecKit.
- This does not wire commands.
- This does not start Journey 2 or Journey 3.
- This does not create backlog or implementation scope.
- This does not close J0-12 globally.
- Future target HLD updates require separate explicit approval.

## Evidence basis

- PR #111 / RT-1: generic file/doc evidence alone → ACTION, not PASS.
- PR #112 / RT-2: original declared evidence → PASS, but required human review.
- PR #115 (`docs/FLOW_DECLARED_EVIDENCE_CONFIRMATION.md`): seven items
  confirmed (DECLARED-001/002/003/004/006/007/008); DECLARED-005 and
  DECLARED-009 amended; old DECLARED-010 rejected.
- PR #116
  (`docs/journey0_real_target_dry_runs/flow-journey0-corrected-declared-evidence-dry-run.md`):
  corrected declared set → PASS, 5/5 product-surface source types, no gaps,
  no mutation; replacement DECLARED-010 used.
- PR #117 (`docs/FLOW_J0_12_J0_17_UNBLOCK_REVIEW.md`): scoped flow provenance
  accepted for Journey 1 planning
  (`SCOPED_FLOW_PROVENANCE_ACCEPTED_FOR_J1_PLANNING`); J0-12 remains globally
  open.
- PR #118 (`docs/FLOW_JOURNEY1_EXECUTION_PROMPT.md`): prepared the execution
  prompt this run follows.

Provenance caveat, carried forward verbatim:

> Corrected declared evidence is human-declared Journey 0 evidence for `flow`.
> It is accepted as scoped input for Journey 1 planning/hardening, but it is not
> automatically validated global product truth and must not be generalized to
> other targets.

## Current HLD/source context reviewed

Bounded target reads (read-only, exact allowed paths):

- `/Users/saffi/code/flow/README.md` — product intro, "What it is not"
  (HLD-011 exclusion list), usage, persistence safety.
- `/Users/saffi/code/flow/HLD.md` — authoritative design; sections HLD-001
  through HLD-016 with HLD-ID/ROLE/STATUS/RISK/SPECS/RESOURCES metadata and
  HLD-VERIFY/HLD-RATIONALE on high-risk sections.
- `/Users/saffi/code/flow/core.md` — the agnostic runner loop (CLI + text
  only).

Target docs present: yes. Current HLD exists: yes — this is a hardening run,
not a from-scratch authoring run. No target file contents are reproduced here
beyond section labels and short claim references needed for review.

## Proposed HLD section map

| HLD section | Evidence | Change type | Risk | Human review |
|---|---|---|---|---|
| HLD-001 What it is | DECLARED-001 (confirmed) | keep / clarify | low | yes |
| HLD-002 Vocabulary | DECLARED-001, -003 | keep | low | no |
| HLD-003 Core model | DECLARED-005 (amended) | clarify | high | yes |
| HLD-004 Task lifecycle | DECLARED-002, -007 (confirmed) | keep | low | no |
| HLD-005 Wait model (fork-join) | DECLARED-002 (confirmed), DECLARED-009 (amended) | remove invariant + clarify | high | yes |
| HLD-006 Escalation triggers | DECLARED-008 (confirmed) | keep | low | no |
| HLD-007 Human-in-the-loop | DECLARED-006 (confirmed), DECLARED-009 (amended) | clarify | medium | yes |
| HLD-008 The baton | DECLARED-001 (confirmed), DECLARED-005 (amended) | keep / clarify | medium | yes |
| HLD-009 CLI contract | DECLARED-003, -006 (confirmed), DECLARED-009 (amended) | clarify | medium | yes |
| HLD-010 Work routing | DECLARED-003 (confirmed) | keep | low | no |
| HLD-011 Out of scope | old DECLARED-010 (rejected), replacement DECLARED-010 | rework | high | yes |
| HLD-012 Technology | DECLARED-005 (amended), DECLARED-003 (confirmed) | clarify | low | yes |
| HLD-013 Concurrency and durability | DECLARED-005 (amended) | keep | low | no |
| HLD-014 Recovery | DECLARED-009 (amended) | clarify | medium | yes |
| HLD-015 Autonomy contract | DECLARED-009 (amended) | clarify (lifecycle invariant set) | high | yes |
| HLD-016 Output layer | DECLARED-005 (amended) | keep / clarify | medium | yes |
| README "What it is not" | old DECLARED-010 (rejected) | rework (mirrors HLD-011) | medium | yes |

All references are by DECLARED id with PR #115/#116 provenance. No new product
claims are introduced by this map.

## Proposed additions

Proposals only — final wording requires a separately approved target HLD patch.

1. **Markdown projection roles (HLD-003 or HLD-008 vicinity).** Add the three
   promised product-surface roles of markdown projections from amended
   DECLARED-005: (1) integration surface for agents, (2) context state for
   work in progress, (3) user-facing context and reporting in reports.
   Currently the HLD frames markdown as a one-way projection "for human
   reading" only; the promised roles are stronger than the current text.
2. **Replacement product limit (HLD-011 rework).** Add the replacement
   DECLARED-010 limit as the governing boundary rule: interface and
   infrastructure expansion is allowed when it supports baton and context
   management, but must not weaken baton/context integrity, durable task
   state, stable IDs, explicit references, escalation traceability,
   session/log links, copy-pasteable context, or human authority over
   decisions. This is human-declared corrected evidence, not automatically
   validated product truth; the final wording is a human decision.
3. **SDD-gate metadata completion.** Fill `HLD-SPECS: TBD` on HLD-001,
   HLD-002, HLD-006, HLD-011, HLD-012 and `HLD-RESOURCES: TBD` on HLD-011.
   Per `docs/JOURNEY1_SDD_READY_GATE.md` §6/§11, `TBD` metadata blocks PASS.

## Proposed clarifications

1. **HLD-005 / HLD-007 / HLD-009 / HLD-014 / HLD-015 — escalation
   concurrency.** The current HLD encodes "a task holds at most one open
   escalation at a time" as a structural invariant (HLD-005 HLD-VERIFY and
   HLD-RATIONALE; HLD-015 `lifecycle` invariant; the HLD-009 verb table; the
   HLD-007 "resolves that one escalation" wording; the HLD-014 flaky-mark
   escalation path). Amended DECLARED-009 (owner decision 2026-07-03) states
   this invariant is stale design residue: a task may have multiple
   escalations open concurrently if references, ownership, reply routing,
   task state, and context integrity remain clear. All five sections need a
   coordinated clarification pass; the invariant must not survive as a
   product constraint.
2. **HLD-003 / HLD-012 — storage as implementation detail.** Amended
   DECLARED-005: SQLite is an implementation detail, replaceable without
   product change; it must not be promised as a storage contract. The
   single-source-of-truth *principle* (one durable state store; projections
   are derived) is product surface; the *technology* (SQLite) is not. HLD-003
   (governance, HIGH risk) should carry the principle; HLD-012 (operations)
   may keep SQLite as the current implementation choice.
3. **HLD-001 — baton vs report framing.** Confirmed DECLARED-001 names
   durable-baton task management as the core capability; current HLD-001
   frames the report as "the point" and the baton as the means. These are
   compatible but the relationship should be stated once, explicitly, so
   Journey 2 does not have to guess which is the anchor capability.
4. **HLD-012 — runner set.** Confirmed DECLARED-003: AI session runners
   (Claude, Devin, Codex) via CLI are the intended primary machine actors and
   the named set is current. HLD-012's "Runner (now): Claude. Later
   (pluggable): Devin, Codex" should be aligned with the confirmed current
   set.

## Proposed removals

1. **The one-open-escalation-per-task invariant** everywhere it appears as a
   product constraint (HLD-005, HLD-007, HLD-009, HLD-014, HLD-015). Per
   amended DECLARED-009 it is stale design residue and must not be encoded as
   product truth. Note: implementation and tests currently enforce it; the
   HLD change makes the invariant's removal a product decision, and the
   implementation change is out of scope for Journey 1.
2. **The HLD-011 exclusion list as an intentional product limit** (and its
   README "What it is not" mirror). Per rejected old DECLARED-010, the list
   (no web UI, HTTP API, Unix sockets, daemons, pools, staging, migration
   tooling) is slicing residue, not product limits; the excluded capabilities
   are candidate future features. The replacement DECLARED-010 boundary rule
   (Proposed additions #2) takes its governance place. Removal here means
   removal *as a product-limit claim*; recording current implementation scope
   is fine.

## Open questions

1. Does the "integration surface for agents" role of markdown projections
   (amended DECLARED-005) imply agents may *read* projections directly, or
   only that projections are a promised stable format? The current HLD says
   batons are read via the CLI and markdown is never an input. Human decision
   needed before final wording.
2. When the one-open-escalation invariant is removed, what replaces the
   HLD-014 flaky-mark escalation semantics ("every further orphaning
   escalates immediately") in a multiple-open-escalation world? Product
   decision needed.
3. Which entries of the old HLD-011 exclusion list, if any, does the owner
   want to keep as *current implementation scope notes* versus fully open
   candidate features? The rejection said "we want all — but it was sliced
   out"; the granularity is a human call.
4. Should the required-metadata gaps (`HLD-SPECS: TBD` ×5) be filled with real
   spec intents or explicitly accepted as provisional with revisit triggers
   (gate §8)? Human risk-acceptance call.
5. Does the HLD need an explicit requirements/feature-candidate section per
   gate §6 minimum contents, or do the existing role-tagged sections satisfy
   the human reviewer for structural completeness (gate §17 known limit)?

## Human review checklist

- [ ] Confirm the escalation-concurrency clarification set (HLD-005/007/009/
      014/015) matches the 2026-07-03 owner decision exactly.
- [ ] Confirm the storage-as-implementation-detail split between HLD-003
      (principle) and HLD-012 (current technology).
- [ ] Approve or amend final wording for the three markdown projection roles.
- [ ] Approve or amend the replacement DECLARED-010 boundary rule wording for
      HLD-011.
- [ ] Decide the granularity of the old exclusion-list rework (open question
      3).
- [ ] Answer open questions 1, 2, 4, 5.
- [ ] Decide whether to approve a specific target HLD patch — separate
      explicit approval required; nothing in this package authorizes it.

## Forbidden uses

- Do not treat this draft as authoritative HLD content.
- Do not apply any of it to `/Users/saffi/code/flow` without a separate
  explicit approval naming exact target write paths.
- Do not use it to invoke SpecKit, start Journey 2/3, wire commands, or
  create backlog/implementation scope.
- Do not generalize the scoped flow provenance basis to other targets.
- Do not treat generic file/doc evidence or human-declared evidence as
  validated global product truth.
- Do not cite this draft as closing J0-12.
