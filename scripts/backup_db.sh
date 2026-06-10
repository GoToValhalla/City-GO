#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required in the process environment." >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-backups}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${BACKUP_DIR}/citygo_${STAMP}.dump"

mkdir -p "${BACKUP_DIR}"
pg_dump --format=custom --no-owner --no-privileges --file="${OUT}" "${DATABASE_URL}"
echo "${OUT}"
