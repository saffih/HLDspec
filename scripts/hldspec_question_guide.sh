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
  hldspec_question_guide.sh <workspace> [--queue /path/to/queue.json]

Builds and prints a read-only guide for the current HLDspec checkpoint questions.

It does not:
- edit files
- answer questions
- convert HLDs
- invoke SpecKit
- promote artifacts
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

WORKSPACE="$1"
shift

QUEUE_ARGS=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --queue)
      QUEUE_ARGS+=(--queue "${2:-}")
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

"${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_question_guide.py" "$WORKSPACE" "${QUEUE_ARGS[@]}"

STATE_SYNC="$WORKSPACE/.specify/sync"
FIRSTRUN_SYNC="$WORKSPACE/firstrun/.specify/sync"
if [ -f "$STATE_SYNC/hldspec_question_guide.md" ]; then
  cat "$STATE_SYNC/hldspec_question_guide.md"
elif [ -f "$FIRSTRUN_SYNC/hldspec_question_guide.md" ]; then
  cat "$FIRSTRUN_SYNC/hldspec_question_guide.md"
fi
