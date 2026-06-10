# City Go — QA Test Matrix

## Зачем нужен этот файл

Этот документ — **основная QA-поверхность для itinerary + replan**.

Он используется для:
- проверки корректности маршрутов;
- проверки деградаций;
- проверки edge cases;
- regression testing после изменений в scoring / routing.

Важно:
- тесты описывают **ожидаемое поведение системы**, а не текущую реализацию;
- каждый тест должен быть воспроизводим;
- статусы заполняются вручную.

---

## Статусы тестов

- `not_run`
- `passed`
- `failed`
- `partial`
- `blocked`

---

# 1. Core Generation Tests

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-001-1 | Standard route generation | city=amsterdam, budget=240, start=10:00 | 4–6 points, valid order | baseline | not_run |
| TC-001-2 | No start time | no trip_start | route returned, degraded OH logic | degradation | not_run |
| TC-001-3 | Few places in city | city has <5 places | radius expansion triggered | retrieval | not_run |
| TC-001-4 | Missing opening hours | all OH null | route built, uncertainty surfaced | data gap | not_run |
| TC-001-5 | Very short budget | budget=20 | 1–2 points near start | constraint | not_run |

---

# 2. Distance / Geo Tests

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-002-1 | Nearby walk | GPS, budget=90 | 2–3 nearby points | distance priority | not_run |
| TC-002-2 | Edge of city | GPS near border | no out-of-city drift | geo filtering | not_run |
| TC-002-3 | Poor GPS accuracy | accuracy >500m | expanded radius | fallback | not_run |
| TC-002-4 | No nearby places | empty radius | expansion triggered | retrieval | not_run |

---

# 3. Opening Hours Core Tests

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-010-1 | Fully open | visit inside window | oh_score ~1.0 | baseline | not_run |
| TC-010-2 | Partial overlap | visit partially overlaps | reduced score | overlap | not_run |
| TC-010-3 | Closed | visit outside window | oh_score = 0 | rejection | not_run |
| TC-010-4 | Missing OH | opening_hours=None | oh_score = 0.65 | fallback | not_run |
| TC-010-5 | Malformed OH | broken format | no crash, fallback score | robustness | not_run |

---

# 4. Opens Later Scenarios (CRITICAL)

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-020-1 | Opens later valid | opens=18:00, visit_time=18:30 | included in route | core logic | not_run |
| TC-020-2 | Opens later invalid position | opens=18:00, visit_time=15:30 | excluded or swapped | ordering | not_run |
| TC-020-3 | Opens after route ends | opens=18:00, route ends=17:00 | excluded | constraint | not_run |
| TC-020-4 | Evening candidate pool | start=19:00, opens=20:00 | NOT filtered out | retrieval bug | not_run |

---

# 5. Closing Soon Logic

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-030-1 | Closing soon reorder | closes=17:00, start=14:00 | appears early | urgency | not_run |
| TC-030-2 | Two closing soon | 2 places close early | both early | priority conflict | not_run |
| TC-030-3 | Closing soon far away | far distance | not forced reorder | geometry | not_run |

---

# 6. Waiting Gap Scenarios

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-040-1 | Small wait gap | gap=5min | keep with note | UX | not_run |
| TC-040-2 | Medium gap with alternatives | gap=30min | swapped | decision logic | not_run |
| TC-040-3 | Large gap no alternatives | gap=60min | keep with warning | fallback | not_run |

---

# 7. Midnight / Night Scenarios

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-050-1 | Midnight crossing | open=22:00–02:00 | valid late visit | overnight | not_run |
| TC-050-2 | Yesterday window | open prev day | correct match | window logic | not_run |
| TC-050-3 | After closing | visit after 02:00 | oh_score=0 | correctness | not_run |
| TC-050-4 | 24h place | open=00:00–00:00 | always valid | special case | not_run |

---

# 8. Route Structure & Budget

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-060-1 | Route truncation | budget too small | tail trimmed | constraint | not_run |
| TC-060-2 | Single place case | extreme short budget | 1 place returned | fallback | not_run |
| TC-060-3 | No truncation needed | normal case | full route kept | baseline | not_run |

---

