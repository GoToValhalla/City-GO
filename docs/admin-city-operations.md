# Admin City Operations

Дата актуализации: 2026-06-22.

## City Workspace

Операторский экран города доступен по адресу:

```text
/admin/cities/<city_slug>
```

Frontend получает данные из одного backend endpoint:

```text
GET /admin/cities/by-slug/{city_slug}/workspace
```

Ответ объединяет:

- `city` — карточка города, статус публикации, счётчики мест, разрешённые действия;
- `readiness` — текущий readiness score и quality status;
- `import_job` — последний import/enrichment job, прогресс, ошибки, доступные действия;
- `coverage` — адреса/фото/категории для быстрого operational review.

Страница не заменяет существующие разделы `/admin/imports`, `/admin/routes/data-quality` и `/admin/coverage`; она даёт entry point, из которого оператор переходит в детальные инструменты.

## Backend-Driven Categories

Admin UI больше не должен держать собственный список категорий. Селекты категорий читают:

```text
GET /admin/taxonomy/categories
```

Список строится из:

- таблицы `categories`;
- реально встреченных `places.category`;
- базового набора известных категорий для пустых окружений.

Каждая категория содержит flags `is_route_eligible`, `is_catalog_visible`, `is_default_enabled`, `is_observed`, `observed_count` и `source`. Это позволяет отличать справочник от фактических данных города и не ломать UI при новых категориях из импорта.

## Safety Rules

- Публикация и снятие города остаются явными actions с confirmation в UI.
- Telegram/CI уведомления не содержат secret values.
- City Workspace не запускает фоновые операции автоматически при открытии страницы.
- Import/enrichment actions используют существующие `/admin/import-jobs/{city_id}/...` endpoints.
