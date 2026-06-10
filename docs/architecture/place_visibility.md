# Place Visibility — City Go

> Документ описывает модель публичности/видимости мест, import behavior, и admin publish flow.
> Обновлён после реализации P0-4 (draft imports) и Import Quality Gate (auto_publish / needs_review / hidden).

---

## Поля публичности Place

| Поле                   | Тип    | Default модели | Назначение                                              |
|------------------------|--------|----------------|---------------------------------------------------------|
| `is_published`         | bool   | `True`*        | Место прошло модерацию и разрешено к публикации         |
| `is_visible_in_catalog`| bool   | `True`*        | Место показывается в публичном каталоге                 |
| `is_route_eligible`    | bool   | `True`*        | Место может быть включено в маршруты                    |
| `is_searchable`        | bool   | `True`*        | Место индексируется в поиске (write-only, не читается)  |
| `publication_status`   | str    | `"published"`* | `draft`/`published`/`unpublished`/`needs_review`/`hidden` |
| `is_active`            | bool   | `True`         | Место физически активно (не закрыто, не удалено)        |
| `status`               | str    | `"active"`     | Операционный статус (`active`/`draft`/`closed`/...)     |

> *Default модели = `True`/`"published"` — **намеренно**, для backward совместимости
> с legacy/seed данными. Новые import пути используют Quality Gate.

---

## Что считается Draft/Unpublished (непубличным)

Место **не появляется** в каталоге если хотя бы одно из:
- `is_published = False`
- `is_visible_in_catalog = False`
- `publication_status` = `"draft"` / `"needs_review"` / `"hidden"` / `"unpublished"`

Draft/unpublished место **не появляется**:
- в публичном каталоге (`GET /places/*`)
- в route candidates (`CandidateRetrievalService` — использует `public_route_place_conditions`)
- в поиске

Draft место **видно** только:
- в admin panel (`GET /admin/places`)

---

## Что считается Published (публичным)

Место считается **published** если:
- `is_published = True`
- `is_visible_in_catalog = True`
- `publication_status = "published"`
- `is_active = True`
- `status = "active"` (или NULL)

Публичный фильтр в коде: `services/place_public_visibility.py::public_place_conditions()`.

```python
# Backward compat: _true_or_null принимает True ИЛИ NULL (для legacy данных)
def public_place_conditions():
    return (
        _true_or_null(Place.is_active),
        or_(Place.status.is_(None), Place.status == "active"),
        _true_or_null(Place.is_published),
        _true_or_null(Place.is_visible_in_catalog),
        ...
    )
```

---

## Что считается Route Eligible

Место может участвовать в маршрутах если:
- Все published условия выполнены
- `is_route_eligible = True` (или NULL — backward compat)
- Категория не в `PUBLIC_HIDDEN_CATEGORIES` (transport, parking, atm, etc.)

Route place filter: `public_route_place_conditions()` в `place_public_visibility.py`.

**ВАЖНО**: `CandidateRetrievalService` (маршруты) использует `public_route_place_conditions()`
начиная с реализации Route Eligibility Fix. До этого использовал `public_place_conditions()`,
что позволяло non-eligible местам попадать в маршруты.

---

## Как Import создаёт места — Import Quality Gate

Вместо всегда-draft поведения (P0-4), теперь применяется Quality Gate
(`services/import_publication_gate.py`):

| Решение | `publication_status` | `is_published` | `is_route_eligible` |
|---|---|---|---|
| `auto_publish` | `"published"` | `True` | По категории |
| `needs_review` | `"needs_review"` | `False` | `False` |
| `hidden` | `"hidden"` | `False` | `False` |

Категории `health` и `service` всегда получают `needs_review("non_tourist_category")` —
они хранятся в БД, но не публикуются в туристический каталог.
Удалять их нельзя — задел для будущего service/useful слоя.

Подробнее: `docs/architecture/data_import_quality_gate.md`.

### Пути создания мест

| Path | Файл | Behavior |
|---|---|---|
| API seed import | `services/place_seed_write_service.py` | Quality Gate |
| OSM import script | `data/scripts/import_city_osm.py` | Quality Gate |
| Admin create place | `services/admin_service.py` | Draft (схема) |
| Dev seed script | `scripts/seed_minimal_data.py` | Published (явно, dev only) |

---

## Admin Publish Flow

### Публикация места

```
POST /admin/places/{id}/publish
Authorization: Bearer <ADMIN_API_TOKEN>
{"reason": "Проверено вручную"}
```

После вызова: `is_published=True`, `is_visible_in_catalog=True`, `is_route_eligible=True`,
`publication_status="published"`, `published_at=<now>`, audit log.

### Снятие с публикации

```
POST /admin/places/{id}/unpublish
Authorization: Bearer <ADMIN_API_TOKEN>
{"reason": "Требует проверки"}
```

После вызова: `is_published=False`, `is_visible_in_catalog=False`, `is_route_eligible=False`,
`publication_status="unpublished"`, `unpublished_at=<now>`, audit log.

---

## Жизненный цикл места (обновлённый)

```
Import / Seed write
        │
        ▼
  [Quality Gate]
  assess_import_quality()
        │
        ├── quality_ok ──────────► [Published]   is_published=True, route_eligible=by_category
        │
        ├── low_confidence ──────► [Needs Review] is_published=False, ждёт admin
        │   no_source
        │   missing_hours
        │
        └── no_title ────────────► [Hidden]       is_published=False, is_active=True
            no_coords
            hidden_category
            very_low_confidence

[Needs Review] ──► POST /admin/places/{id}/publish ──► [Published]
[Published]    ──► POST /admin/places/{id}/unpublish ► [Unpublished]
[Unpublished]  ──► POST /admin/places/{id}/publish ──► [Published]
```

---

## Ограничения текущего решения

1. **Несколько источников истины**: `is_published`, `is_visible_in_catalog`, `is_route_eligible`, `publication_status` — четыре поля.
2. **`is_searchable` мёртвое поле**: пишется, но не читается ни одним SQL-фильтром.
3. **Нет Admin UI для `needs_review` очереди**: нужен P2 для bulk approve.
4. **`review_reason` не хранится в модели**: причина ревью только в import summary.

---

## Следующие шаги

- **P2**: Admin UI с очередью `needs_review` — bulk approve/reject.
- **P2**: Single source of truth — заменить 4 boolean поля на единый `publication_status` enum.
- **P3**: Автоматический переход `needs_review → auto_publish` после enrichment (адрес + фото).
