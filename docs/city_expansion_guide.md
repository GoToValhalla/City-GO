# City Go — инструкция по добавлению стран, регионов, городов и зон импорта

## 1. Общая архитектура

Country хранит страну. Region хранит область, край, республику, столицу или другой регион внутри страны. City Candidate — город-кандидат, который найден или подготовлен, но ещё не является полноценным городом продукта. City — рабочий город в приложении. Пользователю доступен только город с `launch_status=published` и `is_active=true`.

Import Scope — зона частичного импорта города: центр, tourist core, food area, parks и так далее. Import Job — cron-ready задание. Import Batch — audit конкретного запуска. Source Observation — каждый raw object, который вернул источник. Place Source Presence — состояние видимости объекта в источнике. Published Place — только публично видимое место в `places`, а не raw-наблюдение.

## 2. Как добавить новую страну

Создать запись в `countries`: `code`, `name`, `default_locale`. Через API: `POST /city-expansion/countries`.

## 3. Как добавить новый регион

Создать запись в `regions`: `country_id`, `code`, `name`, `type`, `timezone`, опционально `center_lat`, `center_lng`, `bbox`. Через API: `POST /city-expansion/regions`.

## 4. Как добавить city candidate

Создать `city_candidates` со статусом `candidate` или `needs_review`. Не публиковать автоматически.

## 5. Как approve city candidate

После проверки источников и bbox перевести candidate в `approved`, затем создать `cities` запись с `launch_status=draft` или `data_importing`.

## 6. Как создать city

Создать `cities`: `slug`, `name`, `country_id`, `region_id`, `timezone`, `center_lat`, `center_lng`, `bbox`, `launch_status`. Новый город не должен быть `published` до coverage gate.

## 7. Как создать import scopes

Создать `city_import_scopes` для конкретного `city_id`. Scope может быть `enabled`, но не `published`. Route builder использует только published city и публично видимые places.

## 8. Как выбрать bbox/polygon для scope

Использовать OSM/Nominatim/boundary и ручную проверку. Для больших городов сначала создавать центральные/tourist scopes, а не весь город.

## 9. Как выбрать import_profile

`tourist_core` — достопримечательности, музеи, галереи, смотровые точки, парки, пляжи, природные зоны, кафе и рестораны.

`food_and_coffee` — кафе, рестораны, fast food, бары, пекарни, кондитерские, кофе, чай, мороженое.

`nature_walk` — парки, сады, nature reserve, playground, пляжи, вода, лес, природные точки, смотровые точки.

`useful_services` — туалеты, аптеки, ATM, парковки, shelter, банки, клиники, больницы, полиция.

Транспортные остановки, bus stop, platform, stop_position, tram_stop, railway halt/station сейчас не импортируются в публичный каталог. Если они уже есть в базе, они скрываются visibility-фильтром и quality cleanup.

## 10. Как запустить dry-run import

```bash
cd /Users/user/app
.venv/bin/python data/scripts/import_city_osm.py --city kutaisi --scope tourist_core --profile tourist_core --dry-run
```

Dry-run делает live-запрос в Overpass, нормализует raw objects и возвращает счётчики `raw_count`, `normalized_count`, `rejected_count`, распределение категорий и причины отбраковки. Production places не меняются.

## 11. Как читать dry-run diff

Смотреть:

- `mode`
- `city`
- `scope`
- `profile`
- `production_changes=false`
- `accepted_categories`
- `rejection_reasons`

Если `raw_count` неожиданно большой, сузить bbox или профиль до apply.

## 12. Как запустить apply import

```bash
cd /Users/user/app
.venv/bin/python data/scripts/import_city_osm.py --city kutaisi --scope tourist_core --profile tourist_core --apply
```

Apply создаёт `import_batches`, `source_observations`, `place_scope_links`, `place_source_presence`, затем создаёт или обновляет `places`.

Import теперь не только добавляет новые места, но и обновляет существующие места по тому же `source_url` / OSM object:

- нормальное новое название перезаписывает старое;
- адрес обновляется;
- часы работы обновляются;
- координаты обновляются, если смещение безопасное;
- категория обновляется, если смена не выглядит опасной;
- `last_verified_at` обновляется при успешной обработке;
- мусорные названия скрываются;
- закрытые/удалённые объекты скрываются;
- сильный перенос координат отправляет место в `needs_review`;
- резкая смена категории отправляет место в `needs_review`.

## 13. Как запустить quality cleanup без импорта

Dry-run по одному городу:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/cleanup_imported_places_quality.py --city kutaisi --dry-run
```

Apply по одному городу:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/cleanup_imported_places_quality.py --city kutaisi --apply
```

Quality cleanup не удаляет места из БД. Он скрывает плохие места из публичного каталога через `status` и `is_active=false`.

Скрываются:

- `category=transport`;
- названия вида `1`, `2`, `1,`, `№1`, `yes`, `unknown`;
- места, которые уже имеют непубличный lifecycle/status;
- места, которые пропали из источника 3 раза подряд.

## 14. Как запустить cron import по указанным городам

Управляемый список городов/scopes лежит в:

```text
data/config/import_targets.json
```

Ручной dry-run по всем configured due scopes:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/run_due_import_jobs.py --dry-run
```

Ручной apply только по tourist core двух городов:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/run_due_import_jobs.py --city kutaisi,yerevan --scope tourist_core --force --apply
```

