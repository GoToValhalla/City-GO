# Place Web Enrichment Probe

Цель: быстро проверить, может ли бесплатный парсер закрыть часть проблем с адресами, сайтами, телефонами, часами работы и фото-кандидатами для мест City Go.

Это **preview-only** инструмент. Он ничего не пишет в БД и ничего не применяет автоматически.

## Что делает

Скрипт `data/scripts/place_web_enrichment_probe.py` принимает CSV/JSON со списком мест и создаёт:

- `preview.csv` — таблица предложенных значений;
- `preview.json` — полный результат с debug-источниками;
- `summary.json` — агрегированная статистика.

## Источники первой версии

Используются только бесплатные/открытые источники:

1. Nominatim search.
2. Nominatim reverse geocoding.
3. OSM extra tags из Nominatim.
4. Wikidata P18 image.
5. Wikipedia summary thumbnail.
6. Официальный сайт через `og:image`.
7. Категорийная заглушка, если реальное фото не найдено.

Не используются:

- Google scraping;
- 2GIS scraping;
- TripAdvisor scraping;
- Instagram scraping;
- Яндекс.Карты scraping;
- запись в PostgreSQL;
- prod apply.

## Пример запуска

```bash
python data/scripts/place_web_enrichment_probe.py \
  --input data/exports/place_enrichment/active/place_enrichment_алматы_20260608_204651/export.csv \
  --output-dir data/exports/place_web_enrichment_probe/almaty_50 \
  --limit 50 \
  --sleep 1.1
```

Пауза `--sleep 1.1` нужна, чтобы не нарушать лимит Nominatim.

## Формат входа

Поддерживаются CSV и JSON.

Минимальные поля:

```text
id или place_id
title или name
city_name или city
category
lat
lng
current_address
current_website
current_phone
current_opening_hours
current_image_url
source_url
raw_osm_tags
```

Скрипт совместим с экспортом `run_place_enrichment_export.py`.

## Формат preview.csv

Основные поля:

```text
input_place_id
input_title
input_city
input_category
current_address
current_image_url
suggested_address
suggested_website
suggested_phone
suggested_opening_hours
suggested_image_url
image_match_status
suggested_data_source
suggested_source_url
suggested_confidence
suggested_comment
rejection_reason
```

## image_match_status

Возможные значения:

```text
osm_image
wikidata_p18
wikipedia_thumbnail
site_og_image
category_placeholder
```

Важно: `category_placeholder` — это не фото места. Это только заглушка, чтобы карточка не была пустой.

## Как оценивать результат

Для теста на 20–50 мест смотреть:

1. Сколько мест получили `suggested_address`.
2. Сколько мест получили реальное фото, то есть `image_match_status != category_placeholder`.
3. Сколько мест получили `suggested_website`.
4. Сколько результатов явно мусорные.
5. Какие источники реально сработали.

Минимальный критерий пользы:

```text
адреса: +30–50%
реальные фото: +15–30%
сайты: +20–40%
```

Если результат ниже — сначала смотреть не код, а источники и категории мест.

## Ограничения первой версии

1. Скрипт не ищет сайты через поисковик.
2. Скрипт берёт сайт только если он найден в OSM/Nominatim или уже есть во входном CSV.
3. Скрипт не скачивает изображения.
4. Скрипт не проверяет размер изображения через HEAD.
5. Скрипт не делает визуальную проверку фото.
6. Скрипт не применяет результат в БД.

Это сделано намеренно, чтобы прототип был безопасным и не пересекался с prod pipeline.

## Следующие улучшения, если прототип покажет пользу

1. Добавить поиск официального сайта через разрешённый поисковый API.
2. Добавить Wikimedia Commons search по Wikidata QID.
3. Добавить Mapillary area photo.
4. Добавить HEAD-проверку изображений.
5. Добавить source provenance.
6. Добавить preview/apply через админку.
7. Добавить массовый запуск по городу.

## Главное правило

До ручного просмотра preview нельзя применять данные в БД.
