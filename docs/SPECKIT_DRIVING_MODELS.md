# SpecKit Driving Models

HLDspec drives SpecKit work through **two distinct models**. Both run the same
underlying SpecKit ritual; they differ in their entry point and in how much they
decompose first. This doc documents both, names the canonical ritual chain they
share, and is bound to the code by an anti-drift test
(`tests_v2/test_speckit_driving_models_docs.py`) so the chain cannot silently
diverge between the doc and the implementations.

> Canonical architecture/terminology still wins from
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md). This doc
> is the focused reference for the *two driving models* and *the shared chain*.

---

## The canonical SpecKit ritual chain

Both models drive the same ordered SpecKit ritual. This is the single source of
truth for the chain:

```
CONSTITUTION → SPECIFY → CLARIFY → PLAN → CHECKLIST → TASKS → ANALYZE → IMPLEMENT
```

| Step | SpecKit skill | Produces |
|---|---|---|
| `CONSTITUTION` | `/speckit.constitution` | `.specify/memory/constitution.md` (per project, before features) |
| `SPECIFY` | `/speckit.specify` | feature branch + `specs/<branch>/spec.md` |
| `CLARIFY` | `/speckit.clarify` | resolves `[NEEDS CLARIFICATION]` markers |
| `PLAN` | `/speckit.plan` | `plan.md` |
| `CHECKLIST` | `/speckit.checklist` | quality checklist over the plan |
| `TASKS` | `/speckit.tasks` | `tasks.md` |
| `ANALYZE` | `/speckit.analyze` | cross-artifact consistency verdict |
| `IMPLEMENT` | `/speckit.implement` | code |

`CONSTITUTION` is a per-project step that precedes feature work. The per-feature
ritual is the chain from `SPECIFY` onward.

**SpecKit owns every step** — it creates branches, writes specs/plans/tasks, and
implements code. HLDspec never generates these; it orders the steps, gates them,
and reports state.

---

## Model 1 — HLD pipeline (decompose-then-drive)

**Entry point:** a source HLD.

`ProjectMachine` runs the full preparation chain (HLD conversion → spec build
plan → prework → approval gate), then `SpecKitExecutionMachine` drives the ritual
**feature-by-feature in dependency order** for the many features decomposed from
the HLD. State persists in `speckit_execution_state.json` so runs resume across
sessions.

`SpecKitExecutionMachine` has two modes:

- **gated** (default, `invoker=None`): returns a human checkpoint per phase; the
  human/orchestrator invokes SpecKit. The machine only orders and gates.
- **live** (`invoker` provided): actually invokes SpecKit per phase through
  `SpecKitInvoker` (`hldspec/speckit_invoker.py`), deriving phase completion from
  whether the project tree actually changed (anti-hollow-completion gate).

Use this model when you start from an HLD and need many ordered features prepared
and driven by the book.

## Model 2 — Ad-hoc in-target (drive one named feature)

**Entry point:** standing in a target repo, "I want the next feature: X".

`next_feature_readiness.py` is **read-only**. It infers the current ritual phase
from durable repo evidence (git branch, `specs/<branch>/` artifacts, constitution
presence, dirty tree, recorded execution evidence) — never from chat history or
session memory — and reports:

- the current phase,
- verified vs missing evidence,
- the single next SpecKit command (`speckit_next_action`),
- blockers, and the single next safe action.

It models the same ritual chain but with a richer state vocabulary
(`READY_FOR_SPECKIT_SPECIFY`, `READY_FOR_PLAN`, `IMPLEMENTATION_REVIEW_REQUIRED`,
`READY_FOR_COMMIT`, `MERGE_BLOCKED_PENDING_CI_OR_APPROVAL`, …) because it also
covers the pre-ritual (init/constitution), the commit/push/merge tail, and
branch/spec binding conflicts. It is resumable by construction: rerunning after
an interruption reproduces the same phase from the same repo state.

This model **never** runs SpecKit, creates branches, commits, pushes, opens PRs,
or merges; `merge_allowed` is always `False`.

Use this model when you are in a repo and want to drive one feature, layer by
layer, on top of the current state.

---

## Why two models, and how they stay honest

The two models are two front doors over the same ritual; they currently encode
the chain independently (the executor's `PHASE_ORDER`, the invoker's
`PHASE_SKILL`, and the navigator's `/speckit.X` next-actions). Whether they should
collapse onto one shared chain definition is an open architecture decision and is
**not** resolved here.

Until it is, the anti-drift test
(`tests_v2/test_speckit_driving_models_docs.py`) binds all representations to the
canonical chain above: if the chain changes in the doc, the executor, the
invoker, or the navigator without the others, the test fails. This makes the
current dual-model state safe — the chain cannot silently diverge.
