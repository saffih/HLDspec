# Agent Instructions for HLDspec

made by AI

This repository contains wrapper tools for turning a High-Level Design document into Spec Kit artifacts and downstream planning or implementation artifacts.

Do not bypass the wrappers unless explicitly instructed.

## Limited agent run card

When the agent has limited context/capacity, it should read this short file first:

```text
docs/LIMITED_AGENT_RUN_CARD.md
```

This run card overrides long-form reading order. It tells the agent the minimum safe workflow, context-budget rules, human-in-loop format, stop points, and first command.

For simulator-style usage, use:

```text
docs/SIMULATOR_AGENT_PROMPT.md
```


## Python runner preference

Shell wrappers should prefer `uv run python` when `uv` is available and fall back to `python3` when it is not.

Use this pattern in bash wrappers:

```bash
if command -v uv >/dev/null 2>&1; then
  PYTHON_RUN=(uv run python)
else
  PYTHON_RUN=(python3)
fi
```

Then call Python as:

```bash
"${PYTHON_RUN[@]}" script.py
```

Do not make `uv` mandatory unless the repo explicitly adopts a `pyproject.toml`/locked environment.


## Real Beskeptic framework contract

HLDspec must treat `saffih/skeptic/skeptic.md` as the authoritative Beskeptic/Skeptic framework.

Cached framework contract:

```text
docs/BESKEPTIC_FRAMEWORK_CACHE.json
docs/BESKEPTIC_FRAMEWORK_CACHE.md
```

Every first-run workspace should include:

```text
.specify/sync/beskeptic_framework_cache.json
.specify/sync/beskeptic_framework_cache.md
```

`beskeptic_cycles` are valid only when they preserve the real Skeptic phase flow:

```text
GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
```

Do not claim "real Beskeptic" from naming alone; the framework source, companion question bank, and phase flow must be present in artifacts.

The framework cache must include both `skeptic.md` and the companion `skeptic-questions.md` domain question bank.



## Source-HLD-affecting feedback

Some checkpoint answers are not process-only. They may affect HLD boundaries, section structure, architecture intent, or source-of-truth content.

HLDspec must generate:

```text
.specify/sync/hld_source_update_queue.json
.specify/sync/hld_source_update_queue.md
```

The judge/orchestrator must distinguish:

- process-only decisions
- source-HLD-affecting decisions
- unclear feedback requiring review

Do not treat an append-only decision log as sufficient when the feedback should change HLD content or structure.

Do not modify the source HLD without explicit human approval.

## HLD decision source-of-truth log

Human checkpoint answers are architecture/process decisions. They must not live only in transient queue JSON.

Whenever a human checkpoint exists or is answered, HLDspec must write:

```text
.specify/sync/hld_decision_log.json
.specify/sync/hld_decision_log.md
.specify/sync/hld_source_decision_appendix.md
```

The source HLD remains the source of truth only after the appendix is explicitly applied.

Applying to the source HLD requires explicit human approval and must use:

```bash
scripts/apply_hld_decision_log_to_source.py <source-HLD.md> <hld_source_decision_appendix.md> --approved
```

The source appendix must be marker-bounded:

```text
<!-- HLDSPEC-DECISION-LOG:BEGIN -->
...
<!-- HLDSPEC-DECISION-LOG:END -->
```

Do not lose human feedback in workspace-only artifacts.


## Checkpoint continuation responsibility

When HLDspec generates a human checkpoint, the human only supplies the decision answers.

The judge/orchestrator must know the continuation process without being told again:

1. update the relevant checkpoint JSON artifact with the human answers
2. rerun the same `scripts/hldspec_run.sh <path-to-HLD.md>` command
3. continue only to the next safe checkpoint
4. report what changed and what checkpoint was reached

For conversion checkpoints, the relevant JSON artifact is:

```text
.hldspec-first-run/.specify/sync/hld_conversion_decision_queue.json
```

Do not ask the human what command to run after a checkpoint.


## State-discovery invocation

The human should be able to point the judge/orchestrator at the project with a minimal invocation:

```text
HLDspec
```

or, if the HLD path is needed:

```text
HLDspec ./Flow-System-HLD.md
```

This means the judge/orchestrator must discover the current HLDspec state and lead the process.

The judge/orchestrator must not ask the human what command to run, what JSON to edit, or whether to generically continue.

Required state-discovery order:

1. Identify the project root and source HLD.
2. Locate `.hldspec-first-run`.
3. Read `~/code/HLDspec/AGENTS.md`.
4. Read `~/code/HLDspec/docs/HLD_AGENT_CATCHUP.md` if present.
5. Inspect checkpoint artifacts in this order:
   - `.hldspec-first-run/.specify/sync/hld_conversion_decision_queue.md`
   - `.hldspec-first-run/firstrun/.specify/sync/spec_build_plan_decision_queue.md`
   - `.hldspec-first-run/firstrun/.specify/sync/hld_source_update_queue.md`
   - `.hldspec-first-run/firstrun/.specify/sync/target_spec_work_order.md`
   - `.hldspec-first-run/firstrun/.specify/sync/spec_branch_queue.md`
   - `.hldspec-first-run/firstrun/.specify/sync/spec_build_plan_review.md`
6. If a checkpoint contains `human_decision: TBD`, ask only those listed questions.
7. After the human answers, update the relevant JSON artifact, rerun the same HLDspec command, and continue to the next safe checkpoint.
8. If no checkpoint exists, run:

```bash
~/code/HLDspec/scripts/hldspec_run.sh <source-HLD.md>
```

The human owns decisions. The judge/orchestrator owns state discovery, command execution, queue updates, continuation, and reporting.

Minimal acceptable human interaction:

```text
HLDspec
```

Then, only checkpoint answers such as:

```text
Q-001: SPLIT_AS_PROPOSED
Q-002: SPLIT_AS_PROPOSED
Q-003: KEEP_AS_ONE
```


## Default HLDspec invocation contract

Every project-level HLDspec invocation is handled as a judge/orchestrator run by default.

The human should be able to invoke HLDspec with a short prompt such as:

