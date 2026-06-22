# City Go — Алembic миграции: архитектура и инварианты

## Текущее состояние (22.06.2026)

| Параметр | Значение |
|---|---|
| Текущий head | `e2f4a6b8c0d1` (merge_city_publication_and_import_pipeline_heads) |
| Base | `e48f13974bc8` (init_place_model) |
| Всего ревизий | 39 |
| Число активных heads | **1** (инвариант) |
| Число bases | **1** (инвариант) |

Проверить командой:
```bash
.venv/bin/alembic heads   # должен показать ровно один head
```

---

## Дерево миграций

История линейна с тремя историческими точками ветвления, все уже слиты.

```
e48f13974bc8  init_place_model                    [base]
└─ d7f42a463fe3  add_city_model
   └─ 784d6d2f3828  add_slug_to_places
      └─ 1e31cbdc17df  add_category_model
         └─ 4a31a10f9e37  add_category_id_to_places
            └─ 3000b4f577bc  add_tag_model
               └─ ac1e9bce72eb  add_place_tag_model
                  └─ 3607cc80012d  add_collection_models
                     └─ 281a07116c51  add_route_models
                        └─ 3fb51e7943f5  add_place_schedule_model
                           └─ 9c8e4b1a2f10  add_image_url_to_places
                              └─ b21f3c5c1d90  add_route_mode_and_distance
                                 └─ c7b36de91a2d  add_places_city_foreign_key
                                    └─ d3a7f8840e12  add_place_recommendation_fields
                                       └─ e4f0b9ad72c1  postgis / geospatial
                                          └─ f6c2d9a1b4e8  add_telegram_user_contexts
                                             ├─[ветка A]─ 7a0f1f2c9d31  place_data_quality
                                             │            └─ cb12a6d8e901  user_signal
                                             │               └─ d1f8a7c2b904  place_status
                                             │                  └─ f24ad91c7b66  route_build_events
                                             │                     └─ a37d9108c2b5  place_import_events
                                             │                        └─ b9d2c1f0a882  place_verification_tasks
                                             │                           ├─ c2b8a9e1d4f3  user_id_route_build_events
                                             │                           │  └─ 2b7f6a4d9c10  city_expansion [branchpoint]
                                             │                           │     ├─ f3a8c2d1e9b4  place_images
                                             │                           │     └─ 9b3c5f7a2e61  admin_publication_and_audit
                                             │                           └─ [MERGE-1]
                                             │                              5f2d7a91c4b8  place_existence_confidence
                                             │                              down=(f3a8c2d1e9b4, b9d2c1f0a882)
                                             │
                                             └─[MERGE-2]
                                                8a44c9f2d6b1  merge_alembic_heads
                                                down=(5f2d7a91c4b8, f6c2d9a1b4e8)
                                                └─[MERGE-3]
                                                   c1f4e7a9d2b3  merge_remaining_heads  ← HEAD
                                                   down=(8a44c9f2d6b1, 9b3c5f7a2e61)
```

---

## Merge-миграции (исторические, не содержат DDL)

Все три merge-ревизии — пустые (только `pass` в `upgrade`/`downgrade`).
Их цель — свести несколько параллельных веток в единую цепочку.

| Ревизия | Имя | Родители (down_revision) |
|---|---|---|
| `5f2d7a91c4b8` | add_place_existence_confidence | `f3a8c2d1e9b4`, `b9d2c1f0a882` |
| `8a44c9f2d6b1` | merge_alembic_heads | `5f2d7a91c4b8`, `f6c2d9a1b4e8` |
| `c1f4e7a9d2b3` | merge_remaining_heads (**head**) | `8a44c9f2d6b1`, `9b3c5f7a2e61` |

---

## Инвариант: single-head

**Правило:** в любой момент `alembic heads` должен возвращать ровно одну ревизию.

**Текущий head:** `e2f4a6b8c0d1` (merge city publication defaults and import pipeline heads).

Текущие поздние миграции:
- `e8f1a2b3c4d5` — feature_toggles
- `f9a2b3c4d5e6` — seed global toggles
- `a1b2c3d4e5f7` — system_logs, product_events, admin_operations
- `f0a1b2c3d4e6` — City quality/import metadata used by seed migrations
- `fa21b0c7d9e2` — Astrakhan/Arkhangelsk seed data
- `b73c0d1e2f40` — city publication defaults
- `d4e5f6a7b8c0` — import job pipeline fields
- `e2f4a6b8c0d1` — merge revision that restores one active head

