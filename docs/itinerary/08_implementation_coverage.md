# City Go — покрытие use cases кодом (itinerary vs recommendation)

Сопоставление продуктовых сценариев из [`01_use_cases.md`](01_use_cases.md) с реализацией в репозитории.  
**Не заменяет** QA-матрицу [`03_test_matrix.md`](03_test_matrix.md): там сценарии ручного прогона; здесь — привязка к модулям и **существующим** автотестам.

---

## HTTP-контуры (кратко)

| Контур | Эндпоинты | Роль в UC |
|--------|-----------|-----------|
| **Itinerary** | `POST /routes/generate`, `POST /routes/replan` | Основной носитель UC из §1–8 документа 01 (текст, старт, replan, контекст). |
| **Recommendation** | `POST /recommendations/route` | Узкий сценарий: координаты, бюджет времени, интересы, фильтры; **без** текста itinerary и **без** replan. |
| **Editorial routes** | `GET /routes/…` | Готовые маршруты из БД; **не** динамическая генерация из UC-001. |

---

## Условные обозначения

| Оценка | Смысл |
|--------|--------|
| **полное** | Основной happy path и ключевые ветки отражены в коде; есть целевые автотесты или однозначная реализация в сервисах. |
| **частичное** | Поведение есть, но не все acceptance из 01_use_cases; или только эвристика без отдельного UC-теста. |
| **минимальное** | Поля/парсинг/заглушка без полной продуктовой семантики. |
| **в плане (V1/V2)** | В 01_use_cases приоритет V1/V2 — ожидаемый пробел. |
| **нет** | В текущем API/сервисах сценарий не выделен. |

Колонки **It** / **Rec** — покрытие контуром **itinerary** / **recommendation** соответственно (`—` = не применимо).

---

## Таблица покрытия UC

