# HLDspec Answer Dossier Extraction Strategy

made by AI

Date: 2026-05-23

## Purpose

This document records the current strategy for improving HLDspec prework quality before SpecKit invocation.

The goal is not to manually write final specs. The goal is to produce a high-quality SpecKit Answer Dossier: a structured context package that lets later SpecKit/spec-orchestration steps build a correct constitution, specification, plan, tasks, and implementation path without guessing.

## Current problem

The current prework package can reach a formal approval checkpoint while still being too shallow for high-quality downstream SpecKit use.

Observed weaknesses:

- It can list bottom-up numeric IDs without enough named capability meaning.
- It can count API/interface surfaces, data/source-of-truth objects, and open questions without surfacing the important named items.
- It does not sufficiently expose provider/consumer relationships.
- It does not sufficiently explain how components integrate.
- It does not consistently show data ownership, source-of-truth ownership, and update timing.
- It can become stale after earlier checkpoints are resolved.
- It can make the first feature look valid because it has no dependencies, while still failing to explain why it is the correct foundation.
- It does not yet give Architect and Product Manager agents enough structured context to produce a quality product.

## Source-HLD facts that matter

The Flow HLD itself says it is the authoritative architecture document and that it defines:

- system architecture and component relationships
- architectural decisions and rationale
- Brain/core.md architecture and contracts
- integration patterns and data flow
- quality standards and success metrics

It also says implementation guidance should come from:

- Component Interface Definitions
- Database Schema Specification
- core.md Contract Invariants
- Technical Debt / deprecation timelines

Therefore HLDspec should extract those areas into named answer packs before asking for SpecKit approval.

## Recommended extraction method

Use a hybrid method.

Do not use only grep.
Do not use only full chunk digestion.

Recommended pipeline:

```text
1. Parse HLD headings and line ranges.
2. Run initial grep hotspot extraction for generic high-signal terms.
3. Build a project vocabulary from headings, repeated nouns, code symbols, command names, component names, protocol names, and capitalized terms.
4. Run a second project-specific grep using the learned vocabulary to find places generic keywords missed.
5. Run full section classification for recall.
6. Run Architect pass over architect-worthy sections.
7. Run Product Manager pass over PM-worthy sections.
8. Synthesize maps and answer packs.
9. Run dossier quality gate.
10. Only then allow SpecKit prework approval.
```

## Strategy A: keyword grep hotspots

Use grep/sed/awk or Python regex to find high-signal line windows.

Architect keywords:

```text
MUST
NEVER
FORBIDDEN
CRITICAL
Interface
Contract
Protocol
API
CLI
HTTP
SSE
Socket
TASK_OFFER
TASK_ACK
TASK_NACK
Database
Source of Truth
WIP
Sync
Projection
Provider
Consumer
Integration
Data Flow
Retry
Fallback
Failure
Error
Security
Permission
Environment
Session
```

PM keywords:

```text
Stakeholder
Persona
Pain Point
Business Outcome
Job-to-be-Done
User Story
Acceptance Criteria
Success Metric
Workflow
Journey
Priority
v1 Scope
MVP
Non-goal
Business Value
Adoption
Quality Metric
```

Output:

```text
.specify/sync/grep_hotspots.json
.specify/sync/grep_hotspots.md
```

Pros:

- fast
- deterministic
- catches explicit contracts and MUST/NEVER rules

Cons:

- misses implicit architecture/product meaning
- produces duplicates
- cannot reliably build integration maps alone

## Strategy B: full section chunk classifier

Classify every HLD section, using heading-derived chunks instead of arbitrary token windows.

Each chunk should emit structured JSON:

```json
{
  "hld_id": "HLD-xxx or inferred section key",
  "title": "section title",
  "line_start": 0,
  "line_end": 0,
  "architect_signal": "high|medium|low|none",
  "pm_signal": "high|medium|low|none",
  "reason": "",
  "capabilities": [],
  "interfaces": [],
  "contracts": [],
  "data_objects": [],
  "provider_consumer_links": [],
  "integration_paths": [],
  "failure_fallbacks": [],
  "user_goals": [],
  "acceptance_criteria": [],
  "success_metrics": [],
  "open_questions": [],
  "tbds": []
}
```

