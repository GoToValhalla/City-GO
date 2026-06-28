# Admin Operational Center

## Экраны

- `/admin/cities/:citySlug?tab=...` — workspace города с десятью вкладками.
- `/admin/quality` — live quality summary и очередь возможных дублей.
- `/admin/coverage` — покрытие данных по городам.
- `/admin/coverage?tab=gaps` — Data Coverage Assurance: must-have POI gaps, причины и действия.
- `/admin/system-health` — сервисы, очереди и persisted alert lifecycle.
- `/admin/analytics` — агрегаты product events и route build events.
- `/admin/system-logs` — correlation filters и bounded pagination.
- `/admin/imports?city=<slug>&job=<id>` — конкретный запуск импорта или обогащения.
- `/admin/enrichment?city=<slug>&batch=<id>` — конкретный ручной пакет обогащения.

## Drill-down Contract

Административная статистика не должна быть тупиковой.

1. Любой счётчик открывает набор записей, из которого он рассчитан.
2. Город, категория, статус, период и остальные фильтры сохраняются в URL.
3. Запуск импорта или pipeline имеет ссылку с `job`.
4. Ручной пакет обогащения имеет ссылку с `batch`.
5. Из запуска доступны шаги, счётчики, логи, аудит и изменённые места.
6. Из пакета доступны исходный CSV, enriched CSV, preview, result и затронутые места.
7. Из очереди проверки, фото, конфликта или лога можно открыть карточку места.
8. `request_id` открывает всю correlation chain в системных логах.
9. Инцидент открывает логи по module, request ID и городу.
10. Внешний источник фото или обогащения хранится как отдельная безопасная ссылка.
11. Must-have coverage metric открывает `/admin/coverage?tab=gaps` с сохранённым городом, статусом и причиной.

Рекомендуемые URL:

```text
/admin/places?city=<slug>&photo=false
/admin/verification?city=<slug>&status=needs_recheck
/admin/photos?city=<slug>&source=<provider>
/admin/imports?city=<slug>&job=<job_id>
/admin/enrichment?city=<slug>&batch=<batch_id>
/admin/coverage?tab=gaps&city_slug=<slug>&status=critical
/admin/coverage?tab=gaps&city_slug=<slug>&gap_reason=not_route_eligible
/admin/system-logs?request_id=<request_id>
/admin/audit?entity_type=<type>&entity_id=<id>
```

Если backend пока предоставляет только агрегат и не хранит исходные события, UI сохраняет фильтры и показатель в URL, но не изображает несуществующий список. Для полной детализации продуктовой аналитики нужен отдельный paginated raw-events endpoint с контролем персональных данных.

## API

- `GET /admin/quality`
- `GET /admin/data-quality/summary`
- `GET /admin/data-quality/duplicates`
- `GET /admin/data-quality/issues`
- `POST /admin/data-quality/issues/refresh`
- `POST /admin/data-quality/bulk-actions/preview`
- `POST /admin/data-quality/bulk-actions/apply`
- `GET /admin/system-health`
- `GET /admin/system-health/alerts`
- `POST /admin/system-health/alerts/{log_id}`
- `GET /admin/analytics`
- `GET /admin/cities/by-slug/{slug}/workspace`
- `GET /admin/coverage-gaps`
- `GET /admin/coverage-gaps/cities/{city_slug}`
- `POST /admin/coverage-gaps/sync`
- `POST /admin/coverage-gaps/refresh`
- `PATCH /admin/coverage-gaps/{gap_id}`

Все endpoints используют `admin_required`. Старые поля workspace сохранены; поле `operations` добавлено совместимо.

## Data Quality Contract

`City.readiness_score` больше не является источником истины для экранов качества. Это legacy/stored значение оставлено только как исторический след и diagnostic field в ответах `stored_readiness_score` / `stored_coverage_score`.

Текущий источник истины для операционной готовности города:

- `services.admin_platform_quality.city_quality_row` — live score по реальному состоянию мест;
- `/admin/quality` — список городов с live `readiness_score`;
- `/admin/cities/by-slug/{slug}/workspace` — тот же live score в workspace города;
- `/admin/data-quality/summary` — live `coverage_score` в `by_city`.

`services.data_quality.refresh.refresh_data_quality_issues` синхронизирует состояние issues:

1. создаёт новые deterministic issues;
2. обновляет существующие open issues;
3. переоткрывает `resolved`, если проблема снова появилась;
4. переводит stale open/candidate/deferred issues в `resolved`, если текущий refresh их больше не нашёл.

