#!/usr/bin/env bash
# Run a campaign filtered by tag (for cron scheduling)
# Usage: ./scripts/run-campaign.sh <tag>
# Example cron entries:
#   0 6 * * *   cd /path/to/surfaced && ./scripts/run-campaign.sh daily
#   0 6 * * 1   cd /path/to/surfaced && ./scripts/run-campaign.sh weekly
#   0 6 1 * *   cd /path/to/surfaced && ./scripts/run-campaign.sh monthly

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

TAG="${1:?Usage: run-campaign.sh <tag>}"
LOGDIR="$(dirname "$0")/../logs"
mkdir -p "$LOGDIR"
LOGFILE="$LOGDIR/campaign-${TAG}-$(date +%Y%m%d-%H%M%S).log"

echo "Starting campaign with tag: $TAG at $(date)" | tee "$LOGFILE"
uv run surfaced run --tag "$TAG" 2>&1 | tee -a "$LOGFILE"
echo "Finished at $(date)" | tee -a "$LOGFILE"
