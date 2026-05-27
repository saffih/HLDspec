# Agent bootstrap for this repo

> **Canonical system model:** for terminology, ownership boundaries, the full flow, and the SpecKit Run Card, read `docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md` — it is authoritative and wins on any conflict.

> **HLDspec repo-development handoff:** before editing this repo or handing work to another model/agent, read `docs/HLDSPEC_DEVELOPMENT_HANDOFF.md` and `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md`. `AGENTS.md`, compatibility shims, and generated `HANDOFF.md` files are pointers; the docs files are the source of truth.

## HLDspec trigger

When a user prompt starts with `HLDspec`, use the minimal agent UX contract:

```text
docs/HLDSPEC_MINIMAL_AGENT_UX.md
```

Accepted short forms include:

```text
HLDspec HLD: /path/to/HLD.md create /path/to/target
HLDspec create /path/to/target from /path/to/HLD.md
HLDspec HLD: /path/to/HLD.md target: /path/to/target runtime: claude
```

Agent behavior:

1. Extract source HLD, target workspace, mode, runtime, and comment.
2. Default runtime to `claude` when omitted.
3. Supported runtime values are `claude`, `codex`, and `devin`.
4. Use the public HLDspec facade: `start`, `status`, `review`, `doctor`, and later `continue` only when safe.
5. Do not expose low-level scripts to the user unless debugging a failure.
6. Return only target, mode, runtime, blockers, and next safe action.

Example minimal request:

```text
HLDspec HLD: /Users/saffi/code/flow/flow-hld.md create /Users/saffi/code/flowHld runtime claude
```

## Hard rules

- Do not search the web for this workflow.
- Do not search unrelated memory/docs before reading the generated context.
- Canonical flow reference: `docs/CANONICAL_FLOW.md`.
- Treat the source HLD as read-only.
- Work only on workspace copies.
- HLDspec must use SpecKit instead of reimplementing SpecKit.
- Before any SpecKit phase, read `.specify/source/HLD.md`, `.specify/source/hld_reference_map.json`, `.specify/source/speckit_single_spec_input.md`, `.specify/source/implementation_slices.json`, and `.specify/source/slice_test_policy.md`; use one full specify/plan/tasks/analyze cycle, then implement only the explicitly selected slice unless full implementation is approved.
- Invoke SpecKit only via the proxy script after SPECKIT_PREWORK_APPROVAL_GATE is passed and prework is APPROVED.
- Before any SpecKit phase, read `.specify/source/HLD.md`, `.specify/source/hld_reference_map.json`, `.specify/source/speckit_single_spec_input.md`, and any slice-control files mirrored under `.specify/source/`. Run one complete specify -> plan -> tasks -> analyze sequence, then implement only selected approved slice/task IDs.

- Do not create final specs manually.
- Do not implement.
- Do not answer human checkpoint questions silently.
- Do not promote artifacts without judge approval.

SpecKit owns:
- `.specify/memory/constitution.md` updates after approval
- `spec.md` and `checklists/requirements.md`
- `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, and `tasks.md`
- implementation after explicit approval

Judge-led review protocol: `docs/JUDGE_LED_REVIEW_PROTOCOL.md`.

RunSkeptic source:
- authoritative file: `saffih/skeptic/skeptic.md`
- companion question bank: `skeptic-questions.md`
- required flow: `GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`

## Stage rule

If the generated context says:

```text
CONVERSION_READY_TO_APPLY
```

then the next step is conversion of the workspace HLD copy.

Do not rerun `first_run_readonly.sh` yet.

Convert only the workspace `HLD.md` using:

- workspace `HLD.raw.md`
- recorded conversion decisions
- conversion plan
- raw marking plan

After conversion, then run the next read-only flow if the generated context says it is safe.

## Stage rule: SpecKit-ready prework

Before invoking SpecKit, an agent must produce and review:

```bash
bash scripts/hldspec_speckit_ready.sh <workspace>
```

This builds:

- architecture analysis
- compact constitution context
- bottom-up spec list
- readiness review

It does not invoke SpecKit, create final specs, or implement.

## Multi-orchestrator model

HLDspec workspaces support three interchangeable orchestrators: **Claude**, **Codex**, and **Devin**. The orchestrator is the judge — it reads pipeline state, makes approval decisions, and delegates bounded phase execution to junior agents.

All runners use the generated target `AGENTS.md` as the source-of-truth instruction file. Tool-specific files may exist only as launch shims that point back to `AGENTS.md`.

### Orchestrator roles

| Orchestrator | Instruction file | Judge role |
|---|---|---|
| Claude Code | `AGENTS.md` (`CLAUDE.md` shim allowed) | Reads state, approves checkpoints, spawns junior subagents or Codex |
| Codex CLI | `AGENTS.md` | Reads state, approves checkpoints, spawns junior `codex exec` calls |
| Devin | `AGENTS.md` (`.devin/instructions.md` shim allowed) | Reads state, approves checkpoints, creates bounded Devin subtasks |

### Junior agent role

Junior agents handle exactly one phase of one feature. They are cheap and bounded:

- **Tools allowed**: Read, Write, Edit, Bash (workspace-scoped)
- **Tools forbidden**: WebSearch, WebFetch, recursive agent spawning
- **Budget**: 20 tool calls max per invocation
- **Scope**: one feature directory, one SpecKit skill
- **If blocked**: report the blocker and stop — never improvise

Optional tmux sessions are a convenience surface only. HLDspec may render tmux
commands from the session plan so windows are role-named, sessions are easy to
attach to, and pane output is captured under `.hldspec/tmux/`; tmux state never
becomes approval state or source truth.

### Installing orchestrator instructions

After `hldspec_speckit_ready.sh` creates the workspace, install the universal orchestrator instruction file and optional compatibility shims:

```bash
bash scripts/install_orchestrator_instructions.sh \
  --workspace /path/to/workspace \
  --orchestrators claude,codex,devin   # default: all three
