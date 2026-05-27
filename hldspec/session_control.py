"""Session-plan + bounded-subagent control plane.

The control plane is `session_plan.json` + subagent packets + receipts + phase
reports + the gate validator. Tmux is optional UI rendered *from* the session
plan; it is never the control system.

Roles (see docs/archive/P0_SESSION_CONTROL_RUNSKEPTIC_REVIEW_2026-05-27.md):

- main-controller : user interaction, approval gates, source-truth + continuation
  decisions. Owns continuation; runs no long/mechanical work itself.
- hldspec-basepack: prepares the source package / control files, validates shape,
  stops.
- target-runner  : runs one bounded SpecKit/test phase in the target, reports, stops.
- consultant     : review-only; checks meaning/source consistency; applies
  RunSkeptic; returns PASS/ACTION/CONFLICT; stops.

Core rule: the control plane owns continuation; agents do bounded work and stop.
No agent may self-approve (`can_self_approve` is invariantly False) and every gate
is owned by the main controller.
"""
from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import gate_validator as gv
from . import model_routing as mr
from .script_io import load_json_dict, write_json_dict
from .workspace_adapter import TargetWorkspaceAdapter

SCHEMA_VERSION = 1

# Roles
MAIN_CONTROLLER = "main-controller"
BASEPACK = "hldspec-basepack"
RUNNER = "target-runner"
CONSULTANT = "consultant"
ROLES: tuple[str, ...] = (MAIN_CONTROLLER, BASEPACK, RUNNER, CONSULTANT)

# Backends. dry-run is the default; nothing launches without --execute.
DEFAULT_BACKEND = "dry-run"
BACKENDS: tuple[str, ...] = (
    "dry-run",
    "command-only",
    "tmux",
    "claude",
    "codex",
    "manual",
)

DEFAULT_SESSION_NAME = "hldspec-run"
CONTEXT_BUDGET = "SMALL_RELEVANT_ARTIFACTS_ONLY"

# Required reads every Runner/Consultant must confirm in their Context Receipt.
REQUIRED_READS: tuple[str, ...] = (
    ".hldspec/source_package/source_package.json",
    ".hldspec/source_package/source_manifest.json",
    ".hldspec/source_package/session_plan.json",
    ".hldspec/source_package/speckit_runbook.md",
)

# Machine-readable companions the gate reads (finding F2). Markdown stays human-facing.
CONTEXT_RECEIPT_FILE = "context_receipt.json"
PHASE_REPORT_FILE = "phase_report.json"
SESSION_PLAN_FILE = "session_plan.json"

CONTEXT_RECEIPT_REQUIRED_KEYS: tuple[str, ...] = (
    "required_files_read",
    "current_phase",
    "actor",
    "model_tier",
    "stop_condition",
    "validation_command",
)
PHASE_REPORT_REQUIRED_KEYS: tuple[str, ...] = (
    "phase",
    "actor",
    "validation_result",
    "runskeptic_result",
    "consultant_result",
    "next_safe_action",
)


# ---------------------------------------------------------------------------
# Subagent packet
# ---------------------------------------------------------------------------
@dataclass
class SubagentPacket:
    role: str
    phase: str
    model_tier: str
    required_reads: list[str]
    allowed_files: list[str]
    forbidden_files: list[str]
    task: str
    expected_output: str
    validation_command: str
    stop_condition: str
    report_format: str
    next_gate_owner: str
    context_budget: str = CONTEXT_BUDGET
    broad_scan: bool = False  # forbidden by default
    web: bool = False  # forbidden by default
    write_access: bool = False
    can_self_approve: bool = False  # invariant: must remain False


def _yn(value: bool) -> str:
    return "yes" if value else "no"


# Section headings are part of the contract; tests assert exact headings.
PACKET_SECTIONS: tuple[str, ...] = (
    "ROLE:",
    "PHASE:",
    "MODEL TIER:",
    "REQUIRED READS:",
    "ALLOWED FILES:",
    "FORBIDDEN FILES:",
    "TASK:",
    "EXPECTED OUTPUT:",
    "VALIDATION COMMAND:",
    "STOP CONDITION:",
    "REPORT FORMAT:",
    "NEXT GATE OWNER:",
    "CONTEXT BUDGET:",
    "BROAD SCAN:",
    "WEB:",
    "WRITE ACCESS:",
)


