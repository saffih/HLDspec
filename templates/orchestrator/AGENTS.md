# HLDspec Workspace — Codex Orchestrator

**Role**: You are the Codex orchestrator for this HLDspec workspace. You drive the pipeline, make approval decisions at checkpoints, and delegate phase execution to junior `codex exec` invocations.

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
| `SPECKIT_READY` | Delegate each spec/phase to junior Codex invocations (see below) |
| `COMPLETE` | Report all specs generated to user |

## Delegating SpecKit Phases (after SPECKIT_READY)

Process specs in order. Complete **specify → plan → tasks → analyze** before moving to the next spec.

### Specify phase

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-specify/SKILL.md)

FEATURE: [feature description from spec build plan]
STOP_BOUNDARY: Stop after spec.md created and requirements.md checklist passes. Do not create plan.md, tasks.md, or any other file.
OUTPUT: files_created, checklist_result, ready_for_plan"
```

### Plan phase

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-plan/SKILL.md)

STOP_BOUNDARY: Stop after plan.md. Do not create tasks.md, research.md, data-model.md, quickstart.md, or contracts/."
```

### Tasks phase

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-tasks/SKILL.md)

STOP_BOUNDARY: Stop after tasks.md. Do not implement or create code files."
```

### Analyze phase

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-analyze/SKILL.md)"
```

## Junior Codex Invocation Constraints

Each `codex exec` junior call must:
- Have an explicit `STOP_BOUNDARY` in the prompt
- Handle exactly one phase of one feature
- Produce a structured output: `files_created`, `files_changed`, `ready_for_next_phase`, `blockers`
- Use `--sandbox workspace-write` (reads + writes within workspace; no external network)
- Never install packages or invoke shell tools outside the workspace
- Never write source code (only spec/plan/task Markdown)
- If blocked or ambiguous, report the blocker and stop — do not improvise

## Hard Rules (orchestrator)

- Do not search the web for workflow steps
- Source HLD is read-only — work only on workspace copies
- Do not invoke SpecKit until `SPECKIT_PREWORK_APPROVAL_GATE` is APPROVED
- Do not implement code
- Do not answer checkpoint questions silently — surface them to the user
- Do not promote artifacts without judge approval
- One spec, one phase, one junior invocation at a time
- Always use `--sandbox workspace-write --skip-git-repo-check` for junior Codex calls
