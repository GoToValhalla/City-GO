#!/usr/bin/env bash
set -euo pipefail

run_docker() {
  timeout --signal=TERM --kill-after=15s 90s docker "$@"
}

# Prefer the standalone binary on legacy hosts. Some old Docker CLIs accept
# the version probe but reject real `docker compose` subcommands.
if command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_MODE="standalone"
  echo "Docker Compose command: docker-compose"
elif docker compose version >/dev/null 2>&1; then
  COMPOSE_MODE="plugin"
  echo "Docker Compose command: docker compose"
else
  echo "ERROR: neither 'docker compose' nor 'docker-compose' is available on the production host." >&2
  exit 127
fi

run_compose_timeout() {
  local duration="$1"
  shift
  if [ "$COMPOSE_MODE" = "plugin" ]; then
    timeout --signal=TERM --kill-after=30s "$duration" docker compose "$@"
  else
    timeout --signal=TERM --kill-after=30s "$duration" docker-compose "$@"
  fi
}

run_compose() {
  run_compose_timeout 90s "$@"
}

compose_recreate_no_pull() {
  # docker compose v2 supports `up --pull never`; legacy docker-compose v1 does not.
  # Images are already pulled explicitly in the registry step, so v1 can safely omit it.
  if [ "$COMPOSE_MODE" = "plugin" ]; then
    run_compose up -d --no-deps --force-recreate --pull never "$@"
  else
    run_compose up -d --no-deps --force-recreate "$@"
  fi
}

diagnose_runtime() {
  echo "=== production runtime diagnostics ==="
  run_compose ps || true
  run_compose logs --tail=250 db backend import-worker bot || true
  run_compose_timeout 30s exec -T db pg_isready -U postgres -d city_guide </dev/null || true
  run_compose_timeout 30s exec -T db psql -U postgres -d city_guide -v ON_ERROR_STOP=1 -c \
    "SELECT now() AS checked_at, count(*) AS connections, count(*) FILTER (WHERE state = 'active') AS active, count(*) FILTER (WHERE wait_event IS NOT NULL) AS waiting FROM pg_stat_activity WHERE datname = current_database();" </dev/null || true
  run_compose_timeout 30s exec -T db psql -U postgres -d city_guide -v ON_ERROR_STOP=1 -c \
    "SELECT pid, usename, application_name, state, wait_event_type, wait_event, age(clock_timestamp(), query_start) AS query_age, left(query, 180) AS query FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() ORDER BY query_start NULLS LAST LIMIT 30;" </dev/null || true
}

wait_for_database() {
  local attempts="${1:-30}"
  for attempt in $(seq 1 "$attempts"); do
    if run_compose_timeout 10s exec -T db pg_isready -U postgres -d city_guide </dev/null >/dev/null 2>&1 \
      && run_compose_timeout 15s run -T --rm --no-deps backend python -c \
        "from core.readiness import check_database_ready; ok, reason = check_database_ready(); print(reason); raise SystemExit(0 if ok else 1)" </dev/null >/dev/null 2>&1; then
      echo "Database readiness OK attempt=${attempt}"
      return 0
    fi
    echo "Database not ready attempt=${attempt}/${attempts}"
    sleep 3
  done
  return 1
}

wait_for_backend_ready() {
  local attempts="${1:-30}"
  for attempt in $(seq 1 "$attempts"); do
    if run_compose_timeout 15s exec -T backend curl -sf http://localhost:8000/ready </dev/null >/dev/null 2>&1; then
      echo "Backend and database readiness OK attempt=${attempt}"
      return 0
    fi
    echo "Backend readiness failed attempt=${attempt}/${attempts}"
    sleep 3
  done
  return 1
}

post_start_api_smoke() {
  echo "=== post-start API smoke ==="
  curl -fsS --connect-timeout 5 --max-time 15 http://localhost:8000/ready >/dev/null
  curl -fsS --connect-timeout 5 --max-time 15 "http://localhost:8000/places/?limit=1" >/dev/null
  curl -fsS --connect-timeout 5 --max-time 15 \
    -H "Authorization: Bearer ${ADMIN_API_TOKEN}" \
    http://localhost:8000/admin/overview >/dev/null
  echo "Public and admin API smoke OK"
}

