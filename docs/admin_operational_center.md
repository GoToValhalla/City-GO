# Admin Operational Center

## Экраны

- `/admin/cities/:citySlug?tab=...` — workspace города с десятью вкладками.
- `/admin/quality` — live quality summary, безопасный автопилот и очередь возможных дублей.
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
12. Critical coverage metric открывает `/admin/data-quality/cities/{city_slug}/critical-coverage/places` с `bucket` и `reason`.

Рекомендуемые URL:

```text
/admin/places?city=<slug>&photo=false
/admin/verification?city=<slug>&status=needs_recheck
/admin/photos?city=<slug>&source=<provider>
/admin/imports?city=<slug>&job=<job_id>
/admin/enrichment?city=<slug>&batch=<batch_id>
/admin/coverage?tab=gaps&city_slug=<slug>&status=critical
/admin/coverage?tab=gaps&city_slug=<slug>&gap_reason=not_route_eligible
/admin/data-quality/cities/<slug>/critical-coverage/places?bucket=route_blocker
/admin/data-quality/cities/<slug>/critical-coverage/places?bucket=card_blocker&reason=missing_image_url
/admin/system-logs?request_id=<request_id>
/admin/audit?entity_type=<type>&entity_id=<id>
```

Если backend пока предоставляет только агрегат и не хранит исходные события, UI сохраняет фильтры и показатель в URL, но не изображает несуществующий список. Для полной детализации продуктовой аналитики нужен отдельный paginated raw-events endpoint с контролем персональных данных.

## API

- `GET /admin/quality`
- `GET /admin/data-quality/summary`
- `GET /admin/data-quality/cities/{city_slug}/critical-coverage`
- `GET /admin/data-quality/cities/{city_slug}/critical-coverage/places`
- `GET /admin/data-quality/duplicates`
- `GET /admin/data-quality/issues`
- `POST /admin/data-quality/issues/refresh`
- `POST /admin/data-quality/bulk-actions/preview`
- `POST /admin/data-quality/bulk-actions/apply`
- `POST /admin/data-quality/automation/preview`
- `POST /admin/data-quality/automation/apply`
- `POST /admin/data-quality/automation/rollback`
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

- `services.admin_platform_quality.city_quality_row` — live score по реальному состоянию маршруто-релевантных мест;
- `/admin/quality` — список городов с live `readiness_score`;
- `/admin/cities/by-slug/{slug}/workspace` — тот же live score в workspace города;
- `/admin/data-quality/summary` — live `coverage_score` в `by_city`.

### Route Review Universe

Операционная готовность больше не равна качеству всех импортированных объектов. Ручная проверка считается только по `review_universe_total` — местам, которые могут быть туристическими или маршрутными кандидатами.

Stoplist категории (`pharmacy`, `bank`, `atm`, `bus_stop`, `transit_stop`, `parking`, `toilets`, `hospital`, `clinic`, `police`, `service` и другие инфраструктурные категории) попадают в `excluded_by_design` / `auto_excluded_total` и не раздувают процент `нужно проверить`.

`/admin/quality` возвращает дополнительные поля:

- `review_universe_total` — сколько мест реально участвует в ручной оценке качества;
- `manual_review_total` — сколько ручных блокеров найдено внутри этой вселенной;
- `auto_excluded_total` — сколько мест исключено правилами как не маршрутные точки;
- `blockers.excluded_by_design` — тот же счётчик внутри breakdown.

Этот контракт нужен, чтобы город с тысячами аптек, банков, остановок и сервисных POI не выглядел как ручная работа оператора. Оператор должен видеть только `data_gap` / `review_candidate`, а автоматические исключения должны быть прозрачной статистикой.

### Critical Data Coverage v2

`services.data_quality.critical_coverage` разделяет маршрутную готовность и полноту карточки.

`/admin/quality` возвращает summary поля:

- `route_candidate_total` — туристические/маршрутные кандидаты;
- `route_ready_total` — места без route blockers;
- `route_blockers_total` — места, которые нельзя безопасно использовать в маршруте;
- `card_ready_total` — места с достаточной карточкой;
- `card_blockers_total` — места с user-facing gaps;
- `auto_enrichment_total` — места, которые можно отправить в enrichment;
- `critical_manual_review_total` — места с конфликтом, pending photo candidate или ручной очередью;
- `critical_coverage` — полный breakdown по route/card/auto/manual/coverage/next_actions.

Drill-down endpoints:

