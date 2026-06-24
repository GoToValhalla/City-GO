#!/usr/bin/env bash
set -euo pipefail

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

docker compose config >/dev/null
echo "=== production state before deploy ==="
df -h || true
docker system df || true
docker compose ps || true
curl -sf --connect-timeout 5 --max-time 10 http://localhost/build.json || true
echo

if ! docker compose ps frontend 2>/dev/null | grep -q "Up"; then
  docker compose up -d --no-deps frontend || true
fi

echo "=== docker login and pull fresh images ==="
REGISTRY_OK=0
for attempt in 1 2 3; do
  if echo "${GH_TOKEN}" | docker login ghcr.io -u "${GH_ACTOR}" --password-stdin \
    && timeout --signal=TERM --kill-after=30s 10m docker compose pull; then
    REGISTRY_OK=1
    break
  fi
  echo "WARN: ghcr login/pull failed attempt=${attempt}/3"
  docker image prune -f || true
  sleep 10
done
if [ "$REGISTRY_OK" != "1" ]; then
  echo "ERROR: ghcr.io unavailable; existing containers were left running."
  docker compose ps || true
  exit 1
fi

# PostgreSQL ALTER TABLE requires an ACCESS EXCLUSIVE lock. Runtime services are
# stopped first so open transactions cannot block Alembic indefinitely.
echo "=== quiesce database clients before migrations ==="
docker compose stop -t 30 import-worker bot backend || true
docker compose ps || true

restore_runtime() {
  echo "=== restore previous runtime after failed deploy ==="
  docker compose start backend bot import-worker || true
  docker compose ps || true
}

echo "=== migrations ==="
docker compose rm -sf migrate || true
set +e
timeout --signal=TERM --kill-after=30s 12m docker compose run -T --rm migrate </dev/null
MIGRATE_EXIT=$?
set -e
docker compose logs --tail=200 migrate || true
if [ "$MIGRATE_EXIT" != "0" ]; then
  echo "ERROR: migrations failed or timed out (exit code ${MIGRATE_EXIT})."
  docker compose run -T --rm --no-deps backend alembic heads </dev/null || true
  docker compose run -T --rm --no-deps backend alembic current </dev/null || true
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
docker compose up -d --no-deps --force-recreate --pull never backend
BACKEND_OK=0
for attempt in $(seq 1 30); do
  if docker compose exec -T backend curl -sf http://localhost:8000/health </dev/null >/dev/null 2>&1; then
    BACKEND_OK=1
    echo "Backend health OK attempt=${attempt}"
    break
  fi
  echo "Backend not ready attempt=${attempt}/30"
  sleep 3
done
if [ "$BACKEND_OK" != "1" ]; then
  docker compose logs --tail=300 backend || true
  exit 1
fi

echo "=== recreate frontend ==="
docker compose rm -sf frontend || true
docker compose up -d --no-deps --force-recreate --pull never frontend
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
  docker compose logs --tail=240 frontend || true
  exit 1
fi

echo "=== recreate background services ==="
docker compose up -d --no-deps --force-recreate --pull never bot import-worker
BACKGROUND_OK=0
for attempt in $(seq 1 10); do
  if docker compose ps bot 2>/dev/null | grep -q "Up" \
    && docker compose ps import-worker 2>/dev/null | grep -q "Up"; then
    BACKGROUND_OK=1
    break
  fi
  sleep 3
done
if [ "$BACKGROUND_OK" != "1" ]; then
  docker compose logs --tail=200 bot import-worker || true
  exit 1
fi

curl -sf --connect-timeout 5 --max-time 10 http://localhost/api/health >/dev/null
curl -sf --connect-timeout 5 --max-time 10 http://localhost/api/version || curl -sf http://localhost:8000/version
docker compose exec -T backend alembic current </dev/null || true
docker compose ps || true
docker image prune -f || true
echo "Deploy done: $(date)"