```text
HLDspec ./Flow-System-HLD.md
```

The external coding agent must then read:

```text
docs/HLD_AGENT_CATCHUP.md
```

and run:

```bash
scripts/hldspec_run.sh <path-to-HLD.md>
```

The agent owns orchestration, checkpoint reporting, bounded context, and subagent management if needed. The human owns generated decision checkpoints.


## Single-command project runner

For project-level use, prefer the single command:

```bash
scripts/hldspec_run.sh <path-to-HLD.md> [workspace]
```

This command continues HLDspec to the next safe checkpoint.

It may:
- run the read-only first run
- show the generated human decision queue
- apply already answered conversion decisions to the working copy
- rerun first-readonly on the converted working copy
- report whether target-spec generation is allowed

It must not:
- modify the source HLD
- answer human checkpoint questions
- run downstream analysis
- create tasks
- run implementation work

The judge/orchestrator should run this command and report its checkpoint output to the human.


## Simple project entrypoint

When the human asks an agent to run HLDspec from a project repository, the agent should read:

```text
docs/PROJECT_AGENT_PROMPT.md
```

The simple wrapper command is:

```bash
scripts/project_first_run.sh <path-to-HLD.md> [workspace]
```

The wrapper runs the read-only first-run workflow and prints the current checkpoint. It does not call an agent, edit the source HLD, create specs, create target constitution, or run downstream work.


## Core rule

`HLD.md` is the canonical source of truth.

Generated files under `.specify/sync/` are derived artifacts and may be regenerated.

Use the scripts in this repo to validate, sync, and process HLD-driven work.

## Main tools

Use these wrappers:

```bash
./hld_spec_sync.py
./hld_spec_downstream.py
```

Do not manually create or update specs, plans, tasks, or downstream artifacts when the wrapper can do it.

## HLD creation or improvement

When asked to create a new HLD, improve an HLD, or make an HLD workable for HLDspec:

1. Read `HLD_GENERATION.md`.
2. Use the format from `HLD_FORMAT.md`.
3. Keep one canonical `HLD.md`.
4. Use stable section headings:

```md
## HLD-003 - Section Title
```

5. Add required metadata under each major section:

```md
HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 001,002
HLD-RESOURCES: hld_spec_sync.py,.specify/memory/constitution.md,specs/*/spec.md
HLD-VERIFY: related specs preserve HLD anchors; feature graph includes dependencies
```

6. Use inline section references:

```md
REF HLD-002
DEPENDS REF HLD-002
BLOCKED_BY REF HLD-009
CONFLICTS_WITH REF HLD-011
```

7. Do not renumber existing HLD IDs unless explicitly requested.
8. Mark unknown mappings as `TBD`; do not invent them.
9. Mark unresolved design conflicts as `CONFLICT` or `CONFLICTS_WITH REF HLD-xxx`.



## Applying approved HLD conversion decisions

After the human checkpoint is answered, use:

```bash
scripts/apply_hld_conversion_decisions.py <working-HLD.md> <hld_conversion_decision_queue.json>
```

Rules:

- Run only on the working HLD copy, never on the source HLD.
- Refuse to run while any blocking question has `human_decision: TBD`.
- Preserve all original content under inserted HLD anchors.
- Add metadata only; do not summarize, delete, or reinterpret architecture.
- Rerun `scripts/first_run_readonly.sh` after conversion.


## Spec-boundary classification rule

Do not assume one HLD section equals one target spec.

After an HLD map exists, classify sections before spec planning:

```bash
scripts/classify_hld_sections.py HLD.md <workspace>
```

Generated artifacts:

```text
.specify/sync/hld_section_classification.json
.specify/sync/hld_section_classification.md
```

Sections classified as `HLD_CONTEXT_ONLY`, `GOVERNANCE`, `RUNBOOK`, `REFERENCE`, `VERIFICATION_CONTEXT`, `APPENDIX`, or merge/context sections are preserved as HLD anchors but must not become standalone planned specs by default.

If plan quality worsens after splitting, stop and consolidate HLD-SPECS mapping instead of splitting more.


## Existing huge HLD or raw HLD not in HLDspec format

Use this workflow when the user provides a large existing HLD that is not yet in HLDspec format, or asks to make an HLD workable for spec sync.

The goal is to make the HLD parseable and safe for bounded processing without destroying the original document.

### Case

Use this workflow when:

- the HLD is very large
- the HLD does not use `## HLD-xxx - Title` headings
- the HLD does not contain `HLD-*` metadata lines
- the HLD has implicit cross-section relationships
- the user asks to convert, prepare, normalize, or make the HLD usable by HLDspec
- the user wants to update specs from an existing HLD but `--hld-map-only` fails

### Required solution

Do not run full HLD-to-spec sync on an unformatted huge HLD.

Do not blindly rewrite the whole HLD.

Do this instead:

1. Preserve the original HLD.

```bash
cp <original-hld-file>.md HLD.raw.md
cp HLD.raw.md HLD.md
```

2. If `--hld-format-report` exists, run it first.

```bash
./hld_spec_sync.py --hld HLD.md --hld-format-report
```

Review:

```text
logs/hld_spec_sync/<timestamp>/hld_format_report.md
logs/hld_spec_sync/<timestamp>/suggested_hld_sections.json
```

This report is read-only. It should not modify `HLD.md`, call an agent, or write specs.

3. If `--hld-format-report` does not exist yet, use the grep fallback.

```bash
grep -nE '^(#|##|###) ' HLD.raw.md > /tmp/hld_headings.txt
cat /tmp/hld_headings.txt
```

4. Identify major sections only.

Do not tag every subsection. Use `HLD-xxx` IDs only for major design areas, such as:

- executive summary
- governance/source of truth
- architecture
- processing flow
- interfaces/contracts
- data/state
- failure modes/recovery
- testing/verification
- risks/open questions

5. Convert accepted major sections into HLDspec format.

```md
## HLD-003 - Section Title

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

6. Use `TBD` instead of inventing mappings.

Unknown spec IDs, owners, resources, or source-of-truth decisions must be marked as `TBD`.

Do not guess.

7. Add inline references between sections where relationships are known.

```md
This section DEPENDS REF HLD-002 because governance defines what may be generated.

