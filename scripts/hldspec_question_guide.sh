#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

run_python() {
  if command -v uv >/dev/null 2>&1; then
    export UV_CACHE_DIR="${UV_CACHE_DIR:-$PWD/.hldspec-uv-cache}"
    uv run python "$@"
  else
    python3 "$@"
  fi
}

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

QUEUE_PATH=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --queue)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
        echo "ERROR: --queue requires a path" >&2
        exit 2
      fi
      QUEUE_PATH="$2"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -n "$QUEUE_PATH" ]; then
  run_python "$ROOT/scripts/build_hldspec_question_guide.py" "$WORKSPACE" --queue "$QUEUE_PATH"
else
  run_python "$ROOT/scripts/build_hldspec_question_guide.py" "$WORKSPACE"
fi

STATE_SYNC="$WORKSPACE/.specify/sync"
FIRSTRUN_SYNC="$WORKSPACE/firstrun/.specify/sync"
if [ -f "$STATE_SYNC/hldspec_question_guide.md" ]; then
  cat "$STATE_SYNC/hldspec_question_guide.md"
elif [ -f "$FIRSTRUN_SYNC/hldspec_question_guide.md" ]; then
  cat "$FIRSTRUN_SYNC/hldspec_question_guide.md"
fi
