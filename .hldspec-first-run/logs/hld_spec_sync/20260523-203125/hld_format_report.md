# HLD Format Report

Source: `/Users/saffi/code/HLDspec/.hldspec-first-run/HLD.md`
Lines: 6455
Markdown headings detected: 343
Existing HLDspec headings: 0
Candidate major sections: 36

## Verdict

This HLD is not yet HLDspec-formatted. Convert major sections first; do not run full sync yet.

## Warnings

- HLD-009 candidate 'Component Deep-Dive' spans about 1680 lines; consider splitting before sync.
- HLD-010 candidate 'Component Interface Definitions' spans about 572 lines; consider splitting before sync.

## Detected headings

- line 1: level 1 [plain] Flow System - High-Level Design (HLD)
- line 23: level 2 [plain] IMPORTANT: Single Source of Truth
- line 62: level 4 [plain] Specification Alignment Plan
- line 86: level 2 [plain] Executive Summary
- line 90: level 3 [plain] Key Architectural Decisions
- line 101: level 2 [plain] CLI Entry Point
- line 144: level 2 [plain] Stakeholder Analysis
- line 146: level 3 [plain] Stakeholder Inventory
- line 152: level 3 [plain] Stakeholder Concerns
- line 163: level 3 [plain] Authority Levels
- line 173: level 3 [plain] core.md Governance (v2.8.3)
- line 189: level 3 [plain] Approval Criteria (v2.7)
- line 208: level 3 [plain] Success Criteria
- line 222: level 2 [plain] User Personas
- line 224: level 3 [plain] Single Persona: System Owner / Developer
- line 257: level 2 [plain] Business Case Foundation
- line 259: level 3 [plain] Business Objectives
- line 276: level 3 [plain] Job-to-be-Done
- line 294: level 3 [plain] Success Metrics
- line 322: level 3 [plain] Strategic Alignment
- line 356: level 2 [plain] User Stories
- line 358: level 3 [plain] Epic 1: Task Management
- line 382: level 3 [plain] Epic 2: AI Task Execution
- line 407: level 3 [plain] Epic 3: Reply Handling
- line 433: level 3 [plain] Epic 4: Session Management
- line 464: level 3 [plain] Epic 5: Reporting and Documentation
- line 490: level 3 [plain] Epic 6: Data Management
- line 516: level 3 [plain] Epic 7: Logging and Monitoring
- line 542: level 3 [plain] Epic 8: End-to-End Workflows
- line 660: level 2 [plain] System Architecture Overview
- line 749: level 2 [plain] Component Deep-Dive
- line 751: level 3 [plain] 1. TEA Architecture (Model-View-Update)
- line 753: level 4 [plain] Model (Centralized State)
- line 765: level 4 [plain] View (Pure Functions)
- line 774: level 4 [plain] Update (Event-Driven)
- line 782: level 3 [plain] 2. Flow Core Database API (Critical Safety Layer)
- line 786: level 4 [plain] Safety Mechanisms
- line 795: level 4 [plain] Critical Rule
- line 800: level 3 [plain] 3. AI Integration Layer (Delicate Integration Point)
- line 802: level 4 [plain] core.md - The AI Process Loop Code
- line 811: level 4 [plain] core.md Contract Invariants (CRITICAL)
- line 874: level 4 [plain] Reply Decision Criteria (Objective)
- line 932: level 4 [plain] core.md Error Recovery Paths
- line 956: level 4 [plain] 8-Step Process Loop (Corrected Implementation)
- line 971: level 4 [plain] Process Loop Exit Conditions
- line 993: level 4 [plain] Recipe System (Learnable Behavior)
- line 1002: level 4 [plain] Session Spawn and Execution
- line 1011: level 4 [plain] Logging Architecture Rationale
- line 1037: level 3 [plain] 4. Brain Architecture (core.md - The AI Process Controller)
- line 1039: level 4 [plain] Overview
- line 1050: level 4 [plain] Brain Responsibilities
- line 1080: level 4 [plain] Brain Structure and Content
- line 1101: level 4 [plain] Brain-System Interactions
- line 1174: level 4 [plain] Brain Contracts and Invariants
- line 1213: level 4 [plain] Brain Data Flow
- line 1261: level 4 [plain] Brain Lifecycle and Evolution
- line 1308: level 4 [plain] Brain Quality Assurance
- line 1343: level 4 [plain] Brain Integration Points
- line 1375: level 4 [plain] Brain Failure Modes
- line 1401: level 4 [plain] Brain Success Metrics
- line 1426: level 3 [plain] 5. Specification Hierarchy and Integration
- line 1439: level 4 [plain] HLD as Single Source of Truth
- line 1454: level 4 [plain] Specification Directory Structure
- line 1487: level 4 [plain] Specification Integration with HLD
- line 1552: level 4 [plain] Specification Maintenance
- line 1575: level 4 [plain] Cross-Reference Matrix
- line 1589: level 4 [plain] Quality Assurance for Specifications
- line 1605: level 4 [plain] Archive and Deprecated Specifications
- line 1623: level 4 [plain] Current Implementation Structure
- line 1664: level 4 [plain] Architecture Decision: HLD Architecture vs flow_loop.py
- line 1696: level 4 [plain] Session Status Values (Actually Implemented)
- line 1702: level 4 [plain] Task Status Values (Database Schema)
- line 1713: level 4 [plain] CLI Protocol (Current Implementation)
- line 1722: level 4 [plain] CLI Architecture (Nervous System Model)
- line 1822: level 4 [plain] Task Discovery
- line 1829: level 4 [plain] Status Notification
- line 1842: level 4 [plain] Report Notification (REQUIRED)
- line 1849: level 4 [plain] Session Management
- line 1854: level 4 [plain] Error Handling
- line 1862: level 3 [plain] 5. Automatic Sync Operations
- line 1866: level 4 [plain] Triggering
- line 1872: level 4 [plain] One-Way Projection
- line 1878: level 4 [plain] core.md Integration
- line 1883: level 4 [plain] Performance Targets
- line 1890: level 3 [plain] 6. Session Management
- line 1892: level 4 [plain] Implementation Status
- line 1898: level 4 [plain] Session Lifecycle
- line 1906: level 4 [plain] Session Limits
- line 1912: level 4 [plain] Failover Algorithm
- line 1958: level 4 [plain] NULL Task Reassignment Mechanism
- line 1985: level 4 [plain] Session Affinity (Optional)
- line 1991: level 4 [plain] Unix Socket Task Delivery System
- line 2200: level 4 [plain] Auto-Spawn
- line 2208: level 3 [plain] 7. WIP Lifecycle Management
- line 2212: level 4 [plain] Auto-Create
- line 2219: level 4 [plain] Auto-Mark Done
- line 2225: level 4 [plain] UI Integration
- line 2231: level 4 [plain] WIP Rules
- line 2237: level 4 [plain] WIP Update Mechanism (Clarification)
- line 2260: level 3 [plain] 8. HTTP API & Web UI
- line 2262: level 4 [plain] HTTP API Design
- line 2269: level 4 [plain] Key Endpoints
- line 2277: level 4 [plain] Server-Sent Events (SSE) Architecture
- line 2413: level 4 [plain] Web UI Design
- line 2420: level 4 [plain] UI Pages
- line 2429: level 2 [plain] Component Interface Definitions
- line 2431: level 3 [plain] Overview
- line 2435: level 3 [plain] 1. Database API Interface
- line 2443: level 4 [plain] Core Methods
- line 2490: level 4 [plain] Safety Mechanisms
- line 2498: level 4 [plain] Connection Pool Architecture (v2.9)
- line 2559: level 3 [plain] 2. CLI Command Interface
- line 2567: level 4 [plain] Core Commands
- line 2605: level 4 [plain] Command Format
- line 2610: level 4 [plain] CLI Command Implementation Status (v2.8.4)
- line 2637: level 3 [plain] 3. HTTP API Interface
- line 2645: level 4 [plain] Endpoints
- line 2756: level 4 [plain] Response Format
- line 2762: level 4 [plain] Error Response Format
- line 2784: level 4 [plain] Authentication
- line 2790: level 4 [plain] CORS Configuration
- line 2795: level 4 [plain] Rate Limiting
- line 2800: level 4 [plain] Request Validation
- line 2806: level 4 [plain] Pagination
- line 2812: level 4 [plain] Caching Strategy
- line 2818: level 4 [plain] API Versioning
- line 2824: level 3 [plain] 4. Storage API Interface
- line 2832: level 4 [plain] Core Methods
- line 2853: level 4 [plain] Directory Structure
- line 2862: level 3 [plain] 5. Config API Interface
- line 2870: level 4 [plain] Core Methods
- line 2888: level 4 [plain] Configuration Structure
- line 2920: level 3 [plain] 6. Session Spawning Interface
- line 2928: level 4 [plain] Session Management Approaches
- line 2953: level 4 [plain] Command Interface
- line 2970: level 4 [plain] When to Use Each Approach
- line 2985: level 4 [plain] Session Context (flow spawn only)
- line 2995: level 4 [plain] Implementation Note
- line 3001: level 2 [plain] Entity Model Transparency
- line 3005: level 3 [plain] Entity Relationships
- line 3022: level 3 [plain] User Navigation
- line 3043: level 3 [plain] Implementation
- line 3045: level 2 [plain] Database Schema Specification
- line 3047: level 3 [plain] Overview
- line 3053: level 3 [plain] Core Tables
- line 3055: level 4 [plain] hints
- line 3075: level 4 [plain] tasks
- line 3112: level 4 [plain] reports
- line 3139: level 4 [plain] sessions
- line 3156: level 4 [plain] config
- line 3168: level 3 [plain] Supporting Tables
- line 3170: level 4 [plain] task_notes
- line 3185: level 4 [plain] report_links
- line 3202: level 4 [plain] tasks_fts
- line 3216: level 3 [plain] Indexes
- line 3218: level 4 [plain] Performance Indexes
- line 3250: level 3 [plain] Foreign Key Relationships
- line 3252: level 4 [plain] Core Relationships
- line 3256: level 4 [plain] Junction Table Relationships
- line 3259: level 3 [plain] Constraints
- line 3261: level 4 [plain] CHECK Constraints
- line 3267: level 4 [plain] UNIQUE Constraints
- line 3272: level 3 [plain] Timestamp Convention
- line 3289: level 2 [plain] v1 Scope Definition
- line 3295: level 3 [plain] v1 Architecture Migration
- line 3321: level 3 [plain] v1 Complete Task Lifecycle (Already Implemented)
- line 3347: level 3 [plain] v1 Components
- line 3379: level 3 [plain] Critical Implementation Gaps (Architectural Migration Tasks for v1)
- line 3419: level 3 [plain] v1 Implementation Plan
- line 3526: level 3 [plain] v1 Success Criteria
- line 3561: level 2 [plain] Data Flow Diagrams
- line 3563: level 3 [plain] Task Execution Flow
- line 3599: level 3 [plain] Session Spawn Flow
- line 3639: level 3 [plain] Reply Flow (Binary Decision Model)
- line 3683: level 2 [plain] Critical Integration Points
- line 3685: level 3 [plain] 1. AI-to-System Integration (Most Critical)
- line 3693: level 3 [plain] 2. Database-to-Markdown Sync
- line 3701: level 3 [plain] 3. Session Health and Failover
- line 3709: level 3 [plain] 4. WIP Lifecycle
- line 3717: level 3 [plain] 5. Task Assignment and Session Limits
- line 3725: level 4 [plain] Round-Robin Auto-Assignment (v2.8.7)
- line 3764: level 2 [plain] Security Considerations
- line 3766: level 3 [plain] Database Security
- line 3773: level 3 [plain] CLI Security
- line 3779: level 3 [plain] Session Security
- line 3785: level 3 [plain] API Security
- line 3793: level 2 [plain] Performance Requirements
- line 3795: level 3 [plain] Database Performance
- line 3801: level 3 [plain] Session Performance
- line 3807: level 3 [plain] Task Execution Performance
- line 3814: level 2 [plain] Error Handling Strategy
- line 3816: level 3 [plain] Error Categorization
- line 3822: level 3 [plain] Retry Policy
- line 3828: level 3 [plain] Escalation Policy
- line 3836: level 2 [plain] Milestones
- line 3838: level 3 [plain] Milestone 1: Core.md Integration and Validation ✅ **COMPLETED**
- line 3844: level 4 [plain] Objective
- line 3847: level 4 [plain] Problems Solved
- line 3884: level 4 [plain] Deliverables
- line 3910: level 4 [plain] Backend Scenario Testing Methodology
- ... 143 more headings omitted from markdown report; see JSON.

