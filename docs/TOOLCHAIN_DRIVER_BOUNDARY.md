# Toolchain Driver Boundary

**Status:** product contract + first runtime slice. Defines the universal
ownership boundary a Toolchain Driver must respect, and documents the first
slice that makes it operational for SpecKit: `hldspec/toolchain_driver_boundary.py`
(zone classification) and `hldspec/helper_selection.py` (selected-helper state),
surfaced through `scripts/hldspec_agent_session.py status` / `select-helper`.

Core invariant (unchanged from the product framing): **HLDspec operates
toolchains; it does not impersonate them.**

---

## 1. Vocabulary bridge

This doc introduces four terms. Each maps onto an existing repo realization —
no parallel concept is created.

| New term | Existing realization |
|---|---|
| Toolchain | `helper_registry.py` helper entry's `toolchain` field (e.g. `"SpecKit"`). One toolchain (SpecKit) is operational today. |
| Toolchain Driver | An *operational* helper (`helper_registry.operational_helpers()`) operating through its declared `allowed_actions`/`forbidden_actions`/`stop_rules`. Today: `helper_id: speckit`. |
| Approved Control Surface | A helper's `recommendable_commands` / `allowed_actions` (docs/JOURNEY3_HELPER_CONTRACT.md §6) — the CLI/API/input seams the driver may use. For `speckit`: `/speckit.*` commands, recommended at `GUIDE_ONLY`/`PROPOSE_COMMAND`; the opt-in `EXECUTE_WITH_APPROVAL` `SpecKitInvoker`/drive-loop path is the only capability that goes further (see §5). |
| Tool-owned artifacts | Files classified `TOOL_OWNED_FORBIDDEN` or `READ_ONLY_EVIDENCE` by `toolchain_driver_boundary.classify_path` — SpecKit's own generated/governed territory. |
| HLDspec-owned artifacts | Files classified `HLDSPEC_OWNED` — HLDspec's own control state. |

---

## 2. Ownership zones

Defined in `hldspec/toolchain_driver_boundary.py`. Five zones, evaluated in this
order (most specific match wins):

| Zone | Path roots (target-relative) | May the driver write? | May the driver read? |
|---|---|---|---|
| `HLDSPEC_OWNED` | `.hldspec/` | Yes — freely | Yes |
| `ADAPTER_MIRROR` | `.specify/source/` | Yes — **only** as a generated, banner-stamped mirror, never authoritative (docs/JOURNEY2_PACKAGE_CONTRACT.md §10) | Yes |
| `READ_ONLY_EVIDENCE` | `.specify/memory/`, `specs/` | **No** | Yes — as evidence only |
| `TOOL_OWNED_FORBIDDEN` | rest of `.specify/` | **No** | Yes |
| `AMBIGUOUS_ESCALATE` | anything else (including paths outside the target) | **No** (default-deny) | Not assumed safe either — escalate to a human decision before treating it as evidence |

**Ambiguous-ownership escalation rule:** a path that does not provably fall into
`HLDSPEC_OWNED` or an explicit `ADAPTER_MIRROR` seam is never assumed writable.
Unknown paths escalate to `AMBIGUOUS_ESCALATE` rather than defaulting to "probably
fine" — the same fail-closed posture `target_discovery.py` uses for unknown
brownfield classification.

**Known narrower exception, already implemented, not modeled here:**
`refresh_target.py` may update `.specify/memory/constitution.md` between explicit
`HLDSPEC:MANAGED:CONSTITUTION` markers — a narrow, already-built write seam for
one file, gated by `--adopt-constitution-managed-block`. This module's coarser
`READ_ONLY_EVIDENCE` classification for `.specify/memory/` is the safe default
for any *other* driver code that has not implemented that specific protocol. The
two classifications do not conflict: refresh_target's managed-block writer is a
named, reviewed exception to the general rule this module states.

**Existing enforcement this module formalizes, not replaces:**
`refresh_target.py::_classify_*` already implements file-by-file safety
classification for the install/refresh step (`OWNED_BY_HLDSPEC_SAFE_TO_UPDATE`,
`EXISTS_BUT_UNOWNED_DO_NOT_TOUCH`, `CONFLICT_REQUIRES_HUMAN`, etc.) and is not
refactored to import this module. Both must agree on what is tool-owned; this
module is the place new driver code (status reporting, helper selection, future
drivers) looks instead of re-deriving the boundary per call site.

