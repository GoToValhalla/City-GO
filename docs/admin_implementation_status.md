# City Go — статус реализации админки

Дата: 2026-06-06.

## Реализовано

### Backend admin API

Добавлены и расширены endpoints:

```text
GET /admin/dashboard
GET /admin/cities
POST /admin/cities/import
GET /admin/import-jobs
GET /admin/import-jobs/{city_id}
GET /admin/places
POST /admin/places
PUT /admin/places/{place_id}
POST /admin/places/{place_id}/publish
POST /admin/places/{place_id}/unpublish
POST /admin/places/{place_id}/verify
POST /admin/place-images
GET /admin/place-images/pending
POST /admin/place-images/{image_id}/approve
POST /admin/place-images/{image_id}/reject
POST /admin/place-images/{image_id}/set-primary
GET /admin/routes
POST /admin/routes
PUT /admin/routes/{route_id}
PUT /admin/routes/{route_id}/points
POST /admin/routes/{route_id}/publish
POST /admin/routes/{route_id}/unpublish
GET /admin/audit-log
```

### Отдельная админка

Отдельное приложение находится в папке:

```text
admin/
```

Интерфейс на русском языке.

Разделы:

```text
Дашборд
Города
Места
Фото
Маршруты
Аудит
```

### Места

Реализовано:

- список мест;
- ручное добавление места;
- публикация места;
- снятие места с публикации;
- подтверждение существования места;
- отображение publication status;
- отображение рейтинга достоверности.

### Фото

Реализовано:

- ручное добавление фото по URL;
- добавление фото в очередь проверки;
- список фото на проверке;
- подтверждение фото;
- отклонение фото;
- установка primary через существующий endpoint.

### Города

Реализовано:

- список городов;
- создание города через админку;
- постановка города в import flow;
- список import jobs;
- detail import job по city_id.

Важно: текущий backend создаёт import request и фиксирует статус. Реальный worker сбора мест и фото должен быть подключён DevOps отдельно.

### Маршруты

Реализовано:

- список маршрутов;
- создание editorial route;
- редактирование маршрута через backend endpoint;
- замена точек маршрута через backend endpoint;
- публикация маршрута;
- снятие маршрута.

### Audit log

Реализовано логирование:

- создание города;
- создание места;
- редактирование места;
- публикация места;
- снятие места;
- подтверждение места;
- добавление фото;
- создание маршрута;
- редактирование маршрута;
- замена точек маршрута;
- публикация маршрута;
- снятие маршрута.

### Тесты

Добавлен файл:

```text
tests/test_admin_router_full.py
```

Проверяет:

- dashboard;
- city import;
- import jobs;
- publish/unpublish place;
- audit log;
- manual photo creation;
- photo review queue;
- route creation;
- route points replacement;
- publish/unpublish route.

## Документация

Добавлен DevOps-документ:

```text
docs/admin_city_operations.md
```

Он описывает:

- запуск админки;
- backend endpoints;
- добавление города;
- import flow;
- подключение реального worker;
- публикацию мест;
- работу с фото;
- работу с маршрутами;
- audit log;
- production deployment notes;
- проверки перед публикацией города.

## Что требует отдельного инфраструктурного подключения

- реальный import worker;
- cron/scheduler обновления городов;
- storage для файловых upload фото;
- reverse proxy protection или полноценная auth;
- CORS для admin domain;
- monitoring import failures;
- rollback import batch.
