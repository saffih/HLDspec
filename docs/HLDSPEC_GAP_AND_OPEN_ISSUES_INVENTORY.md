# HLDspec Gap and Open Issues Inventory

**Status:** docs-only inventory
**Scope:** current known HLDspec gaps and open issues
**Non-goal:** no runtime enforcement, no validators, no producers, no gates, no
code changes of any kind

This inventory captures known gaps explicitly so they do not disappear through
context compaction, handoff, or future sessions. It is a prerequisite for adding
validators, producers, advisory reports, or gate enforcement.

---

## Gap state vocabulary

| State | Meaning | Constraint |
|---|---|---|
| `OPEN` | Identified, not yet classified or resolved | Must be resolved before completion |
| `BLOCKING` | Cannot proceed until resolved | Blocks downstream work |
| `CONFLICT` | Unresolved disagreement between sources | Requires reconciliation |
| `NEEDS_OWNER` | Requires human or role-owner decision | Cannot be resolved by automation |
| `ASSUMED_FOR_NOW` | Treated as resolved without full evidence | Requires explicit assumption text |
| `SAFE_TO_DEFER` | Acknowledged, not blocking | Requires reason and scope/owner |
| `RESOLVED_BY_EVIDENCE` | Answered by inspected evidence | Evidence reference required |
| `RESOLVED_BY_DECISION` | Answered by explicit decision | Decision reference required |
| `PARTIAL` | Something exists but does not fully satisfy the requirement | Gap between current and required state |
| `KNOWN_LIMITATION` | Accepted limitation, not a hidden blocker | Acknowledged and scoped |

Rules:

- `SAFE_TO_DEFER` requires a reason and a scope/owner.
- `ASSUMED_FOR_NOW` requires explicit assumption text.
- `PARTIAL` means something exists but does not fully satisfy the requirement.
- `KNOWN_LIMITATION` means an accepted limitation, not a hidden blocker.
- Do not mark unresolved material gaps as resolved.

---

## Context safety and gap continuity

