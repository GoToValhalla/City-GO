#!/usr/bin/env bash
set -euo pipefail

run_docker() {
  timeout --signal=TERM --kill-after=15s 90s docker "$@"
}

run_compose() {
  timeout --signal=TERM --kill-after=15s 90s docker compose "$@"
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
ensure_env() {
  local key="$1"
  local value="$2"
  if ! grep -q "^${key}=." .env 2>/dev/null && [ -n "$value" ]; then
    printf '%s=%s\n' "$key" "$value" >> .env
  fi
}
ensure_env ADMIN_API_TOKEN "${ADMIN_API_TOKEN:-}"
ensure_env TELEGRAM_BOT_TOKEN "${TELEGRAM_BOT_TOKEN:-}"
ensure_env TELEGRAM_CHAT_ID "${TELEGRAM_CHAT_ID:-}"
if ! grep -q '^APP_ENV=' .env 2>/dev/null; then
  echo "APP_ENV=production" >> .env
fi

timeout 30s docker compose config >/dev/null

echo "=== docker daemon preflight ==="
if ! timeout 30s docker info >/dev/null; then
  echo "ERROR: Docker daemon is not responding within 30 seconds. Deploy stopped before changing runtime containers."
  exit 1
fi

# A cancelled SSH session does not necessarily stop the remote `docker compose
# run` process. Remove one-off migration containers left by previous deploys so
# they cannot keep a PostgreSQL transaction or consume server resources.
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
    && timeout --signal=TERM --kill-after=30s 8m docker compose pull; then
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

# PostgreSQL ALTER TABLE requires an ACCESS EXCLUSIVE lock. Runtime services are
# stopped first so open transactions cannot block Alembic indefinitely.
echo "=== quiesce database clients before migrations ==="
timeout --signal=TERM --kill-after=15s 2m docker compose stop -t 30 import-worker bot backend || true
run_compose ps || true

restore_runtime() {
  echo "=== restore previous runtime after failed deploy ==="
  run_compose start backend bot import-worker || true
  run_compose ps || true
}

echo "=== migrations ==="
run_compose rm -sf migrate || true
set +e
timeout --signal=TERM --kill-after=30s 5m docker compose run -T --rm migrate </dev/null
MIGRATE_EXIT=$?
set -e
run_compose logs --tail=200 migrate || true
if [ "$MIGRATE_EXIT" != "0" ]; then
  echo "ERROR: migrations failed or timed out (exit code ${MIGRATE_EXIT})."
  timeout 90s docker compose run -T --rm --no-deps backend alembic heads </dev/null || true
  timeout 90s docker compose run -T --rm --no-deps backend alembic current </dev/null || true
  restore_runtime
  exit 1
fi

echo "=== production schema guard ==="
set +e
timeout --signal=TERM --kill-after=30s 3m docker compose run -T --rm --no-deps backend python scripts/prod_schema_guard.py </dev/null
SCHEMA_EXIT=$?
set -e
if [ "$SCHEMA_EXIT" != "0" ]; then
  echo "ERROR: production schema guard failed or timed out (exit code ${SCHEMA_EXIT})."
  restore_runtime
  exit 1
fi

echo "=== recreate backend ==="
run_compose up -d --no-deps --force-recreate --pull never backend
BACKEND_OK=0
for attempt in $(seq 1 30); do
  if timeout 15s docker compose exec -T backend curl -sf http://localhost:8000/health </dev/null >/dev/null 2>&1; then
    BACKEND_OK=1
    echo "Backend health OK attempt=${attempt}"
    break
  fi
  echo "Backend not ready attempt=${attempt}/30"
  sleep 3
done
if [ "$BACKEND_OK" != "1" ]; then
  run_compose logs --tail=300 backend || true
  exit 1
fi

echo "=== recreate frontend ==="
run_compose rm -sf frontend || true
run_compose up -d --no-deps --force-recreate --pull never frontend
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
  run_compose logs --tail=240 frontend || true
  exit 1
fi

echo "=== recreate background services ==="
run_compose up -d --no-deps --force-recreate --pull never bot import-worker
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
  run_compose logs --tail=200 bot import-worker || true
  exit 1
fi

curl -sf --connect-timeout 5 --max-time 10 http://localhost/api/health >/dev/null
curl -sf --connect-timeout 5 --max-time 10 http://localhost/api/version || curl -sf --max-time 10 http://localhost:8000/version
timeout 60s docker compose exec -T backend alembic current </dev/null || true
run_compose ps || true
echo "Deploy done: $(date)"
