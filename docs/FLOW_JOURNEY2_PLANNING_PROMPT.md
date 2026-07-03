# Flow Journey 2 Planning Prompt

## Status

Prepared prompt document only.

This document records the approved prompt shape for a future scoped Journey 2
SDD / Package Preparation run for `/Users/saffi/code/flow`.

It does not execute Journey 2. It does not authorize this document to decompose
features, build a target package, invoke SpecKit, wire commands, mutate
`/Users/saffi/code/flow`, create backlog, or create implementation scope.

## Approval Basis

- **Approval decision:** `AUTHORIZE_PREPARING_JOURNEY_2_PLANNING_PROMPT: yes`
- **Human approver:** Hadas / project owner
- **Target:** `/Users/saffi/code/flow`
- **Evidence basis:** PRs #111 through #125 (cumulative), with PR #125 as the
  gate-promotion event
- **Allowed output in this slice:** Journey 2 planning prompt document only
- **Allowed purpose:** prepare a scoped SDD / Package Preparation prompt from
  the SDD-ready PASS-for-planning state

Not authorized:

- execute Journey 2 in this slice
- start Journey 3
- invoke SpecKit
- wire commands
- mutate `/Users/saffi/code/flow`
- create backlog or implementation scope
- close J0-12 globally
- treat HLD-017 candidates as implemented commitments

## Evidence Basis To Carry Forward

The future Journey 2 runner must treat the following as the bounded source
context:

### Journey 0 / Journey 1 evidence chain

- `docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md`
- `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md`
- `docs/FLOW_JOURNEY1_PLANNING_JUSTIFICATION.md`
- `docs/FLOW_JOURNEY1_PLANNING_SCOPE.md`
- `docs/FLOW_DECLARED_EVIDENCE_CONFIRMATION.md`
- `docs/journey0_real_target_dry_runs/flow-journey0-corrected-declared-evidence-dry-run.md`
- `docs/FLOW_J0_12_J0_17_UNBLOCK_REVIEW.md`

### Journey 1 execution and SDD-ready gate

- `docs/FLOW_JOURNEY1_EXECUTION_PROMPT.md`
- `docs/flow_journey1_hld_hardening/flow-journey1-readiness-report.md`
- `docs/flow_journey1_hld_hardening/flow-hld-hardening-draft.md`
- `docs/flow_journey1_hld_hardening/flow-hld-hardening-owner-decisions.md`
- `docs/flow_journey1_hld_hardening/flow-sdd-ready-gate-rerun.md`
- `docs/flow_journey1_hld_hardening/flow-drift-disposition.md`
- `docs/flow_journey1_hld_hardening/flow-sdd-ready-gate-v2.md`
- `docs/flow_journey1_hld_hardening/flow-sdd-action-owner-acceptance.md`

### Journey 2 contracts (the rules the run must follow)

- `docs/JOURNEY1_SDD_READY_GATE.md`
- `docs/JOURNEY2_PACKAGE_CONTRACT.md`
- `docs/JOURNEY2_SDD_COMPLETENESS_GATE.md`
- `docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md`
- `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`
- `docs/JOURNEY2_READINESS_GATE_INVENTORY.md`
- `docs/THREE_JOURNEYS.md`

### Target HLD (read-only input)

- `/Users/saffi/code/flow/HLD.md`
  SHA-256: `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0`

Evidence summary:

