# Flow Journey 1 Planning Scope

**Status:** planning scope only. This doc bounds a future Journey 1 planning
effort for the `flow` target and defines the human confirmation checklist for
the 10 declared evidence items from RT-2. It authorizes nothing by itself.

- This does not start Journey 1 execution.
- This does not authorize HLD writing.
- This does not authorize SpecKit.
- This does not authorize command wiring.
- This does not mutate `/Users/saffi/code/flow`.
- This does not create backlog or implementation scope.
- Declared evidence remains planning evidence until human-confirmed.
- All 10 declared items require human confirmation before authoritative HLD
  writing.
- J0-17 remains **BLOCKED** after this doc.

## Purpose

Turn the PR #113 justification ("Journey 1 planning is justified for
consideration") into a bounded planning scope: what Journey 1 planning may
inspect, what it may produce, and the exact human confirmation checklist that
must be completed before any authoritative HLD writing.

## Source inputs

- `docs/FLOW_JOURNEY1_PLANNING_JUSTIFICATION.md` (PR #113 — the decision input;
  not re-argued here)
- `docs/journey0_real_target_dry_runs/flow-journey0-dry-run.md` (RT-1: ACTION)
- `docs/journey0_real_target_dry_runs/flow-journey0-declared-evidence-dry-run.md`
  (RT-2: PASS; DECLARED-001…010; provenance caveat)
- `docs/THREE_JOURNEYS.md` (Journey 1 boundary)
- `docs/JOURNEY0_SCHEMA_AND_WIRING_PLAN.md` (PASS semantics; stabilization table)
- `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` (J0-12 PROVENANCE_OPEN, J0-16
  DO_NOT_WIRE, J0-17 BLOCKED)

No target-repo files were read for this doc. No new evidence was collected. No
target file contents or snippets appear here.

## What Journey 1 planning may do

Planning (not execution) may:

- **Inspect** only: the RT-1/RT-2 reports, the PR #113 justification doc, the
  Journey 0/1 contract docs listed above, and `docs/JOURNEY1_SDD_READY_GATE.md`.
  No target-repo reads; no re-runs against the target.
- **Cite** evidence only by RT-2 accepted refs — COLLECTED-001…003 and
  DECLARED-001…010 — using the DECLARED id and RT-2 provenance column only.
- **Use** the RT-2 HLD update-plan section mapping (five candidate sections) as
  the candidate structure for a future flow HLD.
- **Produce** planning documents in HLDspec `docs/` only: a Journey 1 plan
  outline, the human confirmation pass for this checklist, and
  PASS/ACTION/BLOCKED expectations per `docs/JOURNEY1_SDD_READY_GATE.md`.

## What Journey 1 planning must not do

- Start Journey 1 execution (HLD authoring/hardening) — J0-17 is BLOCKED.
- Write or edit any HLD content or HLD section prose, in HLDspec or the target.
- Invoke SpecKit; prepare Journey 2 packaging; perform Journey 3 helper handoff.
- Wire Journey 0 or Journey 1 into the command surface (J0-16 DO_NOT_WIRE).
- Mutate `/Users/saffi/code/flow` or read any target path (including the three
  RT paths — planning works from the recorded reports only).
- Create backlog or implementation scope for `flow`.
- Expand, merge, reinterpret, or add to the declared evidence items, or invent
  new product claims.
- Treat declared evidence as verified product truth.

## Human confirmation checklist

Ten items, one per DECLARED id from RT-2. Every item shares two fixed fields:

- **May be used for planning before confirmation:** yes (scope/structure only,
  cited by id + RT-2 provenance).
- **May anchor authoritative HLD writing before confirmation:** no.

A human confirms each item by answering its confirmation question with
confirm / amend / reject. An amended or rejected item returns to Journey 0
declared-evidence review; it does not silently carry into Journey 1.

### DECLARED-001 — durable-baton task management (capability)

- **Confirmation question:** Is "task management with a durable baton across
  AI handoffs" still the core capability of flow as you intend it today?
- **Why confirmation is needed:** It is the anchor capability every other item
  hangs on; drafted from README.md/HLD-001, not ratified.
- **Risk if wrong:** The whole HLD is framed around the wrong product core.

### DECLARED-002 — fork-join workflow capability

- **Confirmation question:** Are escalation, splitting, and dependency gates
  (fork-join) all current intended capabilities, none dropped or superseded?
- **Why confirmation is needed:** Drafted from HLD-004/HLD-005 fragments that
  may contain stale design.
- **Risk if wrong:** HLD hardens abandoned mechanics as product commitments.

### DECLARED-003 — AI session runners as actors

- **Confirmation question:** Are AI session runners (Claude, Devin, Codex) via
  CLI the intended primary machine actors, and is the named set current?
- **Why confirmation is needed:** Specific runner names may be examples, not
  product commitments.
- **Risk if wrong:** Actor model over-commits to specific vendors/tools.

### DECLARED-004 — human operator as actor

- **Confirmation question:** Is the human operator's role (creates tasks,
  steers, holds authority decisions) complete and correctly bounded?
- **Why confirmation is needed:** Authority boundaries between human and AI
  actors are product decisions, not derivable from files.
- **Risk if wrong:** HLD misassigns decision authority between human and AI.

### DECLARED-005 — CLI in; SQLite state + markdown projections out ⚠ special review