This section REF HLD-006 for rollback behavior.

This approach CONFLICTS_WITH REF HLD-011 because both define different ownership rules.
```

8. Validate the formatted HLD.

```bash
./hld_spec_sync.py --hld HLD.md --hld-map-only
```

Review:

```text
.specify/sync/hld_index.md
.specify/sync/hld_ref_map.json
.specify/sync/hld_sections/
```

Do not continue if map validation fails.

9. Rerun the current primary first-run workflow on the converted HLD.

```bash
bash scripts/first_run_readonly.sh HLD.md /tmp/hldspec-first-run --force
```

Review:

```text
/tmp/hldspec-first-run/.specify/sync/spec_build_plan_review.md
/tmp/hldspec-first-run/.specify/sync/spec_build_plan.md
/tmp/hldspec-first-run/.specify/sync/spec_build_plan.json
```

10. Stop on plan-quality blockers.

Stop and ask the human before continuing when the review reports:

```text
DECOMPOSE
CONFLICT
SPLIT_PLANNED_SPEC
RESOLVE_CONFLICT
```

Do not treat a blocked or decomposed plan as safe.

11. Use legacy `--target-hld` only when explicitly requested.

The `--target-hld` flow is a controlled legacy workflow. It is not the default continuation after raw-HLD conversion.

Before using it, the judge/orchestrator must explain why the first-run Spec Build Plan Review is insufficient for the current task and must get explicit human approval.

12. Do not create downstream artifacts from raw-HLD assumptions.

Downstream planning, tasks, research, data-model, quickstart, implementation, or target-constitution work must wait until the relevant plan/spec boundary is reviewed and accepted.

### Do not

- Do not overwrite or delete `HLD.raw.md`.
- Do not tag every small subsection.
- Do not invent spec IDs, owners, resources, or source-of-truth decisions.
- Do not manually split the HLD into many canonical source files by default.
- Do not use legacy `--target-hld` as the default continuation after raw-HLD conversion.
- Do not continue if `--hld-map-only` reports validation errors.
- Do not use auto-conversion or auto-chunk execution without first reviewing a report or chunk plan.

### Success criteria

The HLD is ready for HLDspec processing when:

- `HLD.raw.md` preserves the original.
- `HLD.md` has stable `## HLD-xxx - Title` major sections.
- each major section has required `HLD-*` metadata.
- cross-section relationships use `REF HLD-xxx`.
- `./hld_spec_sync.py --hld HLD.md --hld-map-only` passes.
- `hld_index.md` gives a useful overview of the design.
- `first_run_readonly.sh` on the converted HLD produces a Spec Build Plan Review.
- blocked/decomposed/conflicting plan results are escalated to the human instead of continuing silently.


## HLDspec operating rules vs target Spec Kit Constitution

Do not create `.specify/memory/constitution.md` inside this HLDspec repo as the repo's own constitution.

Use these sources instead:

1. `AGENTS.md` = operational rules for agents working in this repo.
2. `TERMINOLOGY.md` = canonical names.
3. `HLD_FORMAT.md` = HLD input contract.
4. `HLD_GENERATION.md` = HLD authoring guidance.
5. `README.md` = user-facing usage.

The path `.specify/memory/constitution.md` means the **target Spec Kit Constitution** in the workspace being processed by HLDspec.

`hld_spec_sync.py` must handle the target Spec Kit Constitution as an output artifact:

- if the target constitution exists, read it and update it safely when the HLD requires changes
- if the target constitution does not exist, create it from the HLD and Spec Build Plan
- if the HLD and current constitution conflict, report a conflict instead of guessing
- never assume the target constitution already exists
- never treat HLDspec repo operating rules as the target workspace constitution

Future `--plan-specs` output should include a constitution action:

```json
{
  "constitution_action": "create|update|no_change|conflict",
  "required_constitution_rules": [],
  "conflicts": []
}
```

## Beskeptic Cycles and Key Aspects

Use the real Skeptic Framework from `https://github.com/saffih/skeptic/blob/main/skeptic.md`.

A **Beskeptic Cycle** is HLDspec's operational use of the real Skeptic flow on one workflow step and selected Key Aspects.

Do not invent a replacement framework.

Real Skeptic flow:

```text
GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN
```

Top-level Skeptic decisions:

- `FIX`
- `DECOMPOSE`
- `CONFLICT`

Final outcomes:

- `HANDLED`
- `CONFLICT`

Read-only Razor diagnostics may use:

- `PASS`
- `ACTION`
- `CONFLICT`

Spec-specific labels are recommendations under a Skeptic decision, not replacements for Skeptic decisions:

- `KEEP_SPEC`
- `FIX_SPEC`
- `SPLIT_SPEC`
- `MERGE_SPEC`
- `DEFER_SPEC`

### Key Aspects

A **Key Aspect** is the specific concern a Beskeptic Cycle is aimed at.

Core:

- `scope_done`
- `source_of_truth`
- `ownership`
- `testability`
- `user_decision`

HLD:

- `hld_structure`
- `hld_metadata`
- `hld_refs`
- `bounded_context`
- `resume_invalidation`

Spec:

- `spec_boundary`
- `spec_decomposition`
- `bottom_up_order`
- `coverage`
- `feature_graph`

Integration and API:

- `integration`
- `api_contract`
- `producer_consumer`
- `dependency_order`
- `data_state_ownership`

Runtime and resource:

- `performance`
- `memory`
- `latency`
- `scalability`
- `reliability`
- `failure_recovery`

Execution safety:

- `staged_write_safety`
- `reversibility`
- `blast_radius`
- `verification_path`

### Required Key Aspects by workflow step

Format Report:

- `hld_structure`
- `source_of_truth`
- `scope_done`
- `user_decision`

HLD Map Validation:

- `hld_metadata`
- `hld_refs`
- `source_of_truth`
- `testability`

Spec Build Plan:

- `spec_boundary`
- `spec_decomposition`
- `bottom_up_order`
- `source_of_truth`
- `dependency_order`
- `api_contract`
- `integration`
- `coverage`
- `performance`
- `memory`
- `user_decision`

