#!/usr/bin/env bash
# Деплой на prod БЕЗ GitHub Actions: build/migrate/up на сервере в /srv/app.
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/app}"
BUILD_MODE="${BUILD_MODE:-build}"
SKIP_BUILD="${SKIP_BUILD:-false}"
IMAGE_PRUNE="${IMAGE_PRUNE:-false}"

cd "$APP_DIR"
echo "=== PROD DEPLOY $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="
echo "dir=$APP_DIR build_mode=$BUILD_MODE skip_build=$SKIP_BUILD image_prune=$IMAGE_PRUNE"

if [ "$SKIP_BUILD" != "true" ]; then
  if [ "$BUILD_MODE" = "pull" ]; then
    echo "=== docker compose pull ==="
    docker compose pull
  else
    echo "=== docker compose build (no GH workers) ==="
    docker compose build backend frontend
  fi
fi

echo "=== migrations ==="
set +e
docker compose up migrate
MIGRATE_EXIT=$?
set -e
docker compose logs migrate || true
if [ "$MIGRATE_EXIT" != "0" ]; then
  echo "ERROR: migrate failed exit=$MIGRATE_EXIT" >&2
  exit 1
fi

echo "=== up -d ==="
docker compose up -d --remove-orphans
if [ "$IMAGE_PRUNE" = "true" ]; then
  docker image prune -f || true
fi

echo "=== health ==="
for attempt in $(seq 1 20); do
  if docker compose exec -T backend curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "backend health OK attempt=$attempt"
    docker compose exec -T backend curl -sf http://localhost:8000/ready || true
    echo "=== frontend ==="
    if docker compose exec -T frontend wget -qO- http://127.0.0.1:80/ >/dev/null 2>&1; then
      echo "frontend OK"
    else
      echo "WARN: frontend check failed" >&2
    fi
    echo "=== containers ==="
    docker compose ps
    exit 0
  fi
  sleep 3
done
echo "ERROR: backend health timeout" >&2
docker compose ps || true
docker compose logs --tail=60 backend || true
exit 1
