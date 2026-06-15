# HLDspec — The Three Journeys (Product Framing)

**Status:** product direction. This doc sets the product-level shape of HLDspec
as three journeys with clean contracts between them. It is the framing that the
upcoming Journey 1 / Journey 2 / Journey 3 contract work hardens.

It does **not** change runtime behavior, add a helper, or refactor code. The
existing self-contained SpecKit run-card runtime stays valid and is reclassified
here as **the first Journey 3 helper implementation**, not the definition of
Journey 3.

> Relationship to the canonical doc:
> `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` remains authoritative on terminology,
> ownership, and mechanics. This doc renames and **re-scopes** the three journeys
> at the product level; the canonical names map 1:1 (see the bridge table below).
> Where the two disagree on Journey 3's *scope*, this doc states the intended
> direction; the canonical doc is updated as each journey contract is hardened.

---

## 1. Why this reframing is needed

The product was drifting toward "HLDspec drives SpecKit in the target repo."
That makes SpecKit the definition of the last journey. It is too narrow.

Reframing to three journeys with explicit contracts:

1. Prevents Journey 3 from becoming too broad (a catch-all that re-does upstream work).
2. Stops HLDspec from being defined only by SpecKit.
3. Creates clean contracts between journeys (each has a typed input and output).
4. Makes failure visible **earlier**:
   - a bad HLD fails in Journey 1,
   - a bad decomposition/package fails in Journey 2,
   - target/helper/runtime issues fail in Journey 3.
5. Lets us support multiple helpers later without redesigning the product.
6. Keeps the target-repo helper self-sufficient and human-driven.
7. Makes RunSkeptic sharper because each journey has one job and one boundary.

Two load-bearing statements:

> **SpecKit is a helper inside Journey 3, not the definition of Journey 3.**

> **Journey 2 produces the package; Journey 3 delivers and operates it.**

---

## 2. The pipeline at a glance

```text
Source HLD (read-only)
   │
   ▼
┌──────────────────────────────────────────┐
│ Journey 1 — HLD Authoring / HLD Hardening │  gate: is the HLD SDD-ready?
└──────────────────────────────────────────┘
   │  produces:  SDD-ready HLD
   ▼
┌──────────────────────────────────────────┐
│ Journey 2 — SDD / Package Preparation     │  gate: is the package complete + evidence-based?
└──────────────────────────────────────────┘
   │  produces:  target package
   ▼
┌──────────────────────────────────────────┐
│ Journey 3 — Target Delivery + Helper RT   │  gate: is the package delivered + operable?
└──────────────────────────────────────────┘
   │  produces:  helper runtime in target repo (run card, completion map, …)
   ▼
Targeteer completes the work using a selected helper
   (helper: speckit | claude-code | codex | devin | manual)
```

Each arrow is a **typed handoff**. A journey may only consume the artifact the
prior journey produced — never the raw upstream input. Journey 3 consumes the
target package; it does not re-read the source HLD to re-derive features.

---

## 3. The three journeys

### Journey 1 — HLD Authoring / HLD Hardening

| | |
|---|---|
| **Purpose** | Create or improve an HLD until it is SDD-ready. |
| **Input** | Source HLD and design resources (read-only), human intent. |
| **Output** | An **SDD-ready HLD** plus its readiness verdict and reason trail. |
| **Boundary** | A gate. It judges HLD quality; it does not decompose features or prepare a package. |
| **Pass/fail gate** | `PASS` / `ACTION` / `BLOCKED` on SDD-readiness (see below). |
| **Must not do** | Invent product truth the human did not decide; pass an ambiguous HLD downstream; start feature decomposition; write into the source HLD. |

Journey 1 answers one question: **is the HLD clear, bounded, coherent, and
complete enough to be safely decomposed?**

It must define (Prompt 1 hardens these):

- what "SDD-ready HLD" means,
- required HLD sections,
- allowed ambiguity vs blocker ambiguity,
- `PASS` / `ACTION` / `BLOCKED` criteria,
- what must **not** be passed to Journey 2,
- the RunSkeptic questions for HLD quality.

