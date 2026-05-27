# HLDspec Canonical Flow

> Canonical system model and terminology:
> [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md). This doc
> details the pipeline steps; the canonical doc wins on any terminology conflict.

This document defines the current canonical HLDspec flow after the SpecKit ownership correction.

## Core principle

HLDspec prepares and reviews the data needed by SpecKit. It does not replace SpecKit.

```text
HLDspec owns:
- HLD ingestion and safe working copy
- HLD conversion checkpoints
- HLD map and section classification
- Spec Build Plan
- SpecKit prework extraction
- constitution update plan
- feature dependency graph
- SpecKit invocation queue
- SpecKit proxy dossier
- Skeptic quality review
- human checkpoints and rebuild loops

SpecKit owns:
- .specify/memory/constitution.md updates after approval
- specs/<feature>/spec.md
- checklists/requirements.md
- clarify flow
- plan.md
- research.md
- data-model.md
- contracts/
- quickstart.md
- tasks.md
- implementation phase
```

## Canonical flow

```text
1. Source HLD
2. Safe .hldspec-first-run workspace
3. Raw-HLD format report
4. HLD conversion plan
5. HLD conversion decision queue
6. Human answers split/keep decisions
7. Working HLD conversion
8. HLD map
9. HLD section classification
10. Spec Build Plan
11. Spec Build Plan Review
12. Spec Build Plan Decision Queue if blocked
13. SpecKit prework artifacts:
    - speckit_input_manifest
    - speckit_invocation_queue
    - constitution_update_plan
    - feature_dependency_graph
14. SpecKit prework quality review
15. SpecKit proxy dossier
16. Human approval of constitution/dependency/first-feature case
17. SpecKit proxy subagent invokes SpecKit in sequence
18. SpecKit specify
19. SpecKit clarify if needed
20. SpecKit plan
21. SpecKit tasks
22. Implement only after explicit approval
```

## Current safe checkpoint after a green plan gate

When the Spec Build Plan is green, the next checkpoint is not "target spec generation".

The next checkpoint is:

```text
SpecKit prework approval gate
```

The judge/orchestrator must present:

```text
speckit_prework_quality_review.md
speckit_proxy_dossier.md
speckit_input_manifest.md
speckit_invocation_queue.md
constitution_update_plan.md
feature_dependency_graph.md
```

The human approves, modifies, decomposes, fixes constitution, or rebuilds the dependency graph.

## Deprecated wording

Do not use these as the current canonical next step:

```text
target-spec generation is allowed
write target specs
create specs manually from HLDspec
```

Those phrases came from the earlier design before the SpecKit ownership boundary was corrected.

## Legacy/fallback artifacts

These artifacts may still exist for compatibility or inspection:

```text
target_spec_work_order.md/json
spec_branch_queue.md/json
```

They are not the controlling checkpoint when SpecKit is available. Their generated markdown must explicitly say `Legacy/supporting when SpecKit is available`.

The controlling handoff is:

```text
speckit_invocation_queue.md/json
speckit_proxy_dossier.md/json
speckit_prework_quality_review.md/json
```

## RunSkeptic rule

If HLDspec artifacts disagree about the next step, classify as:

```text
CONFLICT: workflow source-of-truth conflict
```

Resolve by updating the runner and docs to this canonical flow before continuing.
