# SpecKit Delegation Prompt Requirements

## Purpose

HLDspec must generate prompts that allow agents to run SpecKit by the book inside the target workspace.

The prompts must be bounded, evidence-backed, and phase-specific.

## Required prompt outputs

For each feature package, HLDspec should generate prompts under:

```text
target/prompts/speckit/<feature>/
  RUN_CARD.md
  RUN_CARD.json
  01-specify.md
  02-clarify.md
  03-plan.md
  04-checklist.md
  05-tasks.md
  06-analyze.md
  07-implement.md
```

`RUN_CARD.md` and `RUN_CARD.json` are the first-class execution handoff
contract. The numbered phase prompts are supporting material for running the
approved package through the SpecKit lifecycle.

Implementation prompts may be generated but must remain blocked until explicit approval.

## SpecKit Run Card contract

The Run Card is a Markdown/JSON contract. It should declare:

```text
Requires:
- approved prework
- dependency graph and invocation queue
- bounded evidence
- clean RunSkeptic status

Ensures:
- one bounded execution handoff
- explicit stop conditions
- explicit report-back format
- reassessment triggers for HLDspec
```

## Required prompt fields

Each prompt must include:

```text
Prompt ID:
Target agent:
Target surface:
Goal:

Context:
- Target directory:
- Branch:
- Feature/package:
- SpecKit phase:
- Existing artifacts:
- Allowed evidence sources:

Pre-loaded HLD knowledge:
- HLD group:
- HLD sections:
- Key constraints:
- Key dependencies:
- Source-of-truth locations:
- API/data ownership:
- Testability requirements:
- Constitution principles:

Subagent strategy:
- MODEL_ROUTINE:
- MODEL_DEFAULT:
- MODEL_STRONG:
- MODEL_CRITICAL:

Required action:
Constraints:
RunSkeptic instructions:
Question-answering policy:
Output required:
Stop condition:
```

## Pre-loaded context rule

The prompt must include the relevant extracted HLD knowledge directly.

The target agent should not reread huge HLD files unless the prompt explicitly authorizes it.

Allowed evidence should be bounded to:

- `target/targetHLD/HLD.md`
- extracted HLD sections under `target/targetHLD/sections/`
- spec package record
- dependency graph
- invocation queue
- constitution update plan or approved constitution
- proxy dossier
- relevant existing SpecKit artifacts

## Question-answering and clarification policy

When SpecKit asks a question, the receiving agent must not stop by default.
It must first try to answer from the approved HLDspec evidence already included in
or referenced by the prompt / Run Card.

Every question is classified as:

```text
ANSWER_FROM_EVIDENCE
ANSWER_FROM_APPROVED_DEFAULT
ESCALATE_TO_HUMAN
```

### ANSWER_FROM_EVIDENCE

Use when the answer is directly supported by approved evidence such as:

- active HLD sections
- working HLD
- spec package map
- dependency graph
- invocation queue
- constitution update plan or approved constitution
- role reviews
- proxy dossier
- Run Card

If the evidence clearly answers the question, answer it and continue.
Record the evidence path or section used.

### ANSWER_FROM_APPROVED_DEFAULT

Use only for safe, reversible defaults that do not affect architecture, source of
truth, security/privacy, data ownership, dependency order, feature split/merge,
user-visible scope, constitution rules, or implementation approval.

### ESCALATE_TO_HUMAN

Stop and escalate only when the question exposes a real gap, contradiction, or
human-owned decision.

Escalate questions that affect:

- architecture boundary
- source of truth
- constitution rule
- API contract
- data ownership
- security or privacy
- user-visible scope
- dependency order
- feature split or merge
- implementation approval

Stop conditions for clarification:

- the approved HLD/prework evidence does not answer it
- approved evidence is contradictory
- the answer would change architecture boundaries
- the answer would choose or change a source of truth
- the answer affects API contract, data ownership, security/privacy, dependency
  order, feature split/merge, user-visible scope, constitution rules, or
  implementation approval
- RunSkeptic returns ACTION or CONFLICT

## One-Go Execution Policy and Answer-Finding Protocol

Generated bundle prompts and SpecKit Run Cards must render these sections so the receiving agent stays self-sufficient instead of stopping at the first SpecKit question:

- `## One-Go Execution Policy` — do as much as safely possible in one run; clarification is not a stop by default; do not stop just because SpecKit asks a question.
- `## Answer-Finding Protocol` — resolve clarification questions from approved evidence first, in a defined order, before escalating.
- `## HLD Section Gap Map` — map each clarification to its evidence dimension (Feature purpose, Architecture boundary, Source of truth, Dependency order, acceptance/scope, governance/approval) and read the matching approved evidence first.
- `## Clarification Policy` — stop only when approved evidence is missing, approved evidence is contradictory, the question requires a human-owned decision, or RunSkeptic returns ACTION or CONFLICT.
- `## How to run RunSkeptic` — the self-contained RunSkeptic operating block (framework path, flow, statuses, evidence markers, report fields).
- `## Reassessment Request` — the structured request the receiving agent returns to HLDspec when a real blocker stops the run, instead of guessing or silently halting.

