# City Go — Itinerary Known Gaps and Roadmap

## Зачем нужен этот файл

Этот документ фиксирует:
- известные дыры в itinerary / replan логике;
- что относится к MVP;
- что относится к следующему слою качества;
- в каком порядке это лучше реализовывать.

Важно:
- это **не use case файл**;
- это **не QA matrix**;
- это рабочий документ для product / backend / QA синхронизации.

---

## Текущий продуктовый принцип

City Go должен строить не просто список мест, а **маршрут во времени**.

Значит:
- candidate retrieval не должен слишком рано убивать хорошие точки;
- ranking должен учитывать не только качество места, но и временную валидность;
- route builder должен учитывать порядок посещения;
- replan должен работать в той же логике, что и generate;
- explanation должен честно объяснять ограничения и деградации.

---

# 1. Критичные product / logic gaps

## G-001 — Candidate retrieval может слишком рано исключать хорошие точки
### Проблема
Если на retrieval слое фильтровать точки по принципу “закрыто в момент старта”, то из candidate pool исчезают места, которые:
- откроются позже по ходу маршрута;
- могут быть валидны на 2–4 позиции;
- нужны для вечернего сценария.

### Пример
- старт в 15:00
- маршрут на 4 часа
- место открывается в 18:00

Такое место нельзя выбрасывать только потому, что оно закрыто в 15:00.

### Что должно быть
На раннем слое надо убирать только:
- неактивные точки;
- несовместимые по жёстким ограничениям точки;
- точки, закрытые **весь день**, если у нас есть достаточно надёжные opening hours.

### Приоритет
**MVP**

---

## G-002 — Opening hours нельзя использовать как жёсткий бинарный сигнал в ranking
### Проблема
Если делать `open = 1 / closed = 0`, система:
- теряет места, которые скоро откроются;
- не различает “полностью открыто” и “закрывается через 10 минут”;
- даёт слишком грубый маршрут.

### Что должно быть
Нужен `opening_hours_score`, основанный на overlap:
- visit window
- open window

С безопасной деградацией:
- нет данных → нейтральный score
- malformed data → safe fallback
- partial overlap → сниженный score, а не мгновенный discard

### Приоритет
**MVP**

---

## G-003 — Нет полноценной visit-time-aware логики на уровне всего маршрута
### Проблема
Точка может быть “хорошей” в вакууме, но плохой в конкретном порядке маршрута.

### Что должно быть
Нужен sequential pass:
- считать `visit_time` для каждой точки;
- валидировать точку в реальном времени посещения;
- при проблеме делать local swap или оставлять warning.

### Приоритет
**MVP**

---

## G-004 — Нет нормального handling для closing soon
### Проблема
Если место закрывается заметно раньше других, текущий ranking может поставить его слишком поздно.

### Что должно быть
Нужен отдельный слой urgency:
- closing soon bonus;
- local reorder;
- либо хотя бы explanation, что точка поставлена раньше из-за closing time.

### Приоритет
**V1**

---

## G-005 — Нет полноценной wait-gap логики
### Проблема
Пользователь может прийти к точке до открытия:
- на 5 минут раньше;
- на 30 минут раньше;
- на 90 минут раньше.

Сейчас это может либо молча проходить, либо ломать качество маршрута.

### Что должно быть
Нужны правила:
- маленький gap → можно оставить с warning;
- средний gap → пытаться переставить;
- большой gap → swap / исключение / fallback.

### Приоритет
**V1**

---

## G-006 — Diversity logic пока недостаточно сильная
### Проблема
Если в базе много однотипных мест, маршрут может получаться однообразным.

### Что должно быть
Diversity должна смотреть:
- не только на соседние точки;
- но и на глобальное распределение категорий в маршруте.

### Приоритет
**V1**

---

## G-007 — Budget constraints должны жить сквозным контекстом
### Проблема
Budget не должен теряться между:
- generate
- current_route_context
- replan
- stop insertion

### Что должно быть
Budget level должен:
- сохраняться в route context;
- участвовать в replan;
- фильтровать stop insertion;
- отражаться в explanation.

### Приоритет
**MVP**

---

## G-008 — Нет meal slot logic для длинных маршрутов
### Проблема
Маршрут на 4–8 часов может пройти через окно 12:00–15:00 и не содержать ни одной food точки.

### Что должно быть
Если маршрут длинный и проходит через lunch window:
- система должна уметь вставить food/cafe slot;
- или хотя бы поднять вес food категории в середине маршрута.

### Приоритет
**V1**

---

## G-009 — Return-to-start пока не влияет на форму маршрута полноценно
### Проблема
Флаг `return_to_start` не должен быть просто полем в схеме.

### Что должно быть
Если пользователь просит loop:
- последние точки должны учитывать близость к старту;
- return leg должен входить в time / distance;
- route shape должен адаптироваться под loop-сценарий.

### Приоритет
**V1**

---

## G-010 — Нет pinned / must-visit механики
### Проблема
Пользователь может хотеть обязательно включить конкретное место.

### Что должно быть
Нужен механизм:
- pinned place;
- оптимальная вставка в маршрут;
- warning, если точка закрыта или неудобна.

### Приоритет
**V1**

---

## G-011 — Explanation пока недостаточно продуктовый
### Проблема
Даже если маршрут логически правильный, пользователь не понимает:
- почему точка здесь;
- почему она раньше другой;
- почему была деградация;
- почему маршрут урезан.

