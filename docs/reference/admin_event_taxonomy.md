# Admin Event Taxonomy

## Product events

- `place_viewed` — карточка места показана.
- `place_detail_opened` — открыта детальная страница.
- `route_generation_success` — маршрут собран.
- `route_generation_failed` — маршрут не собран.
- `import_finished` / `import_failed` — итог импорта.
- `enrichment_finished` — итог обогащения.

Dimensions по мере доступности: `city_slug`, `place_id`, `user_id`,
`payload.channel` (`web`/`telegram`) и `payload.environment`.

## Admin audit actions

Мутации именуются глаголом и сущностью: `publish_city`, `unpublish_place`,
`acknowledged_alert`, `resolved_alert`. Повторная идемпотентная операция не должна
повторно менять бизнес-состояние.

## Correlation

`SystemLog.request_id` связывает логи запроса. `city_slug`, `place_id`, `route_id`,
`actor_id` используются для drill-down. Секреты и персональные данные запрещены.
