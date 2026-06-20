# City Go

City Go — городской travel/local guide сервис с упором на места, маршруты, планирование прогулок и дальнейший AI-слой рекомендаций.

## Что это

Проект объединяет backend, frontend, админку и Telegram-бота для городского гида. Основной пользовательский сценарий — собрать полезный маршрут по городу от выбранной стартовой точки с учётом времени, интересов, бюджета, темпа и качества данных по местам.

Текущая продуктовая цель:
- строить маршруты в реальном времени;
- строить маршрут от нужного места: центр города, текущая геолокация, адрес, точка на карте или выбранное место;
- поддержать планирование маршрутов заранее;
- дать пользователю понятный маршрут списком и на карте;
- объяснять, почему маршрут не собрался или получился частичным;
- подготовить основу для live route editing: заменить, удалить, добавить место, перестроить от текущей точки.

Пилотный город:
- Зеленоградск, Калининградская область

## Текущий стек

- Python 3.11
- FastAPI
- PostgreSQL
- Alembic
- SQLAlchemy 2.0
- Pydantic
- Uvicorn
- React / Vite
- Docker Compose

## Основной маршрутный API

Новая пользовательская сборка маршрутов работает через:

```http
POST /v1/user-routes/build
```

Старый endpoint:

```http
POST /routes/generate
```

объявлен legacy и помечен как deprecated. В ответ добавляется header:

```http
X-Deprecated: Use POST /v1/user-routes/build instead
```

Текущая цепочка route building:

```text
POST /v1/user-routes/build
→ UserRouteBuildService
→ RouteBuilderService
→ RouteEngine
→ InstantRouteStrategy
→ build_dynamic_route
→ context_merge
→ candidate_retrieval
→ hard_filters
→ scoring
→ interest_matching
→ adaptive_plan
→ assembly
→ time_ordering
→ time_aware
→ budget_fit
→ quality_gates
→ finalize
→ UserRouteState
```

`RouteEngine` сейчас является безопасным тонким слоем над существующим пайплайном. Он нужен как точка расширения под будущие стратегии:

- `InstantRouteStrategy` — маршрут сейчас / от выбранной стартовой точки;
- `PlannedRouteStrategy` — планирование на дату и время;
- `RecomputeRouteStrategy` — пересборка активного маршрута от текущей позиции.

## Статусы маршрута

`/v1/user-routes/build` возвращает доменный результат, а не только сетевую ошибку.

| Статус | Значение |
|---|---|
| `ready` | Маршрут собран в полезном виде. |
| `partial_route` | Маршрут собран частично, его можно показать пользователю с предупреждением. |
| `no_route` | Маршрут не собран, причина должна быть в `partial_reason` и `debug_trace`. |
| `failed` | Системная или алгоритмическая ошибка качества маршрута. |

Ключевые поля ответа:

```json
{
  "status": "ready | partial_route | no_route | failed",
  "partial_reason": "not_enough_route_points | time_budget_too_tight | filters_too_strict | interests_not_matched | ...",
  "total_places": 3,
  "points": [],
  "warnings": [],
  "user_warnings": [],
  "debug_trace": []
}
```

## Текущая логика route building

Маршрут должен стремиться к полезной форме, но target по точкам является soft target, а не жёстким правилом.

| Время | Цель по точкам | Минимум для `ready` |
|---:|---:|---:|
| до 60 минут | 2 точки | 2 точки |
| до 120 минут | 4 точки | 3 точки |
| до 240 минут | 6 точек | 5 точек |
| больше 240 минут | до 8 точек | 6 точек |

Правила деградации:
- маршрут из 1 точки не считается полноценным `ready`;
- короткий маршрут возвращается как `partial_route` с понятным warning, если не проходит soft threshold;
- при очень tight budget допускается one-point `partial_route` с warning `budget_very_tight`;
- если интересы не совпали с местами, система должна использовать fallback на близкие категории или нейтральные точки;
- если radius слишком узкий, candidate retrieval использует расширение радиуса и city-wide fallback;
- если hard filters удалили всё, debug trace должен показывать причины удаления;
- frontend отдельно обрабатывает `ready`, `partial_route` и `no_route`.

