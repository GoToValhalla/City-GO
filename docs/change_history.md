# CHANGE HISTORY

## 2026-07-14

### Sites UI/UX integration — follow-up audit and CSS fixes

- Подтверждена корректная интеграция `b40babd` (Sites UI/UX): fast-forward
  pull, конфликтов нет, порядок CSS-каскада (`.app-screen` поверх `:root`)
  проверен по байтовым смещениям в собранном бандле.
- Найдены и исправлены 11 случаев конфликта старой/новой темы: правила, где
  `color`/`background` уже использовали новые `--cg-*` токены, но соседний
  `border-color`/`border`/градиент на том же селекторе оставался захардкожен
  старыми rgba-значениями тёмной темы и не перекрашивался в новой светлой
  теме. Исправлено через существующий в проекте паттерн
  `color-mix(in srgb, var(--cg-X) N%, var(--cg-border-soft))`
  (`cards.css`, `discovery.css`, `place-map.css`, `place-ui.css`,
  `places.css`, `responsive.css`).
- `CityPicker`: добавлен `aria-live="polite"` на счётчик результатов поиска
  (`city-picker-summary`), чтобы screen reader объявлял изменение числа
  найденных городов при вводе запроса.
- Проверено и признано не дефектом: отсутствие focus-trap/focus-return в
  `CityPicker` — это существующий по всему проекту базовый уровень
  доступности диалогов (сравнение с `PlaceMapPanel`), а не регресс,
  внесённый этой интеграцией; изменения не вносились.
- Проведён аудит состояний loading/empty/partial-data/warning/error для
  places catalog, place details, nearby, open-now, route builder, route
  draft, route result — везде raw backend-ошибки пользователю не
  показываются, mock/demo-данные не используются, add/replace/remove для
  маршрутов работают через прежние API. Дефектов не найдено.
- Локальные проверки: frontend `npm test` — 89 файлов / 324 теста пройдено,
  1 тест пропущен; `npm run lint` — PASS; `npm run build` — PASS.
- CI и deploy не запускались.

## 2026-07-13

### Sites UI/UX integrated into the production web frontend

- Подтверждено, что Sites commit `efebbfe` принадлежит отдельному внутреннему
  репозиторию и не мог появиться в GitHub `GoToValhalla/City-GO` автоматически.
- Светлая mobile-first оболочка из Sites адаптирована к существующему
  React/Vite frontend без перезаписи FastAPI API, admin UI и git-истории.
- Добавлен поисковый выбор города по названию, региону, стране и slug;
  одноимённые города показываются как `Название · Регион · Страна`.
- Главная получила новый header, hero с MapLibre-картой, быстрые сценарии,
  четыре карточки реальных мест и нижнюю мобильную навигацию.
- `POST /routes/random` получил два UI-сценария: «Случайные места» с заданным
  временем и «Случайное настроение» со случайными временем и 1–3 категориями.
- Добавлены unit/component tests для city identity/search, выбора города,
  random route plan и обоих payload-вариантов.
- Архитектурный контракт обновлён в
  `docs/architecture/web_bot_ui_redesign.md`.
- Локальные проверки: frontend `npm test` — 89 файлов / 324 теста пройдено,
  1 файл / 1 тест пропущен; `npm run lint` — PASS; `npm run build` — PASS.
- CI и deploy не запускались.

## 2026-07-06

### Destination Data Pipeline + Operational Workspace v1

- Добавлен `DestinationDataPipelineRun` и Alembic migration `a1b2c3d4e5f6`.
- Добавлены admin endpoints `/admin/destinations/{slug}/data-pipeline/*`, `/memberships/recalculate`, `/readiness`, `/review-items`.
- Реализован backend-owned bbox pipeline: deterministic scope candidates, idempotent place upsert, materialized memberships, service-only hiding, enrichment through `PlaceDataMergeService`, `ReviewItem` for protected/conflicting data, readiness metrics.
- Расширена admin Destination detail page: readiness cards, coverage, run actions, latest run, run history, pending reviews, public destination catalog link.
- Добавлены backend regression tests for run/import/enrichment/recalc/readiness/public catalog/route candidates and frontend workspace tests.
- Документация: `docs/architecture/destination_data_pipeline_v1.md`.

### Destination-first foundation v1
- Добавлены модели `Destination`, `DestinationScope`, `DestinationPlaceMembership`, миграция и backfill городов.
- Feature flags для phased rollout catalog/route/import reads.
- Public API `/v1/destinations`, `destination_slug` в каталоге мест, compatibility layer для city flow.
- Route candidate retrieval и walking guard через destination membership под флагом.
- Admin API и UI для направлений (list + detail).
- Документация: `docs/architecture/destination_foundation_v1.md`.
- Исправлена потеря `destination_slug` в `place_list_params_service.normalize_place_list_params`.


