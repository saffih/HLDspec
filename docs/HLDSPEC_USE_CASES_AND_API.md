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

The canonical command surface is defined in
[`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) (HLDspec
Product Facade). This section maps those commands to use cases and must stay in
sync with it.

### Current public facade

These commands are current product behavior:

| Command | Status | Purpose |
|---|---|---|
| `hldspec start` | current | Prepare or resume an agent-first target session. |
| `hldspec status` | current | Show recorded target session state and next action. |
| `hldspec review` | current | Show human-relevant review/checkpoint files. |
| `hldspec continue` | current | Run ProjectMachine to the next safe checkpoint through the new target layout. |
| `hldspec diff` | current | Compare current source hash against the recorded target session hash. |
| `hldspec doctor` | current | Check required docs/tools and target session files. |
| `hldspec speckit-doctor` | current | Check target-level SpecKit readiness and branch/manual workflow state. |
| `hldspec operator-state` | current | Show readiness-first Operator State, SpecKit lifecycle state when phase artifacts exist, and the evidence-backed next safe action. |
| `hldspec speckit-state` | current | Alias of `operator-state`. |

### Future product commands

These names are valid future product concepts, but are not current public behavior until implemented and tested:

| Command | Status | Purpose |
|---|---|---|
| `hldspec interview` | future | Collect missing source, target, intent, constraints, and approval expectations. |
| `hldspec prework` | future | Generate use-case/API map, packages, graph, queue, context packs, and review material. |
| `hldspec speckit` | future | Delegate exactly one approved SpecKit phase from bounded evidence. |
| `hldspec pause` | future | Record an explicit user pause/checkpoint without advancing machines. |

### Legacy/debug commands

These names and direct scripts are not the normal product workflow:

| Command or path | Status | Purpose |
|---|---|---|
| `hldspec run` | legacy/debug | Older runner name; do not document as current product behavior. |
| `hldspec speckit-proxy` | legacy/debug | Older proxy naming; future product command should be `hldspec speckit`. |
| direct low-level scripts | legacy/debug | Maintainer/debug tools used by agents or maintainers, not the user workflow. |

Rule: use cases are canonical; command names are an interface mapping. A command must be marked current, future, or legacy/debug before docs can advertise it as product behavior.


## Complete use-case catalog target

Every use case below is part of the product contract. Current commands may not implement every use case yet, but each use case must have a stable owner, artifacts, stop condition, and test expectation before deeper orchestration or validator work proceeds.

### UC-001 start with no source yet

- Trigger: user starts HLDspec without a source path.
- Preconditions: no reliable source HLD/resource path is known.
- Command/API: future `hldspec interview`; current agent session may ask in chat before writing durable state.
- Artifacts read: none required.
- Artifacts written: none before target is known; after target is known, current `start` writes `target/.hldspec/interview_answers.json` and `.md`.
- Stop condition: source and target are identified, or a human decision is required.
- Human decision: choose source and target.
- Tests expected: no durable files are written before target is known.

### UC-002 start with source only

- Trigger: source HLD/resource path is provided, target is absent.
- Preconditions: source exists and is readable; target is not known.
- Command/API: current `hldspec start` requires target; future interview path should help choose target.
- Artifacts read: source HLD/resources.
- Artifacts written: none until target is chosen; once target is supplied, current `start` writes `target/.hldspec/interview_answers.json` and `.md`.
- Stop condition: target chosen or created.
- Human decision: approve target workspace path.
- Tests expected: source remains read-only; no hidden state is written outside target.

### UC-003 create new target from raw HLD

- Trigger: source and target are provided; target has no HLDspec session state.
- Preconditions: source exists; target does not exist or is safe to create.
- Command/API: current `hldspec start --source <source> --target <target>`.
- Artifacts read: source HLD/resources.
- Artifacts written: `target/targetHLD/raw/HLD.raw.md`, `target/targetHLD/HLD.md`, `target/.hldspec/agent_session.json`, `target/.hldspec/interview_answers.json`, `target/.hldspec/interview_answers.md`, `target/.hldspec/agent_tool_manifest.md`, `target/prompts/agent/START_HLDSPEC_AGENT.md`.
- Stop condition: target session prepared and next safe action printed.
- Human decision: none unless target already contains conflicting state.
- Tests expected: target layout matches `TargetWorkspaceAdapter(layout="new")`; source remains unchanged; no durable product artifacts are written outside target.

### UC-004 adopt existing target without HLDspec state

- Trigger: target exists but lacks `target/.hldspec/agent_session.json`.
- Preconditions: target is a directory; source is known.
- Command/API: current `hldspec start` auto-detects adopt mode.
- Artifacts read: existing target tree, source HLD/resources.
- Artifacts written: target session manifest and prompts only after safety checks.
- Stop condition: adoption checkpoint or prepared session.
- Human decision: required if existing target contains ambiguous or conflicting SpecKit/HLDspec artifacts.
- Tests expected: existing target files are not overwritten silently.

### UC-005 resume existing HLDspec target

- Trigger: target has a session manifest.
- Preconditions: `target/.hldspec/agent_session.json` exists.
- Command/API: current `hldspec status`, `hldspec review`, `hldspec continue`.
- Artifacts read: target session, state, review files, checkpoint files.
- Artifacts written: event log and newly generated artifacts only when `continue` runs.
- Stop condition: next safe checkpoint.
- Human decision: required when checkpoint or conflict exists.
- Tests expected: resume does not skip gates.

### UC-006 update after source/resources changed

- Trigger: current source hash differs from recorded source hash.
- Preconditions: previous target session exists.
- Command/API: current `hldspec diff`; future update workflow.
- Artifacts read: source, recorded manifest, artifact hashes.
- Artifacts written: stale report and affected rebuild plan.
- Stop condition: affected outputs rebuilt or human review required.
- Human decision: required if source change affects constitution, feature boundaries, or package order.
- Tests expected: stale artifacts are detected and unaffected artifacts are not rebuilt.

### UC-007 upgrade after HLDspec guidance/templates changed

- Trigger: HLDspec guidance, templates, or validator rules changed.
- Preconditions: target session exists.
- Command/API: future upgrade workflow.
- Artifacts read: guidance fingerprints, generated prompts, generated docs.
- Artifacts written: upgrade plan and refreshed generated guidance where approved.
- Stop condition: upgrade review or refreshed artifacts.
- Human decision: required if upgrade changes build order, constitution, or package boundaries.
- Tests expected: stale prompts/guidance are detected.

### UC-008 review checkpoint and capture human decisions

- Trigger: checkpoint or review files exist.
- Preconditions: target session exists.
- Command/API: current `hldspec review`; future decision capture API.
- Artifacts read: review files, decision queues, conflicts.
- Artifacts written: machine-readable decision artifact after user answers.
- Stop condition: decision recorded or still awaiting human answer.
- Human decision: answer checkpoint questions.
- Tests expected: decisions are recorded in a controlled artifact and are replayable.

### UC-009 continue after approval

- Trigger: user requests progress after required approvals.
- Preconditions: target session exists; no unresolved blocking conflict for the next step.
- Command/API: current `hldspec continue`.
- Artifacts read: session, approval records, state, queues, working HLD.
- Artifacts written: event log, mirrored sync artifacts, next generated artifacts.
- Stop condition: next safe checkpoint or pipeline completion.
- Human decision: required if approval is missing or conflict is found.
- Tests expected: `continue` invokes ProjectMachine with `workspace_layout="new"`.

### UC-010 handle unresolved conflict

- Trigger: conflict artifact exists or a machine returns conflict/blocking status.
- Preconditions: target session exists.
- Command/API: current/future conflict gate through `status`, `review`, and `continue`.
- Artifacts read: conflict artifacts, review reports, state.
- Artifacts written: no further generated product artifacts until resolved; optional handoff note.
- Stop condition: human decision required.
- Human decision: select resolution or defer.
- Tests expected: promotion and continuation are blocked when unresolved conflict exists.

### UC-011 generate use-case/API map

- Trigger: working HLD is converted or sufficient raw evidence exists.
- Preconditions: HLD evidence exists in target.
- Command/API: future `hldspec prework`.
- Artifacts read: working HLD, interview answers, source/resource manifest.
- Artifacts written: `target/.hldspec/hld_usecase_api_map.json` and `.md`.
- Stop condition: map review ready.
- Human decision: required for unclear buildable/context-only sections.
- Tests expected: context-only sections are not selected as first buildable features.

### UC-012 generate package/dependency/invocation queue

- Trigger: use-case/API map is ready.
- Preconditions: buildable/context-only classification exists.
- Command/API: future `hldspec prework`.
- Artifacts read: use-case/API map, working HLD, constraints, existing specs if any.
- Artifacts written: spec packages, dependency graph, invocation queue.
- Stop condition: queue review ready.
- Human decision: required if graph/order conflicts exist.
- Tests expected: dependency graph and invocation queue match.

### UC-013 generate context packs and bounded prompts

- Trigger: package/dependency queue is approved or ready for review.
- Preconditions: package id and allowed evidence are known.
- Command/API: future prompt generation inside `hldspec prework`.
- Artifacts read: package plan, allowed evidence list, constitution rules, backend choices.
- Artifacts written: `target/.hldspec/context_packs/`, `allowed_evidence.json`, `forbidden_reads.md`, package prompts.
- Stop condition: prompt review ready.
- Human decision: required if prompt needs broad evidence or uncertain scope.
- Tests expected: prompt validator rejects broad-read prompts.

Implementation note: `scripts/build_speckit_context_prompts.py` provides the first deterministic generator and validator for this use case. It remains a maintainer/debug tool until wired into a public guarded flow.

### UC-014 delegate one SpecKit phase

- Trigger: approved package and phase are available.
- Preconditions: bounded dossier exists; human approval permits the phase.
- Command/API: future `hldspec speckit`.
- Artifacts read: bounded dossier, phase prompt, allowed evidence.
- Artifacts written: SpecKit-owned phase outputs and HLDspec execution log.
- Stop condition: one phase completes or asks a question.
- Human decision: required before implementation and for unknowns.
- Tests expected: exactly one phase is delegated.

### UC-015 answer SpecKit clarification from evidence only

- Trigger: SpecKit asks a clarification question.
- Preconditions: question is tied to one package/phase.
- Command/API: future evidence-answering path under `hldspec speckit`.
- Artifacts read: allowed evidence, question record, package context.
- Artifacts written: answer record with evidence references or escalation record.
- Stop condition: answer recorded or escalated.
- Human decision: required when evidence is missing or ambiguous.
- Tests expected: answers cite allowed evidence and never guess unknowns.

### UC-016 escalate unknown SpecKit question to human

- Trigger: SpecKit question cannot be answered from allowed evidence.
- Preconditions: allowed evidence was checked.
- Command/API: future escalation path.
- Artifacts read: question, evidence manifest, package context.
- Artifacts written: human question queue and checkpoint report.
- Stop condition: human decision required.
- Human decision: answer, defer, or update source/target intent.
- Tests expected: unknowns are escalated rather than guessed.

### UC-017 verify SpecKit output and RunSkeptic findings

- Trigger: SpecKit phase output exists.
- Preconditions: phase completed or produced reviewable artifacts.
- Command/API: future verify path.
- Artifacts read: SpecKit output, package prompt, expected outputs, RunSkeptic rules.
- Artifacts written: verification report with PASS/ACTION/CONFLICT.
- Stop condition: verified, action required, or conflict requires human decision.
- Human decision: required for ACTION/CONFLICT promotion blockers.
- Tests expected: unresolved findings block promotion.

### UC-018 detect stale artifacts and rebuild affected outputs

- Trigger: source, guidance, package graph, or SpecKit output changed.
- Preconditions: fingerprints exist.
- Command/API: future stale detection.
- Artifacts read: input manifest, artifact hashes, dependency graph.
- Artifacts written: stale report and rebuild plan.
- Stop condition: affected rebuild plan ready or complete.
- Human decision: required when rebuild changes approved decisions.
- Tests expected: stale dependency test covers source and guidance changes.

### UC-019 brownfield target with existing specs

- Trigger: target already contains SpecKit specs or implementation artifacts.
- Preconditions: target exists and contains existing work.
- Command/API: future brownfield/adopt path.
- Artifacts read: existing specs, implementation evidence, target state.
- Artifacts written: drift report and adoption plan.
- Stop condition: human review.
- Human decision: approve adoption, preserve, or isolate existing work.
- Tests expected: no overwrite without approval.

### UC-020 user-requested pause before continuing

- Trigger: user requests no further progress after current point.
- Preconditions: any active session.
- Command/API: future `hldspec pause`; current behavior should respect explicit human checkpoint.
- Artifacts read: current session/state.
- Artifacts written: pause marker or handoff note.
- Stop condition: action withheld until user resumes.
- Human decision: resume or change direction later.
- Tests expected: no further machine action after pause marker.

### UC-021 development handoff between agents/models

- Trigger: repo-development work transfers to another agent/model/session.
- Preconditions: local repo state is known.
- Command/API: current development handoff generator.
- Artifacts read: git status, backlog, handoff protocol, recent tests.
- Artifacts written: `.hldspec-dev/handoff/HANDOFF.md` and `.json`.
- Stop condition: handoff packet generated.
- Human decision: approve next implementation step if needed.
- Tests expected: handoff includes canonical backlog and handoff pointers.

### UC-022 maintainer/debug direct-script run

- Trigger: maintainer/debugging need.
- Preconditions: user/agent intentionally leaves product facade.
- Command/API: legacy/debug direct scripts.
- Artifacts read: script-specific inputs.
- Artifacts written: script-specific outputs, preferably under target-owned or debug-owned paths.
- Stop condition: script exits and output is reviewed.
- Human decision: required before promoting debug output into product flow.
- Tests expected: direct scripts are documented as non-product workflow.

### UC-023 completed history / merged-work audit

- Trigger: target contains completed or merged history that may already satisfy planned work.
- Preconditions: merge evidence or completed specs exist.
- Command/API: future audit path.
- Artifacts read: git history, completed specs, merge records, target status.
- Artifacts written: completed-work audit and classification.
- Stop condition: history classified as done, stale, or needs review.
- Human decision: required when evidence is insufficient.
- Tests expected: no live work is inferred from stale docs alone.

## Rewrite council scenarios - 2026-05-27

These scenarios capture the evolved product target from the single-HLD rewrite
discussion. They are evaluation cases: future implementation work should be able
to say which scenarios it addresses, which it defers, and which gate proves it.

### RUC-001 single-HLD source package setup

- User story: user provides a source HLD and a target repo/workspace.
- Expected behavior: HLDspec creates the authoritative package under
  `target/.hldspec/source_package/` and only materializes derived runner-facing
  files under `.specify/source/`.
- Success means: canonical source truth is HLDspec-owned; SpecKit-owned
  directories are not hand-authored by HLDspec.
- Blocks if: source package writes final SpecKit specs manually or treats
  `.specify/source/` as the authority.

### RUC-002 HLD shaping before SpecKit

- User story: user wants to clarify, mark, or improve an HLD before execution.
- Expected behavior: HLDspec marks anchors, records open questions, proposes HLD
  patches, and stops for source-truth decisions before SpecKit phases.
- Success means: the original source HLD remains read-only; the workspace copy
  and source package carry approved changes.
- Blocks if: the agent silently answers checkpoint questions or modifies source
  truth without approval.

### RUC-003 single SpecKit input by default, layered only by real boundaries

- User story: one coherent HLD should become one SpecKit-ready input unless
  meaningful boundaries justify layers.
- Expected behavior: HLDspec defaults to one single-spec input; optional layers
  are based on source-of-truth, architecture, dependency, deployable value, or
  testability boundaries.
- Success means: no size-based bundle slicing; graph/queue parity remains for
  layered paths.
- Blocks if: the tool reintroduces many-spec bundles as the default or deletes
  the layered dependency model entirely.

### RUC-004 bounded runner and consultant phase execution

- User story: an implementation or SpecKit phase is delegated to a target agent.
- Expected behavior: runner does one bounded phase and stops; consultant is
  review-only; the controller owns continuation and gate decisions.
- Success means: Context Receipt, Phase Report, validation result, RunSkeptic
  result, Consultant result, and next safe action are machine-readable enough for
  `continue` to block or pass.
- Blocks if: a runner continues recursively, self-approves, or proceeds without
  required evidence.

### RUC-005 HLD-side stale artifact detection

- User story: approved HLD/source-package content changes after derived artifacts
  already exist.
- Expected behavior: HLDspec compares anchor/hash changes against derived
  citations and classifies SAFE, REVIEW, REGENERATE, or BLOCK.
- Success means: cited changed/deleted anchors block or force regeneration;
  uncited changes require review instead of silent PASS.
- Blocks if: stale derived prompts/spec inputs continue after source anchors
  changed.

### RUC-006 ordinary target-repo "make X happen" workflow

- User story: user is working inside the target repo and says, "I want X; make
  it happen."
- Expected behavior: the target agent may edit code, but if behavior,
  architecture, API, data shape, UI flow, ownership, or rollout changes, it must
  record a provisional source-truth delta before claiming done.
- Success means: request, interpretation, target diff, source-truth impact,
  evidence, and next decision are captured in target-owned HLDspec artifacts.
- Blocks if: code behavior changes while the HLD/source package has no
  corresponding provisional delta.

### RUC-007 POC and experiment promotion

- User story: user asks for a POC or says to try an implementation direction.
- Expected behavior: the POC is tracked as provisional truth, not invisible
  throwaway work and not canonical product truth.
- Success means: controller can accept, revise, reject, split, or continue the
  POC; only accepted deltas are promoted into the canonical source package.
- Blocks if: prototype code becomes the only record of product behavior.

### RUC-008 generated target agent instructions

- User story: a future target-agent session starts from the target repo without
  the original chat context.
- Expected behavior: HLDspec installs or generates target instructions such as
  `AGENTS.generated.md` that explain source-truth delta rules, selected
  engineering guidance, gate expectations, and forbidden promotion behavior.
- Success means: ordinary target agents know to update provisional deltas and
  report source-truth impact.
- Blocks if: the workflow depends on hidden chat memory.

### RUC-009 Engineering Toolbox P0

- User story: HLDspec should help target agents build healthy software without
  dumping a full architecture textbook into every prompt.
- Expected behavior: mention principles by default; expand into selected
  guidance only when risk, ambiguity, or tool-specific enforcement requires it;
  expand full Toolbox Cards only for risky or non-obvious choices.
- Success means: selected card -> generated guidance -> target prompt/report
  requirement -> gate blocks missing evidence -> gate passes with evidence.
- Blocks if: the toolbox is only documentation or if unrelated cards bloat every
  target prompt.

### RUC-010 API, data, and concurrency safety defaults

- User story: common implementation choices should have safe boring defaults.
- Expected behavior: simple HTTP+JSON APIs use explicit DTO/contracts; schemas
  use deliberate primary keys, foreign keys, unique constraints, indexes, JSON
  columns, and migrations; shared mutable records default to optimistic revision
  updates rather than broad locking.
- Success means: risky choices have triggers, required tests, observability, and
  rollback/simplification paths.
- Blocks if: blind last-write-wins updates, speculative indexes, business-critical
  JSON blobs, or API contracts without DTO/schema strategy pass unchecked.

### RUC-011 source-truth promotion remains controller-owned

- User story: agents can propose changes, but source truth must not be promoted
  accidentally.
- Expected behavior: target agents write provisional deltas only; the controller
  or human-owned gate promotes accepted deltas into the canonical source package.
- Success means: provisional ledger is never treated as a second canonical HLD.
- Blocks if: target agents directly mutate approved source-package truth or
  generated SpecKit artifacts as a shortcut.

### RUC-012 brownfield and existing-work reconciliation

- User story: target repo may already have code, specs, partial implementation,
  or merge history.
- Expected behavior: HLDspec audits existing work, classifies it as usable,
  stale, conflicting, or requiring review, and avoids overwriting it silently.
- Success means: adoption plan identifies what source truth already covers and
  what code has drifted beyond recorded truth.
- Blocks if: HLDspec assumes a clean target or infers completion from stale docs.

## Core user scenarios

### Scenario 1 - First project run from a raw HLD

User says:

```text
HLDspec ./Flow-System-HLD.md
```

Expected behavior:

```text
1. Discover project root.
2. Create or reuse the target workspace and HLDspec control plane.
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

This section is historical compatibility guidance. The current public facade is
the "Current command surface status" section above, backed by
`HLDSPEC_TERMINOLOGY_AND_FLOW.md`.

### legacy/debug hldspec run

Legacy/debug command:

```bash
scripts/hldspec_run.sh <source-HLD.md>
```

Behavior:

```text
- legacy natural project runner
- creates/reuses .hldspec-first-run
- stops at safe checkpoints
- never modifies source HLD without approval
```

### legacy/debug hldspec status

Legacy/debug wrapper:

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
HLD_READY
HLD_READY_WITH_ACTIONS
HLD_BLOCKED
HLD_READINESS_HLD_MISSING
HLD_CONVERSION_DECISIONS
CONVERSION_CHECKPOINT
CONVERSION_READY_TO_APPLY
WORKING_HLD_CONVERTED
AGENT_SESSION_PREPARED
INIT_PREREQS_READY
INIT_PREREQS_BLOCKED
BUILD_LOOP_INIT_BLOCKED
WORKSPACE_INITIALIZED
MIRROR_SYNCED
SOURCE_FRESHNESS_BLOCKED
SPECKIT_APPROVAL_GATE_BLOCKED
FIRST_RUN_PENDING
SPEC_BUILD_PLAN_CHECKPOINT
SPEC_BUILD_PLAN_BLOCKED
SPEC_BUILD_PLAN_GREEN
SPECKIT_PREWORK_MISSING
SPECKIT_PREWORK_REWORK
SPECKIT_PREWORK_REWORK_REQUIRED
SPECKIT_PREWORK_RUNSKEPTIC_REWORK
SPECKIT_PREWORK_ENGINEERING_GUIDANCE_MISSING
SPECKIT_PREWORK_ENGINEERING_GUIDANCE_REWORK
SPECKIT_PREWORK_STALE
SPECKIT_PREWORK_READY_FOR_APPROVAL
SPECKIT_PREWORK_APPROVAL_GATE
SPECKIT_PREWORK_APPROVED
READY_FOR_SPECIFY
SPECIFY_ACTIVE
PLAN_ACTIVE
TASKS_ACTIVE
ANALYZE_READY
```

## Existing-sensitive greenfield discovery

Before HLDspec treats a target as new, it inspects existing target state and
writes read-only control reports:

```text
target/.hldspec/sync/target_discovery_report.json
target/.hldspec/sync/target_discovery_report.md
target/.hldspec/sync/phase_ledger.json
target/.hldspec/sync/phase_ledger.md
```

Classifications:

```text
NEW_GREENFIELD          empty or missing target; use target-prep path
PREPARED_GREENFIELD     trusted HLDspec source-package/session lineage exists
INITIALIZED_GREENFIELD  real .specify/memory exists with HLDspec lineage
PHASED_GREENFIELD       specs/* phase artifacts exist with HLDspec lineage
EVOLVING_GREENFIELD     implementation-slice or implementation lineage exists
UNKNOWN_BROWNFIELD      existing code/artifacts without trusted HLDspec lineage
```

`UNKNOWN_BROWNFIELD` blocks this slice: arbitrary brownfield adoption is not
implemented. Known-origin HLDspec/SpecKit continuation is managed greenfield
evolution and must not recommend wipe/rebuild by default.

Phase wake rules:

```text
DONE       artifact exists and HLDspec validation/report evidence exists
ACTIVE     partial phase artifact exists
UNVERIFIED artifact exists without trusted evidence
STALE      source HLD hash or artifact hash changed
BLOCKED    unsafe to continue
```

File existence alone must not mean DONE. `continue` may use discovery as a
blocker/reporting input only; it must not run SpecKit or product implementation
from discovery alone. HLDspec orchestration runs from the HLDspec repo, while
later product work runs from the target repo only after an approved handoff.

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
