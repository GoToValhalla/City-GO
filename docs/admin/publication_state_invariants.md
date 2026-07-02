# Publication state invariants

Этот документ фиксирует границы между product publication state, import operational state, quality state и manual review state.

## City product state

Поля product publication state:

- `City.is_active`
- `City.launch_status`

Право менять эти поля имеют только:

- `services/admin_city_publication_service.py` — явная публикация/снятие публикации города;
- `scripts/repair_publication_states.py` — явный repair action с dry-run/apply;
- будущие explicit admin actions, если они пишут audit/reason и проходят тесты инвариантов.

Не имеют права менять City product state:

- import jobs;
- enrichment jobs;
- snapshot refresh;
- admin overview/read endpoints;
- publication reconciliation по умолчанию;
- quality/readiness scoring;
- Telegram moderation.

Import status `failed/partial/stale/running` — это operational state. Он не должен переводить опубликованный город в draft/hidden/unpublished.

## Place publication state

Поля publication state:

- `Place.is_active`
- `Place.is_published`
- `Place.is_visible_in_catalog`
- `Place.is_route_eligible`
- `Place.is_searchable`
- `Place.publication_status`

Published place нельзя сбрасывать в draft/hidden/rejected из import/enrichment/reconciliation. Снять место с публикации можно только:

- явным admin action;
- явной destructive policy с reason/audit;
- repair script с явным флагом.

Import/enrichment/backfill могут улучшать raw/data-quality поля, но не должны выключать уже published flags.

## Manual review state

Manual queue — только explicit manual cases:

- `publication_status in ('needs_review', 'needs_manual_review', 'deferred')`;
- либо `review_queue_items.status='open'` для явно ручной проверки.

Не являются manual queue по умолчанию:

- `draft`;
- `auto_backlog`;
- `low_confidence`;
- отсутствие фото;
- отсутствие адреса;
- низкая уверенность без конфликта/high-risk reason.

Telegram moderation использует только manual queue. Если manual queue пустая, бот пишет `Очередь пуста` и не подтягивает draft/backlog.

## Auto backlog

Auto backlog — это очередь для deterministic policy, enrichment и backfill. Она не должна превращаться в ручную задачу на 17k мест.

Trusted auto publish допустим, если место:

- `draft/auto_backlog/low_confidence`;
- имеет координаты;
- имеет адрес;
- `address_source` официальный/сайтовый/provider official;
- `address_confidence >= 0.85`;
- `quality_score >= 65`;
- не closed/inactive/spam;
- не duplicate suspected;
- категория подходит для catalog/route.

Отсутствие фото не блокирует trusted auto publish. Это отдельная data-quality/enrichment задача.

## Admin statistics semantics

- `Требуют проверки` = только manual review queue.
- `Не проверено авто` = auto backlog.
- `Низкая уверенность` = quality bucket, не ручная очередь.
- `Ошибка импорта` = operational import problem, не product hidden state.
- `Активные города` = `City.is_active=true AND City.launch_status='published'`.

## Protected invariants

Защищены кодом и должны покрываться тестами:

1. Failed/partial import не снимает опубликованный город с публикации.
2. Import/enrichment/reconciliation не снимает published place с публикации.
3. Publication reconciliation не делает destructive bulk reset без явного destructive флага и reason.
4. Manual moderation не показывает draft/auto_backlog/low_confidence.
5. Admin overview разделяет manual review, auto backlog и quality buckets.
6. Repair scripts работают через dry-run по умолчанию и пишут snapshot/report перед apply.
