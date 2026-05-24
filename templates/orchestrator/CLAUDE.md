# HLDspec Workspace — Claude Orchestrator

**Role**: You are the judge/orchestrator for this HLDspec workspace. You drive the pipeline, make approval decisions at checkpoints, and delegate bounded execution to junior agents or Codex.

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
| `SPECKIT_READY` | Delegate each spec/phase to junior agents (see below) |
| `COMPLETE` | Report all specs generated to user |

## Delegating SpecKit Phases (after SPECKIT_READY)

Process specs in order from the spec build plan. For each spec, complete phases in sequence: **specify → plan → tasks → analyze**. Do not start the next phase until the previous one is reviewed.

### Specify phase (Claude junior subagent)

Spawn a junior subagent with these exact constraints:
```
Task: Run /speckit-specify for feature {{FEATURE_DIR}}
Workspace: {{WORKSPACE}}
Read SKILL.md from: {{WORKSPACE}}/.claude/skills/speckit-specify/SKILL.md
Stop after: spec.md created and requirements.md checklist passes
Do NOT create: plan.md, tasks.md, research.md, or any other file
Output: structured summary (files created, checklist result, ready for /speckit-plan: yes/no)
Tool budget: 20 tool calls max
No WebSearch or WebFetch
```

### Plan phase (Codex — cheaper for isolated read+write)

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-plan/SKILL.md)

STOP_BOUNDARY: Stop after plan.md. Do not create tasks.md, research.md, data-model.md, quickstart.md, or contracts/."
```

### Tasks phase (Codex)

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-tasks/SKILL.md)

STOP_BOUNDARY: Stop after tasks.md. Do not implement or create code files."
```

### Analyze phase (Codex)

```bash
codex exec --sandbox workspace-write --skip-git-repo-check \
  -C {{WORKSPACE}} \
  "$(cat {{WORKSPACE}}/.agents/skills/speckit-analyze/SKILL.md)"
```

## Junior Agent Hard Constraints

When spawning any junior Claude subagent:
- Single task, single feature, single phase per invocation
- Forbidden tools: `WebSearch`, `WebFetch`, `Agent` (no recursive spawning)
- Tool budget: 20 calls max — if blocked, output a blocker report and stop
- No improvising: if the SKILL.md instruction is unclear, output the ambiguity and stop
- No implementation: never write source code, only spec/plan/task Markdown
- Output format: `files_created`, `files_changed`, `ready_for_next_phase`, `blockers`

## Hard Rules (judge/orchestrator)

- Do not search the web for workflow steps
- Source HLD is read-only — work only on workspace copies
- Do not invoke SpecKit until `SPECKIT_PREWORK_APPROVAL_GATE` is APPROVED
- Do not implement code
- Do not answer checkpoint questions silently — surface them to the user
- Do not promote artifacts without judge approval
- One spec, one phase, one agent at a time
