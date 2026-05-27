# HLDspec Orchestration Contract

## Purpose

HLDspec is a judge-led orchestration product. Agents and role-specific tools may propose artifacts, but only the judge can promote an artifact into a controlling artifact for the next phase.

## Core rule

```text
Judge controls.
Senior roles synthesize.
Junior agents extract or draft.
Artifacts are proposed by default.
Only judge promotion makes an artifact controlling.
```

## Role hierarchy

### Judge / Orchestrator

Owns global state, source-of-truth rules, human checkpoints, artifact promotion, allowed next actions, blocked actions, and stop conditions.

The judge must not perform cheap extraction work when a deterministic script or junior bounded task is sufficient.

The generated target `AGENTS.md` is the universal instruction contract for the
active runner. Claude and Devin launch files may exist only as compatibility
shims that point back to `AGENTS.md`; they must not duplicate or override the
orchestration contract.

Optional tmux sessions are a UI convenience for launching, attaching, and
capturing runner panes. They are rendered from the session plan and may not carry
approval state, checkpoint state, or source-of-truth decisions.

### Product Lead

Owns product synthesis: use cases, user stories, acceptance criteria, product open questions, user-visible scope, and non-goals.

The Product Lead may trigger junior product tasks and synthesize their outputs into a Product Manager pack. The Product Lead cannot globally promote artifacts.

### Junior Product agents

Allowed work: extract use cases, draft user stories, draft acceptance criteria, and find product open questions.

Forbidden work: decide priority, approve product scope, decide architecture, modify source HLD, trigger SpecKit, or promote artifacts.

### Architect Lead

Owns architecture synthesis: API/interface boundaries, data/source-of-truth ownership, dependency order, constitution-impacting constraints, and architecture open questions.

The Architect Lead may trigger junior architecture tasks and synthesize their outputs into an Architect pack. The Architect Lead cannot globally promote artifacts.

### Junior Architect agents

Allowed work: extract API boundaries, extract data/source-of-truth objects, map dependencies, and find architecture risks/open questions.

Forbidden work: decide product scope, approve architecture, modify source HLD, trigger SpecKit, or promote artifacts.

### SpecKit Proxy

Consumes only judge-promoted evidence. It may run only the approved single phase. It must not implement unless a later explicit implementation gate is added and approved.

## Cost hierarchy

Before triggering any agent, choose the cheapest sufficient method:

```text
1. deterministic script / grep / JSON transform
2. junior low-context extractor
3. junior focused drafter
4. senior synthesis
5. judge decision
```

Junior tasks must use one task, one role, one artifact type, smallest relevant context, strict output schema, and no approval authority.

## Model routing policy

The judge owns model routing. Use abstract model tiers in artifacts and prompts; map those tiers to concrete provider models at runtime.

```text
MODEL_ROUTINE  -> bounded extraction, summaries, checklist shaping, evidence lookup
MODEL_DEFAULT  -> orchestration, routine repo execution, focused implementation
MODEL_STRONG   -> product drafting, specify, tasks, recoverable implementation work
MODEL_CRITICAL -> judge decisions, constitution, plan, analyze, high-blast-radius implementation, merge/history audit
```

Core rule:

```text
Weakest sufficient model creates.
Strongest necessary model promotes.
```

Concrete model mapping is runner-specific. If only one runner account has
credits, that runner becomes the orchestrator and must still preserve the same
abstract tiers, gates, stop rules, and promotion rules.

| Runner | `MODEL_ROUTINE` | `MODEL_DEFAULT` | `MODEL_STRONG` | `MODEL_CRITICAL` |
|---|---|---|---|---|
| Codex | `gpt-5.5 low` | `gpt-5.5 medium` | `gpt-5.5 high` | `gpt-5.5 xhigh` |
| Claude | `Haiku 4.5` | `Sonnet 4.6` | `Sonnet 4.6` | `Opus 4.7` |
| Devin | `SWE 1.6` | `SWE 1.6` under credit pressure; `codex 4.3 code` when available | `Sonnet 4.5` | `Opus 4.6` |

Devin is optimized for fewer user interaction turns. Prefer a complete run card
with explicit files, commands, acceptance tests, and stop boundaries. `SWE 1.6`
may draft, edit, run tests, and perform a second mechanical review, but it must
not approve architecture, constitution, source-of-truth, API, data ownership,
dependency, security, rollout, split/merge, or promotion decisions.

Standard assigned agents:

| Assigned agent | Model tier | Authority |
|---|---|---|
| HLDspec Judge Orchestrator | `MODEL_CRITICAL` | controls state, gates, promotion, model routing |
| Product Lead Reviewer | `MODEL_STRONG` | product synthesis only |
| Architect Lead Reviewer | `MODEL_CRITICAL` | architecture/data/API/dependency synthesis only |
| Junior Product Extractor | `MODEL_ROUTINE` | evidence extraction only |
| Junior Architect Extractor | `MODEL_ROUTINE` | evidence extraction only |
| SpecKit Specify Proxy | `MODEL_STRONG` | one feature, specify phase only |
| SpecKit Clarify Proxy | `MODEL_STRONG` | evidence-backed clarification only; escalates human-owned decisions |
| SpecKit Plan Proxy | `MODEL_CRITICAL` | one feature, plan phase only |
| SpecKit Tasks Proxy | `MODEL_STRONG` | one feature, tasks phase only |
| SpecKit Analyze Reviewer | `MODEL_CRITICAL` | read-only consistency review |
| SpecKit Implementer | `MODEL_STRONG` or `MODEL_CRITICAL` | approved implementation only |
| Merge History Auditor | `MODEL_CRITICAL` | normal-merge evidence and `MERGED_DONE` classification |

Human-owned decisions are never delegated to `MODEL_ROUTINE`. Architecture, source-of-truth, API, security, data ownership, dependency order, split/merge, implementation approval, and merge/history classification require `MODEL_CRITICAL` review or explicit human approval.

## Promotion lifecycle

Every meaningful artifact starts as `PROPOSED` when it exists.

Allowed promotion statuses:

```text
MISSING
PROPOSED
NEEDS_HUMAN_ANSWERS
NEEDS_REWORK
ACCEPTED
REJECTED
SUPERSEDED
```

Rules:

- `MISSING` blocks dependent downstream actions.
- `PROPOSED` is evidence only and cannot control downstream actions.
- `NEEDS_HUMAN_ANSWERS` blocks downstream actions.
- `NEEDS_REWORK` blocks downstream actions.
- `ACCEPTED` can be consumed by dependent downstream artifacts.
- `REJECTED` cannot be consumed.
- `SUPERSEDED` is audit-only.

## Required promotion chain

```text
Junior task packets -> senior role review
Product Manager pack -> judge promotion
Architect pack -> judge promotion
Answer pack -> judge promotion
Prework package -> explicit human approval
Proxy dry-run -> judge review
Real SpecKit phase -> separate future approval
```

## Hard gates

The proxy dry-run must refuse when:

- answer pack is missing
- answer pack has blocking open questions
- answer pack has not been judge-promoted to `ACCEPTED`
- prework has not been explicitly approved
- requested phase is implementation
- requested phase contains multiple phases

## Agent triggering rule

No agent calls another agent directly.

Correct pattern:

```text
Judge -> senior role -> junior task packets -> senior synthesis -> judge promotion
```

Forbidden pattern:

```text
Junior output -> answer pack -> SpecKit proxy
Senior pack -> SpecKit proxy without judge promotion
PM agent -> Architect agent -> SpecKit proxy
```
