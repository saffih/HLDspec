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
  hldspec_interview.sh [workspace] [source-HLD.md] [--queue path] [--answer Q-001=OPTION] [--note Q-001=TEXT] [--rerun]

Examples:
  scripts/hldspec_interview.sh .hldspec-first-run --answer Q-001=SPLIT_AS_PROPOSED
  scripts/hldspec_interview.sh .hldspec-first-run HLD.md --answer SPQ-001=KEEP_AS_ONE_WITH_REASON --rerun

Behavior:
  - discovers the active HLDspec checkpoint queue when --queue is omitted
  - validates question IDs and allowed options
  - writes answers into the controlling JSON queue
  - regenerates queue markdown
  - writes source-HLD update artifacts for conversion decisions
  - optionally reruns hldspec_run.sh after valid answers
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

WORKSPACE="${1:-$PWD/.hldspec-first-run}"
if [ "${1:-}" != "" ] && [[ "${1:-}" != --* ]]; then
  shift
fi

SOURCE_HLD=""
if [ "${1:-}" != "" ] && [[ "${1:-}" != --* ]]; then
  SOURCE_HLD="$1"
  shift
fi

QUEUE=""
RERUN=0
ARGS=()

while [ "$#" -gt 0 ]; do
  case "$1" in
    --queue)
      QUEUE="${2:-}"
      shift 2
      ;;
    --answer)
      ARGS+=(--answer "${2:-}")
      shift 2
      ;;
    --note)
      ARGS+=(--note "${2:-}")
      shift 2
      ;;
    --rerun)
      RERUN=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ ! -d "$WORKSPACE" ]; then
  echo "ERROR: workspace not found: $WORKSPACE" >&2
  exit 1
fi

"${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_state.py" "$WORKSPACE" --source-hld "$SOURCE_HLD" >/dev/null

if [ "${#ARGS[@]}" -eq 0 ]; then
  echo "HLDspec interview"
  echo "- workspace: $WORKSPACE"
  echo "- state: $WORKSPACE/.specify/sync/hldspec_state.md"
  echo
  cat "$WORKSPACE/.specify/sync/hldspec_state.md"
  echo
  echo "Provide answers with --answer QUESTION_ID=OPTION."
  exit 0
fi

CMD=("${PYTHON_RUN[@]}" "$ROOT/scripts/apply_hldspec_queue_answers.py" "$WORKSPACE" --source-hld "$SOURCE_HLD")
if [ -n "$QUEUE" ]; then
  CMD+=(--queue "$QUEUE")
fi
CMD+=("${ARGS[@]}")
"${CMD[@]}"

"${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_state.py" "$WORKSPACE" --source-hld "$SOURCE_HLD" >/dev/null

echo
echo "Updated state: $WORKSPACE/.specify/sync/hldspec_state.md"

if [ "$RERUN" = "1" ]; then
  if [ -z "$SOURCE_HLD" ]; then
    echo "ERROR: --rerun requires source-HLD.md argument" >&2
    exit 2
  fi
  exec bash "$ROOT/scripts/hldspec_run.sh" "$SOURCE_HLD" "$WORKSPACE"
fi
