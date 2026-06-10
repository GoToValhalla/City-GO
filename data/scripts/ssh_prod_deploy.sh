#!/usr/bin/env bash
# SSH → git pull → prod_on_server_deploy.sh (без rsync, без enrichment).
set -euo pipefail

HOST="${SSH_HOST:-${DEPLOY_HOST:?set SSH_HOST or DEPLOY_HOST}}"
USER="${SSH_USER:-${DEPLOY_USER:?set SSH_USER or DEPLOY_USER}}"
PORT="${SSH_PORT:-${DEPLOY_PORT:-22}}"
KEY="${SSH_KEY:-$HOME/.ssh/deploy_key}"
APP_DIR="${APP_DIR:-/srv/app}"
BUILD_MODE="${BUILD_MODE:-build}"
SKIP_BUILD="${SKIP_BUILD:-false}"
IMAGE_PRUNE="${IMAGE_PRUNE:-false}"

if [ ! -f "$KEY" ]; then
  echo "ERROR: SSH key not found: $KEY" >&2
  exit 1
fi

SSH_OPTS=(-o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 -i "$KEY" -p "$PORT")

echo "=== SSH deploy $USER@$HOST:$APP_DIR build_mode=$BUILD_MODE ==="
ssh "${SSH_OPTS[@]}" "$USER@$HOST" bash -s <<REMOTE
set -euo pipefail
cd "$APP_DIR"
if [ -d .git ]; then
  git fetch origin master
  git checkout master
  git pull --ff-only origin master
else
  echo "WARN: $APP_DIR is not a git repo; using existing tree"
fi
chmod +x data/scripts/prod_on_server_deploy.sh
BUILD_MODE="$BUILD_MODE" SKIP_BUILD="$SKIP_BUILD" IMAGE_PRUNE="$IMAGE_PRUNE" \
  bash data/scripts/prod_on_server_deploy.sh
REMOTE
