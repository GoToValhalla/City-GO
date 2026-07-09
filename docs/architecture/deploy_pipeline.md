# Deploy Pipeline & Migrations

## Порядок запуска локального docker-compose

```text
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

Prod smoke: `docs/admin/prod_smoke_checklist.md`.
Если `place-enrichment-export` упал — backend не стартует (ошибка в экспорте видна в логах).
0 результатов экспорта — **не ошибка**, сервис завершается с кодом 0.

**Address recovery не блокирует deploy.** Geocoding apply на production — только отдельной ops-задачей через review/preview/apply.

---

## GitHub Actions после clean migration

Новый репозиторий: `GoToValhalla/City-GO`.

### CI

Файл: `.github/workflows/ci.yml`

Триггеры:

```text
push в main
pull_request в main
manual workflow_dispatch
```

Concurrency:

```text
ci-${{ github.ref }}
cancel-in-progress: true
```

Это отменяет старый незавершённый CI для той же ветки, если пришёл новый push.

### Backend tests job

Job: `backend-tests`

Среда:

```text
ubuntu-latest
Python 3.11
DATABASE_URL=sqlite:///./ci_test.db
```

Шаги:

```text
checkout
setup-python с pip cache
pip install -r requirements.txt
pip install -r requirements-dev.txt
python -m pytest -q --no-cov
```

Важно: backend CI намеренно запускается с `--no-cov`, потому что в `pytest.ini` сейчас включён исторический `--cov-fail-under=75`, а фактически подтверждённый локальный полный прогон после миграции:

```text
694 passed, 4 skipped
```

Coverage gate нужно возвращать отдельной задачей после пересмотра покрытия, иначе CI будет падать не из-за поломки тестов, а из-за старого порога покрытия.

### Frontend tests job

Job: `frontend-tests`

Среда:

```text
ubuntu-latest
Node.js 20
working-directory: frontend
```

Шаги:

```text
checkout
setup-node с npm cache
npm ci
npm run lint
npm run test
npm run build
```

---

## Ручные workflow

После clean migration опасные prod-команды не должны запускаться автоматически.

Оставлены только ручные workflow-заготовки:

```text
.github/workflows/deploy.yml
.github/workflows/admin-smoke.yml
.github/workflows/city-import.yml
.github/workflows/data-enrichment.yml
```

Текущий принцип:

```text
CI можно запускать автоматически.
Deploy/import/enrichment/admin-smoke — только вручную.
Реальные prod-команды добавляются после переноса секретов и проверки инфраструктуры.
```

---

## Deploy pipeline

Файл: `.github/workflows/deploy.yml`

Текущий статус после clean migration:

```text
manual placeholder
не деплоит на production
не использует старые секреты
не выполняет SSH/docker команды
```

Перед включением реального deploy нужно отдельно:

```text
1. Проверить production server path.
2. Проверить SSH secret.
3. Проверить GHCR/container registry strategy.
4. Проверить ADMIN_API_TOKEN.
5. Проверить DATABASE_URL/production .env.
6. Прогнать manual admin smoke.
7. Только после этого включать реальные deploy steps.
```

---

## Post-deploy health gate для будущего реального deploy

После `docker compose up -d` deploy workflow должен проверять:

```text
GET http://localhost:8000/health
```

Если backend не отвечает — deploy должен падать и печатать:

```text
docker compose ps
docker compose logs backend --tail=100
```

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

Публичные `/api/places`, `/api/cities/available` не требуют Bearer-токена — им нужен только живой backend.

---

## Import-worker на production deploy

`import-worker` — отдельный consumer очереди `admin_city_import`; тяжёлые импорты не
должны выполняться внутри backend/web/API. В `docker-compose.yml` сервис находится
за profile `ops`, но production deploy не включает весь profile целиком.

Сервисы в profile `ops`:

```text
seed
address-backfill
place-enrichment-export
import-worker
```

`seed`, `address-backfill` и `place-enrichment-export` — ручные/одноразовые ops-задачи,
поэтому deploy явно стартует только сервис `import-worker`:

```bash
docker compose up -d --no-deps import-worker
```

После старта workflow проверяет, что container для `import-worker` существует и имеет
Docker state `running`. Если container отсутствует, `exited` или `restarting`, deploy
падает без постановки jobs в очередь и без запуска импорта вручную.

---

## Почему «0 мест» при живом frontend

1. **502 на `/api/*`** — backend в crash-loop. UI показывает «Загрузка…» и пустой список.
2. **API жив, но мало мест** — `seed` даёт только демо-места; основной каталог зависит от OSM/import/enrichment pipeline.

---

## Place Enrichment Export

Рекомендуемый ручной запуск локально/на сервере:

```bash
docker compose run --rm place-enrichment-export
```

С параметрами:

```bash
docker compose run --rm place-enrichment-export \
  python data/scripts/run_place_enrichment_export.py \
    --city zelenogradsk --limit 50 --missing-fields address,photo
```

Результат:

```text
data/exports/place_enrichment/active/<batch_id>/export.csv
```

После clean migration `data/exports/` не хранится в git. Экспортные артефакты должны храниться как runtime/artifacts, а не как исходный код.

---

## Address Recovery Flow

Рекомендуемый оркестратор:

```text
data/scripts/run_address_recovery_flow.py
```

Полный цикл описан в:

```text
docs/architecture/place_address_lifecycle.md
```
