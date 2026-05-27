# HLDspec Architecture README

## Purpose

HLDspec turns a full HLD into a controlled SpecKit handoff. It does not replace SpecKit. It preserves product truth, prepares source-package evidence, creates bounded prompts and control artifacts, and gates continuation before implementation.

## Core idea

One full HLD becomes one full SpecKit source input. SpecKit should then run one specify, one plan, one tasks, and one analyze pass for the complete product. Implementation is not all-at-once by default. HLDspec controls many slice-controlled implementation passes after the full task graph exists.

```text
One full HLD
One source package
One specify, one plan, one tasks, one analyze
Many slice-controlled implementation passes
```

## Source of truth

The source HLD is product truth. HLDspec copies it into the target workspace and builds a source package from the working HLD copy.

Authoritative HLDspec-owned source package:

```text
target/.hldspec/source_package/
```

Generated SpecKit-readable mirror:

```text
target/.specify/source/
```

HLDspec authors the source package. The `.specify/source/` directory is a generated read-only mirror. Markdown files in the mirror carry a generated banner. Product truth should not be hand-authored in the mirror.

## Main artifacts

The source package contains:

```text
HLD.md
HLD.marked.md
hld_reference_map.json
speckit_single_spec_input.md
source_manifest.json
source_package.json
implementation_slicing_policy.md
implementation_slices.json
slice_test_policy.md
speckit_slice_execution_prompt.md
anchor_coverage_schema.json
speckit_runbook.md
runner_prompt.md
consultant_prompt.md
session_plan.json
subagent_packets/
```

## Anchor model

`HLD.marked.md` inserts stable markers before HLD sections:

```text
<!-- ANCHOR: HLD-001 -->
```

`hld_reference_map.json` maps each anchor to heading, title, role, risk, status, line range, and section hash. Derived artifacts must cite anchors so HLDspec can detect unsupported claims and stale output.

## SpecKit phase model

HLDspec should communicate with SpecKit as follows:

1. `specify`: use the full HLD-derived source input.
2. `plan`: produce a full product plan and organize it by implementation slices.
3. `tasks`: produce a full task graph; every task has slice, anchors, dependencies, expected files, tests, and MVP flag.
4. `analyze`: verify coverage, dependencies, anchors, and test completeness.
5. `implement`: do not run raw all-task implementation unless full implementation is explicitly approved. Normally, implement only the selected slice or selected task IDs.

## Implementation slices

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

The slices do not split product truth. They only scope execution. Every slice must account for HLD anchors as implemented, partially implemented, deferred, blocked, or not applicable.

## Testing rule

A slice is complete only when:

- focused tests for that slice pass
- prior-slice regression passes
- anchor coverage is updated
- no uncited product behavior was added
- `phase_report.json` is written
- `anchor_coverage.json` is written

## Agent control plane

HLDspec uses a bounded-subagent control plane:

```text
session_plan.json
subagent packets
context_receipt.json
phase_report.json
gate validator
```

The main controller owns continuation and gates. Target runners execute one bounded phase and stop. Consultants are review-only. Tmux is optional UI only and never source truth.

## Gates

Continuation may be blocked by missing context receipt, missing phase report, failed validation, stale anchors, unsupported claims, RunSkeptic ACTION/CONFLICT, missing required PASS, Consultant BLOCK, missing Consultant PASS, missing human approval, or unexpected dirty tree.

## Development rule

When changing HLDspec itself, local repo is authoritative. GitHub is only the sync target. Do not push unless explicitly instructed. A patch is incomplete until focused tests, related regressions, the full `tests_v2` suite, and `git diff --check` actually run.
