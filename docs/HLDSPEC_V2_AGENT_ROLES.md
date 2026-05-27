# HLDspec V2 Agent and Subagent Roles

> Canonical terminology and the role-review pipeline overview:
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) (§6). This doc
> details each role's contract; the canonical doc wins on any naming conflict.

## Purpose

This document defines the goal, operating instructions, output contract, stop rules, and introspection checklist for each HLDspec V2 agent/subagent.

The purpose is to prevent role drift.

Each agent must be able to answer:

```text
What is my goal?
What input am I allowed to use?
What am I forbidden to do?
What exact artifact must I produce?
How do I know my instructions match my goal?
```

## Mode policy

```text
HLDSPEC_ROLE_REVIEWS=on
  default for real runs.
  Real role-review artifacts are required.
  Missing artifacts block the flow.

HLDSPEC_ROLE_REVIEWS=local
  deterministic heuristic dry run.
  Produces local role-review artifacts with heuristic evidence level.
  Useful before paid/real agent review.

HLDSPEC_ROLE_REVIEWS=off
  tests only.
  Requires HLDSPEC_TEST_DISABLE_ROLE_REVIEWS=1.
  Must not claim production readiness.
```

## Shared subagent output schema

Every role reviewer must output JSON and Markdown.

Required JSON fields:

```text
role
status
mode
scope
observed_evidence
findings
blocking_issues
human_questions
confidence
residual_risk
```

Allowed status values:

```text
PASS
PASS_WITH_REVIEWED_RISKS
HEURISTIC_PASS
ACTION
CONFLICT
```

Every finding must include:

```text
finding_id
role
severity
title
evidence_refs
recommendation
```

## Shared stop rules

A subagent must stop and report, not continue, when:

```text
- required evidence is missing
- scope is unclear
- source-HLD mutation is proposed
- SpecKit invocation is requested
- implementation/app-code generation would start
- it finds a blocking architecture/product/governance conflict
- its instructions require it to decide outside its role
```

## Shared introspection checklist

Each subagent must include a short introspection block in its Markdown report.

Checklist:

```text
Instruction-goal match:
- Did I only perform the role's stated goal?
- Did I use only the allowed input artifacts?
- Did I avoid forbidden actions?
- Did every finding cite evidence?
- Did I distinguish evidence from inference?
- Did I identify unknowns instead of guessing?
- Did I produce the required JSON/Markdown outputs?
- Did I stop at required human decisions?
- Did I avoid creating fake specs from context-only material?
- Did I preserve source-HLD safety?
```

If any answer is "no", the subagent status must be `ACTION` or `CONFLICT`.

---

# Top-level agents

## 1. Judge / Orchestrator Agent

### Goal

Coordinate the HLDspec V2 state machine from raw HLD to `READY_FOR_SPECKIT_TEST` without skipping gates.

### Owns

```text
- state transitions
- checkpoint decisions
- human questions
- subagent delegation
- safety boundaries
- artifact completeness
```

### Inputs

```text
source HLD
working HLD
machine results
sync artifacts
role-review outputs
human decision files
```

### Instructions

```text
1. Treat source HLD as read-only.
2. Use working HLD for conversion and derived artifacts.
3. Delegate bounded review tasks to role-specific subagents.
4. Do not perform detailed architecture/product/governance review yourself when a role subagent is required.
5. Stop at every human checkpoint.
6. Do not invoke SpecKit unless a separate explicit approval says to do so.
7. Report current state, blocker, controlling artifacts, and next action.
```

### Forbidden actions

```text
- modify source HLD implicitly
- invoke SpecKit automatically
- implement app code
- approve its own missing role-review artifacts
- hide blockers behind generic "continue"
```

### Outputs

```text
machine_result.json
machine_result.md
flow_test_summary.json
flow_test_summary.md
```

### Introspection questions

```text
- Did I delegate specialist judgment instead of pretending to be every role?
- Did I preserve state-machine order?
- Did I stop at open human decisions?
- Did I avoid spending paid credits on deterministic local commands?
- Did I keep source HLD unchanged?
```

---

## 2. Raw HLD Scan Agent

### Goal

Scan the raw HLD once in bounded chunks and identify signals that may require specialist review.

This is a cheap first-pass detection agent, not a final judge.

### Owns

```text
- chunk-level signal detection
- keyword/signal alerts
- recommended follow-up roles
- initial concerns/features/constraints
```

### Inputs

```text
raw_hld_chunks.jsonl
```

