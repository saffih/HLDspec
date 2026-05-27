# HLDspec

HLDspec is an agent-first control layer for turning one full HLD into a controlled SpecKit workflow.

HLDspec does not replace SpecKit. HLDspec preserves product truth, prepares evidence, validates source references, gates decisions, and hands SpecKit bounded work. SpecKit owns the final specs, plans, tasks, and implementation artifacts.

## Current model

```text
One full HLD
-> one HLDspec source package
-> one SpecKit workspace
-> one complete specify -> plan -> tasks -> analyze sequence
-> many approved implementation slices
```

The HLD is not split into partial source-truth documents. The full HLD remains the product source of truth. Slicing controls implementation scope, not product truth.

## Ownership boundaries

HLDspec owns:

```text
.hldspec/
.hldspec/source_package/
```

SpecKit owns:

```text
.specify/
specs/
implementation artifacts
```

HLDspec may mirror selected source-package files into:

```text
.specify/source/
```

`.specify/source/` is generated read-only context for SpecKit. It is not the source of truth.

## Source package

The source package is the HLDspec-owned handoff bundle. It contains the full HLD, stable HLD anchors, the HLD reference map, the single SpecKit input, and execution-control policy.

Key source-package artifacts include:

```text
.hldspec/source_package/HLD.md
.hldspec/source_package/HLD.marked.md
.hldspec/source_package/hld_reference_map.json
.hldspec/source_package/speckit_single_spec_input.md
```

Generated mirrors may appear under:

```text
.specify/source/
```

## SpecKit sequence

HLDspec instructs the SpecKit proxy to run the full SpecKit sequence before implementation:

```text
1. /speckit.specify
2. /speckit.clarify, if needed
3. /speckit.plan
4. /speckit.tasks
5. /speckit.analyze
6. /speckit.implement only after explicit approval
```

The specify, plan, tasks, and analyze phases are complete-product phases. They are not run separately for infrastructure, business logic, API, CLI, or UI.

## Slice-controlled implementation

Implementation is controlled slice by slice after the complete SpecKit task graph exists.

Canonical slices:

```text
FOUNDATION
WALKING_SKELETON
DOMAIN_MODEL
CONTRACTS
BUSINESS_LOGIC
PERSISTENCE
API
CLI
UI
INTEGRATION_HARDENING
```

Each implementation pass must name:

```text
selected slice
allowed task IDs
allowed files
forbidden files
HLD anchors in scope
deferred anchors
focused tests
prior-slice regression tests
stop condition
report format
```

No raw all-task implementation is allowed unless explicitly approved.

See:

```text
docs/SPECKIT_SLICE_CONTROL.md
```

## Testing and gates

A slice is complete only when:

```text
focused tests pass
prior-slice regression passes
anchor coverage is updated
no uncited product behavior was added
phase report is written
no stop condition is triggered
```

HLDspec gates continuation using source-package validation, stale-anchor checks, unsupported-claim checks, RunSkeptic status, consultant review, and human approval when required.

## User-facing workflow

The public facade is intentionally small:

```text
start
status
review
continue
diff
doctor
```

Agents should use the facade and generated run cards rather than calling low-level scripts directly.

## Documentation map

```text
AGENTS.md                              agent bootstrap and hard rules
docs/HLDSPEC_TERMINOLOGY_AND_FLOW.md   canonical architecture and terminology
docs/SPECKIT_PROXY_PROTOCOL.md         HLDspec-to-SpecKit handoff protocol
docs/SPECKIT_SLICE_CONTROL.md          technical slice-control model
docs/TEST_STRATEGY_V2.md               test strategy
docs/DOCS_INDEX.md                     documentation index
```

## Legacy files

Some older root-level scripts and docs may still exist for compatibility or history. The current model is defined by the documents above.
