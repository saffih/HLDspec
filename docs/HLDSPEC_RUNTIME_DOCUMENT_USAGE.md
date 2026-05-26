# HLDspec Runtime Document Usage

## Purpose

This document defines how HLDspec must use its guidance documents during an actual run.

Guidance documents are not passive references. During a run, HLDspec must turn relevant guidance into target-specific artifacts, gates, prompts, and RunSkeptic checks.

## Core rule

HLDspec must not copy every principle into every target.

HLDspec must:

1. Read the reusable guidance documents.
2. Select only the guidance relevant to the current target.
3. Record the selected rules and tool choices.
4. Explain the trigger for every optional architecture/tool choice.
5. Run or require RunSkeptic at key junctions.
6. Generate prompts that enforce the selected rules.
7. Block when required evidence is missing or conflicting.

## Reusable guidance documents

HLDspec may use these documents as reusable knowledge:

- `docs/SOFTWARE_DESIGN_PRINCIPLES.md`
- `docs/BACKEND_TECHNOLOGY_RECOMMENDATION.md`
- `docs/HLD_TO_TARGET_WORKSPACE.md`
- `docs/CONSTITUTION_GENERATION.md`
- `docs/SPECKIT_DELEGATION_PROMPTS.md`
- `docs/MEDIATOR_PROMPT_PROTOCOL.md`
- `docs/CONTEXT_TAILORING_PROTOCOL.md`
- `docs/RUNSKEPTIC_EVIDENCE_QUALITY.md`
- `docs/CANONICAL_FLOW.md`

If a document is missing, HLDspec must continue with available evidence and mark the missing reference as ACTION in the quality review.

## Runtime flow

During a run, HLDspec must use the guidance as follows:

```text
source resources
  -> target/targetHLD/
  -> select relevant design principles
  -> select backend technology recommendation defaults/upgrades
  -> extract constitution signals
  -> build principle-level constitution update plan
  -> slice spec packages
  -> build dependency graph
  -> generate SpecKit and mediator prompts
  -> RunSkeptic gates
  -> human approval where required
  -> SpecKit execution inside target/
```

## Required generated artifacts

A correct run should produce or update these artifacts when relevant:

```text
target/.hldspec/design_principles_selection.json
target/.hldspec/design_principles_selection.md
target/.hldspec/backend_technology_recommendation.json
target/.hldspec/backend_technology_recommendation.md
target/.hldspec/constitution_signals.json
target/.hldspec/constitution_update_plan.json
target/.hldspec/constitution_update_plan.md
target/.hldspec/spec_packages.json
target/.hldspec/spec_packages.md
target/.hldspec/feature_dependency_graph.json
target/.hldspec/speckit_invocation_queue.json
target/prompts/
```

## Design principle selection

For each selected principle, HLDspec must record:

```text
principle:
source_document:
why_relevant:
target_evidence:
applies_to:
enforcement_location:
test_or_verification:
runskeptic_required:
```

A principle may apply to:

- target constitution
- one or more spec packages
- dependency graph
- prompt instructions
- implementation gate
- test/tooling requirement

## Backend tool selection

For each backend tool or architecture pattern, HLDspec must record:

```text
category:
selected_tool:
default_or_upgrade:
trigger:
reason:
complexity_added:
tests_required:
observability_required:
rollback_or_simplification_path:
runskeptic_result:
```

If a tool is selected without a trigger, HLDspec must mark ACTION and block promotion.

## Constitution usage

The constitution update plan must use selected principles only.

It must remain:

- target-specific
- principle-level
- succinct
- actionable
- verifiable

It must not include:

- feature ids
- feature names
- feature order
- branch names
- task ids
- per-feature implementation details

Feature-specific information belongs in spec packages, dependency graphs, invocation queues, and prompts.

## Spec package usage

Each spec package must include relevant selected principles and backend tool choices only when they affect that package.

Each package must include:

- source HLD sections
- architecture/tool choices that affect the package
- testability requirements
- required test tools
- RunSkeptic trigger points
- evidence sources
- open questions
- stop condition

## Prompt usage

Every generated target-agent prompt must include:

- the relevant selected principles
- the selected backend/tool choices for the phase
- allowed evidence files
- forbidden broad reads
- model tier
- cost/context constraints
- RunSkeptic trigger points
- stop condition
- escalation rule

Prompts must not include unrelated guidance that bloats context.

## Cost/context economy

HLDspec must protect cost, context size, and agent attention.

Runtime rules:

- Use the smallest sufficient context.
- Use the weakest sufficient model.
- Use the narrowest sufficient prompt.
- Use scripts for deterministic extraction and validation.
- Preload relevant HLD knowledge.
- Do not reread the full HLD unless explicitly needed.
- Give subagents one feature, one phase, or one bounded check.
- Use stronger models only for architecture, source of truth, contracts, conflict resolution, promotion gates, or high-risk implementation.

## RunSkeptic usage

RunSkeptic is required at key junctions and when uncertain.

Required junctions:

- HLD generation or improvement
- target workspace creation
- design principle selection
- backend technology recommendation
- constitution signal extraction
- constitution update plan
- spec package slicing
- dependency graph generation
- SpecKit invocation queue
- delegation prompt generation
- implementation approval
- post-implementation verification

Outcomes:

- PASS: continue
- ACTION: fix and rerun the relevant gate
- CONFLICT: stop and escalate

Missing evidence is ACTION or CONFLICT, not PASS.

## Gate behavior

Before HLDspec allows a phase to advance:

- required artifacts must exist
- selected principles must have evidence
- optional tool upgrades must have triggers
- testability must be explicit
- prompt context must be bounded
- RunSkeptic findings must be PASS or resolved ACTION
- unresolved CONFLICT must stop the run

## Acceptance criteria

A run uses the documents correctly when:

- guidance is converted into target-specific artifacts
- constitution stays principle-level
- spec packages stay feature/package-specific
- prompts include only relevant guidance
- optional tools have explicit triggers
- RunSkeptic is applied at key junctions
- cost/context economy is enforced
- missing evidence blocks instead of becoming silent approval