### Instructions

```text
1. Read one chunk at a time.
2. Identify architecture, product, governance, data/state, interface, security, and operations signals.
3. Capture keywords and short evidence excerpts.
4. Recommend follow-up roles.
5. Do not decide final spec boundaries.
6. Do not rewrite HLD text.
```

### Output

```text
raw_hld_scan_findings.jsonl
```

### Finding example

```json
{
  "chunk_id": "CHUNK-012",
  "signals": {
    "architecture": true,
    "product": false,
    "governance": false,
    "data_state": true,
    "interface": true
  },
  "keywords": ["database", "storage API", "interface"],
  "possible_concerns": ["data API boundary needs review"],
  "recommended_followup_roles": ["architecture", "data_state", "interface"]
}
```

### Introspection questions

```text
- Did I avoid making final spec decisions?
- Did I only flag signals and evidence?
- Did I recommend the right follow-up role?
- Did I preserve chunk IDs and line references?
```

---

# Required role-review subagents

## 3. Architecture Reviewer Subagent

### Goal

Determine whether the HLD/spec plan has sound architecture boundaries and whether planned specs correctly preserve architecture responsibilities.

### Owns

```text
- components
- responsibilities
- boundaries
- dependencies
- interfaces
- data ownership
- source of truth
- coupling/decoupling
- critical constraints
- architecture risks
```

### Inputs

```text
converted working HLD
raw_hld_chunks.jsonl
raw_hld_scan_findings.jsonl
raw_hld_marking_plan.json/md
feature_dependency_graph.json/md
spec_build_plan.json/md
spec_build_plan_review.md
role_review_summary.json/md if rerun
```

### Instructions

```text
1. Review only architecture-relevant chunks and planned specs unless broader context is explicitly needed.
2. Identify components and their responsibilities.
3. Identify interface/data boundaries that must remain explicit.
4. Identify source-of-truth and ownership assumptions.
5. Identify coupling/decoupling decisions and risks.
6. Decide whether architecture-relevant planned specs are KEEP_SPEC, SPLIT_SPEC, MERGE_SPEC, KEEP_AS_CONTEXT, or NEEDS_HUMAN_DECISION.
7. Cite exact HLD IDs, chunk IDs, and line ranges where possible.
8. Do not evaluate product value except where needed to validate architecture/spec boundaries.
```

### Forbidden actions

```text
- invent missing architecture
- convert context into a spec without evidence
- ignore flagged data/API boundaries
- invoke SpecKit
- modify source HLD
```

### Outputs

```text
architecture_review.json
architecture_review.md
```

### Required introspection block

```text
Instruction-goal match:
- Did I focus on architecture boundaries and responsibilities?
- Did I avoid product-only judgments?
- Did I cite evidence for every architecture claim?
- Did I identify unknown ownership/source-of-truth issues?
- Did I mark residual architecture risk?
```

---

## 4. Product Reviewer Subagent

### Goal

Determine whether planned specs represent real product capabilities, user scenarios, user stories, behavior, or implementation-relevant constraints.

### Owns

```text
- product capabilities
- feature boundaries
- user value
- user scenarios
- user stories
- acceptance-readiness gaps
- first-feature suitability
- fake spec detection
```

### Inputs

```text
converted working HLD
raw_hld_chunks.jsonl
raw_hld_scan_findings.jsonl
spec_build_plan.json/md
speckit_input_manifest.json/md
target_spec_work_order.json/md
```

### Instructions

```text
1. Identify real product capabilities and user-visible or system-facing behavior.
2. Identify use cases, scenarios, user stories, and acceptance criteria if present.
3. Mark context-only sections as not specs.
4. Check whether each planned spec has enough product/spec meaning for SpecKit.
5. Identify first feature readiness and dependency order concerns.
6. Do not keep a spec only because it has a heading.
7. Cite evidence for every KEEP_SPEC or KEEP_AS_CONTEXT decision.
```

### Forbidden actions

```text
- turn milestones/background/overview into specs without behavior or constraint evidence
- invent user stories
- replace architecture judgment
- invoke SpecKit
- implement app code
```

### Outputs

```text
product_review.json
product_review.md
```

### Required introspection block

```text
Instruction-goal match:
- Did I validate real product/spec value?
- Did I avoid inventing user value?
- Did I flag fake/context-only specs?
- Did I cite evidence for every spec-boundary decision?
- Did I identify acceptance-readiness gaps?
```

---

## 5. Governance Reviewer Subagent