| # | Gap | State | Notes |
|---|---|---|---|
| CS-1 | Context Safety + Gap Continuity doctrine exists, but no runtime enforcement yet | `PARTIAL` | Doctrine merged (PRs #62, #63). Enforcement staged per roadmap. |
| CS-2 | No persisted `gap_ledger.json` | `OPEN` | Future artifact under `.hldspec/source_package/`. |
| CS-3 | No persisted `worker_receipts.json` | `OPEN` | Future artifact under `.hldspec/source_package/`. |
| CS-4 | No persisted `evidence_not_inspected.json` | `OPEN` | Future artifact under `.hldspec/source_package/`. |
| CS-5 | No persisted `decomposition_plan.json` | `OPEN` | Future artifact under `.hldspec/source_package/`. |
| CS-6 | No persisted `test_runner_receipts.json` | `OPEN` | Future artifact under `.hldspec/source_package/`. |
| CS-7 | No pure validators yet for persisted context-safety artifacts | `OPEN` | Roadmap phase 2. |
| CS-8 | No advisory context-safety report yet | `OPEN` | Roadmap phase 4. |
| CS-9 | No gate wiring yet for unresolved context/gap states | `OPEN` | Roadmap phase 5. |

---

## Spec / capability decomposition

| # | Gap | State | Notes |
|---|---|---|---|
| SD-1 | HLD → capabilities → deliverables → atomic tasks is documented, but no explicit spec-size / capability-size rule is enforced | `PARTIAL` | Validation-first decomposition is doctrine (PR #63). No enforcement. |
| SD-2 | No rule yet that generated specs must be small enough to plan, validate, and implement without overwhelming the agent | `OPEN` | |
| SD-3 | No explicit "sprint-sized / one capability / one bounded deliverable" criterion yet | `OPEN` | |
| SD-4 | No artifact yet that records decomposition from HLD to capabilities to atomic tasks | `OPEN` | Related to CS-5 (`decomposition_plan.json`). |

**Strategic requirement:** a generated spec or SDD slice should map to one
capability, one bounded deliverable, or one sprint-sized implementation unit. If
a spec requires multiple components, multiple owners, or multiple independent
validation strategies, it must be decomposed before implementation.

---

## Control-plane isolation

| # | Gap | State | Notes |
|---|---|---|---|
| CP-1 | External controller mode exists, but safe-default policy is not fully documented/enforced | `PARTIAL` | External controller mode works; policy incomplete. |
| CP-2 | Normal mode still permits target-local `.hldspec` control state | `OPEN` | |
| CP-3 | No documented rule that controller roots must be outside the target Git repository | `OPEN` | |
| CP-4 | No default home-folder controller-root convention, such as `~/control-plane-hldspec/<target-id>/` | `OPEN` | |
| CP-5 | Need explicit policy that the target repo is evidence/delivery surface, not the control plane | `OPEN` | |
| CP-6 | Need explicit policy for exactly which runtime handoff artifacts may be materialized into the target | `OPEN` | |
| CP-7 | Need future enforcement/guidance that control plane must not be a sibling directory inside the same Git repository as the target | `OPEN` | |
| CP-8 | Existing split-brain detection exists, but broader control-plane isolation policy remains incomplete | `PARTIAL` | Split-brain detection is implemented; broader policy is not. |

**Strategic requirement:** for brownfield or agent-managed targets, HLDspec
control state should be externalized outside the target repository. The target
repo is treated as evidence and delivery surface, not as the control plane. The
control plane should live in a separate controller root, preferably under a
user-owned directory such as `~/control-plane-hldspec/<target-id>/`, and should
not be a sibling directory inside the same Git repository.

HLDspec may materialize only explicitly scoped runtime handoff artifacts into
the target, such as a read-only SpecKit mirror, and must fail closed on
split-brain between controller and target-local control state.

---

## Journey 2 / SDD completeness

| # | Gap | State | Notes |
|---|---|---|---|
| J2-1 | Coverage ledger exists and `NOT_COVERED` blocks the source gate, but this is only trace coverage | `PARTIAL` | Trace coverage enforced. Semantic coverage not validated. |
| J2-2 | `COVERED_IN_SDD` means citation/trace coverage only, not semantic proof | `KNOWN_LIMITATION` | By design for current phase. |
| J2-3 | No semantic SDD completeness validation | `OPEN` | |
| J2-4 | `NEEDS_CLARIFICATION` is not enforceable yet | `OPEN` | |
| J2-5 | No inquiry ledger exists yet | `OPEN` | Contract defined in `JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`. |
| J2-6 | `RESEARCH_REQUIRED` is not enforceable yet | `OPEN` | |
| J2-7 | No research/evidence ledger exists yet | `OPEN` | |
| J2-8 | `BLOCKED_BY_PRODUCT_DECISION` is not enforceable yet | `OPEN` | |
| J2-9 | No product-decision ledger or owner-decision artifact exists yet | `OPEN` | |
| J2-10 | `build_completeness_report` exists but broader live integration remains incomplete beyond current `NOT_COVERED` gate wiring | `PARTIAL` | |

---

## Validation architecture

| # | Gap | State | Notes |
|---|---|---|---|
| VA-1 | Independent validator pattern is documented, but not enforced as an artifact or gate | `PARTIAL` | Doctrine exists (PR #63). No enforcement. |
| VA-2 | Planner / implementer / validator separation is doctrine only | `PARTIAL` | Context isolation section in doctrine doc. |
| VA-3 | Atomic task validation-first criteria are documented but not machine-checked | `PARTIAL` | Atomic-task criteria in doctrine doc. |

---

## Testing discipline

| # | Gap | State | Notes |
|---|---|---|---|
| TD-1 | One fresh routine test/check pass per command is doctrine/prompt discipline, not enforced by HLDspec | `KNOWN_LIMITATION` | Prompt-level discipline. |
| TD-2 | No persisted test-runner receipt artifact exists yet | `OPEN` | Related to CS-6 (`test_runner_receipts.json`). |

---

## Driver / readiness

| # | Gap | State | Notes |
|---|---|---|---|
| DR-1 | Driver does not yet report persisted `context_safety_status` or `gap_continuity_status` | `OPEN` | |
| DR-2 | Driver does not yet block next actions based on persisted unresolved gap states | `OPEN` | |

---

## Journey 3 / helper execution

| # | Gap | State | Notes |
|---|---|---|---|
| J3-1 | Context-safety doctrine applies cross-journey, but no Journey 3 / helper integration yet | `OPEN` | |
| J3-2 | No enforcement yet that helper execution must consume persisted decomposition/gap/test receipts | `OPEN` | |

---

## SpecKit / helper scope

| # | Gap | State | Notes |
|---|---|---|---|
| SK-1 | Helper expansion beyond the current intended path remains intentionally deferred | `SAFE_TO_DEFER` | **Reason:** out of scope for current phase. **Owner:** product/architecture lead. |
| SK-2 | SpecKit execution must not expand as part of this inventory | `KNOWN_LIMITATION` | Boundary: this inventory does not change SpecKit scope. |

---

## Baton / external workflow

| # | Gap | State | Notes |
|---|---|---|---|
| BW-1 | Baton is separate and must not be touched unless explicitly scoped | `KNOWN_LIMITATION` | Boundary: no HLDspec/Baton integration implied. |

---

## Docs / governance

| # | Gap | State | Notes |
|---|---|---|---|
| DG-1 | Current gap list was not previously captured as a stable project artifact | `RESOLVED_BY_EVIDENCE` | This inventory resolves this gap. |
| DG-2 | Need future process for updating gap states without letting the inventory become stale | `OPEN` | |

---

## Recommended next implementation sequence

1. Inventory current gaps and open issues (this PR).
2. Normalize persisted artifact schemas.
3. Add pure validators.
4. Add producers.
5. Add advisory reports.
6. Wire safe blockers into gates.
7. Integrate status into driver/readiness.

---

## Non-goals for this inventory

This document is a docs-only inventory. Explicitly out of scope:

- No runtime enforcement or new validators.
- No gate changes or gate wiring.
- No source-package behavior changes.
- No Journey 3 / helper expansion.
- No SpecKit execution changes.
- No Baton edits.
- No parser grammar changes.
- No code changes of any kind.
- No claims that unresolved gaps are already enforced.