Target Spec Prompt:

- `bounded_context`
- `source_of_truth`
- `hld_refs`
- `dependency_order`
- `coverage`
- `integration`
- `api_contract`
- `performance`
- `memory`

Target Spec Generation:

- `spec_boundary`
- `coverage`
- `integration`
- `api_contract`
- `staged_write_safety`
- `testability`
- `performance`
- `memory`

Coverage Gate:

- `coverage`
- `hld_refs`
- `feature_graph`
- `source_of_truth`

Integration Gate:

- `integration`
- `api_contract`
- `producer_consumer`
- `dependency_order`
- `data_state_ownership`
- `feature_graph`
- `performance`
- `memory`
- `reliability`
- `failure_recovery`
- `user_decision`

Downstream Planning and Tasks:

- `coverage`
- `integration`
- `api_contract`
- `bottom_up_order`
- `testability`
- `dependency_order`

Implementation:

- `scope_done`
- `reversibility`
- `testability`
- `integration`
- `staged_write_safety`
- `performance`
- `memory`
- `reliability`
- `blast_radius`
- `user_decision`

Resume:

- `resume_invalidation`
- `bounded_context`
- `hld_refs`
- `source_of_truth`

### User Escalation format

If evidence cannot resolve a conflict, ask the user with:

```text
Conflict:
<short issue>

Key Aspect:
<canonical key aspect>

Why it matters:
<what becomes unsafe or incorrect>

Option A:
<thesis and tradeoff>

Option B:
<antithesis and tradeoff>

Evidence checked:
<files/artifacts checked>

Decision needed:
<specific question for the user>
```

Do not guess unresolved source-of-truth, ownership, API/interface, dependency, performance/memory, coverage, or integration decisions.


## Target-spec context rule

A Target Spec must be designed from the Spec Build Plan plus explicitly selected full HLD source evidence.

Correct model:

```text
HLD Sections
-> HLD Map
-> Spec Build Plan
-> planned spec references related HLD Sections
-> target-spec context selects those full related HLD Sections
-> one focused Target Spec
```

Do not use this wrong model:

```text
one HLD Section -> one Spec
```

Do not use this wrong model either:

```text
Section Card or summary -> Spec
```

Section Cards, if introduced later, are routing/context-control aids only. They help decide what full source evidence to fetch. They do not replace the full HLD Section text.

When target-spec support exists, a target-spec prompt must include:

- the relevant Spec Build Plan entry
- the full text of explicitly related HLD Sections
- required refs from those sections
- relevant normal refs when they affect the target spec
- related API/interface sections when applicable
- related data/state sections when applicable
- related performance/memory sections when applicable
- related reliability/failure-recovery sections when applicable
- current target Spec Kit Constitution context when applicable
- existing related specs only when needed and bounded

A target-spec prompt must not include:

- the whole HLD by default
- all existing specs by default
- Section Cards alone as source evidence
- one arbitrary HLD section without its required and relevant related sections

Beskeptic check for target-spec context:

- `source_of_truth`: Is the full HLD evidence present?
- `bounded_context`: Is irrelevant bulk excluded?
- `spec_boundary`: Does the planned spec own one capability?
- `hld_refs`: Were required refs and relevant normal refs included?
- `api_contract`: Are API/interface sections included when needed?
- `data_state_ownership`: Are data/state sections included when needed?
- `performance` / `memory`: Are resource constraints included when relevant?
- `reliability` / `failure_recovery`: Are failure sections included when relevant?

If a planned spec needs sections that are missing, the target-spec run must stop with `CONFLICT` instead of guessing.


## Chunked judge/subagent protocol

Use the simple chunked judge/subagent model for large HLD work.

The main agent is the **judge/orchestrator**. It owns workflow quality, subagent briefing, context discipline, output review, final synthesis, and escalation.

Subagents are **bounded workers**. They do not own final decisions.

The human owns unresolved decisions.

Default context protection is:

```text
proper chunks
+ bounded subagent briefs
+ judge/orchestrator review
+ human-in-loop stop points
```

Local scripts may read whole files. Agents and subagents should not load or paste the whole HLD into model context by default.

Chunking defaults:

- normal chunk: one major HLD section
- small-section batch: 3-5 small major sections
- large section: process alone
- very large section: inspect internal headings first before editing or splitting

The judge/orchestrator should keep only a compact running summary:

```text
Sections completed
Open uncertainties
Conflicts
Decisions needed
Potential splits
Next chunk
```

Every subagent brief must include role, task, chunk, relevant context, allowed files/commands, forbidden actions, context rule, stop conditions, required output, and evidence required.

Every subagent output must include what was inspected, what changed if anything, findings, evidence, uncertainty, risks, recommended action, files changed, and whether human decision is needed.

See `docs/CHUNKED_AGENT_PROTOCOL.md`.


## Downstream context guard

`hld_spec_downstream.py` must not build unbounded downstream prompts by default.

If `--use-hld-map` is not used and `--max-hld-chars` is `0`, the run must stop unless `--allow-full-hld-context` is provided.

Preferred safe modes:

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-007 --phase analyze --prompt-only
./hld_spec_downstream.py --hld HLD.md --max-hld-chars 30000 --phase analyze --prompt-only
```

Use `--allow-full-hld-context` only with explicit human approval.


## Context budget protocol

Large HLDs must be handled as a context-budget problem.

Local scripts may read whole files. Agent/model context must be bounded.

Do not paste or load the whole HLD into agent context by default.

Use local tools for bounded inspection:

```bash
wc -l HLD.md
grep -nE '^(#|##|###) ' HLD.md
rg -n 'HLD-|REF HLD-|CONFLICTS_WITH|DEPENDS REF' HLD.md
sed -n '120,220p' HLD.md
awk '/^## HLD-/{print NR ":" $0}' HLD.md
```

`grep`, `rg`, `sed`, `awk`, `wc`, `head`, and `tail` are acceptable when their output is bounded and summarized.

For raw HLD conversion:

- preserve `HLD.raw.md`
- edit only the working `HLD.md`
- convert in bounded batches of 3-5 major sections
- inspect very large candidate sections before splitting
- do not rewrite the whole HLD in one hidden pass
- do not invent refs, owners, resources, or spec mappings
- use `HLD-SPECS: TBD` unless certain
- after each batch, report changed sections, metadata chosen, refs added, uncertain fields, and a diff summary
- let the human steer before continuing when interpretation is involved

For future target-spec work, use a bounded target-spec context package. Do not use whole-HLD, all-specs, or all-logs context by default.

See `docs/CONTEXT_BUDGET.md`.


## External project agent communication protocol

When an agent is invoked from another project directory and told to use this HLDspec repository, the agent must keep the human in the loop throughout the work.

This is a communication and control rule, not a read-only-only rule.

Before each major step, state:

```text
What I see:
<observable state>

