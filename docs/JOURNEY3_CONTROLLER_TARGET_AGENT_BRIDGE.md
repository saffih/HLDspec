# Journey 3 — Controller / Target / Agent-Bridge Terminology

**Status:** design + terminology proposal. This doc names the controller / target /
helper / agent-bridge architecture so UX and future implementation share one
vocabulary. It is **partly descriptive** (it names mechanisms that already exist —
the external-controller pointer, the control-plane resolver, the helper registry/
selection) and **partly forward-looking** (the agent bridge, `bridge.json`,
`SKILL.md`, `command_envelope`, the convenience symlink — *not yet implemented*).
Each term below is tagged **EXISTS** or **PROPOSED** so the doc never pretends code
exists that does not.

**Authority:** this doc **defers to
[`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) on any conflict**
(that doc is canonical and wins). It does not redefine ownership zones — those are
owned by [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md). It does not
redefine the helper model — that is owned by
[`JOURNEY3_HELPER_CONTRACT.md`](JOURNEY3_HELPER_CONTRACT.md) and
[`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md). It adds **naming and a
UX operating model** over those contracts; it is not a competing source of truth.

---

## 1. Why this terminology is needed

HLDspec runs over three distinct directories that are easy to conflate, plus a
toolchain helper and (future) an agent doorway. Conflating them causes the real
failure mode already observed in dogfooding: the **target silently accumulating
HLDspec control-plane state**, or an agent looking in the target for control files
that live under an external controller. The terms below make the four roots, the
helper runtime, and the agent doorway nameable and ownable.

---

## 2. Glossary

| Term | Status | One-line meaning |
|---|---|---|
| `hldspec_tool_root` | **EXISTS** | The HLDspec implementation/tool repo. |
| `controller_root` | **EXISTS** (external mode) | Per-target HLDspec control/persistence directory. |
| `control_state_root` | **EXISTS** | The resolved `.hldspec/` control plane (in-target by default, under the controller when externalized). |
| `target_root` | **EXISTS** | The real product repo/workspace. |
| `helper_runtime_capsule` | **EXISTS** (as artifacts); name **PROPOSED** | The minimal target-resident files a selected helper needs. |
| `helper_adapter` | **EXISTS** (as the Toolchain Driver); name **PROPOSED** | HLDspec-side code that knows how to drive a specific helper. |
| `agent_bridge` | **PROPOSED** | An agent-discoverable doorway describing the controller↔target binding. |
| `bridge.json` | **PROPOSED** | Machine-readable binding metadata for the agent bridge. |
| `SKILL.md` | **PROPOSED** | Human/agent-readable operating contract in the bridge. |
| `command_envelope` | **PROPOSED** | A bounded, approval-aware description of one helper/tool action. |
| controller-first operation | **PROPOSED** (UX) | Driver invoked from the controller / with `--controller`. |
| target-working-dir execution | **EXISTS** | Agents/helpers execute from the target; control metadata stays controller-owned. |
| Target Controller Link | **PROPOSED** | Optional convenience symlink from target to controller bridge. |

### 2.1 `hldspec_tool_root` — **EXISTS**

The HLDspec implementation repo or installed tool location (e.g. `~/code/HLDspec`).
Owns generic driver code, journey logic, the helper registry
(`hldspec/helper_registry.py`), helper adapters/toolchain driver, and policy code.
It is **tool code**, reused across many targets. It is **not** a target-specific
controller and holds no per-target control state.

### 2.2 `controller_root` — **EXISTS** (external-controller mode)

The external, per-target HLDspec controller directory that holds the control/
persistence state for **one** target. It is neither the product repo nor the tool
repo.

- **Binding reality:** the authoritative binding is the pointer file
  `.hldspec-run.json` written in the target (`hldspec/run_state.py`, field
  `controller_root`). `control_paths.resolve_controller_root(target)` reads it. The
  controller root is **wherever that pointer names** — it may be any path.
- **Naming convention (PROPOSED):** a sibling `~/code/flow.hldspec` for target
  `~/code/flow` is the recommended human convention, but it is **not** enforced; the
  dogfood run placed controller state under `.hldspec-runs/`. The pointer is
  authoritative; the directory name is ergonomic only.

### 2.3 `control_state_root` — **EXISTS**

The resolved `.hldspec/` control plane. It owns the source package + manifest +
binding, helper recommendation/selection, session plan, subagent packets, reports,
receipts, driver status, queues, and protected approval state.

