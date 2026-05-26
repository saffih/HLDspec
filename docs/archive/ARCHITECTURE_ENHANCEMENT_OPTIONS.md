# HLDspec Architecture Enhancement Options

## Purpose

This document is a product and architecture planning note. It does not change
the runtime flow, generated artifacts, or any SpecKit constitution file.

Goal: make HLDspec simpler, more robust, and stable when the source HLD leaves
important design details unspecified.

The core product question is:

> Can HLDspec complete a design responsibly when the HLD is incomplete, without
> inventing architecture or silently making human-owned decisions?

The answer should be yes, but only if the system separates deterministic
analysis, explicit options, human checkpoints, and SpecKit-owned outputs.

## Product Outcome

HLDspec should behave like a senior architecture judge:

- identify what is known from the HLD
- extract the smallest useful design units
- expose missing source-of-truth, ownership, contract, and sequencing choices
- propose options with tradeoffs
- stop at human-owned decisions
- prepare high-quality SpecKit input after approval
- never hand-roll final specs or implementation

The user experience should be:

1. Run one command.
2. See the current checkpoint and why it exists.
3. Answer only real decisions.
4. Get bounded SpecKit-ready packages.
5. Preserve a clear audit trail of what changed and who approved it.

## Current Stress Points

These are the instability patterns observed during the refactor work:

| Stress point | Product risk |
|---|---|
| Shell scripts still encode workflow decisions | The visible command path can diverge from `ProjectMachine`. |
| Plan-green semantics exist in multiple places | One path can advance while another path blocks. |
| Artifact freshness is partial | Stale artifacts can pass gates if inputs live outside `.specify/sync`. |
| Markdown can look like control state | A report phrase can accidentally become a gate contract. |
| Legacy target-spec language remains in compatibility paths | Agents can misread old wording as current permission. |
| HLDs omit ownership or contract details | Agents may invent missing source-of-truth or update timing. |

## Target Shape

Keep the architecture boring and explicit:

```text
HLD input
  -> deterministic extraction
  -> artifact contracts and freshness checks
  -> state-machine gates
  -> option packets for human decisions
  -> approved SpecKit prework
  -> SpecKit proxy execution
```

The runtime should have five stable seams:

| Seam | Responsibility |
|---|---|
| `ProjectMachine` | Owns workflow order and next checkpoint. |
| Artifact contract registry | Defines schema, producer, consumers, inputs, freshness, validator. |
| Validator plugins | Decide whether an artifact is complete enough to consume. |
| Ports/adapters | Isolate shell, SpecKit, agents, git, and filesystem concerns. |
| Event log | Records irreversible facts and approval provenance. |

## Design Rule For Unspecified Architecture

When the HLD leaves a design decision unspecified, HLDspec must classify it
instead of filling the gap silently.

| Classification | Meaning | Allowed behavior |
|---|---|---|
| Known | Direct HLD evidence exists. | Use it and cite the source section. |
| Inferred | Strong evidence exists but wording is indirect. | Mark as inference and keep confidence visible. |
| Option | Multiple valid designs exist. | Present options with tradeoffs. |
| Human-owned | Source-of-truth, API, security, data ownership, dependency, split/merge, rollout, or implementation decision. | Stop at checkpoint. |
| SpecKit-owned | Final spec, plan, tasks, implementation output. | Delegate only through the SpecKit proxy after approval. |

This keeps the system productive without crossing into invention.

## Recommended Enhancements

### 1. Single Gate Semantics

Create one shared function for plan-green and prework-green checks.

Current issue: `review_spec_build_plan.py`, `build_hldspec_state.py`,
`project_continue.sh`, and `SpecBuildPlanMachine` can express similar checks
independently.

Target:

```text
hldspec/gates.py
  plan_gate_status(plan, review_text) -> GateDecision
  prework_gate_status(review, dossier, approval) -> GateDecision
```

The shell adapter should never reimplement these rules.

### 2. Artifact Contract Registry As Runtime API

Extend the current registry so every controlling artifact declares:

- `schema_version`
- producer
- consumers
- required fields
- input artifacts
- whether inputs are workspace-root, sync-local, or project-root
- freshness rule
- validator function
- promotion requirements

This makes stale and partial artifacts fail closed.

### 3. Event Log Before More Automation

Before adding more agent execution, record important transitions as events:

- checkpoint presented
- human answer recorded
- artifact rebuilt
- gate passed or failed
- artifact promoted
- SpecKit phase started or completed

