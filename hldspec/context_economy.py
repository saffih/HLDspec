from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"

PHASES: tuple[tuple[str, str, str], ...] = (
    ("01-specify", "SpecKit specify", "MODEL_STRONG"),
    ("02-clarify", "SpecKit clarify", "MODEL_STRONG"),
    ("03-plan", "SpecKit plan", "MODEL_CRITICAL"),
    ("04-research-data-contracts", "SpecKit research/data/contracts", "MODEL_CRITICAL"),
    ("05-tasks", "SpecKit tasks", "MODEL_STRONG"),
    ("06-implement", "SpecKit implement", "MODEL_STRONG"),
    ("07-verify-runskeptic", "Verify and RunSkeptic", "MODEL_CRITICAL"),
)

REQUIRED_PROMPT_MARKERS: tuple[str, ...] = (
    "## Target",
    "## Package",
    "## Exact phase",
    "## Allowed evidence",
    "## Forbidden reads",
    "## Model tier",
    "## Scope limit",
    "## Stop condition",
    "## RunSkeptic triggers",
    "## Expected outputs",
    "## Human checkpoint rules",
)

FORBIDDEN_BROAD_READ_PATTERNS: tuple[str, ...] = (
    "read the whole repo",
    "read the entire repo",
    "read the whole repository",
    "read the entire repository",
    "scan the whole repo",
    "scan the entire repo",
    "scan the whole repository",
    "scan the entire repository",
    "read everything",
)