# 9. Diversity Tests

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-070-1 | Many cafes | 30 cafes | capped diversity | collapse | not_run |
| TC-070-2 | Single category city | only cafes | allowed | fallback | not_run |
| TC-070-3 | Mixed city | cafes + museums | balanced route | normal | not_run |

---

# 10. Context Tests

## Budget

| TC ID | Scenario | Input | Expected | Status |
|------|--------|------|---------|--------|
| TC-080-1 | Budget filter | budget=1 | cheap only | not_run |
| TC-080-2 | Budget replan | replan + budget | respected | not_run |

## Dog

| TC ID | Scenario | Input | Expected | Status |
|------|--------|------|---------|--------|
| TC-081-1 | Dog route | with_dog=true | only dog-friendly | not_run |

## Indoor

| TC ID | Scenario | Input | Expected | Status |
|------|--------|------|---------|--------|
| TC-082-1 | Indoor only | indoor_only=true | no outdoor | not_run |

---

# 11. Replan Tests

| TC ID | Scenario | Input | Expected | Edge Focus | Status |
|------|--------|------|---------|-----------|--------|
| TC-090-1 | Coffee insertion | coffee_stop | nearest open inserted | replan | not_run |
| TC-090-2 | Coffee none available | no cafes open | unchanged route | fallback | not_run |
| TC-090-3 | Shorten route | budget reduced | trimmed route | constraint | not_run |
| TC-090-4 | Continue from here | moved location | reordered route | geometry | not_run |
| TC-090-5 | Multi-stop replan | partial completion | remaining rebuilt | flow | not_run |
| TC-090-6 | Completed route | all done | empty + message | edge | not_run |

---

# 12. Failure Scenarios

| TC ID | Scenario | Input | Expected | Status |
|------|--------|------|---------|--------|
| TC-100-1 | No places | empty city | safe response | not_run |
| TC-100-2 | All closed | night 03:00 | warning route | not_run |
| TC-100-3 | Missing OH | most null | uncertainty surfaced | not_run |
| TC-100-4 | Malformed data | broken OH | no crash | not_run |

---

# 13. System Behavior

| TC ID | Scenario | Input | Expected | Status |
|------|--------|------|---------|--------|
| TC-110-1 | No start time | missing trip_start | degraded route | not_run |
| TC-110-2 | Missing timezone | city no tz | fallback UTC | not_run |
| TC-110-3 | Reserve exhausted | no swap candidates | warning kept | not_run |
| TC-110-4 | Radius expansion | few candidates | expanded search | not_run |

---

# 14. Explanation Tests (VERY IMPORTANT)

| TC ID | Scenario | Input | Expected | Status |
|------|--------|------|---------|--------|
| TC-120-1 | Point reason | normal route | each point has reason | not_run |
| TC-120-2 | Closing soon explanation | early closing | reason mentions it | not_run |
| TC-120-3 | Wait gap explanation | early arrival | wait message shown | not_run |
| TC-120-4 | Truncation explanation | trimmed route | explanation present | not_run |
| TC-120-5 | Data limitation | missing OH | uncertainty explained | not_run |

---

# 15. High-Risk Regression Set

Этот набор должен гоняться после каждого изменения scoring / routing.

| TC ID | Scenario |
|------|--------|
| TC-R1 | Opens later scenario |
| TC-R2 | Closing soon reorder |
| TC-R3 | Midnight crossing |
| TC-R4 | Replan coffee |
| TC-R5 | Budget constraint |
| TC-R6 | Missing opening_hours |
| TC-R7 | Route truncation |
| TC-R8 | Reserve exhausted |

---

# 16. Как использовать этот файл

### Для разработки
- при добавлении логики → добавляем тест-кейс;
- при фиксе бага → добавляем regression тест.

### Для QA
- каждый тест должен быть:
  - воспроизводим;
  - с конкретным входом;
  - с чётким expected результатом.

### Для продукта
- если сценарий не покрыт → это gap, а не “edge case”.

---

# 17. Главный принцип тестирования

> Мы тестируем не только корректность маршрута,
> но и честность поведения системы.

Это включает:
- отсутствие ложной уверенности;
- объяснимость решений;
- предсказуемость деградации.