Это обеспечивает детерминированность `alembic upgrade head` в docker-compose:

```yaml
# docker-compose.yml — сервис migrate
command: alembic upgrade head
```

При наличии нескольких heads команда завершается с ошибкой
`FAILED: Multiple head revisions are present`, и backend не поднимается.

### Автоматическая проверка

Инвариант зафиксирован в тесте:

```bash
python3.11 -m pytest tests/test_alembic_single_head_new.py -v
```

Тест проверяет без подключения к БД:
- ровно один head
- ровно один base
- известный head = `e2f4a6b8c0d1`
- известный base = `e48f13974bc8`
- общее число ревизий = 39
- ключевые таблицы присутствуют в `Base.metadata`

---

## Как добавить новую миграцию

```bash
# 1. Сгенерировать ревизию (ТОЛЬКО если работаешь один, head один)
.venv/bin/alembic revision --autogenerate -m "add_something"

# 2. Проверить сгенерированный файл вручную (autogenerate не всегда корректен)

# 3. Убедиться, что head остался один
.venv/bin/alembic heads

# 4. Прогнать тест
python3.11 -m pytest tests/test_alembic_single_head_new.py -v

# 5. Обновить EXPECTED_COUNT в тесте (было 29 → стало 30)
# 6. Обновить KNOWN_HEAD в тесте на новый revision id
```

### Если появилось несколько heads (параллельная разработка)

```bash
# Свести к одному head через merge-ревизию
.venv/bin/alembic merge heads -m "merge_heads"

# Убедиться что теперь один head
.venv/bin/alembic heads

# Обновить тест
```

---

## Как устроена загрузка моделей в env.py

`migrations/env.py` импортирует модели поимённо (`import models.city`, `import models.place` и т.д.).

Первый же такой импорт запускает `models/__init__.py`, который в свою очередь
импортирует **все** модели пакета. Поэтому `Base.metadata` содержит все 29 таблиц
независимо от порядка импортов в `env.py`.

**Важно:** если когда-либо будет удалён или изменён `models/__init__.py`,
нужно будет синхронизировать список импортов в `env.py` вручную.
Тест `test_env_metadata_covers_all_tables` страхует от этого.

---

## Команды для диагностики

```bash
# Текущие heads (должен быть один)
.venv/bin/alembic heads

# Полное дерево истории
.venv/bin/alembic history

# Точки ветвления/слияния
.venv/bin/alembic branches

# Текущая ревизия применённая к БД (требует подключения)
.venv/bin/alembic current

# Проверка чистого upgrade (требует PostgreSQL)
# Запустить в docker-compose: docker-compose run --rm migrate
```

---

## Чистый upgrade на PostgreSQL (прогон P0-1 часть Б)

**Статус на 07.06.2026:** не прогонялся в рамках текущей задачи — нет доступа к
PostgreSQL в среде выполнения. Требуется отдельный прогон:

```bash
# Поднять БД
docker-compose up -d db

# Прогнать чистый upgrade
docker-compose run --rm migrate

# Убедиться, что backend поднимается
docker-compose up -d backend

# Проверить /ready
curl http://localhost:8000/ready
```

До выполнения этого прогона «чистый upgrade» считается структурно подтверждённым
(граф корректен, один head, один base), но не эмпирически доказанным.

---

## CI / pytest (SQLite)

- GitHub Actions: `alembic upgrade head` на `sqlite:///./ci_test.db`, затем `pytest` с тем же `DATABASE_URL`.
- `tests/conftest.py`: session autouse применяет alembic к `SessionLocal` (middleware `public_access_middleware` читает `feature_toggles` из этой БД).
- In-memory `create_all` остаётся для `get_db` override (изолированные фикстуры `client` / factories).
- `ALEMBIC_SKIP_FILE_CONFIG=1` в pytest — `fileConfig` в `migrations/env.py` не сбрасывает caplog.
- Проверка схемы: `tests/test_test_db_schema_new.py` (таблицы `feature_toggles`, `system_logs`, поля `places`).

---

## Остаточные риски

| Риск | Вероятность | Влияние | Митигация |
|---|---|---|---|
| Чистый upgrade не прогнялся на PostgreSQL | Средняя | Высокое | Прогнать docker-compose run migrate на чистой БД |
| Новая ветка без merge-ревизии | Низкая | Высокое | Тест test_alembic_single_head_new.py + CI |
| Удаление models/__init__.py | Очень низкая | Высокое | Тест test_env_metadata_covers_all_tables |
