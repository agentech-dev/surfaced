#!/usr/bin/env bash
# Run prompts filtered by tag (for cron scheduling)
# Usage: ./scripts/surfaced-runner.sh <tag>
# Example cron entries:
#   0 6 * * *   cd /path/to/surfaced && ./scripts/surfaced-runner.sh daily
#   0 6 * * 1   cd /path/to/surfaced && ./scripts/surfaced-runner.sh weekly
#   0 6 1 * *   cd /path/to/surfaced && ./scripts/surfaced-runner.sh monthly

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Load API keys
if [ -f .env ]; then
    set -a
    source .env
    set +a
fi

TAG="${1:?Usage: surfaced-runner.sh <tag>}"
LOGDIR="$(dirname "$0")/../logs"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/run-${TAG}-$(date +%Y%m%d-%H%M%S).log"

echo "Starting run with tag: $TAG at $(date)" | tee "$LOGFILE"
uv run surfaced run --tag "$TAG" 2>&1 | tee -a "$LOGFILE"
echo "Finished at $(date)" | tee -a "$LOGFILE"