### Что должно быть
Explanation должен уметь отражать:
- closing soon;
- wait gap;
- truncation;
- radius expansion;
- missing data;
- fallback timezone;
- low-confidence route.

### Приоритет
**MVP / V1**

---

## G-012 — Missing / malformed data handling нужно сделать системным, а не точечным
### Проблема
Данные по place и city могут быть неполными:
- opening_hours нет;
- opening_hours сломаны;
- timezone нет;
- average_visit_duration_minutes нет;
- price_level нет.

### Что должно быть
Safe degradation rules:
- не падать;
- использовать fallback;
- логировать проблему;
- отражать uncertainty в explanation.

### Приоритет
**MVP**

---

# 2. Текущие продуктовые риски

## R-001 — False confidence
Система может выглядеть слишком уверенной там, где данные слабые.

### Риск
Пользователь увидит “красивый” маршрут, но часть точек будет невалидна.

### Снижение риска
- warning flags;
- route-level uncertainty;
- safe fallback logic.

---

## R-002 — Over-filtering on retrieval
Если candidate pool режется слишком агрессивно, pass 2 уже нечего спасать.

### Снижение риска
- retrieval должен быть более щадящим;
- часть проблем должна решаться на ranking / validation слоях.

---

## R-003 — Route looks smart but feels awkward
Даже если формально маршрут валиден, он может быть:
- однообразным;
- слишком тяжёлым;
- с нелогичными паузами;
- без еды в длинном маршруте.

### Снижение риска
- diversity;
- fatigue;
- meal slot;
- better explanation.

---

## R-004 — Replan diverges from generate logic
Если generate и replan живут по разным правилам, продукт становится непредсказуемым.

### Снижение риска
- общие time/opening helpers;
- общий контекст ограничений;
- одинаковые fallback rules.

---

# 3. MVP scope

Ниже — то, что должно быть доведено в первую очередь.

## MVP-1 — Opening-hours-safe generate
Включает:
- safe opening hours parsing;
- timezone-aware checks;
- pass 2 visit-time validation;
- midnight crossing support;
- honest degradation without trip_start_datetime;
- route warnings when confidence is low.

## MVP-2 — Budget-safe context flow
Включает:
- budget_level в generate;
- budget_level в current_route_context;
- budget_level в replan;
- budget-aware stop insertion.

## MVP-3 — Honest failure handling
Включает:
- no places found;
- all places closed;
- missing opening_hours;
- malformed opening_hours;
- missing timezone;
- reserve exhausted.

## MVP-4 — Explanation baseline
Включает:
- point reason;
- route explanation;
- data limitation notes;
- truncation / fallback notes.

## MVP-5 — Replan baseline consistency
Включает:
- coffee stop;
- shorten route;
- continue from here;
- completed route handling;
- safe no-op / safe fallback behavior.

---

# 4. V1 scope

## V1-1 — Closing-soon prioritization
- urgency bonus;
- local reorder;
- explanation for reordering.

## V1-2 — Wait-gap logic
- opens soon handling;
- wait tolerance;
- swap vs keep decision.

## V1-3 — Stronger diversity
- global category counter;
- anti-collapse logic;
- explanation when diversity impossible.

## V1-4 — Meal slot injection
- lunch-aware insertion;
- mid-route cafe/food logic.

## V1-5 — Loop route optimization
- return-to-start aware ordering;
- end proximity weighting;
- return leg in route metrics.

## V1-6 — Pinned place support
- must-visit point;
- optimal insertion;
- explicit warnings.

## V1-7 — Low-confidence route handling
- confidence level for route;
- explicit uncertainty surfacing.

---

# 5. V2 scope

## V2-1 — Route from A to B
- directed route;
- separate start and end constraints.

## V2-2 — Area polygon constraints
- district / neighborhood routing;
- polygon-aware candidate filter.

## V2-3 — Travel fatigue logic
- fatigue_weight;
- penalties for heavy sequences;
- rest-aware composition.

## V2-4 — Weather-aware routing
- indoor/outdoor adaptation;
- weather-dependent penalties.

## V2-5 — Multi-day itineraries
- day splits;
- area grouping by day;
- fatigue and meal structure.

## V2-6 — Group itineraries
- multi-user interests;
- compromise scoring.

---

# 6. Recommended implementation order

## Step 1
Stabilize opening-hours foundation:
- safe parsing
- timezone usage
- pass 2 validation
- no-crash guarantees

## Step 2
Stabilize context persistence:
- budget in route context
- budget in replan
- stop insertion respects constraints

## Step 3
Improve explanation:
- point-level reason
- route-level degradation notes
- uncertainty notes

## Step 4
Improve route quality:
- diversity
- closing soon
- wait gap

## Step 5
Improve long-route behavior:
- meal slot
- fatigue
- loop routes

## Step 6
Add stronger user control:
- pinned places
- A→B
- area routing

---

# 7. What we intentionally do not do in MVP

Чтобы не расползаться, в MVP мы не уходим в:

- full constraint solver;
- beam search / heavy route optimization;
- live transport / transit engine;
- booking/reservation integrations;
- full weather routing;
- multi-day planner;
- collaborative/group planning;
- social layer;
- real-time crowd estimation.

---

# 8. Working product rule

Главное правило для itinerary блока:

> Лучше честный, ограниченный, объяснимый маршрут,
> чем “умный” маршрут, который выглядит красиво, но разваливается в реальности.

Это правило применять ко всем спорным решениям:
- over-filter vs degrade;
- swap vs keep with warning;
- missing data vs false precision;
- fallback vs fake certainty.