mkdir -p /srv/app

echo "=== download compose from ${GH_REPO}@main ==="
curl -sf --connect-timeout 15 --max-time 60 \
  -H "Authorization: token ${GH_TOKEN}" \
  -H "Accept: application/vnd.github.raw" \
  -o /srv/app/docker-compose.yml \
  "https://api.github.com/repos/${GH_REPO}/contents/docker-compose.yml?ref=main"

cd /srv/app
touch .env

# Deployment secrets are the source of truth. Always replace existing values so
# runtime workers do not keep an obsolete Telegram token after secret rotation.
HOST_PYTHON="$(command -v python3 || command -v python || true)"
if [ -z "$HOST_PYTHON" ]; then
  echo "ERROR: neither python3 nor python is available on the production host. Cannot update /srv/app/.env safely." >&2
  exit 1
fi
"$HOST_PYTHON" - <<'PY'
import os
from pathlib import Path

path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines()
updates = {
    'ADMIN_API_TOKEN': os.environ.get('ADMIN_API_TOKEN', ''),
    'TELEGRAM_BOT_TOKEN': os.environ.get('TELEGRAM_BOT_TOKEN', ''),
    'TELEGRAM_CHAT_ID': os.environ.get('TELEGRAM_CHAT_ID', ''),
    'APP_ENV': 'production',
}
for key in ('ADMIN_API_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'):
    if not updates[key]:
        raise SystemExit(f'{key} is empty; refusing to deploy with broken runtime notifications')
filtered = [line for line in lines if not any(line.startswith(f'{key}=') for key in updates)]
filtered.extend(f'{key}={value}' for key, value in updates.items())
path.write_text('\n'.join(filtered) + '\n', encoding='utf-8')
print('Runtime secrets updated: admin token and Telegram credentials are configured')
PY

run_compose_timeout 30s config >/dev/null

echo "=== docker daemon preflight ==="
if ! timeout 30s docker info >/dev/null; then
  echo "ERROR: Docker daemon is not responding within 30 seconds. Deploy stopped before changing runtime containers."
  exit 1
fi

echo "=== cleanup stale migration containers ==="
STALE_MIGRATE_IDS=$(timeout 30s docker ps -aq --filter label=com.docker.compose.service=migrate || true)
if [ -n "$STALE_MIGRATE_IDS" ]; then
  echo "Removing stale migration containers: $STALE_MIGRATE_IDS"
  timeout --signal=TERM --kill-after=15s 90s docker rm -f $STALE_MIGRATE_IDS
fi

echo "=== production state before deploy ==="
df -h || true
run_compose ps || true
curl -sf --connect-timeout 5 --max-time 10 http://localhost/build.json || true
echo

if ! run_compose ps frontend 2>/dev/null | grep -q "Up"; then
  run_compose up -d --no-deps frontend || true
fi

echo "=== docker login and pull fresh images ==="
REGISTRY_OK=0
for attempt in 1 2 3; do
  if echo "${GH_TOKEN}" | timeout 60s docker login ghcr.io -u "${GH_ACTOR}" --password-stdin \
    && run_compose_timeout 8m pull; then
    REGISTRY_OK=1
    break
  fi
  echo "WARN: ghcr login/pull failed attempt=${attempt}/3"
  sleep 10
done
if [ "$REGISTRY_OK" != "1" ]; then
  echo "ERROR: ghcr.io unavailable; existing containers were left running."
  run_compose ps || true
  exit 1
fi

echo "=== ensure PostgreSQL is running before migrations ==="
run_compose up -d db
if ! wait_for_database 30; then
  echo "ERROR: PostgreSQL is not ready before migrations."
  diagnose_runtime
  exit 1
fi

echo "=== quiesce database clients before migrations ==="
run_compose_timeout 2m stop -t 30 import-worker bot backend || true
run_compose ps || true