| ID | Кратко | It | Rec | Ключевой код (itinerary) | Ключевой код (recommendation) | Автотесты (ориентиры) | Оценка |
|----|--------|----|-----|--------------------------|-------------------------------|------------------------|--------|
| UC-001 | Generate from scratch | да | частично | `routers/itinerary.py` → `generate_itinerary_stub`, `itinerary_service`, `itinerary_route_builder_service` | `route_builder_service`, `routers/recommendations.py` | `test_itinerary_scoring_new`, `test_route_builder_pipeline_smoke`, `test_recommendations_route_router` | полное / частичное |
| UC-002 | Quick walk near me | частично | частично | `start_context`, `route_mode=walk`, candidate radius | `lat`/`lng`, walk не как отдельный enum в Rec | те же + geo в itinerary | частичное |
| UC-003 | Full day | частично | частично | `time_budget`, `max_places`, сборка | `time_budget_minutes`, лимит точек в assembly | pipeline smoke | частичное |
| UC-004 | Interest-driven | да | частично | `itinerary_text_parser`, `itinerary_scoring_service` | `interests`, `avoided_categories` | `test_itinerary_scoring_new`, scoring pipeline | полное / частичное |
| UC-010 | With dog | да | нет | `itinerary_scoring_service`, filters, explanation | — | `test_itinerary_scoring_new` | полное (It) |
| UC-011 | Budget-conscious | да | частично | `budget_level` в merge/scoring | `budget_level` в `RequestContext` / hard_filters / scoring | `test_itinerary_scoring_new`, pipeline | частичное |
| UC-012 | Indoor only | да | нет | `itinerary_candidate_service`, scoring | — | `test_itinerary_scoring_new` | полное (It) |
| UC-013 | Anti-tourist | частично | нет | preferences из текста + scoring | — | `test_itinerary_scoring_new` | частичное |
| UC-014 | With children | частично | нет | scoring, time estimator | — | `test_itinerary_scoring_new` | частичное |
| UC-020 | Evening route | частично | частично | retrieval + time index, scoring OH | `time_aware_service` + кандидаты | `test_opening_hours_*`, `test_candidate_opening_hours_filter_new` | частичное |
| UC-021 | Closing soon order | частично | да | в основном NN-order + pass2 swap | `route_time_ordering_service` перед time-aware | `test_route_time_ordering_service.py` | частичное |
| UC-022 | Midnight crossing | да | частично | `itinerary_time_service` | общая логика OH в pipeline | `test_opening_hours_midnight_crossing.py` | полное (It) |
| UC-023 | Waiting gap | частично | частично | swap закрытых, warnings в explanation | `time_aware_hours` small wait-gap + warnings | `test_time_aware_service.py`, `test_replan_stop_respects_opening_hours_new.py` | частичное |
| UC-024 | Truncation by budget | да | да | `trim_route_to_time_budget` | finalize / ограничение длины маршрута | pipeline smoke, itinerary builder | полное |
| UC-025 | Opens later in route | да | частично | candidate pool + placement | time-aware по визитам | `test_generate_filters_closed_places_new.py`, OH-тесты | полное / частичное |
| UC-026 | Start too late | частично | частично | деградации, explanation | пустой/короткий маршрут без спец UX | мало явных тестов | минимальное |
| UC-030 | Typed address start | да | нет | `start_context_resolver`, `StartContextInput.address` | только lat/lng | нет выделенного unit на resolver | частичное |
| UC-031 | Loop / return to start | частично | нет | `return_to_start` в merge/context | — | `test_itinerary_replan_new` (контекст) | частичное |
| UC-032 | Area-constrained | минимальное | нет | `area` в `StartContextInput` | — | нет | минимальное |
| UC-033 | Route A → B | нет | нет | — | — | — | в плане (V2) |
| UC-034 | Must end near departure | нет | нет | — | — | — | в плане (V1) |
| UC-040 | Coffee stop replan | да | нет | `itinerary_replan_service` | — | `test_itinerary_replan_new.py` | полное (It) |
| UC-041 | Shorten route | да | нет | replan `shorten_route` | — | `test_itinerary_replan_new.py` | полное (It) |
| UC-042 | Continue from here | да | нет | replan `continue_from_here` | — | `test_itinerary_replan_new.py` | полное (It) |
| UC-043 | Custom replan message | частично | нет | `reason_type=custom` + парсинг | — | `test_itinerary_replan_new.py` | частичное |
| UC-044 | Multi-stop replan | да | нет | completed ids, хвост | — | `test_itinerary_replan_new.py` | полное (It) |
| UC-045 | Replan after strong deviation | частично | нет | continue / shorten | — | частично теми же тестами | частичное |
| UC-050 | No places found | да | да | пустой/короткий маршрут + explanation | пустой `points` допустим | smoke router Rec; itinerary косвенно | частичное |
| UC-051 | All closed | частично | частично | OH pass, warnings | hard_filters / time | OH-тесты | частичное |
| UC-052 | Missing OH many | да | да | fallback scores, не ломать маршрут | аналогично в scoring/time | `test_opening_hours_fallback_new.py` | частичное |
| UC-053 | Pinned must-visit | нет | нет | — | — | — | в плане (V1) |
| UC-054 | Diversity collapse | частично | частично | diversity в selection | assembly diversity | частично через generate tests | частичное |
| UC-055 | Replan when completed | частично | нет | хвост пустой | — | `test_itinerary_replan_new.py` | частичное |
| UC-056 | Malformed OH | да | частично | устойчивость парсинга OH | те же идеи в time-aware | `test_opening_hours_filter.py` и др. | частичное |
| UC-057 | No swap candidate | да | частично | `choose_replacement_for_closed_place` | нет swap как в itinerary | OH / replan тесты | частичное |
| UC-058 | Low-confidence route | частично | частично | explanation, warnings | `explanation`, warnings на точках | `test_explainability_service.py` | минимальное |
| UC-060 | No trip_start | да | частично | ослабленный pass2 при отсутствии старта | `now` в pipeline | `test_opening_hours_fallback_new` и др. | частичное |
| UC-061 | Missing city TZ | частично | частично | fallback TZ | город/сессия в retrieval | `test_opening_hours_timezone_new.py` | частичное |
| UC-062 | Reserve exhausted | да | частично | replacement loop | — | встроено в itinerary builder тесты косвенно | частичное |
| UC-063 | Radius expansion | да | частично | candidate retrieval expansion | радиус в `MergedContext` / retrieval | `test_candidate_retrieval_db_smoke` (контекст) | частичное |
| UC-070 | Explanation per point | да | частично | `itinerary_explanation_service` | точки + поля времени в Rec | `test_explainability_service.py`, itinerary | частичное |
| UC-071 | Route-level explanation | да | да | summary в ответе generate | `explanation` в Rec JSON | `test_recommendations_route_router.py` (summary) | полное |
| UC-072 | Honest uncertainty | частично | частично | warnings в текстах | warnings / time_warning | частично | минимальное |