**Mode-dependent location (this is the rule — never state it flat):**

- **Normal/default mode (no pointer):** `target_root/.hldspec/`. This is the
  canonical, implemented default described in
  [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md)
  ("HLDspec Control Plane — `target/.hldspec/`").
- **External-controller mode (pointer present):** the *same* control plane resolves
  to `controller_root/.hldspec/` (Option C; PR #30/#32/#33/#34/#35). Externalization
  copies control state to the controller and removes the in-target `.hldspec/`.

So `control_state_root` = "the resolved `.hldspec/` — in-target by default, under the
controller once a pointer externalizes it," not "always under the controller." The
resolver (`control_paths.resolve_hldspec_dir` / `resolve_control_sync_dir`,
`hld_source_package.source_package_paths`) is the single place that decides.

### 2.4 `target_root` — **EXISTS**

The real target/product repo or workspace (e.g. `~/code/flow`). Owns product code,
product tests, and — when a helper is installed — the target-local
`helper_runtime_capsule`.

**Honest statement about "ownership" (avoids the "target is empty/clean" trap):** in
external-controller mode the target should hold **only** the helper runtime capsule
plus the `.hldspec-run.json` pointer, *not* the control plane. In normal/default mode
the target legitimately holds `target/.hldspec/` (the control plane itself). The
target is therefore never "empty"; what it owns depends on the mode. The aspiration
"target must not silently accumulate control-plane state" applies specifically to
**external mode**, where leaked in-target control state is a split-brain hazard
(detected fail-closed by `hld_source_package.source_package_split_brain`).

### 2.5 `helper_runtime_capsule` — artifacts **EXIST**; name **PROPOSED**

The minimal, explicit set of **target-resident** files a selected helper needs to
operate. For SpecKit this is the `ADAPTER_MIRROR` zone `.specify/source/` plus the
SpecKit runtime (`.specify/`, `.specify/memory/constitution.md`, `specs/`).

- It is **delivered/runtime** material, **not** HLDspec control state. It must live in
  the target because SpecKit executes there (it reads `.specify/`, writes `specs/`).
- It must be **idempotently generated** and **explicitly owned**. Ownership is already
  defined by [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md): the mirror
  is `ADAPTER_MIRROR` (generated, banner-stamped, never authoritative); the rest of
  `.specify/`/`specs/` is helper-owned runtime. `helper_runtime_capsule` is just the
  **name for that target-resident set as a whole** — it does not introduce a new
  ownership zone.
- **Why SpecKit needs target-local artifacts:** SpecKit's `specify → plan → tasks →
  implement` ritual runs in the product repo and persists into `.specify/` and
  `specs/`. The capsule is the in-target surface that makes the helper runnable; the
  authoritative source remains the control plane (mirror is read-only, regenerated).

### 2.6 `helper_adapter` — **EXISTS** (as the Toolchain Driver); name **PROPOSED**

HLDspec-side code that knows how to use a specific helper/toolchain (e.g. SpecKit).
This is the existing **Toolchain Driver** role
([`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md),
`hldspec/toolchain_driver.py`, `hldspec/helper_selection.py`); `helper_adapter` is a
**naming alias** for that adapter role, not a new component.

The adapter knows the helper's required runtime capsule, readiness checks, command
shapes, expected outputs, and forbidden areas. It **does not replace the helper** and
**does not own product truth**. The generic driver delegates helper-specific
knowledge to the adapter.

### 2.7 `agent_bridge` — **PROPOSED** (not implemented)

An agent-discoverable skill/doorway letting an agent that starts in **either** the
controller or the target discover the binding and the safe operating rules.

- **Preferred canonical cross-agent location:** `.agents/hldspec/`.
- **Provider-specific shims (optional):** `.devin/hldspec/`, `.claude/hldspec/`,
  `.codex/hldspec/` — each should point to or include the canonical `.agents/hldspec/`
  bridge rather than fork it.
- The bridge is a **doorway / instruction surface**, **not** the controller and
  **not** an authority. (See §5 — it confers no approval power.)

### 2.8 `bridge.json` — **PROPOSED** (not implemented)

Machine-readable binding metadata for the agent bridge: controller root, target root,
control state root, selected helper, and mode. Must be **validated by the driver**;
broken or ambiguous binding must **fail closed** (BLOCKED). It would mirror, not
replace, the authoritative `.hldspec-run.json` pointer.

