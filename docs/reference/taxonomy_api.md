# Taxonomy Admin API

Все endpoints защищены `admin_required`.

## Categories and tree

- `GET /admin/taxonomy/categories` — поиск, active, parent, route policy, пагинация.
- `POST /admin/taxonomy/categories` — создание собственной категории.
- `PATCH /admin/taxonomy/categories/{id}` — редактирование, архивирование и восстановление.
- `GET /admin/taxonomy/tree` — дерево с breadcrumb.
- `PUT /admin/taxonomy/tree` — атомарная смена родителей и порядка с cycle validation.

Удаление используемых категорий не предоставляется. Категории архивируются обратимо.

## Mappings and classification

- `GET/POST /admin/taxonomy/mappings`
- `PATCH /admin/taxonomy/mappings/{id}`
- `POST /admin/taxonomy/classify/preview`
- `POST /admin/taxonomy/classify/apply`

Apply проверяет confidence и optimistic `expected_category_id`.

## Conflicts

- `GET /admin/taxonomy/conflicts`
- `POST /admin/taxonomy/conflicts/{id}/resolve`

Действия: accept, choose, create_mapping, apply_similar, defer, exclude, enrich. Решённая запись исчезает из active queue.

## Bulk

- `POST /admin/taxonomy/bulk/preview`
- `POST /admin/taxonomy/bulk/apply`
- `POST /admin/taxonomy/bulk/{batch_id}/rollback`

Dry-run обязателен. Apply и rollback идемпотентны.

## Quality and workflows

- `GET /admin/quality/rules`
- `PATCH /admin/quality/rules/{id}`
- `POST /admin/workflows/{workflow}/run`
- `GET /admin/workflows/operations/{operation_id}`
- `POST /admin/workflows/operations/{operation_id}/retry`
