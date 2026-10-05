#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/services/private-graphql-proxy/docker-compose.smoke.yml"

export PRIMUS_BACKEND_MODE="${PRIMUS_BACKEND_MODE:-local}"
export PRIMUS_PROXY_UPSTREAM_DISABLED="${PRIMUS_PROXY_UPSTREAM_DISABLED:-true}"
export PRIMUS_PROXY_API_KEY="${PRIMUS_PROXY_API_KEY:-local-smoke-key}"
export PRIMUS_PROXY_AUTH_MODE="${PRIMUS_PROXY_AUTH_MODE:-}"
export AMPLIFY_STORAGE_REPORTBLOCKDETAILS_BUCKET_NAME="${AMPLIFY_STORAGE_REPORTBLOCKDETAILS_BUCKET_NAME:-primus-local-report-block-details}"
export EMBEDDING_CACHE_BUCKET="${EMBEDDING_CACHE_BUCKET:-primus-embeddings}"
export PRIMUS_OBJECT_STORE_ENDPOINT="${PRIMUS_OBJECT_STORE_ENDPOINT:-http://localhost:19000}"
export PRIMUS_OBJECT_STORE_REGION="${PRIMUS_OBJECT_STORE_REGION:-us-east-1}"
export PRIMUS_OBJECT_STORE_FORCE_PATH_STYLE="${PRIMUS_OBJECT_STORE_FORCE_PATH_STYLE:-true}"
export PRIMUS_OBJECT_STORE_ACCESS_KEY_ID="${PRIMUS_OBJECT_STORE_ACCESS_KEY_ID:-primus-local}"
export PRIMUS_OBJECT_STORE_SECRET_ACCESS_KEY="${PRIMUS_OBJECT_STORE_SECRET_ACCESS_KEY:-primus-local-secret}"
export PRIMUS_VECTOR_STORE_PROVIDER="${PRIMUS_VECTOR_STORE_PROVIDER:-qdrant}"
export PRIMUS_VECTOR_STORE_URL="${PRIMUS_VECTOR_STORE_URL:-http://localhost:19002}"
export PRIMUS_VECTOR_STORE_COLLECTION="${PRIMUS_VECTOR_STORE_COLLECTION:-topic-memory-local}"

cd "$ROOT_DIR"
docker compose -f "$COMPOSE_FILE" up -d --build postgres minio minio-init qdrant proxy

docker compose -f "$COMPOSE_FILE" run --rm \
  -e PRIMUS_API_URL=http://proxy:8000/graphql \
  -e PRIMUS_API_KEY="$PRIMUS_PROXY_API_KEY" \
  smoke-tests \
  sh -c "pip install --no-cache-dir -r services/private-graphql-proxy/requirements.txt >/dev/null && python services/private-graphql-proxy/scripts/seed_local_demo.py"

cd "$ROOT_DIR/dashboard"
export PRIMUS_API_URL="${PRIMUS_API_URL:-http://localhost:18080/graphql}"
export PRIMUS_API_KEY="${PRIMUS_API_KEY:-$PRIMUS_PROXY_API_KEY}"
export PRIMUS_ACCOUNT_KEY="${PRIMUS_ACCOUNT_KEY:-local-demo}"
export NEXT_PUBLIC_PRIMUS_BACKEND=local
export NEXT_PUBLIC_PRIMUS_API_URL="$PRIMUS_API_URL"
export NEXT_PUBLIC_PRIMUS_API_KEY="$PRIMUS_API_KEY"
export NEXT_PUBLIC_PRIMUS_ACCOUNT_KEY="$PRIMUS_ACCOUNT_KEY"
export NEXT_PUBLIC_PRIMUS_API_REGION="${NEXT_PUBLIC_PRIMUS_API_REGION:-local}"

npm run dev:web