## Что уже реализовано

### Инфраструктура
- поднят FastAPI-проект;
- подключен PostgreSQL;
- настроен Alembic для миграций;
- вынесен конфиг в `core/config.py`;
- настроены сессии БД и зависимости;
- Docker Compose запускает backend, frontend, bot и миграции.

### Города
Реализовано API для городов:
- `GET /cities/`
- `GET /cities/{city_id}`
- `GET /cities/by-slug/{slug}`

Что хранится у города:
- slug;
- name;
- region;
- country;
- timezone;
- center_lat;
- center_lng;
- is_active.

### Категории
Реализовано API для категорий:
- `GET /categories/`
- `GET /categories/{category_id}`
- `GET /categories/by-code/{code}`

Что хранится у категории:
- code;
- name;
- is_active.

### Места
Реализован CRUD и публичный каталог мест:
- `GET /places/`
- `GET /places/{place_id}`
- `GET /places/by-slug/{slug}`
- `POST /places/`
- `PUT /places/{place_id}`
- `DELETE /places/{place_id}`

Поддерживаются фильтры:
- `city_id`;
- `city_slug`;
- `category_id`;
- комбинированная фильтрация.

Что хранится у места:
- city_id;
- category_id;
- slug;
- title;
- short_description;
- category;
- address;
- lat;
- lng;
- price_level;
- dog_friendly;
- family_friendly;
- indoor;
- outdoor;
- is_active;
- route eligibility / visibility flags;
- quality score / quality tier.

### Data Foundation P1

Добавлены quality scoring и city readiness operations:

- `services/quality_scoring.py` — пересчёт `quality_score`, `quality_tier`, component scores и route eligibility для места.
- `services/city_readiness/score.py` — пересчёт city readiness и запись `CityQualitySnapshot`.
- `POST /admin/routes/readiness/{city_slug}/recalculate` — админский пересчёт readiness по городу.
- `scripts/recalculate_city_readiness.py` — серверный скрипт пересчёта.
- `docs/data-foundation-p1.md` — полный операционный контракт P1.

Примеры:

```bash
python scripts/recalculate_city_readiness.py --city zelenogradsk
python scripts/recalculate_city_readiness.py --all
python -m pytest tests/test_data_foundation_quality_readiness.py -q
```

## Ближайшие задачи по маршрутам

- Проверить production deploy после route building fixes.
- Снять реальный `DEBUG BUILD RESULT` для `/v1/user-routes/build`.
- Убрать временный hard log после диагностики.
- Разобрать `debug_trace` реального запроса: retrieval, hard_filters, scoring, assembly, budget_fit, finalize.
- Расширить `RouteEngine`: добавить `PlannedRouteStrategy` и `RecomputeRouteStrategy` без переписывания текущего instant-пайплайна.
- Добавить доменные сущности для real-time: `RoutePlan`, `RouteSession`, `Waypoint`, `RouteEvent`.
- Доработать route planning режим: маршрут не только “сейчас”, но и заранее на дату/время.
- Доработать real-time режим: старт/пауза/завершение, перестроение от текущей точки, замена следующей точки.
- Продумать карту и список маршрута: активные точки, закрытые/недоступные точки, описание места во внутреннем фрейме.

## Запуск через Docker

### Подготовка

Скопируй `.env.example` в `.env` и заполни переменные:

```bash
cp .env.example .env
```

Убедись, что в `.env` указан правильный хост базы данных для Docker:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@db:5432/city_guide
```

### Продакшн

Собирает React-приложение, раздаёт статику через nginx, запускает backend и бота.

```bash
docker compose up --build
```

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

Миграции применяются автоматически при старте.

### Разработка

Backend запускается с `--reload`, фронтенд — через Vite dev server с hot reload.

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

| Сервис | Адрес |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

### Полезные команды

```bash
# Остановить все контейнеры
docker compose down

# Остановить и удалить данные БД
docker compose down -v

# Посмотреть логи конкретного сервиса
docker compose logs -f backend
docker compose logs -f bot

# Применить миграции вручную
docker compose run --rm migrate
```
