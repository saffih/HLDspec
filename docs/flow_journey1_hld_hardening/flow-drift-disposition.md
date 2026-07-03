# Flow Drift Disposition

Date: 2026-07-03

Status: **RATIFIED** — owner decisions recorded 2026-07-03
(`FLOW_SDD_DRIFT_OWNER_DECISIONS`).

## Purpose

Classify the six drift items from the SDD-ready gate re-run (PR #122) against
the formal SDD-ready gate criteria (`docs/JOURNEY1_SDD_READY_GATE.md`), and
map the formal unresolved/provisional items to their owner decisions.

This is a ratified disposition record. It does not modify
`/Users/saffi/code/flow`, invoke SpecKit, start Journey 2 or Journey 3, or
create implementation scope.

## Gate re-run drift items vs formal gate criteria

The SDD-ready gate (§5) defines SDD-ready as "safe to compile" — clear,
bounded, coherent, and complete enough for Journey 2. It explicitly states:

> SDD-ready does **not** mean fully specified or implementation-detailed.

However, §9 blocks on "unsourced claims" and "unresolved contradictions," and
§17 notes that "a human reviewer remains responsible for structural
completeness" beyond what the automated count catches. The formal
`unresolved`/`provisional` counts alone do not cover every gate dimension.

The gate re-run found six drift items. The classification below separates
implementation gaps (non-blocking per §5) from items where the HLD overstates
current behavior (HLD patch required per owner decision).

| # | Drift item | Category | Disposition | Rationale |
|---|---|---|---|---|
| 1 | `answer`/`feedback` split not fully implemented | Implementation gap | Non-blocking | HLD transition gaps (HLD-007/009/014) already declare this as provisional by design; the readiness report confirmed it "already honest in the HLD" |
| 2 | Mandatory session enforcement not fully implemented | HLD overstated | HLD patch required | Owner decision: HLD is overstated if it claims full enforcement as current working behavior. Patch must distinguish required invariant (session linkage mandatory for baton/task continuity, context integrity, escalation traceability) from current implementation status. Not an implementation blocker if HLD accurately marks both. |
| 3 | Explicit `reclaim` behavior not fully implemented | HLD overstated | HLD patch required | Owner decision: HLD is overstated if it claims full reclaim as current working behavior. Patch must distinguish required reclaim semantics (traceable, tied to specific escalation/dependency/task-state, not relying on old one-open-escalation invariant) from current implementation status. Not an implementation blocker if HLD accurately marks both. |
| 4 | Escalation owner, reply routing, explicit status incomplete | Implementation gap | Non-blocking | Covered by owner decision Q2 (concurrent escalations); HLD patch will state the decided design; implementation is downstream |
| 5 | Report layer and richer reference/projection surface incomplete | Implementation gap | Non-blocking | Covered by owner decision Q1 (markdown projection roles); HLD patch will state the decided design; implementation is downstream |
| 6 | Docs/tests mix hardened semantics with v1 characterization | Flow-side quality | Non-blocking | Flow repo quality item; does not affect HLD text coherence or metadata completeness |

Items 1, 4, 5, 6 are implementation status, non-blocking per §5. Items 2 and
3 are HLD overstatements resolved by the owner's general rule: make the HLD
truthful — no overstated current-behavior claims — then implementation gaps
may remain as non-blocking follow-up if accurately scoped.

## Owner decisions on items 2 and 3

Source: `FLOW_SDD_DRIFT_OWNER_DECISIONS` (2026-07-03).

### Item 2 — Mandatory session enforcement

The HLD is overstated if it claims mandatory session enforcement as fully
current working behavior. The HLD patch must distinguish:

- **Required invariant:** session linkage must be mandatory for operations
  where baton/task continuity, context integrity, or escalation traceability
  depends on it.
- **Current implementation status:** state accurately what enforcement exists
  now, without claiming full enforcement if partial.

Not an implementation blocker for SDD-ready if the HLD accurately marks
current status and required invariant.

### Item 3 — Explicit reclaim behavior

The HLD is overstated if it claims explicit reclaim is fully current working
behavior. The HLD patch must distinguish:

- **Required reclaim semantics:** reclaim/wake behavior must be traceable,
  tied to the relevant escalation/dependency/task-state issue, and must not
  rely on the old one-open-escalation invariant.
- **Current implementation status:** state accurately what reclaim support
  exists now, without claiming full support if partial or implicit.

Not an implementation blocker for SDD-ready if the HLD accurately marks
current status and required invariant.

### General rule

Do not force implementation changes for items 2 and 3 in this slice. First
make the HLD truthful and SDD-ready: no overstated current-behavior claims,
no unresolved owner decisions, no raw provisional claims without revisit
trigger. Implementation gaps may remain listed as non-blocking follow-up if
they are accurately scoped.

## Formal gate blockers and their owner decisions

The readiness report (PR #119) identified the formal gate counts:
`unresolved = 2`, `provisional >= 4`. All have owner decisions (PR #120).

### Unresolved items (BLOCKED class)

| # | Item | Owner decision | Status |
|---|---|---|---|
| 1 | Escalation concurrency: HLD-005/007/009/014/015 encode one-open-escalation invariant; DECLARED-009 ratifies concurrent escalations | Q2: Multiple concurrent escalations with stable ID, owner, routing, status, context | **Resolved in v2 HLD** — HLD-005 encodes concurrent escalations; invariant text removed |
| 2 | Out-of-scope list: HLD-011 asserts exclusion list as product limits; DECLARED-010 rejected as slicing residue | Q3: Exclusion list becomes current implementation status + candidate capabilities under replacement boundary rule | **Resolved in v2 HLD** — HLD-011 retires exclusion list; boundary rule stated |

### Provisional items (ACTION class)

| # | Item | Owner decision | Status |
|---|---|---|---|
| 3 | `HLD-SPECS: TBD` on HLD-001/002/006/011/012; `HLD-RESOURCES: TBD` on HLD-011 | Q4: Replace with real intent where evidence exists; mark explicitly provisional with revisit trigger where insufficient | **Resolved in v2 HLD** — all say "provisional (...revisit at the next SDD-gate assessment)"; HLD-RESOURCES on HLD-011 filled |
| 4 | Markdown projection roles not stated; HLD says "never an input" | Q1: Three product-surface roles (agent integration, context state, user-facing reporting); remove "never an input" | **Resolved in v2 HLD** — HLD-003 states three roles |
| 5 | Transition gaps (answer/feedback naming, anonymous-path policy C) | Covered by Q2/Q3 scope; already honest in HLD as provisional by design | **Resolved in v2 HLD** — HLD-017 records implementation gaps truthfully |
| 6 | Structural completeness: no explicit requirements/feature-candidate section | Q5: Add explicit requirements/feature-candidate section | **Resolved in v2 HLD** — HLD-017 added |

## HLD v2 already addresses all seven items

Verified 2026-07-03: Flow HLD v2 (promoted in Flow PR #13) already
incorporates all owner decisions and drift dispositions. No additional target
HLD patch is required.

| # | Item | Where resolved in v2 HLD |
|---|---|---|
| 1 | Remove one-open-escalation invariant (Q2) | HLD-005 encodes concurrent escalations; invariant text removed from HLD-005/007/009/014/015 |
| 2 | Rework exclusion list (Q3) | HLD-011: "There is no exclusion list"; boundary rule stated; README mirror updated |
| 3 | State markdown projection roles (Q1) | HLD-003: three roles stated; "never an input" removed |
| 4 | Resolve TBD metadata (Q4) | All HLD-SPECS: "provisional (...revisit at the next SDD-gate assessment)" — explicitly provisional with revisit trigger (§8 acceptable) |
| 5 | Add feature-candidate section (Q5) | HLD-017 added: committed design vs candidates vs implementation status |
| 6 | Session enforcement: distinguish design from implementation (item 2) | HLD-017: "optional session naming (not yet the mandatory named sessions of HLD-009/010)"; global header: "This document states the target design" |
| 7 | Reclaim: distinguish design from implementation (item 3) | HLD-017: "lease-based reclaim with escalate-on-repeat (not yet the see-and-act reclaim verb of HLD-014)" |

The v2 HLD uses a centralized gap-tracking pattern:
- Sections HLD-001..016 state the **target design** (authoritative)
- HLD-017 records the **design-vs-implementation gap**
- The document header declares this separation explicitly
- The README usage section notes the gap in plain language

This satisfies the owner's general rule: the HLD is truthful — no overstated
current-behavior claims. Design sections state intent; HLD-017 records what
the implementation does not yet match.

## Remaining action

No target HLD patch needed. Re-run the SDD-ready gate against the current v2
HLD with a fresh formal assessment.

Expected formal counts:
- `unresolved = 0` (both contradictions resolved in v2: escalation concurrency
  and exclusion list)
- `provisional > 0` (HLD-SPECS metadata is explicitly provisional with
  revisit triggers on five sections)
- Expected verdict: **ACTION** (per gate §10: `unresolved == 0` and
  `provisional > 0` → `HLD_READY_WITH_ACTIONS`)

ACTION promotes to PASS after the human explicitly accepts the listed risks
(gate §10 promotion rule).

## Required next steps

1. **Re-run the SDD-ready gate** against the current v2 HLD.
2. **Do not** start Journey 2 or Journey 3 regardless of the re-run verdict.

## Boundaries

- No target mutation needed or performed.
- No SpecKit invocation.
- No Journey 2 or Journey 3.
- No backlog or implementation scope.
- No J0-12 global closure.
- Implementation gaps are recorded in HLD-017, not resolved — they are
  downstream of the SDD-ready gate and are not gate criteria (§5).
