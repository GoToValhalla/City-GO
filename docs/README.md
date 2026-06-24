# Документация City GO

## Основные документы

| Документ | Назначение |
|---|---|
| [`master_technical_spec.md`](master_technical_spec.md) | Главный продуктово-технический документ. |
| [`implementation_status_and_next_steps.md`](implementation_status_and_next_steps.md) | Актуальный статус и следующие шаги. |
| [`architecture/application_architecture_ru.md`](architecture/application_architecture_ru.md) | Архитектура backend, frontend и Telegram. |
| [`architecture/backend_file_map.md`](architecture/backend_file_map.md) | Карта backend-файлов. |

## Админка и данные

| Документ | Назначение |
|---|---|
| [`admin_guide.md`](admin_guide.md) | Запуск и рабочие процессы интегрированной админки. |
| [`admin_operational_center.md`](admin_operational_center.md) | City Workspace, мониторинг, аналитика и alerts. |
| [`architecture/taxonomy_automation_center.md`](architecture/taxonomy_automation_center.md) | Модели, rule engine, Quality Score V2, workflows и bulk. |
| [`reference/category_dictionary.md`](reference/category_dictionary.md) | Иерархия, русские названия и таблица решений. |
| [`reference/taxonomy_api.md`](reference/taxonomy_api.md) | Admin API Taxonomy Center. |
| [`runbooks/taxonomy_rollback.md`](runbooks/taxonomy_rollback.md) | Безопасный откат массовой переклассификации. |
| [`testing-and-allure.md`](testing-and-allure.md) | Pytest, Vitest и CI. |
| [`release_checklist.md`](release_checklist.md) | Release gates. |
| [`backup_restore.md`](backup_restore.md) | Backup и restore PostgreSQL. |
| [`production_data_refresh.md`](production_data_refresh.md) | Production import и refresh данных. |

## Маршруты

| Документ | Назначение |
|---|---|
| [`route_generation_status_and_roadmap.md`](route_generation_status_and_roadmap.md) | Состояние route engine. |
| [`architecture/route_pipeline_observability.md`](architecture/route_pipeline_observability.md) | Наблюдаемость маршрутов. |
| [`architecture/route_scoring_explanation.md`](architecture/route_scoring_explanation.md) | Scoring и explanation. |
| [`architecture/place_route_ui_data_contract.md`](architecture/place_route_ui_data_contract.md) | Контракт мест и route points. |

## Route layers

1. Editorial routes: `GET /routes/...`.
2. Legacy itinerary: `POST /routes/generate`, `POST /routes/replan`.
3. Product route layer: `POST /v1/user-routes/build`, `POST /v1/user-routes/correct`, `POST /v1/recommendations/route`.

Новая route-разработка использует product route layer. Категорийный допуск централизован в taxonomy route policy.
