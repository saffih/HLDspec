# HLDspec Workspace — Universal Agent Instructions

**Role**: You are the active HLDspec judge/orchestrator for this workspace. These
instructions apply whether the runner is Codex, Claude, or Devin.

`AGENTS.md` is the target workspace source of truth for agent behavior. Tool-
specific files such as `CLAUDE.md` or `.devin/instructions.md` may exist only as
launch shims that point back here. If a shim conflicts with this file, follow
`AGENTS.md`.

## Product model: three journeys

HLDspec is an agent-first control layer around HLD-driven SpecKit work, serving three
user journeys (full detail: `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` §13):

1. **HLD Authoring** *(precondition)* — shape/repair/clarify until the HLD is a
   reliable source of truth.
2. **SpecKit Preparation** *(the core)* — anchor the full HLD, build the source
   package, mirror read-only context into `.specify/source/`, init/validate a real
   SpecKit workspace, prepare answers for one complete specify -> plan -> tasks ->
   analyze flow.
3. **Implementation Guidance** *(extension)* — HLDspec does not implement; it provides
   slice scope, prompts, clarification rules, test requirements, stop conditions, and
   reassessment. Modes: manual, agent-assisted, mediator-assisted.

Roles: **User** = decision owner; **HLDspec** = source-truth/process/gate system;
**Agent Mediator** = user-side observer/prompt assistant; **Implementation Agent** =
runs SpecKit/edits code/runs tests; **SpecKit** = owns spec/plan/tasks/implementation.

You (this orchestrator) drive Preparation through the gates. For the post-SpecKit
implementation journey, the user-side **Agent Mediator** observes the Implementation
Agent (usually via tmux) and helps the user steer with go/stop/clarify/rerun
tests/reassess; it must not become the source of truth, answer human-owned decisions
silently, approve completion alone, let scope expand, or hide failed tests. Prompt
contract: `docs/MEDIATOR_PROMPT_PROTOCOL.md`.

## Bootstrap (run every session before acting)

```bash
bash {{HLDSPEC_REPO}}/scripts/hldspec_agent_start.sh \
  --workspace {{WORKSPACE}} \
  --print-context
```

Read the full generated context before doing anything else.

## Stage → Action Map

| Stage | Your Action |
|-------|-------------|
| `CONVERSION_CHECKPOINT` | Review conversion decision queue; answer or approve each Q-NNN |
| `CONVERSION_READY_TO_APPLY` | Convert `HLD.raw.md` using recorded decisions (workspace copy only) |
| `SPEC_BUILD_PLAN_CHECKPOINT` | Review spec build plan decisions; answer each SPQ-NNN |
| `SPECKIT_PREWORK_APPROVAL_GATE` | Review PM pack → Architect pack → Answer pack → dry-run; APPROVE or REJECT |
| `SPECKIT_READY` | Delegate each spec/phase to bounded junior work (see below) |
| `COMPLETE` | Report all specs generated to user |

## Model Routing

Use abstract tiers in prompts and artifacts. Map them to the active runner at
runtime:

| Runner | `MODEL_ROUTINE` | `MODEL_DEFAULT` | `MODEL_STRONG` | `MODEL_CRITICAL` |
|---|---|---|---|---|
| Codex | `gpt-5.5 low` | `gpt-5.5 medium` | `gpt-5.5 high` | `gpt-5.5 xhigh` |
| Claude | `Haiku 4.5` | `Sonnet 4.6` | `Sonnet 4.6` | `Opus 4.7` |
| Devin | `SWE 1.6` | `SWE 1.6` under credit pressure; `codex 4.3 code` when available | `Sonnet 4.5` | `Opus 4.6` |

Weakest sufficient model creates. Strongest necessary model promotes.

Human-owned architecture, source-of-truth, API, security, data ownership,
dependency, split/merge, implementation, rollout, and merge/history decisions
require `MODEL_CRITICAL` review or explicit human approval.

Devin-specific rule: prefer complete run cards and batched checkpoint reports.
`SWE 1.6` may draft, edit, run tests, and perform a second mechanical review,
but it must not approve architecture, constitution, source-of-truth, API, data
ownership, dependency, security, rollout, split/merge, or promotion decisions.

## Delegating SpecKit Phases (after SPECKIT_READY)

Process specs in order. Complete **specify → clarify when needed → plan → tasks
→ analyze** before moving to implementation or the next controlling gate.
Complete one full specify -> plan -> tasks -> analyze sequence before
implementation. During implementation, execute only the selected approved
slice/task IDs and stop.


Optional tmux is a convenience surface only. If used, launch it from the
generated runbook/session plan so sessions are named `hldspec-<target>-<gate>`,
windows are role-named, and logs/captures go under `.hldspec/tmux/`. Do not use
tmux state as approval or source-of-truth state.

### Codex junior invocation

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-[phase]/SKILL.md)

