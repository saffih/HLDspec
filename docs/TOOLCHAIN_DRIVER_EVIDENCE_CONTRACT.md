# Toolchain Driver Evidence Contract

**Status:** design contract, **PROPOSED** — no code in this repo implements the
`DRIVER_OBSERVED` / `MANUAL_ATTESTED` / `DRIVER_VERIFIED_STATE` / development-receipt
vocabulary below. This doc names the boundary **before** any driver evidence-writing
behavior is built, so a future implementation slice has a contract to fill rather than
inventing provenance rules ad hoc. It does not redefine the Driver/Helper vocabulary
(owned by [`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md)), the ownership
zones (owned by [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md)), or the
helper authority model (owned by [`JOURNEY3_HELPER_CONTRACT.md`](JOURNEY3_HELPER_CONTRACT.md)).
It adds one axis those docs do not cover: **who produced a piece of evidence, and
whether the driver actually watched it happen.**

**Role clarification (does not redefine, only restates precisely):** HLDspec is
the specification/control framework — it provides materials, contracts, skills,
agent prompts, and the Journey 3 driver/helper capability described here. HLDspec
itself is not "the driver." The Journey 3 driver/helper may invoke or guide a
toolchain and observes what happened, but the **toolchain** performs the actual
target-repo work; target-repo mutations are attributed to the toolchain, even
when the driver/helper initiated or guided the run. Any evidence the driver/
helper writes is sidecar/control-plane evidence — written outside the target
repo proper, into HLDspec's own control/sync-plane state (the `HLDSPEC_OWNED`
zone per `TOOLCHAIN_DRIVER_BOUNDARY.md` §2) — never a direct mutation of the
target repo's product files, and never a mutation of Flow or any other
target-side system.

---

## 1. Why this doc exists

`hldspec/next_feature_readiness.py` already reads a durable evidence file
(`next_feature_execution_evidence.json`, `EXECUTION_EVIDENCE_FILE`) to decide whether
implementation/commit/push has happened, and a recent hardening slice
(`_read_execution_evidence`, feature-identity + commit-ancestry guards) made that
reader stricter. The next candidate slice (recorded in
`docs/flow_journey3/flow-post-implement-status-decision-record.md`, "Selected: A") is
to make the driver **itself** observe SpecKit analyze/implement phases rather than only
reading whatever evidence happens to be on disk. Before that slice is built, the
provenance/authority distinctions below need to be named — otherwise "the driver says
this happened" and "someone told the driver this happened" collapse into the same
evidence field, which is exactly the failure mode this doc exists to prevent.

## 2. Vocabulary

| Term | Status | Meaning |
|---|---|---|
| Toolchain | **EXISTS** | The tool that performs the work (SpecKit today; Codex, Claude Code, manual editing, or a future tool generally). It does not know HLDspec's evidence format and is not coupled to it. |
| Driver | **EXISTS** | The Journey 3 driver/helper capability HLDspec provides — not HLDspec as a whole — that invokes the selected toolchain through a bounded adapter/execution boundary, observes the returned result, and owns normalized sidecar/control-plane evidence writing plus the audit/reporting needed to improve HLDspec and the driver itself. It does not write to the target repo's product files. See `hldspec/journey3_driver.py`, `hldspec/toolchain_driver.py`. |
| `DRIVER_OBSERVED` (evidence class) | **PROPOSED** | Evidence produced *only* when the driver itself invoked the toolchain and observed the result. Not implemented; no evidence file in this repo currently carries a provenance tag at all. |
| `MANUAL_ATTESTED` / `DRIVER_VERIFIED_STATE` (evidence class) | **PROPOSED** | A separate, not-yet-designed evidence class for work the driver did not invoke (human ran a command directly, another agent bypassed the driver). Names are placeholders for a future slice to design, not a committed schema. |
| Development receipt | **PROPOSED** | A future record the driver may write to help improve HLDspec, prompts, contracts, and adapters. Distinct artifact from readiness evidence; not built here. |
| Readiness evidence | **EXISTS** | Evidence read by `next_feature_readiness.py` to derive `phase`/`safety_status`. Today: `next_feature_execution_evidence.json` only. |

## 3. Driver / Toolchain boundary

- The **toolchain performs the work**. It may vary (SpecKit is the only operational
  one today; Codex, Claude Code, manual work, and future tools are all toolchains in
  this sense). A toolchain is not required to know, and must not be made to know,
  HLDspec's evidence file format — coupling evidence format into the toolchain would
  make every future toolchain re-implement HLDspec's bookkeeping.
- The **driver belongs to HLDspec** — it is a capability HLDspec provides, not
  HLDspec itself. It invokes the selected toolchain through a bounded adapter/
  execution boundary (the ownership zones in `TOOLCHAIN_DRIVER_BOUNDARY.md`
  already bound *what* the driver may touch; this doc is about *what it may
  claim it saw*), observes the returned result, and owns normalized evidence
  writing plus the audit/reporting that helps improve HLDspec and the driver.
  All evidence the driver writes is sidecar/control-plane evidence — it lands in
  HLDspec's own control/sync-plane state (`HLDSPEC_OWNED`, `TOOLCHAIN_DRIVER_BOUNDARY.md`
  §2), never as a direct write into the target repo's product files, and never
  into Flow or any other target-side system. Product-file mutations in the
  target repo are the toolchain's, and are attributed to the toolchain, even
  when the driver initiated or guided the run that produced them.
- The nearest **EXISTS** mechanism for "driver invoked the toolchain and observed the
  result" is `SpecKitInvoker.InvocationResult.verified`
  (`hldspec/speckit_invoker.py`): a command is only treated as having done something
  if it exited successfully *and* (for artifact-producing phases) the project's git
  signature actually changed — the anti-hollow-completion gate referenced in
  `TOOLCHAIN_DRIVER_BOUNDARY.md` §4. This is the closest thing to an "observed" signal
  in the repo today. It is **not** wired to write `next_feature_execution_evidence.json`
  or any tagged evidence file, and the `SpecKitInvoker`/drive-loop path it belongs to
  is itself the opt-in `EXECUTE_WITH_APPROVAL` path, self-acknowledged unproven per
  `TASKS.md` (`TOOLCHAIN_DRIVER_BOUNDARY.md` §5) — not the Journey 3 default.

## 4. Readiness evidence rule

`DRIVER_OBSERVED` evidence, once implemented, may be produced **only** when the driver
invoked the toolchain itself and observed the result (e.g., through something like
`InvocationResult.verified` above). This evidence may feed readiness/status logic
(`next_feature_readiness.py`'s phase derivation).

**Current state, stated plainly:** `next_feature_execution_evidence.json` exists today
and is already read by `next_feature_readiness.py`
(`EVIDENCE_TESTS_PASSED` / `EVIDENCE_IMPLEMENTED_COMMITTED` / `EVIDENCE_PUSHED`). But
the code comment at `next_feature_readiness.py:97-99` is explicit: *"HLDspec never
writes this file; it only reads it to avoid inferring implementation/push state beyond
what is recorded."* No invocation path in this repo writes it, and
its schema carries no provenance field. **Its existing/legacy entries must never be
read or represented as `DRIVER_OBSERVED`** — they are, by this doc's own taxonomy,
unclassified evidence of unknown provenance (in practice, human- or CI-recorded).
Retroactively assigning them a provenance class is future work for whoever designs the
`DRIVER_OBSERVED` write path, not an assumption this doc or any reader may make today.

`next_feature_execution_evidence.json` is a **readiness evidence artifact**, not a
learning ledger. Nothing about that changes here.

## 5. Manual bypass rule

If the user or another agent runs work outside the driver (runs SpecKit commands
directly, edits the project by hand, or otherwise bypasses the bounded adapter/
execution boundary), **the driver did not observe it**. The driver must not produce
`DRIVER_OBSERVED` evidence for manual work, no matter how the resulting state looks on
disk.

Manual work requires its own, separate, not-yet-designed evidence class — placeholder
names `MANUAL_ATTESTED` or `DRIVER_VERIFIED_STATE` — so that "the driver watched this
happen" and "the driver later verified the resulting state some other way" stay
distinguishable from each other and from `DRIVER_OBSERVED`. Designing that class,
including whether/how it feeds readiness at all, is explicitly out of scope for this
doc and for the next driver-observability slice referenced in §1.

## 6. Development / learning receipts

The driver may, in a future slice, write development receipts to help improve
HLDspec, prompts, contracts, and adapters. Two rules bound this, both currently
unimplemented:

- Development receipts must **never** count as readiness evidence. They must not be
  written into, read from, or merged with `next_feature_execution_evidence.json` or
  any future readiness-evidence file.
- Development receipts must not **silently** affect phase promotion, merge decisions,
  readiness status, or execution status. If a development receipt is ever meant to
  influence any of those, that influence must be an explicit, reviewed decision, not
  an emergent side effect of receipts and readiness evidence sharing a file, a reader,
  or a schema.

This is a distinct concern from the "durable SpecKit invocation log" follow-up already
recorded as its own, separately-scoped future item in
`docs/flow_journey3/flow-post-implement-status-decision-record.md` ("Open follow-ups",
item 6: "lives ONLY in point-in-time implement record; not in TASKS.md ... risk of
being missed"). That log is audit durability, not readiness evidence, and not a
development receipt either — the three stay separate, unbundled concepts. Nothing here
builds any of them.

## 7. RunSkeptic questions for this contract

- **CH (inversion):** If a future slice let the driver write `DRIVER_OBSERVED`
  evidence for anything it merely *sees on disk* (rather than something it invoked and
  watched complete), what breaks? Readiness status would silently accept manual/
  bypassed work as driver-verified, defeating the entire point of the distinction —
  the rule in §5 (manual bypass never yields `DRIVER_OBSERVED`) is the guard against
  this.
- **OM (parsimony):** Does a separate evidence-provenance doc earn its place over
  folding this into `TOOLCHAIN_DRIVER_CONTRACT.md`? Yes for now: that contract is
  explicitly scoped to the v0, report-only driver (no invoke-and-observe path exists
  yet), while `DRIVER_OBSERVED` presupposes the `EXECUTE_WITH_APPROVAL` invoke path.
  The two contracts describe different maturity stages of the same driver; merging
  them would force a not-yet-built capability into a doc that currently, correctly,
  describes only reporting.
- **FE (mechanism):** Can a reader tell today whether any entry in
  `next_feature_execution_evidence.json` is driver-observed? No — and §4 says so
  explicitly rather than implying otherwise. That is the honest current mechanism gap
  this doc names without closing.
- **PO (refutation):** Can manual work masquerade as `DRIVER_OBSERVED` once this is
  implemented? Only if a future writer skips the invocation-and-observation step and
  writes the tag anyway — §5 states the rule un-conditionally so that any such writer
  is a documented contract violation, not an ambiguous judgment call.
- **KT (universalizability):** Does "toolchain performs, driver observes and writes
  evidence, evidence carries provenance" hold for every future toolchain (Codex,
  Claude Code, a future ISG Governance driver per `TOOLCHAIN_DRIVER_BOUNDARY.md` §6)?
  Yes by construction — nothing here is SpecKit-specific; only `SpecKitInvoker` is.
- **SH (tradeoff):** Building the full `DRIVER_OBSERVED`/`MANUAL_ATTESTED` schema now
  vs. naming the boundary first — resolved in favor of naming first. The schema
  requires product decisions (does `MANUAL_ATTESTED` feed readiness at all? what
  authority approves it?) that are out of scope for a docs-only slice; building it
  without those decisions would be exactly the "no confusion between driver-observed
  and manual-attested evidence" failure this doc exists to prevent.

## 8. See also

- [`TOOLCHAIN_DRIVER_CONTRACT.md`](TOOLCHAIN_DRIVER_CONTRACT.md) — Driver vs Helper
  vocabulary, v0 report-only scope.
- [`TOOLCHAIN_DRIVER_BOUNDARY.md`](TOOLCHAIN_DRIVER_BOUNDARY.md) — ownership zones,
  the anti-hollow-completion gate (§4), the SpecKit driver path (§5).
- [`JOURNEY3_HELPER_CONTRACT.md`](JOURNEY3_HELPER_CONTRACT.md) — helper authority
  levels (`GUIDE_ONLY` / `PROPOSE_COMMAND` / `EXECUTE_WITH_APPROVAL` /
  `AUTONOMOUS_WITH_GUARDS`).
- [`JOURNEY3_CONTROLLER_TARGET_AGENT_BRIDGE.md`](JOURNEY3_CONTROLLER_TARGET_AGENT_BRIDGE.md) —
  controller/target/agent-bridge terminology (a different axis: where files live, not
  who produced them).
- `hldspec/next_feature_readiness.py` — `EXECUTION_EVIDENCE_FILE`,
  `_read_execution_evidence` — the existing readiness-evidence reader this doc's
  vocabulary will eventually extend.
- `hldspec/speckit_invoker.py` — `InvocationResult.verified` — the nearest existing
  invoke-and-observe mechanism.
- `docs/flow_journey3/flow-post-implement-status-decision-record.md` — the decision
  record that selected the next driver-observability slice this doc prepares for.
