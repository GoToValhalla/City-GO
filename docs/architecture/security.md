# Admin Security — City Go

> Документ описывает текущую модель авторизации admin endpoints (реализована в рамках P0-2, P0-3, P0-6).

---

## Текущая модель (Bearer Token)

### Схема

```
Client → Authorization: Bearer <ADMIN_API_TOKEN> → admin_required → AdminContext → endpoint
```

- Токен читается из заголовка `Authorization: Bearer <token>`.
- Сравнение — `hmac.compare_digest` (защита от timing attack).
- В случае успеха endpoint получает `AdminContext` с фиксированными полями.
- `actor` больше **не** берётся из query-параметров или тела запроса.

### AdminContext

```python
@dataclass(frozen=True)
class AdminContext:
    actor_id: str    # "admin-api" (на этапе Bearer Token)
    actor_role: str  # "admin"
    auth_source: str # "admin_token"
```

На следующем этапе (RBAC) `actor_id` будет содержать идентификатор конкретного пользователя.

---

## Environment Variables

| Переменная       | Описание                              | Обязательна в prod |
|------------------|---------------------------------------|---------------------|
| `ADMIN_API_TOKEN`| Bearer-токен для всех /admin/* endpoints | Да (fail-fast)  |

### Fail-fast в production

В production (`APP_ENV=production`) приложение **не запустится**, если `ADMIN_API_TOKEN` не задан:

```python
if settings.app_env == "production" and not settings.admin_api_token:
    raise RuntimeError("ADMIN_API_TOKEN must be set in production")
```

### Локальная разработка

```bash
export ADMIN_API_TOKEN=dev-local-token-change-me
```

Или в `.env`:
```
ADMIN_API_TOKEN=dev-local-token-change-me
```

---

## Защищённые Endpoints

### `/admin/*` (routers/admin.py)

| Метод | Путь                                 | Действие                        |
|-------|--------------------------------------|---------------------------------|
| GET   | /admin/dashboard                     | Метрики панели                  |
| GET   | /admin/roles                         | Список ролей                    |
| GET   | /admin/cities                        | Список городов                  |
| POST  | /admin/cities/import                 | Создание города + import job    |
| GET   | /admin/cities/{id}/coverage          | Покрытие города                 |
| GET   | /admin/import-jobs                   | Список import jobs              |
| GET   | /admin/import-jobs/{id}              | Конкретный import job           |
| GET   | /admin/places                        | Список мест                     |
| POST  | /admin/places                        | Создание места                  |
| PUT   | /admin/places/{id}                   | Обновление места                |
| POST  | /admin/places/{id}/publish           | Публикация места                |
| POST  | /admin/places/{id}/unpublish         | Снятие с публикации             |
| POST  | /admin/places/{id}/verify            | Верификация места               |
| POST  | /admin/place-images                  | Загрузка фото                   |
| GET   | /admin/routes                        | Список маршрутов                |
| POST  | /admin/routes                        | Создание маршрута               |
| PUT   | /admin/routes/{id}                   | Обновление маршрута             |
| PUT   | /admin/routes/{id}/points            | Замена точек маршрута           |
| POST  | /admin/routes/{id}/publish           | Публикация маршрута             |
| POST  | /admin/routes/{id}/unpublish         | Снятие маршрута с публикации    |
| GET   | /admin/route-feedback                | Feedback по маршрутам           |
| GET   | /admin/audit-log                     | Просмотр audit log              |

### `/admin/place-images/*` (routers/place_image_review.py)

| Метод | Путь                                    | Действие              |
|-------|-----------------------------------------|-----------------------|
| GET   | /admin/place-images/pending             | Очередь проверки      |
| POST  | /admin/place-images/{id}/approve        | Одобрить фото         |
| POST  | /admin/place-images/{id}/reject         | Отклонить фото        |
| POST  | /admin/place-images/{id}/set-primary    | Сделать фото основным |

### `/admin/place-verifications/*` (routers/place_verification.py)

| Метод | Путь                                              | Действие                      |
|-------|---------------------------------------------------|-------------------------------|
| GET   | /admin/place-verifications/queue                  | Очередь верификации           |
| POST  | /admin/place-verifications/places/{id}/verify     | Верификация места             |
| POST  | /admin/place-verifications/places/{id}/confirm-nearby | Подтверждение по геолокации |
| GET   | /admin/place-verifications/stats                  | Статистика верификации        |

### `/place-verification/*` — admin write endpoints (routers/place_verification.py)

| Метод | Путь                                        | Действие                            |
|-------|---------------------------------------------|-------------------------------------|
| POST  | /place-verification/enqueue-stale/{city}    | Поставить устаревшие места в очередь |

> Закрыт в P0-2A. Пишет в БД (`PlaceVerificationTask`), запускает DB-scan всех мест города.
> Остальные endpoints этого router (`GET /queue`) остаются публичными (read-only).

---

## Публичные Endpoints (без auth)

Следующие endpoints остаются открытыми и не требуют авторизации:

- `GET /places/*` — публичный каталог мест
- `GET /cities/*` — публичный каталог городов
- `POST /recommendations/*` — рекомендации маршрутов
- `POST /user-routes/*` — построение маршрутов пользователем
- `POST /user-signals/*` — сигналы пользователя
- `GET /place-verification/queue` — публичная очередь верификации (read-only)
- `GET /place-verification/queue` — список pending tasks (read-only)
- `GET /health`, `GET /ready` — health-check

> `POST /place-verification/enqueue-stale/{city}` — **закрыт** (P0-2A).
> Был публичным, но пишет в БД → перемещён в admin-only.

---

## Deprecated поля (игнорируются, не используются в audit)

Следующие поля в request body/query **приняты для backward compat, но игнорируются** при записи audit log — actor всегда берётся из `AdminContext`:

| Схема                         | Поле       | Статус        |
|-------------------------------|------------|---------------|
| `AdminActionRequest`          | `actor`    | deprecated    |
| `AdminUnpublishRequest`       | `actor`    | deprecated    |
| `AdminCityCreateRequest`      | `actor`    | deprecated    |
| `AdminRouteCreateRequest`     | `actor`    | deprecated    |
| `AdminRouteUpdateRequest`     | `actor`    | deprecated    |
| `AdminRoutePointsUpdateRequest`| `actor`   | deprecated    |
| `AdminPlaceImageCreateRequest`| `actor`    | deprecated    |
| `PlaceImageReviewAction`      | `reviewer` | deprecated    |
| `PlaceVerificationRequest`    | `verifier` | deprecated    |
| `PlaceNearbyConfirmRequest`   | `verifier` | deprecated    |

---

## Audit Log

Каждое admin write-действие записывает событие в таблицу `admin_audit_logs`.

---

## Admin API Error Contract

Каждый HTTP-ответ проходит через request logging middleware и получает заголовок:

```http
X-Request-ID: <request-id>
```

Если клиент передал `X-Request-ID`, backend сохраняет его. Иначе генерируется новый идентификатор.

Unhandled backend errors возвращаются как JSON, а не HTML:

```json
{
  "error": "unhandled_request_exception",
  "request_id": "req-123",
  "method": "GET",
  "path": "/admin/example",
  "exception_type": "RuntimeError",
  "message": "..."
}
```

Frontend admin client обязан показывать:

- HTTP method;
- endpoint;
- status;
- requestId, если он есть в header/body;
- короткое сообщение backend.

Сообщение “backend недоступен” допустимо только для network error без HTTP-ответа.

### Структура события

| Поле          | Описание                                          |
|---------------|---------------------------------------------------|
| `actor`       | Из `AdminContext.actor_id` (не из запроса)        |
| `action`      | Название действия (`publish_place`, `approve_place_image`, ...) |
| `entity_type` | Тип сущности (`place`, `route`, `place_image`)    |
| `entity_id`   | ID сущности                                       |
| `old_value`   | Состояние до изменения (если доступно)            |
| `new_value`   | Состояние после изменения                         |
| `created_at`  | Timestamp события                                 |

### Покрытие audit events

| Действие                | old_state | new_state |
|-------------------------|-----------|-----------|
| create_place            | —         | ✓         |
| update_place            | ✓         | ✓         |
| publish_place           | ✓         | ✓         |
| unpublish_place         | ✓         | ✓         |
| verify_place            | ✓         | ✓         |
| create_place_image      | —         | ✓         |
| approve_place_image     | ✓         | ✓         |
| reject_place_image      | ✓         | ✓         |
| set_primary_place_image | —         | ✓         |
| create_route            | —         | ✓         |
| update_route            | ✓         | ✓         |
| replace_route_points    | ✓         | ✓         |
| publish_route           | ✓         | ✓         |
| unpublish_route         | ✓         | ✓         |
| create_city_import_request | —      | ✓         |

---

## Как вызывать admin endpoints

```bash
# Пример: получить dashboard
curl -H "Authorization: Bearer $ADMIN_API_TOKEN" \
     https://api.citygo.app/admin/dashboard

# Пример: опубликовать место
curl -X POST \
     -H "Authorization: Bearer $ADMIN_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"reason": "Проверено вручную"}' \
     https://api.citygo.app/admin/places/123/publish

# Пример: одобрить фото
curl -X POST \
     -H "Authorization: Bearer $ADMIN_API_TOKEN" \
     https://api.citygo.app/admin/place-images/456/approve
```

---

## Ограничения текущего решения

1. **Один общий токен** — нет разделения по пользователям. Все admin-действия записываются с `actor_id = "admin-api"`.
2. **Нет ротации токена** — компрометация токена требует ручной ротации и рестарта сервиса.
3. **Нет object-level auth** — любой с токеном может изменить любой объект.
4. **Нет rate limiting** на admin endpoints.
5. **HTTP transport** — токен виден в незашифрованном трафике (важно использовать HTTPS).

---

## Следующие шаги (после текущего слоя)

### P1: Улучшения
- Добавить ротацию токена без рестарта (список токенов).
- Логировать IP-адрес и user-agent в audit log.
- Добавить `/admin/audit-log` с фильтрами по actor, entity, дате.

### P2: RBAC
- Ввести таблицу `admin_users` с ролями.
- Заменить Bearer token → JWT или session-based auth.
- Раздельные разрешения: `places:write`, `routes:write`, `images:approve`.

### P3: Object-level auth
- Проверка права доступа к конкретному городу/месту.
- Multi-tenant модель (редактор может менять только свой город).