The Answer-Finding Protocol must point at active HLD sections, the HLD Section Gap Map, role reviews, the spec package map, the dependency graph, the invocation queue, constitution/prework, the Run Card, and the proxy dossier.

These sections are rendered from one canonical source, `hldspec/handoff_policy_blocks.py`, so bundle prompts and Run Cards cannot drift. Each major policy section must appear exactly once in a rendered prompt or Run Card.

## Clarification Policy

- Resolve clarification questions from approved evidence first.
- When SpecKit asks clarification questions, resolve them from approved evidence first.

Clarification is not a stop by default.

If SpecKit asks clarification questions, resolve them from approved evidence first.

Stop only when approved evidence is missing, approved evidence is contradictory, or the question requires a human-owned decision.

If RunSkeptic returns ACTION or CONFLICT, stop even if the clarification appears answerable.

The receiving agent must first try to answer from approved HLDspec evidence: the active HLD sections, Working HLD, spec package map, dependency graph, invocation queue, constitution update plan or approved constitution, role reviews, Run Card, proxy dossier, and relevant existing SpecKit artifacts.

The agent should answer and continue when the answer is directly supported by approved evidence or by an approved safe default.

The agent must stop and escalate only when approved evidence is missing, approved evidence is contradictory, the answer would decide a human-owned issue, or RunSkeptic returns ACTION or CONFLICT.

Human-owned clarification includes architecture boundary, source of truth, constitution rule, API contract, security/privacy, data ownership, user-visible scope, dependency order, feature split/merge, and implementation approval.

## RunSkeptic instructions

Prompts and Run Cards must include a self-contained **How to run RunSkeptic** operating block. It is not enough to say "run RunSkeptic"; the receiving agent must know where to read the framework, what flow to apply, what statuses are allowed, what evidence to report, and when to stop.

The operating block must require the agent to read the actual current framework file first:

```text
~/code/skeptic/skeptic.md
```

The operating block must include the required flow:

```text
GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
```

The operating block must define and require only these statuses:

```text
PASS
ACTION
CONFLICT
```

The operating block must require findings to classify evidence as:

```text
OBSERVED
REPRODUCED
HISTORICAL
INFERRED RISK
```

The operating block must require this output shape:

```text
RunSkeptic status: PASS | ACTION | CONFLICT
Scope reviewed:
Evidence used:
Findings:
Unknowns:
Human decisions needed:
Verification performed:
Next safe action:
```

Minimum concerns:

- architecture
- dependencies
- API contracts
- data ownership
- source of truth
- testability
- security
- reliability
- quality gates

If the real framework file is unavailable, the agent must not claim full RunSkeptic compliance. It may use the embedded fallback block only if it reports the missing source and lower confidence.

Missing concern evidence is ACTION or CONFLICT, not PASS.

## Agent model guidance

Use these abstract tiers:

| Tier | Use for |
|---|---|
| MODEL_ROUTINE | Deterministic extraction, summaries, inventories |
| MODEL_DEFAULT | Orchestration, repo inspection, focused implementation |
| MODEL_STRONG | Bounded module work, single-slice refactors, adapters |
| MODEL_CRITICAL | Architecture decisions, contract changes, promotion gates |

A lower-tier agent may propose. Only the judge or approved critical reviewer may promote across gates.

## Stop rules

The agent must stop when:

- the requested SpecKit phase is complete
- a blocker is found
- evidence is insufficient for a human-owned decision
- implementation would start without approval
- a destructive operation would be required
- a commit or push would be required without explicit approval

## Output requirements

Each phase report must include:

- phase run
- files created or changed
- questions answered from evidence
- questions escalated
- tests or tooling required
- RunSkeptic findings
- next allowed step
- blockers

## Software design principles in prompts

Generated SpecKit prompts must include the relevant parts of `docs/SOFTWARE_DESIGN_PRINCIPLES.md`.

Each prompt should include only the principles needed for the current phase and feature package.

Prompts must explicitly require RunSkeptic before decisions involving:

- architecture boundaries
- interfaces/contracts
- message bus or event-driven behavior
- state machines
- persistent loops or resumability
- data ownership
- testability
- accessibility
- security/reliability/performance
- quality gates

Prompts must also enforce cost/context economy:

- do not reread the full HLD unless authorized
- use preloaded HLD knowledge first
- inspect only allowed evidence
- use weakest sufficient model
- stop when blocked

## Backend technology recommendation usage

Generated prompts must include the selected backend technology recommendation for the current phase when relevant.

The prompt must say whether a tool is a default or an upgrade.

If it is an upgrade, the prompt must include the trigger and RunSkeptic result.

Prompts must not include unrelated toolbox entries that bloat context.
