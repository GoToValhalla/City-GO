# City Go — Production Data Import and Image Refresh

Дата: 2026-06-05.

## Place Import

Dry-run по умолчанию:

```bash
.venv/bin/python scripts/production_place_import.py --api-base http://127.0.0.1:8000
```

Real import только явно:

```bash
.venv/bin/python scripts/production_place_import.py --api-base https://api.example.com --real
```

Seed-пакеты по умолчанию:

- `data/seeds/place_import/zelenogradsk_osm.json`
- `data/seeds/place_import/zelenogradsk_editorial_walks.json`

После real import:

```bash
.venv/bin/python scripts/check_place_coverage_gate.py zelenogradsk
```

## Image Refresh

Локальный refresh без live network:

```bash
.venv/bin/python scripts/refresh_place_images.py
```

Live refresh:

```bash
.venv/bin/python scripts/refresh_place_images.py --live
```

С Mapillary:

```bash
.venv/bin/python scripts/refresh_place_images.py --live --mapillary-token "$MAPILLARY_TOKEN"
```

Токен передаётся явно в процесс и не сохраняется в коде, логах или документах.

## Safety

- Google/Yandex/2GIS scraping не используется.
- Category/area images не маркируются как exact place photo.
- `validate_catalog_images.py` запускается после refresh и возвращает ошибки в JSON.
