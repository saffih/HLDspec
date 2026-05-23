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
  hldspec_smoke.sh <source-HLD.md> [workspace] [--force] [--approve-dry-run] [--phase specify]

Runs an end-to-end read-only smoke:
1. prework
2. status
3. alignment review
4. optional explicit prework approval for dry-run
5. guarded SpecKit proxy dry-run
6. readiness review

Does not modify source HLD.
Does not invoke real SpecKit.
Does not implement.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ] || [ "$#" -lt 1 ]; then
  usage
  exit 0
fi

SOURCE_HLD="$1"
shift
WORKSPACE="${1:-/tmp/hldspec-smoke}"
if [ "${1:-}" != "" ] && [[ "${1:-}" != --* ]]; then
  shift
fi

FORCE=""
APPROVE_DRY_RUN=0
PHASE="specify"

while [ "$#" -gt 0 ]; do
  case "$1" in
    --force)
      FORCE="--force"
      shift
      ;;
    --approve-dry-run)
      APPROVE_DRY_RUN=1
      shift
      ;;
    --phase)
      PHASE="${2:-}"
      shift 2
      ;;
    *)
      echo "ERROR: unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ ! -f "$SOURCE_HLD" ]; then
  echo "ERROR: source HLD not found: $SOURCE_HLD" >&2
  exit 1
fi

SOURCE_HASH_BEFORE="$(shasum -a 256 "$SOURCE_HLD" | awk '{print $1}')"

echo "HLDspec smoke"
echo "- source HLD: $SOURCE_HLD"
echo "- workspace: $WORKSPACE"
echo "- phase: $PHASE"
echo

bash "$ROOT/scripts/hldspec_prework.sh" "$SOURCE_HLD" "$WORKSPACE" $FORCE

echo
echo "Status after prework:"
bash "$ROOT/scripts/hldspec_status.sh" "$WORKSPACE" "$SOURCE_HLD"

echo
echo "Product alignment review:"
"${PYTHON_RUN[@]}" "$ROOT/scripts/run_hldspec_alignment_review.py" --repo "$ROOT" --out-dir "$ROOT/docs" --print-findings

if [ "$APPROVE_DRY_RUN" = "1" ]; then
  echo
  echo "Recording explicit prework approval for dry-run smoke only."
  "${PYTHON_RUN[@]}" "$ROOT/scripts/approve_hldspec_prework.py" "$WORKSPACE" \
    --decision APPROVE_PLAN \
    --notes "Approved by hldspec_smoke.sh for guarded dry-run smoke."
fi

echo
echo "SpecKit proxy dry-run:"
set +e
bash "$ROOT/scripts/hldspec_speckit_proxy.sh" "$WORKSPACE" --phase "$PHASE" --dry-run
PROXY_RC=$?
set -e

SOURCE_HASH_AFTER="$(shasum -a 256 "$SOURCE_HLD" | awk '{print $1}')"

echo
echo "Readiness review:"
"${PYTHON_RUN[@]}" "$ROOT/scripts/run_hldspec_readiness_review.py" "$WORKSPACE" \
  --source-hld "$SOURCE_HLD" \
  --expected-source-sha256 "$SOURCE_HASH_BEFORE"

if [ "$SOURCE_HASH_BEFORE" != "$SOURCE_HASH_AFTER" ]; then
  echo "ERROR: source HLD changed during smoke." >&2
  exit 1
fi

echo
echo "Smoke complete."
echo "- source unchanged: true"
echo "- proxy dry-run exit code: $PROXY_RC"
echo "- readiness: $WORKSPACE/.specify/sync/hldspec_readiness_review.md"

exit 0
