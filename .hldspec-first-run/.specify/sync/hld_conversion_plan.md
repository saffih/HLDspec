# HLD Conversion Plan

made by AI

Status: `STOP_SPLIT_DECISION_REQUIRED`
Candidate sections: 36
Large candidate sections: 3
Human decision required: `true`

## Meaning

At least one candidate section is too large for safe metadata-only conversion and has peer internal headings that require split-boundary review.
Do not auto-convert those sections until split boundaries are accepted.

## Chunks

### chunk-001 - PROCEED_METADATA_ONLY

- candidates: HLD-001, HLD-002, HLD-003, HLD-004, HLD-005
- source lines: 23-256
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-002 - PROCEED_METADATA_ONLY

- candidates: HLD-006, HLD-007, HLD-008
- source lines: 257-748
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-003 - STOP_SPLIT_DECISION_REQUIRED

- candidates: HLD-009
- source lines: 749-2428
- human decision required: `true`
- reason: Candidate is 1680 lines, above the 400-line large-section threshold, and has 9 peer internal headings that can be reviewed as split boundaries.

### chunk-004 - STOP_SPLIT_DECISION_REQUIRED

- candidates: HLD-010
- source lines: 2429-3000
- human decision required: `true`
- reason: Candidate is 572 lines, above the 400-line large-section threshold, and has 7 peer internal headings that can be reviewed as split boundaries.

### chunk-005 - PROCEED_METADATA_ONLY

- candidates: HLD-011, HLD-012, HLD-013, HLD-014, HLD-015
- source lines: 3001-3763
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-006 - PROCEED_METADATA_ONLY

- candidates: HLD-016, HLD-017, HLD-018
- source lines: 3764-3835
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-007 - PROCEED_SINGLE_SECTION_REVIEW

- candidates: HLD-019
- source lines: 3836-4274
- human decision required: `true`
- reason: Candidate is 439 lines, above the 400-line large-section threshold, but no clear peer internal split boundaries were detected. Review as one large section.

### chunk-008 - PROCEED_METADATA_ONLY

- candidates: HLD-020, HLD-021, HLD-022, HLD-023, HLD-024
- source lines: 4275-4821
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-009 - PROCEED_METADATA_ONLY

- candidates: HLD-025, HLD-026, HLD-027, HLD-028, HLD-029
- source lines: 4822-5578
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-010 - PROCEED_METADATA_ONLY

- candidates: HLD-030, HLD-031, HLD-032, HLD-033, HLD-034
- source lines: 5579-6421
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

### chunk-011 - PROCEED_METADATA_ONLY

- candidates: HLD-035, HLD-036
- source lines: 6422-6455
- human decision required: `false`
- reason: Metadata-only batch of small/normal major sections.

## Candidate sections

### HLD-001 - IMPORTANT: Single Source of Truth

- source lines: 23-85
- approx lines: 63
- role: `governance`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-001A - Specification Alignment Plan (lines 62-85, 24 lines)

### HLD-002 - Executive Summary

- source lines: 86-100
- approx lines: 15
- role: `purpose`
- risk: `LOW`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-002A - Key Architectural Decisions (lines 90-100, 11 lines)

### HLD-003 - CLI Entry Point

- source lines: 101-143
- approx lines: 43
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

### HLD-004 - Stakeholder Analysis

- source lines: 144-221
- approx lines: 78
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-004A - Stakeholder Inventory (lines 146-151, 6 lines)
- HLD-004B - Stakeholder Concerns (lines 152-162, 11 lines)
- HLD-004C - Authority Levels (lines 163-172, 10 lines)
- HLD-004D - core.md Governance (v2.8.3) (lines 173-188, 16 lines)
- HLD-004E - Approval Criteria (v2.7) (lines 189-207, 19 lines)
- HLD-004F - Success Criteria (lines 208-221, 14 lines)

### HLD-005 - User Personas

