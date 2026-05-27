# SpecKit Proxy Protocol

> Canonical terminology and flow:
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md). The bounded
> **Execution Handoff** to the proxy is carried by the **SpecKit Run Card** (the
> operational instruction contract); the proxy dossier is the evidence bundle. See
> the canonical doc §8 for the Run Card schema.

This protocol defines how HLDspec should use SpecKit through a bounded subagent.

HLDspec does not replace SpecKit. HLDspec prepares the data, constitution context, architecture constraints, dependency order, and evidence. A SpecKit proxy subagent then engages with SpecKit as a prepared client.

## Roles

| Role | Responsibility |
|---|---|
| Judge/Orchestrator | Owns HLDspec state, human checkpoints, evidence, approval gates, and final decisions. |
| SpecKit Proxy Subagent | Uses the judge-approved dossier to run SpecKit phases and answer SpecKit questions when evidence is sufficient. |
| Human Decision Owner | Approves constitution/architecture/dependency choices and answers questions that cannot be resolved from evidence. |
| SpecKit | Owns creation and evolution of `spec.md`, checklist, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md`, and implementation. |

## Required sequence

The proxy must follow the SpecKit sequence:

```text
constitution if missing or update required
1. constitution, if the constitution is missing or needs update
2. specify
3. clarify, when SpecKit produces clarification questions
4. plan
5. tasks
6. analyze, when consistency review is needed
7. implement, only after explicit approval
```

The proxy must not skip from HLDspec prework directly to implementation.

## Slice-controlled implementation

The proxy must run complete-product SpecKit phases before implementation:

```text
one /speckit.specify
one /speckit.plan
one /speckit.tasks
one /speckit.analyze
```

After analyze, implementation is controlled by HLDspec slice selection. The proxy
must not invoke raw all-task implementation by default.

Each implementation invocation must include:

```text
selected slice
allowed task IDs
allowed files
forbidden files
HLD anchors in scope
deferred anchors
focused tests
prior-slice regression tests
phase report path
anchor coverage update
stop condition
```

The proxy must stop if the selected slice is unclear, a task lacks HLD anchors,
required evidence is missing, tests fail, files outside the approved scope change,
or a human-owned decision appears.

See `docs/SPECKIT_SLICE_CONTROL.md`.

## Run Card and dossier rule

Before invoking SpecKit, HLDspec must generate the execution handoff and its evidence bundle:

```text
target/prompts/speckit/<package-id>/RUN_CARD.json
target/prompts/speckit/<package-id>/RUN_CARD.md
target/.hldspec/sync/speckit_proxy_dossier.json
target/.hldspec/sync/speckit_proxy_dossier.md
```

Legacy `.specify/sync/speckit_proxy_dossier.*` paths may exist for compatibility, but they are not the canonical HLDspec control-plane location. New HLDspec control artifacts live under `target/.hldspec/`.

The dossier must include:

```text
feature to work on
bottom-up position
natural-language input for /speckit.specify
constitution rules and implications
source HLD sections
dependency context
API/interface notes
processing/functionality notes
shared/common dependencies
Skeptic findings
allowed evidence sources
question-answering policy
escalation policy
```

The proxy must use only the SpecKit Run Card, dossier, and listed evidence sources unless the judge explicitly expands scope.

## Evidence sources

The proxy may inspect:

```text
target/targetHLD/raw/HLD.raw.md
target/targetHLD/HLD.md
target/targetHLD/sections/
target/.hldspec/sync/hld_index.md
target/.hldspec/sync/spec_build_plan.json
target/.hldspec/sync/spec_build_plan_review.md
target/.hldspec/sync/speckit_input_manifest.json
target/.hldspec/speckit_invocation_queue.json
target/.hldspec/constitution_update_plan.json
target/.hldspec/feature_dependency_graph.json
target/.hldspec/sync/speckit_prework_quality_review.json
target/prompts/speckit/<package-id>/RUN_CARD.md
target/.specify/memory/constitution.md, if it exists
target/specs/, if the judge allows existing project context
```

The proxy may use local bounded search tools:

```text
rg
grep
find
sed -n
awk
cat for small files
```

The proxy must not load the entire HLD into context when section-level evidence is available.

## Question answering policy

When SpecKit asks a question, the proxy must classify it:

```text
ANSWER_FROM_EVIDENCE
ANSWER_FROM_APPROVED_DEFAULT
ESCALATE_TO_HUMAN
```

### ANSWER_FROM_EVIDENCE

Use this when the answer is directly supported by HLDspec artifacts, HLD evidence, approved constitution rules, or existing project specs.

Required log entry:

```text
question
answer
evidence source
confidence: HIGH
affected artifacts
```

### ANSWER_FROM_APPROVED_DEFAULT

Use this only when SpecKit itself allows a default, the default is pre-approved or explicitly allowed by the Run Card, and the choice does not materially affect architecture, scope, security, data ownership, user experience, dependency order, source of truth, or implementation approval.

Required log entry:

```text
question
answer
default rationale
confidence: MEDIUM
reversal cost
affected artifacts
```

### ESCALATE_TO_HUMAN

Use this when the question affects:

```text
architecture boundary
source of truth
constitution rule
API contract
security/privacy
data ownership
user-visible scope
dependency order
feature split/merge
implementation approval
```

Required output to judge:

```text
question
why evidence is insufficient
options, if SpecKit provided them
recommended option, if evidence supports a recommendation
impact if changed
affected artifacts to rebuild
```

## Clarify phase handling

SpecKit may ask clarification questions during `specify` or via `clarify`.

The proxy should answer clarification questions only when:

```text
the answer is already in the HLD/prework dossier
or the answer is an approved safe default from the Run Card
or the judge has a prior approved decision
```

Otherwise the proxy returns the question to the judge, and the judge interviews the human using the Judge-Led Review Protocol.

## Constitution handling

The proxy must not invent a constitution from scratch.

The proxy must use:

```text
constitution_update_plan.md/json
speckit_prework_quality_review.md/json
approved human decisions
```

If `.specify/memory/constitution.md` is missing, the proxy may invoke SpecKit constitution only after the judge has human approval for the constitution update plan.

If SpecKit constitution asks for missing governance data, the proxy may answer from approved project context. If no evidence exists, escalate.

## Phase completion records

After each SpecKit phase, the proxy must report:

```text
phase run
files created/changed
questions asked
questions answered from evidence
questions escalated
artifacts needing rebuild
readiness for next phase
```

## Safety rules

The proxy must not:

```text
modify the source HLD
answer human-owned architecture decisions
change dependency order without judge approval
invoke implementation without explicit approval
skip constitution checks
create multiple features in one SpecKit specify invocation
continue when a blocking RunSkeptic finding remains
```

## Success criteria

The proxy run is valid when:

```text
the selected feature is the active next item in the approved Run Card and queue
the constitution is approved or safely updated
SpecKit specify created exactly one feature spec
clarifications are resolved or escalated
plan passes constitution checks
tasks are dependency ordered and independently testable
no implementation starts without approval
```

## Context tailoring and bloat guard

This protocol must use the shared context-tailoring rules:

```text
docs/CONTEXT_TAILORING_PROTOCOL.md
```

Use the weakest sufficient agent, the smallest sufficient context, and the strictest sufficient prompt. If a subtask can be done by a deterministic tool, script, grep, or lower-cost bounded agent, do not spend high-reasoning budget on it.
