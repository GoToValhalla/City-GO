# Ханты-Мансийск: адреса на production

## Текущее состояние (проверено через API)

| Метрика | Production | Локально (после apply) |
|---------|------------|------------------------|
| Мест в каталоге | 215 | ~215 |
| С адресом | ~32 (15%) | ~146+ после `apply_from_review` |

Места на проде **есть** (OSM import в Postgres volume). Не хватает **адресов** — recovery применялся локально, не на сервере.

## Почему локально есть адреса, а на проде нет

1. **OSM** — у ~85% объектов нет `addr:*` тегов → `address` пустой в БД.
2. **Enrichment apply** на проде обновил в основном `short_description` (batch `...160951`), не массово адреса.
3. **Address recovery** — в git есть `review.csv` с **114** готовыми адресами (`place_address_recovery_khanty-mansiysk_20260607_190117`). Локально: `applied: 114`. На проде: **не применялось**.

Deploy **не** запускает address backfill (`profile: ops`, только dry-run).

## Применить адреса на production

### Вариант A — GitHub Actions (рекомендуется)

1. Убедитесь, что в GitHub Secrets заданы **без пробелов в конце**: `SSH_HOST`, `SSH_USER`, `SSH_PORT`, `SSH_PRIVATE_KEY`.
2. Actions → **Server Khanty Address Apply** (коммит `b979c7b` или новее).
3. Run workflow → `confirm` = **`APPLY`**
4. В логах: `SSH_OK`, затем `PROD_ADDRESS_APPLY_SCRIPT_DONE`, `applied: 114`

Если workflow падает с `hostname contains invalid characters` или `exit code 255` — проверьте trailing space в `SSH_HOST` или пустой `SSH_USER`. Deploy workflow использует те же секреты; если deploy зелёный, а address apply красный — подождите 1–2 мин (fail2ban) и перезапустите.

### Вариант B — вручную по SSH

```bash
cd /srv/app
REVIEW="data/exports/address_recovery/archive/place_address_recovery_khanty-mansiysk_20260607_190117/review.csv"

docker compose exec -T backend bash -c "PYTHONPATH=/app python data/scripts/check_place_address_coverage.py"

docker compose exec -T backend bash -c "PYTHONPATH=/app python data/scripts/backfill_missing_place_addresses.py --city khanty-mansiysk --apply-from-review ${REVIEW} --preview"

docker compose exec -T backend bash -c "PYTHONPATH=/app python data/scripts/backfill_missing_place_addresses.py --city khanty-mansiysk --apply-from-review ${REVIEW}"

docker compose restart backend
```

**Не монтировать** пустой `/srv/app/data/exports` в контейнер — он перекрывает `review.csv` из Docker-образа.

### Проверка после apply

```bash
curl -sSL 'http://<SERVER>/api/places/?city_slug=khanty-mansiysk&limit=100' | \
  python3 -c "import json,sys; d=json.load(sys.stdin); print('with_address', sum(1 for i in d['items'] if i.get('address')))"
```

Ожидание: **~140+** мест с адресом (32 существующих + ~114 из review).

## Оставшиеся без адреса

После batch останется ~70 мест (нет координат, `should_apply=false`, generic Nominatim). Для них — новый dry-run:

```bash
python data/scripts/run_address_recovery_flow.py --city khanty-mansiysk --limit 500
```

Затем review → apply (отдельный ops-цикл).
