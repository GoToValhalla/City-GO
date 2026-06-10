# City Go — Traceability Matrix (Use Cases → Tests → Code)

## Зачем нужен этот файл

Этот документ связывает:

- use cases (что должно работать)
- тесты (как мы это проверяем)
- код (где это реализовано)

Это даёт:
- прозрачность системы;
- контроль покрытия;
- быстрый дебаг (видно, где сломалось);
- основу для QA и регрессии.

---

# 1. Структура

Каждый use case должен иметь:

- минимум 1 тест;
- ссылку на код (сервис / функция);
- статус покрытия.

---

# 2. Core Use Cases

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-001 | Generate itinerary | test_generate_basic_new | itinerary_service.generate | partial |
| UC-002 | Quick walk near me | test_generate_nearby_new | candidate_service + itinerary_service | partial |
| UC-003 | Full day itinerary | test_generate_full_day_new | itinerary_service.generate | partial |
| UC-004 | Interest-driven route | test_generate_by_interest_new | scoring + filters | partial |

---

# 3. Time-Aware

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-020 | Evening route | test_evening_route_new | opening_hours + scoring | partial |
| UC-021 | Closing soon priority | — | scoring (planned) | none |
| UC-022 | Midnight crossing | test_opening_hours_midnight_crossing_new | opening_hours utils | partial |
| UC-023 | Waiting gap | — | not implemented | none |
| UC-024 | Route truncation | test_route_trim_new | itinerary builder | partial |
| UC-025 | Opens later | test_opening_later_new | pass 2 logic | partial |

---

# 4. Location-Aware

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-030 | Start from address | test_start_from_address_new | geocoding + builder | partial |
| UC-031 | Loop route | — | route builder | none |
| UC-032 | Area constraint | — | not implemented | none |
| UC-033 | A→B route | — | not implemented | none |

---

# 5. Replan

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-040 | Coffee stop | test_replan_stop_respects_opening_hours | itinerary_replan_service | partial |
| UC-041 | Shorten route | test_replan_shorten_new | itinerary_replan_service | partial |
| UC-042 | Continue route | test_replan_continue_new | replan ordering | partial |
| UC-043 | Custom replan | test_replan_custom_new | AI + replan service | partial |
| UC-044 | Multi-stop replan | test_replan_multi_new | replan pipeline | partial |

---

# 6. Failure / Edge

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-050 | No places | test_no_places_new | candidate_service | partial |
| UC-051 | All closed | test_all_closed_new | opening_hours logic | partial |
| UC-052 | Missing OH | test_missing_oh_new | fallback logic | partial |
| UC-056 | Malformed OH | — | parsing layer | none |
| UC-057 | No swap candidate | test_no_swap_new | pass 2 | partial |

---

# 7. System Behavior

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-060 | No trip_start | test_no_start_time_new | defaults | partial |
| UC-061 | Missing timezone | test_timezone_fallback_new | city timezone | partial |
| UC-062 | Reserve exhausted | test_reserve_empty_new | swap logic | partial |

---

# 8. Explanation

| UC ID | Use Case | Tests | Code | Coverage |
|---|---|---|---|---|
| UC-070 | Point explanation | test_point_reason_new | explanation builder | partial |
| UC-071 | Route explanation | test_route_explanation_new | response layer | partial |
| UC-072 | Honest uncertainty | — | not implemented | none |

---

# 9. Coverage Levels

- `none` — нет тестов и/или реализации
- `partial` — частично покрыто (основной happy path)
- `good` — покрыты основные сценарии + edge cases
- `full` — production-level покрытие

---

# 10. Правила

## 10.1 Каждый новый use case
Должен:
- появиться в `02_use_cases.md`
- появиться здесь
- иметь тест

## 10.2 Каждый тест
Должен:
- ссылаться на use case
- проверять конкретное поведение (не “в целом работает”)

## 10.3 Каждый баг
Должен:
- указывать UC ID
- фикситься через тест

---

# 11. Ключевой принцип

> Если use case не связан с тестом —
> он не существует.

> Если тест не связан с use case —
> он бесполезен.