- `GET /admin/data-quality/cities/{city_slug}/critical-coverage` — city-level summary.
- `GET /admin/data-quality/cities/{city_slug}/critical-coverage/places?bucket=route_blocker|card_blocker|auto_enrichment_candidate|manual_review|optional_gap|not_applicable&reason=<reason>` — paginated list of places behind the counter.

Rules:

- photo gaps block card readiness, not route readiness;
- pending photo candidates require manual review and must not be silently approved;
- opening hours are route-critical for museums/galleries/paid attractions/restaurants/cafes/bars;
- opening hours are not route-critical for landmarks, monuments, viewpoints and open squares;
- normalized `PlaceSchedule` rows count as hours coverage;
- service/utility categories are `not_applicable` for tourist routes by default.

### Data Quality Autopilot

Stage 1 автопилота — только безопасное и обратимое исключение очевидных stoplist мест из маршрутов.

Разрешённое действие:

- `auto_exclude_stoplist_from_routes` берёт только open `route_eligibility_suspicious` issues;
- место должно быть `is_route_eligible=true`;
- stoplist категория должна подтверждаться issue evidence или текущей категорией места;
- `preview` ничего не меняет, а возвращает `affected_count`, `blocked_count`, sample, warnings и proposed patch;
- `apply` требует `confirm=true`;
- `rollback` требует `candidate_ids` и `confirm=true`.

Guardrails:

- если после применения в городе осталось бы меньше `8` route-eligible мест, запись блокируется как `route_inventory_guard`;
- blocked записи не мутируются и остаются в очереди;
- автопилот не удаляет места, не снимает публикацию, не merge-ит дубли и не генерирует фото/адреса/описания;
- каждое применение создаёт `DataQualityCandidate(candidate_type=route_eligibility_auto_exclusion, status=auto_applied)`;
- `Place.is_route_eligible` меняется на `false`, `route_exclusion_reason` на `non_tourist_category_policy`;
- source issue переводится в `auto_applied`;
- rollback восстанавливает `Place.is_route_eligible` и `route_exclusion_reason` из `rollback_patch`, candidate переводит в `rolled_back`, issue открывает обратно.

UI-контракт `/admin/quality`:

- блок `Безопасный автопилот` показывает, сколько можно применить и сколько заблокировано guardrail;
- кнопка disabled, если применимых записей нет или уже идёт действие;
- результат применения показывается рядом с кнопкой автопилота;
- сообщения по дублям показываются отдельно в секции дублей.

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
- Кнопка `Не дубль` вызывает `ignore_issues` и убирает группу из активных дублей как не дубль.
- Кнопка `Отложить` вызывает `defer_issues`; группа остаётся видимой как deferred, чтобы её можно было вернуться и разобрать позже.
- Оператор должен открыть места, сравнить адреса/координаты/фото/источники и только после этого принимать решение о merge/delete/reject.

Historical cleanup 2026-06-28:

- убран legacy alias `_city_row`; новый код должен использовать только `city_quality_row`;
- `/admin/data-quality/summary` переведён с `City.readiness_score` на live score;
- refresh перестал оставлять исправленные проблемы открытыми;
- `/admin/quality` считает ручной процент по `review_universe_total`, а stoplist/служебные места выводит как `excluded_by_design`;
- добавлен Stage 1 `Data Quality Autopilot`: preview/apply/rollback для обратимого auto-exclude stoplist мест из маршрутов;
- добавлен `Critical Data Coverage / Quality Rules v2` read-only triage и drill-down endpoints для route/card/auto/manual buckets;
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

- Materialize `quality_bucket` / `PlaceQualityState` after validating Critical Data Coverage v2 numbers on real cities.
- Add bucket filters to `/admin/places` and direct UI links from quality counters.
- Expand Data Quality Autopilot: confidence tiers for more reversible actions after preview/apply/rollback coverage.
- Dedupe scorer tiers: auto-dismiss low-confidence, one-click candidates for high confidence, manual only for ambiguous cases.
- Paginated raw product events с privacy-safe полями.
- Daily `CityQualitySnapshot`, history endpoint и nightly aggregation.
- Historical analytics comparison и CSV export.
- Alert deduplication по fingerprint/module/city.
- Worker heartbeat registry с отдельными SLO.
- Audit `city_id` column вместо JSON fallback.
- Унифицированный table-to-card renderer для legacy admin tables.
- Scheduled weekly Data Coverage Assurance job.
- Admin actions for direct scope expansion and manual POI creation from gap rows.