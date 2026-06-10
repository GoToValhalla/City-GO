# City Go — Itinerary Status Tracking

## Зачем нужен этот файл

Этот документ нужен для **живого контроля статуса** itinerary / replan блока.

Он используется, чтобы:
- отмечать, что уже реализовано;
- не путать идеи, гипотезы и фактический код;
- видеть, что готово, что частично готово, а что ещё не начато;
- синхронизировать product / backend / QA.

Важно:
- этот файл обновляется **только по факту**;
- здесь не должно быть предположений;
- если что-то не проверено, статус не должен быть `implemented`.
- это статус legacy itinerary/replan слоя; актуальный production-контур
  recommendation/user-routes описан в `../implementation_status_and_next_steps.md`
  и `../architecture/backend_file_map.md`.

---

## Статусы

- `not_started` — ещё не начинали
- `in_progress` — в работе
- `partial` — часть логики есть, но поведение неполное
- `implemented` — реализовано в коде
- `needs_verification` — код есть, но нужно прогнать / проверить
- `blocked` — есть зависимость или внешний блокер

---

# 1. Core Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-001 | Generate itinerary from scratch | needs_verification | |
| UC-002 | Quick walk near me | needs_verification | |
| UC-003 | Full day itinerary | partial | meal slot ещё не реализован |
| UC-004 | Interest-driven route | needs_verification | |

---

# 2. Context-Aware Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-010 | Route with dog | needs_verification | |
| UC-011 | Budget-conscious route | needs_verification | проверить generate + replan целиком |
| UC-012 | Indoor only | needs_verification | |
| UC-013 | Anti-tourist mode | partial | нет сильных popularity/crowd сигналов |
| UC-014 | Route with children | partial | логика есть частично, нужен отдельный контроль темпа/усталости |

---

# 3. Time-Aware Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-020 | Evening route | partial | нужно проверить candidate pool и фильтр closed_all_day |
| UC-021 | Closing soon prioritization | not_started | |
| UC-022 | Midnight crossing | needs_verification | код и тесты подготовлены, не прогонялись |
| UC-023 | Waiting gap scenario | not_started | |
| UC-024 | Route truncation due to time budget | needs_verification | |
| UC-025 | Place opens later during route | partial | foundation есть, нужен полный end-to-end verify |
| UC-026 | Start too late for meaningful route | not_started | |

---

# 4. Location-Aware Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-030 | Route from typed address | needs_verification | |
| UC-031 | Loop route | partial | return_to_start есть, но shape optimization нет |
| UC-032 | Area-constrained route | not_started | |
| UC-033 | Route from A to B | not_started | |
| UC-034 | Must end near departure point | not_started | |

---

# 5. Replan Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-040 | Coffee stop insertion | needs_verification | opening hours + budget нужно прогнать |
| UC-041 | Shorten route | needs_verification | |
| UC-042 | Continue from here | needs_verification | |
| UC-043 | Custom replan with user message | needs_verification | |
| UC-044 | Multi-stop replan | needs_verification | |
| UC-045 | Replan after strong deviation | not_started | |

---

# 6. Failure / Edge Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-050 | No places found | needs_verification | |
| UC-051 | All places closed | partial | нужны явные warning / honest fallback |
| UC-052 | Missing opening_hours for many places | partial | explanation ещё не доведён |
| UC-053 | Pinned / must-visit place | not_started | |
| UC-054 | Diversity collapse | partial | глобальный diversity counter ещё не внедрён |
| UC-055 | Completed route replan | needs_verification | |
| UC-056 | Malformed opening_hours data | not_started | |
| UC-057 | No valid swap candidate | partial | часть поведения есть, нужен warning слой |
| UC-058 | Low-confidence data route | not_started | |

---

# 7. System Behavior Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-060 | No trip_start_datetime | needs_verification | |
| UC-061 | Missing city timezone | partial | fallback есть, explanation нет |
| UC-062 | Reserve pool exhausted | partial | нет полного surfaced warning |
| UC-063 | Radius expansion triggered | needs_verification | |

---

# 8. UX / Explanation Use Cases

| ID | Name | Status | Notes |
|---|---|---|---|
| UC-070 | Explanation per point | partial | reason есть, но не все продуктовые причины покрыты |
| UC-071 | Route-level explanation | partial | data limitations / degraded mode ещё не полные |
| UC-072 | Honest uncertainty communication | not_started | |

---

# 9. Known Gaps Tracking

| Gap ID | Name | Status | Notes |
|---|---|---|---|
| G-001 | Candidate retrieval excludes good later-opening places too early | partial | нужно проверить и добить closed_all_day модель |
| G-002 | Budget not fully safe through replan stop insertion | needs_verification | код правили, нужен прогон |
| G-003 | Diversity too weak | not_started | |
| G-004 | No proper closing-soon reorder | not_started | |
| G-005 | No meal slot logic | not_started | |
| G-006 | Return-to-start shape not optimized | not_started | |
| G-007 | No pinned/must-visit support | not_started | |
| G-008 | No wait-gap logic | not_started | |
| G-009 | open_duration mode too weak for timing quality | not_started | |
| G-010 | No warning flag on point | not_started | |
| G-011 | Context persistence must be verified end-to-end | needs_verification | |

---

# 10. New Tests Tracking

## Новые тесты, которые ещё не прогонялись

| File | Status | Notes |
|---|---|---|
| tests/test_opening_hours_filter.py | needs_verification | имя файла без `_new`, создан до фикса правила |
| tests/test_candidate_opening_hours_filter.py | needs_verification | имя файла без `_new`, создан до фикса правила |
| tests/test_replan_stop_respects_opening_hours.py | needs_verification | имя файла без `_new`, создан до фикса правила |
| tests/test_opening_hours_midnight_crossing_new.py | needs_verification | |
| tests/test_opening_hours_timezone_new.py | needs_verification | |
| tests/test_generate_filters_closed_places_new.py | needs_verification | |
| tests/test_opening_hours_fallback_new.py | needs_verification | |

---

# 11. Как обновлять этот файл

## После код-изменений
- `not_started` → `in_progress`
- `in_progress` → `implemented`, только если код действительно написан

## После локальной проверки / тестов
- `implemented` → `needs_verification`, если код есть, но не прогнан end-to-end
- `needs_verification` → `implemented`, если сценарий реально проверен

## Если найден баг
- любой статус → `partial` или `blocked`, в зависимости от проблемы

---

# 12. Рабочее правило

> Если мы не уверены, что сценарий реально проверен,
> статус не должен быть `implemented`.

Лучше:
- `partial`
- `needs_verification`

чем ложное ощущение готовности.
