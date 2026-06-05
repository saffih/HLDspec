"""Assess how far SpecKit has gotten and where to resume.

HLDspec prepares ordered, bundled SpecKit inputs. Once SpecKit starts running
in the implementation project it writes `specs/<short-name>/spec.md|plan.md|
tasks.md`. This module inspects that tree, derives per-spec phase status, and
finds the resume point so HLDspec can tell the operator what to run next.

It is deliberately tolerant: if the SpecKit root cannot be found or read, the
state is UNKNOWN and the caller should fall back to the do-it-all prompt.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hldspec.script_io import load_json_dict, write_json_dict
from hldspec.spec_bundles import as_dict, as_list, utc_now

SCHEMA_VERSION = 1
ASSESSMENT_JSON = "speckit_execution_assessment.json"
ASSESSMENT_MD = "speckit_execution_assessment.md"

# A phase is considered DONE when its signature artifact exists and is non-empty.
PHASE_ARTIFACTS: dict[str, tuple[str, ...]] = {
    "specify": ("spec.md",),
    "plan": ("plan.md",),
    "tasks": ("tasks.md",),
}
PHASE_ORDER: tuple[str, ...] = ("specify", "plan", "tasks")


def select_execution_sync_dir(workspace: Path, *, create: bool = False) -> Path:
    """Prefer the canonical HLDspec control dir while preserving legacy reads."""
    canonical = workspace / ".hldspec" / "sync"
    legacy = workspace / ".specify" / "sync"
    markers = ("speckit_bundle_queue.json", "speckit_invocation_queue.json")
    for sync in (canonical, legacy):
        if any((sync / marker).exists() for marker in markers):
            return sync
    if create:
        canonical.mkdir(parents=True, exist_ok=True)
    return canonical


def _bundles_from_queue(queue: dict[str, Any]) -> list[dict[str, Any]]:
    bundles = [bundle for bundle in as_list(queue.get("bundles")) if isinstance(bundle, dict)]
    if bundles:
        return bundles

    items = [item for item in as_list(queue.get("items")) if isinstance(item, dict)]
    out: list[dict[str, Any]] = []
    for index, item in enumerate(items, start=1):
        feature_id = str(item.get("feature_id") or item.get("planned_spec_id") or item.get("id") or f"feature-{index:03d}")
        short_name = str(item.get("short_name") or item.get("spec_dir") or item.get("slug") or "")
        out.append(
            {
                "bundle_id": feature_id,
                "bundle_slug": str(item.get("bundle_slug") or item.get("feature_slug") or feature_id.lower()),
                "prompt_paths": as_dict(item.get("prompt_paths")),
                "included_specs": [{**item, "feature_id": feature_id, "short_name": short_name}],
            }
        )
    return out


def _nonempty(path: Path) -> bool:
    try:
        return path.is_file() and path.stat().st_size > 0
    except OSError:
        return False


def first_pending_phase(phases: dict[str, str]) -> str | None:
    for phase in PHASE_ORDER:
        if phases.get(phase) != "DONE":
            return phase
    return None


def assess_spec(speckit_root: Path, short_name: str) -> dict[str, Any]:
    """Derive per-phase status for one spec from on-disk SpecKit artifacts."""
    spec_dir = speckit_root / short_name
    phases: dict[str, str] = {}
    if not spec_dir.exists():
        for phase in PHASE_ORDER:
            phases[phase] = "NOT_STARTED"
        return {
            "short_name": short_name,
            "spec_dir": str(spec_dir),
            "exists": False,
            "phases": phases,
            "status": "NOT_STARTED",
        }
    for phase, files in PHASE_ARTIFACTS.items():
        phases[phase] = "DONE" if any(_nonempty(spec_dir / f) for f in files) else "PENDING"
    pending = first_pending_phase(phases)
    status = "DONE" if pending is None else f"PENDING_{pending.upper()}"
    return {
        "short_name": short_name,
        "spec_dir": str(spec_dir),
        "exists": True,
        "phases": phases,
        "status": status,
    }


def build_execution_state(workspace: Path, speckit_root: Path) -> dict[str, Any]:
    sync = select_execution_sync_dir(workspace)
    queue = load_json_dict(sync / "speckit_bundle_queue.json") or load_json_dict(sync / "speckit_invocation_queue.json")
    bundles = _bundles_from_queue(queue)
    assessable = speckit_root.exists() and speckit_root.is_dir()

    out_bundles: list[dict[str, Any]] = []
    resume: dict[str, Any] | None = None

    for bundle in bundles:
        specs_out: list[dict[str, Any]] = []
        bundle_status = "DONE"
        for spec in as_list(bundle.get("included_specs")):
            if not isinstance(spec, dict):
                continue
            short_name = str(spec.get("short_name") or "")
            if assessable and short_name:
                assessment = assess_spec(speckit_root, short_name)
            else:
                assessment = {
                    "short_name": short_name,
                    "spec_dir": "",
                    "exists": False,
                    "phases": {phase: "UNKNOWN" for phase in PHASE_ORDER},
                    "status": "UNKNOWN",
                }
            entry = {"feature_id": str(spec.get("feature_id", "")), **assessment}
            specs_out.append(entry)

            if entry["status"] != "DONE" and bundle_status == "DONE":
                bundle_status = entry["status"]
            if assessable and entry["status"] not in {"DONE"} and resume is None:
                resume = {
                    "bundle_id": str(bundle.get("bundle_id", "")),
                    "bundle_slug": str(bundle.get("bundle_slug", "")),
                    "feature_id": entry["feature_id"],
                    "short_name": short_name,
                    "phase": first_pending_phase(assessment.get("phases", {})) or "specify",
                    "prompt_paths": as_dict(bundle.get("prompt_paths")),
                }

        out_bundles.append(
            {
                "bundle_id": str(bundle.get("bundle_id", "")),
                "bundle_slug": str(bundle.get("bundle_slug", "")),
                "status": bundle_status,
                "prompt_paths": as_dict(bundle.get("prompt_paths")),
                "specs": specs_out,
            }
        )

    if not assessable:
        status = "UNKNOWN"
    elif resume is None and out_bundles:
        status = "ALL_TASKS_DONE"
    elif not out_bundles:
        status = "NO_BUNDLES"
    else:
        status = "IN_PROGRESS"

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "speckit_root": str(speckit_root),
        "assessable": assessable,
        "status": status,
        "resume": resume,
        "bundle_count": len(out_bundles),
        "bundles": out_bundles,
    }


def write_execution_state(workspace: Path, speckit_root: Path) -> dict[str, Any]:
    """Write derived progress assessment without touching machine continuation state."""
    sync = select_execution_sync_dir(workspace, create=True)
    payload = build_execution_state(workspace, speckit_root)
    write_json_dict(sync / ASSESSMENT_JSON, payload)
    (sync / ASSESSMENT_MD).write_text(render_execution_state_md(payload), encoding="utf-8")
    return payload


def _ordered_prompt_paths(payload: dict[str, Any], runtime: str) -> list[str]:
    paths: list[str] = []
    for bundle in as_list(payload.get("bundles")):
        if not isinstance(bundle, dict):
            continue
        path = as_dict(bundle.get("prompt_paths")).get(runtime)
        if path:
            paths.append(str(path))
    return paths


def next_action(payload: dict[str, Any], runtime: str = "claude") -> dict[str, Any]:
    """Map execution state -> next action with an hldspec_v2-style exit code.

    0 = a clear next step exists (continue) or nothing blocks progress;
    2 = a human checkpoint is required (e.g. implementation approval);
    3 = blocked / unassessable -> fall back to the do-it-all handoff.
    """
    status = str(payload.get("status", ""))
    ordered = _ordered_prompt_paths(payload, runtime)

    if status == "UNKNOWN":
        return {
            "exit_code": 3,
            "mode": "DO_IT_ALL",
            "headline": "Cannot assess SpecKit progress. Hand the whole job to SpecKit and let it drive.",
            "instruction": (
                "Run the bundle prompts in order. Each is self-driving: it runs the full SpecKit "
                "ritual (constitution -> specify -> clarify -> plan -> analyze -> tasks), applies the "
                "real RunSkeptic between gates, escalates to the user when evidence is missing, and "
                "stops at its completion gate before the next bundle."
            ),
            "ordered_prompts": ordered,
        }

    if status == "NO_BUNDLES":
        return {
            "exit_code": 3,
            "mode": "NO_BUNDLES",
            "headline": "No bundle queue found. Run build_speckit_bundle_queue.py then build_speckit_bundle_prompts.py first.",
            "ordered_prompts": [],
        }

    if status == "ALL_TASKS_DONE":
        return {
            "exit_code": 2,
            "mode": "IMPLEMENT_GATE",
            "headline": "All specs have tasks generated. Implementation is gated — approve to proceed per spec.",
            "ordered_prompts": ordered,
        }

    resume = payload.get("resume") if isinstance(payload.get("resume"), dict) else {}
    bundle_prompt = as_dict(resume.get("prompt_paths")).get(runtime)
    return {
        "exit_code": 0,
        "mode": "CONTINUE",
        "headline": (
            f"Resume bundle {resume.get('bundle_id', '')} at spec {resume.get('feature_id', '')} "
            f"(phase: {resume.get('phase', '')})."
        ),
        "bundle_prompt": bundle_prompt,
        "resume": resume,
        "instruction": (
            f"Open the bundle prompt above and resume at spec `{resume.get('feature_id', '')}` "
            f"phase `{resume.get('phase', '')}`. Skip phases already marked DONE in the state report; "
            "re-run the RunSkeptic gate for the resumed phase before continuing."
        ),
        "ordered_prompts": ordered,
    }


def render_execution_state_md(payload: dict[str, Any]) -> str:
    lines = [
        "# SpecKit Execution State",
        "",
        f"Status: `{payload.get('status', '')}`",
        f"SpecKit root: `{payload.get('speckit_root', '')}`",
        f"Assessable: `{payload.get('assessable', False)}`",
        "",
    ]
    resume = payload.get("resume")
    if isinstance(resume, dict):
        lines += [
            "## Resume point",
            "",
            f"- bundle: `{resume.get('bundle_id', '')}` `{resume.get('bundle_slug', '')}`",
            f"- spec: `{resume.get('feature_id', '')}` (`{resume.get('short_name', '')}`)",
            f"- next phase: `{resume.get('phase', '')}`",
            "",
        ]
    lines += ["## Bundles", "", "| Bundle | Status | Specs (status) |", "|---|---|---|"]
    for bundle in as_list(payload.get("bundles")):
        if not isinstance(bundle, dict):
            continue
        specs = "; ".join(
            f"`{s.get('feature_id', '')}`:{s.get('status', '')}"
            for s in as_list(bundle.get("specs"))
            if isinstance(s, dict)
        )
        lines.append(f"| `{bundle.get('bundle_id', '')}` {bundle.get('bundle_slug', '')} | `{bundle.get('status', '')}` | {specs} |")
    return "\n".join(lines) + "\n"