---

## 3. Approved write seams vs forbidden write zones

```text
approved_write_seam(target, path)  == zone in {HLDSPEC_OWNED, ADAPTER_MIRROR}
forbidden_write(target, path)      == not approved_write_seam(...)
```

Every new driver write path (today: `helper_selection.write_helper_selection`)
must write only through `HLDSPEC_OWNED` — resolved via
`control_paths.resolve_hldspec_dir`, which is pointer-aware (external-state mode
relocates `.hldspec` to a controller root; a naive `target/.hldspec` path would
silently miss that relocation).

`tests_v2/test_toolchain_driver_status_cli.py::test_status_and_select_helper_never_mutate_tool_owned_zones`
seeds files in every forbidden zone, runs `status` and `select-helper`, and
asserts byte-for-byte equality before/after — the concrete proof, not just a
documented intention.

---

## 4. Toolchain Execution Loop (Journey 3) — phase coverage, not skippable

Per the product framing, every toolchain-specific driver must cover all seven
phases below; it may rename/specialize them, never skip one.

| Phase | SpecKit driver realization (today) |
|---|---|
| Spec intake | `build_source_package_content` (Journey 2) → `speckit_single_spec_input.md` consumed at `/speckit.specify` |
| Clarification | `/speckit.clarify`, `[NEEDS CLARIFICATION]` markers, human-owned questions (JOURNEY3_HELPER_CONTRACT §4) |
| Planning | `/speckit.plan`, `/speckit.tasks` |
| Verification checks | `/speckit.analyze`, RunSkeptic PASS/ACTION/CONFLICT, `session_continue_preflight` |
| Implementation | `/speckit.implement` guidance at the implementation-approval boundary; bounded by `implementation_slices.json` |
| Testing / evidence collection | Anti-hollow-completion gate (`InvocationResult.verified`, git-signature change detection) in `speckit_invoker.py` |
| Report-back | Fixed report shape: phase / files / RunSkeptic status / next safe action (JOURNEY3_HELPER_CONTRACT §3) |

This is unchanged by this slice — it documents the existing realization so a
future second driver (e.g. ISG Governance, §6) has the same seven-phase
checklist to fill rather than a blank page.

---

## 5. SpecKit driver path

| Question | Answer |
|---|---|
| What starts the flow? | `scripts/hldspec_agent_session.py status\|continue --target <target>` (read-only/gated) or `start` (prepares the workspace). |
| What HLDspec files does it read? | `.hldspec/source_package/*`, `.hldspec/agent_session.json`, `.hldspec/helper_selection.json` (new), `.hldspec/sync/*` reports. |
| What SpecKit files may it read? | `.specify/memory/` (constitution evidence), `specs/<branch>/` phase artifacts — `READ_ONLY_EVIDENCE` per §2. |
| What SpecKit files must it never edit? | Everything under `.specify/` except the narrow constitution managed-block seam (§2) and the `.specify/source/` mirror; everything under `specs/`. |
| Which control surfaces are allowed? | `GUIDE_ONLY`/`PROPOSE_COMMAND` by default (recommend the next `/speckit.*` command); `EXECUTE_WITH_APPROVAL` only via the explicit, opt-in `SpecKitInvoker`/`speckit_drive_loop.py` path, whose real headless-CLI invocation is **self-acknowledged unproven** in `TASKS.md` — this slice does not change that, and does not invoke it. |
| How is PASS/ACTION/BLOCKED reported? | `hsel.build_toolchain_status()` returns `PASS` (selection present), `ACTION` (no selection — defaults to the recommended/registry helper, never BLOCKED on this alone), surfaced in the `## Toolchain` section of `status`. |

---

## 6. Future ISG Governance driver — seam only, not implemented

No ISG Governance code exists in this repo. This section reserves the seam so a
future toolchain does not require redesigning the boundary:

- **Separate toolchain entry**: a future `helper_registry.build_isg_helper()`
  (or equivalent) with `toolchain: "ISG Governance"`, following the same
  `REQUIRED_HELPER_FIELDS` shape as `build_speckit_helper()`.