@dataclass(frozen=True)
class PackageSpec:
    package_id: str
    package_name: str
    description: str = ""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def relpath(path: Path, root: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _first_str(item: dict[str, Any], names: tuple[str, ...], default: str) -> str:
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if isinstance(value, int):
            return str(value)
    return default


def discover_packages(target: Path) -> list[PackageSpec]:
    candidates = [
        target / ".hldspec" / "spec_packages.json",
        target / ".hldspec" / "sync" / "spec_packages.json",
        target / ".hldspec" / "sync" / "spec_build_plan.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = read_json(path)
        except Exception:
            continue
        raw_packages: list[Any] = []
        if isinstance(data, list):
            raw_packages = data
        elif isinstance(data, dict):
            for key in ("packages", "spec_packages", "planned_specs", "features"):
                if isinstance(data.get(key), list):
                    raw_packages = data[key]
                    break
        packages: list[PackageSpec] = []
        for idx, item in enumerate(raw_packages, start=1):
            if not isinstance(item, dict):
                continue
            package_id = _first_str(
                item,
                ("package_id", "id", "spec_id", "feature_id", "slug"),
                f"{idx:03d}-package",
            )
            package_name = _first_str(
                item,
                ("package_name", "name", "title", "feature_name"),
                package_id,
            )
            description = _first_str(item, ("description", "summary", "why"), "")
            packages.append(PackageSpec(package_id=package_id, package_name=package_name, description=description))
        if packages:
            return packages
    return [PackageSpec(package_id="001-foundation", package_name="Foundation package", description="Fallback package used until package planning artifacts exist.")]


def default_allowed_evidence(target: Path, package: PackageSpec) -> list[str]:
    candidates = [
        target / "targetHLD" / "HLD.md",
        target / "targetHLD" / "raw" / "HLD.raw.md",
        target / ".hldspec" / "interview_answers.json",
        target / ".hldspec" / "interview_answers.md",
        target / ".hldspec" / "spec_packages.json",
        target / ".hldspec" / "spec_packages.md",
        target / ".hldspec" / "feature_dependency_graph.json",
        target / ".hldspec" / "feature_dependency_graph.md",
        target / ".hldspec" / "speckit_invocation_queue.json",
        target / ".hldspec" / "speckit_invocation_queue.md",
        target / ".hldspec" / "sync" / "spec_build_plan.json",
        target / ".hldspec" / "sync" / "spec_build_plan_review.md",
        target / ".hldspec" / "sync" / "speckit_prework_package.md",
        target / ".hldspec" / "sync" / "speckit_prework_quality_review.md",
    ]
    evidence = [relpath(path, target) for path in candidates if path.exists()]
    if not evidence:
        evidence = ["targetHLD/HLD.md"]
    return sorted(dict.fromkeys(evidence))


def forbidden_reads_text() -> str:
    return """# Forbidden Reads for Bounded Delegation

These rules apply to generated SpecKit delegation prompts.

- Use only files listed in `target/.hldspec/allowed_evidence.json` for the specific package and phase.
- Do not perform broad repository scans.
- Do not recursively inspect `target/`.
- Do not inspect source files outside the target workspace unless they are explicitly listed as allowed evidence.
- Do not infer missing architecture decisions from unrelated files.
- Escalate missing evidence to the human instead of guessing.
"""


def render_context_pack_md(target: Path, package: PackageSpec, evidence: list[str]) -> str:
    lines = [
        f"# Context Pack - {package.package_id}",
        "",
        f"Package: `{package.package_name}`",
        "",
        "## Purpose",
        "",
        "Bound the evidence for one package so delegated agents do not read broadly or import unrelated context.",
        "",
        "## Allowed evidence",
        "",
    ]
    lines.extend(f"- `{item}`" for item in evidence)
    lines.extend(
        [
            "",
            "## Forbidden reads",
            "",
            "See `target/.hldspec/forbidden_reads.md`.",
            "",
            "## Model tier",
            "",
            "Phase prompts define the required model tier per phase.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_prompt(target: Path, package: PackageSpec, phase_id: str, phase_name: str, model_tier: str, evidence: list[str]) -> str:
    phase_dir = target / "prompts" / "speckit" / package.package_id
    allowed_json = target / ".hldspec" / "allowed_evidence.json"
    forbidden_md = target / ".hldspec" / "forbidden_reads.md"
    context_json = target / ".hldspec" / "context_packs" / package.package_id / "context_pack.json"
    approval_note = ""
    if phase_id == "06-implement":
        approval_note = (
            "\nImplementation phase guard: before changing product code, require explicit human approval "
            "recorded in target/.hldspec/speckit_implementation_approval.json with status APPROVED.\n"
        )
    return f"""# {phase_name} Prompt - {package.package_id}

## Target

`{target}`

## Package

- Package id: `{package.package_id}`
- Package name: `{package.package_name}`
- Description: {package.description or 'none'}

## Exact phase

`{phase_id}` - {phase_name}

Run only this phase. Do not advance to another phase.

## Allowed evidence

Allowed evidence registry: `{allowed_json}`

""" + "\n".join(f"- `{item}`" for item in evidence) + f"""

Context pack: `{context_json}`

## Forbidden reads

Forbidden-read policy: `{forbidden_md}`

- Any file not listed in Allowed evidence.
- Broad repository scan.
- Recursive target workspace scan.
- Unrelated source, implementation, or generated files.

## Model tier

`{model_tier}`

## Scope limit

One package, one phase, one target workspace. Use the minimum evidence needed. Escalate missing evidence.

## Stop condition

Stop when this phase has produced its expected output, found missing evidence, hit a RunSkeptic ACTION/CONFLICT, or needs human approval.{approval_note}

## RunSkeptic triggers

Run or apply RunSkeptic when:

- evidence contradicts the phase goal
- package boundary or source of truth is unclear
- a prompt would require forbidden reads
- implementation approval is missing for code-changing work
- output would promote an unresolved ACTION or CONFLICT

## Expected outputs

- Phase-specific output for `{phase_id}`.
- Evidence list actually used.
- Human questions or escalation record when evidence is missing.
- RunSkeptic PASS/ACTION/CONFLICT status.

## Human checkpoint rules

- Ask the human before changing package boundaries, constitution rules, dependency order, or implementation state.
- Do not answer unknown SpecKit questions from memory.
- Do not continue after unresolved ACTION or CONFLICT.
"""


def generate_context_and_prompts(target: Path, package_id: str | None = None, package_name: str | None = None) -> dict[str, Any]:
    target = target.resolve()
    target.mkdir(parents=True, exist_ok=True)
    packages = discover_packages(target)
    if package_id:
        package = next((item for item in packages if item.package_id == package_id), None)
        if package is None:
            package = PackageSpec(package_id=package_id, package_name=package_name or package_id)
    else:
        package = packages[0]
    if package_name:
        package = PackageSpec(package_id=package.package_id, package_name=package_name, description=package.description)

    evidence = default_allowed_evidence(target, package)
    hldspec_dir = target / ".hldspec"
    context_dir = hldspec_dir / "context_packs" / package.package_id
    prompt_dir = target / "prompts" / "speckit" / package.package_id
    context_dir.mkdir(parents=True, exist_ok=True)
    prompt_dir.mkdir(parents=True, exist_ok=True)

    allowed_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": utc_now(),
        "target": str(target),
        "packages": [
            {
                "package_id": package.package_id,
                "package_name": package.package_name,
                "allowed_evidence": evidence,
            }
        ],
    }
    write_json(hldspec_dir / "allowed_evidence.json", allowed_payload)
    (hldspec_dir / "forbidden_reads.md").write_text(forbidden_reads_text(), encoding="utf-8")

    context_payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": allowed_payload["generated_at"],
        "target": str(target),
        "package_id": package.package_id,
        "package_name": package.package_name,
        "description": package.description,
        "allowed_evidence": evidence,
        "forbidden_reads": str(hldspec_dir / "forbidden_reads.md"),
        "prompt_dir": str(prompt_dir),
    }
    write_json(context_dir / "context_pack.json", context_payload)
    (context_dir / "context_pack.md").write_text(render_context_pack_md(target, package, evidence), encoding="utf-8")

    prompts: list[str] = []
    for phase_id, phase_name, model_tier in PHASES:
        prompt_path = prompt_dir / f"{phase_id}.md"
        prompt_path.write_text(render_prompt(target, package, phase_id, phase_name, model_tier, evidence), encoding="utf-8")
        prompts.append(str(prompt_path))

    return {
        "target": str(target),
        "package_id": package.package_id,
        "allowed_evidence": str(hldspec_dir / "allowed_evidence.json"),
        "forbidden_reads": str(hldspec_dir / "forbidden_reads.md"),
        "context_pack": str(context_dir / "context_pack.json"),
        "prompt_dir": str(prompt_dir),
        "prompts": prompts,
    }


def validate_prompt_text(text: str) -> list[str]:
    errors: list[str] = []
    for marker in REQUIRED_PROMPT_MARKERS:
        if marker not in text:
            errors.append(f"missing required marker: {marker}")
    lowered = text.lower()
    for pattern in FORBIDDEN_BROAD_READ_PATTERNS:
        if pattern in lowered:
            errors.append(f"prompt contains forbidden broad-read wording: {pattern}")
    if "## Allowed evidence" in text:
        allowed_section = text.split("## Allowed evidence", 1)[1].split("## Forbidden reads", 1)[0]
        if "- `" not in allowed_section:
            errors.append("allowed evidence section has no listed files")
    if "## RunSkeptic triggers" in text:
        runskeptic_section = text.split("## RunSkeptic triggers", 1)[1].split("## Expected outputs", 1)[0]
        if "RunSkeptic" not in runskeptic_section:
            errors.append("RunSkeptic trigger section does not mention RunSkeptic")
    return errors


def validate_prompt_file(path: Path) -> list[str]:
    if not path.exists():
        return [f"missing prompt: {path}"]
    return validate_prompt_text(path.read_text(encoding="utf-8"))


def validate_prompt_tree(target: Path) -> dict[str, list[str]]:
    prompt_root = target / "prompts" / "speckit"
    errors: dict[str, list[str]] = {}
    if not prompt_root.exists():
        return {str(prompt_root): ["missing prompts/speckit directory"]}
    for prompt in sorted(prompt_root.glob("*/*.md")):
        prompt_errors = validate_prompt_file(prompt)
        if prompt_errors:
            errors[str(prompt)] = prompt_errors
    if not list(prompt_root.glob("*/*.md")):
        errors[str(prompt_root)] = ["no generated prompts found"]
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate and validate bounded SpecKit delegation prompts.")
    parser.add_argument("target", help="Target workspace path.")
    parser.add_argument("--package-id", default="", help="Package id to generate. Defaults to first discovered package.")
    parser.add_argument("--package-name", default="", help="Package name override.")
    parser.add_argument("--validate-only", action="store_true", help="Validate existing generated prompts without generating.")
    args = parser.parse_args(argv)

    target = Path(args.target).expanduser().resolve()
    if not args.validate_only:
        result = generate_context_and_prompts(target, package_id=args.package_id or None, package_name=args.package_name or None)
        print(json.dumps(result, indent=2, sort_keys=True))
    errors = validate_prompt_tree(target)
    if errors:
        print(json.dumps({"validation_errors": errors}, indent=2, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
