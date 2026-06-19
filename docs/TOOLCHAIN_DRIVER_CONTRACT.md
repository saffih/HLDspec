# Toolchain Driver Contract

## Purpose

General Toolchain Driver v0 is a read-only navigation and reporting layer for
Journey 3. It distinguishes the process navigator from the selected toolchain
helper, then checks durable evidence before proposing the next safe action.

## Vocabulary

| Term | Meaning |
|---|---|
| Driver | Watches state, checks sequence/rules/evidence, performs reality checks, and proposes the next safe step. |
| Helper | Toolchain-specific map, rules, commands, and evidence contract. Only `speckit` is operational today. |
| DriverActor | Who is driving: `human` or `system`. |
| DriverAuthority | How far the driver may act: `GUIDE_ONLY`, `PROPOSE_COMMAND`, `EXECUTE_WITH_APPROVAL`, or `AUTONOMOUS_WITH_GUARDS`. |

## v0 Scope

The v0 driver is report-only:

- It reads the selected/effective helper through `hldspec.helper_selection`.
- It reads installed runtime identity from `.hldspec/runtime/MANIFEST.json`.
- It resolves external-state controller paths through the existing control-path helpers.
- It reports missing, stale, legacy, or mismatched runtime identity as `ACTION`.
- It marks `AUTONOMOUS_WITH_GUARDS` as not allowed.

## Forbidden In v0

- Do not run SpecKit silently.
- Do not edit SpecKit-owned artifacts directly.
- Do not mutate product files.
- Do not repair or regenerate files as a side effect of status reporting.
- Do not commit, push, merge, or approve completion without explicit approval.
- Do not add new operational helpers through this driver slice.

## Evidence Rules

A driver `PASS` requires the effective helper identity to match the installed
runtime helper identity. A missing runtime manifest, a legacy manifest without
helper identity, or a helper mismatch must surface as `ACTION` with a concrete
next safe action. The driver report must show the evidence it used rather than
claiming readiness implicitly.
