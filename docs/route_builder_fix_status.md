# City Go — статус исправления route builder

Дата: 2026-06-06.

Документ фиксирует, что уже реализовано из плана исправления маршрутов и что осталось делать дальше.

---

## 1. Уже было реализовано до текущего изменения

### Route statuses

В backend уже есть статусы маршрута:

```text
ready
partial_route
no_route
```

Файл:

```text
services/route_status_service.py
```

Логика:

- `0` точек → `no_route`;
- меньше минимально ожидаемого количества точек → `partial_route`;
- достаточно точек → `ready`.

### Quality score completeness

В quality score уже есть `completeness` penalty.

Файл:

```text
services/route_quality_score.py
```

Маршрут из одной точки больше не должен считаться полноценным отличным маршрутом, если ожидалось несколько точек.

### Route time mode

В request/context уже есть поле:

```text
route_time_mode
```

Default:

```text
flexible
```

Файлы:

```text
schemas/user_route.py
services/context_merge_service.py
schemas/merged_context.py
services/user_route_context.py
```

### Opening hours hard filter

`closed_now` уже не применяется как hard filter, если режим не `now`.

Файл:

```text
services/route_filter_reasons.py
```

---

## 2. Реализовано текущим изменением

### Assembly fallback

Файл:

```text
services/route_assembly_optimizer.py
```

Проблема:

```text
40 кандидатов → 13 прошли фильтры → assembly выбрал 1 точку
```

Что изменено:

1. Assembly budget теперь берётся как максимум между effective budget и 90% явного бюджета пользователя.
2. Если маршрут остаётся короче минимума, assembly пробует ослабить category constraints.
3. Если этого мало, assembly один раз расширяет remaining budget до 120% пользовательского бюджета.
4. Это применяется только когда маршрут ещё не достиг минимального количества точек.
5. Если кандидатов нет — маршрут остаётся пустым.

Ожидаемый эффект:

- если есть подходящие кандидаты, маршрут не должен останавливаться на одной точке без попытки добрать вторую;
- partial route остаётся возможным, но только после реальной попытки fallback-сборки.

### Counts на странице мест

Файл:

```text
frontend/src/pages/places/PlacesListPage.tsx
```

Что изменено:

1. Страница теперь вызывает `getPlacesByCityResponse`, а не `getPlacesByCity`.
2. UI хранит `total`, `limit`, `offset` из backend response.
3. Шапка показывает total из places API.
4. Под шапкой показывается текст:

```text
Показано N из Total опубликованных мест.
```

5. При локальном поиске показывается:

```text
Найдено N мест по текущему поиску.
```

### Route candidate diagnostics

Файлы:

```text
services/route_candidate_diagnostics.py
services/route_builder_flow.py
```

В `pipeline_trace` для `candidate_retrieval` добавлены диагностические поля:

```text
city_slug
city_db_id
start_point
radius_meters
places_with_city_id
places_public
places_active
places_route_eligible
places_with_coords
geo_query_count
```

Это нужно, чтобы быстро понять, где обрыв:

- город не тот;
- мест в городе нет;
- места не published;
- места без координат;
- radius не захватывает места;
- frontend отправил старт не в том городе.

### V1 verification API wrapper

Файлы:

```text
routers/verification.py
core/router_setup.py
```

Добавлен публичный v1-контракт поверх существующего place verification service:

```text
GET /v1/verification/queue/{city_slug}
GET /v1/verification/stats/{city_slug}
POST /v1/verification/place/{place_id}/confirm
POST /v1/verification/place/{place_id}/reject
```

Это закрывает минимальный API-контур для будущей мобильной/веб-страницы полевой проверки мест.

---

## 3. Добавлены тесты

### Route assembly

Файл:

```text
tests/test_route_assembly_optimizer_new.py
```

Проверки:

1. Assembly не должен останавливаться на одной точке, если есть второй кандидат и можно применить fallback.
2. Если кандидатов нет, маршрут остаётся пустым.

### Verification API

Файл:

```text
tests/test_verification_router_new.py
```

Проверки:

1. Очередь верификации города возвращает места.
2. Confirm обновляет место до `verified` и confidence `100`.
3. Reject помечает место как `not_found` и выключает `is_active`.
4. Stats возвращает summary по городу.

Запуск:

```bash
python -m pytest tests/test_route_assembly_optimizer_new.py tests/test_verification_router_new.py -v
```

---

## 4. Следующие незакрытые блоки из плана

### P0

1. Проверить city isolation для Ханты-Мансийска:
   - routes;
   - demo catalog;
   - fallback coordinates;
   - localStorage current city.

2. Проверить реальный frontend response после assembly fix:
   - `ready`;
   - `partial_route`;
   - `no_route`.

### P1

1. Новый start context contract:
   - current_location;
   - place;
   - map_point;
   - address;
   - city_center.

2. Start context resolver service.

3. City-start consistency validation.

4. Address/reverse-geocoding quality workflow.

### P2

1. Map point selection.
2. Verification page `/verify/{city_slug}`.
3. Trust score как отдельная агрегированная модель.
4. Route inspector в админке.
