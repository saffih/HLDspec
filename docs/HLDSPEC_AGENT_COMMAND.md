# HLDspec Agent Command Protocol

made by AI

## Purpose

This document defines the full agent-led HLDspec command.

The local scripts are tools. They do not replace the judge/orchestrator.

```text
hldspec_run.sh = local tool runner
HLDspec <path-to-HLD> = agent-led protocol that drives the tool runner
```

## Canonical trigger

When the user says:

```text
HLDspec <path-to-HLD>
```

the agent must act as the HLDspec judge/orchestrator.

The user should not need to remember scripts, artifact paths, or stage names.

## Repositories

Default local repositories:

```text
HLDspec repo: ~/code/HLDspec
Target project repo: current project, for example ~/code/flow
Target HLD: path supplied by the user
Reference repo: https://github.com/saffih/HLDspec
```

Use the local HLDspec repo as authoritative. GitHub is reference only because local may have unpushed changes.

## No-credit readiness first

Before spending paid agent, SpecKit, Codex, Devin, Claude, or implementation credits, run the local readiness gate:

```bash
cd ~/code/HLDspec
uv run python scripts/hldspec_ready_gate.py \
  --repo . \
  --output-dir .hldspec-ready-gate \
  --fail-on-not-ready
```

If the gate reports:

```text
NOT_READY
```

stop. Fix HLDspec first.

If the gate reports:

```text
READY_FOR_PAID_AGENT_TEST
```

the agent may continue to one bounded target-HLD test.

## Tool runner step

Run the local HLDspec tool runner only after readiness passes:

```bash
cd <target-project-repo>
~/code/HLDspec/scripts/hldspec_run.sh <path-to-HLD>
```

The runner must not be treated as the whole process. It creates or continues the local workspace and stops at a safe checkpoint.

The runner must not:

```text
- run agents
- invoke SpecKit
- create final specs manually
- implement app code
- modify the source HLD directly
```

## Workspace rule

The source HLD is read-only unless the user explicitly approves source edits.

The working copy is:

```text
.hldspec-first-run/HLD.md
```

All generated/checkpoint artifacts live under:

```text
.hldspec-first-run/
```

The judge may edit only the working copy when marking/converting raw HLD content.

## Artifact discovery order

After each tool run, inspect the current controlling artifacts in this order.

### Raw-HLD conversion checkpoint

```text
.hldspec-first-run/.specify/sync/hld_conversion_decision_queue.md
.hldspec-first-run/.specify/sync/raw_hld_marking_plan.md
.hldspec-first-run/RAW_HLD_MARKING_PROMPT.md
.hldspec-first-run/HLD.md
```

### Converted/prework checkpoint

```text
.hldspec-first-run/firstrun/.specify/sync/hldspec_state.md
.hldspec-first-run/firstrun/.specify/sync/speckit_prework_package.md
.hldspec-first-run/firstrun/.specify/sync/speckit_prework_quality_review.md
.hldspec-first-run/firstrun/.specify/sync/speckit_proxy_dossier.md
```

If the expected files do not exist, locate the earlier checkpoint and explain which artifact controls it.

## Agent-led raw HLD marking

Raw HLD conversion must not be mechanical.

When raw-HLD marking artifacts exist, the judge must use the marking plan to decide section metadata before conversion.

For each candidate section or small batch, use bounded subagents only when useful.

Required bounded perspectives:

```text
product_context
architecture
interface_contract
data_model
processing_behavior
governance_context
security
operations
```

Subagent names:

```text
Product Reviewer
Architecture Reviewer
Interface/API Reviewer
Data/State Reviewer
Processing Behavior Reviewer
Governance/Constitution Reviewer
Security Reviewer
Operations Reviewer
```

Each subagent receives only:

```text
- one candidate section or one small batch
- relevant prior decisions
- its perspective questions
- strict output schema
- forbidden actions
```

Subagents recommend. The judge decides.

## Subagent output schema

Each bounded subagent must return:

```text
perspective:
candidate_ids:
observed_evidence:
recommended_hld_role:
recommended_hld_risk:
spec_candidate: yes/no/unclear
constitution_candidate: yes/no/unclear
resources_or_interfaces:
dependencies:
conflicts:
split_keep_recommendation:
questions_for_human:
confidence: observed / inferred_risk / unknown
```

Rules:

```text
- Do not invent decisions.
- Use TBD when evidence is insufficient.
- Mark inferred risk separately from observed evidence.
- Ask only real checkpoint questions.
```

## Judge synthesis output

After subagent review, the judge decides for each candidate section:

```text
HLD-ID
HLD-ROLE
HLD-STATUS
HLD-RISK
HLD-SPECS
HLD-RESOURCES
HLD-VERIFY
REF
DEPENDS REF
CONFLICTS_WITH REF
split / keep
context-only / spec candidate / constitution candidate
```

The judge must explain:

```text
- what was marked
- why
- what evidence was used
- what remains TBD
- what user decision is required
```

## Product and architecture extraction

The judge must extract and preserve:

```text
- user stories
- use cases
- user journeys
- product goals
- acceptance criteria
- component responsibilities
- architecture boundaries
- interfaces/contracts
- data/source-of-truth ownership
- dependency order
- risks/conflicts
- constitution-worthy rules
```

## Constitution rules

Constitution/prework rules must be architecture-specific, not generic.

Each proposed constitution rule should include:

```text
rule:
rationale:
HLD evidence:
violation example:
SpecKit phase enforced:
affected artifacts:
open question:
```

## SpecKit boundary

HLDspec prepares. SpecKit creates.

HLDspec may prepare:

```text
hldspec_state.md
speckit_prework_package.md
speckit_input_manifest.md
speckit_invocation_queue.md
constitution_update_plan.md
feature_dependency_graph.md
speckit_prework_quality_review.md
speckit_proxy_dossier.md
```

SpecKit owns:

```text
spec.md
clarify
plan.md
tasks.md
implementation
```

Do not invoke SpecKit until the human explicitly approves the prework gate.

## Product-readiness gate

HLDspec is not ready for target work unless local fixtures prove:

```text
clean separated HLD -> FIX / KEEP_PLAN / 0 flagged specs
mixed API/data/processing HLD -> DECOMPOSE / SPLIT_PLANNED_SPEC
explicit CONFLICTS_WITH HLD -> CONFLICT / RESOLVE_CONFLICT
```

## User-facing checkpoint report

At every stop, the judge must report:

```text
1. current stage
2. current checkpoint
3. controlling artifacts
4. what was done
5. what is blocked
6. human decision needed
7. what will happen automatically after the answer
```

Do not ask for generic OK to continue. Ask only real checkpoint questions.

## Stop conditions

Stop immediately when:

```text
- readiness gate is NOT_READY
- source HLD edit would be required
- a real human decision is needed
- RunSkeptic produces CONFLICT
- SpecKit prework needs approval
- tests fail
- generated artifacts disagree about the current stage
```

## RunSkeptic rule

Use `RunSkeptic` as the formal trigger.

Before claiming RunSkeptic compliance:

```text
1. Read the actual current skeptic.md.
2. Apply the current recipe in order.
3. Do not use memory or summaries as substitutes.
4. Use exact categories from skeptic.md.
5. Separate observed evidence from inferred risk.
6. State unknowns, conflicts, and skipped areas.
```

## Ready outcome

The target state is:

```text
- local HLDspec readiness gate passes
- raw-HLD marking is operational
- product-readiness fixtures pass
- target HLD run stops at a clear checkpoint
- hldspec_state.md and speckit_prework_package.md orient the user
- no SpecKit invocation happens before explicit human approval
```

## Checkpoint renderer contract

Checkpoint messages are rendered by `scripts/render_hldspec_checkpoint.py`.

`project_continue.sh` is the state-machine/tool runner. It must not own long-form checkpoint UX text.

Every checkpoint render must include:

```text
- current checkpoint
- blocking reason
- human decision needed
- allowed options when applicable
- controlling artifacts
- what happens after the answer
- what is not modified or not invoked yet
```

