#!/usr/bin/env bash
set -euo pipefail

cd /srv/app

if docker compose version >/dev/null 2>&1; then
  COMPOSE_MODE="plugin"
  echo "Docker Compose command: docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_MODE="standalone"
  echo "Docker Compose command: docker-compose"
else
  echo "ERROR: neither 'docker compose' nor 'docker-compose' is available on the production host." >&2
  exit 127
fi

restore_backend() {
  echo "=== ensure backend remains running ==="
  if [ "$COMPOSE_MODE" = "plugin" ]; then
    timeout --signal=TERM 2m docker compose up -d backend || true
    timeout --signal=TERM 30s docker compose ps backend || true
  else
    timeout --signal=TERM 2m docker-compose up -d backend || true
    timeout --signal=TERM 30s docker-compose ps backend || true
  fi
}
trap restore_backend EXIT

CITY_SLUG="${CITY_SLUG:-}"
LIMIT="${LIMIT:-50}"
APPLY_DISCOVERED="${APPLY_DISCOVERED:-true}"

CMD=(python scripts/discover_new_pois.py --limit "$LIMIT")
if [ -n "$CITY_SLUG" ]; then
  CMD+=(--city "$CITY_SLUG")
fi
if [ "$APPLY_DISCOVERED" = "true" ]; then
  CMD+=(--apply)
fi

echo "=== poi discovery ==="
echo "city=${CITY_SLUG:-all} limit=${LIMIT} apply=${APPLY_DISCOVERED}"

if [ "$COMPOSE_MODE" = "plugin" ]; then
  timeout --signal=TERM 10m docker compose run -T --rm --no-deps \
    -e DB_POOL_SIZE=1 \
    -e DB_MAX_OVERFLOW=0 \
    -e DB_POOL_TIMEOUT_SECONDS=10 \
    -e DB_STATEMENT_TIMEOUT_MS=30000 \
    backend "${CMD[@]}"
else
  timeout --signal=TERM 10m docker-compose run -T --rm --no-deps \
    -e DB_POOL_SIZE=1 \
    -e DB_MAX_OVERFLOW=0 \
    -e DB_POOL_TIMEOUT_SECONDS=10 \
    -e DB_STATEMENT_TIMEOUT_MS=30000 \
    backend "${CMD[@]}"
fi
