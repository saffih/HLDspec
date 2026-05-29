# HLDspec Architecture Layers — Product & Layer Map

This is the canonical **product/layer map** for HLDspec: what the product is,
what each layer owns, and how the pieces relate. It is a North Star architecture
document — it states the **intended** product shape and is honest about what is
**current**, what is **intended target state**, and what is **future / not yet
implemented**.

It does **not** redefine terminology. For authoritative terminology, ownership
boundaries, the full flow, and the SpecKit Run Card, `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`
wins on any conflict. For the current repo file map see `docs/REPO_LAYOUT.md`; for
the phased change plan see `docs/REPO_MIGRATION_PLAN.md`; for the non-droppable
contracts see `docs/ANTI_DRIFT_CONTRACTS.md`.

> **Reading rule.** Every claim below is tagged. **[current]** = implemented and
> tested today. **[target]** = intended end state, alignment in progress.
> **[future]** = not yet implemented; do not treat as current capability.

---

## 1. Product purpose

HLDspec is the **control layer between a human-owned HLD and safe SpecKit /
implementation work**. It prepares, validates, gates, explains, and bounds the
next safe action.

Hard product boundaries:

- **HLDspec does not replace SpecKit.** SpecKit owns the constitution, spec, plan,
  tasks, and implementation artifacts.
- **HLDspec does not implement the product.** It produces evidence, gates,
  prompts, slice scope, and the next safe action — it does not write application
  code.
- HLDspec does not silently make human-owned product or architecture decisions.
  Those escalate to the Human Decision Owner.

---

## 2. The three journeys

HLDspec serves **three distinct journeys**. They are weighted around a single
core and **must not be mixed** — each has its own expectations, artifacts, success
criteria, and tests. They are **not equally implemented**; the support level is
stated honestly per journey.

### A. HLD Authoring — *precondition / helper*

- Purpose: help shape unclear source material into a reliable HLD.
- Output: a better HLD, clearer decisions, fewer gaps.
- Support level: **HLD Authoring is a precondition/helper** journey **[current,
  partial]**. It remains precondition/helper
  **unless current evidence and tests prove deeper support** — do not claim it as
  a fully realized journey.

### B. SpecKit Preparation — *the core product*

- Purpose: turn a reliable HLD into a SpecKit-ready source package and target
  workspace.
- Output: an anchored source package, a read-only `.specify/source/` mirror,
  readiness facts, and the next safe action.
- Support level: **SpecKit Preparation is the core product** **[current]** — it is
  the primary deliverable and the journey with the most implementation and test
  coverage today.

### C. Implementation Guidance — *extension*

- Purpose: guide implementation after SpecKit artifacts exist.
- Output: bounded prompts, slice scope, run cards, stop conditions, and
  reassessment guidance.
- Support level: **Implementation Guidance is an extension** journey **[partly
  current, partly future]**. It remains an extension **unless current evidence and
  tests prove deeper support**. Existing-product change mode within this journey
  is **[future]** scope (see §6).

---

## 3. Implementation modes (a separate axis)

**Journey and mode are different axes. Do not collapse them.** A journey is *what*
HLDspec is helping with; a mode is *how* the implementation work is carried out.
Any journey can, in principle, be supported through more than one mode.

- **Manual** — the human follows HLDspec outputs and checklists.
- **Agent-assisted** — an Implementation Agent receives bounded prompts and edits
  code within approved scope.
- **Mediator-assisted** — an Agent Mediator observes, prompts, checks drift, and
  helps the user decide go / stop / clarify / reassess.

The **Devin Mediator** is a Devin-specific runtime adapter of the mediator role —
it is **not** the generic HLDspec Operator (see §5).

---

## 4. Product layers

The product expresses **seven layers**. Each layer has one owner and one job.

### Layer 1 — Public Interface  **[current; landed via migration Phase 1]**

The public user experience is **agent one-liner first**: a normal user does not
need to know any script path. The user gives an agent one short instruction and
reads back STATUS, blockers, evidence, and the next safe action.

Copy-ready instruction:

```text
Use HLDspec with source HLD: <path-to-HLD.md> and target project: <path-to-target>. Prepare the target, check SpecKit readiness, and report STATUS, blockers, evidence, and next safe action. Do not implement or run SpecKit unless HLDspec says it is safe.
```

Aligning every front-door doc to this was **migration Phase 1** (see
`docs/REPO_MIGRATION_PLAN.md`); that work has landed on `main` — the README,
`USER_RUN_MODEL.md`, and `HLDSPEC_TERMINOLOGY_AND_FLOW.md` now lead with the agent
one-liner and frame the command surface as internal tooling.

### Layer 2 — Agent-Facing Tool Surface  **[current]**

The commands an agent (or a maintainer) may run **internally**: `start`,
`status`, `review`, `continue`, `diff`, `doctor`, `speckit-doctor`,
`operator-state`, `speckit-state`. This is a **tool surface, not the human UX**.
These commands are **internal/manual/debug/fallback** tooling and are **not the
normal human UX** — the agent one-liner in Layer 1 is. The canonical command list
lives in `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md`.

