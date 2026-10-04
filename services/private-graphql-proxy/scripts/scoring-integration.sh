#!/usr/bin/env sh
set -eu

if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  cat <<'EOF'
Run the private GraphQL proxy scoring integration harness.

Required environment:
  PRIMUS_PROXY_UPSTREAM_API_URL
  PRIMUS_PROXY_UPSTREAM_API_KEY
  PRIMUS_ACCOUNT_KEY
  PRIMUS_PROXY_SCORING_SCORECARD
  PRIMUS_PROXY_SCORING_SCORE

Optional:
  PRIMUS_PROXY_SCORING_DATASET=apptek-com/apptek_callcenter_dialogues
  PRIMUS_PROXY_SCORING_SPLIT=test
  PRIMUS_PROXY_SCORING_FIXTURE_LIMIT=3
EOF
  exit 0
fi

cd "$(dirname "$0")/.."
docker compose -f docker-compose.smoke.yml --profile scoring-integration up --build --abort-on-container-exit --exit-code-from scoring-integration scoring-integration
