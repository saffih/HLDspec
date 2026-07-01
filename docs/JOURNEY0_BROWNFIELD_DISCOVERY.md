# Journey 0 — Brownfield Product Discovery / HLD Gap Assessment

**Status:** product direction / design proposal. This doc defines the *contract
and boundary* of a pre-HLD discovery journey for brownfield products. It is **not
yet hardened or gated** the way Journeys 1–3 are (no RunSkeptic-tested gate, no
schemas, no implementation). Those are explicit future steps (see
[§9 Status and next steps](#9-status-and-next-steps)).

> Relationship to the canonical doc:
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) remains
> authoritative on terminology, ownership, and mechanics and **wins on any
> conflict**. This doc adds a pre-HLD on-ramp ahead of the existing three
> journeys; it does not renumber them or change runtime behavior.

---

## 1. What Journey 0 is, and where it sits

Journey 0 is a **pre-HLD discovery journey for brownfield products**. It runs
*before* Journey 1, when a target already contains some combination of code,
specs, docs, HLD fragments, `.specify/` state, `.hldspec/` state, or blocked
implementation history — and those inputs may be incomplete, stale, or
contradictory.

It answers one question:

> **What evidence exists, what conflicts, what is missing, and can an
> authoritative HLD responsibly be written?**

Journey 0 is an **on-ramp into Journey 1, not a fourth peer journey** and not a
renumbering. The product is still the three journeys
([`THREE_JOURNEYS.md`](THREE_JOURNEYS.md)); Journey 0 precedes and feeds the
first one:

```text
(brownfield target: code / specs / docs / HLD fragments / .specify / .hldspec)
        │
        ▼
┌──────────────────────────────────────────────┐
│ Journey 0 — Brownfield Discovery / Gap Assess │  read-only; produces evidence + decisions
└──────────────────────────────────────────────┘
        │  produces:  accepted evidence + explicit product decisions + HLD Update Plan
        ▼
   Source HLD (read-only)  ──►  Journey 1 ──► Journey 2 ──► Journey 3
   (authored / hardened from Journey 0 output)
```

For brownfield products such as **Baton Flow** (`~/code/flow`), Journey 0 is the
correct entry point before attempting to create or update the authoritative HLD.
`~/code/flow` is the **motivating proving-ground**, not a target to run now —
this doc defines the journey; it does not execute against any repo.

## 2. Why this is before Journey 1, not part of Journey 1

Journey 1 and Journey 0 ask different questions:

| | Question |
|---|---|
| **Journey 0** | What evidence exists, what conflicts, what is missing, and can an authoritative HLD *responsibly be written*? |
| **Journey 1** | Is the HLD itself clear, complete, and SDD-ready? |

Journey 1 assumes there is a candidate HLD to judge. On a brownfield product that
assumption fails: there may be several partial, stale, or contradictory sources
and no single authority. Folding discovery into Journey 1 would force the HLD
gate to silently pick winners among conflicting evidence — exactly the product
decision that must stay with a human. Journey 0 surfaces those conflicts and the
required decisions first, so Journey 1 can then author or harden **one**
authoritative HLD from *accepted* evidence and *explicit* decisions.

In Journey 0, existing code, specs, docs, and HLD fragments are **evidence, not
automatic authority**. When they conflict, Journey 0 classifies the conflict and
surfaces a product decision instead of silently choosing a winner.

## 3. Relationship to the existing brownfield boundary

HLDspec already states that **arbitrary brownfield *adoption* is unsupported** —
HLDspec will not silently treat existing, untrusted code as if it had HLDspec
lineage and proceed toward implementation
([`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) glossary;
enforced in `hldspec/target_discovery.py` via the `UNKNOWN_BROWNFIELD`
classification and in `hldspec/product_runability.py`).

**Journey 0 does not lift or relax that restriction.** It adds a *read-only
assessment step ahead of it*: it inspects and reports, then a human decides
whether and how to feed the result into Journey 1. This is continuous with the
read-only brownfield primitives HLDspec already ships — the `UNKNOWN_BROWNFIELD`
discovery/classification in `hldspec/target_discovery.py` and the read-only
"where are we?" aggregator `hldspec/journey3_driver.py` /
`scripts/hldspec_journey3_status.py`. Journey 0 is the product framing those
read-only inspectors point toward; it proposes no change to them here.

## 4. Inputs

Everything already present in or around the brownfield target, treated as
evidence:

- existing source code and tests,
- existing specs (`.specify/`, `specs/`) and any blocked implementation history,
- existing docs and design notes,
- HLD fragments (whole or partial, current or stale),
- prior `.hldspec/` state and discovery/classification output,
- human knowledge offered during discovery.

## Resource discovery trigger

A user may start from mixed resources rather than a clean HLD.

Convenience alias:

```text
HLD discover target <target-repo> from <resources/context>
```

This is Journey 0-style read-only discovery. It treats all resources as
evidence, not authority.

Resources may include old SpecKit specs, existing code/tests, docs, design
notes, HLD fragments, prior `.specify` state, prior `.hldspec` state, and human
context.

Journey 0 classifies evidence, conflicts, stale parts, missing decisions, and
whether an authoritative HLD can responsibly be drafted.

Journey 0 must not create backlog, create SpecKit specs, mutate the target repo,
invoke SpecKit, or implement.

### Old SpecKit specs

Old SpecKit specs are evidence, not authority.

HLDspec must not preserve old SpecKit spec boundaries by default. Old specs may
be stale, oversized, mixed, partially implemented, or inconsistent with the
current target repo.

Journey 0 should classify old spec content into product intent, existing
behavior, desired behavior, implementation detail, stale assumption, dependency,
acceptance criterion, test expectation, migration/compatibility concern, and
open human decision.

Old spec content may feed the Evidence Pack, Spec Inventory, Gap Report,
Product Decision Register, and HLD Update Plan. It must not directly become the
new backlog.

## 5. Outputs

Journey 0 **may produce** the following artifacts. (Their schemas are
deliberately **not** defined here — that is a later hardening step.)

| Artifact | Purpose |
|---|---|
| **Brownfield Evidence Pack** | The collected, labeled evidence from all inputs. |
| **Product Surface Map** | What the product appears to be/do, derived from evidence. |
| **Spec Inventory** | Existing specs/spec-fragments and their status (current / stale / superseded). |
| **HLD-Code-Spec Gap Report** | Where HLD, code, and specs agree, diverge, or are silent. |
| **Product Decision Register** | The explicit product decisions discovery surfaced as required. |
| **HLD Draftability Verdict** | Whether an authoritative HLD can responsibly be written yet. |
| **HLD Update Plan** | What Journey 1 should author/harden, from accepted evidence + decisions. |

## 6. Evidence labels

Every material finding in Journey 0 is classified:

- **OBSERVED** — directly present in code, specs, docs, or state.
- **INFERRED** — reasonably derived from evidence, not directly stated.
- **UNKNOWN** — not determinable from available evidence; a gap.
- **CONFLICT** — sources disagree; no silent winner.
- **PRODUCT_DECISION_REQUIRED** — resolving it needs a human product decision, not more inspection.

## 7. Gap handling rules

Journey 0 routes each gap; it does not resolve product or authority conflicts
itself:

| Gap kind | Disposition |
|---|---|
| **HLD gap** (HLD missing/incomplete) | → **Journey 1** (author/harden the HLD). |
| **Code gap** (HLD/spec intent not yet built) | → later **implementation** (Journey 2 → Journey 3), never inside Journey 0. |
| **HLD–code conflict** | → **product decision** (Product Decision Register; `PRODUCT_DECISION_REQUIRED`). |
| **Stale spec residue** | → mark **stale / superseded** in the Spec Inventory; do not treat as authority. |
| **Safety / authority gap** | → **block before implementation**; a missing owner/authority is not auto-resolved. |

## 8. Non-goals (hard boundaries)

Journey 0 **must not**:

- mutate the target repo,
- create or modify `.specify/`,
- create or modify target `.hldspec/`,
- invoke SpecKit,
- approve protected transitions,
- produce implementation work orders,
- silently resolve product or authority conflicts.

Journey 0 is read-only discovery and assessment. It identifies evidence, gaps,
stale inputs, conflicts, and required product decisions, then **hands off to
Journey 1** — which may author or harden the authoritative HLD from accepted
evidence and explicit decisions.

## 9. Status and next steps

This doc is **direction only**. It intentionally does **not**:

- implement code or a discovery machine,
- define artifact schemas,
- run against any target repo (including `~/code/flow`),
- change Journeys 1–3 or their contracts.

Natural next steps, each a separate gated change:

1. **RunSkeptic-harden** this contract into a testable Journey 0 gate (the way
   Journeys 1–3 were hardened), defining PASS/ACTION/BLOCKED and the disconfirming
   checks for "can an authoritative HLD responsibly be written?".
2. **Define schemas** for the Journey 0 artifacts (Evidence Pack, Gap Report,
   Decision Register, Draftability Verdict, HLD Update Plan).
3. **Wire to existing read-only primitives** (`target_discovery.py`,
   `journey3_driver.py`) without granting any mutation or adoption authority.
4. **First read-only proof** on a brownfield proving-ground (e.g. Baton Flow),
   under explicit authorization, once the above are gated.