- source lines: 222-256
- approx lines: 35
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-005A - Single Persona: System Owner / Developer (lines 224-256, 33 lines)

### HLD-006 - Business Case Foundation

- source lines: 257-355
- approx lines: 99
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-006A - Business Objectives (lines 259-275, 17 lines)
- HLD-006B - Job-to-be-Done (lines 276-293, 18 lines)
- HLD-006C - Success Metrics (lines 294-321, 28 lines)
- HLD-006D - Strategic Alignment (lines 322-355, 34 lines)

### HLD-007 - User Stories

- source lines: 356-659
- approx lines: 304
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-007A - Epic 1: Task Management (lines 358-381, 24 lines)
- HLD-007B - Epic 2: AI Task Execution (lines 382-406, 25 lines)
- HLD-007C - Epic 3: Reply Handling (lines 407-432, 26 lines)
- HLD-007D - Epic 4: Session Management (lines 433-463, 31 lines)
- HLD-007E - Epic 5: Reporting and Documentation (lines 464-489, 26 lines)
- HLD-007F - Epic 6: Data Management (lines 490-515, 26 lines)
- HLD-007G - Epic 7: Logging and Monitoring (lines 516-541, 26 lines)
- HLD-007H - Epic 8: End-to-End Workflows (lines 542-659, 118 lines)

### HLD-008 - System Architecture Overview

- source lines: 660-748
- approx lines: 89
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

### HLD-009 - Component Deep-Dive

- source lines: 749-2428
- approx lines: 1680
- role: `architecture`
- risk: `MEDIUM`
- large section: `true`
- recommended action: `STOP_SPLIT_DECISION_REQUIRED`
- human decision required: `true`
- reason: Candidate is 1680 lines, above the 400-line large-section threshold, and has 9 peer internal headings that can be reviewed as split boundaries.

Proposed split plan:
- HLD-009A - 1. TEA Architecture (Model-View-Update) (lines 751-781, 31 lines)
- HLD-009B - 2. Flow Core Database API (Critical Safety Layer) (lines 782-799, 18 lines)
- HLD-009C - 3. AI Integration Layer (Delicate Integration Point) (lines 800-1036, 237 lines)
- HLD-009D - 4. Brain Architecture (core.md - The AI Process Controller) (lines 1037-1425, 389 lines)
- HLD-009E - 5. Specification Hierarchy and Integration (lines 1426-1861, 436 lines)
- HLD-009F - 5. Automatic Sync Operations (lines 1862-1889, 28 lines)
- HLD-009G - 6. Session Management (lines 1890-2207, 318 lines)
- HLD-009H - 7. WIP Lifecycle Management (lines 2208-2259, 52 lines)
- HLD-009I - 8. HTTP API & Web UI (lines 2260-2428, 169 lines)

