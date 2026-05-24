#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ORDER = {
    "governance": 0,
    "foundation_data_tool": 1,
    "use_logic_orchestration": 2,
    "api_contract": 3,
    "ui_workflow": 4,
    "operations_validation": 5,
    "boundary_mixed": 1,
    "unknown": 9,
}
MAX_REVIEWABLE_SPEC_COUNT = 30
CONTEXT_TITLE_WORDS = {
    "assumption",
    "architecture overview",
    "business case",
    "changelog",
    "critical integration",
    "data flow",
    "decision log",
    "executive summary",
    "handoff",
    "lesson",
    "milestone",
    "next step",
    "open conflict",
    "open question",
    "overview",
    "specification hierarchy",
    "stakeholder",
    "success criteria",
    "technical debt",
    "technology stack",
    "tea architecture",
    "user stories",
    "user persona",
    "v1 scope",
}
TOKEN_STOPWORDS = {
    "and",
    "contract",
    "core",
    "critical",
    "feature",
    "flow",
    "interface",
    "layer",
    "source",
    "spec",
    "the",
    "truth",
}
CONSTITUTION_TITLE_WORDS = {
    "data retention",
    "governance",
    "important: single source of truth",
    "security consideration",
}


def load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sync_dir(workspace: Path) -> Path:
    direct = workspace / ".specify" / "sync"
    nested = workspace / "firstrun" / ".specify" / "sync"
    if (direct / "hldspec_architecture_analysis.json").exists():
        return direct
    if (nested / "hldspec_architecture_analysis.json").exists():
        return nested
    direct.mkdir(parents=True, exist_ok=True)
    return direct


def slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return text[:50] or "spec"


def split_candidates(section: dict[str, Any]) -> list[dict[str, Any]]:
    hld_id = section["hld_id"]
    title = section["title"]
    lower = title.lower()
    tool_kind = "Storage" if "storage" in lower else "Database" if "database" in lower or "db" in lower else "Foundation/Data"

    return [
        {
            "source_hld_ids": [hld_id],
            "title": f"{title} - {tool_kind} Interface",
            "layer": "foundation_data_tool",
            "reason": "split low-level tool/data/state ownership from higher layers",
        },
        {
            "source_hld_ids": [hld_id],
            "title": f"{title} - Use Logic and Orchestration",
            "layer": "use_logic_orchestration",
            "reason": "split domain behavior and lifecycle rules from tool and API layers",
        },
        {
            "source_hld_ids": [hld_id],
            "title": f"{title} - API Contract",
            "layer": "api_contract",
            "reason": "split caller-facing contract from implementation and use logic",
        },
    ]


def title_has(title: str, words: set[str]) -> bool:
    lower = title.lower()
    return any(word in lower for word in words)


def token_set(text: str) -> set[str]:
    normalized = text.lower().replace("entrypoint", "entry point").replace("coremd", "core md")
    tokens = set()
    for token in re.split(r"[^a-z0-9]+", normalized):
        if len(token) <= 2 or token in TOKEN_STOPWORDS:
            continue
        tokens.add("spawn" if token == "spawning" else token)
    return tokens


def spec_title(spec_dir: Path) -> str:
    spec_md = spec_dir / "spec.md"
    if not spec_md.exists():
        return ""
    text = spec_md.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^#\s+Feature Specification:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def spec_hld_refs(spec_dir: Path) -> list[str]:
    spec_md = spec_dir / "spec.md"
    if not spec_md.exists():
        return []
    text = spec_md.read_text(encoding="utf-8", errors="replace")
    return sorted(set(re.findall(r"\bHLD-[0-9A-Za-z_-]+\b", text)))