What it means:
<interpretation and uncertainty>

What I plan to do:
<next action>

Command or edit:
<exact command or file edit, if any>

Expected result:
<what should happen>

Human decision needed:
<yes/no and why>
```

After each major step, state:

```text
What happened:
<result>

Files created or changed:
<paths>

What it means:
<interpretation>

Next decision:
<continue / stop / ask user / fix input / rerun>
```

Stop and ask for human decision before actions that:

- create or modify specs
- create or modify `.specify/memory/constitution.md`
- create downstream plan/tasks/research/data-model/quickstart files
- modify implementation files
- choose between unresolved architecture options
- decide source-of-truth, ownership, API contract, data/state ownership, performance/memory, or failure/recovery behavior
- accept a `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT` result as safe to continue

For safe diagnostic commands, the agent may run the command after explaining the purpose and expected output. The agent must still report the result and let the human steer.

The human may interrupt, correct, or redirect after any update. Do not continue silently through long chains of actions.


## Standard workflow

HLDspec currently has three workflow levels:

1. **Current primary read-only workflow**: uses `scripts/first_run_readonly.sh` to run HLD format report, HLD map, Spec Build Plan, Plan Quality Gate, and Spec Build Plan Review.
2. **Current controlled legacy workflow**: uses `--target-hld` to process one bounded HLD section at a time. Use only when explicitly needed and after reviewing the plan/gate output.
3. **Intended bottom-up generation workflow**: will use `--target-spec`, Coverage Gate, and Integration Gate after the Spec Build Plan is clean or explicitly accepted.

Do not confuse the three.

The current primary workflow is read-only and safe for first real HLD runs. The controlled legacy workflow is still section-driven. The intended generation workflow is capability/spec-driven.

### Current primary read-only workflow

The first-run wrapper must self-detect HLD readiness. It first runs the HLD format report. If the input has no HLDspec markers, it must stop before HLD map / Spec Build Plan and write `HLD_CONVERSION_PROMPT.md` for conversion. Do not require the user to know in advance whether an HLD is raw or ready.

Use this for the first real run on a project HLD:

```bash
bash scripts/first_run_readonly.sh /path/to/HLD.md
```

This produces:

```text
logs/hld_spec_sync/<timestamp>/hld_format_report.md
.specify/sync/hld_index.md
.specify/sync/spec_build_plan.md
.specify/sync/spec_build_plan_review.md
.specify/sync/spec_build_plan.json
```

It must not call an agent, create specs, or create the target Spec Kit Constitution.

Review `spec_build_plan_review.md` before any generation or downstream step.

Run Beskeptic Cycles on these Key Aspects:

- `hld_structure`
- `hld_metadata`
- `spec_boundary`
- `spec_decomposition`
- `bottom_up_order`
- `api_contract`
- `coverage`
- `integration`
- `performance`
- `memory`
- `user_decision`

### Current controlled legacy target-HLD workflow

Use this only when explicitly needed for bounded legacy sync or controlled comparison.

Do not use it as the default first run now that `--plan-specs` and the first-run workflow exist.


#### 1. Validate HLD structure

```bash
./hld_spec_sync.py --hld HLD.md --hld-map-only
```

Review:

```text
.specify/sync/hld_index.md
.specify/sync/hld_ref_map.json
.specify/sync/hld_sections/<section-id>.md
```

Do not continue if the HLD map is invalid.

Run Beskeptic Cycles on these Key Aspects:

- `hld_metadata`
- `hld_refs`
- `source_of_truth`
- `testability`

#### 2. Review bounded HLD-to-spec prompt

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --prompt-only
```

Review:

```text
logs/hld_spec_sync/<timestamp>/context_selection.json
logs/hld_spec_sync/<timestamp>/prompt.md
```

Confirm the prompt uses bounded HLD context and does not load the full HLD unnecessarily.

Run Beskeptic Cycles on these Key Aspects:

- `bounded_context`
- `source_of_truth`
- `hld_refs`
- `coverage`
- `integration`
- `api_contract`
- `performance`
- `memory`

#### 3. Run bounded HLD-to-spec sync

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003
```

Review:

```text
.specify/sync/staged/<run-id>/proposed_writes.md
logs/hld_spec_sync/<timestamp>/run_summary.json
specs/<NNN-feature-slug>/spec.md
.specify/sync/spec_index.json
.specify/sync/feature_graph.json
```

Run Beskeptic Cycles on these Key Aspects:

- `spec_boundary`
- `coverage`
- `integration`
- `api_contract`
- `staged_write_safety`
- `testability`
- `performance`
- `memory`

If the run creates a monolithic spec, mixes responsibilities, misses API contracts, or fails to map HLD anchors, classify the issue as `DECOMPOSE` or `CONFLICT` before continuing.

#### 4. Review spec-to-downstream prompt

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan --prompt-only
```

Review:

```text
logs/hld_spec_downstream/<timestamp>/context_selection.json
logs/hld_spec_downstream/<timestamp>/prompt.md
```

Run Beskeptic Cycles on these Key Aspects:

- `coverage`
- `integration`
- `api_contract`
- `bottom_up_order`
- `testability`
- `dependency_order`