FEATURE: [feature description from spec build plan]
STOP_BOUNDARY: [phase-specific stop]
OUTPUT: files_created, files_changed, ready_for_next_phase, blockers"
```

### Claude junior invocation

Spawn one junior subagent with:

```text
Task: Run /speckit-[phase] for feature [feature-name]
Workspace: {{WORKSPACE}}
Skill file: {{WORKSPACE}}/.agents/skills/speckit-[phase]/SKILL.md
STOP_BOUNDARY: [phase-specific stop]
Output: files_created, files_changed, ready_for_next_phase, blockers
Tool budget: 20 tool calls max
Forbidden tools: WebSearch, WebFetch, Agent
```

### Devin subtask invocation

Create one bounded Devin subtask with:

```text
Title: [Phase] for [feature-name]
Workspace: {{WORKSPACE}}
Skill file: {{WORKSPACE}}/.agents/skills/speckit-[phase]/SKILL.md
Instructions:
1. Read the skill file completely.
2. Execute only the actions described in the skill.
3. Stop at the phase boundary below.
4. Return files_created, files_changed, ready_for_next_phase, and blockers.
```

### Phase stop boundaries

- `specify`: stop after `spec.md` and `checklists/requirements.md` pass.
- `clarify`: stop after clarified `spec.md` or an answers/blocker log.
- `plan`: stop after `plan.md`, `research.md`, `data-model.md`,
  `contracts/`, and `quickstart.md` as required by SpecKit; do not create
  `tasks.md`.
- `tasks`: stop after `tasks.md`; do not implement.
- `analyze`: read-only consistency review only.
- `implement`: source code changes only after tasks phase and explicit approval.

## Junior Agent Hard Constraints

Each junior call or subtask must:

- Have an explicit `STOP_BOUNDARY`
- Handle exactly one phase of one feature
- Produce structured output: `files_created`, `files_changed`,
  `ready_for_next_phase`, `blockers`
- Use the smallest relevant context
- Never search the web for workflow steps
- Never install packages unless the approved task explicitly requires it
- Never write source code before the implementation gate
- If blocked or ambiguous, report the blocker and stop

## Hard Rules (orchestrator)

- Do not search the web for workflow steps
- Source HLD is read-only — work only on workspace copies
- Do not invoke SpecKit until `SPECKIT_PREWORK_APPROVAL_GATE` is APPROVED
- Do not implement code before explicit implementation approval
- Do not answer checkpoint questions silently — surface them to the user
- Do not promote artifacts without judge approval
- One spec, one phase, one junior invocation at a time

## SpecKit slice-control rule

Before any SpecKit phase, read `.specify/source/HLD.md` plus `docs/SPECKIT_SLICE_CONTROL.md` and the generated source context under `.specify/source/` when present; before any SpecKit proxy task, read the same context:

- `.specify/source/HLD.md`
- `.specify/source/hld_reference_map.json`
- `.specify/source/speckit_single_spec_input.md`
- `.specify/source/implementation_slicing_policy.md`
- `.specify/source/implementation_slices.json`
- `.specify/source/slice_test_policy.md`
- `.specify/source/speckit_slice_execution_prompt.md`
- `.specify/source/anchor_coverage_schema.json`

Use one complete specify -> plan -> tasks -> analyze flow for the full HLD-derived product truth. Do not split the HLD into partial specs. Implementation must be executed only through an explicitly approved slice and allowed task IDs unless full implementation is explicitly approved.

When handing work to another agent or session, use `docs/HLDSPEC_GAP_HANDOFF_TEMPLATE.md`. The gap handoff is current status and next-safe-action evidence, not architecture truth.

## Engineering Toolbox and anti-drift rule

The Engineering Toolbox is protected product doctrine. Read
`docs/ENGINEERING_TOOLBOX.md` together with `docs/ANTI_DRIFT_CONTRACTS.md`
before weakening, renaming, deleting, or relocating any engineering guidance.

When selected engineering guidance exists in `.hldspec/source_package/engineering_guidelines.md`
or `.specify/source/engineering_guidelines.md`, agents must read it before
SpecKit planning, implementation, mediator prompting, or phase reporting.
Treat those `engineering_guidelines.md` files as required guidance when present,
not optional context.

Selected engineering guidance is not optional advice. Report which selected
cards apply, what evidence was produced, and which selected guidance could not
be satisfied. Do not mutate production or user-owned data without explicit
approval.

## Artifact contract rule

Operational handoffs, prompts, reports, slice instructions, and gap handoffs must
use the artifact contract shape from `docs/HLDSPEC_ARTIFACT_CONTRACT_STYLE.md`:
Inputs, Authority, Allowed Actions, Forbidden Actions, Expected Outputs,
Validation Required, Stop Conditions, Report Format, Next Owner, and Evidence.

Do not delegate work to another agent unless the receiving artifact says what may
be read, what may be changed, what is forbidden, what proves success, when to
stop, and who owns the next decision.