Nested internal headings, shown for context:
- line 753: level 4 Model (Centralized State)
- line 765: level 4 View (Pure Functions)
- line 774: level 4 Update (Event-Driven)
- line 786: level 4 Safety Mechanisms
- line 795: level 4 Critical Rule
- line 802: level 4 core.md - The AI Process Loop Code
- line 811: level 4 core.md Contract Invariants (CRITICAL)
- line 874: level 4 Reply Decision Criteria (Objective)
- line 932: level 4 core.md Error Recovery Paths
- line 956: level 4 8-Step Process Loop (Corrected Implementation)
- line 971: level 4 Process Loop Exit Conditions
- line 993: level 4 Recipe System (Learnable Behavior)
- line 1002: level 4 Session Spawn and Execution
- line 1011: level 4 Logging Architecture Rationale
- line 1039: level 4 Overview
- line 1050: level 4 Brain Responsibilities
- line 1080: level 4 Brain Structure and Content
- line 1101: level 4 Brain-System Interactions
- line 1174: level 4 Brain Contracts and Invariants
- line 1213: level 4 Brain Data Flow
- line 1261: level 4 Brain Lifecycle and Evolution
- line 1308: level 4 Brain Quality Assurance
- line 1343: level 4 Brain Integration Points
- line 1375: level 4 Brain Failure Modes
- line 1401: level 4 Brain Success Metrics
- line 1439: level 4 HLD as Single Source of Truth
- line 1454: level 4 Specification Directory Structure
- line 1487: level 4 Specification Integration with HLD
- line 1552: level 4 Specification Maintenance
- line 1575: level 4 Cross-Reference Matrix
- line 1589: level 4 Quality Assurance for Specifications
- line 1605: level 4 Archive and Deprecated Specifications
- line 1623: level 4 Current Implementation Structure
- line 1664: level 4 Architecture Decision: HLD Architecture vs flow_loop.py
- line 1696: level 4 Session Status Values (Actually Implemented)
- line 1702: level 4 Task Status Values (Database Schema)
- line 1713: level 4 CLI Protocol (Current Implementation)
- line 1722: level 4 CLI Architecture (Nervous System Model)
- line 1822: level 4 Task Discovery
- line 1829: level 4 Status Notification
- ... 25 more nested headings omitted from markdown only; see JSON.

### HLD-010 - Component Interface Definitions

- source lines: 2429-3000
- approx lines: 572
- role: `architecture`
- risk: `MEDIUM`
- large section: `true`
- recommended action: `STOP_SPLIT_DECISION_REQUIRED`
- human decision required: `true`
- reason: Candidate is 572 lines, above the 400-line large-section threshold, and has 7 peer internal headings that can be reviewed as split boundaries.

Proposed split plan:
- HLD-010A - Overview (lines 2431-2434, 4 lines)
- HLD-010B - 1. Database API Interface (lines 2435-2558, 124 lines)
- HLD-010C - 2. CLI Command Interface (lines 2559-2636, 78 lines)
- HLD-010D - 3. HTTP API Interface (lines 2637-2823, 187 lines)
- HLD-010E - 4. Storage API Interface (lines 2824-2861, 38 lines)
- HLD-010F - 5. Config API Interface (lines 2862-2919, 58 lines)
- HLD-010G - 6. Session Spawning Interface (lines 2920-3000, 81 lines)

Nested internal headings, shown for context:
- line 2443: level 4 Core Methods
- line 2490: level 4 Safety Mechanisms
- line 2498: level 4 Connection Pool Architecture (v2.9)
- line 2567: level 4 Core Commands
- line 2605: level 4 Command Format
- line 2610: level 4 CLI Command Implementation Status (v2.8.4)
- line 2645: level 4 Endpoints
- line 2756: level 4 Response Format
- line 2762: level 4 Error Response Format
- line 2784: level 4 Authentication
- line 2790: level 4 CORS Configuration
- line 2795: level 4 Rate Limiting
- line 2800: level 4 Request Validation
- line 2806: level 4 Pagination
- line 2812: level 4 Caching Strategy
- line 2818: level 4 API Versioning
- line 2832: level 4 Core Methods
- line 2853: level 4 Directory Structure
- line 2870: level 4 Core Methods
- line 2888: level 4 Configuration Structure
- line 2928: level 4 Session Management Approaches
- line 2953: level 4 Command Interface
- line 2970: level 4 When to Use Each Approach
- line 2985: level 4 Session Context (flow spawn only)
- line 2995: level 4 Implementation Note

### HLD-011 - Entity Model Transparency

- source lines: 3001-3044
- approx lines: 44
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-011A - Entity Relationships (lines 3005-3021, 17 lines)
- HLD-011B - User Navigation (lines 3022-3042, 21 lines)
- HLD-011C - Implementation (lines 3043-3044, 2 lines)

### HLD-012 - Database Schema Specification

