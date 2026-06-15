# Journey 1 — SDD-Ready HLD Gate (Contract)

**Status:** product contract. This is the testable gate for Journey 1 of the
three-journey model (`docs/THREE_JOURNEYS.md`). It defines when an HLD is
**SDD-ready** and may pass to Journey 2.

This contract documents and hardens an **already-implemented** gate. It does not
add runtime behavior. The verdict logic, artifacts, and item schema below live in
`hldspec/hld_readiness.py` and `hldspec/state_transitions.py`; this doc is their
binding contract, not a new mechanism.

> Naming: the task proposed `SDD_READY_HLD`, `HLD_READINESS_REPORT`,
> `OPEN_QUESTIONS`, `DECISION_LOG`, `RISK_REGISTER`. The repo already implements
> these concepts under existing names. This doc uses the existing names and lists
> the proposed names as aliases (see §16), per "use existing convention when
> better."

---

## 1. Purpose

Create or improve an HLD until it is **SDD-ready**: clear, bounded, coherent, and
complete enough for Journey 2 to compile into a target package without inventing
product truth.

Journey 1 is a **gate**, not a compiler. It answers one question:

> Is this HLD safe to decompose?

## 2. Input

- The working HLD (`target/targetHLD/HLD.md`), normalized from read-only source
  resources. The source HLD is never modified.
- Human intent and any human answers to readiness questions.

## 3. Output

| Output | Artifact (existing) | Meaning |
|---|---|---|
| **HLD Readiness Report** | `hld_readiness_check.json` / `.md` | The verdict (`HLD_READY` / `HLD_READY_WITH_ACTIONS` / `HLD_BLOCKED`), blockers, next safe action. |
| **Decision Log** | `hld_cross_examination.json` (`examined_items`) / `.md` | Per-item reason trail: statement, reason, reason_kind, confidence, status. |
| **Open Questions** | `grouped_questions` / `blockers` in the above | Grouped clarification questions for unresolved/provisional items. |
| **Risk Register** | `revisit_triggers` + `accepted_risks` in the readiness report | Provisional choices carried forward with revisit triggers and accepted risk. |
| **SDD-ready HLD** | the working HLD itself | The HLD once the verdict is `HLD_READY`, or `HLD_READY_WITH_ACTIONS` with the human accepting the listed risks. A *state*, not a separate file. |

Only these are handed to Journey 2. Journey 1 does **not** emit features, spec
inputs, or constitution material — those are Journey 2 outputs.

## 4. Boundaries

Journey 1:
- judges HLD quality and records the reason trail;
- may shape/repair/clarify the HLD with the human owning every decision;
- stops at the gate.

Journey 1 does not decompose features, build a package, init SpecKit, select a
helper, or write into Journey 2/3 territory. Those are downstream boundaries only.

---

## 5. SDD-ready HLD — definition

An HLD is **SDD-ready** when all are true:

1. **Bounded** — scope, non-goals, and out-of-scope are stated; the HLD does not
   sprawl into undeclared territory.
2. **Coherent** — no unresolved contradiction between requirements, constraints,
   or declared `CONFLICTS_WITH` references.
3. **Sourced** — each material claim has a reason that is `explicit_hld`,
   `inferred_from_context`, `human_choice`, `temporary_poc_choice`, or
   `external_constraint` (not absent).
4. **Decomposable** — components, responsibilities, and boundaries are clear
   enough that Journey 2 can draw feature boundaries without guessing product
   truth.
5. **Evidence-anchored** — high-risk areas declare verification intent
   (`HLD-VERIFY`) or are explicitly accepted as provisional with a revisit trigger.

SDD-ready does **not** mean fully specified or implementation-detailed. It means
*safe to compile*. Remaining detail is Journey 2/3 work.

## 6. Required HLD sections / metadata

Grounded in `hld_map.py` `REQUIRED_METADATA`. Every material HLD section must
carry:

- `HLD-ID` — stable section identity.
- `HLD-ROLE` — one of: `api`, `ui`, `data`, `processing`, `architecture`,
  `operations`, `testing`, `risk`, `governance` (or `requirement` / `constraint`
  / `non_goal` / `feature_candidate` by section intent).
- `HLD-STATUS` — section maturity.
- `HLD-RISK` — risk level (`HIGH` requires verification intent or accepted-risk).
- `HLD-SPECS` — what specs/behaviors the section implies (not `TBD` for PASS).
- `HLD-RESOURCES` — referenced resources/evidence.