### Adaptive route refactor
- Route builder no longer injects hidden `walk` interests on backend or frontend.
- Added adaptive interest expansion: primary exact matches, related categories,
  neutral POI and explicit warnings/user explanation.
- Removed emergency assembly fallback and budget gap fill from recommendation
  route flow; short routes now remain honest instead of being silently padded.
- Added route-level metadata: `route_quality_status`, `route_completeness`,
  `matched_interest_count`, `expansion_level`, `fallback_level`,
  `user_explanation` and `debug_trace`.
- Added regression tests for no interests, zero/one/many exact matches, sparse
  pool, budget target sizing, same-category pools, hard avoided categories,
  budget-fit minimal routes, far starts and algorithm-error gates.
- Architecture note added: `docs/routes/adaptive_route_refactor.md`.

## 2026-06-06

### Route builder P0 stabilization
- `route_time_mode` добавлен в recommendation/user route контракты; default —
  `flexible`, поэтому `closed_now` больше не является hard filter без явного
  режима `now`.
- Радиус candidate retrieval расширен для городов крупнее Зеленоградска:
  2-часовой маршрут теперь ищет в радиусе 5 км, длинные маршруты — шире.
- Route response получил `status`: `ready`, `partial_route`, `no_route`.
  Frontend больше не показывает пустой результат как «Маршрут готов».
- Quality score учитывает `completeness`; маршрут из одной точки получает
  заметный penalty вместо отличной оценки.
- Route points теперь включают `city_slug`; frontend блокирует отображение
  маршрута, если точки пришли из другого выбранного города.
- В route trace добавлена диагностика candidate retrieval: city id, радиус,
  количество мест города, published places и мест с координатами.
- Route builder UI больше не показывает пользователю поля широты/долготы.
  Пример маршрута очищен от захардкоженного «Променада Зеленоградска».

### Public images and route build audit
- Подтверждено, что локальный `master` совпадает с `origin/master`; проблема
  была не в рассинхронизации GitHub.
- Найдена runtime-причина старого поведения: на `127.0.0.1:8000` висел старый
  uvicorn-процесс, поэтому веб/API отвечали кодом до ночных доработок.
- Каталог, nearby/open-now и route candidates приведены к единому public image
  contract: показываются только approved/active `place_images`, legacy
  `places.image_url` больше не просачивается в route points.
- Route result UI теперь рендерит `point.image_url`, если backend вернул
  публично разрешённое фото.
- Форма маршрута получила выбор времени суток и отправляет `time_of_day` в
  backend; это убирает ночную деградацию, когда дневной маршрут проверялся
  относительно текущего времени сервера.
- Диагностика БД: для Зеленоградска сейчас нет approved/active `place_images`,
  поэтому API корректно возвращает `image_url: null`; фото нужно наполнить через
  image import/review pipeline.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `464 passed, 4 skipped`;
  frontend `npm run test -- --run` -> `21 passed`; `npm run build` -> PASS;
  `npm run lint` -> PASS с существующим warning в `PlaceDetailPage`.

### DB-backed place and route UI contract
- Route points from `/v1/user-routes/build` and `/v1/recommendations/route`
  now include DB presentation fields: `title`, `address`, `image_url`,
  `short_description`, `source`.
- Frontend route builder sends the selected city slug in `city_id`, so candidate
  retrieval is restricted to the chosen published city instead of an ambiguous
  general pool.
- Place cards normalize DB fields for UI: `average_visit_duration_minutes`
  becomes `visit_minutes`, raw import descriptions such as `coffee: Title` are
  replaced by readable category fallback copy.
- Place/open-now/nearby payloads include card-ready fields from DB, so discovery
  cards no longer lose description, image, duration, price and source data.
- Web UI no longer treats unverified `image_url` as an exact place photo; cards
  and route points show a deterministic fallback with honest photo status.
- Route builder now converts `time_of_day` into a planned start bucket before
  hard filters/scoring, so a daytime route is not evaluated against the current
  night-time clock.
- Missing DB hours/duration are handled through runtime `effective_*` defaults
  for route/card display without mutating canonical `places` fields.
- Public visibility now hides working seed placeholders from catalog and route
  candidate retrieval.
- Telegram place intent normalization strips punctuation from city queries.
- Architecture note added: `docs/architecture/place_route_ui_data_contract.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `436 passed, 4 skipped`;
  frontend `npm run lint`, `npm run test -- --run`, `npm run build` -> PASS.

## 2026-06-05

### Web and Telegram UI redesign
- Интерфейс веба перепроектирован как route-first продуктовый сценарий:
  главная теперь ведёт к поиску и сборке прогулки, а конструктор маршрута
  показывает время, интересы, ограничения, стартовую точку и понятное preview.
- Route result UI стал богаче: grade/quality, дистанция, time breakdown,
  warnings, timeline точек и correction actions `shorten_route`, `extend_route`,
  `rebuild_from_here`.
- Карточки мест обновлены: фото-статус, часы, длительность, цена, CTA и fallback
  для недоступных изображений без выдачи category/area фото за точное фото места.
- Header очищен от wording `Пилот`: Зеленоградск теперь отображается как выбранный
  город, что согласуется с multi-city архитектурой.
- Telegram UI упрощён: выбор города остаётся первым шагом, главное меню содержит
  5 действий без дублей, route message показывает качество, время, дистанцию,
  warnings и понятные correction-кнопки.
- Архитектура описана в `docs/architecture/web_bot_ui_redesign.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `433 passed, 4 skipped`;
  frontend `npm run lint`, `npm run test -- --run`, `npm run build` -> PASS.