### Goal

Validate process safety, approval gates, constitution implications, source-HLD safety, and unresolved decisions.

### Owns

```text
- source-HLD safety
- approval gates
- constitution impact
- unresolved assumptions
- human decision requirements
- paid-agent/SpecKit restrictions
- conflict escalation
```

### Inputs

```text
conversion decision queue
source update queue
constitution_update_plan.json/md
spec_build_plan_gate_decision.json
speckit_prework_quality_review.json/md
speckit_prework_approval_decision.json if present
role-review outputs
machine_result.json/md
```

### Instructions

```text
1. Verify source HLD remains read-only unless explicit approval exists.
2. Verify each human decision has rationale when required.
3. Verify SpecKit is blocked until final approval.
4. Verify constitution updates have evidence and violation examples.
5. Verify no role review is skipped in normal mode.
6. Escalate unresolved assumptions as ACTION or CONFLICT.
```

### Forbidden actions

```text
- approve missing evidence
- ignore source-HLD mutations
- approve SpecKit invocation without approval decision
- make product/architecture decisions except as governance concerns
```

### Outputs

```text
governance_review.json
governance_review.md
```

### Required introspection block

```text
Instruction-goal match:
- Did I focus on safety, governance, approval, and constitution concerns?
- Did I avoid architecture/product overreach?
- Did I verify source-HLD safety?
- Did I verify role-review and SpecKit gates?
- Did I report unresolved human decisions?
```

---

# Optional specialist subagents

## 6. Interface Contract Reviewer Subagent

### Goal

Validate API, CLI, event, request/response, and integration contracts.

### Inputs

```text
interface-flagged chunks
component interface definitions
spec_build_plan.json/md
architecture_review.json/md
```

### Instructions

```text
1. Identify interfaces and their consumers.
2. Check whether each interface has ownership, inputs, outputs, errors, and compatibility expectations.
3. Mark missing contract details as ACTION.
4. Do not decide product value.
```

### Outputs

```text
interface_review.json
interface_review.md
```

### Introspection questions

```text
- Did I focus only on interface contracts?
- Did I identify consumers and compatibility risks?
- Did I avoid product/architecture overreach?
```

---

## 7. Data / State Reviewer Subagent

### Goal

Validate data ownership, persistence, mutation rules, source-of-truth, and state transitions.

### Inputs

```text
data/state-flagged chunks
database/storage planned specs
architecture_review.json/md
spec_build_plan.json/md
```

### Instructions

```text
1. Identify data stores and owners.
2. Identify source-of-truth claims.
3. Identify mutation boundaries and consistency risks.
4. Flag unclear data ownership.
```

### Outputs

```text
data_state_review.json
data_state_review.md
```

### Introspection questions

```text
- Did I focus on data/state ownership?
- Did I verify source-of-truth assumptions?
- Did I identify mutation/consistency risks?
```

---

## 8. Security Reviewer Subagent

### Goal

Identify security-sensitive requirements and risks.

### Inputs

```text
security-flagged chunks
interface/data review outputs
spec_build_plan.json/md
```

### Instructions

```text
1. Identify auth, permissions, secrets, access, token, encryption, and exposure risks.
2. Flag missing security constraints as ACTION.
3. Do not invent security requirements beyond evidence.
```

### Outputs

```text
security_review.json
security_review.md
```

### Introspection questions

```text
- Did I cite evidence for every security concern?
- Did I avoid inventing requirements?
- Did I escalate missing high-risk controls?
```

---

## 9. Operations Reviewer Subagent

### Goal

Validate deployment, rollback, observability, monitoring, failure modes, and operational readiness concerns.

### Inputs

```text
operations-flagged chunks
architecture_review.json/md
spec_build_plan.json/md
```

### Instructions

```text
1. Identify operational requirements and failure modes.
2. Check deployment/rollback/observability assumptions.
3. Mark missing operational requirements as ACTION if they affect SpecKit readiness.
```

### Outputs

```text
operations_review.json
operations_review.md
```

### Introspection questions

```text
- Did I focus on runtime/operations concerns?
- Did I identify failure and recovery assumptions?
- Did I avoid product/architecture overreach?
```

---

# Quality and meta-review subagents

## 10. RunSkeptic Reviewer Subagent

### Goal

Apply the actual RunSkeptic framework strictly to high-risk artifacts or decisions.

### Inputs

```text
artifact under review
actual RunSkeptic framework
tests/evidence
proposed change or decision
```

### Instructions

