#!/usr/bin/env bash
set -euo pipefail

cd /srv/app

if docker compose version >/dev/null 2>&1; then
  COMPOSE=(docker compose)
  echo "Docker Compose command: docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE=(docker-compose)
  echo "Docker Compose command: docker-compose"
else
  echo "ERROR: neither 'docker compose' nor 'docker-compose' is available on the production host." >&2
  exit 127
fi

CITY_SLUG="${CITY_SLUG:-}"
LIMIT="${LIMIT:-50}"
APPLY_DISCOVERED="${APPLY_DISCOVERED:-true}"

emit_failure_summary() {
  local reason="$1"
  python - "$reason" "$CITY_SLUG" "$LIMIT" "$APPLY_DISCOVERED" <<'PY'
import json
import sys

reason, city_slug, limit, apply_discovered = sys.argv[1:5]
payload = {
    "apply": apply_discovered == "true",
    "city_slug": city_slug or None,
    "cities": [],
    "total_created": 0,
    "status": "error",
    "errors": [reason],
}
print("POI_DISCOVERY_SUMMARY_JSON=" + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
PY
}

backend_container_id="$("${COMPOSE[@]}" ps -q backend | head -n 1 || true)"
if [ -z "$backend_container_id" ]; then
  echo "ERROR: backend container is not running; refusing to start/recreate backend from POI discovery." >&2
  emit_failure_summary "backend_container_not_found"
  exit 1
fi

backend_state="$(docker inspect -f '{{.State.Status}}' "$backend_container_id" 2>/dev/null || true)"
if [ "$backend_state" != "running" ]; then
  echo "ERROR: backend container state is '$backend_state'; refusing to start/recreate backend from POI discovery." >&2
  emit_failure_summary "backend_container_not_running:${backend_state:-unknown}"
  exit 1
fi

CMD=(python scripts/discover_new_pois.py --limit "$LIMIT")
if [ -n "$CITY_SLUG" ]; then
  CMD+=(--city "$CITY_SLUG")
fi
if [ "$APPLY_DISCOVERED" = "true" ]; then
  CMD+=(--apply)
fi

echo "=== poi discovery ==="
echo "city=${CITY_SLUG:-all} limit=${LIMIT} apply=${APPLY_DISCOVERED}"
echo "backend_container=$backend_container_id state=$backend_state"

set +e
timeout --signal=TERM 10m "${COMPOSE[@]}" exec -T \
  -e DB_POOL_SIZE=1 \
  -e DB_MAX_OVERFLOW=0 \
  -e DB_POOL_TIMEOUT_SECONDS=10 \
  -e DB_STATEMENT_TIMEOUT_MS=30000 \
  backend "${CMD[@]}"
status=$?
set -e

if [ "$status" -ne 0 ]; then
  echo "ERROR: POI discovery command failed with exit code $status" >&2
  emit_failure_summary "poi_discovery_command_failed:$status"
  exit "$status"
fi

"${COMPOSE[@]}" ps backend || true
