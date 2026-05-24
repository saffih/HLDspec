# HLDspec MachineResult Renderer

## Purpose

`MachineResult` is the internal contract.

`hldspec.result_renderer` is the adapter that turns the internal state-machine result into:

```text
human-readable checkpoint reports
JSON-compatible dictionaries
```

## Rule

State machines do not print user-facing checkpoint prose.

They return `MachineResult`.

The renderer owns the display contract:

```text
Current checkpoint:
Blocking reason:
Human decision needed:
Controlling artifacts:
Continuation protocol:
What is not modified / not invoked:
```

## Why

This keeps the architecture separated:

```text
State machine: decides state and next action.
Renderer: presents checkpoint and decision format.
Shell/script CLI: adapts command-line execution.
Agent/judge: interprets rendered checkpoint and asks only real questions.
```

## Migration path

```text
1. Keep existing scripts working.
2. Add machine-result renderer.
3. Add CLI renderer adapter.
4. Move raw-HLD conversion into a sub-machine.
5. Replace procedural checkpoint printing with MachineResult rendering.
```
