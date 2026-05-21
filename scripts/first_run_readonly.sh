#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/first_run_readonly.sh <path-to-HLD.md> [workspace] [--force]

Examples:
  bash scripts/first_run_readonly.sh ~/Downloads/HLD.md
  bash scripts/first_run_readonly.sh ~/Downloads/HLD.md /tmp/my-hldspec-first-run --force

What this does:
  Raw/working HLD copy
  -> HLD format report
  -> HLD map
  -> Spec Build Plan
  -> Plan Quality Gate
  -> Spec Build Plan Review

Safety:
  - read-only relative to your source HLD
  - does not call an agent
  - does not create specs
  - does not create target .specify/memory/constitution.md
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

HLD_SOURCE="$1"
WORKSPACE="${2:-$(mktemp -d /tmp/hldspec-first-run.XXXXXX)}"
FORCE="${3:-}"

if [ ! -f "$HLD_SOURCE" ]; then
  echo "ERROR: HLD source not found: $HLD_SOURCE" >&2
  exit 1
fi

if [ -e "$WORKSPACE" ] && [ -n "$(find "$WORKSPACE" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]; then
  if [ "$FORCE" = "--force" ] || [ "${HLD_SPEC_FIRST_RUN_FORCE:-0}" = "1" ]; then
    rm -rf "$WORKSPACE"
  else
    echo "ERROR: workspace exists and is not empty: $WORKSPACE" >&2
    echo "Use --force as the third argument or choose a new workspace." >&2
    exit 1
  fi
fi

mkdir -p "$WORKSPACE"
cp "$HLD_SOURCE" "$WORKSPACE/HLD.raw.md"
cp "$HLD_SOURCE" "$WORKSPACE/HLD.md"

echo "Workspace: $WORKSPACE"
echo "Source HLD: $HLD_SOURCE"
echo

python3 "$ROOT/hld_spec_sync.py" --workspace "$WORKSPACE" --hld HLD.md --hld-format-report

REPORT_DIR="$(ls -dt "$WORKSPACE"/logs/hld_spec_sync/* | head -1)"
REPORT_JSON="$REPORT_DIR/suggested_hld_sections.json"

python3 - "$REPORT_JSON" "$WORKSPACE" "$HLD_SOURCE" <<'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
workspace = Path(sys.argv[2])
source_hld = sys.argv[3]

report = json.loads(report_path.read_text(encoding="utf-8"))
existing = int(report.get("existing_hldspec_section_count", 0) or 0)
suggestions = report.get("suggested_hld_sections", [])
candidate_count = len(suggestions) if isinstance(suggestions, list) else 0
large_sections = [
    item for item in suggestions
    if isinstance(item, dict) and int(item.get("line_count", 0) or 0) >= 400
]

status = "hldspec_ready" if existing > 0 else "needs_conversion"

(workspace / "hld_readiness.json").write_text(
    json.dumps(
        {
            "status": status,
            "source_hld": source_hld,
            "format_report_json": str(report_path),
            "format_report_md": str(report_path.with_name("hld_format_report.md")),
            "existing_hldspec_section_count": existing,
            "candidate_major_section_count": candidate_count,
            "large_candidate_section_count": len(large_sections),
        },
        indent=2,
        sort_keys=True,
    ),
    encoding="utf-8",
)

(workspace / "hld_readiness.env").write_text(
    "\n".join(
        [
            f"STATUS={status}",
            f"EXISTING_HLDSPEC_SECTIONS={existing}",
            f"CANDIDATE_MAJOR_SECTIONS={candidate_count}",
            f"LARGE_CANDIDATE_SECTIONS={len(large_sections)}",
            f"REPORT_JSON={report_path}",
            f"REPORT_MD={report_path.with_name('hld_format_report.md')}",
        ]
    )
    + "\n",
    encoding="utf-8",
)

if status == "needs_conversion":
    prompt = f"""# HLD Conversion Prompt

made by AI

The input HLD is not yet in HLDspec format.

Detected:

- existing HLDspec sections: {existing}
- candidate major sections: {candidate_count}
- large candidate sections: {len(large_sections)}

Use the format report:

```text
{report_path.with_name('hld_format_report.md')}
{report_path}
```

Task:

Convert:

```text
{workspace / 'HLD.raw.md'}
```

into:

```text
{workspace / 'HLD.md'}
```

Rules:

- Preserve original design content.
- Context budget rules:
  - Do not paste the whole HLD into agent context.
  - Use local tools such as `grep`, `rg`, `sed -n`, `awk`, and `wc` for bounded inspection.
  - Convert in bounded batches of 3-5 major sections.
  - For very large candidate sections, inspect internal headings first and explain whether a split is needed.
  - Before each batch, state what sections you will edit and why.
  - After each batch, report changed sections, metadata chosen, refs added, uncertain fields, and a concise diff summary.
  - Let the human steer or stop before the next batch when interpretation is involved.
- Create stable major HLD sections: `## HLD-001 - Title`, `## HLD-002 - Title`, etc.
- Add required metadata under each major section:
  - `HLD-ID`
  - `HLD-ROLE`
  - `HLD-STATUS`
  - `HLD-RISK`
  - `HLD-SPECS`
  - `HLD-RESOURCES`
  - `HLD-VERIFY`
- Use `HLD-SPECS: TBD` unless a mapping is certain.
- Use `HLD-RESOURCES: TBD` unless resources/interfaces/contracts are explicit.
- Add `DEPENDS REF HLD-xxx`, `REF HLD-xxx`, or `CONFLICTS_WITH REF HLD-xxx` only when supported by the text.
- Do not create specs.
- Do not create `.specify/memory/constitution.md`.
- Do not generate implementation files.
- Do not invent architecture decisions.
- Split very large candidate sections only when they contain several independent design responsibilities.

After conversion, run:

```bash
bash scripts/first_run_readonly.sh "{workspace / 'HLD.md'}" "{workspace / 'firstrun'}" --force
```
"""
    (workspace / "HLD_CONVERSION_PROMPT.md").write_text(prompt, encoding="utf-8")
PY

# shellcheck disable=SC1090
. "$WORKSPACE/hld_readiness.env"

echo "HLD readiness: $STATUS"
echo "- existing HLDspec sections: $EXISTING_HLDSPEC_SECTIONS"
echo "- candidate major sections: $CANDIDATE_MAJOR_SECTIONS"
echo "- large candidate sections: $LARGE_CANDIDATE_SECTIONS"

if [ "$STATUS" = "needs_conversion" ]; then
  echo
  echo "Input HLD is not ready for HLD map / Spec Build Plan."
  echo "Open these files:"
  echo "- $REPORT_MD"
  echo "- $REPORT_JSON"
  echo "- $WORKSPACE/HLD_CONVERSION_PROMPT.md"
  echo
  echo "Convert $WORKSPACE/HLD.md to HLDspec format, then rerun:"
  echo "bash scripts/first_run_readonly.sh \"$WORKSPACE/HLD.md\" \"$WORKSPACE/firstrun\" --force"
  exit 2
fi

python3 "$ROOT/hld_spec_sync.py" --workspace "$WORKSPACE" --hld HLD.md --hld-map-only
python3 "$ROOT/hld_spec_sync.py" --workspace "$WORKSPACE" --hld HLD.md --use-hld-map --plan-specs
python3 "$ROOT/scripts/review_spec_build_plan.py" "$WORKSPACE/.specify/sync/spec_build_plan.json"

if [ -e "$WORKSPACE/.specify/memory/constitution.md" ]; then
  echo "ERROR: read-only first run created target constitution unexpectedly" >&2
  exit 1
fi

if find "$WORKSPACE/specs" -name spec.md -print -quit 2>/dev/null | grep -q .; then
  echo "ERROR: read-only first run created specs unexpectedly" >&2
  exit 1
fi

echo
echo "First run complete."
echo
echo "Open these files:"
echo "- $WORKSPACE/logs/hld_spec_sync/*/hld_format_report.md"
echo "- $WORKSPACE/.specify/sync/hld_index.md"
echo "- $WORKSPACE/.specify/sync/spec_build_plan.md"
echo "- $WORKSPACE/.specify/sync/spec_build_plan_review.md"
echo
echo "Next:"
echo "1. Read spec_build_plan_review.md."
echo "2. Resolve flagged specs by editing the working HLD.md or HLD-SPECS mapping."
echo "3. Re-run this script with the edited HLD."
echo
