# Journey 3 Artifact Placement — Layout Decision Review (PR #29)

Status: conflict-record
Date: 2026-06-21
Scope: repo (HLDspec artifact placement; CONFLICT-003 reconciliation)
Owner: agent (read-only review; human ratifies the layout decision)
Canonical references: docs/JOURNEY3_DRIVER_DOGFOOD_20260621.md, docs/HLD_TO_TARGET_WORKSPACE.md,
docs/THREE_JOURNEYS.md, docs/JOURNEY2_PACKAGE_CONTRACT.md, hldspec/control_paths.py,
hldspec/run_state.py, hldspec/workspace_adapter.py, backlog CONFLICT-003 / P1-014 / P0-001

Read-only review. No implementation patched. No package relocated. No target mutated.

---

## RATIFIED DECISION (2026-06-21, human)

Option C is **ratified as the direction to implement** (analysis below is the record that led here):

- **HLDspec control-plane artifacts are externalized:** source package, helper recommendations,
  helper selection, sync queue / lifecycle / dependency graph, prompts / mediator guidance, run
  workspaces, architecture package.
- **Journey 3 delivered runtime artifacts remain in the target repo:** `.specify/`,
  `.specify/source/`, `.specify/memory/constitution.md`, `specs/`.
- **External root:** the **configurable sibling layout is first-class** —
  `~/code/flow.hldspec`, generally `<target-parent>/<target-name>.hldspec`. The **XDG state root
  is the zero-config fallback**. Sibling-vs-XDG must be **explicit in the placement contract**,
  never hidden behavior.
- **Target-clean means:** no HLDspec control-plane directories inside the real target repo. A
  pointer file is acceptable **only if explicitly chosen**, and preferably untracked/ignored. If
  no pointer is used, `--state-location` / environment config must be able to locate the external
  controller root.

This ratification reopens and resolves **CONFLICT-003** in favor of external-controller mode as
canonical for real/brownfield targets; in-target remains the explicit normal-mode option.
Implementation is a separate, gated step — nothing is patched here.

---

## CURRENT_STATE