- Journey 1 gate verdict: **ACTION** (6 provisional, 0 unresolved) per
  `flow-sdd-ready-gate-v2.md` (PR #124).
- Owner acceptance: all 6 provisional risks accepted with revisit triggers
  preserved, promoting verdict to **PASS for the next approved planning gate**
  per `flow-sdd-action-owner-acceptance.md` (PR #125).
- The 11 constitution-backed sections (HLD-003, HLD-004, HLD-005, HLD-007,
  HLD-008, HLD-009, HLD-010, HLD-013, HLD-014, HLD-015, HLD-016) are
  SDD-ready and may be decomposed.
- The 6 provisional sections (HLD-001, HLD-002, HLD-006, HLD-011, HLD-012,
  HLD-017) must be flagged or deferred during decomposition until specs exist.
  Their revisit triggers are preserved.

## The 11/6 Split

This is the load-bearing constraint from the PASS-for-planning acceptance.

### Decomposable (11 constitution-backed sections)

| Section | Topic |
|---|---|
| HLD-003 | Core model |
| HLD-004 | The task lifecycle |
| HLD-005 | The wait model (fork-join) |
| HLD-007 | Human-in-the-loop: answer and feedback |
| HLD-008 | The baton: the context substrate |
| HLD-009 | The CLI contract |
| HLD-010 | Work routing (mandatory named sessions, soft label affinity) |
| HLD-013 | Concurrency and durability |
| HLD-014 | Recovery: lease, see-and-act reclaim, fence, flaky-mark |
| HLD-015 | The autonomy contract: enforce invariants, delegate judgment |
| HLD-016 | The output layer: outcome and report |

These sections are baked (all have non-TBD HLD-SPECS, non-TBD HLD-VERIFY where
HIGH-risk). Journey 2 may decompose features from them.

### Deferred (6 provisional sections)

| Section | Topic | Risk | Revisit trigger |
|---|---|---|---|
| HLD-001 | What it is (purpose) | MEDIUM | assign when the first spec citing this section is drafted |
| HLD-002 | Vocabulary | LOW | assign when the first spec citing this section is drafted |
| HLD-006 | Escalation triggers | MEDIUM | assign when the first spec citing this section is drafted |
| HLD-011 | Scope boundary | LOW | assign when the first spec citing this section is drafted |
| HLD-012 | Technology | LOW | assign when the first spec citing this section is drafted |
| HLD-017 | Requirements and feature candidates | LOW | assign when the first spec citing this section is drafted |

Journey 2 must **not** decompose features from these sections. If a feature
derived from a decomposable section needs to reference a provisional section,
the runner flags the dependency and preserves the revisit trigger — it does not
invent spec intent for the provisional section.

## HLD-017 Candidate Constraint

HLD-017 lists candidate capabilities (Web UI, HTTP API, Unix sockets, daemons,
worker pools, environment staging, migration tooling, richer UI infrastructure,
React-style reply flows, session-log links, richer reference surfaces, robust
markdown/context views). These are **candidates only**:

- They must not be decomposed into features.
- They must not be treated as committed design surface.
- They must not appear in the target package as requirements or spec inputs.
- Adopting any candidate is a separate future design decision under the
  HLD-011 boundary rule.

Only the **committed design surface** listed in HLD-017 may feed decomposition,
and only insofar as its backing sections (HLD-003/004/005/007/008/009/010/
013/014/015/016) are among the 11 decomposable sections.

## Provenance Caveat

J0-12 remains globally open.

For `flow` only, the scoped status is:

`SCOPED_FLOW_PROVENANCE_ACCEPTED_FOR_J1_PLANNING`

The Journey 1 run and SDD-ready gate were conducted under this scoped
acceptance. The future Journey 2 runner must carry this caveat forward:

> Corrected declared evidence is human-declared Journey 0 evidence for `flow`.
> It is accepted as scoped input for Journey 1 planning/hardening, but it is not
> automatically validated global product truth and must not be generalized to
> other targets.

The Journey 1 gate assessed the resulting HLD as SDD-ready (ACTION with 6
provisional items, promoted to PASS after owner acceptance of the listed risks
with preserved revisit triggers). This status is the basis for Journey 2
planning eligibility.

## Execution Prompt For A Future Run

Use the following prompt only in a separate, explicitly approved Journey 2 run:

```text
You are working in /Users/saffi/code/HLDspec.

Task: execute Journey 2 SDD / Package Preparation for the flow target, using
the SDD-ready HLD from the Journey 1 gate (PASS for planning, 6 accepted
provisional risks).

Target:
/Users/saffi/code/flow

Target HLD:
/Users/saffi/code/flow/HLD.md
SHA-256: 3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0

Purpose:
Compile the SDD-ready Flow HLD into a structured, evidence-anchored target
package per docs/JOURNEY2_PACKAGE_CONTRACT.md. Decompose features from the 11
constitution-backed HLD sections. Flag/defer the 6 provisional sections until
specs exist.

Required source context (read before starting):
- docs/FLOW_JOURNEY2_PLANNING_PROMPT.md (this prompt — the authorization and
  constraints)
- docs/JOURNEY2_PACKAGE_CONTRACT.md (the target package schema and validation)
- docs/JOURNEY2_SDD_COMPLETENESS_GATE.md (coverage and completeness rules)
- docs/JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md (architecture reasoning)
- docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md (inquiry/gap tracking)
- docs/JOURNEY1_SDD_READY_GATE.md (the gate the HLD passed)
- docs/THREE_JOURNEYS.md (journey boundaries)
- docs/flow_journey1_hld_hardening/flow-sdd-ready-gate-v2.md (the gate
  assessment — section audit, §5/§6/§9 checks, RunSkeptic)
- docs/flow_journey1_hld_hardening/flow-sdd-action-owner-acceptance.md (the 6
  accepted risks with revisit triggers)
- /Users/saffi/code/flow/HLD.md (read-only — the SDD-ready HLD)

The 11/6 split (load-bearing constraint):
- DECOMPOSE from these 11 sections: HLD-003, HLD-004, HLD-005, HLD-007,
  HLD-008, HLD-009, HLD-010, HLD-013, HLD-014, HLD-015, HLD-016.
- DEFER/FLAG these 6 provisional sections: HLD-001, HLD-002, HLD-006,
  HLD-011, HLD-012, HLD-017. Each has a revisit trigger: "assign when the
  first spec citing this section is drafted." Do not invent spec intent for
  deferred sections.

HLD-017 candidate capabilities:
- The committed design surface in HLD-017 feeds decomposition only through its
  backing decomposable sections.
- The candidate capabilities list (Web UI, HTTP API, sockets, daemons, pools,
  etc.) must NOT be decomposed, treated as commitments, or appear as
  requirements/spec inputs.

Allowed actions:
- Read the required source context and the target HLD (read-only).
- Decompose features from the 11 constitution-backed sections per
  JOURNEY2_PACKAGE_CONTRACT.md §5 (feature schema, spec-input schema,
  right-sized spec bites).
- Every requirement must cite an (HLD-NNN) anchor from a decomposable section.
- Author constitution.proposed.md as a proposal only — never the applied
  constitution.
- Build feature dependency graph and invocation queue from one ordered_features
  list (parity invariant).
- Apply architecture reasoning per JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md
  (14 required fields, expert lenses, slice quality).
- Flag dependencies on provisional sections with their revisit triggers.
- Track open questions via inquiry ledger, gaps via gap register per
  JOURNEY2_INQUIRY_LEDGER_CONTRACT.md.
- Produce package output in the output path set by the execution
  authorization. Do not write into /Users/saffi/code/flow unless the
  execution authorization explicitly names a path there.
- Validate anchor integrity, manifest integrity, and package binding.

Forbidden actions:
- Do not invoke SpecKit.
- Do not start Journey 3.
- Do not select or install a helper (helper recommendations are advisory).
- Do not mutate /Users/saffi/code/flow beyond the approved package output path.
- Do not write into .specify/ as authoritative (only the generated,
  banner-stamped mirror is allowed).
- Do not create backlog or implementation scope.
- Do not close J0-12 globally.
- Do not decompose features from the 6 provisional sections.
- Do not invent spec intent for provisional sections.
- Do not treat HLD-017 candidate capabilities as committed design surface.
- Do not invent requirements, features, or boundaries with no HLD anchor.
- Do not invent constitution rules not grounded in the HLD.
- Do not invent source-of-truth or data-ownership decisions the HLD/human did
  not make.
- Do not promote a package with uncited spec-input claims, stale anchors,
  diverging graph/queue, wiped CONTRACT-*/DATA-* rules, or NOT_COVERED items.

Required evidence handling:
- Use the 11/6 split as stated — do not reclassify sections.
- Preserve all 6 revisit triggers verbatim.
- Cite only anchors from the 11 decomposable sections in requirements.
- When a feature from a decomposable section touches a provisional section,
  record the dependency and the revisit trigger — do not resolve it.
- Use the committed design surface from HLD-017, not the candidate list.

Stop conditions:
- Any requested action would invoke SpecKit.
- Any requested action would mutate /Users/saffi/code/flow outside the
  approved package output path.
- Any requested action would create backlog or implementation scope.
- Any output starts Journey 3.
- Any feature is decomposed from a provisional section.
- Any HLD-017 candidate capability is treated as a committed requirement.
- Any requirement cites an anchor from a provisional section without flagging
  the dependency and preserving the revisit trigger.
- Any product conflict, authority question, or provenance gap cannot be
  resolved from the approved source context.
- The 11/6 split is reclassified.

Expected outputs:
- Feature boundaries and feature briefs derived from the 11 decomposable
  sections (per JOURNEY2_PACKAGE_CONTRACT.md §5).
- Spec inputs with every requirement citing an (HLD-NNN) anchor.
- Feature dependency graph + invocation queue (parity invariant from one
  ordered_features list).
- Architecture package (14 required fields per
  JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md).
- Constitution.proposed.md (proposal only).
- Engineering guidelines.
- Explicit dependency-on-provisional-section register with revisit triggers.
- Package validation report (anchor integrity, manifest, binding).
- Journey 2 completeness report per JOURNEY2_SDD_COMPLETENESS_GATE.md §9.
- Explicit list of deferred provisional-section items with revisit triggers.
- Explicit statement that SpecKit, Journey 3, helper selection, backlog, and
  implementation remain out of scope unless separately approved.
```

## What This Document Does Not Authorize

- It does not execute the prompt above.
- It does not decompose features.
- It does not build a target package.
- It does not mutate `/Users/saffi/code/flow`.
- It does not invoke SpecKit.
- It does not wire commands.
- It does not start Journey 3.
- It does not create backlog or implementation scope.
- It does not close J0-12 globally.
- It does not treat HLD-017 candidates as implemented commitments.

## Next Action

Review this prompt document. If accepted, issue a separate explicit prompt that
authorizes the Journey 2 execution run and defines the exact target/read/write
paths for that run.
