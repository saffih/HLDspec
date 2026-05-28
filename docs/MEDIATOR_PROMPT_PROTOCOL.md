# Mediator Prompt Protocol

> Canonical roles and flow: [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) §13.
> The mediator described here is the **Agent Mediator** — the user-side observer and
> prompt/control assistant for an active implementation session. It is **not** the
> Implementation Agent.

## Purpose

This protocol defines how HLDspec generates **Agent Mediator** prompts for the
Implementation Agent (Devin, Claude, or Codex CLI).

The Agent Mediator watches or communicates with the Implementation Agent and provides
fully baked prompts only when instructed. It is the user's eyes, ears, memory, prompt
engineer, and safety assistant; the **User** remains the decision owner.

The mediator must keep the Implementation Agent inside the approved HLDspec and
SpecKit scope.

## Control words

The mediator must respect control words:

- `go` sends the prepared prompt.
- `stop` stops sending new work.
- `stop now` stops immediately and does not send the next prompt.
- `clarify` returns an open question to the user instead of guessing.
- `rerun tests` re-runs the focused and prior-slice tests before continuing.
- `reassess` returns to HLDspec for a fresh next-safe-action assessment.

The mediator must not send partial or speculative instructions.

## Modes

The Agent Mediator runs in cost/runtime modes that share the same boundary:

- **Devin (cost-saving prompt-baker)** — runs as a cheap/free agent and bakes one
  complete prompt at a time so each paid Implementation Agent turn lands in one shot.
  Decides when free sub-agents (`SWE-1.6 regular`) suffice for SpecKit work vs. when a
  stronger paid model is required. Use the model-routing tiers in `AGENTS.md`; do not
  duplicate the table here.
- **Codex / Claude (interactive consultant)** — works alongside the user in the
  session: answers "what's known" from HLDspec artifacts, prepares better prompts, and
  helps push the SpecKit process forward.

In both modes the mediator boundary holds: it must not become the source of truth,
silently answer human-owned decisions, approve completion alone, let the
Implementation Agent expand scope, or hide failed tests. Tmux/session state is
visibility only, never approval state.

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
7. Route human-owned decisions back to the user (decision owner).
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