---

## Индекс автотестов (itinerary / время / replan)

| Файл | Зона |
|------|------|
| `tests/test_itinerary_scoring_new.py` | Скоринг, контекстные флаги (dog, children, indoor, anti-tourist). |
| `tests/test_itinerary_replan_new.py` | Replan: coffee/food/rest/shorten/continue/custom. |
| `tests/test_replan_stop_respects_opening_hours_new.py` | Replan и часы работы. |
| `tests/test_opening_hours_midnight_crossing.py` | Полночь / окна. |
| `tests/test_opening_hours_timezone_new.py` | Таймзона. |
| `tests/test_opening_hours_fallback_new.py` | Деградации без полных OH. |
| `tests/test_opening_hours_filter.py` | Фильтрация по OH. |
| `tests/test_candidate_opening_hours_filter_new.py` | Кандидаты и OH. |
| `tests/test_generate_filters_closed_places_new.py` | Закрытые места при генерации. |
| `tests/test_route_builder_pipeline_smoke.py` | Сквозной recommendation pipeline (сервисы). |
| `tests/test_explainability_service.py` | Explainability для `FinalRoute`. |
| `tests/test_recommendations_route_router.py` | HTTP smoke `POST /recommendations/route` (моки). |

---

## Правила из §9 `01_use_cases.md`

| Правило | Связанные UC | Itinerary | Recommendation | Примечание |
|---------|----------------|-----------|----------------|------------|
| Открывается позже в окне маршрута | UC-025, UC-020 | частичное | частичное | Тесты на OH и generate; Rec — `time_aware_service`. |
| OH не доминируют единолично | UC-004, scoring | частичное | частичное | Баланс score vs OH в эвристиках. |
| Честная деградация без данных | UC-052, UC-060, UC-061 | частичное | частичное | Fallback + explanation. |

---

## Как поддерживать этот файл

1. После изменения `itinerary_*`, `route_builder_service` или контрактов `schemas/itinerary*.py` / `recommendation_route.py` — проверить строки затронутых UC.  
2. При добавлении автотеста на сценарий из `01_use_cases.md` — дописать файл в колонку «Автотесты» и при необходимости поднять «Оценку».  
3. Статусы в [`03_test_matrix.md`](03_test_matrix.md) (`passed` / `failed`) **не** дублируются здесь: там ручной прогон.

---

## Сводка

- **Itinerary** закрывает большинство **MVP** UC из документа 01, но не все acceptance «на 100%»; часть **V1/V2** осознанно **нет** в коде.  
- **Recommendation** пересекается с UC-001–004, 011, 020–025 (время/OH), 024, 050–052, 056–058, 070–071 только **частично** и **другим контрактом** (без текста и replan).  
- Полное **покрытие чеклистов** из `01_use_cases.md` **не** достигается одним только наличием сервисов — нужны целевые тесты и проход по `03_test_matrix.md`.
