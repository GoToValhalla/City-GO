# Taxonomy & Data Quality Automation Center

## Назначение

`/admin/taxonomy` — единый центр управления категориями, mappings, конфликтами, массовой переклассификацией и route policy. Источником истины является `categories`; поля `places.category` и `places.canonical_category` сохраняются как backward-compatible materialized значения.

## Модели

- `Category`: русские пользовательское и административное названия, дерево, визуальные параметры, каталог, поиск и route policy.
- `TaxonomyMapping`: OSM/Wikidata/import/legacy/text mapping с priority, confidence и условиями.
- `TaxonomyDecision`: объяснимое и обратимое решение для места.
- `TaxonomyConflict`: активная очередь неопределённых или противоречивых решений.
- `TaxonomyBulkBatch`: immutable preview и состояние apply/rollback.
- `QualityRule`, `QualityIssue`: управляемые проверки и найденные нарушения.
- `WorkflowOperation`: идемпотентный журнал шагов фоновой операции.

## Rule engine

Приоритет: manual override → exact source mapping → mapping с дополнительными условиями → legacy mapping → text heuristic → unknown. `confidence >= 0.85` применяется автоматически, `0.60–0.85` отправляется на проверку, более низкий результат остаётся unknown.

Каждый результат содержит категорию, confidence, matched rule, объяснение, предупреждения и альтернативы. Низкоуверенное решение нельзя молча применить через API.

## Route policy

Политики: `always_allowed`, `allowed_by_context`, `useful_only`, `forbidden`, `manual_review`. Контексты: `tourist_walk`, `family`, `food`, `coffee`, `practical`, `emergency`, `accessibility`.

Инфраструктура остаётся полноценной частью каталога. Аптеки, банки, банкоматы и парковки обычно используют `useful_only`; они доступны в practical/emergency/accessibility, но не попадают в обычную туристическую прогулку.

## Workflow lifecycle

Registry содержит:

- `after_import`: taxonomy → validation → duplicates → score → enrichment → verification;
- `after_place_confirmation`: confidence → publication validation → search;
- `after_photo_confirmation`: primary photo → score → закрытие `no_photo`;
- `after_category_change`: route eligibility → score → route cache invalidation.

Операция имеет request ID, idempotency key, статусы шагов, retry counter, error и audit actor. Повторный запуск с тем же ключом возвращает существующую операцию.

## Quality Score V2

Оцениваются taxonomy, address, coordinates, photo, description, opening hours, contacts, verification, freshness, source confidence и duplicate risk. Итог — 0–100 и bucket. Публикация дополнительно проверяет blocking issues; высокий score не обходит блокирующую ошибку.

## Bulk и rollback

1. `POST /admin/taxonomy/bulk/preview` фиксирует точный список ID, old/new category, route flags и `updated_at`.
2. Apply изменяет только записи из preview, которые не менялись после preview.
3. Каждое изменение получает batch ID и taxonomy decision.
4. Rollback восстанавливает old category и route flag только если место всё ещё находится в состоянии, созданном этим batch.

Это защищает чужие изменения после массовой операции.

## Миграция

`d4e6f8a2c101` расширяет `categories` и создаёт automation tables. Миграция поддерживает PostgreSQL и SQLite batch mode, не удаляет legacy-поля и имеет downgrade. Перед production upgrade требуется backup и dry-run на копии базы.
