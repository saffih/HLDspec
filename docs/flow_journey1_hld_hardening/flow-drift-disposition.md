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
| 1 | Escalation concurrency: HLD-005/007/009/014/015 encode one-open-escalation invariant; DECLARED-009 ratifies concurrent escalations | Q2: Multiple concurrent escalations with stable ID, owner, routing, status, context | Decided; HLD text not yet patched |
| 2 | Out-of-scope list: HLD-011 asserts exclusion list as product limits; DECLARED-010 rejected as slicing residue | Q3: Exclusion list becomes current implementation status + candidate capabilities under replacement boundary rule | Decided; HLD text not yet patched |

### Provisional items (ACTION class)

| # | Item | Owner decision | Status |
|---|---|---|---|
| 3 | `HLD-SPECS: TBD` on HLD-001/002/006/011/012; `HLD-RESOURCES: TBD` on HLD-011 | Q4: Replace with real intent where evidence exists; mark explicitly provisional with revisit trigger where insufficient | Decided; HLD metadata not yet updated |
| 4 | Markdown projection roles not stated; HLD says "never an input" | Q1: Three product-surface roles (agent integration, context state, user-facing reporting); remove "never an input" | Decided; HLD text not yet patched |
| 5 | Transition gaps (answer/feedback naming, anonymous-path policy C) | Covered by Q2/Q3 scope; already honest in HLD as provisional by design | Decided; disposition set by owner decisions |
| 6 | Structural completeness: no explicit requirements/feature-candidate section | Q5: Add explicit requirements/feature-candidate section | Decided; HLD section not yet added |

## Remaining blocker

All formal unresolved and provisional items have owner decisions. The gate
remains BLOCKED because the decisions have not been applied to the Flow HLD
text. The HLD still contains the contradictions and TBD metadata.

Resolution requires a separately approved target HLD patch to
`/Users/saffi/code/flow/HLD.md` (and the README mirror), scoped per the
`flow-hld-hardening-owner-decisions.md` §"Future target HLD patch scope."

## HLD patch scope (consolidated)

The target HLD patch must address all seven decided items:

From PR #120 owner decisions (Q1–Q5):
1. Remove one-open-escalation invariant; encode concurrent escalations (Q2)
2. Rework HLD-011 exclusion list and README mirror (Q3)
3. State three markdown projection roles; remove "never an input" (Q1)
4. Resolve TBD metadata with real intent or explicit provisional + trigger (Q4)
5. Add requirements/feature-candidate section (Q5)

From this disposition (items 2–3):
6. HLD-009/010: distinguish required session-enforcement invariant from
   current implementation status — no overstatement
7. HLD-014: distinguish required reclaim semantics from current
   implementation status — no overstatement

## Required next steps

1. **Explicit approval** to write to `/Users/saffi/code/flow/HLD.md` and
   `/Users/saffi/code/flow/README.md`, naming those as exact target write paths.
2. **Apply the HLD patch** per the seven items above.
3. **Re-run the SDD-ready gate** with the fixed snapshot provenance path.
4. **Do not** start Journey 2 or Journey 3 regardless of the re-run verdict.

## Boundaries

- No target mutation by this record.
- No SpecKit invocation.
- No Journey 2 or Journey 3.
- No backlog or implementation scope.
- No J0-12 global closure.
- No implementation changes forced for items 2/3 — HLD truthfulness only.
- Implementation gaps are recorded, not resolved — they are downstream of the
  HLD patch and are not SDD-ready gate criteria.
