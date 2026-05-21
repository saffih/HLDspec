# HLDspec Terminology

made by AI

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
| **Skeptic Framework** | The real framework from `https://github.com/saffih/skeptic/blob/main/skeptic.md`. |
| **Beskeptic Cycle** | HLDspec's operational use of the real Skeptic Framework on one workflow step and selected Key Aspects. |
| **Key Aspect** | Canonical concern being checked, such as `spec_boundary`, `api_contract`, `performance`, or `resume_invalidation`. |
| **Skeptic Spotlight** | The exact artifact part, question, dependency, interface, assumption, or conflict being examined in a Beskeptic Cycle. |
| **Cycle Record** | Compact record of evidence, confidence, decision, recommendation, verification, and outcome from a Beskeptic Cycle. |
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