def active_spec_match(section: dict[str, Any], active_specs: list[dict[str, Any]]) -> dict[str, Any]:
    title = str(section.get("title", ""))
    hld_id = str(section.get("hld_id", ""))
    title_tokens = token_set(title)
    best: tuple[int, dict[str, Any]] = (0, {})
    for spec in active_specs:
        hld_refs = spec.get("hld_refs", [])
        if hld_id and isinstance(hld_refs, list) and hld_id in hld_refs:
            return spec
        spec_text = " ".join(
            [
                str(spec.get("spec_id", "")),
                str(spec.get("slug", "")),
                str(spec.get("title", "")),
                " ".join(str(ref) for ref in hld_refs if isinstance(ref, str)),
            ]
        )
        overlap = len(title_tokens & token_set(spec_text))
        if overlap > best[0]:
            best = (overlap, spec)
    return best[1] if best[0] >= 2 else {}


def boundary_decision(section: dict[str, Any], active_specs: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Classify whether an HLD section should become specs, stay whole, or be context.

    The split force must be balanced by keep/merge/demote decisions. Otherwise
    broad context sections that merely mention APIs turn into mechanical specs.
    """
    title = str(section.get("title", ""))
    layer = str(section.get("layer", "unknown"))
    spec_candidate = bool(section.get("spec_candidate"))
    requires_split = bool(section.get("requires_layered_split"))
    active_match = active_spec_match(section, active_specs or [])

    if title_has(title, CONSTITUTION_TITLE_WORDS):
        return {
            "decision": "CONSTITUTION_ONLY",
            "reason": "section is architecture/governance constraint material, not a standalone SpecKit feature",
            "promote_to_specs": False,
        }
    if title_has(title, CONTEXT_TITLE_WORDS):
        return {
            "decision": "DEMOTE_TO_CONTEXT",
            "reason": "section is planning, history, summary, handoff, or reference context",
            "promote_to_specs": False,
        }
    if active_match:
        return {
            "decision": "MERGE_WITH_ACTIVE_SPEC",
            "reason": f"covered by active non-historical spec {active_match.get('spec_id')}; do not create a duplicate spec",
            "promote_to_specs": False,
            "active_spec_id": active_match.get("spec_id", ""),
        }
    if layer in {"governance", "unknown"}:
        return {
            "decision": "REFERENCE_ONLY",
            "reason": f"section layer is {layer}; use as evidence for specs rather than a standalone spec",
            "promote_to_specs": False,
        }
    if requires_split and spec_candidate:
        return {
            "decision": "SPLIT",
            "reason": "section has buildable mixed responsibilities with independently evolvable boundaries",
            "promote_to_specs": True,
        }
    if spec_candidate:
        return {
            "decision": "KEEP_AS_ONE",
            "reason": "section is a buildable capability and no independent layered split is required",
            "promote_to_specs": True,
        }
    return {
        "decision": "REFERENCE_ONLY",
        "reason": "section is supporting evidence only",
        "promote_to_specs": False,
    }


def spec_feature_branch(spec_dir: Path) -> str:
    spec_md = spec_dir / "spec.md"
    if not spec_md.exists():
        return ""
    text = spec_md.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"^\*\*Feature Branch\*\*:\s*`?\[?([^`\]\n]+)\]?`?", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def default_branch(source_project: Path) -> str:
    for candidate in ("main", "master"):
        result = subprocess.run(
            ["git", "-C", str(source_project), "rev-parse", "--verify", candidate],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode == 0:
            return candidate
    return "HEAD"


def merged_branch_evidence(source_project: Path, branch_name: str) -> dict[str, str]:
    if not branch_name or not (source_project / ".git").exists():
        return {}

    branch = default_branch(source_project)
    for ref in (f"refs/heads/{branch_name}", f"refs/remotes/origin/{branch_name}"):
        rev = subprocess.run(
            ["git", "-C", str(source_project), "rev-parse", "--verify", ref],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if rev.returncode != 0:
            continue
        candidate = rev.stdout.strip()
        ancestor = subprocess.run(
            ["git", "-C", str(source_project), "merge-base", "--is-ancestor", candidate, branch],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if ancestor.returncode == 0:
            return {"commit": candidate, "subject": f"{branch_name} is ancestor of {branch}", "mainline": branch, "evidence_type": "MERGE_ANCESTOR"}

    result = subprocess.run(
        [
            "git",
            "-C",
            str(source_project),
            "log",
            "--merges",
            "--first-parent",
            "--format=%H%x09%s",
            branch,
        ],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return {}

    for line in result.stdout.splitlines():
        commit, _, subject = line.partition("\t")
        if branch_name_mentioned(subject, branch_name):
            return {"commit": commit, "subject": subject, "mainline": branch, "evidence_type": "MERGE_SUBJECT"}
    return {}


def branch_name_mentioned(subject: str, branch_name: str) -> bool:
    escaped = re.escape(branch_name)
    return bool(re.search(rf"(?<![A-Za-z0-9._/-]){escaped}(?![A-Za-z0-9._/-])", subject))


def scan_existing_specs(source_project: Path) -> dict[str, Any]:
    """Scan target project's specs/ directory and classify completed historical specs.

    SpecKit completion is represented by a normal merge of the feature
    branch. A spec that merely exists is not historical unless its feature branch
    appears in first-parent merge history.
    """
    specs_dir = source_project / "specs"
    if not specs_dir.is_dir():
        return {
            "found": False,
            "specs_dir": str(specs_dir),
            "existing_ids": [],
            "highest_number": 0,
            "conflicts": [],
            "history_rule": "MERGED_DONE requires the spec Feature Branch to appear in a first-parent merge commit.",
            "historical_count": 0,
            "non_historical_count": 0,
            "historical_ids": [],
            "non_historical_ids": [],
        }

    existing: list[dict[str, Any]] = []
    for entry in sorted(specs_dir.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        # Match NNN-slug format
        m = re.match(r"^(\d+)-(.+)$", name)
        if m:
            feature_branch = spec_feature_branch(entry)
            merge = merged_branch_evidence(source_project, feature_branch)
            history_status = "MERGED_DONE" if merge else "NOT_HISTORICAL"
            existing.append(
                {
                    "spec_id": name,
                    "number": int(m.group(1)),
                    "slug": m.group(2),
                    "title": spec_title(entry),
                    "hld_refs": spec_hld_refs(entry),
                    "feature_branch": feature_branch,
                    "history_status": history_status,
                    "merge_evidence": merge,
                }
            )

    highest = max((s["number"] for s in existing), default=0)
    historical_ids = [s["spec_id"] for s in existing if s["history_status"] == "MERGED_DONE"]
    non_historical_ids = [s["spec_id"] for s in existing if s["history_status"] != "MERGED_DONE"]
    return {
        "found": True,
        "specs_dir": str(specs_dir),
        "existing_ids": [s["spec_id"] for s in existing],
        "existing_specs": existing,
        "existing_count": len(existing),
        "highest_number": highest,
        "history_rule": "MERGED_DONE requires the spec Feature Branch to appear in a first-parent merge commit.",
        "historical_count": len(historical_ids),
        "non_historical_count": len(non_historical_ids),
        "historical_ids": historical_ids,
        "non_historical_ids": non_historical_ids,
        "conflicts": [],  # filled in after numbering
    }


def build_list(workspace: Path, source_project: Path | None = None) -> dict[str, Any]:
    sync = sync_dir(workspace)
    analysis = load_json(sync / "hldspec_architecture_analysis.json")
    specs: list[dict[str, Any]] = []
    boundary_decisions: list[dict[str, Any]] = []
    existing_scan: dict[str, Any] = {"found": False, "existing_ids": [], "highest_number": 0, "conflicts": []}
    if source_project:
        existing_scan = scan_existing_specs(source_project)
    active_specs = [
        item for item in existing_scan.get("existing_specs", [])
        if isinstance(item, dict) and item.get("history_status") != "MERGED_DONE"
    ]

    for section in analysis.get("sections", []):
        if not isinstance(section, dict):
            continue
        decision = boundary_decision(section, active_specs)
        boundary_decisions.append(
            {
                "hld_id": section.get("hld_id"),
                "title": section.get("title"),
                "layer": section.get("layer", "unknown"),
                "decision": decision["decision"],
                "reason": decision["reason"],
                "active_spec_id": decision.get("active_spec_id", ""),
            }
        )
        if not decision["promote_to_specs"]:
            continue
        if decision["decision"] == "SPLIT":
            specs.extend(split_candidates(section))
        else:
            specs.append(
                {
                    "source_hld_ids": [section.get("hld_id")],
                    "title": section.get("title", "Untitled"),
                    "layer": section.get("layer", "unknown"),
                    "reason": decision["reason"],
                }
            )

    specs.sort(key=lambda item: (ORDER.get(str(item.get("layer")), 9), str(item.get("title"))))

    start_idx = existing_scan["highest_number"] + 1 if existing_scan.get("highest_number", 0) > 0 else 1
    existing_ids_set = set(existing_scan.get("existing_ids", []))

    numbered: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    for offset, spec in enumerate(specs):
        idx = start_idx + offset
        layer = str(spec.get("layer", "unknown"))
        spec_id = f"{idx:03d}-{slugify(str(spec.get('title')))}"
        # Check for numeric collision even if slug differs
        conflict_ids = [eid for eid in existing_ids_set if eid.startswith(f"{idx:03d}-")]
        if conflict_ids:
            conflicts.append({"planned_id": spec_id, "conflicts_with": conflict_ids})
        numbered.append(
            {
                "spec_id": spec_id,
                "title": spec.get("title"),
                "layer": layer,
                "source_hld_ids": spec.get("source_hld_ids", []),
                "depends_on_layers": [name for name, rank in ORDER.items() if rank < ORDER.get(layer, 9) and name not in {"boundary_mixed", "unknown"}],
                "reason": spec.get("reason", ""),
                "status": "PLANNED_REVIEW",
            }
        )

    existing_scan["conflicts"] = conflicts
    has_conflicts = bool(conflicts)
    decision_counts: dict[str, int] = {}
    for item in boundary_decisions:
        decision = str(item.get("decision", "UNKNOWN"))
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
    blocking: list[str] = []
    if len(numbered) > MAX_REVIEWABLE_SPEC_COUNT:
        blocking.append(f"spec count {len(numbered)} exceeds reviewable threshold {MAX_REVIEWABLE_SPEC_COUNT}")
    if has_conflicts:
        blocking.append("planned spec IDs conflict with existing project specs")

    if not numbered:
        status = "NO_SPEC_CANDIDATES"
    elif blocking:
        status = "SPEC_LIST_REQUIRES_DECOMPOSITION"
    else:
        status = "SPEC_LIST_READY_FOR_REVIEW"

    return {
        "schema_version": 1,
        "workspace": str(workspace),
        "source_project": str(source_project) if source_project else None,
        "status": status,
        "ordering_rule": "bottom-up: governance, foundation/data/tool, logic/orchestration, API, UI, operations/testing",
        "max_reviewable_spec_count": MAX_REVIEWABLE_SPEC_COUNT,
        "spec_count": len(numbered),
        "blocking": blocking,
        "boundary_decision_counts": decision_counts,
        "boundary_decisions": boundary_decisions,
        "existing_specs_scan": existing_scan,
        "specs": numbered,
    }


def render_md(data: dict[str, Any]) -> str:
    scan = data.get("existing_specs_scan") or {}
    lines = [
        "# HLDspec SpecKit Spec List",
        "",
        "",
        "",
        f"Status: `{data.get('status')}`",
        f"Spec count: {data.get('spec_count')}",
        f"Max reviewable spec count: {data.get('max_reviewable_spec_count')}",
        "",
    ]
    if data.get("blocking"):
        lines += ["## Blocking", ""]
        for item in data.get("blocking", []):
            lines.append(f"- {item}")
        lines.append("")
    if data.get("source_project"):
        lines += [f"Source project: `{data['source_project']}`", ""]
    if scan.get("found"):
        lines += [
            "## Existing specs scan",
            "",
            f"- scanned: `{scan.get('specs_dir')}`",
            f"- existing count: {scan.get('existing_count', 0)}",
            f"- highest existing number: {scan.get('highest_number', 0)}",
            f"- new specs start at: `{scan.get('highest_number', 0) + 1:03d}-...`",
            f"- history rule: {scan.get('history_rule', '')}",
            f"- historical merged specs: {scan.get('historical_count', 0)}",
            f"- non-historical specs: {scan.get('non_historical_count', 0)}",
            "",
        ]
        existing_specs = [item for item in scan.get("existing_specs", []) if isinstance(item, dict)]
        if existing_specs:
            lines += ["### Existing spec history status", ""]
            for item in existing_specs:
                evidence = item.get("merge_evidence") if isinstance(item.get("merge_evidence"), dict) else {}
                merge = f" merge={evidence.get('commit', '')[:12]}" if evidence.get("commit") else ""
                lines.append(
                    f"- `{item.get('spec_id')}`: `{item.get('history_status')}` "
                    f"branch=`{item.get('feature_branch') or 'TBD'}`{merge}"
                )
            lines.append("")
        if scan.get("conflicts"):
            lines += ["### ⚠ ID conflicts — RESOLVE before approval", ""]
            for c in scan["conflicts"]:
                lines.append(f"- planned `{c['planned_id']}` conflicts with existing: {', '.join(c['conflicts_with'])}")
            lines.append("")
    elif data.get("source_project"):
        lines += [f"- No existing specs found at `{scan.get('specs_dir')}` — numbering starts at 001", ""]

    lines += [
        "Ordering rule:",
        "",
        data.get("ordering_rule", ""),
        "",
        "## Boundary decision counts",
        "",
    ]
    for decision, count in sorted((data.get("boundary_decision_counts") or {}).items()):
        lines.append(f"- `{decision}`: {count}")
    lines += [
        "",
        "## Demoted / reference sections",
        "",
    ]
    demoted = [item for item in data.get("boundary_decisions", []) if item.get("decision") not in {"SPLIT", "KEEP_AS_ONE"}]
    if not demoted:
        lines.append("- none")
    for item in demoted:
        active = f" active=`{item.get('active_spec_id')}`" if item.get("active_spec_id") else ""
        lines.append(f"- `{item.get('hld_id')}` {item.get('title')}: `{item.get('decision')}`{active} - {item.get('reason')}")
    lines += [
        "",
        "## Planned specs",
        "",
    ]
    if not data.get("specs"):
        lines.append("- none")
    for spec in data.get("specs", []):
        lines += [
            f"### {spec.get('spec_id')}",
            "",
            f"- title: {spec.get('title')}",
            f"- layer: `{spec.get('layer')}`",
            f"- source HLD ids: {', '.join(spec.get('source_hld_ids', []))}",
            f"- depends on layers: {', '.join(spec.get('depends_on_layers', [])) or 'none'}",
            f"- reason: {spec.get('reason')}",
            f"- status: `{spec.get('status')}`",
            "",
        ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build dependency-aware SpecKit spec list from HLDspec architecture analysis.")
    parser.add_argument("workspace")
    parser.add_argument("--source-project", help="Path to target project root (scans its specs/ for existing IDs to avoid conflicts)")
    args = parser.parse_args()

    workspace = Path(args.workspace).expanduser().resolve()
    source_project = Path(args.source_project).expanduser().resolve() if args.source_project else None
    sync = sync_dir(workspace)
    data = build_list(workspace, source_project)
    json_path = sync / "hldspec_speckit_spec_list.json"
    md_path = sync / "hldspec_speckit_spec_list.md"
    write_json(json_path, data)
    md_path.write_text(render_md(data), encoding="utf-8")

    print("HLDspec SpecKit spec list generated:")
    print(f"- json: {json_path}")
    print(f"- report: {md_path}")
    print(f"- status: {data['status']}")
    print(f"- spec count: {data['spec_count']}")
    conflicts = (data.get("existing_specs_scan") or {}).get("conflicts", [])
    if conflicts:
        print(f"- WARNING: {len(conflicts)} ID conflict(s) with existing project specs — resolve before approval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
