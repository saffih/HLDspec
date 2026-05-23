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
  hldspec_agent_start.sh <source-HLD.md> [--workspace /path/to/workspace] [--force] [--print-context]

User-facing meaning:
  HLDspec /absolute/path/to/HLD.md

Generates a minimal agent trigger plus internal context files.
Default output is intentionally short.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

SOURCE_HLD="$1"
shift

WORKSPACE=""
FORCE=0
PRINT_CONTEXT=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --workspace)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
        echo "ERROR: --workspace requires a path" >&2
        exit 2
      fi
      WORKSPACE="$2"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    --print-context)
      PRINT_CONTEXT=1
      shift
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

ARGS=("$ROOT/scripts/build_hldspec_agent_start_prompt.py" "$SOURCE_HLD" --repo "$ROOT")
if [ -n "$WORKSPACE" ]; then
  ARGS+=(--workspace "$WORKSPACE")
fi
if [ "$FORCE" = "1" ]; then
  ARGS+=(--force)
fi
if [ "$PRINT_CONTEXT" = "1" ]; then
  ARGS+=(--print-context)
fi

run_python "${ARGS[@]}"
