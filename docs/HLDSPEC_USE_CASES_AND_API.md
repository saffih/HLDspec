# HLDspec Use Cases and Simple API

## Purpose

HLDspec should feel like one simple judge-led product, not a pile of scripts.

The user should be able to point HLDspec at a project and let the judge/orchestrator lead:

```text
HLDspec
```

or:

```text
HLDspec ./Flow-System-HLD.md
```

The judge/orchestrator should discover state, explain where we are, ask only real checkpoint questions, record answers, rerun the correct step, and stop at the next safe checkpoint.

## Product boundary

HLDspec owns:

```text
- raw HLD inspection
- raw HLD to HLDspec conversion
- HLD section classification
- architecture/use-case extraction
- constitution prework
- dependency graph
- SpecKit invocation plan
- checkpoint interview
- RunSkeptic / Beskeptic review
- state summary
- prework package
```

SpecKit owns:

```text
- spec.md
- clarify
- plan.md
- research.md
- data-model.md
- contracts/
- quickstart.md
- tasks.md
- implementation, only after approval
```

HLDspec must not manually replace SpecKit.

## Current command surface status - 2026-05-26

Current implemented facade:

```text
hldspec start
hldspec status
hldspec review
hldspec continue
hldspec diff
hldspec doctor
```

Legacy/debug or not-yet-current command names in this document:

```text
hldspec run
hldspec interview
hldspec prework
hldspec speckit-proxy
hldspec speckit
hldspec pause
```

Rule: use cases are canonical; command names are an interface mapping. A command must be marked current, future, or legacy/debug before docs can advertise it as product behavior.

## Complete use-case catalog target

| Use case | Trigger | Command/API status | Main artifacts | Stop condition | Test expectation |
|---|---|---|---|---|---|
| UC-001 start with no source yet | user starts HLDspec without source | current/future interview path | session context, later `target/.hldspec/interview_answers.*` | source and target identified or human decision needed | no writes before target is known |
| UC-002 start with source only | source provided, target absent | current `start` plus target selection | source HLD, target session | target chosen or created | source is read-only |
| UC-003 create new target from raw HLD | source and target provided, no state | current `start` | `target/targetHLD/`, `target/.hldspec/` | next checkpoint generated | target layout matches adapter |
| UC-004 adopt existing target without HLDspec state | target exists without session | current `start` mode adopt | target inspection, session manifest | adoption checkpoint | existing target not overwritten silently |
| UC-005 resume existing HLDspec target | existing session | current `status`/`continue` | session, state, checkpoints | next safe action | no skipped gates |
| UC-006 update after source/resources changed | source hash changed | current `diff`, future update path | input manifest, affected artifacts | affected rebuild plan | stale artifacts detected |
| UC-007 upgrade after guidance/templates changed | HLDspec guidance changed | future upgrade path | guidance fingerprints, prompts | upgrade review | stale prompts detected |
| UC-008 review checkpoint and capture human decisions | checkpoint exists | current `review`, future decision API | review files, decision queue | decisions recorded | machine-readable decision artifact |
| UC-009 continue after approval | approval exists | current `continue`, needs ProjectMachine integration | ProjectMachine context | next machine checkpoint | `continue` invokes machine |
| UC-010 handle unresolved conflict | conflict exists | current/future conflict gate | conflict artifact | human decision required | promotion blocked |
| UC-011 generate use-case/API map | converted HLD available | future prework path | use-case/API map | map review | context-only sections not first features |
| UC-012 generate package/dependency/invocation queue | use-case map ready | future prework path | packages, graph, queue | queue review | graph and queue match |
| UC-013 generate context packs and bounded prompts | package ready | future prompt generation | context packs, allowed evidence, forbidden reads | prompt review | no broad-read prompt |
| UC-014 delegate one SpecKit phase | approved package and phase | future speckit path | bounded dossier, phase prompt | phase complete or question escalated | one phase only |
| UC-015 answer SpecKit clarification from evidence only | SpecKit asks question | future evidence answering path | evidence log, answer record | answer or escalation | answer cites allowed evidence |
| UC-016 escalate unknown SpecKit question to human | evidence missing | future escalation path | question queue | human decision needed | unknown not guessed |
| UC-017 verify SpecKit output and RunSkeptic findings | phase output exists | future verify path | verification report, findings | PASS/ACTION/CONFLICT | findings block promotion when unresolved |
| UC-018 detect stale artifacts and rebuild affected outputs | inputs changed | future stale detection | artifact hashes, rebuild plan | affected rebuild done or review needed | stale dependency test |
| UC-019 brownfield target with existing specs | specs already exist | future brownfield/adopt path | existing specs, drift report | human review | no overwrite without approval |
| UC-020 user-requested pause before continuing | user requests pause | future/current human checkpoint behavior | state marker, handoff note | action withheld until user resumes | no further machine action |
| UC-021 development handoff between agents/models | repo work transfers | current dev handoff | `.hldspec-dev/handoff/`, backlog | handoff packet generated | handoff includes backlog pointers |
| UC-022 maintainer/debug direct-script run | maintainer debugging | legacy/debug | script outputs | explicit maintainer action | documented as non-product workflow |
| UC-023 completed history / merged-work audit | completed work exists | future audit path | merge evidence, status map | history classified | no live work inferred from stale docs |

