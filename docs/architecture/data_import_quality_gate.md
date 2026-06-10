# Import Quality Gate

> Документ описывает автоматическую классификацию импортируемых мест.
> Реализация: `services/import_publication_gate.py`.

---

## Зачем Quality Gate?

После P0-4 все импортируемые места создавались как `draft`. Это безопасно, но
не масштабируется: при импорте 1 000+ мест из OSM каждое требует ручной
проверки. Quality Gate решает это автоматически:

- **Хорошее место** → публикуется без участия человека.
- **Сомнительное место** → ждёт ревью, не видно в каталоге.
- **Плохое место** → скрывается, можно исправить в будущем.

Ручной approve требуется только для `needs_review` мест. `hidden` места
вообще не нужно трогать, пока данные не исправлены.

---

## Решения и результаты

| Решение | `publication_status` | `is_published` | `is_route_eligible` |
|---|---|---|---|
| `auto_publish` | `"published"` | `True` | `True` если category в `ROUTE_ELIGIBLE_CATEGORIES` |
| `needs_review` | `"needs_review"` | `False` | `False` |
| `hidden` | `"hidden"` | `False` | `False` |

Для `needs_review` и `hidden` место не попадает ни в публичный каталог,
ни в route candidates (оба фильтра проверяют `is_published=True`).

---

## Правила классификации

### HIDDEN (жёсткие условия, в порядке проверки)

| Условие | Причина |
|---|---|
| `title` пустой или None | `no_title` |
| `lat` или `lng` отсутствуют / оба = 0.0 | `no_coordinates` |
| `category` ∈ `PUBLIC_HIDDEN_CATEGORIES` | `hidden_category` |
| `confidence < 0.2` | `low_confidence` |

### NEEDS_REVIEW (мягкие сигналы и нетуристические категории)

| Условие | Причина |
|---|---|
| `category` ∈ `NON_TOURIST_CATEGORIES` (`health`, `service`) | `non_tourist_category` |
| `0.2 ≤ confidence < 0.5` | `low_confidence` |
| `source is None` | `no_source` |
| Динамическая категория + нет адреса + нет opening_hours | `missing_hours_for_dynamic_category` |

`NON_TOURIST_CATEGORIES` — категории, которые хранятся в БД, но **не публикуются
в туристический каталог**. Предназначены для будущего service/useful слоя.
`health` = аптеки, клиники, больницы. `service` = мастерские, сервисные точки.

Динамические категории: `bar`, `cafe`, `coffee`, `food`, `restaurant`.

### AUTO_PUBLISH

Если ни одно из HIDDEN/NEEDS_REVIEW условий не выполнено.

---

## Категории: три уровня видимости

| Тип | Примеры | Gate | В tourist catalog | Route eligible |
|---|---|---|---|---|
| **Туристические** | museum, park, beach, cafe, coffee, bar | AUTO_PUBLISH | ✅ | ✅ (по категории) |
| **Нетуристические** | health, service | NEEDS_REVIEW | ❌ | ❌ |
| **Скрытые (utility)** | transport, useful, fuel, parking, bank, atm | HIDDEN | ❌ | ❌ |

Константы в `services/import_quality_categories.py`:
- `PUBLIC_HIDDEN_CATEGORIES` — всегда hidden (из `place_public_visibility.py`)
- `NON_TOURIST_CATEGORIES` — `{"health", "service"}` → needs_review
- `ROUTE_ELIGIBLE_CATEGORIES` — категории, разрешённые для маршрутов

`NON_TOURIST_CATEGORIES` хранятся в БД и не удаляются — это задел для будущего
отдельного service/useful слоя City Go.

---

## Route Eligibility

`is_route_eligible = True` только при `auto_publish` И категория ∈
`ROUTE_ELIGIBLE_CATEGORIES`:

```
coffee, food, walk, museum, attraction, beach, park, bar,
cafe, culture, viewpoint, sight, restaurant
```

`hotel`, `service`, `health` и все из `PUBLIC_HIDDEN_CATEGORIES`
не попадают в маршруты. `service` и `health` не достигают `auto_publish` —
они остановлены на `needs_review` ещё в gate.

---

## Где вызывается

| Путь | Файл | Вызов |
|---|---|---|
| Seed import | `services/place_seed_write_service.py::write_place_seed_item` | для каждого нового места |
| OSM import | `data/scripts/import_city_osm.py::_apply_import` | для каждого нового места |

Существующие опубликованные места **не затрагиваются** — gate вызывается
только при `place is None` (первая вставка).

---

## Import Summary

После импорта `PlaceSeedImportSummary` содержит:

```json
{
  "total": 100,
  "created": 98,
  "updated": 1,
  "skipped": 1,
  "invalid": 0,
  "auto_published": 75,
  "needs_review_count": 20,
  "rejected_count": 3
}
```

---

## Пороги (константы в `import_publication_gate.py`)

| Константа | Значение | Значение |
|---|---|---|
| `HIDDEN_CONFIDENCE_THRESHOLD` | `0.2` | Ниже → скрыть |
| `AUTO_PUBLISH_CONFIDENCE_THRESHOLD` | `0.5` | Ниже → ревью |

---

## Ограничения до полноценной Admin UI

- Нет поля `review_reason` в модели `Place` (причина хранится в import summary).
- Admin UI для работы с `needs_review` очередью ещё не реализован (`P2`).
- Деструктивный cleanup `cleanup_bad_places.py` не интегрирован с gate.
- `is_searchable` остаётся write-only/dead полем (поиск не использует его).

---

## Следующий шаг

`P2`: Admin UI с очередью `needs_review` мест → bulk approve/reject.
