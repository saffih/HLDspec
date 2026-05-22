# HLDspec V2 Handoff Docs

made by AI

## Purpose

HLDspec V2 now generates consolidated handoff documents before the SpecKit approval gate.

Generated files:

```text
workspace/firstrun/.specify/sync/architecture_handoff.md
workspace/firstrun/.specify/sync/product_handoff.md
```

## Architecture handoff

Contains:

```text
- source artifact list
- plan quality and gate decision
- architecture / dependency focus
- planned specs with architecture flags
- excerpts from dependency graph, constitution plan, spec build review, and proxy dossier
```

## Product handoff

Contains:

```text
- source artifact list
- product / SpecKit readiness summary
- planned specs
- product correctness guard
- excerpts from input manifest, invocation queue, work order, and prework package
```

## Safety

```text
- docs are generated from existing sync artifacts
- docs do not invoke SpecKit
- docs do not modify source HLD
- docs do not implement app code
```

## Flow review command

```bash
cat ~/code/flow/.hldspec-v2-flow-test/workspace/firstrun/.specify/sync/architecture_handoff.md
cat ~/code/flow/.hldspec-v2-flow-test/workspace/firstrun/.specify/sync/product_handoff.md
```
