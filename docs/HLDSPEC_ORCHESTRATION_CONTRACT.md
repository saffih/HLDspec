# HLDspec Orchestration Contract

made by AI

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
