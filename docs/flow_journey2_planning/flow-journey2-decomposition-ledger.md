# Flow Journey 2 — Decomposition Ledger

**Date:** 2026-07-04
**Basis:** Clean-room audit of the planning package against live
`/Users/saffi/code/flow/HLD.md`
(SHA-256 `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0`).

---

## The 11 Decomposed Sections

Evidence basis for every row: feature claims traced to the section's
HLD-VERIFY / body text in the live HLD — all matched (audit 2026-07-04).

| Section | Features derived | Evidence basis | Package implication | Boundary note | Risk | Next approval required |
|---|---|---|---|---|---|---|
| HLD-003 Core model | F01, F06, F08 | HLD-VERIFY + body, matched | Single-store contract, projection roles → CONTRACT-SINGLE-STORE, DATA-PROJECTION-ROLES | Store internals in F01 only; projection consumers read-only | HIGH | Package approval |
| HLD-004 Task lifecycle | F02, F04 | HLD-VERIFY + body, matched | Four-state machine, dependency guard → CONTRACT-FOUR-STATES, CONTRACT-DEPENDENCY-GUARD | Transitions owned by F02; F04 consumes park/wake | HIGH | Package approval |
| HLD-005 Wait model (fork-join) | F04, F05 (F07 scoped-escalation ref) | HLD-VERIFY + body, matched | Concurrent escalations, all-resolved wake → CONTRACT-CONCURRENT-ESCALATIONS, CONTRACT-ALL-RESOLVED-WAKE, DATA-ESCALATION-IDENTITY | Escalation creation in F04; resolution routing in F05 | HIGH | Package approval |
| HLD-007 Answer & feedback | F05 | HLD-VERIFY + body, matched | Answer/feedback discrimination → CONTRACT-ANSWER-FEEDBACK-SPLIT | Report-update magnitude defers to F08/HLD-016 | MEDIUM | Package approval |
| HLD-008 Baton | F06 | HLD-VERIFY + body, matched | Baton ownership + read contract → DATA-BATON-OWNERSHIP | Baton ≠ outcome/report (F08 boundary) | HIGH | Package approval |
| HLD-009 CLI contract | F03 | HLD-VERIFY + body, matched | Session enforcement at entry, verb surface → CONTRACT-SESSION-ENFORCEMENT | Report verb surface deferred by HLD-016 note | HIGH | Package approval |
| HLD-010 Work routing | F03 | HLD-VERIFY + body, matched | Soft affinity, durable identity → CONTRACT-SOFT-AFFINITY, DATA-SESSION-DURABLE | Reclaim mechanics live in F07/HLD-014 | HIGH | Package approval |
| HLD-013 Concurrency & durability | F01, F06 | HLD-VERIFY + body, matched | Atomic claim, one-tx-per-verb → CONTRACT-ONE-TX-PER-VERB, CONTRACT-ATOMIC-CLAIM | Claim-writes-baton crosses F01/F06 by design | HIGH | Package approval |
| HLD-014 Recovery | F07 | HLD-VERIFY + body, matched | Lease/reclaim/fence/flaky-mark → CONTRACT-OWNERSHIP-FENCE, CONTRACT-LEASE-RECLAIM, CONTRACT-FLAKY-MARK | Uses F04 escalation API for ceiling escalations | HIGH | Package approval |
| HLD-015 Autonomy contract | F02, F03, F04, F07, F08 | HLD-VERIFY + body, matched | Closed invariant set + tagging audit → constitution Invariant Boundary | Cross-cutting: every feature's guards must tag from the closed set | HIGH | Package approval |
| HLD-016 Output layer | F08 | HLD-VERIFY + body, matched | Outcome/report distinction, report lifecycle → CONTRACT-MANDATORY-OUTCOME, CONTRACT-REPORT-LIFECYCLE, DATA-REPORT-OWNERSHIP | Report verb surface is a deferred extension to HLD-009 | HIGH | Package approval |

Coverage: all 11 sections appear in ≥1 feature; graph `source_hld_sections`
matches the coverage table in `feature_decomposition.md` exactly; no extras.

---

## The 6 Deferred Provisional Sections

Canonical revisit trigger (verbatim, all six):
**"assign when the first spec citing this section is drafted — revisit at the
next SDD-gate assessment"**

| Section | Flagged feature dependencies (register) |
|---|---|
| HLD-001 What it is | FLOW-F08 (motivation-only "report is the point" framing; also flagged on the spec-input Purpose) |
| HLD-002 Vocabulary | FLOW-F03 (verb names align with vocabulary) |
| HLD-006 Escalation triggers | FLOW-F04 (mechanism specified; triggers deferred) |
| HLD-011 Scope boundary | FLOW-F08 (separate-markdown rendering governed by boundary rule) |
| HLD-012 Technology | FLOW-F01 (SQLite/Python as brownfield reality), FLOW-F03 (runner set) |
| HLD-017 Requirements & candidates | (none — candidate-only surface; see below) |

Dependencies are flagged, not resolved (see `provisional_dependency_register.md`).

---

## HLD-017 Candidates — Retained Candidate-Only

Web UI; HTTP API; Unix sockets; daemons; worker pools; environment staging;
migration tooling; richer UI infrastructure; React-style reply flows;
session-log links; richer task/report/log reference surfaces; robust
markdown/context views beyond current projections.

None appears as a feature, requirement, or spec input (programmatic term scan,
audit 2026-07-04). Adoption of any candidate is a deliberate future design
decision under the HLD-011 boundary rule — never by accretion.

---

## Anchor Check Summary

- 75 requirements (REQ-001..075), all unique, every one anchored.
- All anchors within the 11 decomposable sections; zero stale anchors
  (every cited section exists in the live HLD); zero provisional citations.
- Post-fix precision: REQ-052 now also cites HLD-014; REQ-075 now leads with
  HLD-016 (both keep their original anchors).