### Managed OSM cron import for target cities
- Добавлен управляемый config `data/config/import_targets.json` для текущих
  городов импорта: `zelenogradsk`, `kutaisi`, `yerevan`, `khanty-mansiysk`.
- `data/scripts/run_due_import_jobs.py` заменён на cron entrypoint:
  принимает `--city`, `--scope`, `--dry-run/--apply`, читает config, уважает
  `next_run_at`, ставит scope lock и запускает scoped OSM import.
- `data/scripts/import_target_cities.py` оставлен как backward-compatible wrapper
  над новым runner, без отдельного hardcoded списка городов.
- OSM apply-import теперь корректно отличает `matched_existing_place` от
  `new_source_object`, считает `published_count=created+updated` и помечает
  ранее видимые, но не найденные в новом batch source objects как
  `missing_once` / `missing_repeatedly` / `possible_removed` без удаления places.
- Документация обновлена командами для dry-run, apply и cron.

### City expansion registry and Telegram city selection
- Добавлены таблицы/модели: `countries`, `regions`, `city_candidates`,
  `city_import_scopes`, `city_import_jobs`, `import_batches`,
  `city_scope_import_state`, `source_observations`, `place_discovery_requests`,
  `place_source_presence`, `place_scope_links`.
- `cities` расширены backward-compatible полями `country_id`, `region_id`,
  `city_candidate_id`, `bbox`, `launch_status`; `zelenogradsk` остаётся published.
- Новые стартовые города Кутаиси, Ереван и Ханты-Мансийск добавлены migration seed
  как draft candidates/cities со стартовыми scopes, но не публикуются автоматически.
- Добавлены API: `GET /cities/available`, registry endpoints
  `/city-expansion/*`, scope-aware coverage `/city-expansion/coverage/{city_slug}`,
  `POST /place-discovery/`.
- Candidate retrieval теперь не использует draft/unpublished cities и не берёт places
  из unpublished scopes; legacy places без scope links сохраняют совместимость.
- Добавлены cron-ready/data scripts:
  `data/scripts/import_city_osm.py`, `city_coverage_report.py`,
  `run_due_import_jobs.py`.
- Telegram `/start` теперь сначала просит выбрать город; выбор хранится в
  `telegram_user_contexts.selected_city_slug`; callback data короткие
  (`city:zel`, `city:kut`, `city:yvn`, `city:khm`).
- Telegram handlers маршрутов/мест используют selected city и больше не молча
  fallback-ятся на Зеленоградск.
- Документация: `docs/city_expansion_guide.md`,
  `docs/architecture/city_expansion_architecture.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `427 passed, 4 skipped`;
  `.venv/bin/python scripts/backend_quality_gate.py` -> PASS.

### Route pipeline observability and safety
- Добавлен route pipeline trace: stage counts, durations, hard-filter reasons,
  top scoring values и structured JSON log `city_go.route_pipeline`.
- `POST /v1/recommendations/route` и legacy alias отдают `_trace` только при
  `X-Debug: true`; обычные пользовательские ответы не засоряются debug-данными.
- `HardFiltersService` получил `apply_with_report()`: fallback теперь может
  ослабить только budget, но не возвращает closed/temporarily_closed,
  `is_active=false`, места без координат, явно исключённые места/категории,
  закрытые сейчас места и unknown-hours места для time-sensitive запроса.
- В route request/context добавлено опциональное поле `time_of_day`; при его
  наличии маршрут считается time-sensitive для hard filters.
- Добавлен semantic interests mapping: `архитектура/история`, `природа/море`,
  `еда/кофе`, `вечер`, `семья/дети` теперь поднимают релевантные категории в
  scoring вместо буквального сравнения interest == category.
- Архитектура описана в `docs/architecture/route_pipeline_observability.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `400 passed, 4 skipped`;
  `scripts/backend_quality_gate.py` -> PASS; frontend `npm run test -- --run`,
  `npm run build`, `npm run lint` -> PASS.

### Route assembly quality
- `RouteAssemblyService` переписан как тонкий адаптер над чистым
  `route_assembly_optimizer.py`.
- Assembly теперь учитывает walk time + visit duration до добавления точки в
  маршрут, а не ждёт грубой обрезки после time-aware.
