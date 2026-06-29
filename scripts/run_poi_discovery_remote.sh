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
  echo "ERROR: neither docker compose nor docker-compose is available." >&2
  exit 127
fi

CITY_SLUG="${CITY_SLUG:-}"
LIMIT="${LIMIT:-50}"
APPLY_DISCOVERED="${APPLY_DISCOVERED:-true}"
PER_CITY_TIMEOUT_SECONDS="${PER_CITY_TIMEOUT_SECONDS:-90}"
RESULTS_JSONL="/tmp/city-go-poi-discovery-results-${RANDOM}.jsonl"
: > "$RESULTS_JSONL"

emit_empty_summary() {
  local status="$1"
  local error_text="${2:-}"
  python - "$CITY_SLUG" "$LIMIT" "$APPLY_DISCOVERED" "$status" "$error_text" <<'PY'
import json
import sys
city_slug, limit, apply_discovered, status, error_text = sys.argv[1:6]
payload = {
    "apply": apply_discovered == "true",
    "city_slug": city_slug or None,
    "limit": int(limit),
    "status": status,
    "cities": [],
    "total_created": 0,
    "failed_cities": 1 if error_text else 0,
    "errors": [error_text] if error_text else [],
}
print("POI_DISCOVERY_SUMMARY_JSON=" + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
PY
}

emit_final_summary() {
  local status="$1"
  python - "$RESULTS_JSONL" "$CITY_SLUG" "$LIMIT" "$APPLY_DISCOVERED" "$status" <<'PY'
import json
import sys
from pathlib import Path
path, city_slug, limit, apply_discovered, status = sys.argv[1:6]
rows = []
for line in Path(path).read_text(encoding="utf-8").splitlines():
    if line.strip():
        rows.append(json.loads(line))
errors = []
for row in rows:
    for error in row.get("errors") or []:
        errors.append(f"{row.get('city_slug')}: {error}")
payload = {
    "apply": apply_discovered == "true",
    "city_slug": city_slug or None,
    "limit": int(limit),
    "status": status,
    "cities": rows,
    "total_created": sum(int(row.get("created") or 0) for row in rows),
    "failed_cities": sum(1 for row in rows if row.get("errors")),
    "errors": errors[:20],
}
print("POI_DISCOVERY_SUMMARY_JSON=" + json.dumps(payload, ensure_ascii=False, sort_keys=True), flush=True)
PY
}

append_failed_city() {
  local city="$1"
  local reason="$2"
  python - "$city" "$reason" >> "$RESULTS_JSONL" <<'PY'
import json
import sys
city, reason = sys.argv[1:3]
print(json.dumps({
    "city_slug": city,
    "city_name": city,
    "fetched": 0,
    "created": 0,
    "duplicates": 0,
    "skipped": 0,
    "errors": [reason],
    "places": [],
}, ensure_ascii=False, sort_keys=True))
PY
}

backend_container_id="$(${COMPOSE[@]} ps -q backend | head -n 1 || true)"
if [ -z "$backend_container_id" ]; then
  echo "ERROR: backend container is not running." >&2
  emit_empty_summary "error" "backend_container_not_found"
  exit 1
fi

backend_state="$(docker inspect -f '{{.State.Status}}' "$backend_container_id" 2>/dev/null || true)"
if [ "$backend_state" != "running" ]; then
  echo "ERROR: backend container state is ${backend_state:-unknown}." >&2
  emit_empty_summary "error" "backend_container_not_running:${backend_state:-unknown}"
  exit 1
fi

echo "=== poi discovery ==="
echo "city=${CITY_SLUG:-all} limit=${LIMIT} apply=${APPLY_DISCOVERED} per_city_timeout=${PER_CITY_TIMEOUT_SECONDS}s"
echo "backend_container=$backend_container_id state=$backend_state"

if [ -n "$CITY_SLUG" ]; then
  city_slugs=("$CITY_SLUG")
else
  echo "=== load city queue ==="
  mapfile -t city_slugs < <(${COMPOSE[@]} exec -T backend python -c 'from db.session import SessionLocal; from models.city import City; db=SessionLocal(); [print(slug, flush=True) for slug, in db.query(City.slug).order_by(City.slug.asc()).all() if slug]; db.close()')
fi

if [ "${#city_slugs[@]}" -eq 0 ]; then
  echo "No cities found."
  emit_final_summary "success"
  exit 0
fi

echo "queue_size=${#city_slugs[@]}"
failed=0

for city in "${city_slugs[@]}"; do
  echo "=== poi discovery city: ${city} ==="
  city_log="/tmp/city-go-poi-discovery-${city}-${RANDOM}.log"
  cmd=(python -u scripts/discover_new_pois.py --city "$city" --limit "$LIMIT")
  if [ "$APPLY_DISCOVERED" = "true" ]; then
    cmd+=(--apply)
  fi

  set +e
  timeout --signal=TERM "${PER_CITY_TIMEOUT_SECONDS}s" ${COMPOSE[@]} exec -T \
    -e DB_POOL_SIZE=1 \
    -e DB_MAX_OVERFLOW=0 \
    -e DB_POOL_TIMEOUT_SECONDS=10 \
    -e DB_STATEMENT_TIMEOUT_MS=30000 \
    backend "${cmd[@]}" 2>&1 | tee "$city_log"
  exit_code=${PIPESTATUS[0]}
  set -e

  if [ "$exit_code" -ne 0 ]; then
    echo "ERROR: city ${city} failed with exit code ${exit_code}" >&2
    append_failed_city "$city" "city_command_failed:${exit_code}"
    failed=$((failed + 1))
    continue
  fi

  city_summary="$(grep '^POI_DISCOVERY_SUMMARY_JSON=' "$city_log" | tail -n 1 | sed 's/^POI_DISCOVERY_SUMMARY_JSON=//' || true)"
  if [ -z "$city_summary" ]; then
    echo "ERROR: city ${city} did not emit summary" >&2
    append_failed_city "$city" "city_summary_missing"
    failed=$((failed + 1))
    continue
  fi

  python - "$city_summary" >> "$RESULTS_JSONL" <<'PY'
import json
import sys
payload = json.loads(sys.argv[1])
for row in payload.get("cities") or []:
    print(json.dumps(row, ensure_ascii=False, sort_keys=True))
PY
  echo "city_done=${city}"
done

if [ "$failed" -gt 0 ]; then
  emit_final_summary "partial_failure"
  exit 1
fi

emit_final_summary "success"
${COMPOSE[@]} ps backend || true
