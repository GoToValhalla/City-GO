# Prod smoke-checklist админки

## Деплой

1. Push в `master` → GitHub Actions `Build & Deploy`
2. Pipeline: `docker compose pull` → `docker compose up migrate` → exit 0 → `docker compose up -d`
3. При ошибке migrate деплой падает, backend не стартует (`depends_on: migrate: service_completed_successfully`)

## Проверка миграций (без SSH)

- В логах pipeline: `Running upgrade ... a1b2c3d4e5f7`
- `GET /ready` → `database: ok`

## Admin smoke (браузер + токен)

- [ ] `/admin/overview`
- [ ] `/admin/cities` — inline настройки
- [ ] `/admin/places` — фильтры, bulk, ссылка на карточку
- [ ] `/admin/places/new` — создание draft
- [ ] `/admin/places/{id}` — карточка, действия
- [ ] `/admin/coverage`
- [ ] `/admin/routes/eligibility`
- [ ] `/admin/routes/dry-run`
- [ ] `/admin/routes/data-quality`
- [ ] `/admin/routes/readiness` (SPA fallback; API: `GET /admin/routes/readiness`)
- [ ] `/admin/photos`
- [ ] `/admin/verification`
- [ ] `/admin/imports`
- [ ] `/admin/enrichment`
- [ ] `/admin/features`
- [ ] `/admin/metrics`
- [ ] `/admin/audit`
- [ ] `/admin/system-logs`
- [ ] Mobile 375px — burger menu, таблицы скроллятся
- [ ] Нет 422/502, нет HTML-ошибок
- [ ] Toggle сохраняется и влияет на API

## API smoke (curl)

```bash
curl -sf -H "Authorization: Bearer $ADMIN_API_TOKEN" https://<host>/admin/overview
curl -sf -H "Authorization: Bearer $ADMIN_API_TOKEN" https://<host>/admin/places/1/detail
curl -sf -H "Authorization: Bearer $ADMIN_API_TOKEN" "https://<host>/admin/routes/eligibility?limit=5"
curl -sf -H "Authorization: Bearer $ADMIN_API_TOKEN" https://<host>/admin/routes/readiness
curl -sf -X POST -H "Authorization: Bearer $ADMIN_API_TOKEN" -H "Content-Type: application/json" \
  -d '{"city_slug":"<slug>","duration_min":120}' https://<host>/admin/routes/dry-run
```

Автоматический workflow **Prod Admin Smoke** (`.github/workflows/prod-admin-smoke.yml`) дополнительно проверяет:
- наличие строки `Маршруты` в frontend bundle;
- HTTP 200 для SPA `/admin/routes/*`;
- OpenAPI paths `/admin/routes/eligibility`, `/dry-run`, `/data-quality/{city_slug}`, `/readiness`, `/readiness/{city_slug}`.