The HLD as a whole must contain, at minimum:
- a **purpose / scope** statement,
- **non-goals / out-of-scope**,
- **requirements or feature candidates**,
- **architecture / boundaries** (components, responsibilities, source of truth),
- **constraints and risks**.

## 7. Optional HLD sections / metadata

From `hld_map.py` `OPTIONAL_METADATA` plus `HLD-VERIFY`:
`HLD-OWNER`, `HLD-NOTES`, `HLD-INPUTS`, `HLD-OUTPUTS`, `HLD-DESC`, `HLD-VERIFY`.

`HLD-VERIFY` is optional in general but **required-when-HIGH-risk** (see §9).

---

## 8. Allowed ambiguity (does not block)

Ambiguity that Journey 2/3 can safely resolve downstream:
- **Provisional POC choices** with an explicit revisit trigger
  (`status: provisional`, `reason_kind: temporary_poc_choice`).
- **Implementation-level detail** not affecting boundaries, source of truth, or
  user-visible scope (e.g. internal naming, library choice within a constraint).
- **Reversible defaults** the human accepts as accepted-risk with a revisit
  trigger recorded in the Risk Register.

These produce **ACTION** at most, not BLOCKED, and may proceed when the human
accepts the risk.

## 9. Blocker ambiguity (blocks)

Ambiguity Journey 2 cannot resolve without inventing product truth:
- **Unsourced claims** — a material item with no explicit reason
  (`reason_kind: human_choice` with no decision, or `confidence: low`).
- **Unresolved contradiction** — conflicting requirements/constraints or an open
  `CONFLICTS_WITH` reference.
- **High-risk without evidence** — `HLD-RISK: HIGH` with `HLD-VERIFY` empty/`TBD`
  or a `TBD` owner/specs/resources.
- **Undrawable boundary** — components or source-of-truth ownership unclear enough
  that feature decomposition would be guesswork.
- **Human-owned decision pending** — architecture, source of truth, or scope
  decision the human has not made.

These produce **BLOCKED**.

---

## 10. Gate states — PASS / ACTION / BLOCKED

Product-facing states bind 1:1 to the implemented verdicts in
`hld_readiness.py::build_hld_readiness_check`:

| Gate state | Implemented verdict | Trigger (current logic) | Definition |
|---|---|---|---|
| **PASS** | `HLD_READY` | `unresolved == 0` and `provisional == 0` | The HLD is clear, bounded, coherent, and complete enough for Journey 2 to compile into a target package. |
| **ACTION** | `HLD_READY_WITH_ACTIONS` | `unresolved == 0` and `provisional > 0` | The HLD is mostly usable, but specific ambiguity, missing evidence, contradiction, or unclear boundary must be fixed — or accepted as risk with a revisit trigger — before Journey 2. |
| **BLOCKED** | `HLD_BLOCKED` | `unresolved > 0` | The HLD lacks enough source truth, has unresolved product/architecture conflict, or cannot be safely decomposed. |

Per-item `status` (from `hld_readiness.py::_status`) drives the counts:
`baked` (sourced, low risk), `provisional` (POC/assumption/TBD → ACTION),
`unresolved` (unsourced/low-confidence/high-risk-without-verify → BLOCKED),
`superseded`.

**Promotion rule:** Journey 2 may start on **PASS**, or on **ACTION** only after
the human explicitly accepts the listed risks (recorded in the Risk Register).
**BLOCKED never promotes.**

## 11. Evidence required for PASS

PASS (`HLD_READY`) requires, as machine-checkable evidence:
- `hld_cross_examination.json` and `hld_readiness_check.json` exist (required
  artifacts in `state_transitions.py` for the `HLD_READY` transition);
- `summary.unresolved == 0` **and** `summary.provisional == 0`;
- every examined item has a non-empty `reason` and a valid `reason_kind`;
- no open `CONFLICTS_WITH` reference among examined items;
- every `HLD-RISK: HIGH` section has non-`TBD` `HLD-VERIFY`.

ACTION requires the same artifacts plus a recorded human risk-acceptance for each
provisional item before promotion. BLOCKED requires the grouped questions to be
present so the human can resolve them.

## 12. What Journey 1 must not do

- Must not decompose features, build a target package, or write spec inputs.
- Must not invent product truth, source-of-truth ownership, or constitution
  material the human did not decide.