Events should be append-only. Markdown reports should be renderings, not state.

### 4. Ports Before More Shell Migration

Introduce ports gradually:

| Port | First useful adapter |
|---|---|
| `ArtifactStorePort` | local filesystem `.specify/sync` |
| `SpecKitPort` | existing proxy script |
| `HumanDecisionPort` | queue JSON and reply parser |
| `AgentExecutionPort` | bounded junior agent packet runner |
| `GitPort` | preflight and status checks |

This keeps implementation simple while making future replacement possible.

### 5. Option Packets For Human-Owned Decisions

For incomplete HLD areas, generate an option packet instead of one question at a
time.

Each packet should include:

- decision ID
- source HLD evidence
- missing fact
- options
- tradeoffs
- recommended default if safe
- blast radius
- test/staging validation expectations
- whether the decision affects the constitution

This is the product-manager layer: it makes decision work cheap and explicit.

## Constitution-Impacting Options

These options may require changes to a project SpecKit constitution. HLDspec
must not edit the constitution directly; it should generate a constitution
update plan and wait for approval.

| Option | Constitution impact | Recommendation |
|---|---|---|
| Gate ownership rule | Constitution may state that workflow gates are machine-owned and shell scripts are adapters only. | Adopt for HLDspec itself; expose as optional for downstream projects. |
| Artifact contract rule | Constitution may require controlling artifacts to declare schema, producer, consumers, freshness, and validation. | Adopt when projects have generated artifacts that influence specs or implementation. |
| No invention rule | Constitution may require unknown source-of-truth, API, security, data ownership, dependency, and rollout decisions to become checkpoints. | Strongly adopt. This is the main safety rule. |
| Ports/adapters rule | Constitution may require external systems to be accessed through named interfaces. | Adopt for systems with CLI, agent, git, database, API, or filesystem boundaries. |
| Event log rule | Constitution may require important decisions and promotions to be recorded as immutable events. | Adopt for multi-agent or high-risk projects. |
| Testability rule | Constitution may require seams, deterministic controls, and unit/component/integration intent for every planned spec. | Strongly adopt. |
| Staging rule | Constitution may require non-disruptive validation, rollback, and smoke checks before user-impacting rollout. | Strongly adopt for production systems. |
| UI testability rule | Constitution may require selectors, accessibility hooks, and critical journey automation when UI exists. | Adopt when UI exists. |
| Data ownership rule | Constitution may require every mutable data object to name source-of-truth, mutation owner, and update timing. | Strongly adopt. |
| SpecKit ownership rule | Constitution may state that SpecKit owns final specs, plans, tasks, and implementation artifacts after approved prework. | Adopt for HLDspec-driven workflows. |

## Constitution Decision Packet Template

When an HLDspec run discovers a constitution-impacting decision, generate:

```text
Decision ID:
Source HLD sections:
Current constitution rule:
Missing or conflicting rule:
Options:
Recommended option:
Why:
Blast radius:
Artifacts affected:
Validation required:
Human approval:
```

This template keeps constitution changes deliberate and reviewable.

## Migration Plan

Use small reversible slices:

1. Fix shared gate semantics so all paths agree.
2. Extend artifact freshness to support workspace-root inputs.
3. Add event logging for checkpoint presentation and human answers.
4. Move one shell policy branch at a time into `ProjectMachine`.
5. Add option-packet generation for source-of-truth and data ownership gaps.
6. Generate constitution update plans from option packets, but do not apply them.

## Open Product Decisions

| Decision | Options | Default |
|---|---|---|
| How much autonomy should HLDspec have when architecture is unspecified? | stop always; infer with confidence; propose default for low-risk only | infer only with visible confidence; stop on human-owned domains |
| Should constitution recommendations be generated for every project? | always; only when gaps are detected; opt-in | only when gaps are detected |
| Should shell migration be fast or incremental? | rewrite runner; one branch at a time | one branch at a time |
| Should event log be mandatory before SpecKit proxy execution? | yes; no; only high-risk | yes for high-risk and multi-agent runs |
| Should validator plugins block or warn by default? | block by default; warn by default; severity-based | severity-based |

## Acceptance Criteria

This architecture direction is ready to implement when:

- shared gate semantics have one source of truth
- artifact contracts can validate sync-local and workspace-root inputs
- shell scripts no longer decide gate state
- human-owned decisions are represented as option packets
- constitution-impacting decisions are explicit and never applied silently
- full `tests/`, `tests_v2/`, and ready gate remain green