- `main = 89b25ef` (PR #28 merge is main HEAD). PR #27 merged (`7729e2a`). PR #29 open **draft**
  (`af35c41`, 2 docs files). PR #26 open draft (Journey 2 authoring report, DO_NOT_PATCH).
- Two **committed but divergent** target models coexist in the docs:
  - **Generated-workspace model** (`HLD_TO_TARGET_WORKSPACE.md`): `target/` is a *generated*
    workspace; source is copied into `target/targetHLD/raw/`. In-target `.hldspec/` does not
    pollute *source* because the workspace is already separate.
  - **Delivery-into-real-repo model** (`THREE_JOURNEYS.md`, `JOURNEY2/3` contracts): Journey 3
    **delivers the package into a target repo** where the targeteer works. The "target repo" is a
    real existing repo (e.g. `~/code/flow`). Here in-target `.hldspec/` *does* pollute source.
- Externalization is **already partly implemented**, not hypothetical:
  - `run_state.py`: `CONTROL_ARTIFACTS = (".hldspec", "prompts")`; `default_runs_root()` is
    **external by default** (`$HLDSPEC_RUNS_DIR` or `~/.local/state/hldspec/runs/`); a
    `.hldspec-run.json` pointer in the target names the controller root.
  - `control_paths.py` (invariant C): all control sync reads/writes resolve via the pointer —
    `<controller>/.hldspec/sync` in external mode, `target/.hldspec/sync` in normal mode.
  - `workspace_adapter.TargetWorkspaceAdapter` has a `controller_root` field; when set,
    `hldspec_dir`/`source_package_dir` resolve under the controller.
  - CLI flag `start --state-location {target,external}` (default `target`) already lets a run
    "leave only `.hldspec-run.json` in the target."

## CONFLICT_003_SUMMARY

- **Prior decision (CONFLICT-003, RESOLVED):** HLDspec-owned review/planning artifacts live
  *inside* the target at `target/.hldspec/sync/`; events at `target/.hldspec/events.jsonl`;
  the driver's `layout="new"` source-package path is `target/.hldspec/source_package/`.
- **New dogfood/user decision:** the real source target stays **clean**; HLDspec-owned artifacts
  live in a **named external** location (user preference: sibling `~/code/flow.hldspec`).
- **Reconciliation (not a contradiction, a narrowing):** external-controller mode becomes the
  **canonical default for real/brownfield targets**; the in-target `target/.hldspec/` layout
  becomes the *normal-mode* option, not the only option. This matches what `control_paths` +
  `run_state` already encode. The user's "B" (externalize) is the direction; the only refinement
  is the **ownership line** below (`.specify/` was never going external).

## ARTIFACTS_AFFECTED (control-plane → external · delivered → in-target by design)

| Artifact | Owner | Placement |
|---|---|---|
| source package (`.hldspec/source_package/`) | HLDspec control plane | **external** |
| helper recommendations (`source_package/helper_recommendations.json`) | HLDspec control plane | **external** |
| helper selection (`.hldspec/helper_selection.json`) | HLDspec control plane | **external** |
| run-card / sync queue / lifecycle / dependency graph (`.hldspec/sync/`, queues) | HLDspec control plane | **external** |
| events (`.hldspec/events.jsonl`) | HLDspec control plane | **external** |
| prompts / mediator guidance (`prompts/`) | HLDspec control plane | **external** |
| run workspaces (run-id scratch) | HLDspec control plane | **external** (XDG `~/.local/state/hldspec/runs/` today) |
| architecture package (Journey 2 output, future PR #26 path) | HLDspec control plane | **external** (same rule as source package) |
| `.specify/source/` mirror, `.specify/memory/constitution.md`, `specs/` | SpecKit-owned **delivered** runtime | **in-target by design** (Journey 3 *delivers* into the repo; adapter hardcodes `specify_dir = target_root/.specify`) |

The dogfood already showed Option C half-working in the wild: the `.specify/source/` mirror and
constitution were present in `~/code/flow` (correct delivery), while the authoritative
`.hldspec/source_package/` was absent (control plane not externalized/bound there).

## CODE_PATH_ASSUMPTIONS

**Assume in-target / not pointer-aware (the gap):**
- `journey3_driver.py` — **no** pointer/controller resolution; calls
  `hld_source_package.source_package_paths(target, layout="new")`.
- `hld_source_package.source_package_paths` (read helper, line 319) and
  `build_source_package_content` (**write**, line 439) — construct the adapter **without**
  `controller_root` → always `target/.hldspec/source_package/`.
- `stale_check.py:174`, `mediator_guidance.py:557`, `session_control.py:543` — same.

**Already pointer-aware (the template + the inconsistency):**
- `speckit_operator_state._controller_source_package_dir` →
  `control_paths.resolve_hldspec_dir(target) / "source_package"`.
- `helper_selection.recommendations_path` → adapter with
  `controller_root=control_paths.resolve_controller_root(target)`.
- `control_paths.*` (all control-sync resolution); several `hldspec_agent_session.py` call sites
  (428, 832, 979, 1090, 1368) pass `controller_root`.

→ Threading is **ad-hoc per call site**. Read and write of the source package resolve
*inconsistently* in external mode (split-brain): the driver/build read/write target-local while
control sync and some CLI paths go to the controller. No current code writes
`<target>/.hldspec-runs/` (plural) — the dogfood scratch copy is a **legacy artifact**, not
current behavior.

## LAYOUT_OPTIONS

- **A. In-target (`target/.hldspec/...`)** — CONFLICT-003 status quo. Risk: pollutes a real
  brownfield repo; mixes HLDspec orchestration state with product git history; the targeteer's
  branch/commits carry HLDspec internals; "source target clean" is impossible.
- **B. External (everything HLDspec-owned outside the target).** Risk *if taken literally*: would
  wrongly externalize the `.specify/` mirror + constitution that Journey 3 is *supposed* to
  deliver into the repo. Discoverability cost depends on where the external root lives.
- **C. Boundary split (recommended):** externalize the **HLDspec control plane**; keep the
  **delivered SpecKit runtime** (`.specify/`, `specs/`) in-target. This is B's direction with the
  ownership line made explicit; both existing mechanisms (`control_paths`, adapter `controller_root`)
  already encode it.

## RECOMMENDED_DECISION

**Adopt Option C as the canonical layout** (confirms the user's externalize direction):

1. HLDspec control plane (`.hldspec/` + `prompts/` + run state) is **external** by default for
   real/brownfield targets; only `.hldspec-run.json` (a small pointer) remains in the target.
2. SpecKit-owned **delivered** runtime (`.specify/source/` mirror, `.specify/memory/constitution.md`,
   `specs/`) stays **in-target** — that is the Journey 3 delivery, not pollution.
3. "Source target clean" (**ratified**) = **no HLDspec control-plane directories inside the real
   target repo**. A pointer file is acceptable only if explicitly chosen, preferably
   untracked/ignored; if no pointer is used, `--state-location` / environment config must locate
   the external controller root. Everything else in the target is either the targeteer's product
   code or the intentionally-delivered SpecKit runtime.
4. **External root location (ratified):** the configurable **sibling** layout is first-class —
   `<target-parent>/<target-name>.hldspec` (e.g. `~/code/flow.hldspec`); the **XDG** state root
   (`~/.local/state/hldspec/runs/<run-id>/`) is the zero-config fallback. Sibling-vs-XDG must be
   explicit in the placement contract, never hidden (extend the existing `HLDSPEC_RUNS_DIR` /
   `--state-location` mechanism).

## MIGRATION_STRATEGY

- **Preserve legacy in-target `.hldspec/`:** yes — keep normal-mode (`--state-location target`)
  working; do not force-migrate existing in-target workspaces.
- **Prefer external when a pointer exists:** resolve through `control_paths` everywhere; a valid
  `.hldspec-run.json` pointer wins.
- **Detect both:** a target with both a controller pointer *and* stale in-target `.hldspec/`
  control state is **split-brain** → fail closed (consistent with `control_paths`' existing
  "broken pointer = untrusted lineage" stance and P1-011 binding `UNBOUND_LEGACY`).
- **Error on split-brain**, never silently pick one. No silent legacy fallback (already the
  `control_paths` rule).

## NEXT_SAFE_PATCH_SLICE

Smallest **correct** slice (read + write must resolve identically — fixing only the driver read
would *move* the split-brain, per the write-side check at `hld_source_package.py:439`):

> Route source-package path resolution through a **single pointer-aware resolver** (extend
> `source_package_paths` to resolve `controller_root` from the `.hldspec-run.json` pointer via
> `control_paths.resolve_hldspec_dir`, exactly like `speckit_operator_state._controller_source_package_dir`),
> and have **both** `journey3_driver` (read) and `build_source_package_content` (write) use it.
> Red→green test: build a package in external mode, assert the J3 driver discovers it at the
> controller location and reports `source_package_present: true`.

This is the layout-wiring slice referenced by backlog **P1-014** and the package-discovery work
in **P1-005**; it changes no gates, governance, or generation, and relocates nothing — it makes an
already-implemented mechanism consistent across the two source-package code paths. The
sibling-vs-XDG location decision (above) gates whether this slice also touches the default root.

## What must remain forbidden

No package relocation in this step; no Journey 1/2 generation; no helper execution; no SpecKit
execution; no `.specify/` mutation; no SourceBinding/governance change; no gate change; no merge;
do not close PR #29 or PR #26 without explicit approval; no hidden repair.

## PATCH_NOW: NO
