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
  cat <<'HELP_EOF'
Usage:
  hldspec_speckit_proxy.sh [workspace] [--phase specify|clarify|plan|tasks|analyze|constitution] [--dry-run]

Default workspace:
  $PWD/.hldspec-first-run

This command only builds a guarded one-phase dry run.
It refuses implementation and refuses proxy work until SpecKit prework is explicitly approved.
HELP_EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi

WORKSPACE="${1:-$PWD/.hldspec-first-run}"
if [ "${1:-}" != "" ] && [[ "${1:-}" != --* ]]; then
  shift
fi

PHASE="specify"
DRY_RUN=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --phase)
      PHASE="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --execute)
      echo "ERROR: execution mode is not implemented. This wrapper is dry-run only." >&2
      exit 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ "$DRY_RUN" != "1" ]; then
  echo "ERROR: only --dry-run mode is allowed." >&2
  exit 2
fi

if [ ! -d "$WORKSPACE" ]; then
  echo "ERROR: workspace not found: $WORKSPACE" >&2
  exit 1
fi

"${PYTHON_RUN[@]}" "$ROOT/scripts/build_hldspec_state.py" "$WORKSPACE" >/dev/null || true
"${PYTHON_RUN[@]}" "$ROOT/scripts/build_speckit_proxy_dry_run.py" "$WORKSPACE" --phase "$PHASE"
