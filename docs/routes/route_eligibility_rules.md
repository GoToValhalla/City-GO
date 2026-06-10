# Route Eligibility Rules

Модуль: `services/route_eligibility/`

## Вопрос

**Может ли place участвовать в маршруте?**

## API

- `evaluate_place_route_eligibility(place, city=None)` → `{eligible, reasons}`
- `apply_route_eligible_filters(query)` — SQL для ORM/SQLAlchemy query
- `route_eligible_sql_conditions()` — tuple условий для `select().where()`
- `ROUTE_FORBIDDEN_CATEGORIES` — объединение PUBLIC_HIDDEN + NON_TOURIST + explicit junk

## Place NOT eligible если

| Причина | rejection code |
|---------|----------------|
| нет `city_id` | `missing_city_id` |
| город inactive | `city_inactive` |
| город не published | `city_not_published` |
| `is_active=false` | `place_inactive` |
| `status != active` | `place_status_not_active` |
| `is_published=false` | `place_not_published` |
| `is_visible_in_catalog=false` | `place_not_visible_in_catalog` |
| `is_route_eligible=false` | `route_eligible_false` |
| нет координат / 0,0 | `missing_coordinates` / `invalid_coordinates` |
| forbidden category | `forbidden_category:{code}` |

## Запрещённые категории (примеры)

`pharmacy`, `hospital`, `health`, `bus_stop`, `transport`, `useful`, `parking`, `fuel`, `atm`, `bank`, `service`, `toilet`, `police`, `industrial`, `office` и др. — см. `forbidden_categories.py`.

**Важно:** места не удаляются из БД, только исключаются из candidate pool.

## Где применяется

- `services/candidate_retrieval_service.py` — SQL (canonical)
- `services/itinerary_candidate_service.py` — SQL + Python guard
- `services/itinerary_replan_service.py` — stop search + load places

## Отличие от feature toggles

Feature toggles — включение функциональности (`route_generation_enabled`).
Eligibility — бизнес-правила контента, не toggles.

## Строгость SQL

До этапа: `is_route_eligible IS TRUE OR NULL`.
После этапа: **`is_route_eligible IS TRUE`** (NULL = not eligible).
