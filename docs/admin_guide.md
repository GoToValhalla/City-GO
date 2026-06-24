# City GO — руководство по админке

Дата обновления: 2026-06-24.

Админка встроена во frontend-проект: `frontend/src/pages/admin`. Запуск:

```bash
cd frontend
npm install
npm run dev
```

Backend по умолчанию: `http://127.0.0.1:8000`; другой адрес задаётся `VITE_API_BASE_URL`.

## Основные разделы

- `/admin/overview` — операционная сводка.
- `/admin/cities` и `/admin/cities/{slug}` — города и City Workspace.
- `/admin/places` — поиск, создание, редактирование и массовые действия с местами.
- `/admin/taxonomy` — категории, mappings, конфликты, bulk и route policy.
- `/admin/quality` — качество данных.
- `/admin/photos` и `/admin/verification` — очереди модерации.
- `/admin/imports` и `/admin/enrichment` — операции наполнения.
- `/admin/system-health`, `/admin/system-logs`, `/admin/audit` — мониторинг и расследование.
- `/admin/analytics` — продуктовая и операционная аналитика.

Все admin endpoints защищены `admin_required`. Опасные действия имеют preview или подтверждение, после успеха UI перечитывает backend state.

## Taxonomy Manager

Taxonomy Manager состоит из восьми вкладок:

1. Категории — создание собственных категорий, редактирование, архивирование и восстановление.
2. Иерархия — дерево, drag-and-drop родителя, порядок и проверка циклов.
3. Псевдонимы — текстовые aliases без показа raw keys пользователю.
4. Правила классификации — OSM, Wikidata, legacy/import mappings и quality rules.
5. Конфликты — очередь решений с автоматическим refill после действия.
6. Массовая переклассификация — обязательный dry-run, apply и rollback по batch ID.
7. История изменений — переход в audit с old/new значениями.
8. Настройки маршрутов — централизованная route policy категории.

Категория не удаляется физически. Если она используется местами, применяется обратимое архивирование. `code` служит внутренним стабильным идентификатором, а UI использует русское `display_name`.

## Классификация

Порядок решений:

1. ручной выбор администратора;
2. точный mapping источника;
3. mapping с дополнительными условиями;
4. legacy mapping;
5. эвристика по названию и описанию;
6. unknown и конфликтная очередь.

High confidence применяется автоматически. Medium confidence и неоднозначные решения требуют проверки. Low confidence не меняет категорию.

## Массовая операция

1. Выбрать город, текущую и целевую категории.
2. Запустить dry-run.
3. Проверить количество, примеры и route conflicts.
4. Применить зафиксированный batch.
5. При необходимости откатить batch.

Apply не меняет записи, обновлённые после preview. Rollback не перезаписывает последующие ручные изменения.

## Route policy

- `always_allowed` — туристические категории.
- `allowed_by_context` — еда, кофе и сценарные категории.
- `useful_only` — аптеки, банки, банкоматы, парковки и другая инфраструктура.
- `forbidden` — объекты, не подходящие для маршрутов.
- `manual_review` — неизвестные и спорные категории.

Инфраструктура сохраняется в каталоге и поиске, но не попадает в обычную прогулку без подходящего контекста.

## Workflow

Поддерживаются `after_import`, `after_place_confirmation`, `after_photo_confirmation`, `after_category_change`. Операции имеют request ID, idempotency key, статусы шагов, retry и failure state.

## Проверки

```bash
python -m pytest -q
cd frontend
npm run lint
npm test
npm run build
```

Архитектура и API: `docs/architecture/taxonomy_automation_center.md`, `docs/reference/taxonomy_api.md`. Процедура отката: `docs/runbooks/taxonomy_rollback.md`.
