# Аудит полей рейтингов, метрик и скоров City Go

## Сводная карта

| Поле | Тип | Влияет на маршрут? | Влияет на каталог? |
|------|-----|-------------------|-------------------|
| `confidence` | float 0–1 | Да (soft scoring 14%) | Да (import gate) |
| `existence_confidence_score/level` | int 0–100 + enum | Нет | Косвенно (admin) |
| `verification_status` + audit fields | enum + metadata | Нет | Через `is_active`/`status` |
| `is_published / publication_status / …` | bool + enum | Да (фильтр кандидатов) | Да |
| `image_confidence / image_status` | float + enum | Косвенно (base_quality) | Да (публичное фото) |
| `scoring_breakdown` | dict[float] runtime | Да (ранжирование) | Нет |
| `quality_score` | float 0–1 runtime | Итог маршрута | UI |
| `trust_score` | — | **не существует** | — |

---

## 1. `confidence` (Place.confidence)

- **Значения:** float 0–1, иногда строки `"high"/"medium"/"low"` (legacy)
- **Источник:** OSM import (0.7 accepted, 0.0 rejected), seed/import, admin
- **Import gate:** `<0.2` → hidden, `<0.5` → needs_review
- **Route scoring:** 14% веса в candidate score (`route_data_confidence_score.py`)
- **Отображение:** frontend «OpenStreetMap, уверенность 70%» через `sourceLabel()`
- **Вывод:** нужно и полезно

## 2. `existence_confidence_score` / `existence_confidence_level`

- **Значения:** score int 0–100; level: `verified/high/medium/low/unknown`
- **Источник:** `backfill_place_confidence.py` (import inferred), `place_verification_service.py`, `admin_service.verify_place()`
- **Отображение:** admin dashboard «Достоверность», `PlaceDetailPage` блок «Достоверность места»
- **Маршруты:** не влияет — gap! Место с score=15 может попасть в маршрут
- **Вывод:** полезно для модерации, но не связано с route pipeline

## 3. `trust_score`

**Не существует в кодовой базе.** Ближайшие аналоги — `place.confidence` и `existence_confidence_score`.

## 4. `quality_score` (несколько смыслов!)

### Route quality_score (итог маршрута)
```
raw = diversity*0.25 + budget_fit*0.15 + data_completeness*0.35 + warning_health*0.25
score = min(raw * completeness, minimum_data_cap)
```
- Отображается: ShieldCheck + `{quality*100}%` в `RouteResultPanel.tsx`
- Telegram: «Качество данных: X%»
- НЕ является показателем «безопасности» — это качество данных маршрута

### Scoring `base_quality` (компонент кандидата, 18%)
```
coords:0.3 + opening_hours:0.25 + visit_duration:0.2 + image:0.15 + description:0.1
```

### `route_ready_score` (coverage API, не маршрут)
`(category_coverage*0.6 + data_completeness*0.4)`, показывает готовность города к маршрутам

## 5. `scoring_breakdown` компоненты

| Ключ | Вес в final | |
|------|------------|---|
| `interest` | 27% | interest_match_score |
| `base_quality` | 18% | coords + hours + image + … |
| `time_context` | 18% | open-now, morning/evening fit |
| `data_confidence` | 14% | нормализованный place.confidence |
| `popularity_proxy` | 8% | wikidata/osm/image/description |
| `context` | 7% | indoor/outdoor, family, pace |
| `data_quality` | 4% | validation issues penalty |
| `personalization` | 4% | |
| `distance/popularity/novelty` | **0% — в breakdown, но не в combine** | tech debt |

## 6. `image_confidence` / `image_status` / `image_reviewed_at`

**DB слой** (`place_images` table):
- `confidence` float — 0.72–0.95 в зависимости от источника (OG/OSM/Wikidata/Wikipedia)
- `status`: `needs_review / approved / rejected / active / unavailable`
- Публичное фото: только `approved / active`

**Legacy offline** (`match_confidence` в JSON): `high/medium/low` — артефакт статического каталога, не в live API

## 7. Publication flags (критично!)

```python
is_published          # bool — общая публикация
is_visible_in_catalog # bool — видимость в каталоге
is_route_eligible     # bool — допуск в кандидаты маршрута
publication_status    # published / needs_review / hidden / draft / unpublished
```

**Import Quality Gate:**
- `auto_publish` → все True, `is_route_eligible` только для ROUTE_ELIGIBLE_CATEGORIES
- `needs_review / hidden` → все False

---

## Архитектурные риски

1. **Три «confidence» без единого словаря** — путаница в naming (admin dashboard `places_low_confidence` → existence level, не place.confidence)
2. **Existence verification не влияет на маршруты** — место `not_found` может остаться route-eligible
3. **`scoring_breakdown` содержит мёртвые ключи** (`distance`, `popularity`, `novelty`) — tech debt
4. **Два verify-пути** с разной семантикой score (full: 0/15/40/100 vs admin quick: max(current, 90))
5. **`match_confidence` (offline JSON)** — дублирует live `image_confidence`, кандидат на удаление