## Core user scenarios

### Scenario 1 - First project run from a raw HLD

User says:

```text
HLDspec ./Flow-System-HLD.md
```

Expected behavior:

```text
1. Discover project root.
2. Create or reuse .hldspec-first-run.
3. Inspect raw HLD.
4. If raw HLD is not in HLDspec format, generate conversion questions.
5. Ask only the listed conversion questions.
6. Do not continue to SpecKit prework until conversion questions are answered.
```

User should see:

```text
Current stage: CONVERSION_CHECKPOINT
Why we stopped: raw HLD section boundaries need decisions
Questions:
- Q-001 ...
- Q-002 ...
Allowed answers:
- SPLIT_AS_PROPOSED
- MODIFY_SPLIT
- KEEP_AS_ONE
```

### Scenario 2 - Continue after checkpoint answers

User answers:

```text
Q-001: SPLIT_AS_PROPOSED
Q-002: SPLIT_AS_PROPOSED
Q-003: KEEP_AS_ONE
```

Expected behavior:

```text
1. Judge records answers in the controlling JSON queue.
2. Judge reruns the same HLDspec command.
3. HLDspec converts the working HLD only.
4. Source HLD is not modified.
5. HLDspec continues to the next safe checkpoint.
```

The user should not be asked what command to run.

### Scenario 3 - Convert raw HLD directly for debugging

User says:

```text
Convert this HLD to HLDspec format.
```

Expected behavior:

```text
1. Use the raw-HLD converter utility.
2. Write a separate converted output unless explicit overwrite is requested.
3. Validate HLD headings and metadata.
4. Write a conversion index.
5. Do not invoke SpecKit.
```

This is a utility path, not the normal product flow.

### Scenario 4 - Build architecture use cases before SpecKit

After conversion, HLDspec should extract:

```text
- users / actors
- user journeys
- system use cases
- feature candidates
- API/interface surfaces
- data/source-of-truth objects
- dependencies
- non-goals
- risks
- verification requirements
```

Expected behavior:

```text
1. Build a use-case and API map from HLD evidence.
2. Separate context-only sections from implementable features.
3. Do not treat stakeholder analysis, business case, personas, or milestones as first buildable features.
4. Use those sections as context for constitution and planning.
```

### Scenario 5 - Constitution and dependency approval

Before invoking SpecKit, HLDspec should present:

```text
- constitution case
- dependency order
- first buildable feature
- API/processing split warnings
- Beskeptic findings
- feedback impact rules
```