Без явного `status` список `/admin/data-quality/issues` возвращает только актуальные статусы из `OPEN_STATUSES`. Исторические записи доступны через явный фильтр, например `status=resolved`.

### Possible Duplicate Review

`possible_duplicate` — ручная очередь проверки, а не автоматическое удаление или merge.

- `GET /admin/data-quality/duplicates` возвращает сгруппированные дубли по городу, нормализованному названию и набору place IDs.
- Группа содержит `issue_ids`, `place_ids`, `places`, `status_counts`, evidence и временные метки.
- `/admin/quality` показывает первые группы дублей и ссылки на карточки мест.
- Кнопка `В проверку` вызывает `propose_duplicate_review`, создаёт `DataQualityCandidate(candidate_type=duplicate_review)` и переводит issues в `candidate_created`; сами места не меняются.
- Кнопка `Не дубль` вызывает `ignore_issues` и убирает группу из активной очереди.
- Кнопка `Отложить` вызывает `defer_issues`; группа остаётся видимой как deferred, чтобы её можно было вернуться и разобрать позже.
- Оператор должен открыть места, сравнить адреса/координаты/фото/источники и только после этого принимать решение о merge/delete/reject.

Historical cleanup 2026-06-28:

- убран legacy alias `_city_row`; новый код должен использовать только `city_quality_row`;
- `/admin/data-quality/summary` переведён с `City.readiness_score` на live score;
- refresh перестал оставлять исправленные проблемы открытыми;
- возможные дубли (`possible_duplicate`) остаются ручной очередью, без автоматического merge/delete.

## Data Coverage Assurance Contract

Город нельзя считать готовым только по факту завершённого импорта. Must-have POI должны быть:

1. найдены и сопоставлены с `places`; или
2. иметь понятную причину отсутствия; и
3. не иметь blocking gap reason для critical policy.

Основные причины: `outside_bbox`, `unsupported_tag`, `source_absent`, `hidden_by_policy`, `missing_name`, `missing_coordinates`, `duplicate_candidate`, `not_imported_scope`, `not_visible_in_catalog`, `not_route_eligible`.

Админка должна показывать не просто список дыр, а следующий операционный шаг: расширить scope, расширить taxonomy, опубликовать найденное место, включить route eligibility, смержить дубль или добавить место вручную.

## Action State Contract

1. UI запрашивает подтверждение опасного действия.
2. Во время запроса действие disabled и показывает busy state.
3. Success закрывает dialog, показывает сообщение и перечитывает backend state.
4. Error не меняет состояние на success.
5. Решённая запись удаляется из активной очереди, после чего выполняется refill.
6. Каждая transition записывается в admin audit log.

## Alert Lifecycle

`open -> acknowledged -> resolved`. Новая ошибка представлена новым `SystemLog`, поэтому не теряется из-за закрытого старого alert. Resolved alert можно открыть повторно.

## Определения аналитики

- `active_users`: distinct non-empty `ProductEvent.user_id` за период.
- `place_views`: число `place_viewed`.
- `route_builds`: число `RouteBuildEvent`.
- `route_success_rate`: доля route events без warnings.
- `average_route_points`: среднее `RouteBuildEvent.total_places`.
- `published_share`: опубликованные места / все места выборки.

Frontend получает агрегаты, а не персональные raw events. Отсутствующие метрики показываются как «Недостаточно данных».

## Monitoring Policy

Health center использует реальные jobs, queues, logs и route events. Логи выдаются страницами до 200 строк. Рекомендуемый online retention — 30 дней; старые записи архивируются фоновой задачей. Секреты, токены и персональные данные запрещены в логах.

## Responsive Contract

- Sidebar становится drawer при ширине до 768 px.
- Touch targets — минимум 44 px.
- Safe-area учитывается для drawer, content и dialogs.
- Workspace tabs прокручиваются внутри панели, не расширяя страницу.
- Диалоги ограничены viewport и имеют внутренний scroll.
- Drill-down ссылки должны оставаться доступными в карточном mobile-представлении.

## Следующие доработки

- Paginated raw product events с privacy-safe полями.
- Daily `CityQualitySnapshot`, history endpoint и nightly aggregation.
- Historical analytics comparison и CSV export.
- Alert deduplication по fingerprint/module/city.
- Worker heartbeat registry с отдельными SLO.
- Audit `city_id` column вместо JSON fallback.
- Унифицированный table-to-card renderer для legacy admin tables.
- Scheduled weekly Data Coverage Assurance job.
- Admin actions for direct scope expansion and manual POI creation from gap rows.