```

This renders `templates/orchestrator/` templates with the correct workspace and repo paths.
`AGENTS.md` is always installed; `CLAUDE.md` and `.devin/instructions.md` are
shim files only.

### SpecKit phase delegation

After `SPECKIT_PREWORK_APPROVAL_GATE` is approved, the orchestrator delegates each spec/phase to a junior agent:

| Phase | Assigned agent name | Model tier | Preferred junior | Output file |
|---|---|---|---|---|
| specify | SpecKit Specify Proxy | `MODEL_STRONG` | Claude subagent or `codex exec` | `spec.md` + `checklists/requirements.md` |
| clarify | SpecKit Clarify Proxy | `MODEL_STRONG` | Claude subagent or `codex exec` | clarified `spec.md` / answers log |
| plan | SpecKit Plan Proxy | `MODEL_CRITICAL` | `codex exec` | `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` |
| tasks | SpecKit Tasks Proxy | `MODEL_STRONG` | `codex exec` | `tasks.md` |
| analyze | SpecKit Analyze Reviewer | `MODEL_CRITICAL` | `codex exec` | analysis output |
| implement | SpecKit Implementer | `MODEL_STRONG` or `MODEL_CRITICAL` by blast radius | `codex exec` or Devin | source code (only after tasks phase and approval) |
| merge/history audit | Merge History Auditor | `MODEL_CRITICAL` | judge/orchestrator | `MERGED_DONE` classification |

Always complete specify → clarify when needed → plan → tasks → analyze before implement. The orchestrator reviews each phase output before starting the next.

Model routing rule:
- Weakest sufficient model creates draft artifacts.
- Strongest necessary model promotes artifacts across gates.
- Human-owned architecture, source-of-truth, API, security, data ownership, dependency, split/merge, implementation, and merge/history decisions require `MODEL_CRITICAL` judge review or explicit human approval.

Concrete tier mapping is runner-specific. Preserve the same abstract tiers
across Codex, Claude, and Devin so the workflow does not depend on one vendor:

| Runner | `MODEL_ROUTINE` | `MODEL_DEFAULT` | `MODEL_STRONG` | `MODEL_CRITICAL` |
|---|---|---|---|---|
| Codex | `gpt-5.5 low` | `gpt-5.5 medium` | `gpt-5.5 high` | `gpt-5.5 xhigh` |
| Claude | `Haiku 4.5` | `Sonnet 4.6` | `Sonnet 4.6` | `Opus 4.7` |
| Devin | `SWE 1.6` | `SWE 1.6` under credit pressure; `codex 4.3 code` when available | `Sonnet 4.5` | `Opus 4.6` |

Devin-specific credit rule: prefer complete run cards and few user turns.
`SWE 1.6` may draft, edit, run tests, and perform a second mechanical review,
but it must not approve architecture, constitution, source-of-truth, API, data
ownership, dependency, security, rollout, split/merge, or promotion decisions.

### Codex junior invocation

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C /path/to/workspace \
  "$(cat .agents/skills/speckit-plan/SKILL.md)

STOP_BOUNDARY: Stop after plan.md. Do not create tasks.md or any other file."
```

Key flags:
- `--sandbox workspace-write` — grants file write access within the workspace
- `--skip-git-repo-check` — required when workspace is not a git repo

## Standard concerns (required on every HLDspec run)

These concerns are mandatory and must be visible in generated artifacts before promotion:

1. Design for testability
- Explicit seams (ports/adapters/interfaces)
- Unit/component/integration coverage intent
- Deterministic test controls for time/random/external I/O

2. Staging and non-disruptive validation
- Test/staging environment strategy before user-impacting rollout
- Data isolation/masking expectations
- Rollback and smoke/regression validation path

3. UI testability
- Stable selectors/test ids/accessibility hooks where UI exists
- Critical user journey validation plan
- Explicit UI testing tool path (automation, assertions, evidence)

4. Contract and refactor safety
- Interface contract ownership per boundary
- Source-of-truth and update timing ownership
- Backward compatibility and migration constraints when refactoring

5. Skeptic concern coverage
- RunSkeptic reports must address these concerns explicitly.
- Missing concern evidence is an ACTION/CONFLICT finding, not a silent pass.

## Non-negotiables for junior/limited agents

- Do not bypass checkpoint ownership.
- Do not approve or promote artifacts.
- Do not invent missing source-of-truth, contract, or update-timing values.
- Do not patch generated artifacts as a fix; fix source or generator and rebuild.
- Do not proceed to SpecKit without approved prework gate.

## Known limitations

- Artifact existence does not always imply completeness unless a validator enforces required keys.
- Local static checks cannot guarantee production runtime safety.
- Historical docs in `docs/` may describe prior states; use canonical and current run artifacts first.
