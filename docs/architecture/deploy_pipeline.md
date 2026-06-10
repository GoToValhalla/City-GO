# Deploy Pipeline & Migrations

## Порядок запуска (docker-compose)

```
db (healthy)
  └── migrate (alembic upgrade head)
        └── seed (minimal data)
              └── place-enrichment-export (CSV export всех городов)
                    └── backend (uvicorn)
                          └── bot
frontend (independent)

address-backfill (profile: ops, manual only) — NOT in deploy chain
```

Каждый шаг deploy chain запускается только после успешного завершения предыдущего (`condition: service_completed_successfully`).
Если `migrate` завершился с ошибкой — backend не стартует.

**Текущий head:** `a1b2c3d4e5f7` (admin ops: system_logs, product_events, admin_operations).

Prod smoke: `docs/admin/prod_smoke_checklist.md`.
Если `place-enrichment-export` упал — backend не стартует (ошибка в экспорте видна в логах).
0 результатов экспорта — **не ошибка**, сервис завершается с кодом 0.

**Address recovery не блокирует deploy.** Geocoding apply на production — только отдельной ops-задачей через review/preview/apply.

### Post-deploy health gate

После `docker compose up -d` deploy workflow проверяет `GET http://localhost:8000/health` внутри контейнера `backend`.
Если backend не отвечает — deploy помечается failed, в лог попадают `docker compose ps` и `docker compose logs backend`.

Типичная причина 502 на `/api/*` при «успешном» deploy: backend crash-loop из-за `APP_ENV=production` без `ADMIN_API_TOKEN` в `/srv/app/.env`.

Восстановление на сервере:

```bash
cd /srv/app
# сгенерировать токен локально: python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# добавить/обновить в .env:
#   APP_ENV=production
#   ADMIN_API_TOKEN=<сгенерированный_токен>
docker compose up -d backend frontend
docker compose logs --tail=50 backend
curl -sf http://localhost:8000/health
```

Автоматически при deploy: если в `/srv/app/.env` нет `ADMIN_API_TOKEN`, deploy подставит значение из GitHub secret `ADMIN_API_TOKEN` (Repository → Settings → Secrets).

Публичные `/api/places`, `/api/cities/available` не требуют Bearer-токена — им нужен только живой backend.

### Почему «0 мест» при живом frontend

1. **502 на `/api/*`** — backend в crash-loop (часто `ADMIN_API_TOKEN` + `APP_ENV=production`). UI показывает «Загрузка…» и пустой список.
2. **API жив, но мало мест** — `seed` даёт только 3 демо-места; для `khanty-mansiysk` основной каталог из OSM import (сохраняется в Postgres volume). См. `docs/operations/khanty_address_production_apply.md` если места есть, но **нет адресов**.

---

## Place Enrichment Export (автоматический)

Запускается после `seed`, перед `backend`.

```yaml
place-enrichment-export:
  command: python data/scripts/run_place_enrichment_export.py \
             --limit 100 --missing-fields address,photo,description --git-artifact
  depends_on: [migrate, seed]
  restart: "no"
  volumes:
    - enrichment_exports:/app/data/exports/place_enrichment
```

Результат:
- Batch-файлы в `data/exports/place_enrichment/active/<batch_id>/export.csv`
- Доступны в `/admin/place-enrichment` и (после `git commit && git push`) в GitHub для ChatGPT
- Не изменяет БД; 0 мест — не ошибка

**Ручной запуск:**
```bash
docker compose run --rm place-enrichment-export
# или с параметрами:
docker compose run --rm place-enrichment-export \
  python data/scripts/run_place_enrichment_export.py \
    --city zelenogradsk --limit 50 --missing-fields address,photo
```

---

## CI pipeline (GitHub Actions)

Файл: `.github/workflows/ci.yml`

Шаги backend-джобы:
1. Установка зависимостей
2. **`alembic upgrade head`** — smoke-проверка применения миграций на SQLite
3. `pytest` — полный тест-сьют
4. Проверка синтаксиса shell-скриптов

Это гарантирует, что любой PR с ломаной миграцией не пройдёт CI.

---

## Deploy pipeline (GitHub Actions → SSH)

Файл: `.github/workflows/deploy.yml`

Шаги деплоя на сервере:
1. Pull новых docker-образов
2. **`docker compose up migrate`** — запуск миграций с явным ожиданием
3. Проверка exit code `migrate` → если ≠ 0, деплой падает (`exit 1`)
4. Печать логов миграций в вывод деплоя
5. `docker compose up -d --remove-orphans` — запуск всех сервисов

---

## Address Recovery Flow

Рекомендуемый оркестратор: `data/scripts/run_address_recovery_flow.py`

Полный цикл (см. `docs/architecture/place_address_lifecycle.md`):

```
coverage before → dry-run + review CSV/JSON → apply-from-review (optional) → coverage after → flow summary
```

```bash
# Локально / staging: preview без записи в БД
python data/scripts/run_address_recovery_flow.py --all-cities --limit 500 --sleep 1.0

# Локальный apply (только should_apply=true)
python data/scripts/run_address_recovery_flow.py --all-cities --limit 500 --sleep 1.0 --apply
```

Артефакты: `data/exports/address_recovery/` (в `.gitignore`).

**Production apply** — отдельная задача: сначала preview/summary, затем явное подтверждение изменения production DB.

### address-backfill (ops only, не в deploy chain)

Сервис `address-backfill` в `docker-compose.yml` с `profiles: ["ops"]` — **не стартует** при `docker compose up -d` и **не блокирует** backend.

Deploy **не выполняет** geocoding `--apply`. Массовый Nominatim apply запрещён в default deploy.

Ручной ops (dry-run / coverage, без apply в compose default):
```bash
# Coverage report only (read-only)
python data/scripts/check_place_address_coverage.py --export

# Address recovery dry-run (review artifacts, без apply)
docker compose --profile ops run --rm address-backfill

# Production apply — отдельная задача, только после review
python data/scripts/run_address_recovery_flow.py --all-cities --limit 500 --sleep 1.0 --apply
# или GitHub workflow Server Khanty Address Apply / apply-from-review CSV
```

Nominatim User-Agent: `PLACE_ADDRESS_GEOCODER_USER_AGENT` (без `example.com`).

---

## Image Enrichment

Скрипт: `scripts/refresh_place_images.py`

**Статус**: pipeline работает с JSON-файлами (`frontend/public/data/`), **не интегрирован** в docker-compose и не пишет напрямую в БД.

Ручной запуск:
```bash
PYTHONPATH=/app python scripts/refresh_place_images.py  # dry-run
PYTHONPATH=/app python scripts/refresh_place_images.py --live  # реальные HTTP-запросы
```

Количество мест без фото в БД: `/place-coverage/{city_slug}` → поля `with_photo` / `without_photo`.

**TODO**: подключить image pipeline к БД (отдельная задача P2+).

---

## Будущие улучшения

- Healthcheck endpoint `/health` → добавить проверку версии миграций (текущий head)
- Отдельный cron/ops schedule для address recovery (не в deploy chain)
- Image enrichment — DB integration вместо JSON-файлов
