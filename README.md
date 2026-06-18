# City Guide API

Backend для городского гида в стиле Tripadvisor с упором на сценарный поиск, маршруты, города и места.

## Что это

Проект представляет собой backend на Python для будущего городского travel/local guide сервиса.

Текущая цель:
- построить чистую backend-основу
- заложить архитектуру под масштабирование на другие города
- подготовить API для мест, городов и категорий
- сделать базу для дальнейшей разработки фильтров, тегов, подборок, маршрутов и AI-логики

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

## Что уже реализовано

### Инфраструктура
- поднят FastAPI-проект
- настроено виртуальное окружение
- подключен PostgreSQL
- настроен Alembic для миграций
- вынесен конфиг в `core/config.py`
- настроены сессии БД и зависимости

### Города
Реализовано API для городов:
- `GET /cities/`
- `GET /cities/{city_id}`
- `GET /cities/by-slug/{slug}`

Что хранится у города:
- slug
- name
- region
- country
- timezone
- center_lat
- center_lng
- is_active

### Категории
Реализовано API для категорий:
- `GET /categories/`
- `GET /categories/{category_id}`
- `GET /categories/by-code/{code}`

Что хранится у категории:
- code
- name
- is_active

### Места
Реализован базовый CRUD для мест:
- `GET /places/`
- `GET /places/{place_id}`
- `GET /places/by-slug/{slug}`
- `POST /places/`
- `PUT /places/{place_id}`
- `DELETE /places/{place_id}`

Поддерживаются фильтры:
- `city_id`
- `city_slug`
- `category_id`
- комбинированная фильтрация, например:
  - `/places/?city_slug=zelenogradsk&category_id=1`

Что хранится у места:
- city_id
- category_id
- slug
- title
- short_description
- category
- address
- lat
- lng
- price_level
- dog_friendly
- family_friendly
- indoor
- outdoor
- is_active

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

## Запуск через Docker

### Подготовка

Скопируй `.env.example` в `.env` и заполни переменные:

```bash
cp .env.example .env
```

Убедись, что в `.env` указан правильный хост базы данных для Docker:

```
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

Бот для локальной разработки: @cityGuideDevBot

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

## Структура проекта

```text
.
├── core/
│   ├── __init__.py
│   └── config.py
├── db/
│   ├── __init__.py
│   ├── base.py
│   ├── dependencies.py
│   └── session.py
├── migrations/
│   ├── versions/
│   ├── env.py
│   └── script.py.mako
├── models/
│   ├── __init__.py
│   ├── category.py
│   ├── city.py
│   └── place.py
├── routers/
│   ├── __init__.py
│   ├── categories.py
│   ├── cities.py
│   └── places.py
├── schemas/
│   ├── __init__.py
│   ├── category.py
│   ├── city.py
│   └── place.py
├── services/
│   ├── __init__.py
│   ├── category_service.py
│   ├── city_service.py
│   └── place_service.py
├── .env
├── .env.example
├── alembic.ini
├── main.py
└── requirements.txt
```
