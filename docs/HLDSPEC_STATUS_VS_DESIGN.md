# HLDspec: status vs design — gaps, resources, usage

Written 2026-05-31 to answer "where are the gaps, missing resources, and usage?" after a
session that drove a real forward run on the Baton Flow HLD. The short answer: HLDspec
works and is materially more correct than a week ago, **but there are two parallel
implementations and the design (new layout) is ahead of what actually runs (old layout).**

## CORRECTION (2026-05-31, same day): not two engines — one engine, two front-ends

The table below originally framed this as "two competing implementations." On closer
inspection that was an overstatement. The new layout (`ProjectMachine`) **orchestrates
the same scripts** the old layout does — it calls `first_run_readonly.sh`,
`project_first_run.sh`, and the same `build_*`/`hld_spec_sync.py` generators, then
re-homes outputs via `TargetWorkspaceAdapter`. So:

- **All four content fixes** (resolve-before-escalate, dossier-from-HLD, rich specify
  input, plan implementation-marking) live in the **shared generator chain** that
  `first_run_readonly.sh` runs → **both front-ends already get them.**
- **Both front-ends had hermeticity** — old via `check_workspace_freshness.py` in
  `project_continue.sh`; new via the `start`/`diff` source-hash in `agent_session.py`.
- The **one real seam** was that `ProjectMachine._ensure_first_readonly` rebuilt only
  when `spec_build_plan_review.md` was *absent* — the same stale-skip bug fixed for the
  old layout. **FIXED 2026-05-31:** it now also rebuilds when the working HLD's sha256
  differs from a recorded fingerprint (`source_hld_fingerprint.txt`). Test:
  `tests_v2/test_project_machine_freshness.py` (red→green). 903 pass.

So "gap #1 = reconcile two layouts" was wrong. The accurate statement: there are two
**front-ends** over one engine; they are now consistent on hermeticity and share all
content fixes. What remains is **cosmetic/strategic** (pick one canonical front-end for
docs + usage), not a functional fork. Table retained below for the layout differences.

## The two front-ends (one engine underneath)

| | **Old layout (what actually ran this session)** | **New layout (what the backlog/design describes)** |
|---|---|---|
| Entry | `scripts/hldspec_run.sh` → `scripts/project_continue.sh` | `scripts/hldspec` → `hldspec_agent_session.py` (`start/status/review/continue/diff/doctor`) |
| Workspace | `.hldspec-first-run/.specify/sync/*.json` | `target/.hldspec/sync/`, `target/targetHLD/`, `target/.specify/` |
| SpecKit prompts | `.specify/sync/speckit_bundle_prompts/<runtime>/<bundle>/prompt.md` | `target/prompts/speckit/<package-id>/01-specify.md … 07-verify.md` |
| State | `hldspec_state.json` under `.specify/sync` | `target/.hldspec/agent_session.json` + `events.jsonl` |
| On the Flow run | **79 json artifacts produced; this is the path I drove end-to-end** | **0 files — never exercised on Flow** |

**This is the single biggest gap.** The product *design* (agent-first facade, stateless
external IO, `target/.hldspec/` layout) is documented and partially built in
`hldspec_agent_session.py`, but the **working, contamination-free, gated pipeline I fixed
and ran is the OLD `project_continue.sh` path.** They are not reconciled. A user reading
the backlog sees the new design; a user running `hldspec_run.sh HLD.md` gets the old one.

## What actually works today (old layout — verified this session)

End-to-end on the Baton Flow HLD, all fixed + tested this session:
- **Hermeticity gate** (`6fc57e8`) — refuses a stale workspace; `HLDSPEC_FRESH=1` clean rebuild.
- **Resolve-before-escalate** (`87f5d99`) — 22 heuristic questions → resolved from HLD, not escalated.
- **Dossier contracts from HLD, not keyword table** (`5aedbed`) — 0 contamination (was 23).
- **Rich specify input** (`8de47dc`) — first touch point hands SpecKit full HLD prose.
- **Plan marks built anchors** (`27e0578`) — implemented/deferred/not_built, no silent re-spec.
- Reaches `SPECKIT_PREWORK_APPROVAL_GATE` cleanly; prework quality gate enforces real blockers.

Self-assessed maturity (backlog scorecard, 2026-05-26): **overall 6/10** — foundational
contracts + several enforcement gates exist; not yet product-ready.