- source lines: 3045-3288
- approx lines: 244
- role: `data`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-012A - Overview (lines 3047-3052, 6 lines)
- HLD-012B - Core Tables (lines 3053-3167, 115 lines)
- HLD-012C - Supporting Tables (lines 3168-3215, 48 lines)
- HLD-012D - Indexes (lines 3216-3249, 34 lines)
- HLD-012E - Foreign Key Relationships (lines 3250-3258, 9 lines)
- HLD-012F - Constraints (lines 3259-3271, 13 lines)
- HLD-012G - Timestamp Convention (lines 3272-3288, 17 lines)

Nested internal headings, shown for context:
- line 3055: level 4 hints
- line 3075: level 4 tasks
- line 3112: level 4 reports
- line 3139: level 4 sessions
- line 3156: level 4 config
- line 3170: level 4 task_notes
- line 3185: level 4 report_links
- line 3202: level 4 tasks_fts
- line 3218: level 4 Performance Indexes
- line 3252: level 4 Core Relationships
- line 3256: level 4 Junction Table Relationships
- line 3261: level 4 CHECK Constraints
- line 3267: level 4 UNIQUE Constraints

### HLD-013 - v1 Scope Definition

- source lines: 3289-3560
- approx lines: 272
- role: `purpose`
- risk: `LOW`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-013A - v1 Architecture Migration (lines 3295-3320, 26 lines)
- HLD-013B - v1 Complete Task Lifecycle (Already Implemented) (lines 3321-3346, 26 lines)
- HLD-013C - v1 Components (lines 3347-3378, 32 lines)
- HLD-013D - Critical Implementation Gaps (Architectural Migration Tasks for v1) (lines 3379-3418, 40 lines)
- HLD-013E - v1 Implementation Plan (lines 3419-3525, 107 lines)
- HLD-013F - v1 Success Criteria (lines 3526-3560, 35 lines)

### HLD-014 - Data Flow Diagrams

- source lines: 3561-3682
- approx lines: 122
- role: `processing`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-014A - Task Execution Flow (lines 3563-3598, 36 lines)
- HLD-014B - Session Spawn Flow (lines 3599-3638, 40 lines)
- HLD-014C - Reply Flow (Binary Decision Model) (lines 3639-3682, 44 lines)

### HLD-015 - Critical Integration Points

- source lines: 3683-3763
- approx lines: 81
- role: `api`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-015A - 1. AI-to-System Integration (Most Critical) (lines 3685-3692, 8 lines)
- HLD-015B - 2. Database-to-Markdown Sync (lines 3693-3700, 8 lines)
- HLD-015C - 3. Session Health and Failover (lines 3701-3708, 8 lines)
- HLD-015D - 4. WIP Lifecycle (lines 3709-3716, 8 lines)
- HLD-015E - 5. Task Assignment and Session Limits (lines 3717-3763, 47 lines)

Nested internal headings, shown for context:
- line 3725: level 4 Round-Robin Auto-Assignment (v2.8.7)

### HLD-016 - Security Considerations

- source lines: 3764-3792
- approx lines: 29
- role: `architecture`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-016A - Database Security (lines 3766-3772, 7 lines)
- HLD-016B - CLI Security (lines 3773-3778, 6 lines)
- HLD-016C - Session Security (lines 3779-3784, 6 lines)
- HLD-016D - API Security (lines 3785-3792, 8 lines)

### HLD-017 - Performance Requirements

- source lines: 3793-3813
- approx lines: 21
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-017A - Database Performance (lines 3795-3800, 6 lines)
- HLD-017B - Session Performance (lines 3801-3806, 6 lines)
- HLD-017C - Task Execution Performance (lines 3807-3813, 7 lines)

### HLD-018 - Error Handling Strategy

- source lines: 3814-3835
- approx lines: 22
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-018A - Error Categorization (lines 3816-3821, 6 lines)
- HLD-018B - Retry Policy (lines 3822-3827, 6 lines)
- HLD-018C - Escalation Policy (lines 3828-3835, 8 lines)