### 2.9 `SKILL.md` — **PROPOSED** (not implemented)

The human/agent-readable operating contract inside the bridge: what to read, where to
work, what may be written, and what is protected. It must read correctly whether the
agent starts in `controller_root` or `target_root`.

### 2.10 `command_envelope` — **PROPOSED** (not implemented)

A bounded description of one proposed helper/tool action, so the **driver proposes
actions without becoming the helper**. Fields: working directory; command/instruction;
required reads; allowed writes; forbidden writes; expected outputs; approval
requirement; helper mode. It is the same shape already carried informally by the
session subagent packets (`hldspec/session_control.py`) — formalizing it is future
work.

### 2.11 controller-first operation — **PROPOSED** (UX direction)

The intended normal operation: a human runs the driver from `controller_root` or
passes `--controller`, with `--target` explicit. **Today** the resolver defaults to
**in-target** unless a `.hldspec-run.json` pointer exists, so controller-first is a UX
*direction*, not the current default. Explicit flags must always beat discovery.

### 2.12 target-working-dir execution — **EXISTS**

Agents/helpers usually execute **from the target root**, because product/toolchain
work happens there (SpecKit reads `.specify/`, edits `specs/` and product code).
Instructions, packets, receipts, reports, and control metadata remain
**controller-owned** unless they are specifically target-runtime material (the
capsule). The session role commands already run "in `{target}`" while reading packets
from the resolved control plane (PR #33/#34/#35).

### 2.13 Target Controller Link — **PROPOSED** (not implemented)

An optional convenience symlink from target to controller bridge. Constraints:

- **Must not** be named `.hldspec` by default (that name is the control plane).
- Preferred path: `target_root/.agents/hldspec → controller_root/.agents/hldspec`.
- Must be **ignored/untracked** unless intentionally supported.
- Must **not** be canonical over an explicit `--controller`.
- A broken or mismatched link is **BLOCKED**.

> This doc does **not** create any symlink in any real target. The link is a described
> convenience, not an action taken here.

---

## 3. Directory examples

```
~/code/HLDspec                                  = hldspec_tool_root      (EXISTS)
~/code/flow.hldspec                             = controller_root        (EXISTS; name PROPOSED convention)
~/code/flow.hldspec/.hldspec                    = control_state_root     (EXISTS; external mode)
~/code/flow                                     = target_root            (EXISTS)
~/code/flow/.specify/, .specify/source/, specs/ = helper_runtime_capsule (EXISTS as artifacts)
~/code/flow/.hldspec-run.json                   = binding pointer        (EXISTS; authoritative)
~/code/flow/.agents/hldspec
   -> ~/code/flow.hldspec/.agents/hldspec       = Target Controller Link (PROPOSED; not created here)
```

In **normal/default mode** (no pointer) the same target instead holds its control
plane in-target at `~/code/flow/.hldspec/`, and there is no controller_root.

---

## 4. Architecture principles

1. **Controller owns** decisions, orchestration, session state, packets, source
   package, approvals, and reports.
2. **Target owns** product code and the helper runtime capsule.
3. **Helper adapter** (Toolchain Driver) knows how to use the toolchain but **does not
   become the helper** and does not own product truth.
4. **Agent bridge** (proposed) makes the controller↔target binding discoverable to
   agents; it is a doorway, not an owner.
5. **Driver** can run from the controller or with explicit `--controller`/`--target`.
6. **Agent** may work from the target but must read controller-owned packets/
   instructions.
7. **Symlink/bridge is ergonomics, not authority.**
8. **Explicit flags beat discovery.**
9. **Ambiguous discovery fails closed** (BLOCKED).
10. In **external mode**, the target must not silently accumulate control-plane state
    (split-brain is detected and fails closed).
11. **Helper runtime in the target is allowed only when explicitly declared/selected**
    (helper selection is controller-owned).

---

## 5. UX / work cycle

Steps marked **(proposed)** depend on the not-yet-implemented bridge; the rest
describe existing mechanisms.

1. Human runs the driver from `controller_root`:
   `hldspec journey3-status --target <target_root>`.
2. Driver validates the controller↔target binding (today: `.hldspec-run.json` +
   split-brain check; **(proposed)** `bridge.json`).
3. Driver identifies the selected helper and helper-runtime status
   (`helper_selection.py`, readiness checks).
4. If helper runtime is missing, driver **proposes** materializing the
   `helper_runtime_capsule` (it does not auto-apply).
5. Human **approves** the protected transition (approval is controller-owned).
6. HLDspec / helper adapter idempotently materializes the target-local capsule
   (`.specify/source/` mirror, etc.).
7. Driver creates controller-owned session packets (`write_session_artifacts`).
8. Agent starts in `target_root`.
9. **(proposed)** Agent discovers `.agents/hldspec/SKILL.md`.
10. **(proposed)** Agent resolves controller/target via `bridge.json` (today: reads
    the resolved control plane via the pointer).
11. Agent reads its packet from the **controller-owned** control plane.
12. Agent works **only** in allowed target files (per packet `allowed_files`).
13. Agent writes receipts/reports **only** to approved controller report locations.
14. Driver validates reports and gates continuation (`session_continue_preflight`,
    gate validator).

**Starts-from-controller vs starts-from-target:** the model must work both ways. From
the controller, `--target` makes the target explicit. From the target, the
`.hldspec-run.json` pointer (today) / bridge (proposed) resolves the controller. Either
way, control artifacts stay controller-owned and the agent executes in the target.

---

## 6. Safety / fail-closed rules

- The **agent bridge confers no authority by itself.** Approval gates remain
  controller-owned whether or not a bridge exists; a bridge cannot grant or imply
  approval.
- A bridge **must not override protected approvals.**
- A helper/agent **must not edit** source-package truth, binding, helper selection,
  governance, or approvals (these are controller-owned, protected state).
- If controller/target identity does **not** match the binding → **BLOCKED.**
- If the bridge is **missing**, the driver still works with explicit paths
  (`--controller`/`--target`).
- If the bridge is **broken or ambiguous** → **BLOCKED** (no guessing).
- If a symlink points to an **unexpected location** → **ACTION/BLOCKED.**
- The bridge must **not** cause recursive tool traversal into the controller unless
  explicitly intended (avoid an agent scanning the controller as if it were product
  code).
- Writes "through the bridge" must be restricted to **approved receipt/report paths**.
- **Split-brain** (control plane present in *both* controller and target in external
  mode) is **BLOCKED**, never auto-reconciled
  (`hld_source_package.source_package_split_brain`).

---

## 7. Not yet implemented (this slice is terminology + UX only)

This slice defines vocabulary and the operating model. It changes **no code
behavior**. The following are **named here but not implemented**:

- `agent_bridge` discovery (`.agents/hldspec/`) and provider shims
  (`.devin|.claude|.codex/hldspec/`).
- `bridge.json` schema and driver validation.
- `SKILL.md` bridge contract.
- `command_envelope` as a formal type (the session packets are its informal
  precursor).
- `Target Controller Link` symlink support.
- The `controller_root` directory-naming convention (`flow.hldspec`) as anything more
  than an ergonomic suggestion — the `.hldspec-run.json` pointer remains authoritative.
- A static guard that fails closed on accidental in-target control-plane accumulation
  in external mode (today only split-brain on the source package is detected).

---

## 8. Backlog follow-ups

Tracked in [`HLDSPEC_DEVELOPMENT_BACKLOG.md`](HLDSPEC_DEVELOPMENT_BACKLOG.md):

1. Implement agent-bridge discovery (`.agents/hldspec/`).
2. Implement `bridge.json` validation (fail closed on broken/ambiguous binding).
3. Implement optional provider-specific shims pointing at the canonical bridge.
4. Formalize `command_envelope` (lift the session-packet shape into a typed seam).
5. Add a static guard for accidental control-plane accumulation in the target
   (external mode).
6. **Reconcile** the canonical
   [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) in-target
   control-plane description (`target/.hldspec/`) with the implemented Option-C
   external-controller mode, so the canonical doc reflects both modes.

---

## 9. See also

- [`HLDSPEC_TERMINOLOGY_AND_FLOW.md`](HLDSPEC_TERMINOLOGY_AND_FLOW.md) — **canonical**
  terminology/ownership/flow (wins on conflict).
- [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md) — ownership zones
  (`HLDSPEC_OWNED` / `ADAPTER_MIRROR` / `READ_ONLY_EVIDENCE` / …).
- [`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md) — Driver vs Helper.
- [`JOURNEY3_HELPER_CONTRACT.md`](JOURNEY3_HELPER_CONTRACT.md) — helper model and
  authority levels.
- [`AGENT_ARTIFACT_HYGIENE.md`](AGENT_ARTIFACT_HYGIENE.md) — where artifacts may live.