Expected behavior:

```text
1. Ask for approval or requested change.
2. If feedback affects constitution, dependency order, or feature boundaries, rebuild affected artifacts.
3. Do not patch only the markdown package.
```

### Scenario 6 - SpecKit proxy run

After human approval, HLDspec may act as a proxy user of SpecKit.

Expected behavior:

```text
1. Select exactly one feature from the approved invocation queue.
2. Create a bounded dossier for that feature.
3. Invoke SpecKit in sequence:
   - constitution if needed
   - specify
   - clarify
   - plan
   - tasks
   - implement only after explicit approval
4. Answer SpecKit questions only from HLD/prework evidence.
5. Escalate unknown or architectural questions to the human.
6. Record every question, answer, evidence source, and changed file.
```

### Scenario 7 - Source-HLD-affecting feedback

If the user says something that changes architecture intent or section boundaries, HLDspec must not lose it.

Expected behavior:

```text
1. Classify feedback as:
   - process-only
   - source-HLD-affecting
   - unclear
2. Record it in decision logs.
3. Create a source update queue/appendix if the source HLD should change.
4. Do not modify the source HLD without explicit approval.
```

## Simple command API

### hldspec run

Primary command:

```bash
scripts/hldspec_run.sh <source-HLD.md>
```

Behavior:

```text
- natural project runner
- creates/reuses .hldspec-first-run
- stops at safe checkpoints
- never modifies source HLD without approval
```

### hldspec status

Recommended wrapper:

```bash
scripts/hldspec_status.sh [project-root]
```

Behavior:

```text
- prints current stage
- prints current checkpoint
- prints controlling artifacts
- prints next allowed actions
- prints whether human decision is needed
```

Required output shape:

```text
Current stage:
Current checkpoint:
Controlling artifact:
Human decision needed:
Next allowed action:
```

### hldspec interview

Recommended wrapper:

```bash
scripts/hldspec_interview.sh [project-root]
```

Behavior:

```text
- discovers active checkpoint
- shows only open questions
- accepts answers interactively or through flags
- updates controlling JSON
- reruns HLDspec if requested
```

Non-interactive examples:

```bash
scripts/hldspec_interview.sh ~/code/flow --answer Q-003=KEEP_AS_ONE --rerun
```

```bash
scripts/hldspec_interview.sh ~/code/flow --accept-recommendations --rerun
```

### hldspec convert

Utility command:

```bash
python3 scripts/convert_hld_to_hldspec.py <raw-HLD.md> --default-flow-splits
```

Behavior:

```text
- converts raw HLD to HLDspec format
- writes separate output by default
- validates headings and metadata
- writes conversion index
```

### hldspec prework

Recommended wrapper:

```bash
scripts/hldspec_prework.sh [project-root]
```

Behavior:

```text
- builds use-case/API map
- builds constitution update plan
- builds feature dependency graph
- builds SpecKit invocation queue
- builds prework package
- runs Beskeptic quality gate
```

Must stop before SpecKit invocation.

### hldspec speckit-proxy

Recommended wrapper:

```bash
scripts/hldspec_speckit_proxy.sh [project-root] --feature <id> --phase specify|clarify|plan|tasks
```

Behavior:

```text
- runs one SpecKit phase for one approved feature
- uses only bounded dossier context
- records questions, answers, evidence, escalations, and changed files
- never implements without explicit approval
```

## Artifact API

### State artifact

```text
.specify/sync/hldspec_state.json
.specify/sync/hldspec_state.md
```

Required fields:

```text
current_stage
last_completed_stage
current_checkpoint
blocking_questions
controlling_artifacts
supporting_artifacts
legacy_supporting_artifacts
next_allowed_actions
source_hld_modified
working_hld_modified
```

### Use-case/API map

Recommended artifact:

```text
.specify/sync/hld_usecase_api_map.json
.specify/sync/hld_usecase_api_map.md
```

Purpose:

```text
Show what HLDspec thinks the system does before generating SpecKit work.
```

Required contents:

```text
actors
user journeys
system use cases
API/interface surfaces
data/source-of-truth objects
feature candidates
context-only sections
dependencies
non-goals
risks
open questions
```

This artifact should prevent mistakes like selecting `Stakeholder Analysis` as the first SpecKit feature.

### Conversion queue

```text
.specify/sync/hld_conversion_decision_queue.json
.specify/sync/hld_conversion_decision_queue.md
```

Purpose:

```text
Ask human only when raw HLD section boundaries require judgment.
```

### Spec Build Plan

```text
.specify/sync/spec_build_plan.json
.specify/sync/spec_build_plan.md
.specify/sync/spec_build_plan_review.md
```

Purpose:

```text
Plan candidate specs from HLD evidence.
```

Rules:

```text
- Context sections may inform specs but should not become first buildable features.
- First feature should be independently buildable.
- Product/business/stakeholder sections should usually map to context, not direct SpecKit implementation.
```

### SpecKit prework package

```text
.specify/sync/speckit_prework_package.json
.specify/sync/speckit_prework_package.md
```

Purpose:

```text
One human-facing review package before SpecKit invocation.
```

Must include:

```text
- where we are
- constitution case
- use-case/API case
- dependency case
- first buildable feature case
- Beskeptic findings
- feedback impact rules
- human checkpoint
```

### SpecKit proxy dossier

```text
.specify/sync/speckit_proxy_dossier.json
.specify/sync/speckit_proxy_dossier.md
```

Purpose:

```text
Bounded handoff for one feature and one SpecKit phase.
```

## Stage model

```text
NO_WORKSPACE
RAW_HLD_INSPECTED
CONVERSION_CHECKPOINT
WORKING_HLD_CONVERTED
USECASE_API_MAP_READY
SPEC_BUILD_PLAN_READY
SPEC_BUILD_PLAN_CHECKPOINT
SPECKIT_PREWORK_READY
SPECKIT_PREWORK_APPROVAL_GATE
SPECKIT_PROXY_DOSSIER_READY
SPECKIT_PHASE_RUNNING
SPECKIT_PHASE_DONE
IMPLEMENT_APPROVAL_REQUIRED
```

## Feature classification rules

### Buildable feature

A section may become a buildable feature if it has at least one of:

```text
- concrete system behavior
- data object/source-of-truth ownership
- API/interface contract
- processing behavior
- UI behavior
- operational behavior
- testable acceptance criteria
```

### Context-only section

A section should usually be context-only if it is mainly:

```text
- stakeholder analysis
- user persona description
- business case
- executive summary
- milestone/status list
- changelog
- assumptions
- decision log
- glossary
```

Context-only sections may feed:

```text
- constitution
- product constraints
- non-goals
- prioritization
- verification context
```

They should not be selected as the first buildable SpecKit feature.

## API/interface split rules

HLDspec must explicitly decide whether API/interface and processing are:

```text
- split into separate features
- sequenced as contract first, behavior second
- intentionally kept together with a reason
```

This applies especially to:

```text
- database APIs
- HTTP APIs
- storage APIs
- CLI commands
- session/spawn interfaces
- AI integration interfaces
```

## Human-facing output contract

At every stop, show only:

```text
1. Where we are
2. What happened
3. Why we stopped
4. What question needs a decision
5. Options
6. Recommendation, if evidence supports one
7. What HLDspec will do after the answer
```

Do not show all internal artifacts unless asked.

## Current known design correction

If the first feature case says:

```text
004 - Stakeholder Analysis
```

that is wrong for normal SpecKit implementation flow.

Correct behavior:

```text
Stakeholder Analysis = context-only
First feature = first independently buildable system foundation
```

The use-case/API map should catch this before prework approval.

