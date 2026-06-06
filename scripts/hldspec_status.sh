#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if command -v uv >/dev/null 2>&1; then
  export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.hldspec-uv-cache}"
  PYTHON_RUN=(uv run python)
else
  PYTHON_RUN=(python3)
fi

usage() {
  cat <<'EOF'
Usage:
  hldspec_status.sh [workspace] [source-HLD.md]

Default workspace:
  $PWD/.hldspec-first-run

Prints current HLDspec stage, checkpoint, controlling artifacts, and next allowed actions.
Does not modify source HLD or invoke SpecKit.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

WORKSPACE="${1:-$PWD/.hldspec-first-run}"
SOURCE_HLD="${2:-}"

"${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_state.py" "$WORKSPACE" --source-hld "$SOURCE_HLD" >/dev/null

if [ -f "$WORKSPACE/targetHLD/HLD.md" ] || [ -f "$WORKSPACE/.hldspec/agent_session.json" ] || [ -f "$WORKSPACE/.hldspec/source_package/session_plan.json" ]; then
  STATE_MD="$WORKSPACE/.hldspec/sync/hldspec_state.md"
  STATE_JSON="$WORKSPACE/.hldspec/sync/hldspec_state.json"
else
  STATE_MD="$WORKSPACE/.specify/sync/hldspec_state.md"
  STATE_JSON="$WORKSPACE/.specify/sync/hldspec_state.json"
fi

if [ ! -f "$STATE_MD" ]; then
  echo "ERROR: state report was not generated: $STATE_MD" >&2
  exit 1
fi

echo "HLDspec status"
echo "- workspace: $WORKSPACE"
echo "- state json: $STATE_JSON"
echo "- state report: $STATE_MD"
echo
cat "$STATE_MD"

echo
echo "Checkpoint question guide:"
bash "$ROOT/scripts/hldspec_question_guide.sh" "$WORKSPACE" || true