- **Confirmation question:** Is **SQLite** product surface (a promised,
  user-visible storage contract) or an implementation detail (replaceable
  without product change)? Same question for markdown projections.
- **Why confirmation is needed:** The item names implementation technology;
  anchoring HLD content on it would freeze an implementation choice as product
  truth.
- **Risk if wrong:** HLD locks in a storage technology as a contract, blocking
  legitimate implementation changes — or omits a real user-facing contract.

### DECLARED-006 — human replies drive state transitions

- **Confirmation question:** Is "human replies in; task state transitions +
  baton updates out" the intended interaction contract, with no other
  input/output channels missing?
- **Why confirmation is needed:** Input/output surface completeness cannot be
  inferred from three files.
- **Risk if wrong:** HLD omits or misstates a primary interaction channel.

### DECLARED-007 — core task loop workflow

- **Confirmation question:** Is the loop create → claim → read baton → work →
  note → done/escalate/split → loop the current intended lifecycle, with no
  states added or removed since core.md was written?
- **Why confirmation is needed:** Drafted from core.md, which may lag current
  intent.
- **Risk if wrong:** HLD canonizes an outdated lifecycle; downstream
  decomposition builds wrong states.

### DECLARED-008 — escalation/resume workflow

- **Confirmation question:** Is escalate → human replies → task wakes →
  re-claim → continue the current intended escalation flow?
- **Why confirmation is needed:** Escalation semantics come from core.md and
  HLD-005 fragments; they interact with DECLARED-009.
- **Risk if wrong:** HLD encodes a resume protocol the product no longer
  follows.

### DECLARED-009 — one open escalation per task ⚠ special review

- **Confirmation question:** Is the one-open-escalation-per-task structural
  invariant **current product intent**, or **stale design residue** from
  HLD-005?
- **Why confirmation is needed:** It is an interpreted invariant from a single
  HLD fragment, not an observed behavior; invariants are the most expensive
  claims to encode wrongly.
- **Risk if wrong:** A stale invariant becomes a hard product constraint the
  HLD enforces forever — or a real invariant is dropped and concurrency bugs
  are designed in.

### DECLARED-010 — no web UI / HTTP / sockets / daemons / pools

- **Confirmation question:** Is the exclusion list (no web UI, HTTP API, Unix
  sockets, daemons, pools — HLD-011) the complete and current set of
  intentional product limits?
- **Why confirmation is needed:** Negative scope defines the product boundary;
  it must be a decision, not residue.
- **Risk if wrong:** HLD forbids a direction the owner actually wants, or
  silently permits scope creep.

## Evidence usable before confirmation

- COLLECTED-001…003 (structural: README.md, HLD.md, core.md existence) and
  DECLARED-001…010 may be used for **planning scope and structure**: naming
  candidate HLD sections, ordering planning work, and identifying open
  questions. Citation is by evidence id and RT-2 provenance column only.
- Generic file evidence cannot PASS alone and confers no product authority
  (RT-1 proved this).

## Evidence blocked from HLD writing until confirmation

All 10 declared items (DECLARED-001…010). None may anchor authoritative HLD
content until the human confirmation pass above is complete, with
DECLARED-005 and DECLARED-009 explicitly resolved. There is no partial
unlock: confirmation of some items does not authorize HLD writing for those
items while others are open.

## Provenance caveat

Carried forward verbatim from `docs/FLOW_JOURNEY1_PLANNING_JUSTIFICATION.md`:

> Declared evidence is user-approved but **not automatically validated as
> product truth**. It was drafted by reading the three allowed target files and
> approved by a human for dry-run use, not ratified as authoritative product
> definition. Additionally, the full Journey 0 provenance model is still open
> (backlog J0-12: PROVENANCE_OPEN). Any Journey 1 planning output must carry
> this caveat forward verbatim, and HLD writing must not begin until the
> declared items are human-confirmed as product truth.

## Stop conditions

Stop and return to human review if any of these occur during planning:

- A declared evidence item is contradicted, reinterpreted, or expanded.
- Planning output starts to contain HLD section prose (that is HLD writing).
- Any step requires reading target paths or re-running against the target.
- Any step requires command wiring, SpecKit invocation, or target mutation.
- The provenance caveat would be weakened or dropped.
- The confirmation checklist is treated as complete without an explicit human
  confirm/amend/reject answer per item.
- Anything implies J0-17 is lifted.

## Exit criteria for a future Journey 1 execution prompt

A Journey 1 execution prompt for `flow` may be drafted (still requiring human
approval to run) only when all of the following hold:

1. All 10 checklist items have an explicit human confirm/amend/reject answer.
2. DECLARED-005 is resolved as product surface or implementation detail.
3. DECLARED-009 is resolved as current intent or stale residue.
4. Amended/rejected items have been re-reviewed through Journey 0
   declared-evidence review and the resulting evidence set is re-approved.
5. J0-17 is explicitly unblocked by human/project approval after blocker and
   stabilization review (including J0-12 provenance disposition).
6. The provenance caveat is carried into the execution prompt verbatim.

Until then, Journey 1 execution remains forbidden.

## Next action

Prepare the human confirmation pass for the 10 declared evidence items using
the checklist above (confirm / amend / reject per item, with DECLARED-005 and
DECLARED-009 answered explicitly). Do not auto-start Journey 1 execution;
J0-17 remains BLOCKED until human and project approval.