- **Separate driver**: a new `helper_id` (e.g. `isg-governance`) reaching
  `LIFECYCLE_OPERATIONAL_HELPER` only through the Generic Helper Bootstrap
  (`docs/HELPER_BOOTSTRAP_CONTRACT.md`) — never hand-added as "implemented".
  Until then it stays in `PLANNED_HELPER_IDS`-equivalent territory and
  `helper_selection.write_helper_selection` rejects it, the same way it rejects
  `claude-code`/`codex`/`devin`/`manual` today.
- **Separate approved controls**: its own `recommendable_commands` /
  `required_target_evidence` — not SpecKit's.
- **Same universal driver boundary**: `toolchain_driver_boundary.py`'s zones are
  generic (`HLDSPEC_OWNED`/`ADAPTER_MIRROR`/`READ_ONLY_EVIDENCE`/
  `TOOL_OWNED_FORBIDDEN`/`AMBIGUOUS_ESCALATE`); a second toolchain gets its own
  tool-owned-root prefixes added to the same module, not a parallel boundary
  module.

---

## 7. SourceBinding prerequisite (bridge, not new enforcement)

Before any future `NextActionPacket` may report READY, it must trace through
evidence that already exists in pieces today — this section names the bridge so
a future READY-gating slice does not re-derive it:

| SourceBinding element | Existing realization |
|---|---|
| HLD anchors | `hld_reference_map.json` (Journey 2) |
| Source package files | `source_package.json` + `source_manifest.json` SHA256 manifest |
| Target repo evidence | `target_discovery.py` reports, git lifecycle evidence |
| Toolchain evidence | `speckit_readiness.py`, `speckit_operator_state.py`, `specs/<branch>/` phase artifacts (read as `READ_ONLY_EVIDENCE`) |
| Lens outputs | Not yet implemented — `docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md` (lens registry, docs-only) |
| Helper/toolchain provenance | `helper_recommendations.json::registry_provenance` + this slice's `helper_selection.json::registry_provenance` (both carry `registry_sha256`) |
| Implementation slices | `implementation_slices.json` |

This slice does **not** implement a NextActionPacket or a READY gate — it only
makes the helper/toolchain provenance leg of this table real and checkable
(`helper_selection.recommendations_current`).

---

## 8. Inquiry/gap ledger (pointer)

Already specified, docs-only, separately gated: see
`docs/JOURNEY2_INQUIRY_LEDGER_CONTRACT.md`. Not duplicated here.

---

## 9. RunSkeptic questions for this contract

- **CH (inversion):** If a new driver write path bypassed `control_paths.resolve_hldspec_dir`, what breaks? External-state mode would write to a target-local path that gets deleted after externalization — the selection would silently vanish. `helper_selection.py` uses the resolver; the CLI mutation test does not currently run under external-state mode, which is a residual risk (see report).
- **OM (parsimony):** Does the five-zone model earn its place over a simple "is it under `.hldspec/`" check? Yes — without `ADAPTER_MIRROR` and `READ_ONLY_EVIDENCE` as distinct zones, either the `.specify/source/` mirror becomes unwritable (breaking existing behavior) or the rest of `.specify/`/`specs/` becomes writable by accident.
- **FE (mechanism):** Can a reader see *why* a path is forbidden? `classify_path` returns one of five named zones with a docstring rule, not a boolean.
- **PO (refutation):** Can a forbidden write pass silently? `is_forbidden_write` defaults to `True` for anything not explicitly approved (`AMBIGUOUS_ESCALATE` is forbidden, not permissive) — disprovable only by adding a path to `HLDSPEC_OWNED_PREFIXES`/`ADAPTER_MIRROR_PREFIXES` deliberately.
- **KT (universalizability):** Does the same five-zone model work for a second toolchain? Yes by construction (§6) — the zones are not SpecKit-specific; only the prefix tuples are.
- **SH (tradeoff):** One generic boundary module vs. refactoring `refresh_target.py` to use it — resolved in favor of the generic module standing alone for new code, with `refresh_target.py`'s existing classifiers left untouched (surgical-change discipline; avoids re-testing a working, already-enforced path for no behavior change).