- Добавлены category constraints: кофейни/еда/вечерние места не могут забить весь
  маршрут одной категорией.
- Добавлен локальный loop cleanup для очевидных backtrack-петель.
- В response добавлены `total_walk_distance_meters`, `time_breakdown` и
  `category_distribution`.
- Архитектура описана в `docs/architecture/route_assembly_quality.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `403 passed, 4 skipped`;
  `scripts/backend_quality_gate.py` -> PASS; frontend `npm run test -- --run`,
  `npm run build`, `npm run lint` -> PASS.

### Contextual scoring and explanations
- Scoring получил новые компоненты: `base_quality`, `time_context`,
  `data_confidence`, `popularity_proxy`; `distance` оставлен в breakdown, но больше
  не участвует в итоговом score, чтобы не создавать proximity bias.
- `RoutePoint` теперь несёт `scoring_breakdown`, а API/user-route responses
  сериализуют его по точкам.
- Explanation строит `reason`, `match_type`, `score_components` и `data_notes`
  из реальных scoring/time сигналов, сохраняя старые поля для совместимости.
- Архитектура описана в `docs/architecture/route_scoring_explanation.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `406 passed, 4 skipped`;
  `scripts/backend_quality_gate.py` -> PASS; frontend `npm run test -- --run`,
  `npm run build`, `npm run lint` -> PASS.

### Route correction engine
- `remove_place` теперь делает remove + попытку заменить точкой той же категории,
  а не просто деградирует маршрут.
- `shorten_route` удаляет худшую точку по `score / minutes`, не последнюю по порядку.
- Добавлен action `extend_route`: backend/Telegram/frontend type contract поддерживают
  запрос на добавление ещё одной точки.
- Correction logic вынесена в `user_route_correction_actions.py`,
  `user_route_correction_policy.py`, `user_route_replacement_loader.py`.