## Suggested HLD section skeletons

### HLD-001 - IMPORTANT: Single Source of Truth

```md
## HLD-001 - IMPORTANT: Single Source of Truth

HLD-ID: HLD-001
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-002 - Executive Summary

```md
## HLD-002 - Executive Summary

HLD-ID: HLD-002
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-003 - CLI Entry Point

```md
## HLD-003 - CLI Entry Point

HLD-ID: HLD-003
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-004 - Stakeholder Analysis

```md
## HLD-004 - Stakeholder Analysis

HLD-ID: HLD-004
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-005 - User Personas

```md
## HLD-005 - User Personas

HLD-ID: HLD-005
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-006 - Business Case Foundation

```md
## HLD-006 - Business Case Foundation

HLD-ID: HLD-006
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-007 - User Stories

```md
## HLD-007 - User Stories

HLD-ID: HLD-007
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-008 - System Architecture Overview

```md
## HLD-008 - System Architecture Overview

HLD-ID: HLD-008
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-009 - Component Deep-Dive

```md
## HLD-009 - Component Deep-Dive

HLD-ID: HLD-009
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-010 - Component Interface Definitions

```md
## HLD-010 - Component Interface Definitions

HLD-ID: HLD-010
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-011 - Entity Model Transparency

```md
## HLD-011 - Entity Model Transparency

HLD-ID: HLD-011
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-012 - Database Schema Specification

```md
## HLD-012 - Database Schema Specification

