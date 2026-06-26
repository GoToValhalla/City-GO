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

POLICY_MODE="${POLICY_MODE:-shadow}"
CITY_SLUG="${CITY_SLUG:-}"
LIMIT="${LIMIT:-100}"
AUTO_PUBLISH_ENABLED="${AUTO_PUBLISH_ENABLED:-false}"
AUTO_PUBLISH_THRESHOLD="${AUTO_PUBLISH_THRESHOLD:-90}"

if [ "$POLICY_MODE" = "apply" ] && [ "$AUTO_PUBLISH_ENABLED" != "true" ]; then
  echo "ERROR: apply mode requires AUTO_PUBLISH_ENABLED=true. Refusing to publish by accident." >&2
  exit 2
fi

CMD=(python scripts/run_publication_policy.py --mode "$POLICY_MODE" --limit "$LIMIT" --auto-publish-threshold "$AUTO_PUBLISH_THRESHOLD")
if [ -n "$CITY_SLUG" ]; then
  CMD+=(--city "$CITY_SLUG")
fi
if [ "$AUTO_PUBLISH_ENABLED" = "true" ]; then
  CMD+=(--auto-publish-enabled)
fi

echo "=== publication policy ==="
echo "mode=${POLICY_MODE} city=${CITY_SLUG:-all} limit=${LIMIT} threshold=${AUTO_PUBLISH_THRESHOLD} auto_publish_enabled=${AUTO_PUBLISH_ENABLED}"

# Do not run policy through `docker compose exec backend`: the process shares the
# live backend container memory cgroup and can kill the public API with exit 137.
# A one-off container uses the same image and network, but isolates failures from
# the running backend service.
if [ "$COMPOSE_MODE" = "plugin" ]; then
  timeout --signal=TERM --kill-after=20s 10m docker compose run -T --rm --no-deps \
    -e DB_POOL_SIZE=1 \
    -e DB_MAX_OVERFLOW=0 \
    -e DB_POOL_TIMEOUT_SECONDS=10 \
    -e DB_STATEMENT_TIMEOUT_MS=30000 \
    backend "${CMD[@]}"
else
  timeout --signal=TERM --kill-after=20s 10m docker-compose run -T --rm --no-deps \
    -e DB_POOL_SIZE=1 \
    -e DB_MAX_OVERFLOW=0 \
    -e DB_POOL_TIMEOUT_SECONDS=10 \
    -e DB_STATEMENT_TIMEOUT_MS=30000 \
    backend "${CMD[@]}"
fi
