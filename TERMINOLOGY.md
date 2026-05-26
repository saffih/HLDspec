# HLDspec Terminology

Use these terms consistently in docs, prompts, reports, logs, code comments, and agent instructions.

## Source-of-truth terms

| Term | Meaning |
|---|---|
| **HLDspec Operating Rules** | Rules for this HLDspec repo. They live in `AGENTS.md`, `TERMINOLOGY.md`, `HLD_FORMAT.md`, `HLD_GENERATION.md`, and README guidance. |
| **Target Workspace** | The external project/workspace being processed by HLDspec. |
| **Target Spec Kit Constitution** | `.specify/memory/constitution.md` inside the target workspace. It is generated or updated by `hld_spec_sync.py`; it is not the HLDspec repo's own constitution. |
| **Constitution Action** | Planned action for the target Spec Kit Constitution: `create`, `update`, `no_change`, or `conflict`. |

## Framework terms

| Term | Meaning |
|---|---|
| **Skeptic Framework** | The real framework from `https://github.com/saffih/skeptic/blob/main/skeptic.md`; current `skeptic.md` is the runtime source of truth. |
| **RunSkeptic** | Formal invocation string for applying the Skeptic Framework. |
| **RunSkeptic review** | HLDspec's operational use of the real Skeptic Framework on one workflow step and selected Key Aspects. |
| **Key Aspect** | Canonical concern being checked, such as `spec_boundary`, `api_contract`, `performance`, or `resume_invalidation`. |
| **Skeptic Spotlight** | The exact artifact part, question, dependency, interface, assumption, or conflict being examined in a RunSkeptic review. |
| **Cycle Record** | Compact record of evidence, confidence, decision, recommendation, verification, and outcome from a RunSkeptic review. |
| **User Escalation** | Structured user handoff when evidence cannot resolve a conflict. |

## Architecture terms

| Term | Meaning |
|---|---|
| **Raw HLD** | Original user-provided HLD before HLDspec formatting. Usually preserved as `HLD.raw.md`. |
| **Canonical HLD** | Working `HLD.md` treated as design source of truth. |
| **HLD Section** | Design source unit using `## HLD-xxx - Title` and `HLD-*` metadata. |
| **Spec** | Capability-level specification. Not the same as an HLD Section. |
| **Spec Boundary** | Responsibility and scope of one spec. |
| **Spec Build Plan** | Read-only bottom-up plan of planned specs, dependencies, HLD sources, coverage expectations, integration expectations, target constitution action, and conflicts. |
| **Target Spec** | The single spec selected for a create/update run. |
| **Coverage Gate** | Check that HLD anchors and related refs are covered by the correct specs. |
| **Integration Gate** | Check that cross-spec relationships, API contracts, producer/consumer edges, data/state ownership, and failure behavior are explicit. |
| **API Contract** | Explicit interface agreement between producer and consumer specs/components. |
| **Integration Gap** | Missing, implicit, stale, or conflicting integration/API contract. |
| **Section Card** | Compact routing/context summary for one HLD Section. Used to decide what full source evidence to fetch. It is not a replacement for the HLD Section text. |
| **Target Spec Context** | Bounded evidence package used to build one target spec: Spec Build Plan entry, full related HLD Sections, required refs, relevant normal refs, and related constraints. |

## Key Aspect groups

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

Integration/API:

- `integration`
- `api_contract`
- `producer_consumer`
- `dependency_order`
- `data_state_ownership`

Runtime/resource:

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

## Decision terminology

Use real Skeptic decisions:

- `FIX`
- `DECOMPOSE`
- `CONFLICT`

Use final outcomes:

- `HANDLED`
- `CONFLICT`

Use Razor read-only diagnostic terms only for Razor:

- `PASS`
- `ACTION`
- `CONFLICT`

Use spec-specific labels only as recommendations under a Skeptic decision:

- `KEEP_SPEC`
- `FIX_SPEC`
- `SPLIT_SPEC`
- `MERGE_SPEC`
- `DEFER_SPEC`

## SpecKit proxy terms