### HLD-019 - Milestones

- source lines: 3836-4274
- approx lines: 439
- role: `architecture`
- risk: `MEDIUM`
- large section: `true`
- recommended action: `PROCEED_SINGLE_SECTION_REVIEW`
- human decision required: `true`
- reason: Candidate is 439 lines, above the 400-line large-section threshold, but no clear peer internal split boundaries were detected. Review as one large section.

Proposed split plan:
- HLD-019A - Milestone 1: Core.md Integration and Validation ✅ **COMPLETED** (lines 3838-4274, 437 lines)

Nested internal headings, shown for context:
- line 3844: level 4 Objective
- line 3847: level 4 Problems Solved
- line 3884: level 4 Deliverables
- line 3910: level 4 Backend Scenario Testing Methodology
- line 3943: level 4 Validation Results
- line 4160: level 4 Architecture Impact
- line 4180: level 4 Technical Specifications
- line 4232: level 4 Acceptance Criteria
- line 4249: level 4 Metrics
- line 4263: level 4 Sign-off

### HLD-020 - Environment Staging

- source lines: 4275-4549
- approx lines: 275
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-020A - FLOW_ENV Variable (lines 4277-4282, 6 lines)
- HLD-020B - Path Construction (lines 4283-4287, 5 lines)
- HLD-020C - Automatic Port and Database Selection (lines 4288-4337, 50 lines)
- HLD-020D - Testing Workflow with Environment Staging (lines 4338-4549, 212 lines)

Nested internal headings, shown for context:
- line 4342: level 4 When to Use Test Environment
- line 4358: level 4 Test Environment Setup
- line 4386: level 4 Testing Workflow
- line 4426: level 4 Test Data Management
- line 4443: level 4 Test Environment Reset
- line 4458: level 4 Testing Best Practices
- line 4485: level 4 Example Testing Session
- line 4517: level 4 Environment Staging Scripts
- line 4530: level 4 Troubleshooting

### HLD-021 - Technology Stack

- source lines: 4550-4571
- approx lines: 22
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-021A - Core Technologies (lines 4552-4557, 6 lines)
- HLD-021B - Web Technologies (lines 4558-4563, 6 lines)
- HLD-021C - Development Tools (lines 4564-4571, 8 lines)

### HLD-022 - Open Questions and Contradictions

- source lines: 4572-4712
- approx lines: 141
- role: `risk`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-022A - Contradictions Between Specs and Current Implementation (lines 4574-4616, 43 lines)
- HLD-022B - Gaps in Current Implementation (lines 4617-4647, 31 lines)
- HLD-022C - Architecture Decisions Needed (lines 4648-4712, 65 lines)

### HLD-023 - Next Steps for HLD Refinement

- source lines: 4713-4723
- approx lines: 11
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

### HLD-024 - Technical Debt and Deprecation Timeline

- source lines: 4724-4821
- approx lines: 98
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-024A - Overview (lines 4726-4729, 4 lines)
- HLD-024B - Current Technical Debt Items (lines 4730-4802, 73 lines)
- HLD-024C - Technical Debt Management Process (lines 4803-4811, 9 lines)
- HLD-024D - Prevention of Future Technical Debt (lines 4812-4821, 10 lines)

Nested internal headings, shown for context:
- line 4732: level 4 1. flow_loop.py (Python Script Process Loop)
- line 4773: level 4 2. CLI Protocol Format (Text-based → JSON)

### HLD-025 - Human Handoff Summary

- source lines: 4822-4957
- approx lines: 136
- role: `purpose`
- risk: `LOW`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-025A - Executive Summary (lines 4824-4827, 4 lines)
- HLD-025B - What Was Accomplished (lines 4828-4849, 22 lines)
- HLD-025C - Current HLD State (lines 4850-4865, 16 lines)
- HLD-025D - Verification Results (lines 4866-4882, 17 lines)
- HLD-025E - Remaining Work (lines 4883-4902, 20 lines)
- HLD-025F - Human Action Required (lines 4903-4916, 14 lines)
- HLD-025G - Success Metrics (lines 4917-4937, 21 lines)
- HLD-025H - Contact and Support (lines 4938-4951, 14 lines)
- HLD-025I - Conclusion (lines 4952-4957, 6 lines)

