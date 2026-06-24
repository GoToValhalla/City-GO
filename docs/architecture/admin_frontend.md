# Admin Frontend — City Go

Операционный слой использует единый `adminApi`, URL-driven filters и backend-driven
state. City Workspace фиксирует город и ведёт в существующие операционные выборки.
Общий `AdminConfirmDialog` заменяет browser confirm/prompt. Контракт экранов описан
в `docs/admin_operational_center.md`.

## Как открыть

Перейти по адресу `/admin/login` и ввести логин и пароль.

---

## Credentials (ВРЕМЕННЫЕ — поменяй перед деплоем)

| Что | Файл | Переменная |
|-----|------|------------|
| Логин | `frontend/src/pages/admin/adminCredentials.ts` | `ADMIN_LOGIN` |
| Пароль | `frontend/src/pages/admin/adminCredentials.ts` | `ADMIN_PASSWORD` |
| API-токен | build variable `VITE_ADMIN_API_TOKEN` | `frontend/src/pages/admin/adminToken.ts` |

**`VITE_ADMIN_API_TOKEN` (frontend build) должен совпадать с `ADMIN_API_TOKEN` в backend `.env`.**

Ручная настройка production: `docs/operations/admin_api_token_manual_setup.md`.

После изменения login/password — `npm run build`. Токен задаётся при сборке (Docker build-arg / `.env.local`).

---

## Страницы

| URL | Компонент | Backend endpoint |
|-----|-----------|-----------------|
| `/admin/login` | `AdminLoginPage` | нет (локальная проверка) |
| `/admin` | redirect → `/admin/dashboard` | — |
| `/admin/dashboard` | `AdminDashboardPage` | `GET /admin/dashboard` |
| `/admin/places` | `AdminPlacesPage` | `GET /admin/places` + publish/unpublish/verify |
| `/admin/place-images` | `AdminPlaceImagesPage` | `GET /admin/place-images/pending` + approve/reject/set-primary |
| `/admin/place-verifications` | `AdminPlaceVerificationsPage` | `GET /admin/place-verifications/queue` + stats + verify |
| `/admin/import-jobs` | `AdminImportJobsPage` | `GET /admin/import-jobs` + `/admin/import-jobs/{city_id}` |
| `/admin/coverage` | `AdminCoveragePage` | `GET /admin/cities` + `GET /admin/cities/{id}/coverage` |
| `/admin/audit-log` | `AdminAuditLogPage` | `GET /admin/audit-log` |
| `/admin/place-enrichment` | `AdminPlaceEnrichmentPage` | Export, batch list, Preview/Apply import, file downloads |

---

## Архитектура

```
frontend/src/pages/admin/
  adminCredentials.ts         — TEMPORARY hardcoded login/password
  adminToken.ts               — Bearer token из VITE_ADMIN_API_TOKEN (build variable)
  adminSession.ts             — localStorage session (save/clear/has)
  adminApi.ts                 — HTTP client с Bearer auth, auto-logout на 401/403
  adminTypes.ts               — TypeScript типы для всех admin API ответов
  Admin.css                   — стили admin shell
  AdminLoginPage.tsx          — страница входа
  AdminRouteGuard.tsx         — защита маршрутов (redirect → /admin/login)
  AdminLayout.tsx             — sidebar + topbar + logout
  AdminDashboardPage.tsx      — сводка метрик
  AdminPlacesPage.tsx         — список мест с фильтрами и action-кнопками
  useAdminPlacesList.ts       — пагинация: limit=50, reload + loadMore
  AdminPlacesLoadSentinel.tsx — IntersectionObserver, подпись «Показано X из Y»
  AdminPlaceImagesPage.tsx    — очередь фото (pending/approve/reject/set-primary)
  AdminPlaceVerificationsPage.tsx — верификация мест (очередь + статистика)
  AdminImportJobsPage.tsx     — задачи импорта + детали по городу
  AdminCoveragePage.tsx       — покрытие данных по городам
  AdminAuditLogPage.tsx       — журнал аудита
  AdminPlaceEnrichmentPage.tsx — export + ChatGPT path hint + batch table
  AdminEnrichmentBatchTable.tsx — batch list, Preview/Apply import, file downloads
  adminEnrichmentTypes.ts     — EnrichmentBatchMeta, ImportPreview/Apply types
  adminEnrichmentForm.ts      — хук формы экспорта
  adminEnrichmentHelpers.ts   — batchFileUrl, STATUS_LABEL
  adminEnrichment_new.test.tsx — тесты place-enrichment UI
  adminAuth_new.test.tsx      — тесты: session/guard/login/api
```