def render_packet(packet: SubagentPacket) -> str:
    def block(items: list[str]) -> str:
        return "\n".join(f"  - {i}" for i in items) if items else "  - (none)"

    return "\n".join(
        [
            f"ROLE: {packet.role}",
            f"PHASE: {packet.phase}",
            f"MODEL TIER: {packet.model_tier}",
            "REQUIRED READS:",
            block(packet.required_reads),
            "ALLOWED FILES:",
            block(packet.allowed_files),
            "FORBIDDEN FILES:",
            block(packet.forbidden_files),
            f"TASK: {packet.task}",
            f"EXPECTED OUTPUT: {packet.expected_output}",
            f"VALIDATION COMMAND: {packet.validation_command}",
            f"STOP CONDITION: {packet.stop_condition}",
            "REPORT FORMAT:",
            packet.report_format,
            f"NEXT GATE OWNER: {packet.next_gate_owner}",
            f"CONTEXT BUDGET: {packet.context_budget}",
            f"BROAD SCAN: {'allowed' if packet.broad_scan else 'forbidden'}",
            f"WEB: {'allowed' if packet.web else 'forbidden'}",
            f"WRITE ACCESS: {_yn(packet.write_access)}",
            "SELF-APPROVAL: forbidden",
            "",
        ]
    )


CONTEXT_RECEIPT_TEMPLATE = """\
CONTEXT RECEIPT
- Required files read:
  - [ ] .hldspec/source_package/source_package.json
  - [ ] .hldspec/source_package/source_manifest.json
  - [ ] .hldspec/source_package/session_plan.json
  - [ ] .hldspec/source_package/speckit_runbook.md
  - [ ] .hldspec/source_package/runner_prompt.md or consultant_prompt.md
  - [ ] .specify/memory/constitution.md, if initialized
- Current phase:
- Actor:
- Model tier:
- Allowed files:
- Forbidden files:
- Stop condition:
- Validation command:
- Source anchors used:
- I will stop on:
  - missing source
  - unsupported claim
  - source contradiction
  - unrelated dirty work
  - RunSkeptic ACTION/CONFLICT
  - failed validation
"""

PHASE_REPORT_TEMPLATE = """\
PHASE REPORT
- Phase:
- Actor:
- Files read:
- Files changed:
- Source anchors used:
- Unsupported claims:
- Questions/conflicts:
- Tests/checks run:
- Validation result:
- RunSkeptic result:
- Consultant result:
- Blocking issues:
- Next safe action:

Continuation is owned by the main-controller. This actor must STOP after this report.
"""


# ---------------------------------------------------------------------------
# Packet builders — model tier is routed per task (finding F3)
# ---------------------------------------------------------------------------
def build_basepack_packet(phase: str = "source_package_preparation") -> SubagentPacket:
    return SubagentPacket(
        role=BASEPACK,
        phase=phase,
        model_tier=mr.tier_for_operation("manifest_generation"),  # MODEL_SIMPLE
        required_reads=list(REQUIRED_READS),
        allowed_files=[".hldspec/source_package/**"],
        forbidden_files=[".specify/**", "source HLD (read-only)", "target application code"],
        task=(
            "Prepare/validate the source package control files under "
            ".hldspec/source_package/ and regenerate the derived .specify/source/ "
            "mirror. Do not author product meaning; escalate meaning changes to a "
            "MODEL_SMART actor."
        ),
        expected_output="Validated source package + session plan + packets; PHASE REPORT.",
        validation_command="python3 -m unittest tests_v2.test_source_package -v",
        stop_condition="Stop after source package / control files validation. Do not continue.",
        report_format=PHASE_REPORT_TEMPLATE,
        next_gate_owner=MAIN_CONTROLLER,
        write_access=True,  # bounded write inside .hldspec/source_package/
    )


