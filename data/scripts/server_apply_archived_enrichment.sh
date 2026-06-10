#!/usr/bin/env bash
# Safe server apply for archived place enrichment batches (no volume overlay).
set -euo pipefail
cd /srv/app

BATCHES=(
  place_enrichment_khanty-mansiysk_20260607_160951
  place_enrichment_zelenogradsk_20260607_160951
)
IMAGE="$(docker compose config --images backend | head -1)"
NET="$(docker inspect "$(docker compose ps -q backend 2>/dev/null | head -1)" -f '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null || true)"
NET="${NET:-app_default}"

run_py() {
  docker run --rm --env-file .env --network "$NET" "$IMAGE" \
    bash -c "PYTHONPATH=/app $*"
}

echo "=== Pull latest images ==="
docker compose pull

echo "=== Verify archive batches in image ==="
for bid in "${BATCHES[@]}"; do
  run_py "ls -la data/exports/place_enrichment/archive/${bid}"
done

echo "=== Preview ==="
for bid in "${BATCHES[@]}"; do
  run_py "python data/scripts/import_place_enrichment_csv.py --batch-id ${bid} --preview"
done

echo "=== Apply ==="
for bid in "${BATCHES[@]}"; do
  run_py "python data/scripts/import_place_enrichment_csv.py --batch-id ${bid} --apply --no-archive-if-archived"
done

echo "=== Verify DB ==="
run_py "python data/scripts/verify_enrichment_apply.py --city-slug khanty-mansiysk --batch-id place_enrichment_khanty-mansiysk_20260607_160951"
run_py "python data/scripts/verify_enrichment_apply.py --city-slug zelenogradsk --batch-id place_enrichment_zelenogradsk_20260607_160951"

echo "SERVER_APPLY_SCRIPT_DONE"
