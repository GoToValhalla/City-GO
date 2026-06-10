#!/usr/bin/env bash
set -euo pipefail

HOST="$(printf '%s' "${DEPLOY_HOST:?}" | tr -d '[:space:]')"
USER="$(printf '%s' "${DEPLOY_USER:?}" | tr -d '[:space:]')"
PORT="$(printf '%s' "${DEPLOY_PORT:-22}" | tr -d '[:space:]')"
KEY="${SSH_KEY:-$HOME/.ssh/deploy_key}"

export SSH_OPTS="-o StrictHostKeyChecking=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=20 \
  -o ConnectTimeout=30 \
  -o ControlMaster=auto \
  -o ControlPath=${HOME}/.ssh/cm-%r@%h:%p \
  -o ControlPersist=600"

ssh_prod() {
  local attempt=1
  while [ "$attempt" -le 5 ]; do
    if ssh $SSH_OPTS -i "$KEY" -p "$PORT" "$USER@$HOST" "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep $((attempt * 3))
  done
  return 1
}

scp_prod() {
  local attempt=1
  while [ "$attempt" -le 5 ]; do
    if scp $SSH_OPTS -i "$KEY" -P "$PORT" "$@"; then
      return 0
    fi
    attempt=$((attempt + 1))
    sleep $((attempt * 3))
  done
  return 1
}
