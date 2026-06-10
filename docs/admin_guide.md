# City Go — руководство по админке

Дата обновления: 2026-06-07.

Документ описывает отдельную админку City Go, backend API, рабочие процессы публикации, модерации фото, редактирования карточек, маршрутов, аудита и добавления города. Документ нужен разработке, QA и DevOps.

---

## 1. Назначение админки

Админка управляет тем, что попадает в публичный продукт:

- какие города опубликованы;
- какие места видны пользователю;
- какие места можно использовать в маршрутах;
- какие фото подтверждены;
- какие карточки мест заполнены и проверены;
- какие маршруты активны;
- какие данные требуют перепроверки;
- какие изменения сделал администратор.

Админка — отдельный frontend-проект в папке `admin/`.

---

## 2. Запуск админки

Локально:

```bash
cd admin
npm install
npm run dev
```

По умолчанию admin frontend обращается к backend:

```text
http://127.0.0.1:8000
```

Для другого backend:

```bash
VITE_API_BASE_URL=https://example.com npm run dev
```

Сборка:

```bash
cd admin
npm run build
```

Тесты:

```bash
cd admin
npm run test
```

---

## 3. Backend endpoints админки

### Dashboard

```text
GET /admin/dashboard
```

Показывает:

- города всего;
- опубликованные города;
- места всего;
- опубликованные места;
- скрытые места;
- места без фото;
- места с низкой достоверностью;
- фото на проверке;
- маршруты всего;
- активные маршруты;
- события аудита.

### Города

```text
GET /admin/cities
POST /admin/cities/import
```

`POST /admin/cities/import` создаёт город и ставит задачу на автоматический сбор мест и фото.

Payload:

```json
{
  "name": "Калининград",
  "country": "Россия",
  "region": "Калининградская область",
  "timezone": "Europe/Kaliningrad",
  "center_lat": 54.7104,
  "center_lng": 20.4522,
  "radius_km": 15,
  "actor": "admin"
}
```

Правила:

- город создаётся в `launch_status = importing`;
- `is_active = false`;
- город не публикуется автоматически;
- после импорта нужны ревью мест и фото.

### Import jobs

```text
GET /admin/import-jobs
GET /admin/import-jobs/{city_id}
```

Показывает состояние city import:

- city id;
- city slug;
- city name;
- статус;
- количество мест;
- количество опубликованных мест;
- количество неопубликованных мест;
- фото на проверке;
- следующий шаг.

Текущий endpoint использует city/import state как лёгкий job status. Полноценный async worker должен быть следующим расширением.

### Места

```text
GET /admin/places
POST /admin/places
PUT /admin/places/{place_id}
POST /admin/places/{place_id}/publish
POST /admin/places/{place_id}/unpublish
POST /admin/places/{place_id}/verify
```

Фильтры списка:

```text
city_slug
publication_status
verification_status
q
limit
offset
```

### Фото

```text
POST /admin/place-images
GET /admin/place-images/pending
POST /admin/place-images/{image_id}/approve
POST /admin/place-images/{image_id}/reject
POST /admin/place-images/{image_id}/set-primary
```

Правило:

```text
area_photo и category_photo нельзя показывать как точное фото места.
```

Ручное добавление фото:

```json
{
  "place_id": 1,
  "image_url": "https://example.com/photo.jpg",
  "source_type": "manual_upload",
  "source_url": "https://example.com",
  "attribution": "Example",
  "license": "CC BY-SA",
  "confidence": 0.8,
  "actor": "admin",
  "comment": "Фото добавлено вручную"
}
```

После ручного добавления:

```text
status = needs_review
```

Фото публикуется только после approve.

### Маршруты

```text
GET /admin/routes
POST /admin/routes
PUT /admin/routes/{route_id}
PUT /admin/routes/{route_id}/points
POST /admin/routes/{route_id}/publish
POST /admin/routes/{route_id}/unpublish
```

Админ может:

- создать editorial route;
- редактировать карточку маршрута;
- менять точки маршрута;
- публиковать маршрут;
- снимать маршрут с публикации.

Пример замены точек маршрута:

```json
{
  "actor": "admin",
  "reason": "Ручная сборка маршрута",
  "points": [
    {"place_id": 10, "position": 1},
    {"place_id": 15, "position": 2}
  ]
}
```

