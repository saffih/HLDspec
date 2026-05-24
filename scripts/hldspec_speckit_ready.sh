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
  hldspec_speckit_ready.sh <workspace> [--hld /path/to/HLD.md] [--source-project /path/to/project]

Builds pre-SpecKit readiness artifacts:
- architecture analysis
- constitution context pack
- dependency-aware spec list (scans source-project/specs/ for existing IDs)
- readiness review
- orchestrator instruction files (CLAUDE.md, AGENTS.md, .devin/)

Options:
  --hld PATH             Source HLD file (used for architecture analysis)
  --source-project PATH  Target project root — scans its specs/ for existing spec IDs
                         to avoid numbering conflicts. Defaults to dirname(--hld) if
                         --hld is provided.

It does not invoke SpecKit, create final specs, or implement.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

WORKSPACE="$1"
shift

HLD_PATH=""
SOURCE_PROJECT=""

while [ "$#" -gt 0 ]; do
  case "$1" in
    --hld)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
        echo "ERROR: --hld requires a path" >&2
        exit 2
      fi
      HLD_PATH="$2"
      shift 2
      ;;
    --source-project)
      if [ "$#" -lt 2 ] || [ -z "${2:-}" ]; then
        echo "ERROR: --source-project requires a path" >&2
        exit 2
      fi
      SOURCE_PROJECT="$2"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

# Derive source project from HLD path if not explicitly set
if [ -z "$SOURCE_PROJECT" ] && [ -n "$HLD_PATH" ]; then
  SOURCE_PROJECT="$(dirname "$(realpath "$HLD_PATH")")"
fi

if [ -n "$HLD_PATH" ]; then
  run_python "$ROOT/scripts/build_hldspec_architecture_analysis.py" "$WORKSPACE" --hld "$HLD_PATH"
else
  run_python "$ROOT/scripts/build_hldspec_architecture_analysis.py" "$WORKSPACE"
fi
run_python "$ROOT/scripts/build_speckit_constitution_context.py" "$WORKSPACE"

if [ -n "$SOURCE_PROJECT" ]; then
  run_python "$ROOT/scripts/build_hldspec_speckit_spec_list.py" "$WORKSPACE" --source-project "$SOURCE_PROJECT"
else
  run_python "$ROOT/scripts/build_hldspec_speckit_spec_list.py" "$WORKSPACE"
fi

run_python "$ROOT/scripts/build_hldspec_architecture_findings_disposition.py" "$WORKSPACE"
run_python "$ROOT/scripts/run_hldspec_speckit_readiness.py" "$WORKSPACE"

# Install orchestrator instruction files (idempotent — skips existing non-stub files)
echo ""
echo "Installing orchestrator instructions..."
bash "$ROOT/scripts/install_orchestrator_instructions.sh" --workspace "$WORKSPACE"
