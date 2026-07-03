# Flow Drift Disposition — Proposed

Date: 2026-07-03

Status: **PROPOSED** — requires owner sign-off before the next gate re-run
treats these classifications as settled.

## Purpose

Classify the six drift items from the SDD-ready gate re-run (PR #122) against
the formal SDD-ready gate criteria (`docs/JOURNEY1_SDD_READY_GATE.md`), and
map the formal unresolved/provisional items to their owner decisions.

This is a proposed disposition only. It does not modify `/Users/saffi/code/flow`,
invoke SpecKit, start Journey 2 or Journey 3, or create implementation scope.

## Gate re-run drift items vs formal gate criteria

The SDD-ready gate (§5) defines SDD-ready as "safe to compile" — clear,
bounded, coherent, and complete enough for Journey 2. It explicitly states:

> SDD-ready does **not** mean fully specified or implementation-detailed.

However, §9 blocks on "unsourced claims" and "unresolved contradictions," and
§17 notes that "a human reviewer remains responsible for structural
completeness" beyond what the automated count catches. The formal
`unresolved`/`provisional` counts alone do not cover every gate dimension.

The gate re-run found six drift items. The proposed classification below
separates implementation gaps (non-blocking per §5) from items where the HLD
asserts current behavior the implementation may not fully support (potentially
§9-relevant, needs owner judgment).

| # | Drift item | Category | Proposed disposition | Rationale |
|---|---|---|---|---|
| 1 | `answer`/`feedback` split not fully implemented | Implementation gap | Non-blocking | HLD transition gaps (HLD-007/009/014) already declare this as provisional by design; the readiness report confirmed it "already honest in the HLD" |
| 2 | Mandatory session enforcement not fully implemented | HLD asserts current behavior | **Owner call needed** | HLD-009 HLD-VERIFY and HLD-010 assert enforcement at CLI entry as current working behavior; if implementation doesn't fully match, this is a potential §9 unsourced claim — or the HLD may be accurate and the gap narrower than stated |
| 3 | Explicit `reclaim` behavior not fully implemented | HLD asserts current behavior | **Owner call needed** | HLD-014 HLD-VERIFY describes lease/reclaim mechanics as current behavior; same §5-vs-§9 tension as item 2 |
| 4 | Escalation owner, reply routing, explicit status incomplete | Implementation gap | Non-blocking | Covered by owner decision Q2 (concurrent escalations); HLD patch will state the decided design; implementation is downstream |
| 5 | Report layer and richer reference/projection surface incomplete | Implementation gap | Non-blocking | Covered by owner decision Q1 (markdown projection roles); HLD patch will state the decided design; implementation is downstream |
| 6 | Docs/tests mix hardened semantics with v1 characterization | Flow-side quality | Non-blocking | Flow repo quality item; does not affect HLD text coherence or metadata completeness |

Items 1, 4, 5, 6 are implementation status, which the gate explicitly excludes
from the SDD-ready definition (§5). Items 2 and 3 sit at the boundary: the
HLD asserts behavior as current (present tense, HLD-VERIFY), and if the
implementation doesn't match, that's potentially an unsourced high-risk claim
(§9). The owner must decide whether these are:

- **(a)** Accurately described in the HLD (implementation covers the core
  behavior; the gap is narrower than "not fully implemented" suggests) →
  non-blocking.
- **(b)** Overstated in the HLD (the HLD claims more than the implementation
  delivers) → the HLD patch should correct the assertion, or accept as
  provisional with a revisit trigger (§8).
- **(c)** Genuinely blocking → the implementation must be fixed before
  SDD-ready, which is Flow-side work outside HLDspec scope.

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

## Required next steps

1. **Explicit approval** to write to `/Users/saffi/code/flow/HLD.md` and
   `/Users/saffi/code/flow/README.md`, naming those as exact target write paths.
2. **Apply the HLD patch** per the five owner decisions.
3. **Re-run the SDD-ready gate** with the fixed snapshot provenance path.
4. **Do not** start Journey 2 or Journey 3 regardless of the re-run verdict.

## Boundaries

- No target mutation by this record.
- No SpecKit invocation.
- No Journey 2 or Journey 3.
- No backlog or implementation scope.
- No J0-12 global closure.
- Implementation gaps are recorded, not resolved — they are downstream of the
  HLD patch and are not SDD-ready gate criteria.