### HLD-026 - Lessons Learned from Skeptic-Stabilized HLD Completion

- source lines: 4958-5082
- approx lines: 125
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-026A - Process Effectiveness (lines 4960-4973, 14 lines)
- HLD-026B - Technical Insights (lines 4974-5000, 27 lines)
- HLD-026C - Process Improvements (lines 5001-5017, 17 lines)
- HLD-026D - Quality Assurance (lines 5018-5029, 12 lines)
- HLD-026E - Remaining Work (lines 5030-5046, 17 lines)
- HLD-026F - Recommendations for Future Projects (lines 5047-5057, 11 lines)
- HLD-026G - Success Metrics (lines 5058-5082, 25 lines)

### HLD-027 - Changelog

- source lines: 5083-5456
- approx lines: 374
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-027A - Version 2.9 (2026-05-18) - Connection Pool Exhaustion Prevention & Alignment Fixes (lines 5085-5121, 37 lines)
- HLD-027B - Version 2.8.7 (2026-05-18) - Session Health Monitoring Implementation (lines 5122-5148, 27 lines)
- HLD-027C - Version 2.8.6 (2026-05-18) - Session Health Monitoring Clarification (lines 5149-5181, 33 lines)
- HLD-027D - Version 2.8.4 (2026-05-17) - Comprehensive HLD Review and Improvements (lines 5182-5208, 27 lines)
- HLD-027E - Version 2.8.3 (2026-05-17) - Data Directory Migration (lines 5209-5222, 14 lines)
- HLD-027F - Version 2.8.2 (2026-05-17) - Database Schema Simplification (lines 5223-5233, 11 lines)
- HLD-027G - Version 2.8.1 (2026-05-17) - SpecKit Clarification (lines 5234-5240, 7 lines)
- HLD-027H - Version 2.8 (2026-05-17) - Comprehensive HLD Review (lines 5241-5257, 17 lines)
- HLD-027I - Version 2.7 (2026-05-16) - Assumption Validation (lines 5258-5270, 13 lines)
- HLD-027J - Version 2.6 (2026-05-16) - CONFLICT Resolution & Database Schema (lines 5271-5295, 25 lines)
- HLD-027K - Version 2.5 (2026-05-16) - Lower Tier Requirements: SSE & No Security (lines 5296-5310, 15 lines)
- HLD-027L - Version 1.18 (2026-05-16) - v1 Scope Correction: Architecture Migration (lines 5311-5320, 10 lines)
- HLD-027M - Version 1.17 (2026-05-15) - HLD Improved and Aligned (lines 5321-5331, 11 lines)
- HLD-027N - Version 1.16 (2026-05-15) - Architecture Decision: HLD Architecture for v1 (lines 5332-5340, 9 lines)
- HLD-027O - Version 1.15 (2026-05-15) - v1 Complete Task Lifecycle (lines 5341-5351, 11 lines)
- HLD-027P - Version 1.14 (2026-05-15) - v1 Scope Definition (lines 5352-5363, 12 lines)
- HLD-027Q - Version 1.13 (2026-05-15) - CLI Architecture (Nervous System Model) (lines 5364-5375, 12 lines)
- HLD-027R - Version 2.4 (2026-05-16) - Architectural Decision: AI-First Philosophy Validation (lines 5376-5383, 8 lines)
- HLD-027S - Version 2.3 (2026-05-16) - Architectural Decision: CLI-Only for core.md (lines 5384-5400, 17 lines)
- HLD-027T - Version 2.1 (2026-05-16) - BMAD Party Mode Enhancements (lines 5401-5407, 7 lines)
- HLD-027U - Version 1.12 (2026-05-14) - Session Architecture Correction (lines 5408-5420, 13 lines)
- HLD-027V - Version 1.8 (2026-05-14) - Eighth Skeptic Pass Fixes (lines 5421-5423, 3 lines)
- HLD-027W - Version 1.7 (2026-05-14) - Seventh Skeptic Pass Fixes (lines 5424-5426, 3 lines)
- HLD-027X - Version 1.6 (2026-05-14) - Sixth Skeptic Pass Fixes (lines 5427-5432, 6 lines)
- HLD-027Y - Version 1.5 (2026-05-14) - Fourth Skeptic Pass Fixes (lines 5433-5437, 5 lines)
- HLD-027Z - Version 1.4 (2026-05-14) - Third Skeptic Pass Fixes (lines 5438-5442, 5 lines)
- HLD-02727 - Version 1.3 (2026-05-14) - Second Skeptic Pass Fixes (lines 5443-5447, 5 lines)
- HLD-02728 - Version 1.2 (2026-05-14) - First Skeptic Pass Fixes (lines 5448-5456, 9 lines)