Output:

```text
.specify/sync/chunk_signal_map.json
.specify/sync/chunk_signal_map.md
```

Pros:

- high recall
- finds hidden PM and architect signals in prose
- better for long HLDs

Cons:

- noisy
- expensive
- duplicates related facts across many chunks
- still needs synthesis

## Strategy C: hybrid extraction with terminology learning

Use grep to find hotspots, learn the project terminology, run a second project-specific grep, then use full-section classification to avoid missing implicit context, then synthesize.

Terminology learning should collect:

```text
component names
command names
Python module/class names
protocol message names
database table names
status values
environment variable names
file/path names
capitalized domain phrases
repeated nouns from headings
```

For Flow, examples include terms such as:

```text
core.md
devin-bg
flow_spawn
flow_loop.py
FLOW_ENV
FLOW_SESSION_LOG
WIP
TASK_OFFER
TASK_ACK
TASK_NACK
append-wip
get-wip
notify
Database API
Storage
Config
Session Spawning
```

Second grep examples:

```text
grep around learned terms like "core.md", "devin-bg", "FLOW_ENV", "TASK_ACK", "append-wip", "get-wip", "session_health_daemon", "enhanced_connection_pool"
```

Expected best result:

```text
generic grep gives precision
learned vocabulary grep catches project-specific missed areas
section classifier gives recall
synthesis gives usable dossier
quality gate prevents shallow approval
```

Output:

```text
.specify/sync/speckit_answer_dossier.md
.specify/sync/architecture_answer_pack.md
.specify/sync/product_answer_pack.md
.specify/sync/interface_contract_map.md
.specify/sync/integration_map.md
.specify/sync/data_ownership_map.md
.specify/sync/dependency_reason_map.md
.specify/sync/open_questions_tbd_map.md
```

## Architect pass

The Architect pass should extract architecture, not product requirements.

Process:

```text
1. Identify components.
2. Identify what each component owns.
3. Identify interfaces exposed by each component.
4. Identify consumers of each interface.
5. Identify inputs, outputs, errors, and fallback behavior.
6. Identify data/state ownership.
7. Identify read/write/update timing.
8. Identify source of truth.
9. Identify integration flows across components.
10. Identify dependency order and the reason for the order.
11. Identify security/permission constraints.
12. Mark unknowns as TBD/NEEDS_CLARIFICATION.
```

Required Architect artifacts:

```text
architecture_answer_pack.md
interface_contract_map.md
integration_map.md
data_ownership_map.md
dependency_reason_map.md
failure_fallback_map.md
architecture_open_questions.md
```

Required interface map fields:

```text
contract_id
contract_name
provider
consumer
protocol_or_api
source_of_truth
inputs
outputs
errors
fallback
security_rule
data_owned
data_read
data_written
update_timing
depends_on
blocks
source_hld_sections
evidence
tbd_or_questions
```

Important Flow contracts to detect:

```text
Brain-to-Flow CLI Contract
CLI Protocol Contract
Database API Contract
WIP Source-of-Truth Contract
Task Delivery Handshake Contract
HTTP/UI API Contract
Storage Projection Contract
Session Spawn Contract
Environment Isolation Contract
Logging Contract
Reply Handling Contract
```

## Product Manager pass

The Product Manager pass should extract product intent, user value, and acceptance context. It should not define implementation contracts.

Process:

```text
1. Identify stakeholder/persona.
2. Identify job-to-be-done.
3. Identify pain points.
4. Identify user journeys/workflows.
5. Identify user stories.
6. Identify acceptance criteria.
7. Identify success metrics.
8. Identify priority/v1 scope.
9. Identify non-goals and deferred scope.
10. Identify open product questions.
```

Required PM artifacts:

```text
product_answer_pack.md
user_journey_map.md
acceptance_criteria_map.md
success_metrics_map.md
scope_priority_map.md
open_product_questions.md
```

Required PM fields:

```text
capability_id
capability_name
persona
job_to_be_done
user_goal
pain_point
user_story
acceptance_criteria
success_metrics
priority
scope_status
non_goals
source_hld_sections
evidence
tbd_or_questions
```

## Synthesis pass

The synthesis pass merges Architect and PM outputs into the SpecKit Answer Dossier.

For each planned spec, the dossier must include:

```text
planned_spec_id
capability_name
plain_english_purpose
source_hld_sections
pm_value
user_story_or_workflow
acceptance_criteria
success_metrics_or_TBD
architecture_owner
owns
provides
consumes
interfaces
provider_consumer_links
data_owns
data_reads
data_writes
source_of_truth_or_TBD
update_timing_or_TBD
integration_paths
dependency_reasons
failure_fallbacks
security_rules
open_questions
not_for_speckit_yet
```

## Quality gate

The Answer Dossier quality gate must fail if any planned spec lacks:

```text
named capability
owner/responsibility
provides
consumes
interface provider/consumer map
data ownership or explicit TBD
source-of-truth or explicit TBD
update timing or explicit TBD
dependency reason
integration path if it interacts with another spec
failure/fallback notes if relevant
PM user value or explicit non-user-facing classification
acceptance criteria or explicit TBD
traceability to HLD section(s)
```

The gate should also fail if:

```text
the prework package is stale
the current checkpoint is misreported
counts are provided without named maps
source-of-truth is invented
update timing is invented
ownership is invented
first feature is justified only by "no dependencies"
```

## Experiment design

Run three strategies on the same Flow HLD.

### Experiment A: grep-only

Outputs:

```text
grep_hotspots.json
grep_hotspots.md
```

Score against known important contracts:

```text
Brain-to-Flow CLI
CLI Protocol
Database API
WIP Lifecycle
Unix Socket Task Delivery
HTTP/SSE
Storage Projection
Session Spawning
Environment Isolation
Logging
Reply Handling
```

### Experiment B: chunk-only

Outputs:

```text
chunk_signal_map.json
chunk_signal_map.md
```

Score:

```text
recall of hidden PM and architect signals
noise level
duplicate findings
missed cross-section dependency links
```

### Experiment C: hybrid with terminology learning

Steps:

```text
1. generic grep
2. vocabulary extraction
3. project-specific second grep
4. full section classifier
5. synthesis
6. quality gate
```

Outputs:

```text
speckit_answer_dossier.md
architecture_answer_pack.md
product_answer_pack.md
interface_contract_map.md
integration_map.md
data_ownership_map.md
dependency_reason_map.md
open_questions_tbd_map.md
```

Score:

```text
coverage per planned spec
provider/consumer completeness
data ownership completeness
dependency reason completeness
PM acceptance criteria completeness
TBD correctness
traceability to HLD sections
human review usefulness
```

Expected winner:

```text
Hybrid extraction with synthesis and quality gate.
```

## UX requirement

The user should not need to provide long prompts.

Target interaction:

```text
HLDspec /Users/saffi/code/flow/HLD.md
```

or after a checkpoint:

```text
next
ok
accept all
```

HLDspec must own:

```text
state discovery
workspace selection
checkpoint presentation
answer application
artifact rebuilding
stale package detection
SpecKit approval gating
```

## Next implementation patch

Add an Answer Dossier stage after plan quality PASS and before SPECKIT_PREWORK_APPROVAL_GATE.

Likely files/scripts to add:

```text
scripts/build_hld_answer_dossier_experiment.py
scripts/build_hld_architecture_answer_pack.py
scripts/build_hld_product_answer_pack.py
scripts/build_hld_interface_contract_map.py
scripts/build_hld_data_ownership_map.py
scripts/build_hld_integration_map.py
scripts/build_hld_answer_dossier_quality_review.py
```

Likely files to update:

```text
scripts/project_continue.sh
scripts/first_run_readonly.sh
scripts/build_speckit_prework_package.py
scripts/build_speckit_prework_quality_review.py
docs/HLDSPEC_IMPLEMENTATION_TODO.md
tests/
```

Do not invoke SpecKit as part of this stage.

