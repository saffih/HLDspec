# SpecKit Delegation Prompt Requirements

## Purpose

HLDspec must generate prompts that allow agents to run SpecKit by the book inside the target workspace.

The prompts must be bounded, evidence-backed, and phase-specific.

## Required prompt outputs

For each feature package, HLDspec should generate prompts under:

```text
target/prompts/speckit/<feature>/
  01-specify.md
  02-clarify.md
  03-plan.md
  04-checklist.md
  05-tasks.md
  06-analyze.md
  07-implement.md
```

Implementation prompts may be generated but must remain blocked until explicit approval.

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

## Question-answering policy

When SpecKit asks a question, the agent must classify it as:

```text
ANSWER_FROM_EVIDENCE
ANSWER_FROM_REASONABLE_DEFAULT
ESCALATE_TO_HUMAN
```

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

## RunSkeptic instructions

Prompts must instruct the agent to apply RunSkeptic for high-risk concerns.

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

If the RunSkeptic executable is unavailable, the agent must apply the framework manually from the documented source.

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