#### 5. Run downstream planning

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan
```

Review:

```text
.specify/sync/downstream/gap_closure_plan.md
specs/<NNN-feature-slug>/plan.md
specs/<NNN-feature-slug>/research.md
specs/<NNN-feature-slug>/data-model.md
specs/<NNN-feature-slug>/quickstart.md
logs/hld_spec_downstream/<timestamp>/run_summary.json
```

Do not proceed downstream if source specs are missing coverage, have unresolved integration gaps, or lack required API/interface contracts.

### Intended bottom-up generation workflow

This is the target architecture after the read-only plan is reviewed. `--plan-specs` exists now. `--target-spec`, `--coverage-check`, and `--integration-check` are not yet implemented and must not be treated as available.

#### 1. Generate a Format Report when the HLD is raw or huge

```bash
./hld_spec_sync.py --hld HLD.md --hld-format-report
```

Review:

```text
logs/hld_spec_sync/<timestamp>/hld_format_report.md
logs/hld_spec_sync/<timestamp>/suggested_hld_sections.json
```

#### 2. Validate the HLD Map

```bash
./hld_spec_sync.py --hld HLD.md --hld-map-only
```

#### 3. Create or refresh the Spec Build Plan

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --plan-specs
```

For first real runs, prefer the wrapper:

```bash
bash scripts/first_run_readonly.sh /path/to/HLD.md
```

Expected outputs:

```text
.specify/sync/spec_build_plan.md
.specify/sync/spec_build_plan.json
```

The Spec Build Plan must include:

```text
constitution_action: create|update|no_change|conflict
planned specs
spec layers
source HLD Sections
dependency order
API/interface expectations
coverage expectations
integration expectations
performance/memory concerns when relevant
conflicts and user decisions needed
```

Run Beskeptic Cycles on these Key Aspects:

- `spec_boundary`
- `spec_decomposition`
- `bottom_up_order`
- `source_of_truth`
- `dependency_order`
- `api_contract`
- `integration`
- `coverage`
- `performance`
- `memory`
- `user_decision`


Review `spec_build_plan_review.md` before continuing. If the review says `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT`, stop and fix the HLD/spec mapping or ask the user for a decision.

#### 4. Future: review one Target Spec prompt

Not implemented yet. Do not run this command until code and tests support `--target-spec`.

Future command shape:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-spec 001 --prompt-only
```

When implemented, review that the prompt uses the Spec Build Plan and includes:

```text
source HLD Sections
required refs
relevant normal refs
dependency specs
target Spec Kit Constitution context
API/interface expectations
performance/memory expectations
coverage expectations
integration expectations
```

#### 5. Future: create or update one Target Spec

Not implemented yet. Do not run this command until code and tests support `--target-spec`.

Future command shape:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-spec 001
```

When implemented, only the selected Target Spec and required sync metadata should change.

#### 6. Future: run Coverage Gate

Not implemented yet. Do not run this command until code and tests support `--coverage-check`.

Future command shape:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --coverage-check --target-spec 001
```

Expected future outputs:

```text
.specify/sync/coverage_matrix.json
.specify/sync/coverage_report.md
```

Do not continue if HLD coverage is partial, stale, duplicated, wrong, or unresolved.

#### 7. Future: run Integration Gate

Not implemented yet. Do not run this command until code and tests support `--integration-check`.

Future command shape:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --integration-check --target-spec 001
```

Expected future outputs:

```text
.specify/sync/integration_matrix.json
.specify/sync/integration_report.md
```

Do not continue if API contracts, producer/consumer relationships, data/state ownership, dependency edges, performance, memory, or reliability expectations are unresolved.

#### 8. Future: continue downstream only after Coverage Gate and Integration Gate

Not implemented yet. Do not run target-spec downstream commands until `--target-spec`, Coverage Gate, and Integration Gate are implemented and tested.

Future command shape:

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-spec 001 --phase plan --prompt-only
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-spec 001 --phase plan
```

### Required distinction

Use `--target-hld` for the current supported bounded-section workflow.

Use `--target-spec` only after the Spec Build Plan exists and the command is implemented.

Do not pretend the intended bottom-up commands exist until code and tests support them.


## Resume behavior

Sync map-aware target runs support:

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --resume
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --restart-map-run
```

Downstream resume is not currently the default workflow unless implemented and documented.

