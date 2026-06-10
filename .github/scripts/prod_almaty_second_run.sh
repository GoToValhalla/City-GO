#!/usr/bin/env bash
# Второй прогон Алматы на prod: snapshot → slug → enrichment → snapshot.
set -euo pipefail

OUT_DIR="${OUT_DIR:-/tmp/almaty_run}"
APPLY_SLUG="${APPLY_SLUG:-true}"
ADDRESS_LIMIT="${ADDRESS_LIMIT:-50}"
IMAGE_LIMIT="${IMAGE_LIMIT:-50}"
CITY_FROM="алматы"
CITY_TO="almaty"

exec_backend() {
  docker compose exec -T backend "$@" </dev/null
}

mkdir -p "$OUT_DIR"
cd /srv/app

echo "=== ALEMBIC ==="
exec_backend alembic upgrade head

CID="$(docker compose ps -q backend | head -1)"
if [ -z "$CID" ]; then
  echo "backend container not found" >&2
  exit 1
fi

for script in city_data_snapshot.py migrate_city_slug.py backfill_missing_place_addresses.py \
  enrich_place_images.py cleanup_imported_places_quality.py; do
  docker cp "$OUT_DIR/$script" "$CID:/app/data/scripts/$script"
done
if [ -f "$OUT_DIR/place_address_backfill.py" ]; then
  docker cp "$OUT_DIR/place_address_backfill.py" "$CID:/app/services/place_address_backfill.py"
fi
if [ -f "$OUT_DIR/migrate_city_slug.py" ]; then
  docker cp "$OUT_DIR/migrate_city_slug.py" "$CID:/app/data/scripts/migrate_city_slug.py"
fi

echo "=== BEFORE ==="
exec_backend python data/scripts/city_data_snapshot.py --city "$CITY_FROM" | tee "$OUT_DIR/before.json"

echo "=== SLUG DRY-RUN ==="
exec_backend python data/scripts/migrate_city_slug.py --from-slug "$CITY_FROM" --to-slug "$CITY_TO" | tee "$OUT_DIR/slug_dry.json"
if grep -q '"already_migrated": true' "$OUT_DIR/slug_dry.json" 2>/dev/null; then
  echo "slug already at $CITY_TO, skipping apply"
elif [ "$APPLY_SLUG" = "true" ]; then
  echo "=== SLUG APPLY ==="
  exec_backend python data/scripts/migrate_city_slug.py --from-slug "$CITY_FROM" --to-slug "$CITY_TO" --apply | tee "$OUT_DIR/slug_apply.json"
fi

echo "=== ALIAS CHECK ==="
exec_backend python -c "from db.session import SessionLocal; from services.city_slug_resolver import resolve_city_by_slug; db=SessionLocal(); c=resolve_city_by_slug(db,'$CITY_FROM'); print(c.slug if c else 'missing')"

echo "=== ADDRESS BACKFILL ==="
exec_backend python data/scripts/backfill_missing_place_addresses.py \
  --city "$CITY_TO" --limit "$ADDRESS_LIMIT" --apply | tee "$OUT_DIR/address_result.json"

echo "=== IMAGE ENRICHMENT ==="
exec_backend python data/scripts/enrich_place_images.py \
  --city "$CITY_TO" --limit "$IMAGE_LIMIT" --apply | tee "$OUT_DIR/image_result.json"

echo "=== QUALITY ==="
exec_backend python data/scripts/cleanup_imported_places_quality.py --city "$CITY_TO" --apply | tee "$OUT_DIR/quality.json"

echo "=== AFTER ==="
exec_backend python data/scripts/city_data_snapshot.py --city "$CITY_TO" | tee "$OUT_DIR/after.json"

echo "=== DONE ==="
ls -la "$OUT_DIR"
touch "$OUT_DIR/DONE"
