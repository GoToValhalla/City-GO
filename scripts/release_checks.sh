#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"

"${PYTHON_BIN}" scripts/backend_quality_gate.py
"${PYTHON_BIN}" -m pytest -q
alembic upgrade head
export BASE_URL="${BASE_URL:-http://127.0.0.1:8000}"
scripts/release_smoke.sh
"${PYTHON_BIN}" scripts/check_place_coverage_gate.py