### HLD-028 - Decision Log

- source lines: 5457-5521
- approx lines: 65
- role: `governance`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-028A - DEC-1: CLI-Only Requirement for core.md (lines 5459-5488, 30 lines)
- HLD-028B - DEC-2: AI-First Philosophy - CLI API Flexibility (lines 5489-5521, 33 lines)

### HLD-029 - Data Retention Policy

- source lines: 5522-5578
- approx lines: 57
- role: `governance`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-029A - Purpose (lines 5524-5527, 4 lines)
- HLD-029B - Retention Periods by Entity Type (lines 5528-5540, 13 lines)
- HLD-029C - Data Deletion Process (lines 5541-5554, 14 lines)
- HLD-029D - Compliance Considerations (lines 5555-5564, 10 lines)
- HLD-029E - Storage Management (lines 5565-5578, 14 lines)

### HLD-030 - Operational Runbook

- source lines: 5579-5770
- approx lines: 192
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-030A - Purpose (lines 5581-5584, 4 lines)
- HLD-030B - Deployment (lines 5585-5650, 66 lines)
- HLD-030C - Health Monitoring (lines 5651-5719, 69 lines)
- HLD-030D - Incident Response (lines 5720-5755, 36 lines)
- HLD-030E - Maintenance (lines 5756-5770, 15 lines)

Nested internal headings, shown for context:
- line 5612: level 4 Recovery Objectives (Single-Stakeholder System)
- line 5631: level 4 Incident Response Procedures
- line 5682: level 4 Alert Definition and Routing (v2.8.3)

### HLD-031 - Error Handling Specification

- source lines: 5771-5873
- approx lines: 103
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-031A - Error Categories (lines 5773-5794, 22 lines)
- HLD-031B - Retry Strategy (lines 5795-5807, 13 lines)
- HLD-031C - Error Escalation (lines 5808-5834, 27 lines)
- HLD-031D - Error Logging Requirements (lines 5835-5853, 19 lines)
- HLD-031E - Error Recovery (lines 5854-5873, 20 lines)

### HLD-032 - Implementation Handoff

- source lines: 5874-5970
- approx lines: 97
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-032A - Purpose (lines 5876-5879, 4 lines)
- HLD-032B - Traceability Matrix (lines 5880-5894, 15 lines)
- HLD-032C - Test Strategy (lines 5895-5919, 25 lines)
- HLD-032D - Test Data Requirements (lines 5920-5933, 14 lines)
- HLD-032E - Acceptance Criteria (lines 5934-5946, 13 lines)
- HLD-032F - Validation Checklist (lines 5947-5970, 24 lines)

### HLD-033 - Session Spawning Failure Modes

