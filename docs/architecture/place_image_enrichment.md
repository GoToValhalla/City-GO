# Place Image Enrichment

City Go хранит для каждого места не просто `image_url`, а честный `image`
contract. UI обязан различать точное фото места, фото района и иллюстрацию
категории.

## Contract

`image.match_status`:
- `exact_place_photo` — фото относится к конкретному месту.
- `area_photo` — фото района или улицы рядом.
- `category_photo` — иллюстрация категории, не фото места.
- `no_photo` — фото отсутствует.

`image.match_confidence`:
- `high` — Wikidata P18, Commons depicts QID или подтверждённый источник.
- `medium` — географически близкое фото района.
- `low` — fallback категории или непроверенный источник.

## MVP Pipeline

Текущий MVP работает без закрытых API и без секретов:
1. `data/scripts/enrich_catalog_images.py` добавляет `image` block в frontend catalog.
2. `data/scripts/validate_catalog_images.py` проверяет enum-поля и обязательный URL для exact photo.
3. UI показывает `Фото места`, `Фото района рядом` или `Иллюстрация категории`.
4. `data/scripts/image_pipeline/run.py` строит enrichment artifact и verification queue:
   `data/enrichment/zelenogradsk_image_enrichment.json`,
   `data/enrichment/zelenogradsk_image_verification_queue.json`.

Live режим:

```bash
.venv/bin/python -m data.scripts.image_pipeline.run --live
```

Он включает Wikidata P18, Commons depicts и official website og:image. Mapillary
подключается только с явным токеном:

```bash
.venv/bin/python -m data.scripts.image_pipeline.run --live --mapillary-token "$TOKEN"
```

Google Places не включён: для него нужны отдельные ToS/attribution правила.

## Rules

- Кафе/рестораны без Wikidata QID не получают `exact_place_photo`.
- Commons text search по названию кафе запрещён без QID/depicts match.
- Фото района можно показывать только как `area_photo`.
- Category fallback не должен выглядеть как фото заведения.
- Кафе без Wikidata/official image остаётся `category_photo`.
- Verification queue содержит все места, где фото не является high-confidence exact.