HLD-ID: HLD-012
HLD-ROLE: data
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-013 - v1 Scope Definition

```md
## HLD-013 - v1 Scope Definition

HLD-ID: HLD-013
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-014 - Data Flow Diagrams

```md
## HLD-014 - Data Flow Diagrams

HLD-ID: HLD-014
HLD-ROLE: processing
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-015 - Critical Integration Points

```md
## HLD-015 - Critical Integration Points

HLD-ID: HLD-015
HLD-ROLE: api
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-016 - Security Considerations

```md
## HLD-016 - Security Considerations

HLD-ID: HLD-016
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-017 - Performance Requirements

```md
## HLD-017 - Performance Requirements

HLD-ID: HLD-017
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-018 - Error Handling Strategy

```md
## HLD-018 - Error Handling Strategy

HLD-ID: HLD-018
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-019 - Milestones

```md
## HLD-019 - Milestones

HLD-ID: HLD-019
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-020 - Environment Staging

```md
## HLD-020 - Environment Staging

HLD-ID: HLD-020
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-021 - Technology Stack

```md
## HLD-021 - Technology Stack

HLD-ID: HLD-021
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-022 - Open Questions and Contradictions

```md
## HLD-022 - Open Questions and Contradictions

HLD-ID: HLD-022
HLD-ROLE: risk
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-023 - Next Steps for HLD Refinement

