# CITY GO — Legacy Code Register

Дата начала реестра: 2026-07-02

Назначение: фиксировать код, который больше не является source of truth, но сохраняется как историческая реализация. Такой код не удаляется сразу, но должен быть явно помечен как `LEGACY`, описан и запрещён для нового использования.

## Правила работы с legacy

1. Не удалять сразу, если код связан с миграциями, историческими данными или production rollback.
2. Помечать в начале файла или класса:
   - статус;
   - как работало;
   - почему legacy;
   - чем заменено;
   - что запрещено.
3. Не использовать legacy-модели/сервисы в новых endpoint/test fixtures.
4. Активный source of truth должен быть указан явно.
5. Любой endpoint должен проверяться по цепочке: router -> service -> model/table -> tests.

## Реестр

| Область | Legacy artifact | Статус | Active source of truth | Комментарий |
|---|---|---|---|---|
| Public catalog change review | `models/place_change_review.py` / `PlaceChangeReview` / table `place_change_reviews` | LEGACY, historical compatibility only | `models/review_queue_item.py` / `ReviewQueueItem` with `field_name='place_change'`, `status='open'` | Старый row-per-field workflow. Активные `/admin/place-change-reviews/*` endpoint'ы читают `ReviewQueueItem`, не `PlaceChangeReview`. |

## Первый подтверждённый кейс

### `PlaceChangeReview` vs `ReviewQueueItem`

Фактическая цепочка активного endpoint:

```text
routers/admin_place_change_review.py
  -> services/place_change_review_service.py
  -> _open_review_row()
  -> ReviewQueueItem
  -> field_name='place_change'
  -> status='open'
```

Что было ошибкой:

- тесты и фиксы создавали `PlaceChangeReview`, потому что модель называлась похоже;
- endpoint при этом искал `ReviewQueueItem`, поэтому approve/reject возвращали 404 или падали на NOT NULL constraints;
- это показало, что в проекте есть неразмеченные legacy-дубли.

Текущее решение:

- `PlaceChangeReview` оставлен как историческая модель;
- файл помечен как `LEGACY MODEL`;
- новый код не должен использовать эту модель;
- active review workflow — только `ReviewQueueItem`.

## Следующие зоны аудита

- publication services/scripts;
- import job tables/services;
- review queue services;
- admin overview/metrics summaries;
- Telegram moderation handlers;
- old route/itinerary builders;
- old enrichment scripts.
