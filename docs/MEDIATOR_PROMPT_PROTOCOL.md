# Mediator Prompt Protocol

## Purpose

This protocol defines how HLDspec generates mediator prompts for target agents such as Devin, Claude, or Codex CLI.

A mediator watches or communicates with a target agent and provides fully baked prompts only when instructed.

The mediator must keep the target agent inside the approved HLDspec and SpecKit scope.

## Control words

The mediator must respect control words:

- `go` sends the prepared prompt.
- `stop` stops sending new work.
- `stop now` stops immediately and does not send the next prompt.

The mediator must not send partial or speculative instructions.

## General mediator prompt template

```text
Prompt ID: [ID]

Target agent: [Devin/Claude/Codex CLI]
Target surface: [tmux session/API/CLI]
Goal: [Brief goal statement]

Context:
- Target directory: [path]
- HLD workspace: target/targetHLD/
- HLD specs available: [path]
- Design docs available: [path]
- Existing artifacts: [list key files]

Pre-loaded HLD Knowledge:
[Extract key answers from HLD/spec packages upfront.]
- [Key group assignments]
- [Key constraints]
- [Key dependencies]
- [Source-of-truth locations]
- [API/data ownership]
- [Testing requirements]
- [Constitution principles]

Subagent Strategy:
- Use MODEL_ROUTINE for deterministic extraction, summaries, inventories.
- Use MODEL_DEFAULT for orchestration, repo inspection, focused implementation.
- Use MODEL_STRONG for bounded module work, single-slice refactors, adapters.
- Use MODEL_CRITICAL for architecture decisions, contract changes, promotion gates.
- Default to the weakest sufficient model.
- Scope junior agents to one feature directory and one SpecKit phase.
- If blocked, report blocker and stop. Never improvise.

Required action:
[Concise task description using pre-loaded HLD context.]

Constraints:
- Do not reread huge HLD specs unless explicitly allowed.
- Do not reread design docs unless explicitly allowed.
- Treat source HLD as read-only.
- Work only on workspace copies.
- Use the approved target directory.
- Stop before commit, push, destructive operations, or implementation without approval.
- Answer human checkpoint questions explicitly.

RunSkeptic Instructions:
- Source: [path to skeptic.md]
- Flow: GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
- If executable unavailable, apply framework manually using documentation.
- Missing concern evidence is ACTION or CONFLICT, not silent PASS.

Output required:
[Specific deliverables.]

Stop condition:
[Clear completion criteria.]
```

## Mediator responsibilities

The mediator must:

1. Pre-load context from HLDspec artifacts.
2. Produce one complete prompt at a time.
3. Keep scope bounded to one feature and one phase unless approved.
4. Monitor for blockers.
5. Detect target-agent drift.
6. Prevent improvised architecture decisions.
7. Route human-owned decisions back to the judge/human.
8. Stop on control words.
9. Never approve its own work silently.
10. Never push or commit without explicit approval.

## Devin-specific notes

For Devin-style agents, prompts must include:

- exact target repo path
- exact branch expectation
- exact phase command or phase goal
- bounded allowed evidence
- explicit "do not improvise" rule
- blocker report format
- clear stop condition

## Design principle enforcement

Mediator prompts must enforce `docs/SOFTWARE_DESIGN_PRINCIPLES.md`.

The mediator must ensure the target agent uses RunSkeptic at key decision points and does not skip design principles for speed.

The mediator must also protect cost/context economy by:

- preloading only relevant HLD knowledge
- preventing broad rereads
- keeping target-agent scope to one feature and one phase
- routing mechanical work to simple tools or lower-tier agents
- escalating architecture or source-of-truth decisions
