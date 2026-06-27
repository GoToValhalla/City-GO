# Data Quality Foundation

## Цель

Data Quality Foundation фиксирует проблемы качества данных как отдельный диагностический слой. Он не скрывает города, не меняет публикацию мест и не выключает `is_route_eligible` автоматически.

## Модель

- `data_quality_issues` хранит детерминированно найденные проблемы места или города.
- `data_quality_candidates` хранит предложенные исправления, которые должны пройти review/apply lifecycle.
- `fingerprint` стабилен для одного и того же факта, поэтому повторный refresh идемпотентен.
- JSON-поля используют PostgreSQL `JSONB` и SQLite fallback через существующий паттерн проекта.

## Operational Split

В админке есть два соседних, но разных контура:

- **Data Quality** — диагностические issues и candidates: фото, адреса, слабые описания, подозрительная route eligibility.
- **Place Verification** — очередь проверки существования/актуальности места: `verified`, `needs_recheck`, `unverified`, `low/unknown confidence`.

Эти контуры не должны подменять друг друга. Data Quality может подсказать, что место проблемное, но не подтверждает физическое существование места. Place Verification подтверждает или отклоняет место, но не является bulk-механизмом route eligibility.

## Deterministic Rules First

Refresh сейчас создаёт issues для:

- `missing_photo`;
- `missing_address`;
- `low_confidence`;
- `requires_review`;
- `route_eligibility_suspicious`;
- `weak_description`.

Route eligibility suspicious срабатывает только как issue, если route-eligible место имеет stoplist-сигнал: `pharmacy`, `bank`, `atm`, остановки, служебные и utility категории. Место не изменяется.

## Data Quality Admin API

- `GET /admin/data-quality/summary`
- `GET /admin/data-quality/issues`
- `POST /admin/data-quality/issues/refresh`
- `POST /admin/data-quality/bulk-actions/preview`
- `POST /admin/data-quality/bulk-actions/apply`

Все endpoints защищены `admin_required`.

## Place Verification Admin API

Экран админки **Проверка мест** использует отдельные endpoints:

- `GET /admin/place-verifications/summary`
- `GET /admin/place-verifications/queue`
- `POST /admin/place-verifications/places/{place_id}/verify`
- `POST /admin/place-verifications/places/{place_id}/confirm-nearby`
- `GET /admin/place-verifications/stats`

`GET /admin/place-verifications/summary` — компактный контракт для карточек и мобильного экрана проверки. Он поддерживает опциональный `city_slug` и возвращает:

```json
{
  "queue_total": 0,
  "needs_recheck": 0,
  "unverified": 0,
  "low_confidence": 0,
  "verified_today": 0
}
```

Если этот endpoint недоступен, frontend не должен показывать рабочую очередь как исправную: экран проверки мест теряет свои верхние счётчики и может показать общую ошибку backend.

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

## Smoke Checks

После деплоя backend нужно проверить:

```bash
curl -sS "$API_BASE/admin/data-quality/summary"
curl -sS "$API_BASE/admin/place-verifications/summary"
```

Для production с авторизацией использовать тот же admin auth-механизм, что и админка. Ожидаемый результат для обоих запросов — HTTP 200 и JSON со счётчиками, без HTML error page и без `404 Not Found`.
