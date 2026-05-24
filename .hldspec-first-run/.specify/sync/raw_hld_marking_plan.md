# Raw HLD Marking Plan

made by AI

Status: `RAW_HLD_MARKING_REQUIRED`

## Purpose

Mark raw HLD sections with product, architecture, interface, data, processing, governance, security, and operations perspectives before conversion.

## Rules

- Do not convert raw HLD mechanically when section role/boundary is unclear.
- Use bounded product and architecture perspectives to mark each candidate section.
- Ask only real checkpoint questions when interpretation affects split/role/dependency/constitution.
- Do not create SpecKit specs during marking.
- Do not modify the source HLD.
- Do not default unknown sections to architecture; use TBD until evidence is sufficient.

## Subagent Contract

- judge/orchestrator: Owns final marking decisions, human questions, and source-HLD safety.
- context rule: Each subagent receives only the candidate section, relevant prior decisions, and its perspective questions.

Bounded subagents:
- `product_reviewer`
- `architecture_reviewer`
- `interface_contract_reviewer`
- `data_state_reviewer`
- `processing_behavior_reviewer`
- `governance_reviewer`
- `security_reviewer`
- `operations_reviewer`

## Candidate Marking Items

### HLD-001 - IMPORTANT: Single Source of Truth

- source lines: 23-85
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, data_model, processing_behavior, governance_context, security
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: IMPORTANT: Single Source of Truth
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, data_model, processing_behavior, governance_context, security`
- subagents: product_reviewer, architecture_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-001",
  "HLD-RESOURCES": "product_context, architecture, data_model, processing_behavior, governance_context, security",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?

Judge notes:
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-002 - Executive Summary

- source lines: 86-100
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Flow is a web application that uses AI agent (Devin) to maintain context in Work-In-Progress (WIP) documents, processes tasks through an 8-step loop, and generates reports. The system implements The Elm Architecture (TEA) pattern with Model-View-Update separation, uses SQLite as a single source of t
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-002",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- May belong in constitution/prework rather than a feature spec.

### HLD-003 - CLI Entry Point

- source lines: 101-143
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, governance_context, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: CLI Entry Point
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, governance_context, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-003",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, governance_context, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- May belong in constitution/prework rather than a feature spec.

### HLD-004 - Stakeholder Analysis

- source lines: 144-221
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Stakeholder Analysis
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-004",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-005 - User Personas

- source lines: 222-256
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: User Personas
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-005",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-006 - Business Case Foundation

- source lines: 257-355
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Business Case Foundation
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-006",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-007 - User Stories

- source lines: 356-659
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: User Stories
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-007",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-008 - System Architecture Overview

- source lines: 660-748
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: System Architecture Overview
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-008",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- May belong in constitution/prework rather than a feature spec.

### HLD-009 - Component Deep-Dive

- source lines: 749-2428
- conversion action: `STOP_SPLIT_DECISION_REQUIRED`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Component Deep-Dive
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-009",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-010 - Component Interface Definitions

- source lines: 2429-3000
- conversion action: `STOP_SPLIT_DECISION_REQUIRED`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Component Interface Definitions
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-010",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-011 - Entity Model Transparency

- source lines: 3001-3044
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, interface_contract, data_model, processing_behavior, governance_context
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Entity Model Transparency
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, interface_contract, data_model, processing_behavior, governance_context`
- subagents: product_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-011",
  "HLD-RESOURCES": "product_context, interface_contract, data_model, processing_behavior, governance_context",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-012 - Database Schema Specification

- source lines: 3045-3288
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Database Schema Specification
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-012",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- May belong in constitution/prework rather than a feature spec.

### HLD-013 - v1 Scope Definition

- source lines: 3289-3560
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: v1 Scope Definition
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-013",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-014 - Data Flow Diagrams

- source lines: 3561-3682
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Data Flow Diagrams
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-014",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-015 - Critical Integration Points

- source lines: 3683-3763
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Critical Integration Points
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-015",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-016 - Security Considerations

- source lines: 3764-3792
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Security Considerations
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-016",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-017 - Performance Requirements

- source lines: 3793-3813
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, data_model, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Performance Requirements
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, data_model, operations`
- subagents: product_reviewer, data_state_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-017",
  "HLD-RESOURCES": "product_context, data_model, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

### HLD-018 - Error Handling Strategy

- source lines: 3814-3835
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: interface_contract, data_model, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: - **Permanent Errors**: Auth, corruption - escalate immediately as conflict
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `interface_contract, data_model, governance_context, security, operations`
- subagents: interface_contract_reviewer, data_state_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-018",
  "HLD-RESOURCES": "interface_contract, data_model, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether data/source-of-truth concerns are mixed with interface contract.
- May belong in constitution/prework rather than a feature spec.

### HLD-019 - Milestones

- source lines: 3836-4274
- conversion action: `PROCEED_SINGLE_SECTION_REVIEW`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: ### Milestone 1: Core.md Integration and Validation ✅ **COMPLETED**
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-019",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-020 - Environment Staging

- source lines: 4275-4549
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `interface_contract`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Environment Staging
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, security, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-020",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "interface_contract",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-021 - Technology Stack

- source lines: 4550-4571
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `interface_contract`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: - **Database**: SQLite with WAL mode
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-021",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "interface_contract",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-022 - Open Questions and Contradictions

- source lines: 4572-4712
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, security
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: 1. **CLI Protocol Format**: ✅ **RESOLVED - IMPLEMENTED JSON**
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, security`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, security_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-022",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, security",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-023 - Next Steps for HLD Refinement

