# City Go — гибкое построение маршрута: статус реализации

Дата: 2026-06-06.

Документ фиксирует реализацию первого блока механизма гибкого построения маршрута.

---

## 1. Реализовано сейчас

### Backend contracts

Расширен `schemas/user_route.py`.

Добавлено:

```text
build_mode: auto | by_categories | manual | constructor
start: current_location | place | map_point | address | city_center
```

Добавлены request/response схемы для:

```text
UserRoutePreviewRequest
UserRouteUpdateRequest
UserRouteReplacePlaceRequest
UserRouteAddPlaceRequest
UserRouteAlternativesResponse
UserRouteStructuredBuildRequest
UserRouteStructuredBuildResponse
```

### Новые endpoints

Файл:

```text
routers/user_routes.py
```

Добавлены:

```text
POST /v1/user-routes/preview
POST /v1/user-routes/build-structured
POST /v1/user-routes/{route_id}/update
POST /v1/user-routes/{route_id}/replace-place
GET  /v1/user-routes/{route_id}/alternatives/{place_id}
POST /v1/user-routes/{route_id}/alternatives/{place_id}
POST /v1/user-routes/{route_id}/add-place
```

### Route edit service

Файл:

```text
services/user_route_edit_service.py
```

Реализовано:

- reorder route by `ordered_place_ids`;
- replace one place;
- add place;
- alternatives by same category;
- structured slot options for constructor mode.

Важно:

- пока маршрут stateful-сессией не сохраняется;
- для `GET /alternatives` без persisted route state возвращается пустой ответ;
- для реальной работы alternatives сейчас есть `POST /alternatives`, куда frontend передаёт текущий route state.

### Frontend start selector

Файл:

```text
frontend/src/widgets/recommendation-route/RouteRequestForm.tsx
```

Из пользовательского UI убран ручной ввод `lat/lng`.

Добавлены понятные варианты старта:

```text
От центра города
Использовать мою геолокацию
От адреса
```

Координаты остаются техническим полем внутри payload, но пользователь их руками не вводит.

### Frontend request contract

Файлы:

```text
frontend/src/api/recommendations/recommendationRoute.types.ts
frontend/src/features/routes/model/recommendationRouteForm.ts
```

Добавлены frontend-типы:

```text
RouteBuildMode
RouteStartType
RouteStart
```

`buildRecommendationRouteRequest` теперь формирует `start` object и валидирует start source.

---

## 2. Тесты

Добавлен файл:

```text
tests/test_user_routes_flexible_new.py
```

Покрывает:

- `POST /v1/user-routes/preview`;
- `POST /v1/user-routes/build-structured`;
- `POST /v1/user-routes/{route_id}/update`;
- `POST /v1/user-routes/{route_id}/replace-place`;
- `POST /v1/user-routes/{route_id}/add-place`;
- `POST /v1/user-routes/{route_id}/alternatives/{place_id}`.

Запуск:

```bash
python -m pytest tests/test_user_routes_flexible_new.py -v
```

---

## 3. Что ещё не реализовано из большого документа

### P0 — осталось

1. Полноценный preview screen как отдельное UX-состояние:
   - список точек;
   - итог времени/дистанции;
   - кнопка `Начать маршрут`;
   - inline edit controls.

2. UI для удаления точки и пересборки через новые endpoints.

3. Отображение route status:
   - `ready`;
   - `preview`;
   - `partial_route`;
   - `no_route`.

### P1 — осталось

1. Режим 2: wizard выбора категорий.
2. Режим 3: ручной выбор мест из каталога.
3. Режим 4: constructor slots UI.
4. ACTIVE режим:
   - `Я здесь`;
   - `Пропустить`;
   - visited/skipped.
5. Drag-and-drop порядка точек.
6. UI замены места через alternatives.

### P2 — осталось

1. Карта и polyline.
2. Экран завершения маршрута.
3. Feedback после маршрута.
4. Share route draft.
5. Draft persistence localStorage/DB.
6. Undo последних действий.

---

## 4. Следующий технический шаг

Следующий шаг после текущего изменения:

```text
Сделать frontend preview screen и подключить update/add/replace endpoints к UI.
```

После этого можно переходить к wizard modes.
