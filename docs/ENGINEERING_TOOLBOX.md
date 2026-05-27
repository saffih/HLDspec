# Engineering Toolbox

## Purpose

The Engineering Toolbox is HLDspec's reusable engineering doctrine for target
software. It helps target agents build software that is simple, flexible,
testable, observable, and safe to evolve without turning every run into an
architecture textbook.

The toolbox does not replace the HLD. The HLD says what the product should be.
The toolbox provides selected guidance for how to build it safely.

## Core rule

Mention principles by default. Expand only when a choice is unclear, risky,
tool-specific, or requires gate enforcement.

HLDspec must not copy the whole toolbox into every target. It selects only the
guidance needed for the current target, feature, phase, or risk.

## Terminology

- **Engineering Toolbox**: the global reusable catalog of principles and tool
  cards.
- **Engineering Principle**: a stable rule for healthy software, such as keeping
  business logic outside HTTP handlers or using contracts at boundaries.
- **Toolbox Card**: an opinionated implementation pattern with use conditions,
  safe recipe, tests, observability, risks, and gate flags.
- **Principle Mention**: the shortest form of selected guidance. It names the
  principle without copying the full card.
- **Selected Guidance**: target-specific guidance with trigger, evidence,
  required tests, and enforcement expectation.
- **Full Card Expansion**: the complete Toolbox Card text. Use only when risk or
  ambiguity justifies the context cost.
- **Engineering Selection**: machine-readable selected principles/cards for a
  target or phase.
- **Engineering Guidelines**: generated human-readable guidance derived from the
  Engineering Selection and included in the source package.
- **Engineering Decision**: append-only record of selected defaults, upgrades,
  overrides, rejected options, and exceptions.

## Guidance levels

### Level 1 - Principle Mention

Use when the principle is obvious and low-risk.

Example:

```text
Keep business logic outside HTTP handlers, controllers, framework containers, and
database adapters.
```

### Level 2 - Selected Guidance

Use when the principle affects the current target or phase and needs evidence or
tests.

Example:

```text
Orders are shared mutable records, so use revision-based optimistic updates and
prove stale updates do not overwrite newer changes.
```

### Level 3 - Full Toolbox Card

Use when a choice is risky, tool-specific, easy to get wrong, or gate-enforced.

Example:

```text
concurrency.optimistic_revision
- add a revision/version column
- update with WHERE id = ? AND revision = ?
- affected rows = 0 means conflict/reload/merge
- test two actors reading the same revision
```

## Artifact layout

Global catalog:

```text
docs/
  ENGINEERING_TOOLBOX.md
  engineering_toolbox/
    cards/
      api-http-json.md
      data-schema.md
      concurrency-optimistic-revision.md
```

Target selection and decision state:

```text
target/.hldspec/engineering/
  selection.json
  decisions.jsonl
```

Source package guidance:

```text
target/.hldspec/source_package/
  engineering_guidelines.md
```

Do not create duplicate human-readable engineering guidance files. The target
markdown guidance lives in `engineering_guidelines.md`; the selected machine
truth lives in `selection.json`.

## P0 cards

P0 proves the enforcement loop with three cards only.

### api.http_json

Default to simple HTTP + JSON with explicit DTOs/contracts and a small endpoint
surface. Use OpenAPI or JSON Schema when a client boundary, multi-client API, or
public API exists. Do not default to hypermedia/HATEOAS unless runtime-discovered
transitions are a real product need.

### data.schema_discipline

Use stable primary keys. Use foreign keys where database-enforced integrity
matters. Use unique constraints for business uniqueness. Add indexes for named
query paths, joins, ordering, pagination, or uniqueness; do not add speculative
indexes. Use JSON columns only for truly flexible or raw payload-shaped data; if
a JSON field becomes queried, constrained, joined, or business-critical, promote
it to typed schema.

### concurrency.optimistic_revision

Default to optimistic revision updates for shared mutable records:

```sql
UPDATE table_name
SET field = ?, revision = revision + 1
WHERE id = ? AND revision = ?;
```

If affected rows is `0`, treat it as conflict, reload, merge, or retry according
to a declared policy. Do not default to broad locking or `SELECT FOR UPDATE`.
Locks are a narrow exception for short critical sections where optimistic
conflict handling is not acceptable.

## Enforcement loop

P0 is complete only when this loop is proven:

```text
selected card
  -> generated engineering_guidelines.md
  -> target AGENTS / runner prompt requirement
  -> implementation or phase-report evidence
  -> gate blocks missing evidence
  -> gate passes with evidence
```

The catalog itself is not the product. The selected, enforced target guidance is
the product behavior.

## Gate flags

Mark ACTION or block when:

- selected guidance has no trigger or target evidence
- risky tool upgrade has no tests, observability, or rollback path
- implementation uses an unselected risky pattern
- behavior changes without a provisional source-truth delta
- mutable shared writes lack optimistic revision or explicit single-writer rule
- API boundary lacks DTO/schema/contract strategy
- cache exists without owner, TTL, invalidation, stale-read tolerance, and
  fallback
- schema/index/foreign-key/JSON choice has no reason
- selected card requirements are absent from tests or reports

## Relationship to constitution

Stable principles may be proposed for the target constitution. Feature-specific
or phase-specific choices should stay in engineering selection, spec inputs,
prompts, reports, or provisional change records.

The constitution should not become a toolbox dump.
