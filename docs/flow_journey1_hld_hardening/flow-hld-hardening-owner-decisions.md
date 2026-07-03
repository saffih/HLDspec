# Flow HLD Hardening Owner Decisions

## Purpose

Record the project owner's answers (2026-07-03) to the five open questions in
`flow-hld-hardening-draft.md` (PR #119), so a later, separately approved
target HLD patch has decided product direction to follow. This is a decision
record only.

- This does not modify `/Users/saffi/code/flow/HLD.md`.
- This does not write final authoritative HLD content.
- This does not invoke SpecKit.
- This does not wire commands.
- This does not start Journey 2 or Journey 3.
- This does not create backlog or implementation scope.
- This does not close J0-12 globally.
- A separate explicit approval is required before any target HLD patch.

## Source inputs

- `docs/flow_journey1_hld_hardening/flow-hld-hardening-draft.md` (PR #119)
- `docs/flow_journey1_hld_hardening/flow-journey1-readiness-report.md` (PR #119)
- `docs/FLOW_DECLARED_EVIDENCE_CONFIRMATION.md` (PR #115)
- `docs/journey0_real_target_dry_runs/flow-journey0-corrected-declared-evidence-dry-run.md`
  (PR #116)
- Owner decision block `FLOW_HLD_HARDENING_OWNER_DECISIONS`, provided by the
  project owner on 2026-07-03.

No target repo files were read for this record.

## PR #119 BLOCKED basis

The readiness report's verdict is **BLOCKED** (gate §10: `unresolved > 0`),
on two blocker-class contradictions between the current target HLD and
ratified owner decisions:

1. **Escalation concurrency.** HLD-005/007/009/014/015 encode a
   one-open-escalation-per-task structural invariant; amended DECLARED-009
   (owner decision 2026-07-03) ratifies concurrent open escalations.
2. **Out-of-scope list.** HLD-011 (and the README mirror) asserts the
   exclusion list as intentional product limits; old DECLARED-010 was
   rejected as slicing residue and replacement DECLARED-010 is the accepted
   boundary rule.

Provisional (ACTION-class) items remain: `HLD-SPECS: TBD` ×5 and
`HLD-RESOURCES: TBD` on HLD-011; markdown projection roles not yet stated;
declared transition gaps; structural completeness (gate §17). BLOCKED never
promotes; nothing passed to Journey 2.

## Owner decisions

Recorded verbatim from `FLOW_HLD_HARDENING_OWNER_DECISIONS` (2026-07-03).

### Question 1 — Markdown projection semantics

**Decision:** Markdown projections are product surface and may be used as an
agent integration and handoff surface, not only as a human-facing stable
format. Agents may read projections directly when those projections preserve
stable IDs, task references, baton/context state, reply context, and links to
relevant reports/logs. The canonical durable state may remain elsewhere, but
the HLD must not say markdown is "never an input" if agent handoff and
continuation depend on readable projections.

**Note:** Markdown roles are: agent integration/handoff, context state for
work in progress, user-facing context and reporting.

### Question 2 — Flaky mark and concurrent escalations

**Decision:** Multiple escalations may be open concurrently for a task.
Flaky/blocked/orphaning semantics must be scoped to the specific escalation,
dependency, or task-state issue they refer to, rather than treated as one
global task-level escalation slot. Each escalation needs stable ID/reference,
owner/reply routing, status, relation to task/baton context, and clear
wake/re-claim behavior.

**Note:** The old one-open-escalation invariant is stale. The replacement
rule is traceable concurrent escalations with clear references and routing.

### Question 3 — Exclusion list rework

**Decision:** The old HLD-011 exclusion list should not remain as product
limits. Web UI, HTTP API, sockets, daemons, worker pools, staging, migration
tooling, richer UI infrastructure, React-style reply flows, fork/join,
dependency gates, multiple escalations, session-log links, task/report/log
references, and robust markdown/context views are all allowed candidate
capabilities when they support the core baton/context-management goal.
Existing absences may be described as current implementation status, not
intentional product exclusions.

**Note:** The replacement boundary rule is: no interface or infrastructure
may bypass or weaken baton/context integrity, durable task state, stable IDs,
explicit references, escalation traceability, session/log links,
copy-pasteable context, or human authority over decisions.

### Question 4 — TBD metadata

**Decision:** Replace raw TBD metadata where there is enough
confirmed/corrected evidence to state intent. Where evidence is still
insufficient, mark the item explicitly provisional with a revisit trigger
instead of leaving unqualified "TBD." Do not fake specificity.

**Note:** HLD-SPECS and HLD-RESOURCES should distinguish supported spec
intent from provisional metadata.

### Question 5 — Requirements / feature-candidate section

**Decision:** Add an explicit requirements / feature-candidate section.
Existing role-tagged sections are not enough because the HLD needs to
distinguish committed current product surface from allowed future/candidate
capabilities that were previously sliced out but are now back in scope.

**Note:** This section should prevent both errors: treating candidate
capabilities as excluded forever, and treating every candidate as immediately
implemented.

## Decision implications

- All five open questions from the hardening draft are now decided. The two
  blocker-class contradictions have decided resolutions (Questions 2 and 3);
  the provisional items have decided dispositions (Questions 1, 4, 5).
- Question 3's candidate-capability list names capabilities as *allowed
  candidates* under the boundary rule — it does not commit any of them as
  implemented or scheduled product surface, and it does not create backlog or
  implementation scope.
- These decisions guide a future target HLD patch; they are not themselves
  HLD wording. Final HLD prose remains a human-reviewed output of that
  separately approved patch.
- The implementation/tests that currently enforce the one-open-escalation
  invariant are out of Journey 1 scope; only the HLD-level product claim is
  in scope for the future patch.

## Future target HLD patch scope

A later, separately approved patch to `/Users/saffi/code/flow/HLD.md` (and
the README "What it is not" mirror) may change, per these decisions:

**Allowed sections:** HLD-001, HLD-003, HLD-005, HLD-007, HLD-008, HLD-009,
HLD-011, HLD-012, HLD-014, HLD-015, HLD-016; README "What it is not" mirror;
a new requirements/feature-candidate section; metadata fields `HLD-SPECS` on
HLD-001/002/006/011/012 and `HLD-RESOURCES` on HLD-011.

**Must address:**

- Remove the one-open-escalation-per-task invariant as a product constraint
  across HLD-005/007/009/014/015 and encode traceable concurrent escalations
  (Question 2), including scoped flaky/orphaning semantics in HLD-014.
- Rework HLD-011 and the README mirror: exclusion list becomes current
  implementation status plus candidate capabilities, governed by the
  replacement DECLARED-010 boundary rule (Question 3).
- State the three markdown projection roles and remove the unqualified
  "never an input" claim, preserving the canonical-durable-state principle
  (Question 1).
- Resolve `TBD` metadata per Question 4 (real intent or explicitly
  provisional with revisit triggers).
- Add the requirements/feature-candidate section (Question 5).

**Must not address:** implementation or test changes in the target repo;
SpecKit invocation; command wiring; Journey 2/3 work; backlog or
implementation scope; J0-12 global closure; generalizing scoped flow
provenance to other targets.

**Remaining human review gates:** (1) explicit approval of the specific
target HLD patch, naming exact target write paths, before any target write;
(2) human review of the final HLD wording produced by that patch; (3) re-run
of the SDD-ready gate assessment after the patch.

**Expected next verdict after patch:** ACTION (then PASS after metadata
completion and recorded human risk-acceptance), per the readiness report's
expected trajectory.

## Remaining forbidden actions

- Mutating any file under `/Users/saffi/code/flow` without the separate
  explicit patch approval naming exact write paths.
- Treating this record or the hardening draft as authoritative HLD content.
- Invoking SpecKit; wiring commands; starting Journey 2 or Journey 3.
- Creating backlog or implementation scope from these decisions.
- Closing J0-12 globally or generalizing flow provenance to other targets.
- Treating declared evidence as validated global product truth.

## Stop conditions

A future run applying these decisions must stop if:

- the target HLD patch approval is missing, or does not name exact target
  write paths;
- the target has changed since the PR #119 no-mutation hashes were recorded
  (re-verify before patching);
- applying a decision would require inventing product truth beyond this
  record — return to the owner instead;
- any decision here conflicts with a newer owner decision.

## Next action

Ask the human/project owner whether to approve a specific target HLD patch to
`/Users/saffi/code/flow/HLD.md` (and the README mirror), scoped exactly as
above. Never auto-modify the target HLD.
