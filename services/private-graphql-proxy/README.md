# Private GraphQL Proxy Prototype

This service is a standalone prototype for keeping Primus private data-plane
models out of AWS while preserving the existing GraphQL client contract.

The proxy exposes:

- `POST /graphql`
- `GET /healthz`
- `GET /readyz`

Private models are authoritative in PostgreSQL:

- `Item`
- `ScoreResult`
- `FeedbackItem`
- `Identifier`

Read-only control-plane queries are forwarded to AppSync and cached in
PostgreSQL. The default cache freshness TTL is 15 minutes and the stale-serving
window is 24 hours.

## Configuration

Environment variables remain supported and override YAML when both are set.
For local Virtuus eval runs, prefer `.primus/config.yaml` in the project
directory (or `~/.primus/config.yaml`) so `uvicorn proxy.app` picks up settings
without exporting a dozen variables:

```yaml
primus:
  store: virtuus
  backend_mode: local
  data_dir: .primus/data
  proxy:
    auth_mode: trusted_open
    upstream_disabled: true
```

Postgres remains the default when no YAML is present and no `PRIMUS_STORE` is
set. Existing environment variables still override YAML values.

### Environment variables (Postgres default)

```bash
export PRIMUS_PROXY_DATABASE_URL=postgresql://primus:primus@localhost:55432/primus_proxy
export PRIMUS_PROXY_API_KEY=local-smoke-key
export PRIMUS_PROXY_UPSTREAM_API_URL=https://example.appsync-api.us-east-1.amazonaws.com/graphql
# Set PRIMUS_PROXY_UPSTREAM_API_KEY in your shell or secret manager.
export PRIMUS_PROXY_CACHE_TTL_SECONDS=900
export PRIMUS_PROXY_CACHE_STALE_SECONDS=86400
```

Scoring-side clients should point `PRIMUS_API_URL` at the proxy endpoint and
use `PRIMUS_API_KEY` for the proxy API key.

## Smoke Tests

The smoke harness starts PostgreSQL, the proxy, and a pytest runner:

```bash
services/private-graphql-proxy/scripts/smoke.sh
```

Real AppSync smoke coverage is read-only and requires fixture IDs:

```bash
export PRIMUS_PROXY_UPSTREAM_API_URL=...
# Set PRIMUS_PROXY_UPSTREAM_API_KEY in your shell or secret manager.
export PRIMUS_PROXY_SMOKE_ACCOUNT_ID=...
export PRIMUS_PROXY_SMOKE_SCORECARD_ID=...
export PRIMUS_PROXY_SMOKE_SCORE_ID=...
export PRIMUS_PROXY_SMOKE_SCORE_VERSION_ID=...
export PRIMUS_PROXY_SMOKE_EVALUATION_ID=...
```

Private model smoke writes use generated test IDs and only write to local
PostgreSQL through the proxy.

## Scoring Integration

The scoring integration harness starts PostgreSQL, the proxy, and a full Primus
dependency runner. It seeds public Hugging Face call-center transcript examples
as local private `Item` and `Identifier` rows, then runs the normal Primus
prediction CLI through the proxy.

Required control-plane and score configuration values:

```bash
export PRIMUS_PROXY_UPSTREAM_API_URL="$PRIMUS_API_URL"
# Set PRIMUS_PROXY_UPSTREAM_API_KEY from your shell or secret manager.
export PRIMUS_ACCOUNT_KEY=...
export PRIMUS_PROXY_SCORING_SCORECARD=...
export PRIMUS_PROXY_SCORING_SCORE=...
```

Optional fixture controls:

```bash
export PRIMUS_PROXY_SCORING_DATASET=apptek-com/apptek_callcenter_dialogues
export PRIMUS_PROXY_SCORING_SPLIT=test
export PRIMUS_PROXY_SCORING_FIXTURE_LIMIT=3
```

Run the integration harness:

```bash
services/private-graphql-proxy/scripts/scoring-integration.sh
```

The runner sets `PRIMUS_API_URL` to the local proxy and clears the
`NEXT_PUBLIC_PRIMUS_API_*` variables so the Primus client cannot bypass the
proxy. The test uses AppSync for read-only control-plane data and writes fixture
private rows only to local PostgreSQL.
