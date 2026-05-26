# Agent-First Product Model

## Purpose

HLDspec is an agent-guided system for turning design knowledge into a target product workspace.

A user should not start by choosing low-level scripts. A user should start an HLDspec agent session and provide:

- source HLD or resources
- target directory
- optional comment or intent

The agent uses HLDspec scripts and machines as tools.

## Core rule

All real HLDspec scenarios start with an agent session.

Scripts are tools for agents. Scripts are not the primary user workflow.

## Why agent-first

HLDspec work requires judgment:

- interpret messy HLD/resources
- decide create, update, upgrade, or adopt
- detect source/resource changes
- detect generated artifact drift
- apply RunSkeptic
- choose relevant software design principles
- select backend tools only when triggered
- prepare human checkpoints
- generate SpecKit and mediator prompts
- preserve SpecKit ownership boundaries

A deterministic script can inspect, validate, generate, compare, and report.

An agent must orchestrate.

## Product mental model

```text
User
  -> HLDspec agent session
      -> ProjectMachine
          -> HLDspec tools/scripts
          -> RunSkeptic
          -> target/ artifacts
          -> human checkpoints
          -> SpecKit delegation
```

## User-facing commands

The public product surface should be small:

```text
hldspec start
hldspec status
hldspec review
hldspec continue
hldspec speckit
hldspec diff
hldspec doctor
hldspec stop
```

Low-level scripts remain available as agent tools and debug tools.

## Start command

```bash
hldspec start \
  --source ./HLD.md \
  --target ./target \
  --comment "create target workspace and prepare SpecKit build"
```

The command should prepare or resume an agent session.

It should not force the user to know whether the internal mode is create, update, upgrade, adopt, or resume.

## Mode detection

HLDspec should detect mode from target state:

| Detected situation | Mode | Behavior |
|---|---|---|
| target does not exist | create | create target workspace |
| target exists without HLDspec state | adopt | inspect existing target safely |
| source/resource hash changed | update | rebuild affected target artifacts |
| HLDspec guidance/templates changed | upgrade | update generated guidance/prompts |
| SpecKit artifacts exist | brownfield | preserve and review drift |
| unresolved conflicts exist | blocked | stop and request human decision |
| no relevant change | resume | continue next safe action |

Manual mode override is allowed only for expert use.

## Agent responsibilities

The HLDspec agent must:

1. Read session prompt and state.
2. Use scripts/machines as tools.
3. Keep source HLD/resources read-only.
4. Work inside target.
5. Apply RunSkeptic at key junctions.
6. Enforce cost/context economy.
7. Avoid broad rereads unless required.
8. Generate or refresh target artifacts.
9. Present human checkpoints clearly.
10. Stop on unresolved CONFLICT.
11. Never manually create final SpecKit specs.
12. Delegate SpecKit through approved prompts.

## Tool responsibilities

Tools/scripts should be deterministic.

Tools may:

- inspect
- hash
- classify
- generate
- validate
- render reports
- prepare prompts
- run machine transitions

Tools must not silently own human decisions.

## Target workspace

The agent works toward:

```text
target/
  targetHLD/
  .hldspec/
  .specify/
  prompts/
  specs/
```

`target/` is the future product workspace.

HLDspec prepares `target/`.

SpecKit builds inside `target/`.

## Acceptance criteria

HLDspec is agent-first when:

- user-facing docs start with agent session commands
- scripts are documented as agent tools
- start/status/review/continue commands exist
- the target workspace is the visible unit of work
- generated prompts tell target agents exactly what to do
- RunSkeptic and cost/context economy are enforced at gates
