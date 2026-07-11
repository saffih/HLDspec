# Post-Option-A re-baseline and next-slice decision record

Date: 2026-07-11. Clean-room mode: independently re-derived from current HLDspec and Flow
repository/GitHub state, not from prior summaries or memory.

## Scope and authority of this record

This is a documentation and decision record only. It grants no implementation authority,
no Flow mutation authority, and no SpecKit invocation authority. It does not implement any
selected item. Execution of any item listed below requires a separate, explicitly authorized
task.

## Current state

| | |
|---|---|
| HLDspec main (post-merge) | `40980ed0f0327f6efc02ed1d168153540adb93eb` |
| Flow (`saffih/baton-flow`) main / HEAD | `fa9c0aa87b0ad71de7adf321e7b600e013d61c37` |
| PR #150 | merged (`1ca35ec`) — analyze/later-status evidence recognition |
| PR #151 | merged (`7008733`) — fail-closed branch-identity guard on the same reader |
| PR #152 | merged (`40980ed`) — corrected Option A description in `docs/TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md` |

## Option A completion verification

**STATUS: COMPLETE.** **COMPLETED_BY: PR #150 + PR #151.** **DOC_ALIGNMENT: PR #152.**

Verified directly against current code (`hldspec/next_feature_readiness.py`), not doc claims
alone:

- Analyze/later-status evidence recognition exists: `ANALYZE_COMPLETION_EVIDENCE_STATUSES`
  (includes `ANALYZE_COMPLETED`, `TESTS_PASSED`, `IMPLEMENTED_COMMITTED`, `PUSHED`) gates the
  `READY_FOR_ANALYZE` check as an alternative to an in-spec-dir artifact file.
- Branch identity is fail-closed: missing, empty, non-string, or mismatched branch on
  `next_feature_execution_evidence.json` rejects the record (returns `{}`) rather than passing
  silently.
- `spec_dir` name match and git-ancestry (`commit_sha` reachability) guards are unchanged and
  still enforced.
- HLDspec remains evidence-reader-only: the only production reference to
  `next_feature_execution_evidence.json` is a read (`next_feature_readiness.py`); the only
  writers repo-wide are test fixtures in `tests_v2/test_next_feature_readiness.py`.
- No `DRIVER_OBSERVED` status, enum, or writer exists anywhere in the codebase — every
  occurrence is a doc description of a proposed/deferred evidence class or a test/comment
  asserting its absence.
- No durable SpecKit invocation log was added by any of the three PRs. The pre-existing
  `speckit_invocation_queue.json` (a planning artifact, not an audit log) is untouched.
- No phase or approval semantics changed: `hldspec/state_machine.py` and
  `hldspec/machines/approval_gate.py` have zero diff across the `1ca35ec` and `7008733`
  commits.

This closes the old "stdout-only analyze gap can't be observed" problem the July 2026-07-06/07
decision record was tracking. That record (`flow-post-implement-status-decision-record.md`) is
now superseded on this specific point and should be read as historical context, not current
status.

## Journey 3 current status (Flow, branch-sensitive)

`journey3-status` reports `PASS`, `journey3_phase: READY_FOR_SPECKIT_SPECIFY`,
`binding_status: BOUND_MATCH`, helper `speckit` (`GUIDE_ONLY`/`PROPOSE_COMMAND`, propose-only).

**This is a forward-looking readiness snapshot on Flow's current branch (`main`, HEAD ==
origin/main), not a retrospective proof of feature history.** It says nothing about which
features were previously built; that evidence comes from Flow's merged git history
(PRs #17–#21, ending with feature 025 "Store & Transaction Foundation" implemented and
merged). Treating the readiness snapshot as "the Driver observed prior work" would be a
category error — no provenance/attestation mechanism exists that would support that claim
(see `DRIVER_OBSERVED_STATUS` below).