def build_runner_packet(phase: str = "speckit_specify") -> SubagentPacket:
    return SubagentPacket(
        role=RUNNER,
        phase=phase,
        model_tier=mr.tier_for_operation("command_execution"),  # MODEL_SIMPLE
        required_reads=list(REQUIRED_READS) + [".hldspec/source_package/runner_prompt.md"],
        allowed_files=["target repo files within the phase scope"],
        forbidden_files=[
            ".hldspec/source_package/** (read-only for the runner)",
            "unrelated target files outside phase scope",
            "source HLD (read-only)",
        ],
        task=(
            f"Run exactly one bounded phase ({phase}): the SpecKit/test commands in "
            "speckit_runbook.md. Edit target repo only within the allowed scope. "
            "Report a Context Receipt and a Phase Report, then stop."
        ),
        expected_output="One bounded phase executed; CONTEXT RECEIPT + PHASE REPORT.",
        validation_command="see speckit_runbook.md phase validation command",
        stop_condition="Stop after one bounded phase. Do not start the next phase.",
        report_format=PHASE_REPORT_TEMPLATE,
        next_gate_owner=MAIN_CONTROLLER,
        write_access=True,  # bounded write inside the target phase scope
    )


def build_consultant_packet(phase: str = "review") -> SubagentPacket:
    return SubagentPacket(
        role=CONSULTANT,
        phase=phase,
        model_tier=mr.tier_for_operation("consultant_review"),  # MODEL_SMART
        required_reads=list(REQUIRED_READS) + [".hldspec/source_package/consultant_prompt.md"],
        allowed_files=["read-only access to target + source package"],
        forbidden_files=["ALL — consultant is review-only and writes nothing"],
        task=(
            "Review meaning and source consistency, apply RunSkeptic, aggregate "
            "UI/test evidence, and return PASS / ACTION / CONFLICT. Do not edit files; "
            "do not approve your own findings."
        ),
        expected_output="Consultant verdict PASS/ACTION/CONFLICT with evidence; PHASE REPORT.",
        validation_command="python3 -m unittest tests_v2.test_gate_validator -v",
        stop_condition="Stop after returning the verdict. Review-only; never writes or approves.",
        report_format=PHASE_REPORT_TEMPLATE,
        next_gate_owner=MAIN_CONTROLLER,
        write_access=False,  # review-only
    )


def build_ui_test_packet(phase: str = "ui_validation") -> SubagentPacket:
    return SubagentPacket(
        role=CONSULTANT,
        phase=phase,
        model_tier=mr.tier_for_operation("consultant_review"),  # MODEL_SMART
        required_reads=list(REQUIRED_READS) + [".hldspec/source_package/consultant_prompt.md"],
        allowed_files=["read-only access to UI test evidence + target"],
        forbidden_files=["ALL — review-only; writes nothing"],
        task="Aggregate UI test evidence and report PASS/ACTION/CONFLICT for the UI_VALIDATION_GATE.",
        expected_output="UI evidence summary + verdict; PHASE REPORT.",
        validation_command="UI test suite per runbook",
        stop_condition="Stop after the UI evidence verdict. Review-only.",
        report_format=PHASE_REPORT_TEMPLATE,
        next_gate_owner=MAIN_CONTROLLER,
        write_access=False,
    )


def all_packets() -> dict[str, SubagentPacket]:
    return {
        "basepack": build_basepack_packet(),
        "runner": build_runner_packet(),
        "consultant": build_consultant_packet(),
        "ui_test": build_ui_test_packet(),
    }


# ---------------------------------------------------------------------------
# Packet validation
# ---------------------------------------------------------------------------
def validate_packet(packet: SubagentPacket) -> list[str]:
    errors: list[str] = []
    if packet.role not in ROLES:
        errors.append(f"unknown role: {packet.role!r}")
    if packet.model_tier not in mr.OPERATIONAL_TIERS:
        errors.append(f"invalid model tier: {packet.model_tier!r}")
    for fieldname in ("phase", "task", "expected_output", "validation_command", "stop_condition"):
        if not str(getattr(packet, fieldname)).strip():
            errors.append(f"empty required field: {fieldname}")
    # Invariants
    if packet.can_self_approve:
        errors.append("self-approval is forbidden for every packet")
    if packet.next_gate_owner != MAIN_CONTROLLER:
        errors.append(f"gates must be owned by {MAIN_CONTROLLER}, got {packet.next_gate_owner!r}")
    if packet.broad_scan:
        errors.append("broad scan must be forbidden by default")
    if packet.web:
        errors.append("web must be forbidden by default")
    if packet.role == CONSULTANT and packet.write_access:
        errors.append("consultant must be review-only (write_access must be no)")
    if packet.role == RUNNER and "one bounded phase" not in packet.stop_condition.lower():
        errors.append("runner must stop after one bounded phase")
    if packet.role == BASEPACK and "validation" not in packet.stop_condition.lower():
        errors.append("basepack must stop after source package / control file validation")
    return errors


