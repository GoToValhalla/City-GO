# Place Quality Score

Модуль: `services/place_quality_score/`

## Назначение

Базовая оценка полноты карточки места **без AI**. Используется в:
- Eligibility Dashboard (колонка Quality, причина `low_quality`)
- Data Quality (buckets high/medium/low)
- Dry Run (косвенно через eligibility rules)

## Формула (0–100)

| Компонент | Баллы | Условие |
|-----------|-------|---------|
| coordinates | 15 | `lat`/`lng` заданы, не 0,0 |
| photo | 20 | `image_url` не пустой |
| address | 20 | `address` не пустой |
| description | 15 | `short_description` не пустой |
| hours | 15 | `opening_hours` заданы |
| website | 5 | `source_url` не пустой |
| verification | 10 | `verification_status == verified` |

## Buckets

- `high` — score ≥ 75
- `medium` — 50–74
- `low` — < 50 (`LOW_QUALITY_THRESHOLD`)

## API

`compute_place_quality_score(place)` → `int`

`quality_bucket(score)` → `high|medium|low`

## Ограничения

- Не учитывает subjective tourism value
- Bucket для города считается на sample до 2000 мест (Data Quality)
