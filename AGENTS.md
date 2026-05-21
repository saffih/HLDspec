# Agent Instructions for HLDspec

made by AI

This repository contains wrapper tools for turning a High-Level Design document into Spec Kit artifacts and downstream planning or implementation artifacts.

Do not bypass the wrappers unless explicitly instructed.

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

9. Run one bounded prompt before syncing.

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003 --prompt-only
```

Review:

```text
logs/hld_spec_sync/<timestamp>/context_selection.json
logs/hld_spec_sync/<timestamp>/prompt.md
```

10. Sync one target section at a time.

```bash
./hld_spec_sync.py --hld HLD.md --use-hld-map --target-hld HLD-003
```

11. Continue downstream only after the related spec exists.

```bash
./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan --prompt-only

./hld_spec_downstream.py --hld HLD.md --use-hld-map --target-hld HLD-003 --phase plan
```

### Do not

- Do not overwrite or delete `HLD.raw.md`.
- Do not tag every small subsection.
- Do not invent spec IDs, owners, resources, or source-of-truth decisions.
- Do not manually split the HLD into many canonical source files by default.
- Do not run full-HLD sync when `--use-hld-map --target-hld` is appropriate.
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
- one `--prompt-only --target-hld` run shows bounded context instead of the full huge HLD.


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