# ---------------------------------------------------------------------------
# Session plan
# ---------------------------------------------------------------------------
def _role_entry(
    *,
    role: str,
    command: str,
    prompt_file: str,
    packet_file: str | None,
    allowed_files: list[str],
    forbidden_files: list[str],
    stop_condition: str,
    validation_command: str,
    model_tier: str,
    write_access: bool,
) -> dict:
    return {
        "role": role,
        "command": command,
        "prompt_file": prompt_file,
        "packet_file": packet_file,
        "allowed_files": allowed_files,
        "forbidden_files": forbidden_files,
        "stop_condition": stop_condition,
        "validation_command": validation_command,
        "next_gate_owner": MAIN_CONTROLLER,
        "write_access": write_access,
        "web_allowed": False,
        "broad_scan_allowed": False,
        "model_tier": model_tier,
        "context_budget": CONTEXT_BUDGET,
    }


def build_session_plan(
    target_repo_path: str | Path,
    hldspec_repo_path: str | Path,
    *,
    backend: str = DEFAULT_BACKEND,
    session_name: str = DEFAULT_SESSION_NAME,
    current_gate: str = gv.SOURCE_PACKAGE_APPROVAL_GATE,
) -> dict:
    if backend not in BACKENDS:
        raise ValueError(f"unknown backend: {backend!r}; expected one of {BACKENDS}")
    target = str(target_repo_path)
    hldspec = str(hldspec_repo_path)
    pkt_dir = ".hldspec/source_package/subagent_packets"

    basepack = build_basepack_packet()
    runner = build_runner_packet()
    consultant = build_consultant_packet()

    roles = {
        MAIN_CONTROLLER: _role_entry(
            role=MAIN_CONTROLLER,
            command="(interactive — main controller stays available for the user)",
            prompt_file="(none — controller owns gates and continuation)",
            packet_file=None,
            allowed_files=["all (decision authority)"],
            forbidden_files=["long/mechanical execution by default"],
            stop_condition="Stops at every gate to own the approval/continuation decision.",
            validation_command="python3 scripts/hldspec_agent_session.py doctor --target " + target,
            model_tier=mr.MODEL_SMART,
            write_access=False,
        ),
        BASEPACK: _role_entry(
            role=BASEPACK,
            command=_role_command(BASEPACK, target, hldspec, backend),
            prompt_file=".hldspec/source_package/speckit_runbook.md",
            packet_file=f"{pkt_dir}/basepack_packet.md",
            allowed_files=basepack.allowed_files,
            forbidden_files=basepack.forbidden_files,
            stop_condition=basepack.stop_condition,
            validation_command=basepack.validation_command,
            model_tier=basepack.model_tier,
            write_access=basepack.write_access,
        ),
        RUNNER: _role_entry(
            role=RUNNER,
            command=_role_command(RUNNER, target, hldspec, backend),
            prompt_file=".hldspec/source_package/runner_prompt.md",
            packet_file=f"{pkt_dir}/runner_packet.md",
            allowed_files=runner.allowed_files,
            forbidden_files=runner.forbidden_files,
            stop_condition=runner.stop_condition,
            validation_command=runner.validation_command,
            model_tier=runner.model_tier,
            write_access=runner.write_access,
        ),
        CONSULTANT: _role_entry(
            role=CONSULTANT,
            command=_role_command(CONSULTANT, target, hldspec, backend),
            prompt_file=".hldspec/source_package/consultant_prompt.md",
            packet_file=f"{pkt_dir}/consultant_packet.md",
            allowed_files=consultant.allowed_files,
            forbidden_files=consultant.forbidden_files,
            stop_condition=consultant.stop_condition,
            validation_command=consultant.validation_command,
            model_tier=consultant.model_tier,
            write_access=consultant.write_access,
        ),
    }

    return {
        "schema_version": SCHEMA_VERSION,
        "session_name": session_name,
        "backend": backend,
        "target_repo_path": target,
        "hldspec_repo_path": hldspec,
        "current_gate": current_gate,
        "control_rule": "The control plane owns continuation. Agents do bounded work and stop.",
        "approvals": {},
        "roles": roles,
    }


