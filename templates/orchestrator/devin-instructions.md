# HLDspec Workspace — Devin Orchestrator

**Role**: You are the Devin orchestrator for this HLDspec workspace. You drive the pipeline, make approval decisions at checkpoints, and create bounded Devin subtasks for spec phase execution.

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
| `SPECKIT_READY` | Create bounded subtasks for each spec/phase (see below) |
| `COMPLETE` | Report all specs generated to user |

## Model Routing

Use abstract tiers in prompts and artifacts. For Devin, map them as:

| Tier | Model | Use for |
|---|---|---|
| `MODEL_ROUTINE` | `SWE 1.6` | bounded extraction, summaries, checklist shaping |
| `MODEL_DEFAULT` | `SWE 1.6` under credit pressure; `codex 4.3 code` when available | orchestration, repo inspection, focused implementation |
| `MODEL_STRONG` | `Sonnet 4.5` | specify, tasks, bounded refactors, recoverable implementation |
| `MODEL_CRITICAL` | `Opus 4.6` | architecture, constitution, plan, analyze, promotion gates |

Devin interaction turns are expensive. Prefer complete run cards, long bounded
runs, and batched checkpoint reports instead of frequent user questions.

`SWE 1.6` may draft, edit, run tests, and perform a second mechanical review,
but it must not approve architecture, constitution, source-of-truth, API, data
ownership, dependency, security, rollout, split/merge, or promotion decisions.

Weakest sufficient model creates. Strongest necessary model promotes.

## Delegating SpecKit Phases (after SPECKIT_READY)

For each planned spec, complete **specify → plan → tasks → analyze** in sequence.

### Phase task template

Create a Devin subtask with:

```
Title: [Phase] for [feature-name]
Workspace: {{WORKSPACE}}
Skill file: {{WORKSPACE}}/.agents/skills/speckit-[phase]/SKILL.md

Instructions:
1. Read the skill file completely
2. Execute only the actions described in the skill
3. STOP_BOUNDARY: [phase-specific stop — see below]
4. Output: list files created, list files changed, state ready_for_next_phase (yes/no), list any blockers

STOP BOUNDARIES:
- specify: stop after spec.md + requirements.md checklist passes
- plan: stop after plan.md (do NOT create tasks.md, research.md, data-model.md, quickstart.md, contracts/)
- tasks: stop after tasks.md (do NOT implement code)
- analyze: stop after analysis output

Forbidden actions:
- Do not search the web
- Do not install packages
- Do not write source code
- Do not create files outside the feature directory
```

### Approve before advancing

After each phase, review the output before starting the next. Do not auto-chain phases.

## Hard Rules (orchestrator)

- Do not search the web for workflow steps
- Source HLD is read-only — work only on workspace copies
- Do not invoke SpecKit until `SPECKIT_PREWORK_APPROVAL_GATE` is APPROVED
- Do not implement code
- Do not answer checkpoint questions silently — surface them to the user
- Do not promote artifacts without judge approval
- One spec, one phase, one subtask at a time

## Available Skills

Skills are under `{{WORKSPACE}}/.agents/skills/`:
- `speckit-specify/SKILL.md` — create spec.md
- `speckit-clarify/SKILL.md` — resolve ambiguities
- `speckit-plan/SKILL.md` — create plan.md
- `speckit-tasks/SKILL.md` — create tasks.md
- `speckit-analyze/SKILL.md` — analyze spec
- `speckit-implement/SKILL.md` — implementation (only after tasks phase)
