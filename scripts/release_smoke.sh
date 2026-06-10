#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"

check_get() {
  local path="$1"
  local status
  status="$(curl -sS -o /tmp/citygo_smoke.json -w "%{http_code}" "${BASE_URL}${path}")"
  if [[ "${status}" != "200" ]]; then
    echo "GET ${path} failed with HTTP ${status}" >&2
    cat /tmp/citygo_smoke.json >&2
    exit 1
  fi
  echo "ok GET ${path}"
}

check_get "/health"
check_get "/ready"
check_get "/place-coverage/zelenogradsk"
check_get "/route-analytics/summary"
check_get "/place-import-logs/summary"
