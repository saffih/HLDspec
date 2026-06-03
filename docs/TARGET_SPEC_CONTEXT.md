# Legacy Target Spec Context Rule

Status: **legacy terminology / compatibility reference**. Current HLDspec
prepares bounded SpecKit prework and Run Cards; it must not manually create final
SpecKit specs. Treat "target spec" language here as the older name for a bounded
SpecKit evidence context, not as permission for HLDspec to write final specs.

## Core rule

A target spec is not created from one HLD section.

A target spec is created from:

```text
Spec Build Plan entry
+ explicitly related full HLD Sections
+ required refs
+ relevant normal refs
+ related API/data/performance/recovery constraints
```

## Correct model

```text
HLD Sections
-> HLD Map
-> Spec Build Plan
-> planned spec references related HLD Sections
-> target-spec context selects full related HLD evidence
-> one focused Target Spec
```

## Wrong models

Do not use:

```text
one HLD Section -> one Spec
```

Do not use:

```text
Section Card -> Spec
```

Do not use:

```text
whole HLD -> Spec
```

## Section Cards

Section Cards may be added later as routing aids.

They are useful for:

- reducing context before planning
- deciding which full HLD sections to fetch
- showing key aspects quickly
- helping RunSkeptic spotlights choose evidence

They are not source evidence for final SpecKit prework or run-card context.

The full related HLD Sections remain the source evidence.

## Required bounded SpecKit context package

When a compatibility `--target-spec` path exists, it should build a bounded
evidence package containing:

- Spec Build Plan entry
- full source HLD Sections listed for the planned spec
- required refs
- relevant normal refs
- API/interface sections when applicable
- data/state sections when applicable
- performance/memory sections when applicable
- reliability/failure-recovery sections when applicable
- target SpecKit Constitution context when applicable
- existing related specs only when needed and bounded

## RunSkeptic stop conditions

Stop with `CONFLICT` when:

- the Spec Build Plan does not name source HLD Sections
- required refs are missing
- API/interface ownership is unclear
- data/state ownership is unclear
- performance/memory constraints are referenced but unavailable
- failure/recovery behavior is referenced but unavailable
- the bounded SpecKit context boundary depends on evidence not loaded
- Section Cards are being used as replacement source evidence

## Current boundary

This repo currently supports the read-only first-run cycle and Spec Build Plan review.

Do not continue to SpecKit prework until the plan review is clean and explicitly
accepted.
