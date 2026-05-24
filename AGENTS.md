# Agent bootstrap for this repo

## HLDspec trigger

When a user prompt starts with:

```text
HLDspec /path/to/HLD.md
```

or:

```text
HLDspec /path/to/HLD.md --workspace /path/to/workspace
```

do not guess the process from memory.

Do this first:

```bash
cd /Users/saffi/code/HLDspec
bash scripts/hldspec_agent_start.sh <source-HLD.md> [--workspace <workspace>] --print-context
```

Then follow the generated context exactly.

## Hard rules

- Do not search the web for this workflow.
- Do not search unrelated memory/docs before reading the generated context.
- Treat the source HLD as read-only.
- Work only on workspace copies.
- Invoke SpecKit only via the proxy script after SPECKIT_PREWORK_APPROVAL_GATE is passed and prework is APPROVED.
- Do not create final specs manually.
- Do not implement.
- Do not answer human checkpoint questions silently.
- Do not promote artifacts without judge approval.

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

### Orchestrator roles

| Orchestrator | Instruction file | Judge role |
|---|---|---|
| Claude Code | `CLAUDE.md` | Reads state, approves checkpoints, spawns junior subagents or Codex |
| Codex CLI | `AGENTS.md` | Reads state, approves checkpoints, spawns junior `codex exec` calls |
| Devin | `.devin/instructions.md` | Reads state, approves checkpoints, creates bounded Devin subtasks |

### Junior agent role

Junior agents handle exactly one phase of one feature. They are cheap and bounded:

- **Tools allowed**: Read, Write, Edit, Bash (workspace-scoped)
- **Tools forbidden**: WebSearch, WebFetch, recursive agent spawning
- **Budget**: 20 tool calls max per invocation
- **Scope**: one feature directory, one SpecKit skill
- **If blocked**: report the blocker and stop — never improvise

### Installing orchestrator instructions

After `hldspec_speckit_ready.sh` creates the workspace, install orchestrator instruction files:

```bash
bash scripts/install_orchestrator_instructions.sh \
  --workspace /path/to/workspace \
  --orchestrators claude,codex,devin   # default: all three
```

This renders `templates/orchestrator/` templates with the correct workspace and repo paths.

### SpecKit phase delegation

After `SPECKIT_PREWORK_APPROVAL_GATE` is approved, the orchestrator delegates each spec/phase to a junior agent:

| Phase | Preferred junior | Output file |
|---|---|---|
| specify | Claude subagent or `codex exec` | `spec.md` + `checklists/requirements.md` |
| plan | `codex exec` | `plan.md` |
| tasks | `codex exec` | `tasks.md` |
| analyze | `codex exec` | analysis output |
| implement | `codex exec` or Devin | source code (only after tasks phase) |

Always complete specify → plan → tasks before implement. The orchestrator reviews each phase output before starting the next.

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
