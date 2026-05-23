# HLDspec Implementation TODO

made by AI

Date: 2026-05-23

<!-- HLDSPEC_PROCESS_INTRO_START -->
## Introduction - process and context preservation

This TODO is the working context anchor for HLDspec productization. When context is compacted or a new agent session starts, read this file first, then read:

- `docs/HLDSPEC_USE_CASES_AND_API.md`
- `docs/HLDSPEC_USER_STORIES.md`
- the latest `docs/HLDSPEC_RUNSKEPTIC_*.md` records
- `docs/HLDSPEC_ORCHESTRATION_CONTRACT.md` when present

Working process:

1. Treat the local repo as authoritative. GitHub/remote is the sync target.
2. Start every meaningful product change by reading the actual current `skeptic.md` and applying RunSkeptic in order.
3. Convert broad product goals into testable user stories and acceptance tests before coding larger flow changes.
4. Implement the smallest reversible product layer that closes the current verified gap.
5. Add regression tests at the boundary where downstream behavior can break.
6. Run focused tests, then full unittest discovery when available, then `git diff --check`.
7. Update this TODO with DONE / NEXT / DEFERRED status before committing.
8. Do not rerun a patch script on a dirty tree. If a patch was already applied and the tree is dirty, run verification, update this TODO, then commit the applied changes.

General local patch/sync recipe:

1. `cd /absolute/path/to/repo`
2. `git status --short`
3. `git pull --ff-only`
4. `chmod +x /absolute/path/to/patch.sh`
5. Run the patch with explicit repo path and commit flag, for example:
   ```bash
   PROJECT_REPO=/absolute/path/to/repo \
   PATCH_COMMIT=1 \
   bash /absolute/path/to/patch.sh
   ```
6. Push only after tests pass:
   ```bash
   git push
   ```

Patch scripts should refuse dirty trees unless explicitly designed as repair scripts; apply reversible changes; run focused tests; run full test discovery when available; run `git diff --check`; update the project TODO/status/context file when one exists; commit only when `PATCH_COMMIT=1` or the project-specific equivalent is set; never push unless explicitly requested.

If a patch fails partially, do not rerun blindly. Run `git status --short`, inspect what changed and where it failed, use a repair script designed for the dirty partial state, and verify tests before committing.

Every patch response should include the absolute `cd` command, absolute patch path, exact command block, files changed, tests run, and whether the patch was tested before delivery.

Current productization sequence:

```text
classifier correctness
-> planner enforcement proof
-> formal user stories
-> holistic RunSkeptic review
-> executable use-case/API map
-> prework gate enforcement
-> hldspec_state/status wrapper
-> interview/checkpoint flow
-> bounded SpecKit proxy dry-run
-> real-HLD smoke/readiness
-> Product Manager + Architect + answer packs
-> judge/orchestration promotion gates
-> checkpoint question guide
-> agent-first entrypoint: HLDspec /path/to/HLD.md
```

Context rule:

If future context is short, use this TODO to recover where we are, what is already done, what is intentionally deferred, and what the next safe patch should be. Keep this file updated after every patch.
<!-- HLDSPEC_PROCESS_INTRO_END -->

## Current milestone

Goal: make HLDspec usable through an agent-first flow:

```text
Human says: HLDspec /absolute/path/to/HLD.md
Agent owns the process
Agent uses CLI/tools internally
Human answers only real checkpoint questions
SpecKit is invoked only after judge gates allow it
Implementation remains blocked unless separately approved
```

## Current verified situation

The engine has many internal layers, but the user-facing entrypoint is still missing.

Current real smoke result observed on `/Users/saffi/code/flow/HLD.md`:

```text
workspace: /tmp/hldspec-smoke
stage: CONVERSION_CHECKPOINT
checkpoint: hld_conversion_decisions
status: raw HLD needs conversion decisions before later PM/Architect/SpecKit artifacts can exist
```

Therefore, missing PM/Architect/answer-pack/proxy files in `/tmp/hldspec-smoke/.specify/sync/` are expected until the conversion gate is resolved and first-readonly reaches later stages.

## Done

- DONE: HLD section classifier marks stakeholder, persona, business case, executive summary, assumptions, and milestone sections as context-only.
- DONE: HLD section classifier marks decision log and open conflict sections as governance context.
- DONE: Explicit HLD-SPECS metadata still overrides context-only title classification.
- DONE: Buildable titles such as API/interface/data/system sections remain spec candidates.
- DONE: Focused classifier regression tests cover the false-positive first-feature cases.
- DONE: Plan-level regression test proves context-only sections do not become planned specs and do appear in context_hld_sections.
- DONE: Clean plan quality now reports PASS / KEEP_PLAN instead of FIX / KEEP_PLAN.
- DONE: RunSkeptic stabilization record captures the decision to fix the planner confidence gap before adding new product machinery.
- DONE: Formal user stories and acceptance tests documented in `docs/HLDSPEC_USER_STORIES.md`.
- DONE: Holistic RunSkeptic review documented in `docs/HLDSPEC_RUNSKEPTIC_HOLISTIC_REVIEW.md`.
- DONE: Executable `hld_usecase_api_map` builder added.
- DONE: `.specify/sync/hld_usecase_api_map.json` and `.md` generated by first read-only flow.
- DONE: Use-case/API map includes actors, journeys, system use cases, API/interface surfaces, data/source-of-truth objects, feature candidates, context-only sections, dependencies, non-goals, risks, and open questions.
- DONE: Prework package includes use-case/API case.
- DONE: Prework quality gate can block context-only first feature when map evidence shows the issue.
- DONE: Product alignment RunSkeptic cycles and executable product alignment review added.
- DONE: `hldspec_status` wrapper added.
- DONE: `hldspec_prework` wrapper added.
- DONE: State/continue gates accept PASS / KEEP_PLAN as a green clean plan.
- DONE: `hldspec_interview` wrapper and validated queue answer writer added.
- DONE: Source-HLD update queue is regenerated after conversion answers.
- DONE: Explicit SpecKit prework approval recorder added.
- DONE: Guarded one-phase SpecKit proxy dry-run added.
- DONE: Proxy refuses without prework approval, refuses implementation phase, and refuses missing/blocked/unpromoted answer packs.
- DONE: Real-HLD smoke wrapper and readiness review added.
- DONE: Product Manager pack added for use cases, user stories, acceptance criteria, and product open questions.
- DONE: Architect pack added for API/data/dependency/constitution boundaries and architecture open questions.
- DONE: SpecKit answer pack added from Product Manager and Architect packs.
- DONE: Orchestration contract, junior subagent task packets, judge promotion ledger, and orchestration state builder added.
- DONE: Checkpoint question guide added as a formal read-only process step.
- DONE: Question guide explains current checkpoint questions but does not answer, edit, convert, promote, invoke SpecKit, or implement.
- DONE: Agent-first start prompt/context generator added for the minimal trigger `HLDspec /absolute/path/to/HLD.md`.
- DONE: Minimal trigger UX repaired: default output is now short, with full context kept in generated files.
- DONE: Spec build plan checkpoint answers are now applied back into workspace plan artifacts before continuation.

