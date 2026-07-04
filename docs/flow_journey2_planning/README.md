# Flow Journey 2 Planning — Package Summary

**Date:** 2026-07-04
**Authorization:** `AUTHORIZE_EXECUTING_JOURNEY_2_PLANNING_PROMPT: yes`
**Approval status:** Package approval is PENDING. Prior gate sign-offs (SDD-ready gate v2 acceptance, planning-prompt authorization) were recorded as Hadas (project owner).
**Target:** `/Users/saffi/code/flow`
**HLD SHA-256:** `3c376ae9917b05d09d71fd73037b41a800eecbe51eaa5167481f1db11cf7e5d0`
**Output path:** `docs/flow_journey2_planning/` (HLDspec-side only)

---

## Planning-Run Deliverables

- `flow-journey2-planning-package.md` — planning-run cover doc (authorization, evidence ledger, forbidden conclusions)
- `flow-journey2-decomposition-ledger.md` — decomposition record (11 decomposed, 6 deferred, anchor check)
- `flow-journey2-readiness-report.md` — completeness/readiness report (§9-shaped; verdict)

---

## Package Contents

| File | Role |
|---|---|
| `feature_decomposition.md` | 8 feature boundaries with briefs, ordered_features list, section coverage |
| `speckit_single_spec_input.md` | 75 requirements, every one citing an (HLD-NNN) anchor from the 11 decomposable sections |
| `feature_dependency_graph.json` | DAG of feature dependencies (parity with queue) |
| `speckit_invocation_queue.json` | Invocation order (parity with graph) |
| `architecture_package.json` | 14 required fields per JOURNEY2_ARCHITECTURE_PACKAGE_CONTRACT.md |
| `constitution.proposed.md` | Constitution proposal (CONTRACT-*/DATA-* rules grounded in HLD) |
| `engineering_guidelines.md` | Architecture constraints, quality gates, test strategy |
| `provisional_dependency_register.md` | 6 flagged dependencies on provisional sections with revisit triggers |
| `package_validation_report.md` | Anchor integrity, parity, acyclicity, completeness checks |

---

## Validation Results

Provenance: manual audit, independently re-verified programmatically in the
clean-room audit of 2026-07-04 (not machine gate tooling).

| Check | Method | Result |
|---|---|---|
| Anchor integrity (75 reqs, all cite decomposable sections) | Programmatic anchor scan (clean-room audit) | PASS |
| No provisional section cited as anchor | Programmatic anchor scan (clean-room audit) | PASS |
| All 11 decomposable sections covered | Programmatic anchor scan (clean-room audit) | PASS |
| Parity (graph/queue ordered_features identical) | Ordered-list comparison (clean-room audit) | PASS |
| Acyclicity (DAG, no cycles) | Kahn acyclicity check (clean-room audit) | PASS |
| Dependency consistency (edges match node.dependencies) | Edge/dependency set comparison (clean-room audit) | PASS |
| Architecture package structural completeness | Manual audit + programmatic field check (14 fields, 8 slices × 12 fields) | PASS |

---

## The 8 Features (ordered)

```
1. FLOW-F01  Store & Transaction Foundation          [HLD-003, HLD-013]
2. FLOW-F02  Task Lifecycle & Invariant Discipline   [HLD-004, HLD-015]
3. FLOW-F03  Named Sessions, CLI Entry & Routing     [HLD-009, HLD-010, HLD-015]
4. FLOW-F04  Fork-Join & Concurrent Escalations      [HLD-005, HLD-004, HLD-015]
5. FLOW-F05  Human-in-the-Loop — Answer & Feedback   [HLD-007, HLD-005]
6. FLOW-F06  Baton — Context Substrate               [HLD-008, HLD-003, HLD-013]
7. FLOW-F07  Recovery — Lease, Reclaim, Fence        [HLD-014, HLD-015]
8. FLOW-F08  Output Layer — Outcome & Report         [HLD-016, HLD-003, HLD-015]
```

---

## Deferred Items (preserved revisit triggers)

6 provisional sections NOT decomposed:
- HLD-001 (purpose, MEDIUM) — revisit: assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment
- HLD-002 (vocabulary, LOW) — revisit: assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment
- HLD-006 (escalation triggers, MEDIUM) — revisit: assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment
- HLD-011 (scope boundary, LOW) — revisit: assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment
- HLD-012 (technology, LOW) — revisit: assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment
- HLD-017 (requirements/candidates, LOW) — revisit: assign when the first spec citing this section is drafted — revisit at the next SDD-gate assessment

HLD-017 candidate capabilities NOT treated as commitments (negative cross-check passed).

---

## What This Package Does NOT Authorize

- SpecKit invocation
- Journey 3 start
- Helper selection or installation
- Mutation of `/Users/saffi/code/flow`
- Backlog or implementation scope creation
- Global J0-12 closure
- Decomposition of the 6 provisional sections
- Treatment of HLD-017 candidate capabilities as committed design surface

---

## Planning-Grade Caveat

This is a hand-authored planning-grade package. The machine builder
(`build_source_package_content`) was not run because it would write into
`/Users/saffi/code/flow/.hldspec/source_package/` (mutating the target).
No external-controller mode is currently wired for flow.

Deferred to a future slice:
- Machine-validated anchor map (HLD.marked.md, hld_reference_map.json)
- Machine-validated manifest (source_manifest.json)
- Machine-built coverage ledger (hld_coverage_ledger.json)
- Full SOURCE_PACKAGE_APPROVAL_GATE validation
- RunSkeptic + Consultant review of the package

---

## Provenance

- SDD-ready gate: `docs/flow_journey1_hld_hardening/flow-sdd-ready-gate-v2.md`
  (PR #124, verdict ACTION)
- Owner acceptance: `docs/flow_journey1_hld_hardening/flow-sdd-action-owner-acceptance.md`
  (PR #125, promotes to PASS for planning)
- Planning prompt: `docs/FLOW_JOURNEY2_PLANNING_PROMPT.md` (PR #126)
- Execution authorization: this session (2026-07-04)
