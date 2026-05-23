# HLDspec Agent Orchestrator Contract

made by AI

## User trigger

The intended user-facing trigger is:

```text
HLDspec /absolute/path/to/HLD.md
```

Optional flags may exist later, but the core trigger must be enough for a user to start the process.

## Product shape

HLDspec is agent-first and judge-controlled.

```text
Human
-> HLDspec Orchestrator Agent
   -> internal CLI/tools
   -> bounded junior agents for cheap/simple work
   -> senior Product/Architect synthesis
   -> judge promotion gates
   -> one safe SpecKit proxy dry-run phase
```

The CLI is internal machinery. The human should not need to remember the internal script sequence.

## Orchestrator responsibilities

The orchestrator agent owns process guidance.

It must:

- accept the source HLD path
- treat the source HLD as read-only
- create or reuse a workspace
- work only on workspace copies
- run HLDspec tools internally
- detect the current state/gate
- guide the human through checkpoint questions
- use bounded junior helpers only for narrow extraction/explanation tasks
- build or request Product/Architect/answer-pack artifacts only after earlier gates pass
- stop when a checkpoint or unsafe action is reached
- ask the human only real checkpoint questions

It must not:

- invoke SpecKit unless judge gates explicitly allow it
- create final specs manually
- implement
- mutate the source HLD
- answer human checkpoint questions silently
- promote artifacts without explicit judge action

## Junior subagent rule

Cheap/simple work should be delegated to junior bounded agents, not done by the judge or senior roles.

Junior agents may:

- explain one checkpoint question
- extract candidate use cases
- draft candidate user stories
- extract API/data/dependency evidence
- identify risk/open-question candidates

Junior agents must not:

- decide
- approve
- promote
- edit source HLD
- invoke SpecKit
- implement
- own final synthesis

## Senior role rule

Senior Product and Architect roles synthesize junior outputs.

Product Lead owns:

- product use cases
- user stories
- acceptance criteria
- product open questions
- product recommendation

Architect Lead owns:

- API/interface boundaries
- data/source-of-truth ownership
- dependency order
- constitution/architecture questions
- architecture recommendation

Senior roles still cannot globally promote artifacts. Only the judge can promote.

## Judge rule

The judge controls:

- current state
- controlling artifact
- allowed next actions
- blocked actions
- human checkpoints
- artifact promotion
- stop conditions

Generated artifact existence is not approval.

```text
artifact exists -> PROPOSED
judge review -> ACCEPTED / NEEDS_HUMAN_ANSWERS / NEEDS_REWORK / REJECTED
```

## Current mandatory gate behavior

If the state is:

```text
CONVERSION_CHECKPOINT -> hld_conversion_decisions
```

the orchestrator must:

1. generate or read the question guide
2. explain questions one at a time
3. ask the human to choose allowed options
4. record answers only through validated queue tools
5. stop before conversion until all blocking questions are answered

## SpecKit rule

SpecKit is not invoked by the agent-start entrypoint.

Real SpecKit execution remains deferred until:

- HLD is converted
- first-readonly passes
- question guide/interview flow is verified
- Product/Architect packs are reviewed
- answer pack is READY
- judge promotion marks required artifacts ACCEPTED
- proxy dry-run is DRY_RUN_READY