## Immediate current gate

The current real HLD smoke is blocked at conversion:

```text
CONVERSION_CHECKPOINT -> hld_conversion_decisions
```

Correct next flow:

```text
question guide explains hld_conversion_decision_queue
-> human chooses split/keep answers
-> hldspec_interview records validated answers
-> conversion agent converts /tmp/hldspec-smoke/HLD.raw.md -> /tmp/hldspec-smoke/HLD.md
-> first_run_readonly runs on converted workspace HLD
-> later PM/Architect/answer-pack/orchestration/proxy artifacts are generated
```

Do not inspect PM/Architect/answer-pack/proxy files in the base smoke workspace until conversion has passed.

## Next patch

Run and validate the full agent-first workflow from scratch through conversion decisions, spec-plan split decisions, and the SpecKit prework human-review gate.

Target command:

```bash
cd /Users/saffi/code/HLDspec
bash scripts/hldspec_agent_start.sh /Users/saffi/code/flow/HLD.md --workspace /tmp/hldspec-smoke
```

Expected behavior:

- generate `.specify/sync/hldspec_agent_start_prompt.md`
- preserve `/Users/saffi/code/flow/HLD.md` as read-only
- identify current gate as conversion checkpoint when state exists
- guide the agent to use `hldspec_question_guide.sh`
- stop before conversion until validated human answers are recorded


## Later product wrappers

- TODO: Extend `hldspec_interview.sh` to support `speckit_question_escalation_queue.json` PMQ/ARQ answers if not already supported.
- TODO: Add one-phase-at-a-time real SpecKit execution after explicit approval, only after agent-first entrypoint and promotion gates are stable.
- TODO: Add agent invocation contract artifacts that define allowed inputs, allowed outputs, forbidden actions, and stop conditions.

## Deferred decisions

- DEFERRED: Change unknown section default from SPEC_CANDIDATE to REVIEW_NEEDED. Reason: safer to preserve coverage until use-case/API map is tested on more real HLDs.
- DEFERRED: Auto-promote low-risk Product/Architect/answer packs. Reason: would reintroduce the failure mode “artifact exists means approved.”
- DEFERRED: Real SpecKit execution. Reason: requires agent-first entrypoint, answer-pack readiness, promotion gates, and one-phase dry-run review.
- DEFERRED: Implementation phase. Reason: out of scope until SpecKit specify/clarify/plan/tasks gates are stable.

## Current readiness

- Classifier readiness: high.
- Planner gate readiness: high after plan-level regression passes.
- Use-case/API map readiness: medium; executable and tested, but heuristic.
- Prework package readiness: medium-high.
- Status wrapper readiness: medium-high.
- Interview wrapper readiness: medium; flag-based answer recording is implemented and tested for existing queues.
- Question guide readiness: medium; formal read-only process step exists, but must be smoke-tested on real conversion queues.
- Product/Architect answer-pack readiness: medium; generated and tested, but depends on conversion and first-readonly reaching later stages.
- Orchestration promotion readiness: medium; gates exist, but need full real-HLD smoke after conversion passes.
- SpecKit proxy readiness: medium; guarded dry-run exists, real execution is still deferred.
- Agent-first UX readiness: medium-high; minimal trigger exists and spec-plan checkpoint answers are applied to workspace plan artifacts, but the full real-HLD scratch workflow must still be smoke-tested end to end.

## Rule

Do not add real SpecKit execution until:

```text
converted HLD exists
first_run_readonly passes
question guide/interview flow is verified on real checkpoint questions
Product Manager pack exists and is reviewed
Architect pack exists and is reviewed
answer pack is READY
judge promotion marks required artifacts ACCEPTED
proxy dry-run is DRY_RUN_READY
```

## SpecKit-ready gap closure

DONE: SpecKit-ready prework layer added.

New artifacts:

- `hldspec_architecture_analysis.json/md`
- `speckit_constitution_context.json/md`
- `hldspec_speckit_spec_list.json/md`
- `hldspec_speckit_readiness.json/md`

Rules:

- Constitution is compact shared architecture context plus governance.
- HLD remains the full architecture source of truth.
- Specs are bottom-up capability contracts.
- Tool/state, logic/orchestration, and API/contract layers must be split when independently evolvable.
- No-invention/defer applies to missing metadata, source-of-truth ownership, and update timing.
- This layer does not invoke SpecKit and does not implement.
