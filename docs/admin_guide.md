# City GO — руководство по админке

Дата обновления: 2026-06-27.

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
- `/admin/quality` — качество данных и очереди проблем.
- `/admin/photos` — очередь фото-модерации.
- `/admin/verification` — проверка существования и актуальности мест.
- `/admin/imports` и `/admin/enrichment` — операции наполнения.
- `/admin/system-health`, `/admin/system-logs`, `/admin/audit` — мониторинг и расследование.
- `/admin/analytics` — продуктовая и операционная аналитика.

Все admin endpoints защищены `admin_required`. Опасные действия имеют preview или подтверждение, после успеха UI перечитывает backend state.

## Навигация по данным

Счётчики и статусы являются рабочими ссылками:

- число мест без адреса открывает точную выборку мест без адреса;
- показатель города сохраняет город и фильтр в URL;
- фото открывает карточку места, историю и внешний источник;
- инцидент открывает связанные системные логи;
- request ID открывает correlation chain;
- import job открывается по `/admin/imports?city=<slug>&job=<id>`;
- enrichment batch открывается по `/admin/enrichment?city=<slug>&batch=<id>`;
- из job и batch доступны места, шаги, артефакты, аудит и логи.

Ссылки можно сохранять и передавать другому администратору: выбранный набор восстанавливается из URL.

## Качество данных

Раздел качества данных нужен для измеримых проблем каталога:

- места без фото;
- места без адреса;
- низкая уверенность;
- места, требующие проверки;
- подозрительные route-eligible места из stoplist-категорий;
- слабые или отсутствующие описания.

Основные backend endpoints:

```http
GET /admin/data-quality/summary
GET /admin/data-quality/issues
POST /admin/data-quality/issues/refresh
POST /admin/data-quality/bulk-actions/preview
POST /admin/data-quality/bulk-actions/apply
```

Bulk-действие `propose_exclude_from_routes` создаёт только candidate на изменение route eligibility. Оно не меняет `Place.is_route_eligible` напрямую.

## Проверка мест

Раздел **Проверка мест** отвечает за существование и актуальность места, а не за все проблемы качества данных.

Экран использует верхние счётчики из:

```http
GET /admin/place-verifications/summary
```

Ответ должен иметь вид:

```json
{
  "queue_total": 0,
  "needs_recheck": 0,
  "unverified": 0,
  "low_confidence": 0,
  "verified_today": 0
}
```

Очередь мест загружается отдельно:

```http
GET /admin/place-verifications/queue
```

Если экран показывает красный блок **Сервер временно недоступен**, сначала проверить backend/deploy и доступность `/admin/place-verifications/summary`. До исправления этого endpoint нельзя считать проблему UI-навигацией пользователя.

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