| Term | Meaning |
|---|---|
| **SpecKit Proxy Protocol** | HLDspec protocol for delegating approved SpecKit work to a bounded subagent that uses SpecKit as a prepared client. |
| **SpecKit Proxy Subagent** | Bounded subagent that invokes SpecKit phases using the proxy dossier, answers questions from evidence when safe, and escalates human-owned decisions. |
| **SpecKit Proxy Dossier** | Generated evidence package containing selected feature, constitution context, dependency context, SpecKit input, question policy, and allowed evidence sources. |
| **Answer From Evidence** | Question-answering mode where the proxy answers from HLD/prework/approved constitution evidence. |
| **Answer From Reasonable Default** | Question-answering mode used only for safe non-architecture defaults. |
| **Escalate To Human** | Question-answering mode for architecture, constitution, API, source-of-truth, data ownership, dependency, scope, split/merge, or implementation decisions. |

## Flow status terms

| Term | Meaning |
|---|---|
| **Canonical HLDspec Flow** | Current approved flow documented in `docs/CANONICAL_FLOW.md`. |
| **SpecKit Prework Approval Gate** | Checkpoint after a green Spec Build Plan where the human reviews constitution, dependency graph, invocation queue, quality review, and proxy dossier before SpecKit is invoked. |
| **Legacy Target Work Order** | Earlier HLDspec artifact for manual target-spec generation. It is not the controlling checkpoint when SpecKit is available. |



## Runtime document usage terms

| Term | Meaning |
|---|---|
| **Runtime Document Usage** | Rule that reusable guidance docs must be converted into target-specific artifacts, gates, and prompts during an HLDspec run. |
| **Backend Technology Recommendation** | Short approved backend toolbox with one default and one upgrade per category, plus explicit triggers for upgrades. |
| **Tool Upgrade** | Selection of a stronger backend/tooling option than the default; requires trigger, tests, observability, rollback path, and RunSkeptic result. |
| **Design Principle Selection** | Target-specific subset of reusable design guidance selected for the current HLDspec run. |

## Software design principle terms

| Term | Meaning |
|---|---|
| **Software Design Principles** | Reusable HLDspec design knowledge in `docs/SOFTWARE_DESIGN_PRINCIPLES.md`; used to generate HLDs, target constitutions, spec packages, and prompts. |
| **Cost/Context Economy** | Principle requiring the smallest sufficient context, weakest sufficient model, narrowest sufficient prompt, and bounded evidence for delegated work. |
| **Persistent Loop** | Durable, resumable workflow pattern using explicit state, idempotent steps, stale detection, stop conditions, and retry/escalation rules. |
| **Message-Bus Style** | Event, queue, or bus-based architecture used only when it resolves real coupling, retry, fan-out, audit, or async workflow forces. |
| **Design for Testability** | Principle requiring explicit seams, deterministic controls, test doubles, fixtures, and unit/integration/end-to-end test paths before implementation. |
| **Accessibility Requirement** | User-facing quality requirement covering keyboard access, screen reader labels, contrast, focus order, semantic structure, and clear errors where relevant. |

## Target workspace terms