Readiness verdicts (existing vocabulary, kept):
`HLD_READY` (pass), `HLD_READY_WITH_ACTIONS` (action — provisional choices may
proceed with accepted risk and revisit triggers), `HLD_BLOCKED` (blocked —
unresolved or conflicting decisions).

### Journey 2 — SDD / Package Preparation

| | |
|---|---|
| **Purpose** | Compile the SDD-ready HLD into a structured implementation package. |
| **Input** | The SDD-ready HLD from Journey 1. |
| **Output** | A **target package** (schema below). |
| **Boundary** | A compiler/packager — **not** another authoring assistant. |
| **Pass/fail gate** | The package validates: complete, evidence-based, nothing invented. |
| **Must not do** | Re-author or repair the HLD; invent constitution material or contracts not grounded in the HLD; deliver into a target repo; run a helper. |

Journey 2 takes the SDD-ready HLD and produces:

- feature boundaries and feature briefs,
- SpecKit-ready (and helper-ready) spec inputs,
- architecture constraints,
- engineering tools / repo commands / quality gates,
- constitution material,
- helper recommendations,
- the target package handed to Journey 3.

It must define (Prompt 2 hardens these):

- the `target_package` schema,
- the feature schema,
- the spec-input schema,
- the constitution-material schema,
- validation rules,
- what must be evidence-based (cite HLD anchors),
- what must **not** be invented.

### Journey 3 — Target Delivery + Helper Runtime

| | |
|---|---|
| **Purpose** | Deliver the Journey 2 package into a target repo and guide the targeteer through completion using a selected helper. |
| **Input** | The **target package** from Journey 2. |
| **Output** | A **helper runtime** materialized in the target repo. |
| **Boundary** | A consumer/operator — it does not synthesize the HLD, decompose features, or invent constitution material. |
| **Pass/fail gate** | The package is delivered and the helper runtime is operable: run card, completion map, and helper instructions are present and consistent. |
| **Must not do** | Re-derive features, repair the HLD, author constitution material, or fix upstream ambiguity. If the package is wrong, it **returns to Journey 2** — it does not patch around it. |

Journey 3 installs or materializes, in the target repo:

- a target-local **helper runtime**,
- a **run card**,
- a **completion map**,
- helper-specific instructions,
- model/agent guidance,
- stop rules,
- the report-back protocol.

**SpecKit is only one helper:**

```text
helper: speckit       ← the first implemented helper (existing run-card runtime)
helper: claude-code
helper: codex
helper: devin
helper: manual
```

The current self-contained SpecKit run-card runtime (commit
`feat(speckit): vendor self-contained Journey 3 run-card runtime`) is **the
`helper: speckit` implementation** — the proof that the Journey 3 shape works,
not the shape itself.

---

## 4. Minimal vocabulary

Seven words. Add more only on concrete need.

| Term | Meaning |
|---|---|
| **SDD-ready HLD** | An HLD that passed the Journey 1 gate: clear, bounded, coherent, complete enough to decompose safely. |
| **target package** | The Journey 2 output: feature briefs, spec inputs, architecture constraints, constitution material, engineering tools/gates, helper recommendations. The contract Journey 3 consumes. |
| **targeteer** | The human or agent who completes the work inside the target repo, guided by a helper. |
| **helper** | One selectable delivery mode for the targeteer: `speckit`, `claude-code`, `codex`, `devin`, or `manual`. SpecKit is one of these. |
| **helper runtime** | The target-local materialization of a helper: the files, instructions, and guidance installed into the target repo so the targeteer can work self-sufficiently. |
| **completion map** | The target-local map of what "done" means: features, their order, status, and stop rules — so the targeteer knows what remains. |
| **run card** | The bounded execution instruction for the current step: scope, allowed evidence, forbidden actions, stop conditions, report-back. (The existing **SpecKit Run Card** is the `speckit` instance.) |

Bridge to existing canonical names (`HLDSPEC_TERMINOLOGY_AND_FLOW.md` §13):

