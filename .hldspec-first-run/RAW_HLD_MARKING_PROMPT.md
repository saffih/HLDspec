# Raw HLD Marking Prompt

made by AI

Act as the HLDspec judge/orchestrator.

Goal:
Mark the raw HLD before conversion using bounded product and architecture perspectives.

Inputs:
- raw HLD source
- HLD conversion plan
- raw HLD marking plan

Rules:
- Do not modify the source HLD.
- Do not invoke SpecKit.
- Do not create final specs manually.
- Use bounded subagents only for candidate sections and perspective questions.
- Ask the human only real checkpoint questions.
- Do not default unknown sections to architecture; use TBD until evidence is sufficient.
- Final output should guide HLD metadata: HLD-ROLE, HLD-RISK, HLD-SPECS, HLD-RESOURCES, HLD-VERIFY, refs, split/keep decisions.

Open:
- /Users/saffi/code/flow/HLD.md
- .specify/sync/hld_conversion_plan.md
- .specify/sync/raw_hld_marking_plan.md
