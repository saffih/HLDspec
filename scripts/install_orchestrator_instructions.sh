#!/usr/bin/env bash
# install_orchestrator_instructions.sh
# Install orchestrator instruction files into an HLDspec workspace.
#
# Usage:
#   install_orchestrator_instructions.sh --workspace /path/to/workspace [--orchestrators claude,codex,devin]
#
# Installs:
#   all runners → AGENTS.md
#   claude      → CLAUDE.md shim that points back to AGENTS.md
#   codex       → no extra file; Codex reads AGENTS.md directly
#   devin       → .devin/instructions.md shim that points back to AGENTS.md
#
# Uses HLDspec repo location (auto-detected from script location).

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEMPLATES="$REPO/templates/orchestrator"

usage() {
  cat <<'EOF'
Usage:
  install_orchestrator_instructions.sh --workspace /path/to/workspace [--orchestrators claude,codex,devin]

Options:
  --workspace PATH      Target HLDspec workspace (required)
  --orchestrators LIST  Comma-separated shim list: claude,codex,devin (default: all)
                        AGENTS.md is always installed as the universal contract.
  --force               Overwrite existing files
  -h, --help            Show this help

Examples:
  install_orchestrator_instructions.sh --workspace /tmp/my-workspace
  install_orchestrator_instructions.sh --workspace /tmp/my-workspace --orchestrators claude,codex
EOF
}

WORKSPACE=""
ORCHESTRATORS="claude,codex,devin"
FORCE=0

while [ "$#" -gt 0 ]; do
  case "$1" in
    --workspace)
      WORKSPACE="${2:-}"
      shift 2
      ;;
    --orchestrators)
      ORCHESTRATORS="${2:-}"
      shift 2
      ;;
    --force)
      FORCE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "$WORKSPACE" ]; then
  echo "ERROR: --workspace is required" >&2
  usage >&2
  exit 2
fi

if [ ! -d "$WORKSPACE" ]; then
  echo "ERROR: workspace directory does not exist: $WORKSPACE" >&2
  exit 2
fi

WORKSPACE="$(cd "$WORKSPACE" && pwd)"

# Replace template placeholders in a file
render_template() {
  local src="$1"
  local dest="$2"
  sed \
    -e "s|{{WORKSPACE}}|$WORKSPACE|g" \
    -e "s|{{HLDSPEC_REPO}}|$REPO|g" \
    "$src" > "$dest"
  echo "  wrote: $dest"
}

install_one() {
  local name="$1"
  local src="$2"
  local dest="$3"
  local dest_dir
  dest_dir="$(dirname "$dest")"

  if [ ! -f "$src" ]; then
    echo "  SKIP: template not found: $src"
    return
  fi

  mkdir -p "$dest_dir"

  if [ -f "$dest" ] && [ "$FORCE" = "0" ]; then
    # Check if it's a stub (SpecKit default) — safe to overwrite
    local content
    content="$(cat "$dest")"
    if echo "$content" | grep -q "SPECKIT START" && [ "$(wc -l < "$dest")" -le 10 ]; then
      echo "  overwriting SpecKit stub: $dest"
    else
      echo "  SKIP (exists, use --force to overwrite): $dest"
      return
    fi
  fi

  render_template "$src" "$dest"
}

echo "Installing orchestrator instructions into: $WORKSPACE"
echo "HLDspec repo: $REPO"
echo "Universal contract: AGENTS.md"
echo "Compatibility shims: $ORCHESTRATORS"
echo ""

echo "[universal] AGENTS.md"
install_one universal \
  "$TEMPLATES/AGENTS.md" \
  "$WORKSPACE/AGENTS.md"
echo ""

IFS=',' read -ra ORCS <<< "$ORCHESTRATORS"
for orc in "${ORCS[@]}"; do
  orc="${orc// /}"  # trim spaces
  case "$orc" in
    claude)
      echo "[claude shim] CLAUDE.md"
      install_one claude \
        "$TEMPLATES/CLAUDE.md" \
        "$WORKSPACE/CLAUDE.md"
      ;;
    codex)
      echo "[codex] uses AGENTS.md directly"
      ;;
    devin)
      echo "[devin shim] .devin/instructions.md"
      install_one devin \
        "$TEMPLATES/devin-instructions.md" \
        "$WORKSPACE/.devin/instructions.md"
      ;;
    *)
      echo "  WARN: unknown orchestrator '$orc' (supported: claude, codex, devin)"
      ;;
  esac
done

echo ""
echo "Done. Review AGENTS.md and any installed shim files, then commit them to your workspace."
