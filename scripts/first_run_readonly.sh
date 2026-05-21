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