| Term | Meaning |
|---|---|
| **target/** | Generated target workspace for one app or domain. Contains HLDspec planning, SpecKit workspace files, prompts, and SpecKit-owned specs. |
| **targetHLD/** | HLD workspace inside `target/`. Contains raw HLD evidence, working HLD, extracted sections, inventory, grouping, and HLD-to-package mapping. |
| **target/targetHLD/raw/** | Read-only copied or snapshotted source evidence. |
| **target/targetHLD/HLD.md** | Working canonical HLD used by HLDspec for grouping, constitution signals, dependency planning, and package generation. |
| **Spec Package** | Bite-size SpecKit-ready package derived from one or more HLD groups. It is planning input, not a final SpecKit spec. |
| **Delegation Prompt** | Bounded prompt generated by HLDspec for one agent, one feature package, and one SpecKit phase. |
| **Mediator Prompt** | Prompt used by a mediator agent to instruct or supervise a target agent such as Devin, Claude, or Codex. |

## State and package terms

| Term | Meaning |
|---|---|
| **HLDspec State** | Current machine-readable and human-readable summary of workflow stage, checkpoint, next allowed actions, and controlling artifacts. |
| **SpecKit Prework Package** | Main human-facing review package that combines constitution case, dependency case, first-feature case, Skeptic findings, feedback impact rules, and approval question. |
| **Controlling Artifact** | Artifact the judge/orchestrator should use as the primary source for the current checkpoint. |
| **Supporting Artifact** | Artifact used as evidence or detail behind the controlling artifact. |
| **Legacy/Supporting Artifact** | Older or compatibility artifact that may be present but does not control the current workflow when SpecKit is available. |

## Context tailoring terms

| Term | Meaning |
|---|---|
| **Context Tailoring** | Giving each task only the context, role, goals, rules, evidence, and output schema needed for that task. |
| **Bloat Guard** | Rule that prevents overloading agents with unnecessary context, authority, reasoning level, or historical discussion. |
| **Cost-Fit Delegation** | Choosing the lowest-cost agent and smallest context package that can reliably complete a task. |
| **Weakest Sufficient Agent** | The least capable/cheapest agent that can safely complete the task. |
| **Smallest Sufficient Context** | The minimum file set, section set, or evidence bundle needed to complete the task. |
| **Strictest Sufficient Prompt** | The narrowest prompt that still lets the agent complete the task correctly. |
| **Task Context Package** | The bounded package given to a delegated agent: task, level, personality, context, forbidden actions, output schema, stop condition, and escalation rule. |
| **Nested Delegation** | A subagent delegating a narrower, lower-authority task to another subagent, then verifying the result. |

## Model routing and agent assignment terms

| Term | Meaning |
|---|---|
| **Model Routing Policy** | Judge-owned rule set that chooses the weakest sufficient model tier for creation work and the strongest necessary model tier for promotion gates. |
| **Model Tier** | Abstract capability/cost class assigned to a task packet. HLDspec uses `MODEL_ROUTINE`, `MODEL_STRONG`, and `MODEL_CRITICAL` rather than vendor-specific model names. |
| **MODEL_ROUTINE** | Low-cost model tier for deterministic summaries, bounded extraction, checklist shaping, and evidence lookup with no decision authority. |
| **MODEL_STRONG** | Strong model tier for product drafting, SpecKit `specify`, `tasks`, bounded implementation, and synthesis where mistakes are recoverable at the next gate. |
| **MODEL_CRITICAL** | Strongest model tier for judge decisions, constitution, architecture/data/API planning, RunSkeptic/analyze, implementation with high blast radius, merge/history audit, and artifact promotion. |
| **Assigned Agent Name** | Stable role label recorded in task packets so the judge can route work consistently without relying on prose memory. |
| **Promotion Model Rule** | Rule that cheap agents may propose artifacts, but only a `MODEL_CRITICAL` judge/reviewer may promote artifacts across gates. |
| **SpecKit Phase Agent** | Named bounded agent assigned to exactly one SpecKit phase of one feature, with a model tier, allowed files, stop boundary, and output schema. |
| **Human Decision Owner** | The human who owns product, architecture, source-of-truth, split/merge, dependency, constitution, and implementation-approval decisions that evidence cannot safely answer. |

## Standard assigned agent names

| Assigned Agent Name | Default Model Tier | Responsibility |
|---|---|---|
| **HLDspec Judge Orchestrator** | `MODEL_CRITICAL` | Owns state, gates, promotion, human checkpoints, model routing, and final decisions. |
| **Product Lead Reviewer** | `MODEL_STRONG` | Synthesizes use cases, user stories, acceptance criteria, product scope, and product open questions. |
| **Architect Lead Reviewer** | `MODEL_CRITICAL` | Synthesizes API/data/source-of-truth boundaries, dependency order, constitution impact, and architecture open questions. |
| **Junior Product Extractor** | `MODEL_ROUTINE` | Extracts bounded product evidence; cannot decide or promote. |
| **Junior Architect Extractor** | `MODEL_ROUTINE` | Extracts bounded architecture evidence; cannot decide or promote. |
| **SpecKit Specify Proxy** | `MODEL_STRONG` | Runs `specify` for one approved feature and stops after specification artifacts. |
| **SpecKit Clarify Proxy** | `MODEL_STRONG` | Answers only evidence-backed clarification questions and escalates human-owned decisions. |
| **SpecKit Plan Proxy** | `MODEL_CRITICAL` | Runs `plan` for one approved feature because plan owns architecture, data model, contracts, and implementation approach. |
| **SpecKit Tasks Proxy** | `MODEL_STRONG` | Runs `tasks` for one approved feature and stops before implementation. |
| **SpecKit Analyze Reviewer** | `MODEL_CRITICAL` | Runs read-only consistency/adversarial review before implementation. |
| **SpecKit Implementer** | `MODEL_STRONG` or `MODEL_CRITICAL` | Implements approved tasks; use `MODEL_CRITICAL` for cross-cutting, security, data, or architecture changes. |
| **Merge History Auditor** | `MODEL_CRITICAL` | Verifies normal merge evidence and classifies specs as `MERGED_DONE` history. |