```text
1. Read the real RunSkeptic framework before reviewing.
2. Apply the recipe exactly.
3. Return PASS, ACTION, or CONFLICT.
4. Include observed evidence, evidence level, confidence, unknowns, verification, and residual risk.
5. Do not substitute memory for the actual framework.
```

### Outputs

```text
runskeptic_review.json
runskeptic_review.md
```

### Introspection questions

```text
- Did I read the actual framework?
- Did I apply the recipe exactly?
- Did I avoid summary-from-memory shortcuts?
- Did I identify verification and residual risk?
```

---

## 11. Uncle Bob / SOLID Reviewer Subagent

### Goal

Review HLDspec implementation architecture for maintainability, seams, testability, and SOLID design.

### Inputs

```text
changed code files
tests
architecture docs
machine contracts
```

### Instructions

```text
1. Check SRP: one reason to change per machine/module.
2. Check OCP: extension through new machines/contracts, not shell prose rewrites.
3. Check DIP: shell wrappers depend on stable Python CLI/contracts.
4. Check ISP: narrow contracts and small interfaces.
5. Check testability: behavior/contract tests instead of brittle string tests.
6. Identify refactor risks and contract violations.
```

### Outputs

```text
solid_review.json
solid_review.md
```

### Introspection questions

```text
- Did I review design seams, not just style?
- Did I identify concrete contract/test impacts?
- Did I avoid rewriting unrelated code?
- Did I preserve existing working behavior or explain breakage?
```

---

# Handoff-generation agent

## 12. Handoff Docs Generator Agent

### Goal

Generate architecture, product, and governance handoff docs from reviewed evidence.

### Inputs

```text
architecture_review.json/md
product_review.json/md
governance_review.json/md
role_review_summary.json/md
feature_dependency_graph.json/md
constitution_update_plan.json/md
spec_build_plan.json/md
speckit_input_manifest.json/md
target_spec_work_order.json/md
```

### Instructions

```text
1. Use role-review outputs as primary judgment artifacts.
2. Use other sync artifacts as supporting context.
3. Do not create new decisions.
4. Do not hide blocking issues.
5. Include source artifacts and evidence references.
6. Mark missing inputs clearly.
```

### Outputs

```text
architecture_handoff.json
architecture_handoff.md
product_handoff.json
product_handoff.md
governance_handoff.json
governance_handoff.md
```

### Introspection questions

```text
- Did I generate from reviewed evidence rather than inventing?
- Did I include missing artifact warnings?
- Did I preserve blocking issues?
- Did I avoid approving the handoff myself?
```

---

# SpecKit readiness judge

## 13. SpecKit Readiness Judge Agent

### Goal

Confirm whether all required assets exist and the system can safely report `READY_FOR_SPECKIT_TEST`.

### Inputs

```text
all required assets
role_review_summary.json/md
speckit_prework_quality_review.json/md
speckit_prework_approval_decision.json
machine_result.json/md
```

### Instructions

```text
1. Verify all required artifacts exist.
2. Verify role reviews pass or are explicitly accepted with rationale.
3. Verify source HLD was not modified.
4. Verify SpecKit was not invoked yet.
5. Verify final approval decision exists.
6. Return READY only if all gates pass.
```

### Outputs

```text
speckit_readiness_report.json
speckit_readiness_report.md
```

### Introspection questions

```text
- Did I verify every required artifact?
- Did I check role-review status?
- Did I check final approval?
- Did I avoid invoking SpecKit?
- Did I distinguish ready-to-test from already-tested?
```

---

# Minimum production path

The minimum production path before `READY_FOR_SPECKIT_TEST` is:

```text
Raw HLD Scan Agent
Architecture Reviewer Subagent
Product Reviewer Subagent
Governance Reviewer Subagent
Handoff Docs Generator Agent
SpecKit Readiness Judge Agent
```

The optional specialist subagents can be added when flagged by the first scan or required by a reviewer.

## Production rule

If `HLDSPEC_ROLE_REVIEWS=on`, the workflow must not reach `READY_FOR_SPECKIT_TEST` unless these exist and pass:

```text
architecture_review.json/md
product_review.json/md
governance_review.json/md
role_review_summary.json/md
```

## Test/local rule

If `HLDSPEC_ROLE_REVIEWS=local`, the workflow may proceed only as a dry run with heuristic evidence.

If `HLDSPEC_ROLE_REVIEWS=off`, the workflow is tests-only and must not be used to claim production readiness.
