# HLDspec Product/System Analysis

Status: derived from the post-PR #41 product inquiry (2026-06-26).

---

## Executive Summary

HLDspec is an evidence-gated workflow engine that turns a rough HLD into a
dependency-ordered, human-approved, helper-agnostic execution path. It prepares
and gates; it does not implement application code.

Current product mark: **6/10**. Foundational contracts and enforcement gates
exist. Remaining blockers: guarded product-flow integration, end-to-end
journey coverage, stale-artifact/diff handling, domain validators, and
RunSkeptic status propagation.

---

## PR #41 Outcome

- **Merged:** `6727ba6` (2026-06-26)
- **Phase-order patched:** candidate `specify → analyze → plan → tasks`
  corrected to canonical `specify → plan → tasks → analyze` before merge.
- **Scope:** contract-only — two docs, two anti-drift test files, docs index
  update. Zero runtime code.
- **Tests:** 21 targeted + 1555 tests_v2 + 173 tests, all green post-merge.
- **RunSkeptic:** PASS. No overclaim, no execution authority, driver recommends
  but does not approve, human owner protected.

---

## Three Journeys

### Journey 1 — HLD Authoring / Hardening

Purpose: create or improve an HLD until it is SDD-ready. Input: source HLD
(read-only) + human intent. Output: SDD-ready HLD + readiness verdict.
Code: `hld_readiness.py`, `machines/raw_hld_conversion.py`,
`machines/apply_hld_conversion.py`. Status: PASS_WITH_DEFERRED_WORK.
Deferred: missing-section detection (P1-012), `accepted_risks` wiring.

### Journey 2 — SDD / Package Preparation

Purpose: compile SDD-ready HLD into a structured target package. Input:
SDD-ready HLD. Output: source package + architecture package + spec inputs +
constitution material + `helper_recommendations.json`. Code:
`hld_source_package.py`, `journey2_architecture_package.py`. Status:
PASS_WITH_DEFERRED_WORK. Deferred: architecture-package reasoning fields
(human-owned), inquiry/gap ledger (P1-013, docs-only).

### Journey 3 — Target Delivery + Helper Runtime

Purpose: deliver the J2 package into a target repo and guide the targeteer
through completion via a selected helper (`speckit | claude-code | codex |
devin | manual`). Code: `journey3_driver.py`, `toolchain_driver.py`,
`agent_handoff_pack.py`, `helper_selection.py`. Status:
PASS_WITH_DEFERRED_WORK. Only `speckit` is operational. Deferred:
bridge/command-envelope (P1-016), helper bootstrap lifecycle (docs-only).

---

## Authority Model

Core rule (code-enforced, `toolchain_driver.py`): a system driver may replace
the human *operator*; it must never replace the human *approver/owner*.

- `approver_replacement_allowed = False` for every v0 mode.
- `mutation_allowed = False`, `execution_allowed = False` for every v0 mode.
- v0 has no execution channel. `AUTONOMOUS_WITH_GUARDS` resolves to `BLOCKED`.
- `GUIDE_ONLY`: observe and recommend only.
- `PROPOSE_COMMAND`: produce exact commands; human runs them.
- `EXECUTE_WITH_APPROVAL`: execute only after explicit approval (v0: no-op).

Protected transitions (always reported, never granted):
helper OPERATIONAL, SourceBinding, ISG Governance, NextActionPacket/READY,
product-code mutation, commit/push/merge, accept unresolved risk, override
BLOCKED/ACTION.

---

## State and Artifact Ownership

| Artifact | Owner | Safe overwrite |
|---|---|---|
| Source HLD | human (read-only) | never |
| Target HLD (`target/targetHLD/`) | HLDspec (product artifact) | no (human-edited) |
| Control plane (`target/.hldspec/sync/` or `controller/.hldspec/`) | HLDspec | mostly (generated) |
| Source package + binding | Journey 2 | regen w/ binding |
| Helper selection (`.hldspec/helper_selection.json`) | Journey 3 | yes |
| `.specify/`, `specs/` | SpecKit (tool-owned, forbidden to HLDspec) | no |
| QA feature ledger | target (human-editable, `safe_write` guard) | no |
| QA classification | control-plane (machine-derived) | yes (plain overwrite) |

---

## SpecKit Integration

**Real today:** seven bounded per-package prompts, `speckit_execution_state`
presence-based phase assessment, `SpecKitInvoker`/drive loop as opt-in
`EXECUTE_WITH_APPROVAL`, `proof_speckit_readiness.py` detects
`SKILL_UNAVAILABLE`.

**Contract-only (PR #41, now merged):** receipt-gated transitions in canonical
order (`specify → plan → tasks → analyze`), fail-closed availability/approval
stops, bypass detection. Phase-order reconciled to canonical before merge.

**Next slice:** SpecKit runtime transition validator — a pure validator that
semantically checks `TransitionRequest` + receipts, without executing SpecKit.

---

## Product QA Loop

**Slice 1 (merged):** feature-ledger inventory scanner with `safe_write`
provenance guard. Target-owned.

**Slice 2A (merged, PR #40):** deterministic ledger-row classifier. 8
classifications, priority-ordered total decision table. Advisory only — writes
to control-plane, never modifies ledger, never invokes SpecKit. Evidence gate
prevents INFERRED/code-only evidence from reaching candidate status.
`HARNESS_FIX_CANDIDATE` reserved.

**Slice 2B (future):** work-order candidates from classifications. Requires
its own human gate — classification is not approval.

---

## Roadmap

### P0 — before product-stable claim

- P0-001: External-IO write-path enforcement
- P0-002: Guarded product-flow integration
- P0-003: End-to-end facade journey tests
- P0-004: Stale/diff handling
- P0-005: Domain validators
- P0-006: RunSkeptic status propagation

### P1 — next highest leverage

- **SpecKit runtime transition validator** (next PR)
- P1-009: Tiered re-sync (B/D slices)
- P1-010: Unify DONE semantics
- Reconcile J1 entry points (raw→anchored) + golden fixture

### P2 — important, not urgent

- Helper bootstrap lifecycle implementation (when 2nd helper needed)
- Bridge/command-envelope (P1-016)
- QA Slice 2B (with its own gate)

### DO_NOT_DO_YET

- Runtime executor/bridge inside contract-only slices
- Workflow engine / microservices / event-sourcing
- Auto-derive architecture-package reasoning fields
- Classification → auto-generated work orders

---

## Recommended Next PR

**`speckit-runtime-transition-validator`**: a pure function validator that
takes a `TransitionRequest`, declared receipts, and context flags
(`speckit_available`, `human_approval`) and returns a `ValidationResult` with
one of the fail-closed statuses from the contract. No SpecKit execution, no
receipt minting, no target mutation. Tests first: one red→green per bypass
path enumerated in `docs/SPECKIT_HELPER_EXECUTION_CONTRACT.md`.