### Layer 3 — HLDspec Core  **[current]**

`hldspec/` — state machines, contracts, renderers, source-package logic,
readiness logic, and operator state. This is the active V2 source.

### Layer 4 — SpecKit Readiness & Operator State  **[current, bounded]**

- **SpecKit Doctor** = readiness/preflight facts. **SpecKit Doctor is readiness/
  preflight only and is not the whole Operator**; it does not decide the full
  lifecycle.
- **Operator State** = evidence-backed lifecycle state and the next safe action.
  Implemented **today for the readiness boundary**; broader post-specify lifecycle
  state is **[future]**.
- The **Operator is broader than the Doctor**.

### Layer 5 — Generated Target Artifacts  **[current]**

`target/.hldspec/source_package/`, `target/.specify/source/`,
`target/.specify/memory/`, and `target/specs/` are **target workspace outputs**.
**Generated target workspace artifacts are not repo source** — they are produced
into a user-chosen target directory and must never be confused with the HLDspec
repository's own source files.

### Layer 6 — Compatibility / V1 / Legacy  **[compatibility]**

The V1 HLD→SpecKit pipeline (`hld_spec_sync.py`, `hld_spec_downstream.py`) and the
shared parser `hld_map.py` remain **only because they are still wired** (first-run
read-only analysis and the PoC call them). Compatibility shims must be labeled as
compatibility shims; legacy/reference docs must not look like an active source of
truth. **V1 / compatibility surfaces are not active V2 core** — new work belongs in
Layer 3 (`hldspec/`) and the Layer 2 tool surface.

### Layer 7 — Anti-Drift / QA  **[current]**

Tests in `tests_v2/` enforce terminology, public UX, the command surface, repo
layout, product readiness, and the known boundaries. Anti-drift exists because
alignment keeps slipping; it locks the intended product shape. See
`docs/ANTI_DRIFT_CONTRACTS.md` and this doc's contract test
`tests_v2/test_architecture_layers_contract.py`.

---

## 5. Role / behavior boundaries

These names are **not interchangeable**:

| Term | What it is | What it is not |
|---|---|---|
| **HLDspec Operator** | Core HLDspec behavior producing operator facts, source-package context, slice control, and SpecKit Doctor readiness facts; implements Operator State for the readiness boundary today. | Not just the Doctor; not a Devin-specific thing. |
| **SpecKit Doctor** | The diagnostic/preflight part of the Operator; readiness facts. | **Readiness/preflight only — not the whole Operator.** |
| **Operator State** | Evidence-backed lifecycle state + next safe action (readiness boundary today). | Not a full post-specify lifecycle engine yet. |
| **Agent Mediator** | User-side observer/prompt/safety assistant during an implementation session. | **Agent Mediator is not the Implementation Agent.** |
| **Devin Mediator** | A Devin-specific runtime adapter of the mediator role. | **Devin Mediator is Devin-specific**; it does not define the generic Operator layer. |
| **Implementation Agent** | The hands: runs SpecKit, edits code, runs tests, only within bounded scope. | Not the mediator; not the decision owner. |

---

## 6. Current state vs intended target vs future

**Current [current]:**

- SpecKit Preparation is implemented and tested as the core product.
- Operator State is implemented for the readiness boundary.
- The agent-facing tool surface (Layer 2) is implemented and documented.
- Agent one-liner first is the documented front door (Layer 1): the README,
  `USER_RUN_MODEL.md`, and `HLDSPEC_TERMINOLOGY_AND_FLOW.md` lead with it —
  migration Phase 1, landed.
- Anti-drift tests (Layer 7) protect terminology, UX, command surface, and layout.

**Intended target state [target]:**

- Every tracked top-level file/dir has exactly one *enforced* layer classification
  — migration Phases 3–5.

**Future / not yet implemented [future]:**

- Broader post-specify lifecycle Operator State and richer next-safe-action
  guidance.
- **Existing-product change mode is future scope** (Product Truth Set, Feature
  Derivation Package, overlap classification are not current MVP behavior).

**Production readiness:** **Production-ready remains NO** until CI, install/release,
recovery/rollback, security sign-off, and real-HLD pilots are verified. This
architecture patch improves alignment and anti-drift; it does **not** change
production readiness. See `docs/PRODUCT_READINESS.md`.

---

## 7. What must not drift again

- Public UX is **agent one-liner first**; scripts are internal/manual/debug/
  fallback tooling, **not the normal human UX**.
- SpecKit Preparation is the core product; the other journeys are qualified.
- Journeys and modes are **different axes**.
- HLDspec does not implement the product and does not replace SpecKit.
- Doctor is readiness/preflight only; the Operator is broader.
- Agent Mediator ≠ Implementation Agent; Devin Mediator is Devin-specific.
- Generated target artifacts are not repo source.
- V1 / compatibility surfaces are not active V2 core.
- Production-ready remains NO until its gates are met.