## Gaps (design vs reality), ranked

1. **~~Two unreconciled layouts~~ → DOWNGRADED (see Correction above).** It is one engine
   under two front-ends; all content fixes are shared and hermeticity is now consistent
   across both (fixed 2026-05-31). Remaining is **strategic, not functional**: pick ONE
   canonical front-end for docs/usage so "what is HLDspec's entrypoint?" has one answer.
   Recommendation: the agent-first `hldspec start/...` is the documented intent; make it
   the canonical surface and mark `hldspec_run.sh` as the maintainer/debug path.
2. **Forward SpecKit invocation is human-gated and only partially exercised.** The pipeline
   reaches the approval gate; actually running `/speckit-*` for all stages, by the book,
   end-to-end has only been done for HLD-014 specify (paused at checkpoint). clarify/plan/
   analyze/tasks/implement via the real tool across a full feature set: unproven.
3. **Keyword-heuristic surface (~10 scripts).** Two bugs this session were
   keyword-matching-meaning (over-escalation, dossier). The pattern likely recurs; needs an
   audit against the discriminator "correct on a differently-phrased HLD?" — fix the
   harmful, keep the legit (raw-HLD marking is legit: no anchors to read yet). NOT a sweep.
4. **No explicit "HLD is source of truth" enforcement rule.** The real thread behind the
   fixes ("be faithful to the current HLD") is not a named, checked rule the way
   `hld_verify_coverage` enforces "every HIGH-risk invariant has a test." Cheap, high-leverage.
5. **Implementation-status is drift-blind.** `anchor_implementation_status` = "anchor id
   cited in a declared test"; if HLD prose changes it still reads implemented. A per-anchor
   fingerprint (like the hermeticity sha) could detect drift. Deferred by design.
6. **Backlog's own open items (scorecard):** guarded product-flow integration, end-to-end
   journey coverage, domain validators, RunSkeptic status propagation through handoff/gate
   machine, full self-hosted SpecKit delegation.

## Resources (where things live)

- **Design/contracts:** `docs/CANONICAL_FLOW.md`, `HLDSPEC_ORCHESTRATION_CONTRACT.md`,
  `HLDSPEC_USE_CASES_AND_API.md`, `HLDSPEC_AGENT_COMMAND.md`, `SOFTWARE_DESIGN_PRINCIPLES.md`.
- **Backlog/scorecard:** `docs/HLDSPEC_DEVELOPMENT_BACKLOG.md` (the 6/10 mark + open items).
- **Old-layout engine (what runs):** `scripts/project_continue.sh`, `scripts/first_run_readonly.sh`,
  `hld_spec_sync.py` (planner), `scripts/build_*` (per-artifact generators), `hldspec/spec_bundle_prompts.py`.
- **New-layout facade (the design):** `scripts/hldspec` → `scripts/hldspec_agent_session.py`,
  `hldspec/machines/`, `target/.hldspec/`.
- **Skeptic framework:** `~/code/skeptic/skeptic.md` (read at runtime, never from memory).

## Usage (how to actually run it, today)

Working path, old layout, on a project repo with an anchored `HLD.md`:

```bash
cd <project>                                   # e.g. ~/code/flow
HLDSPEC_FRESH=1 ~/code/HLDspec/scripts/hldspec_run.sh HLD.md   # clean rebuild
~/code/HLDspec/scripts/hldspec_run.sh HLD.md                   # continue to next gate
# (HLDSPEC_SKIP_PREFLIGHT=1 to bypass the slow/flaky preflight)
```

This stops at `SPECKIT_PREWORK_APPROVAL_GATE`. After human approval, the by-the-book
forward run drives the real `/speckit-*` skills (specify → clarify → plan → analyze →
tasks → implement), feeding SpecKit the enriched bundle inputs.

The documented agent-first facade (`hldspec start <hld> <target>` …) is the *intended*
usage but is the **unreconciled new layout** — not the path proven on Flow.

## Bottom line

HLDspec **works and is correct on the path that was exercised** (old layout, 6/10,
contamination-free, gated). The **design is ahead of the running code**: the agent-first
new layout is partly built and unproven. The top design decision is **#1 — reconcile the
two layouts** (migrate forward, or retire one). Everything else (#2–#6) is bounded backlog.
