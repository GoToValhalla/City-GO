#!/usr/bin/env bash
# Полный data pipeline по всем import targets на prod (после deploy).
set -euo pipefail

APP_DIR="${APP_DIR:-/srv/app}"
TS="${RUN_TS:-$(date -u +%Y%m%d_%H%M%S)}"
AUDIT_DIR="$APP_DIR/data/audit/full_city_import_run/$TS"
PIPELINE_ARGS=(
  --apply --force
  --address-backfill-limit 1000
  --address-backfill-sleep 1.1
  --image-enrichment-limit 500
)

cd "$APP_DIR"
mkdir -p "$AUDIT_DIR"
echo "=== FULL CITY IMPORT RUN $TS ===" | tee "$AUDIT_DIR/run.log"
git rev-parse HEAD | tee "$AUDIT_DIR/prod_commit.txt"

echo "=== before snapshot ===" | tee -a "$AUDIT_DIR/run.log"
docker compose exec -T backend python data/scripts/full_city_snapshot.py \
  | tee "$AUDIT_DIR/before_snapshot.json"

echo "=== pipeline ===" | tee -a "$AUDIT_DIR/run.log"
docker compose exec -T backend python data/scripts/run_due_import_jobs.py "${PIPELINE_ARGS[@]}" \
  | tee "$AUDIT_DIR/pipeline_result.json"

echo "=== after snapshot ===" | tee -a "$AUDIT_DIR/run.log"
docker compose exec -T backend python data/scripts/full_city_snapshot.py \
  | tee "$AUDIT_DIR/after_snapshot.json"

docker compose ps | tee "$AUDIT_DIR/docker_compose_ps.txt"
PYTHONPATH="$APP_DIR" python3 data/scripts/full_city_import_report.py \
  --audit-dir "$AUDIT_DIR" \
  --docs-out "$APP_DIR/docs/routes/full_city_import_run_report.md"
echo "DONE audit_dir=$AUDIT_DIR"
