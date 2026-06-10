# City Go — Route Correction Engine

Дата: 2026-06-05.

## Цель

Correction actions должны возвращать валидный улучшенный маршрут, а не просто удалять точку и ухудшать результат.

## Actions

- `remove_place` — удаляет target place и пытается добавить ближайшую замену той же категории.
- `shorten_route` — удаляет точку с худшим `score / minutes`, а не последнюю точку.
- `rebuild_from_here` — пересобирает маршрут от текущих координат пользователя.
- `avoid_category` — пересобирает маршрут с категорией target place как hard avoid.
- `extend_route` — пытается добавить ближайшее доступное место, которого ещё нет в маршруте.

## Modules

- `services/user_route_correct_service.py` — orchestration и rebuild/recalc boundary.
- `services/user_route_correction_actions.py` — применяет action к списку places.
- `services/user_route_correction_policy.py` — pure logic: value-per-minute, excluded ids, target category.
- `services/user_route_replacement_loader.py` — DB lookup для replacement/extend.

## Safety

Replacement не берёт:

- места уже в текущем маршруте;
- target removed place;
- `closed` / `temporarily_closed` / inactive места;
- места без координат;
- место другой категории при `remove_place`.

Если замена не найдена, маршрут пересчитывается из оставшихся точек без падения.