- Архитектура описана в `docs/architecture/route_correction_engine.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `409 passed, 4 skipped`;
  `scripts/backend_quality_gate.py` -> PASS; frontend `npm run test -- --run`,
  `npm run build`, `npm run lint` -> PASS.

### Route result UX and production data refresh
- Backend responses `POST /v1/recommendations/route` и
  `POST /v1/user-routes/build` теперь отдают `user_warnings`: тип, severity,
  пользовательский текст, affected place ids и action hint.
- Frontend route result показывает пользовательские warnings, time breakdown,
  walk distance, budget utilization, category distribution и `data_notes` из
  explanation вместо технических строк.
- Correction UI получил рабочую кнопку `Добавить место`, вызывающую `extend_route`;
  demo-mode также поддерживает добавление точки и пересчёт метрик маршрута.
- Demo route contract синхронизирован с backend-полями:
  `time_breakdown`, `category_distribution`, `total_walk_distance_meters`,
  `quality_breakdown`, `user_warnings`.
- Добавлены production scripts:
  `scripts/production_place_import.py` для dry-run/real seed import и
  `scripts/refresh_place_images.py` для no-live/live image refresh.
- Добавлена документация `docs/production_data_refresh.md`.
- Проверки: `.venv/bin/python -m pytest -q --no-cov` -> `410 passed, 4 skipped`;
  `.venv/bin/python scripts/backend_quality_gate.py` -> PASS;
  frontend `npm run test -- --run` -> `9 files / 18 tests`, `npm run build`,
  `npm run lint` -> PASS.
- Playwright CLI gate 2026-06-05 пройден на `/routes/generate`:
  route build сработал, новые метрики показали ненулевые значения, `Добавить место`
  увеличил маршрут с 3 до 4 точек и пересчитал время/дистанцию/категории.

## 2026-06-04

### Product UI refresh
- Добавлен honest image contract для frontend catalog: `image.url`,
  `image.source`, `image.source_url`, `image.match_status`,
  `image.match_confidence`, `image.attribution`, `image.last_fetched_at`.
- `frontend/public/data/zelenogradsk_places.json` обновлён до `schema_version: 1.3`.
  Текущий split изображений: 15 `exact_place_photo`, 22 `area_photo`,
  71 `category_photo`; кафе/еда без подтверждения больше не маркируются как фото места.
- Добавлены MVP scripts `data/scripts/enrich_catalog_images.py` и
  `data/scripts/validate_catalog_images.py`, плюс общие правила
  `image_enrichment_rules.py`.
- Добавлен полный image pipeline package `data/scripts/image_pipeline/*`:
  Wikidata QID/P18, Commons depicts, official `og:image`, Mapillary area-photo
  URL builder, image selector, enrichment artifacts и verification queue.
- Сгенерированы `data/enrichment/zelenogradsk_image_enrichment.json` и
  `data/enrichment/zelenogradsk_image_verification_queue.json`; текущая очередь
  содержит 93 места, где фото не является high-confidence exact.
- Place cards и detail page теперь показывают статус фото: `Фото места`,
  `Фото района рядом`, `Иллюстрация категории` или `Фото недоступно`.
- Frontend теперь работает без live backend в demo-mode по умолчанию: локальная база
  мест, place detail, open-now, nearby и route builder доступны сразу после Vite start.
- Реальный backend подключается явно через `VITE_USE_BACKEND=true`.
- Demo catalog расширен до `frontend/public/data/zelenogradsk_places.json`: 108 мест
  из сохранённых OSM + editorial seed; live Overpass refresh 2026-06-04 вернул 406,
  поэтому текущий большой JSON построен из локального snapshot.
- Header теперь multi-city-friendly: `City Go` остаётся брендом, а Зеленоградск
  показан как пилотный выбранный город.
- Home carousel больше не показывает raw category keys (`walk`, `culture`): карточки
  используют русские labels, двухстрочное ограничение заголовков и более плотный
  градиент, чтобы текст не наезжал на фото.
- Demo route builder получил aliases для широких интересов (`sea`, `walk`, `quiet`,
  `culture`) и fallback к ближайшим разрешённым местам, если точных совпадений
  меньше двух. Это защищает маршрут от пустого результата на большом OSM-каталоге.
- Route result переведён: `Generated route`, `quality`, `warnings`, `demo` заменены
  на русские пользовательские подписи.
- `frontend/public/data/zelenogradsk_places.json` обогащён фото-полями:
  108 мест, 18 разных Wikimedia Commons изображений, 15 exact/near-exact
  matches для объектов по slug/title. Для кафе без открытого точного фото
  используется фото района или категории, не помеченное как exact.
- Place cards теперь показывают не только название: русская категория, адрес,
  часы, длительность визита и price label. Raw описания вида `coffee: ...`
  очищаются перед выводом.
- Place detail расширен до полноценной карточки: часы, длительность, цена,
  координаты, источник/уверенность данных, статус фото и рабочий CTA
  `Собрать маршрут`.
- `/open-now` и `/nearby` переделаны из текстовых SurfaceCard-заглушек в
  полноценные discovery-экраны с богатыми карточками, фото, фактами и CTA.
- Home carousel получила явную навигацию: текст `листай вправо` и кнопки
  `Назад` / `Вперёд` со scroll behavior.
- Добавлены photo-first паттерны: реальные demo-обложки мест из Wikimedia Commons,
  панорамная карусель локаций на главной, крупное фото в place detail и фото точек
  маршрута.
- Главная дополнена быстрыми сценариями: кофе, море, открыто сейчас, рядом, маршрут.
- Route builder приведён к общему app-shell и заменил абстрактную схему на
  понятное фото-превью маршрута.
- Главная и каталог мест переведены на новый City Go app-shell: sticky navigation,
  прикладной hero с поиском, CTA маршрута, responsive stats и аккуратные cards.
- Стили разнесены на маленькие файлы `responsive.css`, `home.css`, `places.css`,
  `cards.css`; убран старый Vite-style остаток из `App.css`.
- Frontend проверки: `npm run test` -> 8 files / 16 tests, `npm run build` -> PASS,
  `npm run lint` -> PASS.
- Playwright CLI gate 2026-06-04 пройден через официальный
  `npx @playwright/cli@latest`: home CTA кликнут, `/routes/generate` собрал
  demo route на 3 точки, `/open-now`, `/nearby` и place detail проверены на
  наличие карточек, фото, фактов и route CTA.
- Playwright smoke пройден на `/` desktop/mobile, `/open-now`, `/nearby`, place
  detail и `/routes/generate` с успешной генерацией demo route и загрузкой фото.

### Zelenogradsk place coverage quick win
- Добавлен `data/scripts/collect_osm_zelenogradsk.py`: автосбор OSM через Overpass,
  запись raw snapshot и генерация import payload без внешних Python-зависимостей.
- `data/scripts/fetch_osm_zelenogradsk.py` сохранён как wrapper на новый collector.
- `PlaceSeedItem` расширен полями `opening_hours`, `average_visit_duration_minutes`,
  `price_level`, `last_verified_at`; import payload теперь пишет эти поля в `Place`.
- Добавлен `data/scripts/osm_seed_builder.py`: raw OSM -> актуальный
  `/place-seed/import/` payload с canonical taxonomy, category duration defaults и
  opening-hours fallback.
- Сгенерирован `data/seeds/place_import/zelenogradsk_osm.json`: 107 валидных OSM
  places после dedup.
- Добавлен `data/seeds/place_import/zelenogradsk_editorial_walks.json`: отдельный
  editorial walk seed для променада Зеленоградска, источник KP.
- Coverage gate categories синхронизированы с backend taxonomy:
  `coffee`, `food`, `walk`, `museum`, `bar`, `park`.
- Seed-level проверка OSM + editorial payload: 108/108 валидных items, gate shape PASS.
- Полный backend pytest после обновления: `388 passed, 4 skipped`, coverage `80.84%`.

## 2026-06-03

### Backend quality gate
- Добавлен `scripts/backend_quality_gate.py`: custom backend linter для лимита
  100 строк на файл, 2..10 файлов в модуле, complexity <= 5 и coverage floor 100%.
- Добавлен `scripts/backend_quality_baseline.txt`: явный baseline текущего legacy-долга;
  новые backend-файлы и модули проверяются строго.
- `scripts/release_checks.sh` теперь запускает backend quality gate перед тестами,
  миграциями, smoke и data coverage gate.
- Добавлены unit-тесты `tests/test_backend_quality_gate.py` и release-artifact проверка.
- Добавлен `docs/architecture/backend_quality_gate.md`, обновлены status/release docs.
- `requirements-dev.txt` дополнен `pytest-cov==7.1.0`, потому что `pytest.ini`
  уже использует `--cov` и `--cov-fail-under`.
- `models/place.py` теперь выставляет initial `created_at` и `updated_at` одним
  timestamp через SQLAlchemy `before_insert`.
- Полный backend pytest после обновления: `379 passed, 4 skipped`, coverage `80.55%`.

## 2026-05-28

### MVP release packaging
- Добавлены `scripts/backup_db.sh`, `scripts/restore_db.sh`, `scripts/release_smoke.sh`,
  `scripts/release_checks.sh`.
- Добавлены `docs/backup_restore.md`, `docs/release_checklist.md`,
  `docs/mvp_release_candidate.md`.
- `migrations/env.py` синхронизирован с новыми моделями analytics/import/verification/signals.

### Place coverage / import pipeline
- Добавлен `POST /place-seed/import/`: dry-run и real import seed-мест.
- Добавлены нормализация seed-полей, дедупликация slug, validation и upsert `Place` по slug.
- Добавлена таблица `place_import_events` и `GET /place-import-logs/summary`
  для persistent audit каждого dry-run/real импорта.
- Добавлен `GET /place-coverage/{city_slug}`: total places, coordinates, opening hours,
  visit duration, category counts, missing required categories, route-ready score.
- Добавлены data-quality поля `Place`: `source`, `source_url`, `confidence`, `last_verified_at`.
- Coverage report теперь показывает `with_source` и `average_confidence`.
- Добавлен release coverage gate: `scripts/check_place_coverage_gate.py` проверяет
  `/place-coverage/{city_slug}` по MVP-порогам и подключён к `scripts/release_checks.sh`.
- Обновлены `docs/implementation_status_and_next_steps.md`, `docs/project_status.md`,
  `docs/technical_spec.md`, `docs/architecture/backend_file_map.md`.

### Route quality warnings
- Добавлен `services/route_quality_warnings.py`.
- Recommendation pipeline теперь поднимает route-level warnings для слишком короткого
  или слишком однотипного маршрута.
- Добавлен category budget в candidate retrieval: кандидаты чередуются по категориям
  до assembly, чтобы diversity улучшался до route warnings.
- Добавлен `services/route_time_ordering_service.py`: nearby-точки, закрывающиеся
  в течение 90 минут, поднимаются раньше до time-aware pass.
- Time-aware слой разделён на маленькие модули `time_aware_math.py` и
  `time_aware_hours.py`; small wait-gap до 20 минут сдвигает arrival к открытию
  и отдаёт `time_status="wait_before_opening"`.
- `RouteBudgetFitService` теперь сохраняет order-preserving subset: если середина
  маршрута не помещается, но следующая короткая точка помещается, она остаётся
  вместо грубой обрезки всего хвоста.

### Route quality score
- Добавлен `services/route_quality_score.py`: числовая оценка маршрута 0..1.
- `FinalRoute`, `/recommendations/route`, `/v1/user-routes/build` и explanation
  теперь отдают `quality_score` и `quality_breakdown`.
- Score учитывает diversity, fit в time budget, полноту данных точек и warning health.
- Обновлены MVP-веса score и добавлен cap 0.6, если у >40% точек нет часов/цен.

### Canonical recommendations endpoint
- `POST /v1/recommendations/route` зафиксирован как canonical route endpoint.
- `POST /recommendations/route` оставлен как legacy alias и отдаёт deprecation
  headers: `Deprecation`, `Sunset`, `Link` на canonical endpoint.

### Route analytics
- Добавлена таблица `route_build_events` для persistent route observability.
- `POST /v1/recommendations/route`, `/v1/user-routes/build` и corrections пишут
  source, latency, quality score, warnings и city.
- Добавлен `GET /route-analytics/summary`: total routes, average quality,
  warning rate, average latency, breakdown по source.

### Place staleness policy
- В `places` добавлен `status`: `active`, `needs_verification`,
  `temporarily_closed`, `closed`.
- Добавлен `services/place_staleness_policy.py`: effective status и правило stale
  после 30 дней для dynamic-мест и 90 дней для static-мест.
- `closed` / `temporarily_closed` исключаются из retrieval, stale-кандидаты дают
  route-level warning и scoring penalty.
- Coverage report считает active / needs verification / temporarily closed / closed places.
- Добавлена очередь re-verification: `place_verification_tasks`,
  `POST /place-verification/enqueue-stale/{city_slug}`, `GET /place-verification/queue`.
- Добавлен опциональный scheduler enqueue stale-мест: включается через
  `VERIFICATION_SCHEDULER_ENABLED=true`, использует interval hours и список city slugs
  из `core.config`, ошибки по одному городу не останавливают batch.

### User signals
- Добавлены `models/user_signal.py`, `POST /user-signals/`,
  `GET /user-signals/{user_id}/summary`.
- Добавлен `GET /user-signals/{user_id}/profile`: derived profile по категориям,
  action counts и last activity.
- Derived profile расширен favorite/like/dislike/visited/completed route сигналами.
- `user_id` в route build/recommendation request подключает derived profile к scoring:
  category affinity, liked place boost и visited penalty.
- `route_build_events.user_id` и `GET /route-analytics/users/{user_id}/history`
  дают минимальную route history основу для feedback loop.

### Telegram observability
- Добавлен structured JSON event logger для Telegram actions.
- Свободный текст логирует received text, распознанные intents и fallback.
- Route flow логирует start/success/failure, place/nearby/route flows получают
  fallback для неподдерживаемого города.

### Backend request logging
- Добавлен JSON request logging middleware: method, path, status code, duration.
- Router wiring вынесен в `core/router_setup.py`, чтобы `main.py` оставался
  компактной точкой сборки приложения.

### CI/CD gates
- Добавлен `.github/workflows/ci.yml`: backend pytest, shell syntax check release scripts,
  frontend tests and build.
- Добавлен `requirements-dev.txt` с pinned pytest for CI.

### Frontend route builder UX
- Generate Route page теперь вызывает `POST /v1/user-routes/build`, передаёт `user_id`
  и показывает quality/time-warning badges.
- Добавлена correction UX поверх `POST /v1/user-routes/correct`: shorten, remove first,
  rebuild from here.

## 2026-05-27

### Backend Phase 1 и Telegram Phase 1
- Backend recommendation pipeline помечен как Phase 1 done:
  `POST /recommendations/route`, `/v1/user-routes/build`, `/v1/user-routes/correct`,
  route-level `warnings`, `explanation.warnings`, `explanation.data_limitations`.
- Telegram bot Phase 1 помечен как done: маршруты, коррекции, контекст,
  nearby/open-now/category сценарии, city-aware свободный текст.
- Полный backend/test прогон после актуализации: `287 passed, 4 skipped`.

### Документация
- Добавлен [`docs/implementation_status_and_next_steps.md`](implementation_status_and_next_steps.md):
  сводка реализованного и backlog по data coverage, маршрутам, UI,
  персонализации и production readiness.
- Обновлены `docs/README.md`, `docs/master_technical_spec.md`,
  `docs/technical_spec.md`, `docs/project_status.md`,
  `docs/route_generation_status_and_roadmap.md`.
- В `docs/itinerary/05_status_tracking.md` добавлено уточнение, что это статус
  legacy itinerary/replan слоя, а production-контур описан отдельно.

## 2026-04-12

### Юнит-тесты recommendation pipeline
- Добавлены `tests/test_context_merge_service.py`, `tests/test_hard_filters_service.py`, `tests/test_route_assembly_service.py` (изолированные проверки merge, hard filters, assembly; для фильтров при необходимости снижается `MIN_POOL_SIZE`, чтобы не срабатывал fallback ослабления пула).
- Исправлен синтаксис f-строки в `services/itinerary_replan_service.py` (ветка `shorten_route` без бюджета времени).
- В `services/itinerary_scoring_service.py` восстановлена вспомогательная `build_place_text_blob` для согласования с тестом; прочие импорты в `test_itinerary_scoring_new.py` / `test_itinerary_replan_new.py` по-прежнему могут не совпадать со схемами — требуется отдельная синхронизация тестов itinerary.
- Обновлены `docs/architecture/application_architecture_ru.md` (§10), `docs/commenting_policy.md` (§8).

### Itinerary — покрытие UC кодом
- Добавлен [`docs/itinerary/08_implementation_coverage.md`](itinerary/08_implementation_coverage.md): таблица UC ↔ itinerary / recommendation ↔ модули ↔ автотесты; ссылка из [`01_use_cases.md`](itinerary/01_use_cases.md) и [`README.md`](README.md).

### Документация и навигация
- Добавлен [`docs/README.md`](README.md): карта каталога `docs/`, канонические ссылки, кратко три HTTP-контура маршрута (editorial / itinerary / recommendations).
- Обновлён [`docs/master_technical_spec.md`](master_technical_spec.md): §5.10 Recommendations route API; перенумерованы §5.11–5.14; актуализированы §2.3, §8, §10.5, §11 под `POST /recommendations/route` и explainability в ответе.
- Обновлены [`docs/technical_spec.md`](technical_spec.md), [`docs/project_status.md`](project_status.md): endpoint `POST /recommendations/route`, отсылки к master/README.
- [`docs/route_generation_status_and_roadmap.md`](route_generation_status_and_roadmap.md): §3.4 — recommendation pipeline vs itinerary vs `GET /routes`.
- [`docs/architecture/application_architecture_ru.md`](architecture/application_architecture_ru.md): уточнены `recommendation_route.py` и статус `api/routes/recommendation.py`.
- [`docs/architecture/project_structure.md`](architecture/project_structure.md): пометка **устарело** + ссылки на актуальные документы.

## 2026-03-24

### 1) Актуализация master ТЗ
- Обновлен `docs/master_technical_spec.md`.
- Добавлены стратегические направления:
  - social/community layer (как future direction),
  - gamification module (как future direction),
  - personalized travel planning + next destination.
- Добавлены разделы по:
  - data freshness / source confidence / verification lifecycle,
  - AI как recommendation system (а не только retrieval),
  - gap analysis,
  - phased implementation plan (Phase 1 / Phase 2 / Phase 3).

### 2) Frontend Phase 1: безопасная структуризация
- Вынесены типы и API-слой:
  - `frontend/src/entities/place/model/types.ts`
  - `frontend/src/shared/config/env.ts`
  - `frontend/src/shared/api/http.ts`
  - `frontend/src/shared/api/endpoints.ts`
  - `frontend/src/api/places/places.api.ts`
- Вынесена feature-логика поиска:
  - `frontend/src/features/place-search/model/filterPlaces.ts`
- Вынесены UI-компоненты:
  - `frontend/src/components/places/PlaceCard.tsx`
  - `frontend/src/widgets/home/HomeHero.tsx`
  - `frontend/src/widgets/home/HomeStats.tsx`
  - `frontend/src/widgets/home/PlacesSection.tsx`
  - `frontend/src/pages/home/HomePage.tsx`

### 3) Тесты и стабильность
- Добавлены тесты:
  - `frontend/src/shared/api/endpoints.test.ts`
  - `frontend/src/features/place-search/model/filterPlaces.test.ts`
  - `frontend/src/api/places/places.api.test.ts`
  - `frontend/src/pages/home/HomePage.test.tsx`
- Добавлены тестовые зависимости:
  - `vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`.

### 4) Роутинг и новые экраны
- Добавлен базовый роутинг (`react-router-dom`):
  - `/` -> `HomePage`
  - `/places` -> `PlacesListPage`
  - `/places/:slug` -> `PlaceDetailPage`
- Добавлены страницы:
  - `frontend/src/pages/places/PlacesListPage.tsx`
  - `frontend/src/pages/places/PlaceDetailPage.tsx`
- Добавлены переходы:
  - с Home на `/places` (CTA + ссылка в секции мест),
  - из карточек мест на detail `/places/:slug`.

### 5) Responsive-адаптация
- Добавлены адаптивные стили:
  - `frontend/src/styles/responsive.css`
- Обновлены layout-точки:
  - `frontend/src/index.css`
  - адаптация Home/Places/List/Detail под мобильные и планшетные экраны.

### 6) Проверка комментариев (аудит)
- Выполнена быстрая проверка покрытия комментариями/докстрингами по проекту.
- Backend (`*.py`) в значительной части уже содержит комментарии.
- Frontend (`*.ts`, `*.tsx`, `*.css`) имеет мало комментариев, что типично для self-explanatory UI-кода.
- Критичных мест, где отсутствие комментариев ломает понимание логики, в новых изменениях не выявлено.

### 7) Принцип внесения изменений
- Изменения выполнялись маленькими безопасными шагами с обязательной проверкой:
  - `npm run test`
  - `npm run lint`
  - `npm run build`

### 8) Recommendation pipeline: выравнивание под реальный ORM Place (2026)
- `services/candidate_retrieval_service.py`: убраны несуществующие в `Place` поля (`active`, `city_id`, `popularity_score`); сортировка по расстоянию; интересы не режут SQL-пул (scoring).
- `services/hard_filters_service.py`: убраны `place.active` / `needs_review`; PASS1 open-now через `itinerary_time_service.is_place_open_at` (формат `opening_hours` как в itinerary).
- `services/scoring_service.py`: убраны `place.tags` и `place.popularity_score`; нейтральный popularity.
- `services/route_assembly_service.py`: дефолт dwell при `average_visit_duration_minutes is None`; `place_id` как строка; устойчивость к `category is None`.
- Модели БД и миграции не трогались; `itinerary_*` не изменялись.