| This doc | Canonical doc today |
|---|---|
| Journey 1 — HLD Authoring / HLD Hardening | HLD Shaping (+ HLD Readiness Check) |
| Journey 2 — SDD / Package Preparation | SpecKit Groundwork (source package, anchors, spec input) |
| Journey 3 — Target Delivery + Helper Runtime | SpecKit Build Loop Supervision (re-scoped: helper-generic, not SpecKit-only) |
| target package | source package + spec input + constitution material + engineering guidelines |
| run card | SpecKit Run Card |
| helper runtime | the vendored target-local run-card runtime |

The re-scope is deliberate: the canonical Journey 3 is named around SpecKit; this
framing makes SpecKit one helper under a generic delivery + helper-runtime journey.

---

## 5. RunSkeptic — what each vagueness costs

Applied from `skeptic.md` (CH inversion / PO refutation lenses). One failure mode
per journey, stated as the worst material outcome of leaving the contract vague.

**If Journey 1 is vague** — "SDD-ready" has no testable definition:
- `CH:IV` Ambiguous HLDs pass silently; the cost surfaces two journeys later as
  contradictory specs or wrong features, where it is far more expensive to fix.
- `PO:SI` The gate can return PASS while the HLD is unfit — it has no
  disconfirming check. A green Journey 1 means nothing.
- Result: Journey 2 compiles unstable product truth, and Journey 3 delivers it.

**If Journey 2 is vague** — no `target_package` schema / validation rules:
- `PO:CN` Each run produces a differently-shaped package; Journey 3 cannot rely
  on a stable contract and must guess or re-derive — which pushes synthesis
  downstream (the exact failure this reframing prevents).
- `FE:WE` "Evidence-based" is unenforced, so invented constitution material and
  features leak in without HLD anchors.
- Result: Journey 3's input is untrustworthy, so Journey 3 quietly re-authors.

**If Journey 3 keeps doing synthesis** — it re-derives features, repairs the HLD,
or authors constitution material:
- `KT:HU` "Fix it in the target repo" becomes the general rule; upstream gates
  stop mattering because the last journey always patches around them.
- `CH:SO` Source-of-truth splits: the target repo's regenerated material diverges
  from the Journey 2 package and the HLD, with no owner.
- `SH:HC` It hides a real conflict (the package was wrong) as target-side work,
  so the failure is never attributed to Journey 1 or 2.
- Result: the clean-contract benefit collapses; HLDspec is one big synthesis blob
  again, and adding a second helper means re-solving synthesis per helper.

The framing's defense in all three cases is the same rule: **a journey consumes
only the prior journey's typed output, and returns upstream when that output is
wrong — it never patches around it.**

---

## 6. Recommended next sequence

Harden the contracts top-down, because each journey's output is the next
journey's input. Do **not** add Journey 3 helper features before the upstream
contracts are defined.

```text
Prompt 1 — Harden the Journey 1 contract   [DONE: docs/JOURNEY1_SDD_READY_GATE.md]
  Define SDD-ready: required sections, allowed vs blocker ambiguity,
  PASS/ACTION/BLOCKED criteria, what must not pass to Journey 2,
  RunSkeptic questions for HLD quality. Make it testable/gated.

Prompt 2 — Harden the Journey 2 package contract
  Define target_package / feature / spec-input / constitution-material schemas,
  validation rules, what must be evidence-based, what must not be invented.
  Make the package a stable typed artifact.

Prompt 3 — Review/redesign Journey 3 against those contracts
  Re-scope Journey 3 to consume the target package and operate a helper runtime.
  Confirm it synthesizes nothing, keep SpecKit as helper #1, and define the
  seam for a second helper without building one yet.
```

---

## 7. Scope guardrails for this framing

This doc intentionally does **not**:

- implement new runtime behavior,
- add another helper now,
- refactor code deeply,
- over-design a framework,
- remove or invalidate the existing SpecKit helper work.

It defines direction and contracts. Implementation follows the Prompt 1 → 2 → 3
sequence, each gated, each returning to RunSkeptic.
