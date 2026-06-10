#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required in the process environment." >&2
  exit 1
fi

if [[ $# -ne 1 ]]; then
  echo "Usage: scripts/restore_db.sh path/to/backup.dump" >&2
  exit 1
fi

DUMP_PATH="$1"
if [[ ! -f "${DUMP_PATH}" ]]; then
  echo "Backup file does not exist: ${DUMP_PATH}" >&2
  exit 1
fi

pg_restore --clean --if-exists --no-owner --no-privileges --dbname="${DATABASE_URL}" "${DUMP_PATH}"
