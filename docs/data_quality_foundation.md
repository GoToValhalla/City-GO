# Data Quality Foundation

## Цель

Data Quality Foundation фиксирует проблемы качества данных как отдельный диагностический слой. Он не скрывает города, не меняет публикацию мест и не выключает `is_route_eligible` автоматически.

## Модель

- `data_quality_issues` хранит детерминированно найденные проблемы места или города.
- `data_quality_candidates` хранит предложенные исправления, которые должны пройти review/apply lifecycle.
- `fingerprint` стабилен для одного и того же факта, поэтому повторный refresh идемпотентен.
- JSON-поля используют PostgreSQL `JSONB` и SQLite fallback через существующий паттерн проекта.

## Deterministic Rules First

Refresh сейчас создаёт issues для:

- `missing_photo`;
- `missing_address`;
- `low_confidence`;
- `requires_review`;
- `route_eligibility_suspicious`;
- `weak_description`.

Route eligibility suspicious срабатывает только как issue, если route-eligible место имеет stoplist-сигнал: `pharmacy`, `bank`, `atm`, остановки, служебные и utility категории. Место не изменяется.

## Admin API

- `GET /admin/data-quality/summary`
- `GET /admin/data-quality/issues`
- `POST /admin/data-quality/issues/refresh`
- `POST /admin/data-quality/bulk-actions/preview`
- `POST /admin/data-quality/bulk-actions/apply`

Все endpoints защищены `admin_required`.

## Bulk Safety

`propose_exclude_from_routes` создаёт `DataQualityCandidate(candidate_type="route_eligibility_change")` со статусом `pending`.

Запрещено на этом этапе:

- менять `Place.is_route_eligible`;
- auto-apply AI;
- запускать LLM по backlog;
- включать hard publication blocking.

`defer_issues`, `ignore_issues` и `mark_resolved_if_current_state_ok` меняют только lifecycle issue. `mark_resolved_if_current_state_ok` перепроверяет текущее состояние места перед закрытием.

## Readiness Diagnostics

`compute_city_readiness` возвращает `data_quality_diagnostics`:

- `photo_coverage`;
- `address_coverage`;
- `low_confidence`;
- `review_backlog`;
- `route_eligibility_suspicious`.

`DATA_QUALITY_HARD_GATES_ENABLED=false` по умолчанию. Диагностика не блокирует публикацию и не меняет public API.

## AI Policy Hooks

AI сейчас не запускается. Будущий controlled AI слой может работать только после фильтрации, оценки стоимости и явного подтверждения администратора. Допустимые будущие задачи: классификация route eligibility, нормализация категории и подсказка поискового запроса для фото.