- Must not modify the source HLD (read-only); only the working HLD may change.
- Must not invoke SpecKit, init Build Loop, or select a helper
  (`forbidden_actions` on the readiness transitions enforce this).
- Must not promote BLOCKED, or promote ACTION without recorded risk acceptance.

## 13. What Journey 1 must not allow into Journey 2

Never pass downstream:
- an HLD with `unresolved > 0` (BLOCKED);
- an unresolved contradiction or open `CONFLICTS_WITH`;
- a high-risk area with no verification intent and no accepted-risk record;
- a provisional/accepted-risk item with no revisit trigger;
- a material claim with no reason in the Decision Log.

If any of these is present, Journey 1 returns ACTION/BLOCKED and stops. Journey 3
must never compensate for an HLD that should not have passed — the failure is
fixed here, not patched downstream.

## 14. RunSkeptic questions for Journey 1

Asked at the gate, before promotion:
- **CH (inversion):** If this HLD passes, what is the worst downstream outcome,
  and does the Decision Log + Risk Register bound it?
- **OM (parsimony):** Does each required section/metadata prevent a known failure,
  or is the gate demanding ceremony with no failure mode behind it?
- **FE (mechanism):** Can a reader see *how* the verdict was reached (counts →
  verdict), not just the verdict word?
- **PO (refutation):** Is there an HLD this gate would fail? Show one. Can a bad
  HLD pass silently?
- **KT (universalizability):** Is this gate safe applied to every HLD, including
  small/POC ones, without unfair exception?
- **SH (tradeoff):** Does the gate resolve flexibility vs enforceable quality —
  one dominant default (block unsourced truth) with a narrow exception
  (accepted-risk provisional)?

The gate emits RunSkeptic status `PASS` / `ACTION` / `CONFLICT` alongside the
verdict; missing evidence is `ACTION` or `CONFLICT`, never silent PASS.

## 15. Minimal test / validation strategy

**Automated (existing seams):**
- `hldspec/hld_readiness.py` verdict logic — unit-testable directly:
  - all-baked HLD → `HLD_READY` (PASS);
  - one provisional item, no unresolved → `HLD_READY_WITH_ACTIONS` (ACTION);
  - one unresolved item → `HLD_BLOCKED` (BLOCKED);
  - high-risk section with `HLD-VERIFY: TBD` → item `unresolved` → BLOCKED.
- `hldspec/state_transitions.py` — the readiness transitions require the two
  artifacts and forbid SpecKit/Build Loop (covered by
  `tests_v2/test_state_transitions.py`).
- Doc-contract tests (`tests_v2/test_hldspec_concept_docs.py`,
  `test_terminology_and_flow_docs.py`) keep the index and canonical doc aligned.

**Manual checklist** (per HLD, when no fixture exists):
1. Every material section has the §6 required metadata; no `TBD` in PASS.
2. Decision Log has a reason for every examined item.
3. Risk Register lists a revisit trigger for every provisional/accepted-risk item.
4. No open `CONFLICTS_WITH`.
5. Verdict matches counts: `unresolved>0`→BLOCKED, else `provisional>0`→ACTION,
   else PASS.
6. Promotion only on PASS, or ACTION with recorded human risk acceptance.

---

## 16. Vocabulary bridge

| Proposed name | Existing repo name (authoritative) |
|---|---|
| `SDD_READY_HLD` | the working HLD at verdict `HLD_READY` (or accepted `HLD_READY_WITH_ACTIONS`) |
| `HLD_READINESS_REPORT` | `hld_readiness_check.json` / `.md` |
| `OPEN_QUESTIONS` | `grouped_questions` / `blockers` |
| `DECISION_LOG` | `hld_cross_examination.json` `examined_items` reason trail |
| `RISK_REGISTER` | `revisit_triggers` + `accepted_risks` in the readiness report |
| PASS / ACTION / BLOCKED | `HLD_READY` / `HLD_READY_WITH_ACTIONS` / `HLD_BLOCKED` |

---

## 17. Known limits (honest scope)

The current verdict logic is a **heuristic over section metadata**. It reliably
catches unsourced claims, TBD/high-risk-without-verify, and declared
`CONFLICTS_WITH`. It does **not** yet detect:
- semantic contradictions that are not declared as `CONFLICTS_WITH`;
- a *missing whole section* (e.g. no architecture section at all) — absence is not
  currently counted as `unresolved`.

These are tracked as Journey 1 hardening follow-ups, not claimed as working.
Until added, a human reviewer remains responsible for structural completeness at
the gate.
