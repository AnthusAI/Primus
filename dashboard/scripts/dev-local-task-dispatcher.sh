#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DASHBOARD_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
REPO_ROOT="$(cd "$DASHBOARD_DIR/.." && pwd)"

cd "$DASHBOARD_DIR"

# Load provider credentials such as OPENAI_API_KEY, then explicitly select the
# isolated local control plane. Never use load-dev-env.sh here: it resolves the
# configured remote control plane for ordinary dashboard development.
set -a
[ -f "$REPO_ROOT/.env" ] && . "$REPO_ROOT/.env"
[ -f "$DASHBOARD_DIR/.env.local" ] && . "$DASHBOARD_DIR/.env.local"
set +a

export PRIMUS_API_URL="${PRIMUS_LOCAL_API_URL:-http://localhost:18080/graphql}"
export PRIMUS_API_KEY="${PRIMUS_LOCAL_API_KEY:-local-smoke-key}"
export PRIMUS_ACCOUNT_KEY="${PRIMUS_LOCAL_ACCOUNT_KEY:-local-demo}"
export PRIMUS_GRAPHQL_AUTH_MODE="api_key"
export PRIMUS_DISPATCH_MODE="local"
export PRIMUS_FETCH_SCHEMA_FROM_TRANSPORT="false"

ready_url="${PRIMUS_API_URL%/graphql}/readyz"
if ! curl --fail --silent --show-error "$ready_url" >/dev/null; then
  echo "Local control plane is unavailable at $ready_url. Start it with: npm run dev:local-control-plane" >&2
  exit 1
fi

PYTHONPATH="$REPO_ROOT${PYTHONPATH:+:$PYTHONPATH}" \
  exec poetry run python -m primus.cli command dispatcher --interval 0.5 --loglevel INFO "$@"
