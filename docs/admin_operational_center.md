# Admin Operational Center

## Экраны

- `/admin/cities/:citySlug?tab=...` — workspace города с десятью вкладками.
- `/admin/quality` — live quality summary.
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

Рекомендуемые URL:

```text
/admin/places?city=<slug>&photo=false
/admin/verification?city=<slug>&status=needs_recheck
/admin/photos?city=<slug>&source=<provider>
/admin/imports?city=<slug>&job=<job_id>
/admin/enrichment?city=<slug>&batch=<batch_id>
/admin/system-logs?request_id=<request_id>
/admin/audit?entity_type=<type>&entity_id=<id>
```

Если backend пока предоставляет только агрегат и не хранит исходные события, UI сохраняет фильтры и показатель в URL, но не изображает несуществующий список. Для полной детализации продуктовой аналитики нужен отдельный paginated raw-events endpoint с контролем персональных данных.

## API

- `GET /admin/quality`
- `GET /admin/system-health`
- `GET /admin/system-health/alerts`
- `POST /admin/system-health/alerts/{log_id}`
- `GET /admin/analytics`
- `GET /admin/cities/by-slug/{slug}/workspace`

Все endpoints используют `admin_required`. Старые поля workspace сохранены; поле `operations` добавлено совместимо.

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