- source lines: 5971-6183
- approx lines: 213
- role: `operations`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-033A - Failure Points in Session Spawning (lines 5973-5976, 4 lines)
- HLD-033B - Failure Mode 1: flow_spawn.py Execution Failure (lines 5977-6002, 26 lines)
- HLD-033C - Failure Mode 2: bg-devin Invocation Failure (lines 6003-6028, 26 lines)
- HLD-033D - Failure Mode 3: Log File Creation Failure (lines 6029-6054, 26 lines)
- HLD-033E - Failure Mode 4: core.md Loading Failure (lines 6055-6082, 28 lines)
- HLD-033F - Failure Mode 5: Session Registration Failure (lines 6083-6109, 27 lines)
- HLD-033G - Failure Mode 6: Partial Session Spawn (Success at Some Steps, Failure at Others) (lines 6110-6135, 26 lines)
- HLD-033H - Failure Mode 7: Session Spawn Success But Task Discovery Fails (lines 6136-6161, 26 lines)
- HLD-033I - Session Spawn Rollback Strategy (lines 6162-6183, 22 lines)

### HLD-034 - Assumptions

- source lines: 6184-6421
- approx lines: 238
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-034A - ASSUMPTION: Governance Definition (lines 6186-6205, 20 lines)
- HLD-034B - ASSUMPTION: Security Model (lines 6206-6219, 14 lines)
- HLD-034C - ASSUMPTION: Performance Claims (lines 6220-6231, 12 lines)
- HLD-034D - ASSUMPTION: Stakeholder Personas (lines 6232-6243, 12 lines)
- HLD-034E - ASSUMPTION: AI-First Philosophy (lines 6244-6257, 14 lines)
- HLD-034F - ASSUMPTION: CLI Reliability (lines 6258-6271, 14 lines)
- HLD-034G - ASSUMPTION: One-Way Sync Sufficiency (lines 6272-6283, 12 lines)
- HLD-034H - ASSUMPTION: Error Scenario Coverage (lines 6284-6303, 20 lines)
- HLD-034I - ASSUMPTION: Operational Procedure Completeness (lines 6304-6323, 20 lines)
- HLD-034J - ASSUMPTION: Database Recovery Capability (lines 6324-6342, 19 lines)
- HLD-034K - ASSUMPTION: Session Failover Effectiveness (lines 6343-6361, 19 lines)
- HLD-034L - ASSUMPTION: CLI Error Detection (lines 6362-6381, 20 lines)
- HLD-034M - ASSUMPTION: Environment Isolation Reliability (lines 6382-6401, 20 lines)
- HLD-034N - ASSUMPTION: Operational Targets Not Required (v2.7) (lines 6402-6421, 20 lines)

### HLD-035 - Open Conflicts

- source lines: 6422-6441
- approx lines: 20
- role: `risk`
- risk: `HIGH`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

Proposed split plan:
- HLD-035A - RESOLVED: CONFLICT #2 (v2.4) (lines 6424-6431, 8 lines)
- HLD-035B - RESOLVED: CONFLICT #1 (v2.3) (lines 6432-6441, 10 lines)

### HLD-036 - Success Criteria for HLD

- source lines: 6442-6455
- approx lines: 14
- role: `architecture`
- risk: `MEDIUM`
- large section: `false`
- recommended action: `PROCEED_METADATA_ONLY`
- human decision required: `false`
- reason: Candidate is within metadata-only conversion bounds.

## Rules

- Preserve all original HLD content.
- Metadata-only conversion may add HLD headings and metadata but must not delete, summarize, or reinterpret content.
- Use `HLD-SPECS: TBD` unless mapping is certain.
- Use `HLD-RESOURCES: TBD` unless resources/interfaces/contracts are explicit.
- Do not split sections marked `STOP_SPLIT_DECISION_REQUIRED` without human approval.
- After conversion, rerun `scripts/first_run_readonly.sh` on the converted HLD.