Cron-команда для регулярного поиска, обновления и очистки мест:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/run_due_import_jobs.py --apply
```

Runner читает config, выбирает due scopes, ставит lock, запускает OSM import и после успешного импорта запускает `cleanup_imported_places_quality.py` по этому же городу.

Если нужно временно запустить импорт без quality cleanup:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/run_due_import_jobs.py --apply --skip-quality-cleanup
```

Для ручного запуска вне расписания использовать `--force`.

## 15. Как проверить import_batches

Смотреть `import_batches`:

- `raw_count`
- `normalized_count`
- `published_count`
- `needs_review_count`
- `rejected_count`
- `duplicate_count`
- `status`
- `diff_summary`

В `diff_summary` должны быть:

- `created`
- `updated`
- `unchanged`
- `needs_review`
- `rejected`
- `hidden`
- `deactivated_bad_places`
- `missing_from_source`
- `hidden_missing_places`

## 16. Как проверить source_observations

Каждый raw object должен иметь:

- `source_type`
- `source_external_id`
- `payload_hash`
- `match_status`
- `normalization_status`
- `raw_name`
- `raw_category`
- `raw_lat`
- `raw_lng`
- `raw_payload`

При отбраковке должен быть `rejection_reason`.

## 17. Как понять, почему место не попало в places

Проверить `source_observations.rejection_reason`.

Основные причины:

- `missing_name`
- `bad_name`
- `missing_coordinates`
- `unsupported_category`
- `source_closed`
- `source_temporarily_closed`
- `source_removed_from_source`

## 18. Как работает обновление существующего места

Существующее место ищется по:

1. `Place.source_url`
2. `Place.slug`

Если найдено место с тем же источником, importer не создаёт дубль, а обновляет существующую запись.

Безопасно обновляются:

- `title`
- `short_description`
- `address`
- `lat`
- `lng`
- `category`
- `opening_hours`
- `source`
- `source_url`
- `confidence`
- `last_verified_at`

Небезопасные изменения не публикуются автоматически:

- координаты резко сместились;
- категория резко изменилась;
- объект выглядит закрытым или удалённым;
- название стало мусорным.

## 19. Как работает missing source object

Если объект раньше был связан с местом, но в текущем импорте не пришёл из источника:

- 1 раз — `presence_status=missing_once`;
- 2 раза — `presence_status=missing_repeatedly`;
- 3+ раза — `presence_status=possible_removed`, место скрывается как `removed_from_source`.

Важно: объект считается missing только если он реально не пришёл из OSM. Если объект пришёл, но был отклонён нормализацией, он не считается missing.

## 20. Как обработать missing place от пользователя

Создать `place_discovery_requests` через `POST /place-discovery/`. Запрос не публикует place автоматически.

## 21. Как проверить coverage report

```bash
cd /Users/user/app
.venv/bin/python data/scripts/city_coverage_report.py --city yerevan
.venv/bin/python data/scripts/city_coverage_report.py --city yerevan --scope center
```

Также доступно API:

```text
GET /city-expansion/coverage/{city_slug}?scope_code=center
```

## 22. Как publish scope

Перевести scope в `reviewed`, затем `published` только после проверки coverage, дубликатов, мусорных мест и review queue.

## 23. Как publish city

Перевести `cities.launch_status` в `published` и оставить `is_active=true` только после city/scope coverage gate.

## 24. Как проверить, что город появился на сайте и в Telegram

`GET /cities/available` должен вернуть город.

Город должен иметь:

- `is_active=true`;
- `launch_status=published`;
- хотя бы одно публично видимое место.

Draft города можно получить только с `include_draft=true`, и они показываются как “готовится”.

## 25. Как сменить город в Telegram

Пользователь нажимает `⚙️ Сменить город`, затем выбирает город. Callback data короткие:

- `city:zel`
- `city:kut`
- `city:yvn`
- `city:khm`

## 26. Как не сломать существующий город

Не менять slug Зеленоградска.

Не удалять legacy places без отдельного решения.

Не переводить `zelenogradsk` из `published` без отдельного решения.

Не запускать широкий bbox на большой город без dry-run.

Не запускать `--apply`, если dry-run показывает слишком много мусора или странное распределение категорий.

## 27. Что делать, если импорт плохой

Не публиковать город/scope.

Проверить:

- `import_batches.diff_summary`;
- `source_observations.rejection_reason`;
- `place_source_presence.presence_status`;
- результат `cleanup_imported_places_quality.py --dry-run`.

Если плохие места уже попали в базу, запустить:

```bash
cd /Users/user/app
.venv/bin/python data/scripts/cleanup_imported_places_quality.py --city CITY_SLUG --dry-run
.venv/bin/python data/scripts/cleanup_imported_places_quality.py --city CITY_SLUG --apply
```

## 28. Как откатить/пометить плохой import_batch

Пока rollback механика audit-only: отметить batch/status и не продвигать scope/city. Production places не удаляются автоматически.

Для публичного скрытия использовать:

- `status=draft`;
- `status=needs_review`;
- `status=closed`;
- `status=temporarily_closed`;
- `status=removed_from_source`;
- `is_active=false`.

## 29. Риски и защиты

Ложное “места нет” закрывается `source_observations`, `place_source_presence` и `place_discovery_requests`.

Агрессивное удаление закрывается тем, что места не удаляются из БД, а скрываются через `status` и `is_active`.

Дубли scopes закрываются `place_scope_links`.

Мусор из OSM закрывается import profiles, name filters, lifecycle service, quality cleanup, public visibility filter и coverage gate.

Остановки и транспорт временно скрыты через public visibility filter и cleanup, а не удалены из базы.