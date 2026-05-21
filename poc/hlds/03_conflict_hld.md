# POC Conflict HLD

## HLD-001 - Governance

HLD-ID: HLD-001
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: target constitution
HLD-VERIFY: source-of-truth rules are captured before generation

The HLD is the source of truth.

## HLD-002 - Push Sync Ownership

HLD-ID: HLD-002
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 002
HLD-RESOURCES: processing ownership
HLD-VERIFY: sync ownership is resolved before generation

This section CONFLICTS_WITH REF HLD-003.

Approach A says the producer owns sync orchestration.

## HLD-003 - Pull Sync Ownership

HLD-ID: HLD-003
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: 003
HLD-RESOURCES: processing ownership
HLD-VERIFY: sync ownership is resolved before generation

This section CONFLICTS_WITH REF HLD-002.

Approach B says the consumer owns sync orchestration.