- source lines: 4713-4723
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: architecture, interface_contract, data_model, processing_behavior, governance_context
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Next Steps for HLD Refinement
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, data_model, processing_behavior, governance_context`
- subagents: architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-023",
  "HLD-RESOURCES": "architecture, interface_contract, data_model, processing_behavior, governance_context",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- May belong in constitution/prework rather than a feature spec.

### HLD-024 - Technical Debt and Deprecation Timeline

- source lines: 4724-4821
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `interface_contract`
- suggested roles: architecture, interface_contract, processing_behavior, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: This section documents known technical debt in the Flow system and provides deprecation timelines for architectural migrations.
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, interface_contract, processing_behavior, security, operations`
- subagents: architecture_reviewer, interface_contract_reviewer, processing_behavior_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-024",
  "HLD-RESOURCES": "architecture, interface_contract, processing_behavior, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "interface_contract",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.

### HLD-025 - Human Handoff Summary

- source lines: 4822-4957
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: The Skeptic-Stabilized HLD Completion process has been successfully executed. The HLD has been updated from version 2.5 to version 2.6 with comprehensive improvements based on Skeptic analysis and human decisions. The HLD is now READY FOR IMPLEMENTATION HANDOFF with LEVEL 0 completeness resolved.
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-025",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-026 - Lessons Learned from Skeptic-Stabilized HLD Completion

- source lines: 4958-5082
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: ### Process Effectiveness
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-026",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-027 - Changelog

- source lines: 5083-5456
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: ### Version 2.9 (2026-05-18) - Connection Pool Exhaustion Prevention & Alignment Fixes
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-027",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-028 - Decision Log

- source lines: 5457-5521
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Decision Log
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-028",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-029 - Data Retention Policy

- source lines: 5522-5578
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Data Retention Policy
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-029",
  "HLD-RESOURCES": "product_context, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-030 - Operational Runbook

- source lines: 5579-5770
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `product_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Operational Runbook
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-030",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "product_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.

### HLD-031 - Error Handling Specification

- source lines: 5771-5873
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: - Database connection timeout
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-031",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-032 - Implementation Handoff

- source lines: 5874-5970
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Provide implementation team with clear guidance on building, testing, and validating Flow from this HLD.
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-032",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-033 - Session Spawning Failure Modes

- source lines: 5971-6183
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: The session spawning flow is: `flow_spawn.py → bg-devin → core.md (Devin execution)`
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-033",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-034 - Assumptions

- source lines: 6184-6421
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Assumptions
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, architecture_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-034",
  "HLD-RESOURCES": "product_context, architecture, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-035 - Open Conflicts

- source lines: 6422-6441
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: product_context, interface_contract, data_model, processing_behavior, governance_context, security, operations
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: Open Conflicts
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `product_context, interface_contract, data_model, processing_behavior, governance_context, security, operations`
- subagents: product_reviewer, interface_contract_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer, security_reviewer, operations_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-035",
  "HLD-RESOURCES": "product_context, interface_contract, data_model, processing_behavior, governance_context, security, operations",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What user value, use case, or user journey does this section define?
- Is this context-only or does it imply a SpecKit feature?
- What acceptance criteria would make the feature testable?
- Does this define an external API, endpoint, CLI, event, request, or response contract?
- Can the contract be specified separately from processing behavior?
- What consumers depend on this interface?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?
- Does this introduce access, permission, token, secret, or exposure risk?
- What must be validated before implementation?
- Does this define environment, deployment, observability, or runbook behavior?
- Is it a feature, support concern, or constitution/operational constraint?

Judge notes:
- Check whether API/interface contract should be separated from processing behavior.
- Check whether data/source-of-truth concerns are mixed with interface contract.
- Product/use-case evidence exists but may be context for another primary role.
- May belong in constitution/prework rather than a feature spec.

### HLD-036 - Success Criteria for HLD

- source lines: 6442-6455
- conversion action: `PROCEED_METADATA_ONLY`
- primary role: `governance_context`
- suggested roles: architecture, data_model, processing_behavior, governance_context
- suggested risk: `HIGH`
- evidence level: `observed`
- evidence excerpt: - [ ] All component interactions are clearly defined
- split/keep recommendation: `SPLIT`
- refs: none
- depends refs: none
- conflicts refs: none
- suggested specs: `TBD`
- suggested resources: `architecture, data_model, processing_behavior, governance_context`
- subagents: architecture_reviewer, data_state_reviewer, processing_behavior_reviewer, governance_reviewer

Candidate HLD metadata:

```json
{
  "CONFLICTS_WITH_REF": [],
  "DEPENDS_REF": [],
  "HLD-ID": "HLD-036",
  "HLD-RESOURCES": "architecture, data_model, processing_behavior, governance_context",
  "HLD-RISK": "HIGH",
  "HLD-ROLE": "governance_context",
  "HLD-SPECS": "TBD",
  "HLD-STATUS": "active",
  "HLD-VERIFY": "Verify section role, dependencies, resources, and split/keep decision against HLD evidence.",
  "REF": []
}
```

Questions:
- What component, boundary, or responsibility is defined here?
- What must remain connected, and what can be separated?
- Does this section impose architecture constraints for downstream specs?
- What is the source of truth for this state or data?
- Who owns mutation and lifecycle of this data?
- Which features depend on this model before they can be specified?
- What runtime behavior or workflow is defined here?
- Is behavior mixed with API contract or data ownership?
- What inputs, outputs, failure modes, and verification rules are implied?
- Is this a rule, assumption, decision, conflict, or checkpoint rather than a feature?
- Does it belong in constitution/prework rather than a feature spec?
- What human decision would be needed if this is unclear?

Judge notes:
- May belong in constitution/prework rather than a feature spec.
