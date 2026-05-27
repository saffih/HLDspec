from __future__ import annotations

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
    "## RunSkeptic checkpoints",
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


def render_bundle_prompt(bundle: dict[str, Any], *, workspace: Path, sync: Path, runtime: str) -> str:
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
        f"- orchestrator: `{model.get('orchestrator', 'MODEL_CRITICAL')}`",
        f"- default subagent: `{model.get('default_subagent', 'MODEL_STRONG')}`",
        f"- clarification: `{model.get('clarification', 'MODEL_MEDIUM')}`",
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
        "## SpecKit lifecycle",
        "",
        "For each spec, execute in dependency order. Do not skip forward.",
        "",
    ]

    for idx, spec in enumerate(specs, start=1):
        lines += [
            f"### Spec {idx}/{len(specs)} - `{spec.get('feature_id', '')}` - {spec.get('feature_name', '')}",
            "",
            "Allowed phase evidence remains limited to this bundle's allowed evidence list.",
            "",
            "1. Specify: create or update the SpecKit specification input for this spec.",
            "2. Clarify if needed: ask only questions that cannot be answered from allowed evidence.",
            "3. RunSkeptic checkpoint: classify as PASS/ACTION/CONFLICT before planning.",
            "4. Plan: produce the SpecKit plan for this spec.",
            "5. Research/data/contracts if needed: produce only if the plan requires them.",
            "6. RunSkeptic checkpoint: verify contracts, data ownership, dependency safety, and constitution alignment.",
            "7. Tasks: produce implementation tasks for this spec.",
            "8. RunSkeptic checkpoint: verify tasks are bounded, testable, and dependency-safe.",
            "9. Implementation: only if implementation_allowed=true and explicit human approval exists.",
            "10. Verification: run required tests or record why no runnable test exists.",
            "11. Per-spec summary: outputs, evidence used, questions, RunSkeptic status, next safe action.",
            "",
            "Spec input:",
            "",
            "```text",
            str(spec.get("speckit_specify_input", "")).strip() or "No speckit_specify_input recorded. Use allowed evidence only and stop if insufficient.",
            "```",
            "",
        ]

    lines += [
        "## RunSkeptic checkpoints",
        "",
        *_lines([str(item) for item in as_list(bundle.get("runskeptic_checkpoints"))]),
        "",
        "Use only these statuses: PASS, ACTION, CONFLICT.",
        "Stop on ACTION or CONFLICT unless the human explicitly resolves it.",
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
    for required in ("Specify", "Clarify", "Plan", "Research/data/contracts", "Tasks", "Implementation", "Verification", "RunSkeptic"):
        if required not in text:
            errors.append(f"missing lifecycle term: {required}")
    if not all(status in text for status in ("PASS", "ACTION", "CONFLICT")):
        errors.append("prompt must include PASS/ACTION/CONFLICT statuses")
    return errors


def write_bundle_prompts(workspace: Path, *, runtimes: tuple[str, ...] = RUNTIMES) -> dict[str, Any]:
    sync = select_sync_dir(workspace, ("speckit_bundle_queue.json", "speckit_invocation_queue.json"))
    queue_path = sync / "speckit_bundle_queue.json"
    queue = load_json_dict(queue_path)
    bundles = [bundle for bundle in as_list(queue.get("bundles")) if isinstance(bundle, dict)]
    prompt_root = sync / "speckit_bundle_prompts"
    prompt_root.mkdir(parents=True, exist_ok=True)

    for bundle in bundles:
        slug = str(bundle.get("bundle_slug", "bundle"))
        prompt_paths = as_dict(bundle.get("prompt_paths"))
        for runtime in runtimes:
            prompt_path = prompt_root / runtime / slug / "prompt.md"
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(render_bundle_prompt(bundle, workspace=workspace, sync=sync, runtime=runtime), encoding="utf-8")
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
