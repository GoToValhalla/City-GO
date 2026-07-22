# City Go — Admin: добавление, импорт и готовность города

Дата актуализации: 2026-06-10.

Документ описывает рабочую логику админки для добавления нового города, запуска city onboarding pipeline, обновления данных и проверки готовности города.

---

## 1. Компоненты

### Backend admin API

Основной backend City Go обслуживает admin API:

```text
/admin/dashboard
/admin/cities
/admin/cities/import
/admin/import-jobs
/admin/import-jobs/{city_id}
/admin/places
/admin/places/address-refresh
/admin/routes/data-quality/{city_slug}
/admin/routes/readiness
/admin/routes/readiness/{city_slug}
/admin/routes/dry-run
/admin/audit-log
/admin/system-logs
```

### Admin frontend

Текущая админка находится в:

```text
frontend/src/pages/admin
```

Ключевые страницы:

```text
/admin/cities
/admin/imports
/admin/routes/data-quality
/admin/routes/readiness
/admin/routes/dry-run
/admin/places
```

---

## 2. City Onboarding Pipeline

Целевой рабочий сценарий:

1. Админ открывает **Города**.
2. Вводит название города на кириллице или латинице.
3. Указывает регион, страну, timezone и радиус сбора.
4. Нажимает **Создать город и собрать места**.
5. Backend создаёт город и ставит import job в очередь.
6. Worker собирает места из источников.
7. Система сохраняет места, категории, координаты и базовые поля.
8. После импорта админ проверяет:
   - `/admin/imports`;
   - `/admin/routes/data-quality?city=<slug>`;
   - `/admin/routes/readiness/<slug>`;
   - `/admin/routes/dry-run`.
9. Админ запускает адресное обогащение, фото/описания и cleanup eligibility.
10. Город публикуется только после readiness review.

---

## 3. UI-сценарий добавления города

Страница:

```text
/admin/cities
```

Компонент:

```text
frontend/src/pages/admin/AdminCityCreateForm.tsx
```

Форма показывает этапы pipeline:

```text
1. Создание города
2. Постановка import job
3. Сбор мест из источников
4. Сохранение мест
5. Очередь адресов и фото
6. Data Quality report
7. City Readiness
```

После успешного создания форма показывает ссылки:

```text
/admin/imports
/admin/routes/data-quality?city=<city_slug>
/admin/routes/readiness/<city_slug>
```

---

## 4. Backend-сценарий

Frontend вызывает:

```text
POST /admin/cities/import
```

Пример payload:

```json
{
  "name": "Алматы",
  "country": "Казахстан",
  "region": "Алматинская область",
  "timezone": "Asia/Almaty",
  "radius_km": 15
}
```

Backend делает:

1. Нормализует название города.
2. Создаёт slug.
3. Создаёт город.
4. Создаёт import job (`status="queued"`).
5. Возвращает `queued`.

Endpoint только ставит задачу в очередь и не выполняет импорт сам —
ни синхронно, ни через FastAPI `BackgroundTasks`. Единственный
исполнитель очереди — import worker
(`data/scripts/run_admin_import_worker.py`, ops-профиль в
`docker-compose.yml`). Он забирает задачу через `claim_queued_job`
и запускает пайплайн отдельно от API-процесса, со своими лимитами
памяти/времени выполнения и наблюдаемостью.

Response:

```json
{
  "city_id": 1,
  "city_slug": "almaty",
  "city_name": "Алматы",
  "job_status": "queued",
  "message": "Город создан. Задача на автоматический сбор мест и фото поставлена в очередь.",
  "next_step": "Проверить import job, затем открыть очередь мест и фото на модерацию."
}
```

Важно:

```text
Город не должен считаться готовым автоматически после создания.
```

---

## 5. Import worker

После `POST /admin/cities/import`:

1. Создаётся import job (`status="queued"`).
2. Import worker (отдельный процесс/контейнер) забирает задачу через
   `claim_queued_job` и выполняет пайплайн — не API-сервер.
3. Worker должен собрать места и сохранить промежуточный статус.
4. Статус смотреть в `/admin/imports`.
5. Ошибки смотреть в `/admin/system-logs`.

Ожидаемая production-логика worker:

1. Определить координаты города, если они не заданы.
2. Собрать места из доступных источников:
   - OSM;
   - Wikidata;
   - Wikimedia Commons;
   - official website metadata;
   - area/category photo sources, если доступны.
3. Нормализовать категории.
4. Удалить дубли.
5. Сохранить места.
6. Сохранить фото как pending/review.
7. Запустить адресное обогащение для low-confidence адресов.
8. Построить Data Quality report.
9. Построить City Readiness report.

---

## 6. Data Quality после импорта

Страница:

```text
/admin/routes/data-quality?city=<city_slug>
```

Показывает:

- всего мест;
- eligible / not eligible;
- места без фото;
- места без адреса;
- места без описания;
- forbidden categories;
- quality buckets;
- issues.

Действия:

- открыть места без фото;
- открыть места без адреса;
- открыть места без описания;
- поставить обновление адресов по городу в очередь;
- перейти в Eligibility по forbidden category.

Backend cleanup endpoint:

```text
POST /admin/routes/data-quality/{city_slug}/exclude-forbidden-categories
```

Требует:

```json
{ "confirm": true }
```

Действие:

```text
Для всех мест города с категорией из ROUTE_FORBIDDEN_CATEGORIES выставляет is_route_eligible = false.
```

---

## 7. City Readiness

Страницы/API:

```text
GET /admin/routes/readiness
GET /admin/routes/readiness/{city_slug}
```

Readiness нужен, чтобы не публиковать сырой город.

Минимальные сигналы readiness:

- достаточное количество мест;
- доля route eligible мест;
- покрытие фото;
- покрытие адресами;
- покрытие описаниями;
- отсутствие критичного количества forbidden categories;
- успешный dry-run маршрута.

Статусы:

```text
ready
needs_review
not_ready
```

---

## 8. Dry Run после импорта

Страница:

```text
/admin/routes/dry-run
```

Сейчас показывает:

- selected candidates;
- rejected candidates;
- counts;
- quality status;
- quality score;
- warnings;
- quality breakdown;
- SVG mini-map selected-точек с numbered markers и линией.

Dry Run обязателен перед публикацией города.

---

## 9. Публикация мест

Место считается видимым в публичном продукте только если:

```text
is_published = true
is_visible_in_catalog = true
is_searchable = true
status = active
is_active = true
```

Для участия в route builder дополнительно:

```text
is_route_eligible = true
```

Массовые admin actions должны менять именно `is_route_eligible`, а не legacy/non-existing поля.

---

## 10. Definition of Done для нового города

Город можно считать готовым к пользовательскому тесту, если:

1. Import job завершён без критической ошибки.
2. В городе есть достаточный пул мест.
3. Data Quality показывает приемлемое покрытие адресами, фото и описаниями.
4. Forbidden categories исключены из маршрутов.
5. City Readiness не ниже `needs_review`.
6. Admin Dry Run строит маршрут не ниже `acceptable` или понятно объясняет `weak`.
7. В админке есть понятные ссылки на проблемные места.
8. Город не публикуется автоматически без review.

---

## 11. Gaps

- Нужен локальный прогон tests/build.
- Нужен production-safe worker для полного enrichment pipeline.
- Нужна отдельная очередь фото/описаний, если текущий import worker не покрывает их стабильно.
- Нужен deploy workflow, отделённый от CI workflow.
