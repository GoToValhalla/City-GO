# City GO — Verification Status 2026-07-07

Цель документа — зафиксировать, что уже проверено после серии hotfix по `admin_quality`, production smoke и route page, а что остаётся открытым.

## Зафиксированный stable baseline

- Последний подтверждённый deploy + production smoke: `44eab51` (`Fix route smoke request contract`).
- После него frontend hotfix `1f3ffc7` (`Fix route button text contrast on mobile`) запушен в `main`, но требует отдельного CI/deploy/mobile re-check перед закрытием визуального бага.

## Закрыто / проверено

### 1. `/admin/quality` больше не падает по timeout

Статус: **проверено вручную + production smoke passed**.

Проверено:

- админка открывается с мобильного;
- вкладка `Качество` открывается;
- live counters грузятся;
- видны карточки качества: `Без фото`, `Без адреса`, `Без описания`, `Без часов работы`, `Низкое качество`, `Не подходят для маршрутов`, `Возможные дубли`;
- белого экрана нет;
- timeout/деградированного ответа нет.

Связанные контракты:

- `GET /admin/quality` должен оставаться lightweight/bounded;
- response shape должен сохранять `items`, `total`, `todo`, `limit`, `offset`;
- старые поля `readiness_score`, `manual_review_total`, `review_universe_total`, `auto_excluded_total` нельзя менять без test pack.

### 2. Quality drill-down: `Без фото`

Статус: **проверено вручную**.

Проверено:

- переход из карточки `Без фото` открывает каталог мест;
- список загружается;
- белого экрана нет;
- фильтры/каталог не падают на мобильном.

Наблюдение:

- в выборке видны `медицина` и `услуги`; это ожидаемо для общего каталога качества, но такие категории не должны попадать в пользовательские маршруты.

### 3. Quality drill-down: `Не подходят для маршрутов`

Статус: **проверено вручную**.

Проверено:

- переход из карточки `Не подходят для маршрутов` открывает каталог;
- список загружается;
- в списке есть `медицина` / `услуги`, что подтверждает работу route-exclusion слоя;
- белого экрана нет.

Ожидание:

- служебные категории должны быть видимы оператору в админке как исключённые/не маршрутные;
- они не должны попадать в route builder / пользовательские маршруты.

### 4. Production smoke после backend/smoke hotfix

Статус: **прошёл**.

Проверено smoke:

- `build`: ok;
- `frontend`: ok;
- `backend_ready`: ok;
- `admin_system_health`: ok;
- `admin_quality`: ok;
- `admin_taxonomy_categories`: ok;
- `route_quick`: ok после фикса request body.

Ключевой контракт:

- `route_quick` smoke должен отправлять валидный `UserRouteBuildRequest`: top-level `lat`, `lng`, `start_source`, плюс nested `start`.

## Открыто / не закрывать как проверенное

### OPEN-001: Route page button contrast on mobile

Статус: **исправлено кодом, но ещё не закрыто ручной проверкой**.

Коммит:

- `1f3ffc7` — `Fix route button text contrast on mobile`.

Что было сломано:

- на пользовательском экране маршрута primary/dark buttons отображались как чёрные плашки без читаемого текста;
- затронуты CTA, selected chips и action buttons.

Нужно проверить после CI/deploy:

- route page на мобильном;
- кнопка под `Техническая информация` читается;
- кнопка `Собрать маршрут с быстрым редактированием` читается;
- selected chips читаются;
- disabled buttons читаемы и визуально disabled;
- `-webkit-text-fill-color` не ломает Safari.

### OPEN-002: Mobile admin layout remains rough

Статус: **известная проблема, не закрыта**.

Что видно:

- таблица каталога на мобильном едет по ширине;
- фильтры тесные;
- часть контента уходит за viewport;
- таблицу нужно переводить в card/list mobile renderer.

Это не регрессия текущего backend hotfix, но отдельная UX/P1 задача.

### OPEN-003: Full user route functional check

Статус: **не закрыто**.

Причина:

- ручная проверка route builder остановлена из-за визуального бага кнопок на route page;
- после деплоя `1f3ffc7` нужно заново проверить построение быстрого маршрута.

Нужно проверить:

- quick/auto route строится без 422;
- точки маршрута отображаются;
- в маршруте нет `медицина`, `услуги`, аптек, банков, остановок и прочего stoplist;
- при partial route показываются пользовательские предупреждения без raw technical codes.

## Обязательный test pack для будущих изменений

### Если меняется `services/admin_platform_quality.py`

Обязательно:

- `tests/test_admin_performance_foundation_new.py`
- `tests/test_admin_platform_new.py`
- `tests/test_admin_city_workspace_api_new.py`
- `tests/test_data_quality_foundation_new.py`
- `tests/test_critical_coverage.py`
- `tests/test_admin_platform_quality_endpoint.py`
- `tests/test_admin_quality_resilience.py`

### Если меняется `scripts/production_smoke.py`

Обязательно:

- `tests/test_production_smoke_new.py`
- `tests/test_production_smoke_script.py`
- `tests/test_route_quality_product_fixes.py`

### Если меняется route page frontend

Обязательно:

- route page component tests;
- route result/controls tests;
- frontend build;
- mobile visual check on Safari/iPhone viewport.

## Правило закрытия

Нельзя закрывать пункт как `проверено`, если:

- CI ещё не зелёный;
- deploy ещё не выполнен;
- production smoke ещё не прошёл;
- ручной сценарий не был реально открыт после деплоя;
- проверка выполнена на старом commit, а не на актуальном deployed commit.
