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

compose() {
  if [ "$COMPOSE_MODE" = "plugin" ]; then
    docker compose "$@"
  else
    docker-compose "$@"
  fi
}

POLICY_MODE="${POLICY_MODE:-shadow}"
CITY_SLUG="${CITY_SLUG:-}"
LIMIT="${LIMIT:-500}"
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
compose exec -T backend "${CMD[@]}"
