from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from hldspec.script_io import load_json_dict, select_sync_dir, write_json_dict
from hldspec.spec_bundles import as_dict, as_list, render_bundle_queue_md, utc_now

RUNTIMES = ("claude", "codex", "devin")

REQUIRED_PROMPT_MARKERS: tuple[str, ...] = (
    "## Target workspace",
    "## Bundle",
    "## Included specs",
    "## Why grouped",
    "## Dependencies",
    "## Allowed evidence",
    "## Forbidden reads",
    "## Runtime and model recommendation",
    "## Subagent orchestration",
    "## SpecKit lifecycle",
    "## Clarification Policy",
        "Stop only when approved evidence is missing, approved evidence is contradictory, or the question requires a human-owned decision.",
    "## RunSkeptic checkpoints",
    "## How to run RunSkeptic",
    "## Human checkpoint rules",
    "## Expected outputs",
    "## Tests required",
    "## Stop condition",
)

FORBIDDEN_STATUS_WORDS = ("BLOCKER",)


def _lines(items: list[Any]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- none"]


def _runtime_guidance(runtime: str) -> list[str]:
    if runtime == "claude":
        return [
            "Use Claude Code as the orchestrator.",
            "Spawn bounded subagents only for narrow specify/clarify/tasks work.",
            "The orchestrator keeps MODEL_CRITICAL decisions: dependency safety, plan approval, RunSkeptic, and implementation gates.",
        ]
    if runtime == "codex":
        return [
            "Use Codex as the orchestrator with explicit task/subtask boundaries.",
            "Use subagents only when the input bundle section is small and evidence-bounded.",
            "Return control to the orchestrator after every phase output and checkpoint.",
        ]
    if runtime == "devin":
        return [
            "Use Devin as one organized work session with explicit internal subtasks.",
            "Each subtask receives only the bundle evidence and one phase objective.",
            "Return a concise result, evidence list, and PASS/ACTION/CONFLICT status to the orchestrator.",
        ]
    raise ValueError(f"unsupported runtime: {runtime}")


# Abstract model tier -> concrete model per runtime. Mirrors the CLAUDE.md
# model routing table so a prompt names the model the runtime actually uses.
RUNTIME_MODELS: dict[str, dict[str, str]] = {
    "claude": {
        "MODEL_ROUTINE": "Haiku 4.5",
        "MODEL_DEFAULT": "Sonnet 4.6",
        "MODEL_STRONG": "Sonnet 4.6",
        "MODEL_CRITICAL": "Opus 4.7",
    },
    "codex": {
        "MODEL_ROUTINE": "gpt-5.5 low",
        "MODEL_DEFAULT": "gpt-5.5 medium",
        "MODEL_STRONG": "gpt-5.5 high",
        "MODEL_CRITICAL": "gpt-5.5 xhigh",
    },
    "devin": {
        "MODEL_ROUTINE": "SWE 1.6",
        "MODEL_DEFAULT": "SWE 1.6",
        "MODEL_STRONG": "Sonnet 4.5",
        "MODEL_CRITICAL": "Opus 4.6",
    },
}


def _concrete_model(runtime: str, tier: str) -> str:
    return RUNTIME_MODELS.get(runtime, {}).get(tier, tier)


def _spawn_directive(runtime: str, tier: str, role: str) -> str:
    """How this runtime spawns a bounded subagent for a delegated phase."""
    model = _concrete_model(runtime, tier)
    if runtime == "claude":
        return f"Spawn a subagent via the Task tool (model: {model}, tier {tier}) as **{role}**. Brief:"
    if runtime == "codex":
        return f"Open a Codex subtask (model: {model}, tier {tier}) as **{role}**, scoped to this brief:"
    if runtime == "devin":
        return f"Start a Devin sub-session (model: {model}, tier {tier}) as **{role}** with this brief:"
    raise ValueError(f"unsupported runtime: {runtime}")


def _orchestrator_directive(runtime: str, tier: str) -> str:
    """How this runtime keeps a phase in the orchestrator (no delegation)."""
    model = _concrete_model(runtime, tier)
    if runtime == "claude":
        return f"Run directly as the orchestrator (model: {model}, tier {tier}); do not spawn a subagent."
    if runtime == "codex":
        return f"Handle in the main Codex session (model: {model}, tier {tier}); do not open a subtask."
    if runtime == "devin":
        return f"Handle in the main Devin session (model: {model}, tier {tier}); do not open a sub-session."
    raise ValueError(f"unsupported runtime: {runtime}")


def _user_checkpoint(prompt_text: str, options: str) -> list[str]:
    return [
        "",
        f"> **USER CHECKPOINT** — {prompt_text}",
        f"> Reply required: `{options}`. Do not proceed until the user replies.",
        "",
    ]



def clarification_policy_block() -> list[str]:
    return [
        "## Clarification Policy",
        "",
        "Clarification questions are not blockers by default.",
        "",
        "- First answer from approved HLDspec evidence: active HLD sections, Working HLD, spec package map, dependency graph, invocation queue, constitution update plan or approved constitution, role reviews, Run Card, and proxy dossier.",
        "- If approved evidence clearly answers the question, answer it and continue.",
        "- If a pre-approved default is safe and reversible and does not affect architecture, source of truth, security/privacy, data ownership, dependency order, feature scope, constitution rules, user-visible behavior, or implementation approval, answer it and continue.",
        "- Escalate to the human only when approved evidence is missing, contradictory, or the answer is human-owned.",
        "- Stop on RunSkeptic ACTION or CONFLICT.",
        "",
    ]

# Phase-specific RunSkeptic scan content (what to actually inspect).
RUNSKEPTIC_SCAN: dict[str, tuple[str, ...]] = {
    "specify": (
        "Scope creep beyond this spec's source HLD sections.",
        "Acceptance criteria that are missing, vague, or untestable.",
        "Boundary or source-of-truth claims not backed by allowed evidence.",
    ),
    "plan": (
        "Architecture boundary correctness vs HLD facts and constitution rules.",
        "Contract and data-ownership conflicts with already-built specs in the bundle.",
        "Dependency safety: this spec depends only on already-completed work.",
        "Interface stability: contracts stay separable from processing behavior.",
    ),
    "tasks": (
        "Tasks are bounded and independently testable.",
        "Task order respects dependency direction.",
        "No hidden coupling or duplicated ownership across tasks.",
    ),
}


def _runskeptic_block(runtime: str, phase: str, spec_id_value: str, skeptic_path: str) -> list[str]:
    scan = RUNSKEPTIC_SCAN.get(phase, ("Apply the general RunSkeptic scan for this phase.",))
    return [
        f"**RunSkeptic gate ({phase})** — {_orchestrator_directive(runtime, 'MODEL_CRITICAL')}",
        "",
        f"Apply the framework at `{skeptic_path}` (read the real file; do not rely on memory):",
        "",
        "- **GATE:** Is the phase output testable and the scope bounded? If not, stop.",
        "- **SCAN:**",
        *[f"  - {item}" for item in scan],
        "- **MAP:** List concrete findings with evidence references before deciding.",
        "- **DECIDE:** Record one status for this phase.",
        "",
        f"Report: `RunSkeptic {spec_id_value} ({phase}): PASS | ACTION | CONFLICT — <finding or clean>`.",
        "Stop on ACTION or CONFLICT unless the user explicitly resolves it.",
        "",
    ]




def _runskeptic_operating_block(skeptic_path: str) -> list[str]:
    return [
        "RunSkeptic is the required quality gate for this step.",
        "",
        "First, read the actual current framework file:",
        "",
        f"`{skeptic_path}`",
        "",
        "Do not rely on memory or a summary if the file is available.",
        "",
        "Apply this flow in order:",
        "",
        "`GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN`",
        "",
        "For this prompt, RunSkeptic is normally read-only unless the Run Card explicitly authorizes a fix.",
        "",
        "Use only these result statuses:",
        "",
        "- `PASS`: no blocking finding is known; evidence is sufficient for this step.",
        "- `ACTION`: a fixable issue exists, such as missing evidence, stale artifact, invalid output, incomplete contract, weak testability, or unclear prompt/report content.",
        "- `CONFLICT`: a human-owned or architecture/product/source-of-truth decision is unresolved, or multiple valid designs exist and the evidence does not choose between them.",
        "",
        "Minimum checks:",
        "",
        "1. Gate: confirm the requested step is clear, bounded, and testable.",
        "2. Fundamental scan: check purpose, boundaries, ownership, source of truth, main flow, interfaces, dependencies, and high-risk assumptions.",
        "3. Map: list findings before deciding. Do not fix while mapping.",
        "4. Confidence: identify unknowns, skipped areas, and weak evidence.",
        "5. Stabilize: merge related findings and identify root cause.",
        "6. Evidence: mark each finding as `OBSERVED`, `REPRODUCED`, `HISTORICAL`, or `INFERRED RISK`.",
        "7. Decide: choose `PASS`, `ACTION`, or `CONFLICT`; do not promote if any ACTION or CONFLICT remains.",
        "8. Verify: if a fix was explicitly authorized, report the exact tests or checks run; otherwise report what verification would be required.",
        "",
        "Required RunSkeptic output:",
        "",
        "- `RunSkeptic status: PASS | ACTION | CONFLICT`",
        "- `Scope reviewed:`",
        "- `Evidence used:`",
        "- `Findings:`",
        "- `Unknowns:`",
        "- `Human decisions needed:`",
        "- `Verification performed:`",
        "- `Next safe action:`",
        "",
        "Stop immediately if RunSkeptic returns ACTION or CONFLICT, required evidence is missing, a human-owned decision appears, or the step would require reading outside approved evidence.",
        "",
        "If the framework file is unavailable, do not claim full RunSkeptic compliance. Use this embedded fallback and report: `RunSkeptic source: embedded fallback`; `Confidence: lower than full framework review`; `Missing evidence: actual skeptic.md was unavailable`.",
    ]

def render_bundle_prompt(bundle: dict[str, Any], *, workspace: Path, sync: Path, runtime: str, skeptic_path: str = "~/code/skeptic/skeptic.md") -> str:
    if runtime not in RUNTIMES:
        raise ValueError(f"unsupported runtime: {runtime}")

    specs = [spec for spec in as_list(bundle.get("included_specs")) if isinstance(spec, dict)]
    model = as_dict(bundle.get("model_runtime_recommendation"))
    lines = [
        f"# SpecKit Bundle Prompt - {bundle.get('bundle_id', '')} - {bundle.get('bundle_name', '')}",
        "",
        f"Environment: `{runtime}`",
        "",
        "## Target workspace",
        "",
        f"- workspace: `{workspace}`",
        f"- sync dir: `{sync}`",
        "",
        "## Bundle",
        "",
        f"- bundle id: `{bundle.get('bundle_id', '')}`",
        f"- bundle name: `{bundle.get('bundle_name', '')}`",
        f"- bundle slug: `{bundle.get('bundle_slug', '')}`",
        f"- dependency position: `{bundle.get('dependency_position', '')}`",
        f"- implementation allowed: `{bundle.get('implementation_allowed', False)}`",
        "",
        "## Included specs",
        "",
        "| Order | Feature | Layer | Theme | Depends on |",
        "|---:|---|---|---|---|",
    ]

    for idx, spec in enumerate(specs, start=1):
        deps = ", ".join(str(dep) for dep in as_list(spec.get("depends_on_features"))) or "none"
        lines.append(
            f"| {idx} | `{spec.get('feature_id', '')}` {spec.get('feature_name', '')} | "
            f"`{spec.get('layer', '')}` | `{spec.get('theme', '')}` | {deps} |"
        )

    lines += [
        "",
        "## Why grouped",
        "",
        str(bundle.get("why_grouped", "")),
        "",
        "## Dependencies",
        "",
        *_lines([str(dep) for dep in as_list(bundle.get("dependencies"))]),
        "",
        "## Allowed evidence",
        "",
        *_lines([f"`{item}`" for item in as_list(bundle.get("allowed_evidence"))]),
        "",
        "## Forbidden reads",
        "",
        *_lines([str(item) for item in as_list(bundle.get("forbidden_reads"))]),
        "",
        "## Runtime and model recommendation",
        "",
        f"Runtime `{runtime}` maps the abstract tiers to these concrete models:",
        "",
        f"- orchestrator: `{model.get('orchestrator', 'MODEL_CRITICAL')}` -> `{_concrete_model(runtime, model.get('orchestrator', 'MODEL_CRITICAL'))}`",
        f"- default subagent: `{model.get('default_subagent', 'MODEL_STRONG')}` -> `{_concrete_model(runtime, model.get('default_subagent', 'MODEL_STRONG'))}`",
        f"- clarification: `{model.get('clarification', 'MODEL_DEFAULT')}` -> `{_concrete_model(runtime, model.get('clarification', 'MODEL_DEFAULT'))}`",
        "",
        "Pick the weakest sufficient model per phase to avoid wasting tokens; promote to the orchestrator tier only for governance, plan, analyze, and RunSkeptic decisions.",
        "",
        "Runtime-specific guidance:",
        "",
        *_lines(_runtime_guidance(runtime)),
        "",
        "## Subagent orchestration",
        "",
        "- The orchestrator owns the full bundle and must keep the user-facing operation coherent.",
        "- Subagents receive only: one phase objective, this bundle prompt, allowed evidence, forbidden reads, stop condition, and required output format.",
        "- Subagents must return: phase result, files read, files changed if any, open questions, tests run, and RunSkeptic PASS/ACTION/CONFLICT status.",
        "- Control returns to the orchestrator after every phase and before every human checkpoint.",
        "- Do not let subagents continue into the next phase without explicit orchestrator handoff.",
        "",

        '## Clarification Policy',
        '',
        'Clarification is not a stop by default.',
        "If RunSkeptic returns ACTION or CONFLICT, stop even if the clarification appears answerable.",
        'If SpecKit asks clarification questions, resolve them from approved evidence first.',
        "Answer and continue when the answer is directly supported by this bundle's approved HLDspec evidence or by an approved safe default.",
        'Stop only when approved evidence is missing, approved evidence is contradictory, or the question requires a human-owned decision.',
        'Human-owned clarification includes architecture boundary, source of truth, constitution rule, API contract, security/privacy, data ownership, user-visible scope, dependency order, feature split/merge, and implementation approval.',
        '',
        "## Where to find answers",
        "",
        "When SpecKit asks a question, resolve it in this order before escalating:",
        "",
        "- spec-level intent and acceptance: `.specify/sync/speckit_answer_dossier.md`, `.specify/sync/hld_usecase_api_map.md`",
        "- architecture/contracts/data ownership: `.specify/sync/speckit_proxy_dossier.json`, `.specify/sync/speckit_invocation_queue.json`",
        "- governance/constitution rules: `.specify/sync/constitution_update_plan.json`, `.specify/memory/constitution.md` (if present)",
        "- prior clarify answers: run `lookup_speckit_clarify_answer.py` against the dossier",
        "- if no evidence exists: escalate to the user; do not invent an answer.",
        "",
        *clarification_policy_block(),
        "## Constitution preflight",
        "",
        f"{_orchestrator_directive(runtime, 'MODEL_CRITICAL')}",
        "- Confirm `.specify/memory/constitution.md` exists and matches `constitution_update_plan.json`.",
        "- If missing or stale, run `/speckit.constitution` from the update plan before any specify call.",
        "- Constitution rules govern every phase below; treat a violation as a CONFLICT.",
        *_user_checkpoint("Constitution confirmed for this bundle.", "continue / fix / stop"),
        "## SpecKit lifecycle",
        "",
        "For each spec, execute in dependency order. Do not skip forward.",
        "",
    ]

    for idx, spec in enumerate(specs, start=1):
        fid = str(spec.get("feature_id", ""))
        specify_input = str(spec.get("speckit_specify_input", "")).strip() or "No speckit_specify_input recorded. Use allowed evidence only and stop if insufficient."
        lines += [
            f"### Spec {idx}/{len(specs)} - `{fid}` - {spec.get('feature_name', '')}",
            "",
            "Allowed phase evidence remains limited to this bundle's allowed evidence list.",
            "",
            "#### Phase 1 - Specify",
            _spawn_directive(runtime, "MODEL_STRONG", "SpecKit Specify Proxy"),
            "- Run `/speckit.specify` with the spec input below; produce exactly one feature spec.",
            "- Use allowed evidence only; answer or escalate per the answer-location order above.",
            "- Required output: files created/changed, questions answered/escalated, evidence used.",
            "",
            "Spec input:",
            "",
            "```text",
            specify_input,
            "```",
            *_user_checkpoint(f"Specify done for `{fid}` - review spec.md.", "continue / fix / stop"),
            "#### Phase 2 - Clarify (only if open questions remain)",
            _spawn_directive(runtime, "MODEL_DEFAULT", "SpecKit Clarify Proxy"),
            "- Answer only questions resolvable from allowed evidence; escalate the rest to the user.",
            *_user_checkpoint(f"Clarify done for `{fid}`.", "continue / fix / stop"),
            *_runskeptic_block(runtime, "specify", fid, skeptic_path),
            "#### Phase 3 - Plan",
            f"{_orchestrator_directive(runtime, 'MODEL_CRITICAL')} Plan sets architecture, data, dependency, and contract boundaries, so do not delegate it.",
            "- Run `/speckit.plan`.",
            "- Produce Research/data/contracts artifacts only if the plan requires them.",
            *_runskeptic_block(runtime, "plan", fid, skeptic_path),
            *_user_checkpoint(f"Plan + contracts done for `{fid}` - review boundaries.", "approve / fix / stop"),
            "#### Phase 4 - Analyze",
            f"{_orchestrator_directive(runtime, 'MODEL_CRITICAL')} Analyze judges cross-artifact consistency (spec vs plan vs constitution).",
            "- Run `/speckit.analyze`; resolve inconsistencies before tasks.",
            *_user_checkpoint(f"Analyze done for `{fid}`.", "continue / fix / stop"),
            "#### Phase 5 - Tasks",
            _spawn_directive(runtime, "MODEL_STRONG", "SpecKit Tasks Proxy"),
            "- Run `/speckit.tasks`; decompose the approved plan into bounded, testable tasks without changing architecture.",
            *_runskeptic_block(runtime, "tasks", fid, skeptic_path),
            *_user_checkpoint(f"Tasks done for `{fid}` - review task list.", "approve / fix / stop"),
            "#### Phase 6 - Implementation",
            "- Blocked. Run `/speckit.implement` only if implementation_allowed=true AND explicit user approval exists for this spec.",
            "",
            "#### Phase 7 - Verification",
            "- Run the spec's tests, or record why no runnable test exists.",
            "",
            "#### Per-spec summary",
            "- Outputs, evidence used, questions answered/escalated, RunSkeptic statuses, next safe action.",
            "",
        ]

    lines += [
        "## Clarification Policy",
        "",
        "Clarification is not a stop by default.",
        "Resolve clarification questions from approved evidence first.",
        "When SpecKit asks clarification questions, resolve them from approved evidence first.",
        "Stop only when approved evidence is missing, approved evidence is contradictory, or the question requires a human-owned decision.",
        "",
        "## RunSkeptic checkpoints",
        "",
        *_lines([str(item) for item in as_list(bundle.get("runskeptic_checkpoints"))]),
        "",
        "Use only these statuses: PASS, ACTION, CONFLICT.",
        "Stop on ACTION or CONFLICT unless the human explicitly resolves it.",
        "",
        "## How to run RunSkeptic",
        "",
        *_runskeptic_operating_block(skeptic_path),
        "",
        "## Human checkpoint rules",
        "",
        *_lines([str(item) for item in as_list(bundle.get("human_checkpoint_rules"))]),
        "",
        "## Expected outputs",
        "",
        *_lines([str(item) for item in as_list(bundle.get("expected_outputs"))]),
        "",
        "## Tests required",
        "",
        *_lines([str(item) for item in as_list(bundle.get("tests_required"))]),
        "",
        "## Stop condition",
        "",
        str(bundle.get("stop_condition", "")),
        "",
        "## Bundle completion gate",
        "",
        "- Run cross-spec consistency review.",
        "- Check contract/data ownership conflicts.",
        "- Check duplicate tasks and circular dependencies.",
        "- Record bundle-level RunSkeptic PASS/ACTION/CONFLICT.",
        "- Stop for human review before starting the next bundle.",
        "",
    ]
    return "\n".join(lines)


def validate_prompt_text(text: str) -> list[str]:
    errors: list[str] = []
    for marker in REQUIRED_PROMPT_MARKERS:
        if marker not in text:
            errors.append(f"missing required marker: {marker}")
    for word in FORBIDDEN_STATUS_WORDS:
        if word in text:
            errors.append(f"prompt must not use {word} as a RunSkeptic status")
    for required in (
        "Specify",
        "Clarify",
        "Plan",
        "Research/data/contracts",
        "Tasks",
        "Implementation",
        "Verification",
        "RunSkeptic",
        "How to run RunSkeptic",
        "GATE -> FUNDAMENTAL SCAN -> MAP -> CONFIDENCE -> STABILIZE -> EVIDENCE -> DECIDE -> ACT -> VERIFY -> LEARN",
        "OBSERVED",
        "REPRODUCED",
        "HISTORICAL",
        "INFERRED RISK",
        "RunSkeptic status:",
        "Next safe action:",
    ):
        if required not in text:
            errors.append(f"missing lifecycle term: {required}")
    if not all(status in text for status in ("PASS", "ACTION", "CONFLICT")):
        errors.append("prompt must include PASS/ACTION/CONFLICT statuses")
    for required in (
        "## Clarification Policy",
        "Clarification questions are not blockers by default.",
        "approved HLDspec evidence",
        "missing, contradictory, or the answer is human-owned",
    ):
        if required not in text:
            errors.append(f"missing clarification policy content: {required}")
    return errors


def write_bundle_prompts(workspace: Path, *, runtimes: tuple[str, ...] = RUNTIMES, skeptic_path: str = "~/code/skeptic/skeptic.md") -> dict[str, Any]:
    sync = select_sync_dir(workspace, ("speckit_bundle_queue.json", "speckit_invocation_queue.json"))
    queue_path = sync / "speckit_bundle_queue.json"
    queue = load_json_dict(queue_path)
    bundles = [bundle for bundle in as_list(queue.get("bundles")) if isinstance(bundle, dict)]
    prompt_root = sync / "speckit_bundle_prompts"
    # Clear prior output so a regrouping (renamed bundles) leaves no orphan
    # prompt directories that would mislead the next reader.
    if prompt_root.exists():
        shutil.rmtree(prompt_root)
    prompt_root.mkdir(parents=True, exist_ok=True)

    for bundle in bundles:
        slug = str(bundle.get("bundle_slug", "bundle"))
        prompt_paths = as_dict(bundle.get("prompt_paths"))
        for runtime in runtimes:
            prompt_path = prompt_root / runtime / slug / "prompt.md"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(render_bundle_prompt(bundle, workspace=workspace, sync=sync, runtime=runtime, skeptic_path=skeptic_path), encoding="utf-8")
            prompt_paths[runtime] = str(prompt_path.relative_to(workspace))
        bundle["prompt_paths"] = prompt_paths

    queue["generated_at"] = utc_now()
    queue["bundles"] = bundles
    queue["bundle_count"] = len(bundles)
    write_json_dict(queue_path, queue)
    (sync / "speckit_bundle_queue.md").write_text(render_bundle_queue_md(queue), encoding="utf-8")

    readme = render_bundle_prompt_readme(queue)
    (prompt_root / "README.md").write_text(readme, encoding="utf-8")
    return queue


def render_bundle_prompt_readme(queue: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Bundle Prompts",
        "",
        f"Bundle count: `{queue.get('bundle_count', 0)}`",
        "",
        "| Bundle | Specs | Claude | Codex | Devin |",
        "|---|---:|---|---|---|",
    ]
    for bundle in as_list(queue.get("bundles")):
        if not isinstance(bundle, dict):
            continue
        paths = as_dict(bundle.get("prompt_paths"))
        lines.append(
            f"| `{bundle.get('bundle_id', '')}` {bundle.get('bundle_name', '')} | "
            f"{len(as_list(bundle.get('included_specs')))} | "
            f"`{paths.get('claude', '')}` | `{paths.get('codex', '')}` | `{paths.get('devin', '')}` |"
        )
    lines += [
        "",
        "Each prompt is a one-go orchestration prompt for a dependency-safe bite-size bundle.",
        "Implementation remains blocked unless explicit human approval exists.",
        "",
    ]
    return "\n".join(lines)