def _role_command(role: str, target: str, hldspec: str, backend: str) -> str:
    """Command string a role would run, per backend. Never executed here."""
    pkt = {
        BASEPACK: ".hldspec/source_package/subagent_packets/basepack_packet.md",
        RUNNER: ".hldspec/source_package/subagent_packets/runner_packet.md",
        CONSULTANT: ".hldspec/source_package/subagent_packets/consultant_packet.md",
    }.get(role, "")
    if backend == "claude":
        return f"claude -p \"$(cat {target}/{pkt})\""
    if backend == "codex":
        return f"codex exec --sandbox workspace-write -C {target} \"$(cat {pkt})\""
    if backend == "manual":
        return f"Paste {target}/{pkt} into a fresh {role} agent session."
    # dry-run / command-only / tmux all describe the same bounded invocation
    return f"run {role} from packet {pkt} in {target} (bounded; stop after the phase)"


def render_tmux_commands(plan: dict) -> list[str]:
    """Optional tmux rendering from the session plan. Uses the real target path.
    Returned commands are NOT executed by this function."""
    target = plan["target_repo_path"]
    session = plan["session_name"]
    cmds = [f"tmux new-session -d -s {session} -c {target} -n {MAIN_CONTROLLER}"]
    for role in (BASEPACK, RUNNER, CONSULTANT):
        cmds.append(f"tmux new-window -t {session} -c {target} -n {role}")
    return cmds


def render_role_commands(plan: dict) -> dict[str, str]:
    """command-only backend: the exact command for each role."""
    return {role: entry["command"] for role, entry in plan["roles"].items()}


# ---------------------------------------------------------------------------
# Artifact writers
# ---------------------------------------------------------------------------
def write_session_artifacts(target_root: Path, plan: dict, layout: str = "new") -> dict[str, Path]:
    adapter = TargetWorkspaceAdapter(target_root=target_root, layout=layout)
    source_dir = adapter.source_package_dir
    pkt_dir = source_dir / "subagent_packets"
    pkt_dir.mkdir(parents=True, exist_ok=True)

    write_json_dict(source_dir / SESSION_PLAN_FILE, plan)

    packets = {
        "basepack_packet.md": build_basepack_packet(),
        "runner_packet.md": build_runner_packet(),
        "consultant_packet.md": build_consultant_packet(),
        "ui_test_packet.md": build_ui_test_packet(),
    }
    written: dict[str, Path] = {SESSION_PLAN_FILE: source_dir / SESSION_PLAN_FILE}
    for filename, packet in packets.items():
        path = pkt_dir / filename
        path.write_text(render_packet(packet), encoding="utf-8")
        written[filename] = path

    # Runner/consultant prompts embed the Context Receipt the gate requires.
    # Authoritative files carry no mirror banner; the mirror step is the sole
    # banner-adder (these live in .hldspec/, not the derived mirror).
    runner_prompt = (
        "# Target Runner Prompt\n\n"
        "You run ONE bounded phase, then stop. Before acting, output a Context "
        "Receipt; after the phase, output a Phase Report. The main-controller owns "
        "continuation.\n\n" + CONTEXT_RECEIPT_TEMPLATE + "\n" + PHASE_REPORT_TEMPLATE
    )
    consultant_prompt = (
        "# Consultant / RunSkeptic Prompt\n\n"
        "You are review-only. Check meaning and source consistency, apply RunSkeptic, "
        "and return PASS / ACTION / CONFLICT. You write nothing and never approve your "
        "own findings.\n\n" + CONTEXT_RECEIPT_TEMPLATE + "\n" + PHASE_REPORT_TEMPLATE
    )
    runbook = (
        "# SpecKit Runbook\n\n"
        f"Backend selected: `{plan['backend']}`\n\n"
        "## Control model\n\n"
        f"{plan['control_rule']}\n\n"
        "## Roles\n\n"
        + "\n".join(f"- `{r}`" for r in ROLES)
        + "\n\n## Continuation contract\n\n"
        "The gate validator reads machine-readable companions, not the markdown:\n"
        f"- `{CONTEXT_RECEIPT_FILE}` (keys: {', '.join(CONTEXT_RECEIPT_REQUIRED_KEYS)})\n"
        f"- `{PHASE_REPORT_FILE}` (keys: {', '.join(PHASE_REPORT_REQUIRED_KEYS)})\n"
        "Write both the human markdown report AND its `.json` companion; the main "
        "controller's `continue` blocks without a valid Phase Report JSON.\n"
        + "\n## Optional tmux\n\n```\n"
        + "\n".join(render_tmux_commands(plan))
        + "\n```\n"
    )
    (source_dir / "runner_prompt.md").write_text(runner_prompt, encoding="utf-8")
    (source_dir / "consultant_prompt.md").write_text(consultant_prompt, encoding="utf-8")
    (source_dir / "speckit_runbook.md").write_text(runbook, encoding="utf-8")
    written["runner_prompt.md"] = source_dir / "runner_prompt.md"
    written["consultant_prompt.md"] = source_dir / "consultant_prompt.md"
    written["speckit_runbook.md"] = source_dir / "speckit_runbook.md"
    return written