### Audit log

```text
GET /admin/audit-log
```

Логируются:

- actor;
- action;
- entity_type;
- entity_id;
- old_value;
- new_value;
- reason;
- created_at.

### Place enrichment (обогащение данных мест)

```text
POST /admin/place-enrichment/export
GET  /admin/place-enrichment/batches
GET  /admin/place-enrichment/exports
GET  /admin/place-enrichment/exports/{batch_id}/download
GET  /admin/place-enrichment/batches/{batch_id}/files/{filename}
POST /admin/place-enrichment/batches/{batch_id}/preview
POST /admin/place-enrichment/batches/{batch_id}/apply
```

UI: `/admin/place-enrichment` (встроенная админка в `frontend/`, см. `docs/architecture/admin_frontend.md`).

Workflow:

1. Export → `data/exports/place_enrichment/active/<batch_id>/export.csv`
2. Обогащение в ChatGPT → `enriched.csv` в той же папке
3. Preview → `import.preview.json` (без изменений БД)
4. Apply → обновление Place + audit + перенос batch в `archive/`

Подробнее: `docs/architecture/place_data_enrichment.md`, `data/exports/place_enrichment/README.md`.

---

## 4. Публикация и снятие места

У места есть отдельные поля публикации:

```text
is_published
is_visible_in_catalog
is_route_eligible
is_searchable
publication_status
publication_comment
published_at
unpublished_at
```

### Опубликовать место

```text
POST /admin/places/{place_id}/publish
```

После публикации:

```text
is_active = true
status = active
is_published = true
is_visible_in_catalog = true
is_searchable = true
is_route_eligible = true
publication_status = published
```

### Снять место с публикации

```text
POST /admin/places/{place_id}/unpublish
```

Причина обязательна.

После снятия:

```text
is_published = false
is_visible_in_catalog = false
is_searchable = false
is_route_eligible = false
publication_status = unpublished
```

Место не удаляется из БД.

---

## 5. Проверка места и рейтинг достоверности

```text
POST /admin/places/{place_id}/verify
```

После подтверждения:

```text
verification_status = verified
existence_confidence_level = high
existence_confidence_score >= 90
verified_by = actor
verified_at = now
```

Place confidence не равен photo confidence.

---

## 6. Логика добавления/обновления города для DevOps

### 6.1. Добавление города из админки

1. Админ вводит название города.
2. Admin frontend вызывает `POST /admin/cities/import`.
3. Backend создаёт город:
   - `launch_status = importing`;
   - `is_active = false`.
4. Backend пишет audit event `create_city_import_request`.
5. Система должна запустить сбор мест и фото.
6. После сбора город переводится в `imported` или `review_required`.
7. Админ проверяет места, фото, coverage.
8. Только после ревью город можно публиковать.

### 6.2. Что должен сделать production worker

Worker/DevOps job должен выполнять:

1. Получить город со статусом `importing`.
2. Определить координаты города, если они не заданы.
3. Запустить OSM/import pipeline.
4. Запустить image enrichment pipeline.
5. Создать места в статусе draft/unpublished/needs_review.
6. Создать фото-кандидаты в `needs_review`.
7. Посчитать coverage.
8. Обновить city status:
   - `imported`, если импорт успешен;
   - `review_required`, если есть данные, но нужна ручная проверка;
   - `import_failed`, если сбор упал.
9. Записать audit/import log.

### 6.3. Важные ограничения

- Новый город не должен публиковаться автоматически.
- Новые места не должны публиковаться автоматически.
- Фото не должно становиться публичным без approve.
- Area/category фото нельзя показывать как exact photo.
- Ошибочный импорт должен быть обратим через будущий rollback batch.

---

## 7. Тесты

Backend:

```bash
python -m pytest tests/test_admin_router_full.py tests/test_place_image_review_router.py
```

Frontend admin:

```bash
cd admin
npm run test
npm run build
```

---

## 8. Что ещё нужно развить дальше

- Реальная авторизация админки.
- Роли: admin/editor/moderator/viewer.
- Полноценный async import job worker.
- Rollback import batch.
- Upload файлов фото, а не только URL.
- Coverage page города.
- Route analytics UI.
- Moderation dashboard.
- Полный route editor UI с drag-and-drop точек.