The `speckit_invocation_queue.json` source-package artifact lists 8 `ordered_features`
(FLOW-F01..F08) as a static plan with no per-feature status tracking. FLOW-F01 (Store &
Transaction Foundation) corresponds to the already-merged feature 025. No HLDspec or Flow
artifact explicitly names a "next" feature; by queue position FLOW-F02 would be next, but that
is an inference from ordering + git history, not an explicit statement from any source.

## Remaining follow-up classification

Re-evaluated from current sources (not from memory or prior summaries). Process and product
items are kept in separate columns; none are closed without direct evidence.

| # | Item | Status | Owner / authority | Blocks current work | Risk if deferred | Blast radius | Reversible | Active PR |
|---|---|---|---|---|---|---|---|---|
| 1 | HLD-009 mandatory session enforcement | Open — phased-deferred per prior C1 owner decision; constitution `CONTRACT-SESSION-ENFORCEMENT` still conflicts with CLI (only `next`/`done`/`escalate`/`split` accept `--session`) | Flow product owner (product/architecture) | No | Low — gap already disclosed in `quickstart.md` | Large (touches every Flow CLI verb) | Yes | None |
| 2 | Escalation-ID / addressability | Open, candidate-only — IDs not rendered in projection nor addressable in `reply()`; documented in a test docstring, not promoted | Unstated (product/architecture) | No | Low — pre-existing, disclosed | Medium | Yes | None |
| 3 | T007 guard-strength residual | Open — test still forces the failure path internally rather than via a fully external trigger; adjudicated as non-blocking at merge time | Unstated (process) | No | Low | Small | Yes | None |
| 4 | `plan.md:94` cosmetic residual (Flow repo) | Open, confirmed by direct read — still says constitution is "PROPOSAL status"; live constitution is ratified/`APPLIED` (Flow commit `696f58d`, Flow PR #15) | Unstated (process, Flow-repo-side) | No | Low — label-only, gate already honors the applied constitution | Small (1 line) | Yes | None |
| 5 | Durable SpecKit invocation log | Open, **not promoted** to `TASKS.md` or `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` — currently lives only in a point-in-time implement record, at risk of being lost | Unstated (process) | No | Medium — the source record itself flags this risk | Small | Yes | None |
| 6 | Real headless `EXECUTE_WITH_APPROVAL` / minimal live-chain proof | Open — explicitly "unproven"/"deliberately deferred" in `TASKS.md` and the backlog; `SpecKitInvoker` + drive-loop are unit-tested only with an injected runner, no real `claude --print` headless run has ever been executed | Technical proof: no authority needed. **Where/how to record and validate the result is entangled with item 5's unresolved contract-placement question**, and target selection + live-execution authorization are unrecorded | No (gated/opt-in capability) | Medium — unproven mechanism could fail silently the first time something relies on it | Medium | Yes (bounded proof), but the *executed* proof is a live external invocation — the nearest thing in this table to the SpecKit-execution boundary this record does not cross | None |
| 7 | `DRIVER_OBSERVED` provenance implementation | Open, **proposed only** — the evidence contract explicitly states no code implements this vocabulary and scopes designing it as out-of-scope for now | Product/architecture, deliberately unscheduled | No | Low — explicitly out of scope by design | Large if built | Yes | None |
| 8 | Next Flow product feature | Open, **absent from every HLDspec/Flow source** — no `TASKS.md` in Flow, no roadmap language in Flow's README, and the prior decision record explicitly flags this as a separate open product question | Flow product owner — pure product call | No | Low — just idle | N/A | N/A | None |
| 9 | `TOOLCHAIN_DRIVER_EVIDENCE_CONTRACT.md` §5/§8 wording residual | Open, confirmed by direct read at lines ~124 and ~200-201 — still describe the now-implemented evidence-recognition slice as an upcoming "driver-observability slice," which is exactly the framing PR #152 corrected §1 to reject. This conflates completed work (Option A) with item 7, which is deliberately unscheduled | Unstated (process) | No | Low — cosmetic but genuinely confusing given item 7's status | Small (2 lines, 1 file) | Yes | None (found during this task's Phase 1 PR review; not fixed there, per no-modify-PR-#152 constraint) |

Readiness evidence (items covered by the Option A verification above), a durable invocation
audit log (item 5), `DRIVER_OBSERVED` (item 7), manual-attested/dev receipts, and Flow
product-feature selection (item 8) are five distinct evidence/decision classes and are not
interchangeable. No item above is closed without the direct evidence cited in its row.

**NEXT_HLDSPEC_PROCESS_SLICE candidates:** items 3, 4, 5, 6, 9 (no product/architecture
authority required for the *process* portion of each).
**NEXT_FLOW_PRODUCT_FEATURE:** item 8 — not determinable from any current source; requires
owner/product authority. The process track above does not, and must not, silently choose it.

## Candidate comparison and selection

Applying the dominance rule (a candidate must clearly win on: removing a current blocker or
recurring safety-margin gap; satisfying all prerequisites; clear ownership/authority; direct
testability; being small **and** reversible; not bundling distinct evidence classes; not
requiring an unresolved product decision; not depending on an unproven execution path unless
it *is* the bounded proof of that path):

- **Item 6** is the only candidate that addresses a real, currently-unproven safety-margin gap
  (an untested live-invocation code path). It satisfies the "bounded proof of an unproven
  path" exception by definition. But it fails the small-and-reversible test on the *execution*
  side (a real headless invocation is the closest thing in this record's scope to the
  SpecKit-execution boundary this task does not cross), and its own evidence splits authority:
  the technical proof needs no product sign-off, but *where and how the result is recorded* is
  entangled with item 5's unresolved contract-placement question, and *what it runs against*
  (real Flow feature vs. synthetic fixture) is an unrecorded target-selection decision.
- **Item 9** cleanly satisfies every criterion — small, reversible, no authority required,
  directly fixes a real self-contradiction this task's own Phase 1 review surfaced. But it is,
  by the letter of the dominance rule, exactly the "smallest cosmetic cleanup" pattern the rule
  says not to auto-select by default.
- **Item 5** is small and safe (promote a known gap into the durable backlog so it is not lost)
  but its independent value is modest, and its *result-placement* question is the same
  unresolved question entangled in item 6.
- Items 1, 2, 8 require product/architecture authority this record does not have.
- Item 3 and item 4 are low-value, already-adjudicated or purely cosmetic Flow-repo residuals.
- Item 7 is deliberately unscheduled by the evidence contract itself; selecting it would
  reopen a decision that was already made.

**No candidate clearly dominates.** The highest-value candidate (6) is not clean; the
cleanest candidate (9) is not high-value and is the explicitly disfavored default. This
record does not select a next slice. Per the governing decision rule, that is a valid,
first-class outcome, not a failure to decide.

## Ranked owner-decision packet

1. **Item 6 — real headless live-chain proof.** Highest derisking value (closes a real,
   currently-unproven safety-margin gap in the live-invocation path). Blocked on three
   unrecorded decisions: (a) where/how to durably record the proof's result — entangled with
   item 5; (b) what target it runs against (a real Flow feature vs. a disposable synthetic
   fixture); (c) explicit authorization for a live external invocation, since this is the
   nearest thing to the SpecKit-execution boundary a process-only record cannot cross.
   *Owner question: authorize a bounded live-chain proof, and if so, against what target and
   with what result-recording contract?*
2. **Item 9 — §5/§8 wording residual.** Cleanest, safest, zero-authority-required option;
   fixes a self-contradiction this task's own review discovered in a canonical contract doc.
   Low standalone value. Can be executed regardless of how item 6 resolves.
3. **Item 5 — promote the durable invocation log to `TASKS.md`/backlog.** Small, safe,
   no owner decision needed for the promotion itself; only its *design* is undecided (and only
   matters once item 6's execution needs a place to record results).
4. **Item 3 — T007 guard-strength residual.** Low priority; already reviewed and accepted as
   non-blocking at its original merge gate.
5. **Item 1 / Item 2 — HLD-009 session enforcement, escalation-ID/addressability.** Larger
   product/architecture design slices; require an owner decision before any process work can
   start, independent of items 1–9 above.
6. **Item 4 — `plan.md:94` (Flow repo).** Trivial, one line, lowest priority.
7. **Item 7 — `DRIVER_OBSERVED`.** Deliberately unscheduled; no action recommended.
8. **Item 8 — next Flow product feature.** Pure product/owner call, entirely separate from
   the process track; not something a process-only authority can select.

**Owner decision needed:** which of items 6 / 9 / 5 (or none) to authorize next, and — if
item 6 — the target and result-recording contract for the live-chain proof. Items 9 and 5 do
not require resolving item 6 first and can be authorized independently or in parallel.

## Explicit non-authorizations

This record does not implement any item above, does not run SpecKit, does not mutate the Flow
repository, does not introduce `DRIVER_OBSERVED`, does not create an invocation log, does not
implement session enforcement, and does not modify the Flow product feature queue. Execution
of any selected item requires a separate, explicitly scoped and authorized task.

## RunSkeptic receipt

- Source read: `saffih/skeptic` `origin/main` commit `b071899a5e5cebcaf047ca559bedd368ae092f2f`,
  `skeptic.md` blob `1985bd385380ff57fe610099c4cab1e91c551e86` (read in full; unchanged between
  Phase 1 and Phase 2 fetches).
- Companion files read: none (`skeptic-questions.md` not needed — runtime core sufficient).
- Permission mode: read-only / patch-local (this file only).
- DONE: exactly one next slice selected, or an explicit owner-decision packet recorded, in
  exactly one new unmerged file — achieved via the owner-decision packet path.
- Major steps run: Gate, Fundamental Scan, Map, Universal Questions, all Thinkers (CH, OM, FE,
  PO, KT, SH), Structural Checks, selective Domain Checks, Confidence, Stabilize, Evidence,
  Decide, Verify, Learn.
- Thinkers: CH (weak safety margin in unproven live-invocation path — material, drives item 6's
  rank); OM (item 9 flagged as unnecessary-to-auto-select despite being structurally minimal —
  false-simplicity risk if chosen only because it's easy); FE (Option A completion claims are
  OBSERVED against current code, not just doc text); PO (checked that Option A "complete" claim
  is falsifiable — verified against `hldspec/next_feature_readiness.py` directly, not doc
  assertions alone; checked the readiness-snapshot-as-provenance claim and rejected it as a
  category error); KT (a process-only authority selecting a product feature, or silently
  promoting a deferred `DRIVER_OBSERVED` item, would be an unfair/harmful universalization —
  avoided); SH (opposing forces = highest-value-but-entangled item 6 vs. clean-but-low-value
  item 9; no forced middle taken — both ranked honestly, no default dominance claimed).
- Evidence used: OBSERVED (direct code/doc reads across HLDspec and Flow), HISTORICAL (merged
  commit/PR record), REPRODUCED (test suite run: 2662/2662 passed across `tests_v2` + `tests`
  during Phase 1, unaffected by this Phase 2 file).
- Decision path: no FIX applicable (nothing broken); no DECOMPOSE (ambiguity is about which
  slice to authorize, not about splitting a single unsafe change); CONFLICT class resolved as
  owner-decision packet per governing rule, not blocked as unsafe.
- Verification performed: single-file diff scope check; adversarial checks in the PR body;
  hidden/control-character and cross-source consistency checks before commit.
- Unresolved conflicts / unknowns: contract-placement for a durable invocation-log result;
  target selection for a live-chain proof; HLD-009 and escalation-ID priority ordering; Flow's
  next product feature. All explicitly owner-authority items, not blocking this record.
- Final output category: **HANDLED** (record is accurate, evidence-backed, and correctly
  declines to auto-select where no candidate dominates).