```md
## HLD-023 - Next Steps for HLD Refinement

HLD-ID: HLD-023
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-024 - Technical Debt and Deprecation Timeline

```md
## HLD-024 - Technical Debt and Deprecation Timeline

HLD-ID: HLD-024
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-025 - Human Handoff Summary

```md
## HLD-025 - Human Handoff Summary

HLD-ID: HLD-025
HLD-ROLE: purpose
HLD-STATUS: active
HLD-RISK: LOW
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-026 - Lessons Learned from Skeptic-Stabilized HLD Completion

```md
## HLD-026 - Lessons Learned from Skeptic-Stabilized HLD Completion

HLD-ID: HLD-026
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-027 - Changelog

```md
## HLD-027 - Changelog

HLD-ID: HLD-027
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-028 - Decision Log

```md
## HLD-028 - Decision Log

HLD-ID: HLD-028
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-029 - Data Retention Policy

```md
## HLD-029 - Data Retention Policy

HLD-ID: HLD-029
HLD-ROLE: governance
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-030 - Operational Runbook

```md
## HLD-030 - Operational Runbook

HLD-ID: HLD-030
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-031 - Error Handling Specification

```md
## HLD-031 - Error Handling Specification

HLD-ID: HLD-031
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-032 - Implementation Handoff

```md
## HLD-032 - Implementation Handoff

HLD-ID: HLD-032
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-033 - Session Spawning Failure Modes

```md
## HLD-033 - Session Spawning Failure Modes

HLD-ID: HLD-033
HLD-ROLE: operations
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-034 - Assumptions

```md
## HLD-034 - Assumptions

HLD-ID: HLD-034
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-035 - Open Conflicts

```md
## HLD-035 - Open Conflicts

HLD-ID: HLD-035
HLD-ROLE: risk
HLD-STATUS: active
HLD-RISK: HIGH
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```

### HLD-036 - Success Criteria for HLD

```md
## HLD-036 - Success Criteria for HLD

HLD-ID: HLD-036
HLD-ROLE: architecture
HLD-STATUS: active
HLD-RISK: MEDIUM
HLD-SPECS: TBD
HLD-RESOURCES: TBD
HLD-VERIFY: section can be processed without loading the full HLD; related specs preserve HLD anchors
```


## Safe next steps

1. Preserve the original as `HLD.raw.md`.
2. Edit a working `HLD.md` copy only.
3. Convert only major sections to `## HLD-xxx - Title`.
4. Add required `HLD-*` metadata.
5. Use `TBD` for unknown mappings.
6. Add `REF HLD-xxx` links only where relationships are known.
7. Run `./hld_spec_sync.py --hld HLD.md --hld-map-only`.
8. Fix validation errors before syncing specs.

## Do not

- Do not overwrite the raw HLD.
- Do not tag every subsection.
- Do not invent spec IDs, owners, or resources.
- Do not run full-HLD sync before the map validates.
- Do not auto-convert or auto-chunk without reviewing a report or plan.
