#!/usr/bin/env bash
# Start n8n locally for the Signal-to-Pipeline project (decision #43).
# n8n needs Node 20/22/24 — Node 25 is not supported. Uses Homebrew's node@22 if present.
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
for p in /opt/homebrew/opt/node@22/bin /usr/local/opt/node@22/bin; do
  [ -x "$p/node" ] && export PATH="$p:$PATH" && break
done
NODE_MAJOR="$(node -v | sed 's/v\([0-9]*\).*/\1/')"
case "$NODE_MAJOR" in
  20|22|24) ;;
  *) echo "Node $(node -v) is not supported by n8n. Install Node 22: brew install node@22"; exit 1 ;;
esac
export N8N_USER_FOLDER="$REPO/n8n"                         # data + credentials (git-ignored: n8n/.n8n/)
export N8N_RESTRICT_FILE_ACCESS_TO="$REPO/data/clay_exports" # n8n may only touch the export folder
export NODES_EXCLUDE="[]"                                    # re-enable Local File Trigger
echo "Node $(node -v) — starting n8n at http://localhost:5678"
exec npx --yes n8n