# ---------------------------------------------------------------------------
# Continuation control — wires gate_validator into the public `continue` path
# ---------------------------------------------------------------------------
@dataclass
class PreflightResult:
    allowed: bool
    gate: str | None
    blockers: list[str] = field(default_factory=list)
    gated: bool = False  # whether a session plan opted into gating


def target_dirty_files(target_root: Path) -> list[str]:
    """Unrelated dirty files in the target repo, or [] if not a git repo."""
    try:
        out = subprocess.run(
            ["git", "-C", str(target_root), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return []
    if out.returncode != 0:
        return []
    return [line[3:] for line in out.stdout.splitlines() if line.strip()]


def _receipt_present(source_dir: Path) -> bool:
    data = load_json_dict(source_dir / CONTEXT_RECEIPT_FILE)
    return bool(data) and all(k in data for k in CONTEXT_RECEIPT_REQUIRED_KEYS)


def session_continue_preflight(
    target_root: Path,
    *,
    check_dirty: bool = True,
    layout: str = "new",
) -> PreflightResult:
    """Gate the public `continue` path.

    Backward compatible: if no session_plan.json exists, gating is OFF and
    continuation proceeds as before. When a plan exists, the gate validator
    decides continuation from the machine-readable Context Receipt + Phase Report.
    """
    adapter = TargetWorkspaceAdapter(target_root=target_root, layout=layout)
    source_dir = adapter.source_package_dir
    plan_path = source_dir / SESSION_PLAN_FILE
    if not plan_path.is_file():
        return PreflightResult(allowed=True, gate=None, blockers=[], gated=False)

    plan = load_json_dict(plan_path)
    gate = plan.get("current_gate")
    if not gate:
        return PreflightResult(
            allowed=False, gate=None, blockers=["session plan missing current_gate"], gated=True
        )

    blockers: list[str] = []
    report = load_json_dict(source_dir / PHASE_REPORT_FILE)
    if not report or any(k not in report for k in PHASE_REPORT_REQUIRED_KEYS):
        blockers.append("missing Phase Report")

    # Stale-artifact detection (Slice 5): stale cited anchors recorded in
    # hld_change_impact.json block continuation until regenerated/resolved.
    from . import stale_check

    impact_stale = stale_check.load_stale_anchors(source_dir)

    if check_dirty:
        dirty = target_dirty_files(target_root)
        if dirty:
            blockers.append(f"unexpected dirty tree: {', '.join(dirty[:5])}")

    ctx = gv.GateContext(
        receipt_present=_receipt_present(source_dir),
        source_refs=list(report.get("source_anchors_used", []) or []),
        runskeptic_status=str(report.get("runskeptic_result", gv.RUNSKEPTIC_NOT_RUN) or gv.RUNSKEPTIC_NOT_RUN),
        consultant_status=str(report.get("consultant_result", gv.CONSULTANT_NOT_RUN) or gv.CONSULTANT_NOT_RUN),
        unsupported_claims=list(report.get("unsupported_claims", []) or []),
        stale_anchors=sorted(set(report.get("stale_anchors", []) or []) | set(impact_stale)),
        validation_ok=str(report.get("validation_result", "")).upper() == "PASS",
        human_approved=bool(plan.get("approvals", {}).get(gate, False)),
    )
    try:
        gate_result = gv.validate_gate(gate, ctx)
        blockers.extend(gate_result.blockers)
    except gv.UnknownGate as exc:
        blockers.append(str(exc))

    return PreflightResult(allowed=not blockers, gate=gate, blockers=blockers, gated=True)


def packet_to_dict(packet: SubagentPacket) -> dict:
    return asdict(packet)
