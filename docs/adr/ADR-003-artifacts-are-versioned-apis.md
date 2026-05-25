# ADR-003: Artifacts are versioned APIs

**Status:** ACCEPTED  
**Date:** 2026-05-25  

## Context

HLDspec produces JSON artifacts that are consumed by downstream machines, scripts, and operators. Historically these were treated as files with expected fields — consumers assumed the fields they needed would be present. There was no mechanism to detect when a producer changed its output shape and a consumer had not been updated. Silent schema drift caused subtle failures that were hard to diagnose.

When an artifact is consumed by multiple machines and scripts, an undeclared schema change breaks consumers in non-obvious ways. The problem compounds when artifacts are persisted in workspaces across runs: an artifact written by an older producer may be read by a newer consumer, or vice versa.

## Decision

Every artifact produced by HLDspec must declare a `schema_version` field. Consumers validate the version before reading and reject artifacts with unexpected versions. Version changes require explicit migration or a documented breaking change.

Artifact schemas are the API contract between producers and consumers within HLDspec. They are treated with the same discipline as a public API: additive changes are non-breaking, field removals or renames are breaking changes, and breaking changes require a version bump.

## Consequences

- Silent schema changes will fail validators rather than producing silently wrong output.
- Consumers must handle version mismatches explicitly — either by refusing to proceed or by running a migration.
- Workspace artifacts written by old versions of HLDspec may be rejected by new consumers until migrated.
- Adding a required field to an existing artifact is a breaking change and requires a schema_version bump.
- The `prework_contracts.py` validators are the canonical enforcement point for schema version checks.