---

## Auth-схема

1. Пользователь вводит `ADMIN_LOGIN` / `ADMIN_PASSWORD` на `/admin/login`
2. Frontend сравнивает с hardcoded значениями из `adminCredentials.ts`
3. При совпадении: `saveAdminSession()` → `localStorage.setItem('city_go_admin_session', '1')`
4. Redirect → `/admin/dashboard`
5. Все запросы к backend через `adminApi.ts` добавляют `Authorization: Bearer <VITE_ADMIN_API_TOKEN>`
6. Backend проверяет токен через `hmac.compare_digest` (защита timing attack)
7. При 401/403: `clearAdminSession()` + redirect на `/admin/login`
8. При 503: сообщение «ADMIN_API_TOKEN не настроен» (backend `.env`)

---

## Backend endpoints — статус

### ✅ Реализованы и используются
- `GET /admin/dashboard`
- `GET /admin/places` (с фильтрами: city_slug, publication_status, q; `limit`/`offset` для подгрузки)
- `POST /admin/places/{id}/publish`
- `POST /admin/places/{id}/unpublish`
- `POST /admin/places/{id}/verify`
- `GET /admin/place-images/pending`
- `POST /admin/place-images/{id}/approve`
- `POST /admin/place-images/{id}/reject`
- `POST /admin/place-images/{id}/set-primary`
- `GET /admin/place-verifications/queue`
- `GET /admin/place-verifications/stats`
- `POST /admin/place-verifications/places/{id}/verify`
- `POST /admin/place-verifications/places/{id}/confirm-nearby`
- `GET /admin/import-jobs`
- `GET /admin/import-jobs/{city_id}`
- `GET /admin/cities`
- `GET /admin/cities/{id}/coverage`
- `GET /admin/audit-log`
- `POST /admin/place-enrichment/export`
- `GET /admin/place-enrichment/batches`
- `GET /admin/place-enrichment/exports`
- `GET /admin/place-enrichment/exports/{id}/download`
- `GET /admin/place-enrichment/batches/{id}/files/{filename}`
- `POST /admin/place-enrichment/batches/{id}/preview`
- `POST /admin/place-enrichment/batches/{id}/apply`

### ℹ️ Существуют в backend, но не вынесены в отдельные страницы (не в scope)
- `GET /admin/roles` — справочная информация
- `POST /admin/cities/import` — запуск импорта
- `POST /admin/places` — создание места
- `PUT /admin/places/{id}` — редактирование места
- `GET /admin/routes` — список маршрутов
- `POST/PUT /admin/routes/*` — управление маршрутами
- `GET /admin/route-feedback`

---

## Ограничения временной модели

1. **Credentials в коде** — `ADMIN_LOGIN`, `ADMIN_PASSWORD`, `ADMIN_API_TOKEN` хранятся в `adminCredentials.ts`. После `npm run build` попадают в JS bundle.
2. **Нет session expiry** — сессия живёт в localStorage до явного logout или очистки браузера.
3. **Нет RBAC** — все действия доступны любому авторизованному пользователю.
4. **Один токен** — `ADMIN_API_TOKEN` общий для всех пользователей.

## Что заменить в production

| Сейчас | Заменить на |
|--------|------------|
| Hardcoded credentials в `adminCredentials.ts` | Переменные окружения + backend login endpoint |
| localStorage session | HTTP-only cookie / JWT |
| Один API token | Per-user tokens или OAuth |
| Нет logout на backend | Invalidatable tokens |

---

## Тесты

```bash
cd frontend
npx vitest run src/pages/admin/adminAuth_new.test.tsx
```

Покрывают: session storage, route guard, login form validation, API Bearer header.

## Build

```bash
cd frontend && npm run build  # проверено — ошибок нет
```
