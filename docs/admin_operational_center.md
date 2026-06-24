# Admin Operational Center

## Экраны

- `/admin/cities/:citySlug?tab=...` — workspace города с десятью вкладками.
- `/admin/quality` — live quality summary и явно обозначенный Stage 2 backlog.
- `/admin/system-health` — сервисы, очереди и persisted alert lifecycle.
- `/admin/analytics` — агрегаты product events и route build events.
- `/admin/system-logs` — correlation filters и bounded pagination.

## API

- `GET /admin/quality`
- `GET /admin/system-health`
- `GET /admin/system-health/alerts`
- `POST /admin/system-health/alerts/{log_id}`
- `GET /admin/analytics`
- `GET /admin/cities/by-slug/{slug}/workspace`

Все endpoints используют `admin_required`. Старые поля workspace сохранены; поле
`operations` добавлено совместимо.

## Action State Contract

1. UI открывает `AdminConfirmDialog`; browser alert/prompt не используется.
2. Во время запроса действие disabled и показывает busy state.
3. Success закрывает dialog, показывает сообщение и перезагружает backend state.
4. Error не меняет состояние на success.
5. Alert transition идемпотентна по `source_log_id`.
6. Каждая transition записывается в admin audit log.

## Alert Lifecycle

`open -> acknowledged -> resolved`. Новая ошибка представлена новым `SystemLog`, поэтому
не теряется из-за закрытого старого alert. Resolved alert можно открыть повторно.

## Определения аналитики

- `active_users`: distinct non-empty `ProductEvent.user_id` за период.
- `place_views`: число `place_viewed`.
- `route_builds`: число `RouteBuildEvent`.
- `route_success_rate`: доля route events без warnings.
- `average_route_points`: среднее `RouteBuildEvent.total_places`.
- `published_share`: опубликованные места / все места выборки.

Frontend получает агрегаты, а не raw events. Отсутствующие метрики показываются как
«Недостаточно данных».

## Monitoring Policy

Health center использует реальные jobs, queues, logs и route events. Логи выдаются
страницами до 200 строк. Рекомендуемый online retention — 30 дней; старые записи
архивируются фоновой задачей. Секреты, токены и персональные данные запрещены в логах.

## Responsive Contract

- Sidebar становится drawer при ширине до 768 px.
- Touch targets — минимум 44 px.
- Safe-area учитывается для drawer, content и dialogs.
- Workspace tabs прокручиваются внутри панели, не расширяя страницу.
- Диалоги ограничены viewport и имеют внутренний scroll.

## Stage 2 TODO

- Daily `CityQualitySnapshot`, history endpoint и nightly aggregation.
- Historical analytics comparison и CSV export.
- Alert deduplication по fingerprint/module/city.
- Worker heartbeat registry с отдельными SLO.
- Audit `city_id` column вместо JSON fallback.
- Table-to-card renderer для всех legacy admin tables.
