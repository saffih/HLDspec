# HLDspec Principle Enforcement Matrix

## Purpose

This matrix tracks whether HLDspec enforces its own design principles on the HLDspec repo.

## Matrix

| Principle | Current enforcement | Tests proving it | Missing enforcement |
|---|---|---|---|
| Source of truth | `start` preserves source hash and raw HLD under target; session and interview artifacts record source path/hash. | `tests_v2/test_agent_first_cli_contract.py`; `tests_v2/test_self_dogfood_flow.py` | Conflict reconciliation for multiple source inputs. |
| Explicit contracts | Output contract, command surface contract, target workspace adapter, validator reports, promotion reports. | command surface, product contract, promotion gate, self-dogfood tests | Schema validation for every generated artifact. |
| State machine and resumability | `ProjectMachine`, `continue`, target event log, session state, promotion gate. | project machine and product contract tests | Full stale-artifact and resume journey tests. |
| Testability | Unit-style tests for CLI facade, adapter, context economy, validators, promotion gate, self-dogfood smoke. | `python3 -m unittest discover -s tests_v2 -v` | Broader end-to-end journey and red-to-green evidence capture. |
| Context economy | `allowed_evidence.json`, `forbidden_reads.md`, context packs, bounded SpecKit phase prompts, broad-read validator. | `tests_v2/test_context_economy_speckit_prompts.py`; self-dogfood smoke | Product-flow integration through a guarded public command. |
| RunSkeptic | Prompt trigger markers, validator checks, promotion gate checks for promoted capability RunSkeptic status. | context economy and promotion gate tests | Gate-machine and handoff packet RunSkeptic PASS/ACTION/CONFLICT propagation. |
| Quality gates | Context prompt validation, promotion gate, doctor final summary. | validator, promotion, CLI contract tests | Full domain validators: backend triggers, principle evidence, constitution purity, package testability, graph/queue parity, handoff pointers. |
| UX/output quality | Output contract; status/review/doctor sections; next safe action. | CLI contract tests; self-dogfood smoke | Sectioned output for `start` and `diff`; stage-aware doctor checks. |
| Safety | Source read-only behavior, target-only durable writes, implementation approval guard in prompts. | CLI contract, context prompt, promotion gate, self-dogfood tests | Stronger enforcement for every write path and every generated prompt. |

## Rule

If a principle has no enforcement and no test, it is documentation only.

Documentation-only principles must be marked ACTION before promotion.