restore_runtime() {
  echo "=== restore previous runtime after failed deploy ==="
  run_compose start backend bot import-worker || true
  diagnose_runtime
}

echo "=== migrations ==="
run_compose rm -sf migrate || true
set +e
run_compose_timeout 5m run -T --rm migrate </dev/null
MIGRATE_EXIT=$?
set -e
run_compose logs --tail=200 migrate || true
if [ "$MIGRATE_EXIT" != "0" ]; then
  echo "ERROR: migrations failed or timed out (exit code ${MIGRATE_EXIT})."
  run_compose_timeout 90s run -T --rm --no-deps backend alembic heads </dev/null || true
  run_compose_timeout 90s run -T --rm --no-deps backend alembic current </dev/null || true
  restore_runtime
  exit 1
fi

echo "=== production schema guard ==="
set +e
run_compose_timeout 3m run -T --rm --no-deps backend python scripts/prod_schema_guard.py </dev/null
SCHEMA_EXIT=$?
set -e
if [ "$SCHEMA_EXIT" != "0" ]; then
  echo "ERROR: production schema guard failed or timed out (exit code ${SCHEMA_EXIT})."
  restore_runtime
  exit 1
fi

echo "=== reconcile legacy public flags ==="
# This only closes legacy leaks from cities that are not explicitly published.
# It never publishes a city or place.
run_compose_timeout 90s run -T --rm --no-deps backend \
  python scripts/reconcile_publication_flags.py --apply --confirm \
  </dev/null

echo "=== recreate backend ==="
compose_recreate_no_pull backend
if ! wait_for_backend_ready 30; then
  echo "ERROR: backend started without a working database connection."
  diagnose_runtime
  exit 1
fi

echo "=== recreate frontend ==="
run_compose rm -sf frontend || true
compose_recreate_no_pull frontend
FRONTEND_OK=0
for attempt in $(seq 1 20); do
  BUILD_JSON=$(curl -sf --connect-timeout 5 --max-time 10 http://localhost/build.json || true)
  if printf '%s' "$BUILD_JSON" | grep -q "$EXPECTED_FRONTEND_SHA"; then
    FRONTEND_OK=1
    echo "Frontend build SHA OK: ${EXPECTED_FRONTEND_SHA}"
    break
  fi
  echo "Frontend not ready or SHA mismatch attempt=${attempt}/20 actual=${BUILD_JSON}"
  sleep 3
done
if [ "$FRONTEND_OK" != "1" ]; then
  diagnose_runtime
  run_compose logs --tail=240 frontend || true
  exit 1
fi

echo "=== recreate background services ==="
compose_recreate_no_pull bot import-worker
BACKGROUND_OK=0
for attempt in $(seq 1 10); do
  if run_compose ps bot 2>/dev/null | grep -q "Up" \
    && run_compose ps import-worker 2>/dev/null | grep -q "Up"; then
    BACKGROUND_OK=1
    break
  fi
  sleep 3
done
if [ "$BACKGROUND_OK" != "1" ]; then
  diagnose_runtime
  exit 1
fi

echo "=== runtime notification configuration gate ==="
for service in backend import-worker; do
  run_compose_timeout 30s exec -T "$service" python -c \
    "from core.config import settings; assert settings.telegram_bot_token or settings.bot_token; assert settings.telegram_chat_id; print('telegram_runtime_configured service=${service}')" </dev/null
done

echo "=== post-start database stability gate ==="
for check in 1 2 3; do
  sleep 5
  if ! wait_for_backend_ready 5; then
    echo "ERROR: database readiness degraded after background services started (check ${check}/3)."
    diagnose_runtime
    exit 1
  fi
done

if ! post_start_api_smoke; then
  echo "ERROR: post-start API smoke failed."
  diagnose_runtime
  exit 1
fi
curl -sf --connect-timeout 5 --max-time 10 http://localhost/api/version || curl -sf --max-time 10 http://localhost:8000/version
run_compose_timeout 60s exec -T backend alembic current </dev/null || true
run_compose ps || true
echo "Deploy done: $(date)"
