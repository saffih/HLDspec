# Journey 3 Driver — First Real Dogfood (2026-06-21)

Point-in-time dogfood result. Read-only run; no code patched; target not mutated.

## Run context

- **Real target:** `~/code/flow` (real brownfield project; its source code lives there).
- **HLDspec main at run time:** `89b25ef` (after merging PR #28 — `journey3-status` CLI surface).
- **Commands (all read-only, exit code 2 / BLOCKED):**
  - `scripts/hldspec journey3-status --target ~/code/flow`
  - `scripts/hldspec journey3-status --target ~/code/flow --json`
  - `scripts/hldspec journey3-status --target ~/code/flow --no-phase --json`
- **Mutation check:** content-hash manifest of all 703 non-`.git` files **identical** before/after; target HEAD unchanged; `git status` unchanged. Driver self-attests `mutated_target: false`, `executed_anything: false`. Nothing executed (no helper, no SpecKit, no toolchain).

## Driver result

`BLOCKED` / **PACKAGE_GAP**.

Key fields: `source_package_present: false`, `binding_status: UNBOUND_LEGACY`, `helper_selection_present: false`, `effective_helper: speckit (operational, propose_only_no_execution)`. Single blocker: *"Source package missing — return to Journey 2 to generate/import target/.hldspec/source_package/ before Journey 3."*

## Finding

The Journey 3 driver looks for source-package evidence in the real target at **`~/code/flow/.hldspec/source_package/`** (`journey3_driver.py` → `hld_source_package.source_package_paths(target, layout="new")`). That path does not exist in the real target.

The only source package found anywhere was generated **inside an HLDspec scratch copy** of the target, at **`~/code/flow/.hldspec-runs/flow-6f7f768.../.hldspec/source_package/source_package.json`**. HLDspec copied the target into that ephemeral run-workspace and packaged there. The driver never consults the scratch copy, so from the real target's point of view there is no package.

Package resolution is independent of binding: `source_package_paths` takes no binding argument and runs before binding is read, and `UNBOUND_LEGACY` produced no blocker of its own here. So the gap is package-absent-at-discovery-path, not a binding-trust failure → **PACKAGE_GAP** (root and symptom).

## Interpretation

This is an **HLDspec placement/wiring gap, not a problem with `~/code/flow`**. There are three locations in play that do not agree:

1. **Discovery** — where the driver looks: `~/code/flow/.hldspec/source_package/`.
2. **Emission** — where the package actually landed: ephemeral `~/code/flow/.hldspec-runs/<run-id>/.hldspec/source_package/`.
3. **Desired durable home** (placement decision below): external sibling `~/code/flow.hldspec/`.

Emission ≠ discovery ≠ desired durable home. That mismatch is the gap.

## Placement decision

Keep the real source target clean. HLDspec-owned artifacts should live in a **named external sibling directory**, preferably **`~/code/flow.hldspec`** — not buried in a scratch copy inside the real target (`.hldspec-runs/.../`).

### Open reconciliation — conflicts with existing CONFLICT-003

The backlog's **CONFLICT-003 (marked RESOLVED)** currently places HLDspec-owned artifacts *inside* the target: "HLDspec-owned review and planning artifacts live under `target/.hldspec/sync/`… event history under `target/.hldspec/events.jsonl`," with the driver's `layout="new"` discovery path `target/.hldspec/source_package/` consistent with that. The placement decision above (**external sibling, outside the target**) **supersedes/reopens CONFLICT-003** and must be reconciled before implementation. Related: CONFLICT-002 (target layout migration), P1-005 (package discovery & invocation wiring), P1-011 (source-package↔target binding, resolved 2026-06-12 — defines `UNBOUND_LEGACY`).

## PATCH_NOW: NO

No code change. Did not create directories, generate a package, run upstream Journey 1/2, or mutate `~/code/flow`. (Path B — upstream package generation — was explicitly declined and remains gated behind separate approval.)

## NEXT_SLICE recommendation

Define and implement an **external target-artifacts placement contract** so that:

- Journey 2 **emits/binds** the source package into the external sibling (`~/code/flow.hldspec`) rather than only into the ephemeral `.hldspec-runs/<run-id>/.hldspec/` scratch copy, and
- the Journey 3 driver can **locate** that package for `~/code/flow` (discovery path follows the placement contract instead of assuming in-target `target/.hldspec/source_package/`).

Precondition: reconcile with CONFLICT-003 (in-target vs external-sibling for all HLDspec-owned artifacts), since this is a layout-wide decision, not package-only.
