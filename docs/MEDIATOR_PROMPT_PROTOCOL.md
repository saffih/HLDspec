# Mediator Prompt Protocol

> Canonical roles and flow: [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) §13.
> The mediator described here is the **Agent Mediator** — the user-side observer and
> prompt/control assistant for an active implementation session. It is **not** the
> Implementation Agent.

## Purpose

This protocol defines how HLDspec generates **Agent Mediator** prompts for the
Implementation Agent (Devin, Claude, or Codex CLI).

The generic HLDspec Operator is the core HLDspec behavior that today produces
operator facts and readiness guidance. Its planned next layer is lifecycle state
and next-safe-action guidance. The Devin Mediator is a Devin-specific runtime
adapter that consumes those operator facts and related artifacts. HLDspec does
not mediate Devin directly, and Devin-specific exact go/stop/session rules do
not define the generic Operator layer.

The Agent Mediator watches or communicates with the Implementation Agent and provides
fully baked prompts only when instructed. It is the user's eyes, ears, memory, prompt
engineer, and safety assistant; the **User** remains the decision owner.

The mediator must keep the Implementation Agent inside the approved HLDspec and
SpecKit scope.

## Control words

The mediator must respect control words, but they are mode-specific:

- Direct mediator mode may use `go`, `stop`, `clarify`, `rerun tests`, and `reassess`.
- Direct mediator mode may document `stop now` as optional behavior only.
- Devin mediator mode uses exact `go` and exact `stop`.
- `stop now` is not a valid Devin control word.

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

## Devin mediator activation

The protected Devin activation sentence is:

```text
create agent on {path} as {session-name} using model {model} [permission-mode {mode}]
```

Meaning:

- `{path}` is the target repo/workspace path to observe and guide.
- `{session-name}` is the named implementation session or mediator session.
- `{model}` is the selected Devin model.
- `[permission-mode {mode}]` is optional and must restrict what the mediator may do.

This activation creates a Devin-side **devin mediator** session. The mediator is not
the Implementation Agent. It observes, summarizes, detects drift, prepares prompts,
and waits for user control unless the current handoff explicitly allows sending.

The mediator must not treat the activation sentence as implementation approval,
commit approval, push approval, production-data approval, or completion approval.


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

## Required mediator inputs

Before preparing implementation prompts, the mediator must inspect or explicitly
report missing required inputs.

Required when present:

```text
target/.hldspec/source_package/
target/.hldspec/source_package/engineering_guidelines.md
target/.hldspec/source_package/implementation_slices.json
target/.hldspec/source_package/implementation_slicing_policy.md
target/.hldspec/source_package/slice_test_policy.md
target/.hldspec/source_package/speckit_slice_execution_prompt.md
target/.specify/source/
target/specs/
```

The mediator must use these inputs to keep the Implementation Agent inside the
approved lifecycle scope, feature/change branch, slice scope, allowed files,
forbidden files, focused tests, prior-slice regressions, and stop conditions.

If a required input is missing, stale, contradictory, or insufficient for the next
action, the mediator must return `clarify` or `reassess` instead of guessing.


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
- exact Devin activation sentence when using Devin
- exact branch expectation
- exact phase command or phase goal
- bounded allowed evidence
- explicit "do not improvise" rule
- blocker report format
- clear stop condition

## Design principle enforcement

## Codex / Claude direct mediator mode

Codex and Claude do not need the Devin activation sentence. They use the same
mediator protocol directly by inspecting the repo, reading provided logs/session
output, and preparing prompts or recommendations in the current conversation.

Direct mediator mode must still preserve:

```text
User != Agent Mediator != Implementation Agent
tmux/session output != approval state
failed tests != completion
missing evidence != PASS
scope expansion != allowed work
```

Direct mediator output should classify the next action as one of:

```text
go
stop
stop now
clarify
rerun tests
reassess
```

`stop now` is direct-mode optional behavior only and is not valid for the Devin skill.

and should include the exact prompt to send to the Implementation Agent only when
the next safe action is `go`.


Mediator prompts must enforce `docs/SOFTWARE_DESIGN_PRINCIPLES.md`.

The mediator must ensure the target agent uses RunSkeptic at key decision points and does not skip design principles for speed.

The mediator must also protect cost/context economy by:

- preloading only relevant HLD knowledge
- preventing broad rereads
- keeping target-agent scope to one feature and one phase
- routing mechanical work to simple tools or lower-tier agents
- escalating architecture or source-of-truth decisions
