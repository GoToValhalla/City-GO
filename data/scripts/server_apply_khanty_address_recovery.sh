#!/usr/bin/env bash
# Safe production apply: khanty-mansiysk addresses from archived review CSV (no Nominatim).
set -eu
cd /srv/app

BATCH_ID="place_address_recovery_khanty-mansiysk_20260607_190117"
REVIEW_CSV="data/exports/address_recovery/archive/${BATCH_ID}/review.csv"

run_py() {
  docker compose exec -T backend bash -c "PYTHONPATH=/app $*"
}

if [ ! -f "${REVIEW_CSV}" ]; then
  echo "ERROR: review CSV missing at ${REVIEW_CSV}"
  exit 1
fi

echo "=== Preview apply-from-review ==="
run_py "python data/scripts/backfill_missing_place_addresses.py --city khanty-mansiysk --apply-from-review ${REVIEW_CSV} --preview" \
  > /tmp/khanty_preview.json
python3 -c "import json; r=json.load(open('/tmp/khanty_preview.json')); print('would_apply', r.get('would_apply', 0))"

echo "=== Apply-from-review ==="
run_py "python data/scripts/backfill_missing_place_addresses.py --city khanty-mansiysk --apply-from-review ${REVIEW_CSV}" \
  > /tmp/khanty_apply.json
python3 -c "import json; r=json.load(open('/tmp/khanty_apply.json')); print('applied', r.get('applied', 0), 'skipped', r.get('skipped', 0))"

echo "=== Production coverage AFTER ==="
run_py "python data/scripts/check_place_address_coverage.py" > /tmp/khanty_cov_after.json
python3 -c "import json; d=json.load(open('/tmp/khanty_cov_after.json'))['cities']['khanty-mansiysk']; print('after', d['with_real_address'], 'of', d['total_places'])"

echo "=== Restart backend (refresh API) ==="
docker compose restart backend

echo "PROD_ADDRESS_APPLY_SCRIPT_DONE"