For downstream, rerun the explicit target and phase:

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan
```

## Safety rules

Do not directly edit these generated artifacts unless explicitly asked:

```text
.specify/sync/*
.specify/sync/downstream/*
specs/*/plan.md
specs/*/tasks.md
specs/*/research.md
specs/*/data-model.md
specs/*/quickstart.md
```

Prefer wrapper commands that generate or update them.

Do not write implementation files unless the user explicitly asks and the downstream command uses:

```bash
--allow-implementation --implementation-root <path>
```

Do not remove or rename HLD sections, spec directories, or generated metadata unless explicitly requested.

## Protected paths

Do not write to:

```text
.git/
.agents/
.codex/
logs/
```

Do not modify CI/CD, production config, or implementation code unless explicitly requested.

## Validation commands

Before finalizing script changes, run:

```bash
python3 -m py_compile hld_spec_sync.py hld_spec_downstream.py hld_map.py
PYTHONPYCACHEPREFIX=/private/tmp/codex_pycache python3 -m unittest discover -s tests -v
```

For docs-only changes, at minimum verify links and examples manually.

## Expected agent behavior

When asked to "create an HLD":

1. Use `HLD_GENERATION.md`.
2. Produce or update `HLD.md`.
3. Validate with `--hld-map-only`.

When asked to "make an HLD workable":

1. Convert it to the format in `HLD_FORMAT.md`.
2. Add stable `HLD-xxx` headings.
3. Add required `HLD-*` metadata.
4. Add inline `REF HLD-xxx` relationships.
5. Run `--hld-map-only`.

When asked to "update specs from HLD":

Current primary read-only path:

1. Run `bash scripts/first_run_readonly.sh /path/to/HLD.md`.
2. Review `spec_build_plan_review.md`.
3. If the review says `DECOMPOSE`, `CONFLICT`, `SPLIT_PLANNED_SPEC`, or `RESOLVE_CONFLICT`, stop and fix the HLD/spec mapping or ask the user for a decision.
4. Do not generate specs from the plan until the plan is clean or explicitly accepted.

Current controlled legacy path, only when explicitly requested:

1. Validate the HLD map.
2. Run sync prompt-only first with `--use-hld-map --target-hld`.
3. Review `context_selection.json` and `prompt.md`.
4. Run sync for the target HLD section.
5. Beskeptic-check spec boundary, coverage, integration, API contract, performance, and memory concerns.

Future bottom-up generation path after `--target-spec`, Coverage Gate, and Integration Gate exist:

1. Generate and review the Spec Build Plan.
2. Select one Target Spec from the accepted plan.
3. Run target-spec prompt-only.
4. Create/update that one Target Spec.
5. Run Coverage Gate.
6. Run Integration Gate.


When asked to "catch up downstream artifacts for the next feature":

Current controlled legacy path, only when explicitly requested:

1. Identify the target HLD section.
2. Validate the HLD map.
3. Run sync if specs are stale.
4. Run downstream prompt-only.
5. Run downstream phase `plan`, `tasks`, or `all` as requested.

Current primary read-only path:

1. Run or review the Spec Build Plan Review.
2. If the relevant spec boundary, API contract, coverage, or integration dependency is unresolved, stop.
3. Do not create downstream artifacts from raw HLD assumptions.

Future bottom-up path after `--target-spec`, Coverage Gate, and Integration Gate exist:

1. Identify the Target Spec from the accepted Spec Build Plan.
2. Confirm Coverage Gate is clean or explicitly accepted.
3. Confirm Integration Gate is clean or explicitly accepted.
4. Run downstream prompt-only for the Target Spec.
5. Run downstream phase `plan`, `tasks`, or `all` as requested.

Do not generate downstream tasks from raw HLD assumptions when the relevant spec, API contract, or integration dependency is unresolved.


## Do not

- Do not manually split `HLD.md` into many canonical HLD files by default.
- Do not bypass `hld_spec_sync.py` when updating specs from HLD.
- Do not bypass `hld_spec_downstream.py` when creating downstream Spec Kit artifacts.
- Do not load the whole HLD into prompts when `--use-hld-map --target-hld` is appropriate.
- Do not invent HLD IDs, spec IDs, owners, or source-of-truth decisions.
- Do not silently resolve conflicts; mark them as `TBD`, `CONFLICT`, or `CONFLICTS_WITH REF HLD-xxx`.

## Downstream analysis boundary

`downstream_analysis.md` is not a first-run artifact.

It is a bounded downstream-analysis artifact produced only after the upstream HLD/spec boundary is accepted.

Do not run downstream analysis from raw-HLD assumptions.

Correct ownership:

```text
Human
-> owns unresolved decisions

Judge/orchestrator
-> owns process, scope, subagent briefing, context boundary, output review, synthesis, and escalation

Downstream-analysis subagent
-> performs bounded gap analysis for one accepted scope
```

The judge/orchestrator may delegate downstream analysis to a subagent only with a bounded brief.

The downstream-analysis subagent must receive:

```text
Role:
Task:
Accepted scope:
Relevant HLD sections:
Relevant planned specs/specs:
Relevant first-run review findings:
Allowed files/commands:
Forbidden actions:
Context rule:
Stop conditions:
Required output:
Evidence required:
```

The downstream-analysis subagent must not receive the full HLD by default.

The subagent output may propose:

```text
.specify/sync/downstream/downstream_analysis.md
.specify/sync/downstream/gap_closure_plan.md
```

The judge/orchestrator must review the proposal before accepting it.

Stop for human decision before downstream work when there is unresolved:

- architecture direction
- source of truth
- ownership
- API/interface contract
- data/state ownership
- performance/memory behavior
- failure/recovery behavior
- spec boundary
- implementation scope

Safe downstream mode should be bounded by HLD map or by an explicit context limit.

Preferred bounded command shape:

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-007 --phase analyze --prompt-only
```

Do not run this as the first downstream step on a large/raw HLD:

```bash
./hld_spec_downstream.py --hld HLD.md --phase analyze
```

## SpecKit planning and constitution contract

Before target spec writing, branch creation, or implementation, HLDspec must build and discuss the plan with the human.

HLDspec must extract from the HLD and planning artifacts:

```text
user stories
use cases
user journeys
feature/spec candidates
API/interface contracts
processing/functionality behavior
shared/common functionality
architecture dependencies
implementation dependencies
```

Required decomposition rules:

```text
1. Split API/interface contracts from processing behavior when they are mixed.
2. Split user-facing journeys from backend/internal mechanics when they are mixed.
3. Extract common/shared capabilities before dependent features.
4. Keep source-of-truth, data model, and architecture constraints explicit.
5. Build independent foundations before dependent features.
6. Do not start implementation before the plan and constitution are reviewed with the human.
```

Required pre-work artifacts:

```text
.specify/sync/product_story_map.md
.specify/sync/product_story_map.json
.specify/sync/architecture_dependency_graph.md
.specify/sync/architecture_dependency_graph.json
.specify/sync/constitution_plan.md
.specify/sync/constitution_plan.json
.specify/sync/bottom_up_implementation_plan.md
.specify/sync/bottom_up_implementation_plan.json
```

The constitution is not optional. It is the architecture and governance source of truth for the SpecKit process.

The judge/orchestrator must stop and discuss these artifacts with the human before creating project specs, branches, tasks, or implementation files.

Required checkpoint question:

```text
Does this plan and constitution correctly represent the architecture, dependencies, user journeys, and implementation order?
```

Allowed human decisions:

```text
APPROVE_PLAN
MODIFY_PLAN
DECOMPOSE_MORE
FIX_CONSTITUTION
REBUILD_DEPENDENCY_GRAPH
```

The judge/orchestrator may recommend a decision with evidence, but must not answer for the human.


## SpecKit ownership boundary and prework handoff

HLDspec must use SpecKit instead of reimplementing SpecKit.

HLDspec owns:

```text
HLD extraction
user story / use case / user journey extraction
architecture decomposition
API/interface versus processing/functionality split
shared/common foundation extraction
feature dependency graph
constitution update plan
bottom-up SpecKit invocation order
checkpoint/orchestration state
```

SpecKit owns:

```text
spec.md
checklists/requirements.md
clarification flow
plan.md
research.md
data-model.md
contracts/
quickstart.md
tasks.md
implementation phase
```

HLDspec must not manually create final SpecKit feature specs when the real SpecKit workflow is available.

Before invoking SpecKit, HLDspec must generate and discuss:

```text
.specify/sync/speckit_input_manifest.json
.specify/sync/speckit_input_manifest.md
.specify/sync/speckit_invocation_queue.json
.specify/sync/speckit_invocation_queue.md
.specify/sync/constitution_update_plan.json
.specify/sync/constitution_update_plan.md
.specify/sync/feature_dependency_graph.json
.specify/sync/feature_dependency_graph.md
```

The constitution update plan is required because the SpecKit constitution governs later `specify`, `plan`, `tasks`, and `implement` phases.

The judge/orchestrator must stop and discuss the manifest, dependency graph, constitution update plan, and invocation queue with the human before invoking SpecKit.

Allowed human decisions:

```text
APPROVE_PLAN
MODIFY_PLAN
DECOMPOSE_MORE
FIX_CONSTITUTION
REBUILD_DEPENDENCY_GRAPH
```


## Spec Branch Queue

Spec Kit work is branch-oriented. HLDspec must not treat target spec generation as only file creation.

When target-spec generation is allowed, HLDspec must generate:

```text
.specify/sync/spec_branch_queue.json
.specify/sync/spec_branch_queue.md
```

The branch queue is derived from `target_spec_work_order.json`.

Rules:

- process one planned spec branch at a time
- cache the branch name before writing files
- do not create Git branches automatically
- do not jump ahead in the queue unless the human explicitly changes the order
- do not write project `specs/` without explicit human approval
- workspace drafts may be written only under the first-run workspace unless separately approved


## Target Spec Work Order

When target-spec generation is allowed, the judge/orchestrator must not choose an arbitrary feature cluster.

HLDspec must generate:

```text
.specify/sync/target_spec_work_order.json
.specify/sync/target_spec_work_order.md
```

The work order is bottom-up: dependencies before dependents, using `depends_on_specs` from `spec_build_plan.json`.

The judge/orchestrator must follow this order unless the human explicitly changes it.

Before writing specs, show the proposed file list from the work order and get human approval.

## Spec Build Plan decision queue

When `spec_build_plan_review.md` blocks target-spec generation, the judge/orchestrator must not decide the fix from its own read.

HLDspec must generate:

```text
.specify/sync/spec_build_plan_decision_queue.json
.specify/sync/spec_build_plan_decision_queue.md
```

The human answers the listed options. The judge/orchestrator may recommend with evidence, but must not record its recommendation as the human decision.

For example, if planned spec 018 mixes API/interface contract with processing behavior, the queue should ask whether to split the planned spec, modify HLD-SPECS mapping, keep with reason, or defer.

## Human orientation contract

At every HLDspec checkpoint, the judge/orchestrator must orient the human before asking for decisions.

The human should not need to remember the workflow, infer why an artifact is missing, or know the next command.

Required checkpoint response format:

```text
Where we are:
- <current checkpoint/state>
- source HLD modified: yes/no
- working HLD modified: yes/no

What HLDspec already did:
- <completed steps>

Why we stopped:
- <blocking checkpoint/gate>

What I need from you:
- <only the actual checkpoint questions/options>

What I will do after you answer:
- update the relevant JSON artifact
- rerun the same HLDspec command
- stop at the next real checkpoint
```

Rules:

- Do not ask for a generic "OK to continue."
- Do not ask the human what command to run.
- Do not ask the human to edit JSON.
- Do not jump to a feature cluster manually.
- Explain why expected later artifacts do not exist yet when the current checkpoint is earlier in the flow.
- Ask only the generated checkpoint questions.

## SpecKit prework quality gate

Before invoking SpecKit, HLDspec must generate:

```text
.specify/sync/speckit_prework_quality_review.json
.specify/sync/speckit_prework_quality_review.md
```

The judge/orchestrator must present:

```text
1. Constitution case
2. Architecture/dependency case
3. First-feature case
4. Beskeptic findings
5. Feedback impact rules
6. Human approval question
```

The first-feature case must explain why the first feature is first, for example:

```text
Feature 001 is first because it has no dependencies and is the foundation/root feature.
```

If the human gives feedback, the judge/orchestrator must rebuild all affected artifacts, not patch only the visible markdown.

Examples:

```text
constitution feedback -> rebuild constitution plan, manifest if boundaries change, dependency graph if affected, invocation queue, quality review
dependency feedback -> rebuild dependency graph, invocation queue, quality review
decomposition feedback -> update working HLD/HLD-SPECS mapping, rerun first_readonly, regenerate prework artifacts
```

The quality review must use Beskeptic to detect unclear architecture, weak decomposition, missing foundations, API/functionality mixing, and explanations that will not make sense to the human.

SpecKit invocation remains blocked until this gate is approval-ready and the human approves.

## SpecKit Proxy Protocol

When HLDspec reaches an approved SpecKit prework gate, it must use a bounded SpecKit proxy subagent instead of manually creating SpecKit artifacts.

Reference:

```text
docs/SPECKIT_PROXY_PROTOCOL.md
```

Before invoking SpecKit, generate:

```text
.specify/sync/speckit_proxy_dossier.json
.specify/sync/speckit_proxy_dossier.md
```

The SpecKit proxy subagent receives the dossier and uses SpecKit in sequence:

```text
constitution if needed -> specify -> clarify -> plan -> tasks -> analyze if needed -> implement only after explicit approval
```

The proxy may answer SpecKit questions from evidence in the HLD/prework dossier. It must escalate questions affecting architecture, source of truth, constitution, API contract, security, data ownership, user-visible scope, dependency order, feature split/merge, or implementation approval.

The judge/orchestrator remains responsible for final decisions, human checkpoints, affected-artifact rebuilds, and continuation.

