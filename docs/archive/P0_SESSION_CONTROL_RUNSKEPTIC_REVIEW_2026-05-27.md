# RunSkeptic Review — P0 Session-Plan + Bounded-Subagent Control Plane

Read-only RunSkeptic review of the P0 control-plane plan, performed before
implementation as the prompt (§14) requires.

Final category: **HANDLED** — proceed to implement. No blocking CONFLICT; the plan
aligns with the already-resolved source-package ownership (C1). Three substantive
findings are folded into the implementation decisions below.

---

## RunSkeptic Receipt

- **Source read:** `/Users/saffi/code/skeptic/skeptic.md`, sha256
  `c5f60f48a09660e63fb09cf2a464185f928608ba5823fa7284aff6c56e9959bb` (re-confirmed
  unchanged this session). Read in full earlier this session.
- **Companion files read:** none required (design-level review).
- **Permission mode:** read-only (this review performs no edits).
- **DONE statement:** "Decide whether the P0 session-plan + bounded-subagent control
  plane can be implemented as specified; surface ownership/SoT/failure-signal risks;
  confirm the control plane will be *real* (gate-validator actually blocks
  continuation) rather than documentation." Testable: §13 of the prompt gives an
  explicit acceptance test list.
- **Major steps run:** GATE, FUNDAMENTAL SCAN, MAP, CONFIDENCE, STABILIZE, EVIDENCE,
  DECIDE. (ACT happens in the implementation step that follows, not in this review.)
- **Thinkers considered:** CH, OM, FE, PO, KT, SH (SH returned a finding on mirror
  scope).
- **Evidence used:** the P0 prompt; `scripts/hldspec_agent_session.py` (the public
  facade — `command_continue`, `command_doctor`, `build_parser`);
  `scripts/build_hldspec_junior_task_packets.py` and
  `build_hldspec_orchestration_state.py` (old-model precursors);
  `hldspec/gate_validator.py`, `hldspec/model_routing.py`, `hldspec/hld_source_package.py`
  (the foundation); `tests_v2/test_cli_ux_contract.py` (continue contract).
- **Decision path:** GATE → "large but well-specified; tractable as one increment" →
  FUNDAMENTAL SCAN finds no ownership conflict (plan matches C1) → three failure-signal
  / scope findings → DECIDE = FIX/build, decomposed into module + script + facade
  wiring + tests.
- **Verification performed:** confirmed the foundation modules exist and are inert
  (no caller); confirmed continue CLI tests operate on `render_machine_result`, not
  `command_continue`, so gating `command_continue` behind session-plan presence is
  low regression risk; confirmed `.hldspec/source_package/` is the authoritative
  location (matches the plan's target layout).
- **Unresolved conflicts / unknowns:** none blocking. Open scope choice resolved in
  finding F2 (presence-of-machine-readable-report, not full markdown parsing).
- **Final output category:** HANDLED.

---

## GATE

- DONE testable? Yes (§13 acceptance tests).
- Scope tractable as one increment? Yes — the plan is prescriptive (exact file shapes,
  packet sections, gate names). One coherent module + thin script + surgical facade
  wiring + tests.
- Wrong-answer cost? Medium. It is the control plane, but every change is a new module
  plus a *backward-compatible* facade edit (gated on session-plan presence), so it is
  reversible.
- Approach explicit enough? Yes.

Verdict: **PROCEED / FIX**, decomposed.

## FUNDAMENTAL SCAN (ownership, SoT, boundaries, failure signal)

- **Ownership:** session_plan + packets are authored under `.hldspec/source_package/`
  (HLDspec control plane). Consistent with the C1 resolution — no new ownership
  conflict. The runner-facing mirror remains derived/read-only.
- **Failure signal (PO):** the prompt's own sharpest risk — "is session/subagent
  control real or only documentation?" The control plane is real **iff** the gate
  validator is actually invoked on the continuation path and can return BLOCK. Mapped
  to: `command_continue` calls `session_continue_preflight` before `ProjectMachine`,
  and a test asserts refusal.

## Findings (stabilized)

**F1 (SH/OM) — Mirror scope.** The target layout (§3) implies `.specify/source/`
mirrors "everything under `source_package/`". Mirroring executable artifacts
(`session_plan.json` with absolute paths/commands, subagent packets) into
SpecKit-owned space is low-value and blurs the control/spec boundary. **Decision:**
mirror = *source evidence only*. `speckit_runbook.md` mirrors (it is runner-facing
guidance); `session_plan.json` and `subagent_packets/` stay in `.hldspec/` and are
**not** mirrored. (No code change needed: those filenames are not in `MIRROR_FILES`.)

**F2 (PO/FE) — Receipt/report: presence vs content.** File-existence alone would let
a Phase Report saying `Validation result: FAIL` pass the gate. **Decision:** the gate
reads a machine-readable `phase_report.json` (and `context_receipt.json`) with
required keys; `validation_result`, `runskeptic_result`, `consultant_result`,
`source_anchors_used`, `unsupported_claims`, `stale_anchors` feed `GateContext`. The
markdown report/receipt remain human-facing. Full markdown parsing is out of scope
for this slice (logged).

**F3 (OM) — Model tier per task, not per role.** Basepack spans mechanical (control
files) and meaning (HLD authoring). **Decision:** each `build_*_packet` sets its own
tier via `model_routing.tier_for_operation(...)`. This slice's basepack packet is the
control-file-generation task → `MODEL_SIMPLE`; consultant review → `MODEL_SMART`;
runner command/test execution → `MODEL_SIMPLE`; the main controller (gates/
continuation) → `MODEL_SMART`. This also makes the model_routing wiring real and
test-observable.

## Thinkers (brief)

- **CH (dependencies):** `command_continue` currently always runs `ProjectMachine`.
  Gating it could regress existing flows → mitigate by gating **only** when
  `session_plan.json` exists (explicit opt-in). Negative test asserts the bound.
- **KT (universalize):** "no agent self-approves" must hold for every packet → encode
  as a `can_self_approve=False` field invariant + `next_gate_owner == main-controller`,
  validated structurally (not by string-grep).
- **PO:** see F2 and the failure-signal note.
- **FE:** the runbook/prompts are generated; tests must render real artifacts and
  assert exact headings (not `bash -n`).
- **SH:** see F1 (control-plane vs spec boundary; control files stay in `.hldspec/`).

## DECIDE → FIX (decomposed)

1. `hldspec/session_control.py` — roles, `SubagentPacket`, packet builders (per-task
   tier), `validate_packet`, `build_session_plan` (with `current_gate`), backend
   command rendering, tmux rendering, artifact writers, and `session_continue_preflight`
   (wires `gate_validator`).
2. `scripts/hldspec_session_control.py` — dry-run default; `--execute` required to emit
   launch commands.
3. Facade wiring in `scripts/hldspec_agent_session.py` — `command_continue` refuses on
   preflight block; `start` scaffolds plan+packets; `doctor`/`status`/`review` surface
   session/gates/packets.
4. `tests_v2/test_session_control.py` — the §13 acceptance list.

Next safe action after this review: implement slices 1–4 as one increment, run the
§13 validation commands, then report.
