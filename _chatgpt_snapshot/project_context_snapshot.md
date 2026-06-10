# Project Context Snapshot

## Git

```text
branch: master
commit: 7d312ddcbd36361aaa3476378b5cce085074be22

STATUS:
M migrations/versions/9c8e4b1a2f10_add_image_url_to_places.py
?? _chatgpt_snapshot/
```

## File List

- `README.md`
- `__init__.py`
- `api/__init__.py`
- `core/__init__.py`
- `core/config.py`
- `core/place_taxonomy.py`
- `db/__init__.py`
- `db/base.py`
- `db/dependencies.py`
- `db/session.py`
- `docs/ai_prompts.md`
- `docs/ai_retrieval_plan.md`
- `docs/change_history.md`
- `docs/commenting_policy.md`
- `docs/master_technical_spec.md`
- `docs/project_status.md`
- `docs/technical_spec.md`
- `frontend/README.md`
- `frontend/package-lock.json`
- `frontend/package.json`
- `frontend/src/App.css`
- `frontend/src/App.tsx`
- `frontend/src/api/nearby/nearby.api.ts`
- `frontend/src/api/open-now/openNow.api.ts`
- `frontend/src/api/places/places.api.test.ts`
- `frontend/src/api/places/places.api.ts`
- `frontend/src/components/places/PlaceCard.tsx`
- `frontend/src/components/ui/AppHeader.tsx`
- `frontend/src/components/ui/AppLink.tsx`
- `frontend/src/components/ui/Badge.tsx`
- `frontend/src/components/ui/EmptyState.tsx`
- `frontend/src/components/ui/PageBreadcrumbs.tsx`
- `frontend/src/components/ui/SectionHeader.tsx`
- `frontend/src/components/ui/SurfaceCard.tsx`
- `frontend/src/entities/place/model/types.ts`
- `frontend/src/features/place-search/model/filterPlaces.test.ts`
- `frontend/src/features/place-search/model/filterPlaces.ts`
- `frontend/src/index.css`
- `frontend/src/main.tsx`
- `frontend/src/pages/home/HomePage.test.tsx`
- `frontend/src/pages/home/HomePage.tsx`
- `frontend/src/pages/nearby/NearbyPage.tsx`
- `frontend/src/pages/open-now/OpenNowPage.tsx`
- `frontend/src/pages/places/PlaceDetailPage.tsx`
- `frontend/src/pages/places/PlacesListPage.tsx`
- `frontend/src/pages/routes/RoutesPage.tsx`
- `frontend/src/pages/routes/WalkRoutePage.tsx`
- `frontend/src/shared/api/endpoints.test.ts`
- `frontend/src/shared/api/endpoints.ts`
- `frontend/src/shared/api/http.ts`
- `frontend/src/shared/config/env.ts`
- `frontend/src/styles/responsive.css`
- `frontend/src/widgets/home/HomeHero.tsx`
- `frontend/src/widgets/home/HomeStats.tsx`
- `frontend/src/widgets/home/PlacesSection.tsx`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `main.py`
- `migrations/env.py`
- `migrations/versions/1e31cbdc17df_add_category_model.py`
- `migrations/versions/281a07116c51_add_route_models.py`
- `migrations/versions/3000b4f577bc_add_tag_model.py`
- `migrations/versions/3607cc80012d_add_collection_models.py`
- `migrations/versions/3fb51e7943f5_add_place_schedule_model.py`
- `migrations/versions/4a31a10f9e37_add_category_id_to_places.py`
- `migrations/versions/784d6d2f3828_add_slug_to_places.py`
- `migrations/versions/9c8e4b1a2f10_add_image_url_to_places.py`
- `migrations/versions/ac1e9bce72eb_add_place_tag_model.py`
- `migrations/versions/d7f42a463fe3_add_city_model.py`
- `migrations/versions/e48f13974bc8_init_place_model.py`
- `models/__init__.py`
- `models/category.py`
- `models/city.py`
- `models/collection.py`
- `models/collection_place.py`
- `models/place.py`
- `models/place_schedule.py`
- `models/place_tag.py`
- `models/route.py`
- `models/route_place.py`
- `models/tag.py`
- `routers/__init__.py`
- `routers/ai.py`
- `routers/categories.py`
- `routers/cities.py`
- `routers/collection_places.py`
- `routers/collections.py`
- `routers/nearby.py`
- `routers/open_now.py`
- `routers/place_search.py`
- `routers/place_seed_dry_run.py`
- `routers/place_seed_validation.py`
- `routers/place_tags.py`
- `routers/place_taxonomy.py`
- `routers/place_taxonomy_diagnostics.py`
- `routers/places.py`
- `routers/route_places.py`
- `routers/routes.py`
- `routers/tags.py`
- `schemas/__init__.py`
- `schemas/ai.py`
- `schemas/category.py`
- `schemas/city.py`
- `schemas/collection.py`
- `schemas/collection_place.py`
- `schemas/nearby.py`
- `schemas/open_now.py`
- `schemas/pagination.py`
- `schemas/place.py`
- `schemas/place_list_params.py`
- `schemas/place_query_params.py`
- `schemas/place_search.py`
- `schemas/place_search_response.py`
- `schemas/place_seed_bulk_validation_response.py`
- `schemas/place_seed_dry_run_request.py`
- `schemas/place_seed_import_summary.py`
- `schemas/place_seed_item.py`
- `schemas/place_seed_validation_request.py`
- `schemas/place_seed_validation_response.py`
- `schemas/place_tag.py`
- `schemas/place_taxonomy_diagnostics_response.py`
- `schemas/place_taxonomy_payload.py`
- `schemas/place_taxonomy_response.py`
- `schemas/route.py`
- `schemas/route_place.py`
- `schemas/sorting.py`
- `schemas/tag.py`
- `scripts/seed_minimal_data.py`
- `services/__init__.py`
- `services/ai_dictionaries.py`
- `services/ai_service.py`
- `services/category_service.py`
- `services/city_service.py`
- `services/collection_place_service.py`
- `services/collection_service.py`
- `services/nearby_service.py`
- `services/open_now_service.py`
- `services/pagination_service.py`
- `services/place_count_service.py`
- `services/place_detail_service.py`
- `services/place_filters_service.py`
- `services/place_list_params_service.py`
- `services/place_query_params_service.py`
- `services/place_search_params_service.py`
- `services/place_search_response_service.py`
- `services/place_search_service.py`
- `services/place_seed_bulk_validation_service.py`
- `services/place_seed_dry_run_service.py`
- `services/place_seed_import_summary_service.py`
- `services/place_seed_validation_service.py`
- `services/place_service.py`
- `services/place_sorting_service.py`
- `services/place_tag_service.py`
- `services/place_taxonomy_diagnostics_response_service.py`
- `services/place_taxonomy_diagnostics_service.py`
- `services/place_taxonomy_payload_service.py`
- `services/place_taxonomy_response_service.py`
- `services/place_taxonomy_service.py`
- `services/route_place_service.py`
- `services/route_service.py`
- `services/sorting_service.py`
- `services/tag_service.py`
- `telegram_bot/__init__.py`
- `telegram_bot/handlers/__init__.py`
- `telegram_bot/handlers/address.py`
- `telegram_bot/handlers/health.py`
- `telegram_bot/handlers/location.py`
- `telegram_bot/handlers/menu.py`
- `telegram_bot/handlers/start.py`
- `telegram_bot/keyboards/__init__.py`
- `telegram_bot/keyboards/main_menu.py`
- `telegram_bot/services/__init__.py`
- `telegram_bot/services/address_context.py`
- `telegram_bot/services/api_client.py`
- `telegram_bot/services/messages.py`
- `telegram_bot/services/user_context.py`
- `telegram_bot/states/__init__.py`
- `telegram_bot/states/address_state.py`
- `telegram_bot_main.py`
- `tests/test_pagination_service.py`
- `tests/test_place_count_service.py`
- `tests/test_place_filters_service.py`
- `tests/test_place_list_params_schema.py`
- `tests/test_place_list_params_service.py`
- `tests/test_place_query_params_service.py`
- `tests/test_place_search_params_service.py`
- `tests/test_place_search_response_schema.py`
- `tests/test_place_search_response_service.py`
- `tests/test_place_search_response_total.py`
- `tests/test_place_search_router.py`
- `tests/test_place_search_router_empty_result.py`
- `tests/test_place_search_router_filters.py`
- `tests/test_place_search_router_pagination.py`
- `tests/test_place_search_router_validation.py`
- `tests/test_place_search_service.py`
- `tests/test_place_search_service_city_slug.py`
- `tests/test_place_seed_bulk_validation_response_schema.py`
- `tests/test_place_seed_bulk_validation_response_totals.py`
- `tests/test_place_seed_bulk_validation_service.py`
- `tests/test_place_seed_dry_run_request_schema.py`
- `tests/test_place_seed_dry_run_router.py`
- `tests/test_place_seed_dry_run_router_all_invalid.py`
- `tests/test_place_seed_dry_run_router_all_valid.py`
- `tests/test_place_seed_dry_run_router_empty_list.py`
- `tests/test_place_seed_dry_run_service.py`
- `tests/test_place_seed_dry_run_service_empty_slug.py`
- `tests/test_place_seed_dry_run_service_error_count.py`
- `tests/test_place_seed_import_summary_schema.py`
- `tests/test_place_seed_import_summary_service.py`
- `tests/test_place_seed_item_schema.py`
- `tests/test_place_seed_validation_request_schema.py`
- `tests/test_place_seed_validation_response_schema.py`
- `tests/test_place_seed_validation_router.py`
- `tests/test_place_seed_validation_router_empty_list.py`
- `tests/test_place_seed_validation_router_invalid_payload.py`
- `tests/test_place_seed_validation_router_taxonomy_errors.py`
- `tests/test_place_seed_validation_service.py`
- `tests/test_place_service_pagination.py`
- `tests/test_place_service_total.py`
- `tests/test_place_service_total_independent_from_pagination.py`
- `tests/test_place_sorting_service.py`
- `tests/test_place_taxonomy_diagnostics_router.py`
- `tests/test_place_taxonomy_diagnostics_service.py`
- `tests/test_place_taxonomy_payload_schema.py`
- `tests/test_place_taxonomy_payload_service.py`
- `tests/test_place_taxonomy_response_schema.py`
- `tests/test_place_taxonomy_response_service.py`
- `tests/test_place_taxonomy_router.py`
- `tests/test_place_taxonomy_service.py`
- `tests/test_places_router_empty_result.py`
- `tests/test_places_router_filters.py`
- `tests/test_places_router_pagination.py`
- `tests/test_places_router_validation.py`
- `tests/test_sorting_service.py`

## File Contents

### `README.md`

```md
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

### `__init__.py`

```py

```

### `api/__init__.py`

```py

```

### `core/__init__.py`

```py

```

### `core/config.py`

```py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "City Guide API"
    app_env: str = "local"
    app_host: str = "127.0.0.1"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/city_guide"

    # Telegram Bot
    bot_token: str = ""

    # Backend URL for Telegram bot
    backend_base_url: str = "http://127.0.0.1:8000"

    # Telegram Bot defaults
    default_city_slug: str = "zelenogradsk"

    # Optional filters for coffee places
    coffee_category_id: int | None = None
    coffee_tag_id: int | None = None

    # Optional filters for food places
    food_category_id: int | None = None
    food_tag_id: int | None = None

    # Optional filters for walking places
    walks_category_id: int | None = None
    walks_tag_id: int | None = None

    # Optional filters for dog-friendly places
    dog_friendly_category_id: int | None = None
    dog_friendly_tag_id: int | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
```

### `core/place_taxonomy.py`

```py
"""
Каноничный словарь таксономии City GO.

Это source of truth для:
- seed-данных
- фильтров
- backend-валидации
- Telegram bot
- AI / recommendation layer
"""

PLACE_CATEGORIES = [
    "coffee",
    "food",
    "walk",
    "museum",
    "attraction",
    "beach",
    "park",
    "bar",
    "hotel",
    "service",
]

PLACE_TAGS = [
    "breakfast",
    "dessert",
    "local_food",
    "specialty_coffee",
    "pet_friendly",
    "kid_friendly",
    "romantic",
    "quiet",
    "budget",
    "premium",
    "panoramic",
    "historical",
    "photo_spot",
    "seasonal",
    "open_late",
    "indoor",
    "outdoor",
]

PLACE_SCENARIO_TAGS = [
    "coffee_now",
    "food_now",
    "walk_now",
    "with_dog",
    "with_kids",
    "date_place",
    "solo_time",
    "first_time_in_city",
    "rainy_day",
    "evening_plan",
    "weekend_plan",
]

PLACE_VIBE_TAGS = [
    "cozy",
    "calm",
    "lively",
    "authentic",
    "touristy",
    "local_favorite",
]

PLACE_RESTRICTION_TAGS = [
    "cash_only",
    "reservation_needed",
    "seasonal_only",
    "may_be_closed_offseason",
    "dog_outdoor_only",
]

USER_SIGNALS = [
    "view_place",
    "save_place",
    "like_place",
    "dislike_place",
    "open_route",
    "open_collection",
    "click_call",
    "click_website",
    "click_build_route",
    "use_nearby",
    "use_open_now",
    "use_coffee",
    "use_food",
    "use_walks",
    "use_with_dog",
]
```

### `db/__init__.py`

```py

```

### `db/base.py`

```py
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

### `db/dependencies.py`

```py
from collections.abc import Generator

from db.session import SessionLocal


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `db/session.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings

engine = create_engine(settings.database_url, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

### `docs/ai_prompts.md`

```md
# AI Prompts

## Системный промпт
Ты AI-слой городского гида.
Ты не должен выдумывать места, адреса, часы работы, маршруты и факты.
Ты работаешь только с данными, которые приходят из нашей базы через retrieval.
Твоя задача:
- понять запрос пользователя
- извлечь intent и ограничения
- выбрать подходящие данные
- сформировать короткий и понятный ответ
- объяснить, почему выбраны именно эти варианты

## Промпт извлечения intent
Извлеки из запроса пользователя:
- intent
- city_slug
- category_id
- tag_ids
- wants_nearby
- wants_open_now
- wants_route
- wants_collection
Верни только JSON.

## Промпт извлечения фильтров
Извлеки из запроса пользователя фильтры:
- city_slug
- category_id
- tag_ids
- lat
- lng
- radius_km
- open_now
- duration_minutes
Верни только JSON.

## Промпт выбора мест
Ты получил список мест из базы.
Нужно предложить пользователю 3–5 лучших вариантов.
Не выдумывай факты.
Для каждого варианта дай:
- название
- почему подходит
- что учитывать

## Промпт для nearby-ответа
Ты получил nearby-результаты.
Сделай короткий ответ:
- сначала самые близкие
- потом краткое объяснение
- без воды
- без выдумывания данных

## Промпт для open-now-ответа
Ты получил список мест, которые открыты сейчас.
Покажи:
- название
- адрес
- часы работы
- краткое пояснение

## Промпт для подбора подборки
Ты получил список подборок.
Подскажи пользователю, какая подборка подходит лучше всего.
Объясни выбор коротко и по делу.

## Промпт для подбора маршрута
Ты получил список маршрутов.
Выбери наиболее подходящий маршрут по запросу пользователя.
Объясни:
- почему он подходит
- сколько он займет времени
- для какого сценария он лучше всего

## Промпт для ответа по slug
Ты получил конкретный объект из базы по slug.
Сделай короткое описание:
- что это
- кому подходит
- чем полезно
Не добавляй ничего, чего нет в данных.

## Промпт для итогового ответа
Сформируй финальный ответ пользователю.
Требования:
- коротко
- понятно
- по делу
- без выдуманных фактов
- только на основе retrieval-данных
```

### `docs/ai_retrieval_plan.md`

```md
# AI Retrieval Plan

## Цель
Подготовить backend к AI-слою, который будет отвечать не из воздуха, а только на основе нашей базы данных.

## Принцип
AI не должен:
- придумывать места
- придумывать расписание
- придумывать адреса
- придумывать маршруты без опоры на данные

AI должен:
- понимать запрос пользователя
- извлекать параметры из запроса
- подбирать данные из базы
- формировать понятный ответ
- объяснять, почему предложены именно эти места

## Что уже есть в базе
Сейчас в backend уже есть сущности:
- cities
- categories
- tags
- places
- place_tags
- collections
- collection_places
- routes
- route_places
- place_schedules

Это уже достаточно, чтобы строить retrieval-first подход.

## Что нужно для AI retrieval

### 1. Подготовить retrieval endpoints
Нужны endpoint'ы или сервисы, которые AI сможет использовать как источники данных:
- получить места по фильтрам
- получить места по городу
- получить места по тегу
- получить nearby места
- получить места, открытые сейчас
- получить подборки
- получить маршруты

### 2. Подготовить нормализованные ответы
AI удобнее работать, если данные приходят в стабильном формате:
- id
- slug
- title
- city
- category
- tags
- short_description
- address
- schedule
- nearby distance
- route positions
- collection positions

### 3. Подготовить retrieval use cases
Ближайшие сценарии:
- куда пойти рядом
- что открыто сейчас
- что посмотреть впервые
- dog-friendly места
- quiet / romantic / scenic места
- подборка на вечер
- маршрут по городу

### 4. Подготовить prompt layer
Нужны промпты:
- системный
- для извлечения intent
- для извлечения фильтров
- для выбора мест
- для объяснения результатов
- для сборки маршрута
- для пересборки маршрута

## Минимальный roadmap

### Этап 1
Подготовить retrieval-ready сервисы по places.

### Этап 2
Подготовить retrieval-ready сервисы по collections и routes.

### Этап 3
Сделать unified search/retrieval layer.

### Этап 4
Подключить AI-модель как orchestration layer поверх retrieval.

## Что делать дальше
1. описать retrieval contract
2. описать AI prompts
3. описать unified response format
4. подготовить первый AI endpoint
```

### `docs/change_history.md`

```md
# CHANGE HISTORY

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
- Backend не изменялся.
- Изменения выполнялись маленькими безопасными шагами с обязательной проверкой:
  - `npm run test`
  - `npm run lint`
  - `npm run build`
```

### `docs/commenting_policy.md`

```md
# COMMENTING POLICY

## 1. Цель
Единый стандарт комментариев в проекте:
- не писать “шумные” комментарии,
- обязательно документировать неочевидную логику,
- сохранять читаемость и поддерживаемость кода.

## 2. Где комментарии обязательны

### 2.1 Backend (`*.py`)
- сложная бизнес-логика (ветвления, скоринг, эвристики, fallback-цепочки);
- работа со временем, таймзонами, open-now логикой;
- нетривиальные SQL/ORM выборки;
- места, где есть ограничения/допущения (например, временный hardcode);
- публичные сервисные функции и хендлеры — с кратким docstring.

### 2.2 Frontend (`*.ts`, `*.tsx`)
- неочевидная трансформация данных;
- нестандартное состояние/эффекты;
- сложная логика роутинга/guards;
- workaround и временные решения (с пометкой TODO и контекстом).

### 2.3 Миграции и скрипты
- причина миграции и влияние на данные;
- любые потенциально рискованные шаги (backfill, преобразования).

## 3. Где комментарии НЕ нужны
- очевидные присваивания и простые JSX-блоки;
- дублирование названия функции (“set loading to true”);
- описание “что” без объяснения “почему”.

## 4. Формат комментариев

### 4.1 Python
- Для публичных функций: короткий docstring (1–3 строки).
- Для блоков логики: `#` комментарии прямо перед блоком.

Пример:
```python
def rank_places(items: list[Place]) -> list[Place]:
    """Сортирует места по эвристическому скорингу для MVP."""
    # Учитываем близость и признаки сценария пользователя.
    ...
```

### 4.2 TypeScript/TSX
- Короткий `//` комментарий перед сложным фрагментом.

Пример:
```ts
// Фолбэк: если API недоступен, показываем empty state без падения страницы.
if (!response.ok) {
  return []
}
```

## 5. Правила для TODO/FIXME
- Использовать только с контекстом причины.
- Формат:
  - `TODO(scope): что сделать и почему`
  - `FIXME(scope): что сломано и риск`

Пример:
```ts
// TODO(ai-ranking): заменить heuristic score на адаптивный ranking после user-signals v1.
```

## 6. Историчность изменений
- Все существенные изменения фиксируются в `docs/change_history.md`.
- Запись должна содержать:
  - что изменено,
  - зачем изменено,
  - какие риски/ограничения остались.

## 7. Минимальный чек перед merge
- Комментарии добавлены только там, где логика неочевидна.
- Нет устаревших комментариев, противоречащих коду.
- Для новых модулей есть базовая документация поведения.
```

### `docs/master_technical_spec.md`

```md
# MASTER TECHNICAL SPEC

## 1. Document purpose
Этот документ — основное ТЗ проекта.
Он фиксирует:
- цель продукта
- состав функционала
- бизнес-логику
- структуру данных
- API-контракты
- AI-логику
- UI-модули
- статусы реализации
- дальнейшие шаги

Документ должен обновляться после реализации каждой значимой фичи.

---

## 2. Product overview

### 2.1. Working title
City Guide / Зеленоградск Guide

### 2.2. Product goal
Сделать recommendation-driven city/travel platform, которая начинается как городской гид по Зеленоградску и масштабируется в персонализированный travel assistant.

Ближайшая цель (MVP):
- быстрый подбор мест
- nearby-сценарии
- open-now сценарии
- подборки
- маршруты
- AI-поиск и AI-подсказки только на основе собственной БД

Стратегическая цель (future direction):
- персонализированные рекомендации внутри города
- social/community слой поверх city guide
- рекомендации «куда поехать дальше» (next destination) на уровне других городов/стран

### 2.3. Product format
Продукт состоит из:
- backend API
- PostgreSQL database
- AI retrieval layer
- UI frontend
- recommendation layer (planned)
- user memory/profile layer (planned)
- social/community layer (planned)

### 2.4. Key principle
AI не имеет права выдумывать места, адреса, расписания, маршруты или факты.
Все ответы строятся только на данных из БД и retrieval-логике.

---

## 3. Users and usage scenarios

### 3.1. Main user
Турист или житель города, который хочет быстро понять:
- куда сходить
- что рядом
- что открыто
- где погулять
- куда пойти с собакой
- куда пойти на свидание
- что посмотреть впервые
- какой маршрут выбрать
- что подойдет именно ему по интересам и бюджету
- куда поехать после текущего города

### 3.2. Main scenarios
1. Пользователь открывает список мест
2. Пользователь фильтрует места
3. Пользователь ищет места рядом с собой
4. Пользователь ищет, что открыто сейчас
5. Пользователь смотрит подборки
6. Пользователь смотрит маршруты
7. Пользователь задает текстовый AI-запрос
8. Пользователь открывает карточку конкретного места
9. Пользователь получает персональные рекомендации по местам/маршрутам/подборкам
10. Пользователь в будущем получает next destination recommendation

---

## 4. Scope of MVP

### 4.1. Included in MVP
- cities
- categories
- tags
- places
- place detail
- nearby
- open now
- collections
- routes
- AI query
- UI MVP

### 4.2. Not included in current MVP
- отзывы пользователей
- рейтинги пользователей
- бронирование
- избранное / аккаунты
- мультиязычность
- push / notifications
- полноценный LLM orchestration layer
- semantic vector search
- social/community functionality
- gamification
- user profile and account area
- personalized recommendation engine
- travel planning across cities/countries

### 4.3. Future directions (architecture-level, no implementation yet)
1. Social / community layer:
- публичные профили пользователей
- пользовательские подборки
- пользовательские маршруты
- social recommendations
- follow / subscriptions
- community layer поверх city guide

2. Gamification module:
- прогресс пользователя
- коллекции / серии мест
- бейджи
- миссии
- архетип пользователя
- trust/confidence model для действий пользователя
- anti-fraud / anomaly flags / cooldown / weighted signals
- разделение user memory и game progress

3. Personalized travel planning:
- рекомендации мест/маршрутов/сценариев в городе по интересам и бюджету
- рекомендации других городов и стран (future)
- next destination recommendation

---

## 5. Functional modules

## 5.1. Cities module
### Goal
Хранить список городов и масштабировать продукт на несколько городов.

### Current status
DONE

### Functional requirements
- хранить slug города
- хранить название, регион, страну
- хранить timezone
- хранить координаты центра
- уметь получать город по id
- уметь получать город по slug
- уметь получать список городов

### Implemented endpoints
- GET /cities/
- GET /cities/{city_id}
- GET /cities/by-slug/{slug}

---

## 5.2. Categories module
### Goal
Хранить справочник категорий мест.

### Current status
DONE

### Functional requirements
- хранить code и name категории
- уметь получать категорию по id
- уметь получать категорию по code
- уметь получать список категорий

### Implemented endpoints
- GET /categories/
- GET /categories/{category_id}
- GET /categories/by-code/{code}

---

## 5.3. Tags module
### Goal
Хранить сценарные теги мест.

### Current status
DONE

### Functional requirements
- хранить tag code и name
- поддерживать dog-friendly / quiet / romantic и др.
- уметь получать тег по id
- уметь получать тег по code
- уметь получать список тегов

### Implemented endpoints
- GET /tags/
- GET /tags/{tag_id}
- GET /tags/by-code/{code}

---

## 5.4. Places module
### Goal
Хранить основные точки города.

### Current status
DONE

### Functional requirements
- хранить city_id
- хранить category_id
- хранить slug
- хранить title
- хранить short_description
- хранить address
- хранить lat/lng
- хранить price_level
- хранить dog_friendly / family_friendly
- хранить indoor / outdoor
- хранить is_active

### Implemented endpoints
- GET /places/
- GET /places/{place_id}
- GET /places/by-slug/{slug}
- POST /places/
- PUT /places/{place_id}
- DELETE /places/{place_id}

### Filtering requirements
Нужно поддерживать:
- city_id
- city_slug
- category_id
- tag_id
- комбинированные фильтры

### Current status of filtering
DONE

---

## 5.5. Place tags relation
### Goal
Связать места и теги many-to-many.

### Current status
DONE

### Implemented endpoints
- GET /place-tags/
- GET /place-tags/?place_id=...

---

## 5.6. Place schedules / open now
### Goal
Показывать, открыто ли место сейчас.

### Current status
DONE

### Functional requirements
- хранить weekday
- хранить open_time
- хранить close_time
- хранить is_closed
- учитывать timezone города
- выдавать список открытых мест

### Implemented endpoint
- GET /open-now/?city_slug=...

### Logic
- берем timezone города
- вычисляем текущую дату/время
- определяем weekday
- сравниваем с place_schedules

---

## 5.7. Nearby module
### Goal
Искать места рядом с координатой пользователя.

### Current status
DONE

### Functional requirements
- принимать lat/lng
- принимать radius_km
- считать расстояние
- сортировать по расстоянию

### Implemented endpoint
- GET /nearby/?lat=...&lng=...&radius_km=...

### Logic
- используется haversine
- результат сортируется по distance_km asc

---

## 5.8. Collections module
### Goal
Показывать тематические подборки мест.

### Current status
DONE

### Functional requirements
- хранить подборку
- хранить city_id
- хранить slug/title/description
- хранить список мест в подборке

### Implemented endpoints
- GET /collections/
- GET /collections/{collection_id}
- GET /collections/by-slug/{slug}
- GET /collection-places/
- GET /collection-places/?collection_id=...

---

## 5.9. Routes module
### Goal
Показывать готовые маршруты по городу.

### Current status
DONE

### Functional requirements
- хранить маршрут
- хранить city_id
- хранить slug/title/description
- хранить duration_minutes
- хранить порядок точек маршрута

### Implemented endpoints
- GET /routes/
- GET /routes/{route_id}
- GET /routes/by-slug/{slug}
- GET /route-places/
- GET /route-places/?route_id=...

---

## 5.10. AI query module
### Goal
Принимать текстовый запрос и отдавать ответ на основе retrieval.

### Current status
DONE (MVP)

### Implemented endpoints
- GET /ai/health
- POST /ai/query

### Current AI scenarios
- nearby
- open_now
- routes
- collections
- places_filtered
- place_detail

### Current input
POST /ai/query принимает:
- query
- lat (optional)
- lng (optional)

### Current logic
- rule-based intent detection
- rule-based city/category/tag detection
- retrieval through backend services
- filtered/ranked response for places_filtered
- detail retrieval by place slug

### Current limitations
- intent parsing still heuristic
- city detection not scalable enough
- place slug extraction is primitive
- scoring is simple and non-ML
- no semantic search

### Positioning in architecture
Текущая AI-часть — это retrieval/orchestration MVP:
- intent detection
- constraints extraction
- backend retrieval
- heuristic ranking

Целевой AI-контур (future):
- AI + user memory + recommendation engine + adaptive ranking
- explainable recommendations
- travel planning support
- next best actions and next destination

---

## 5.11. Social / community layer (future)
### Current status
PLANNED (not implemented)

### Scope
- public user profiles
- user-created collections
- user-created routes
- follow/subscriptions
- social recommendations

### Notes
- модуль проектируется как надстройка над текущими places/routes/collections
- внедрение без ломки текущего MVP API

---

## 5.12. Gamification module (future)
### Current status
PLANNED (not implemented)

### Scope
- user progress and missions
- badges and place-series collections
- user archetype
- trust/confidence scoring
- anti-fraud flags (anomaly, cooldown, weighted signals)
- explicit split: user memory vs game progress

### Notes
- геймификация не входит в ближайшие релизы
- в модель закладываются точки расширения, но без активации в MVP

---

## 5.13. Personalized travel planning and next destination (future)
### Current status
PLANNED (not implemented)

### Planned entities
- destinations
- destination_profiles
- destination_tags
- destination_budgets
- destination_trip_scenarios

### Planned recommendation factors
- user taste profile
- behavioral profile
- budget
- duration
- season
- solo/couple/family/dog
- trip style

### Planned outputs
- ranked places
- ranked routes
- ranked collections
- scenario recommendations
- similar cities
- next destination

---

## 6. Seed data

### Goal
Наполнить Зеленоградск рабочими местами для тестирования backend, AI и UI.

### Current status
DONE for MVP

### Current state
- в БД залит рабочий seed по Зеленоградску
- данных достаточно для MVP-тестов
- база уже пригодна для проверки фильтров, nearby, open-now, routes, collections, AI

---

## 7. Data model

### Main entities
- cities
- categories
- tags
- places
- place_tags
- place_schedules
- collections
- collection_places
- routes
- route_places

### Domain coverage requirements (must be preserved and expanded)
- гастрономия
- прогулочные точки
- музеи
- исторические здания
- муралы с котиками
- Куршская коса
- сервисные точки
- локальные сценарии

### Future entities (planned, not implemented)
- users
- user_profiles
- user_memory_events
- user_preferences
- user_follows
- user_collections
- user_routes
- recommendation_impressions
- recommendation_feedback
- destinations
- destination_profiles
- destination_tags
- destination_budgets
- destination_trip_scenarios

### Data freshness and confidence model (planned)
Каждая запись, где применимо, должна поддерживать:
- source
- last_verified_at
- confidence
- freshness
- tier_priority
- verification_status

Типы данных по изменчивости:
- почти статичные
- средне-изменчивые
- сильно изменчивые / субъективные

Confidence levels:
- high_confidence
- medium_confidence
- low_confidence

Verification statuses:
- draft
- imported
- normalized
- reviewed
- verified
- needs_recheck
- seasonal
- archived

Tier priority:
- Tier 1
- Tier 2
- Tier 3

### ORM status
- базовые ORM relationships уже добавлены
- модель пригодна для дальнейшего UI и retrieval

---

## 8. API status

### Current API state
Backend MVP is operational.

### What is already stable
- cities
- categories
- tags
- places
- place detail
- nearby
- open now
- collections
- routes
- AI query

### What still needs refinement
- better response contract for UI
- cleaner AI ranking
- less hardcoded AI parsing
- optional response normalization for frontend widgets
- user-signal collection endpoints
- recommendation endpoints (places/routes/collections)
- explainability fields in recommendation responses
- freshness/confidence metadata in API responses where relevant

---

## 9. UI architecture and product surfaces

### Current status
PARTIAL (only Home-like MVP screen implemented)

### Goal
Собрать масштабируемый UI, который работает на текущем backend и может вырасти в recommendation-driven platform.

### Required UI surfaces
- Home screen
- Cities / active city
- Places list
- Place detail page
- Nearby block
- Open now block
- Collections block
- Routes block
- AI query form
- AI results rendering
- Collections list
- Collection detail
- Routes list
- Route detail
- Login/Register
- User Profile / Personal Account

### Page transitions and relations (target)
- Home -> Places List -> Place Detail
- Home -> Nearby / Open Now -> Place Detail
- Home -> Collections -> Collection Detail -> Place Detail
- Home -> Routes -> Route Detail -> Place Detail
- Home -> AI Search -> mixed results (places/routes/collections) -> detail pages
- Auth (Login/Register) -> User Profile / Personal Account
- User Profile -> personal recommendations/history/favorites/visits

### Personalization logic in UI (target)
- отображать рекомендации на основе интересов, истории просмотров, лайков/дизлайков, посещений, завершенных маршрутов
- отображать explainability: почему рекомендовано именно это
- честно показывать неполную уверенность в данных (freshness/confidence badges)

---

## 10. AI and recommendation model

### 10.1. Current AI state (implemented)
- retrieval / orchestration layer
- intent detection
- constraints extraction
- backend retrieval
- heuristic ranking

### 10.2. User signals (planned)
- viewed places
- favorites
- liked/disliked
- visits
- completed routes
- category preferences
- tag preferences

### 10.3. Derived user profile (planned)
- category scores
- tag scores
- scenario affinity
- budget preference
- trip style

### 10.4. Recommendation outputs (planned)
- ranked places
- ranked routes
- ranked collections
- next best actions
- next destination

### 10.5. Explainability (planned)
- рекомендация должна сопровождаться объяснением причин выбора
- UI должен уметь отображать explanation payload

---

## 11. Gap analysis (codebase vs master spec)

### Implemented
- backend CRUD/read APIs for cities/categories/tags/places
- open-now and nearby logic
- collections/routes and relation modules
- AI query MVP (rule-based retrieval orchestration)
- seed data for MVP checks
- basic frontend single-page MVP view with places loading

### Partially implemented
- UI layer: только один экран без page-level architecture
- AI ranking and intent parsing: работает, но остается эвристическим
- API contracts for frontend: стабильны для MVP, но без recommendation/explainability contracts

### Missing
- полноценная UI-архитектура (pages/components/api/types separation)
- auth + personal account
- user memory/signals storage
- recommendation engine and adaptive ranking
- social/community module
- gamification module
- travel planning + next destination module
- freshness/confidence/verification flow in data lifecycle and UI

---

## 12. Current stage
Сейчас проект находится на стадии:

backend MVP DONE  
AI retrieval MVP DONE  
seed data MVP DONE  
frontend UI foundation IN PROGRESS  
next major step = structured UI foundation (Phase 1)

---

## 13. Change log rule
После реализации каждой новой фичи нужно:
1. обновить статус раздела
2. дописать implemented logic
3. зафиксировать ограничения
4. зафиксировать следующий шаг

---

## 14. Phased implementation plan

### Phase 1 (safe foundation, now)
Цель: навести базовую структуру frontend без смены поведения MVP.
- разделить UI на pages/components/widgets
- вынести API-клиент и env-конфиг
- централизовать types
- добавить базовые smoke/unit тесты для критичного UI-потока
- сохранить текущий UX и текущий backend contract

### Phase 2 (product-ready city guide)
Цель: закрыть core UI surfaces и подготовить персонализацию.
- pages: Places List/Detail, Collections/List+Detail, Routes/List+Detail, Nearby, Open Now, AI Search
- добавить Login/Register и каркас Personal Account
- внедрить user signals collection (view/favorite/like/visit/completed route)
- расширить API-контракты для explainability/freshness badges

### Phase 3 (recommendation-driven expansion)
Цель: выйти за рамки каталога в сторону рекомендационной платформы.
- recommendation engine (ranked places/routes/collections + next best actions)
- user taste/behavior profile derivation
- social/community layer (profiles, follows, user routes/collections)
- travel planning and next destination
- подготовка gamification module activation path

## 15. Immediate next step
Запустить Phase 1: структурирование frontend + API layer extraction + базовые тесты без регрессий.
```

### `docs/project_status.md`

```md
# Project Status

## Текущий статус
Проект находится на стадии формирования backend foundation.

## Что уже сделано

### Инфраструктура
- поднят проект на FastAPI
- настроен запуск через Uvicorn
- подключен PostgreSQL
- подключен Alembic
- вынесен конфиг в `core/config.py`

### Города
Реализованы:
- `GET /cities/`
- `GET /cities/{city_id}`
- `GET /cities/by-slug/{slug}`

### Категории
Реализованы:
- `GET /categories/`
- `GET /categories/{category_id}`
- `GET /categories/by-code/{code}`

### Теги
Реализованы:
- `GET /tags/`
- `GET /tags/{tag_id}`
- `GET /tags/by-code/{code}`

### Места
Реализованы:
- `GET /places/`
- `GET /places/{place_id}`
- `GET /places/by-slug/{slug}`
- `POST /places/`
- `PUT /places/{place_id}`
- `DELETE /places/{place_id}`

### Фильтрация мест
Поддерживается фильтрация:
- по `city_id`
- по `city_slug`
- по `category_id`
- по `tag_id`
- комбинированная фильтрация

### Связи мест и тегов
Реализованы:
- `GET /place-tags/`
- фильтр `GET /place-tags/?place_id=...`

### Подборки
Реализованы:
- `GET /collections/`
- `GET /collections/{collection_id}`
- `GET /collections/by-slug/{slug}`

### Связи подборок и мест
Реализованы:
- `GET /collection-places/`
- фильтр `GET /collection-places/?collection_id=...`

### Маршруты
Реализованы:
- `GET /routes/`
- `GET /routes/{route_id}`
- `GET /routes/by-slug/{slug}`

### Связи маршрутов и мест
Реализованы:
- `GET /route-places/`
- фильтр `GET /route-places/?route_id=...`

### Nearby search
Реализован:
- `GET /nearby/?lat=...&lng=...&radius_km=...`

### Open now
Реализован:
- `GET /open-now/?city_slug=...`

### AI query
Реализованы:
- `GET /ai/health`
- `POST /ai/query`

Текущие AI-сценарии:
- nearby
- open_now
- routes
- collections
- places_filtered
- place_detail

Что уже умеет AI:
- принимать текстовый запрос
- определять базовый intent
- определять `city_slug` из текста запроса
- принимать координаты пользователя
- ходить в retrieval-слой backend
- возвращать nearby-результаты
- возвращать места, открытые сейчас
- возвращать маршруты по городу
- возвращать подборки по городу
- возвращать места по категории и/или тегу
- возвращать детальную информацию о месте по slug

## Текущая структура
- `cities`
- `categories`
- `tags`
- `places`
- `place_tags`
- `collections`
- `collection_places`
- `routes`
- `route_places`
- `place_schedules`

## Что делать дальше
1. улучшить AI intent parsing
2. добавить AI retrieval по category/tag без хардкод-словарей
3. добавить нормальные связи ORM между сущностями
4. позже убрать legacy-поле `category` после полного перехода на `category_id`

## Важно
- backend пишется на Python
- используется FastAPI
- база данных PostgreSQL
- миграции через Alembic
- код пишется с комментариями
- архитектура строится под масштабирование на другие города
- AI должен работать только поверх данных из нашей базы
```

### `docs/technical_spec.md`

```md
# Техническое задание

## 1. Общая цель проекта
Разработать backend и далее UI для городского гида в стиле Tripadvisor, но с упором не на длинный каталог отзывов, а на:
- быстрый подбор мест
- nearby-сценарии
- что открыто сейчас
- подборки
- маршруты
- AI-слой поверх собственной базы

Пилотный город:
- Зеленоградск

---

## 2. Текущий стек
- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Uvicorn

---

## 3. Что уже реализовано в backend

### 3.1. Базовая инфраструктура
Реализовано:
- запуск FastAPI
- конфиг через `core/config.py`
- подключение PostgreSQL
- миграции через Alembic
- базовая структура проекта

### 3.2. Сущности
В проекте уже реализованы сущности:
- cities
- categories
- tags
- places
- place_tags
- collections
- collection_places
- routes
- route_places
- place_schedules

### 3.3. Города
Реализованы endpoint’ы:
- `GET /cities/`
- `GET /cities/{city_id}`
- `GET /cities/by-slug/{slug}`

### 3.4. Категории
Реализованы endpoint’ы:
- `GET /categories/`
- `GET /categories/{category_id}`
- `GET /categories/by-code/{code}`

### 3.5. Теги
Реализованы endpoint’ы:
- `GET /tags/`
- `GET /tags/{tag_id}`
- `GET /tags/by-code/{code}`

### 3.6. Места
Реализованы endpoint’ы:
- `GET /places/`
- `GET /places/{place_id}`
- `GET /places/by-slug/{slug}`
- `POST /places/`
- `PUT /places/{place_id}`
- `DELETE /places/{place_id}`

### 3.7. Фильтрация мест
Поддерживается фильтрация:
- по `city_id`
- по `city_slug`
- по `category_id`
- по `tag_id`
- комбинированная фильтрация

Примеры:
- `/places/?city_slug=zelenogradsk`
- `/places/?category_id=1`
- `/places/?tag_id=1`
- `/places/?city_slug=zelenogradsk&category_id=1&tag_id=1`

### 3.8. Связи мест и тегов
Реализованы endpoint’ы:
- `GET /place-tags/`
- `GET /place-tags/?place_id=...`

### 3.9. Подборки
Реализованы endpoint’ы:
- `GET /collections/`
- `GET /collections/{collection_id}`
- `GET /collections/by-slug/{slug}`

### 3.10. Связи подборок и мест
Реализованы endpoint’ы:
- `GET /collection-places/`
- `GET /collection-places/?collection_id=...`

### 3.11. Маршруты
Реализованы endpoint’ы:
- `GET /routes/`
- `GET /routes/{route_id}`
- `GET /routes/by-slug/{slug}`

### 3.12. Связи маршрутов и мест
Реализованы endpoint’ы:
- `GET /route-places/`
- `GET /route-places/?route_id=...`

### 3.13. Nearby search
Реализован endpoint:
- `GET /nearby/?lat=...&lng=...&radius_km=...`

Логика:
- принимает координаты
- считает расстояние через haversine
- возвращает ближайшие места
- сортирует результат по расстоянию

### 3.14. Open now
Реализован endpoint:
- `GET /open-now/?city_slug=...`

Логика:
- использует timezone города
- использует день недели
- использует таблицу `place_schedules`
- возвращает места, открытые сейчас

---

## 4. AI-слой

### 4.1. Реализованные endpoint’ы
- `GET /ai/health`
- `POST /ai/query`

### 4.2. Что уже умеет AI
AI уже умеет:
- принимать текстовый запрос
- определять базовый intent
- определять `city_slug`
- принимать координаты пользователя
- работать только поверх retrieval-слоя backend

### 4.3. Реализованные AI-сценарии
Сейчас реализованы сценарии:
- `nearby`
- `open_now`
- `routes`
- `collections`
- `places_filtered`
- `place_detail`

### 4.4. Что уже возвращает AI
AI уже умеет возвращать:
- nearby-результаты
- места, открытые сейчас
- маршруты по городу
- подборки по городу
- места по категории и/или тегу
- детальную информацию о месте по slug

### 4.5. Ограничения текущего AI
Пока AI работает на rule-based логике:
- словари интентов
- словари категорий
- словари тегов
- словари городов

Пока не реализовано:
- полноценный intent parser
- семантический поиск
- LLM orchestration
- нормализованный retrieval contract для всех сценариев

---

## 5. Что уже сделано архитектурно
- проект готов к масштабированию на другие города
- есть slug-модель для городов, мест, маршрутов и подборок
- есть нормализованные сущности и связи
- есть ORM relationships
- backend уже можно использовать как основу для UI

---

## 6. Текущий этап проекта
Текущий этап:
- backend foundation завершен на хорошем рабочем уровне
- базовый AI retrieval уже реализован
- проект готов к переходу в UI phase

---

## 7. Что нужно сделать дальше

### 7.1. По backend
Нужно доделать:
1. улучшить AI intent parsing
2. убрать/ослабить хардкод-словари
3. улучшить retrieval по places
4. подготовить более стабильный response contract для UI
5. позже убрать legacy-поле `category` после полного перехода на `category_id`

### 7.2. По UI
Следующий большой этап:
- начать frontend/UI

План первого UI:
1. выбрать стек frontend
2. сделать базовую главную страницу
3. сделать список мест
4. сделать карточку места
5. сделать nearby-блок
6. сделать open-now-блок
7. сделать подборки
8. сделать маршруты
9. сделать экран/блок для AI-запроса

---

## 8. Что должен уметь первый UI
Первый UI должен уметь:
- показать города
- показать places list
- открыть place detail
- показать nearby results
- показать open-now results
- показать collections
- показать routes
- отправить запрос в `POST /ai/query`
- отрисовать AI results

---

## 9. Приоритеты следующего этапа
Приоритет такой:
1. начать UI
2. параллельно слегка дочищать AI intent parsing
3. не раздувать backend новыми сущностями без нужды
4. сначала получить живой интерфейс, потом уже улучшать детали

---

## 10. Важно
- код должен оставаться с комментариями
- AI не должен выдумывать данные
- AI работает только поверх нашей базы
- архитектура должна оставаться пригодной для масштабирования
- UI не нужно откладывать до “идеального backend”

```

### `frontend/README.md`

```md
# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
```

### `frontend/package-lock.json`

```json
{
  "name": "frontend",
  "version": "0.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "frontend",
      "version": "0.0.0",
      "dependencies": {
        "lucide-react": "^1.0.1",
        "react": "^19.2.4",
        "react-dom": "^19.2.4",
        "react-router-dom": "^7.9.6"
      },
      "devDependencies": {
        "@eslint/js": "^9.39.4",
        "@testing-library/jest-dom": "^6.9.1",
        "@testing-library/react": "^16.3.0",
        "@types/node": "^24.12.0",
        "@types/react": "^19.2.14",
        "@types/react-dom": "^19.2.3",
        "@vitejs/plugin-react": "^6.0.1",
        "eslint": "^9.39.4",
        "eslint-plugin-react-hooks": "^7.0.1",
        "eslint-plugin-react-refresh": "^0.5.2",
        "globals": "^17.4.0",
        "jsdom": "^27.0.1",
        "typescript": "~5.9.3",
        "typescript-eslint": "^8.57.0",
        "vite": "^8.0.1",
        "vitest": "^4.0.0"
      }
    },
    "node_modules/@acemir/cssom": {
      "version": "0.9.31",
      "resolved": "https://registry.npmjs.org/@acemir/cssom/-/cssom-0.9.31.tgz",
      "integrity": "sha512-ZnR3GSaH+/vJ0YlHau21FjfLYjMpYVIzTD8M8vIEQvIGxeOXyXdzCI140rrCY862p/C/BbzWsjc1dgnM9mkoTA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@adobe/css-tools": {
      "version": "4.4.4",
      "resolved": "https://registry.npmjs.org/@adobe/css-tools/-/css-tools-4.4.4.tgz",
      "integrity": "sha512-Elp+iwUx5rN5+Y8xLt5/GRoG20WGoDCQ/1Fb+1LiGtvwbDavuSk0jhD/eZdckHAuzcDzccnkv+rEjyWfRx18gg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@asamuzakjp/css-color": {
      "version": "4.1.2",
      "resolved": "https://registry.npmjs.org/@asamuzakjp/css-color/-/css-color-4.1.2.tgz",
      "integrity": "sha512-NfBUvBaYgKIuq6E/RBLY1m0IohzNHAYyaJGuTK79Z23uNwmz2jl1mPsC5ZxCCxylinKhT1Amn5oNTlx1wN8cQg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@csstools/css-calc": "^3.0.0",
        "@csstools/css-color-parser": "^4.0.1",
        "@csstools/css-parser-algorithms": "^4.0.0",
        "@csstools/css-tokenizer": "^4.0.0",
        "lru-cache": "^11.2.5"
      }
    },
    "node_modules/@asamuzakjp/css-color/node_modules/lru-cache": {
      "version": "11.2.7",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-11.2.7.tgz",
      "integrity": "sha512-aY/R+aEsRelme17KGQa/1ZSIpLpNYYrhcrepKTZgE+W3WM16YMCaPwOHLHsmopZHELU0Ojin1lPVxKR0MihncA==",
      "dev": true,
      "license": "BlueOak-1.0.0",
      "engines": {
        "node": "20 || >=22"
      }
    },
    "node_modules/@asamuzakjp/dom-selector": {
      "version": "6.8.1",
      "resolved": "https://registry.npmjs.org/@asamuzakjp/dom-selector/-/dom-selector-6.8.1.tgz",
      "integrity": "sha512-MvRz1nCqW0fsy8Qz4dnLIvhOlMzqDVBabZx6lH+YywFDdjXhMY37SmpV1XFX3JzG5GWHn63j6HX6QPr3lZXHvQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@asamuzakjp/nwsapi": "^2.3.9",
        "bidi-js": "^1.0.3",
        "css-tree": "^3.1.0",
        "is-potential-custom-element-name": "^1.0.1",
        "lru-cache": "^11.2.6"
      }
    },
    "node_modules/@asamuzakjp/dom-selector/node_modules/lru-cache": {
      "version": "11.2.7",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-11.2.7.tgz",
      "integrity": "sha512-aY/R+aEsRelme17KGQa/1ZSIpLpNYYrhcrepKTZgE+W3WM16YMCaPwOHLHsmopZHELU0Ojin1lPVxKR0MihncA==",
      "dev": true,
      "license": "BlueOak-1.0.0",
      "engines": {
        "node": "20 || >=22"
      }
    },
    "node_modules/@asamuzakjp/nwsapi": {
      "version": "2.3.9",
      "resolved": "https://registry.npmjs.org/@asamuzakjp/nwsapi/-/nwsapi-2.3.9.tgz",
      "integrity": "sha512-n8GuYSrI9bF7FFZ/SjhwevlHc8xaVlb/7HmHelnc/PZXBD2ZR49NnN9sMMuDdEGPeeRQ5d0hqlSlEpgCX3Wl0Q==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@babel/code-frame": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/code-frame/-/code-frame-7.29.0.tgz",
      "integrity": "sha512-9NhCeYjq9+3uxgdtp20LSiJXJvN0FeCtNGpJxuMFZ1Kv3cWUNb6DOhJwUvcVCzKGR66cw4njwM6hrJLqgOwbcw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-validator-identifier": "^7.28.5",
        "js-tokens": "^4.0.0",
        "picocolors": "^1.1.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/compat-data": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/compat-data/-/compat-data-7.29.0.tgz",
      "integrity": "sha512-T1NCJqT/j9+cn8fvkt7jtwbLBfLC/1y1c7NtCeXFRgzGTsafi68MRv8yzkYSapBnFA6L3U2VSc02ciDzoAJhJg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/core": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/core/-/core-7.29.0.tgz",
      "integrity": "sha512-CGOfOJqWjg2qW/Mb6zNsDm+u5vFQ8DxXfbM09z69p5Z6+mE1ikP2jUXw+j42Pf1XTYED2Rni5f95npYeuwMDQA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-compilation-targets": "^7.28.6",
        "@babel/helper-module-transforms": "^7.28.6",
        "@babel/helpers": "^7.28.6",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/traverse": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/remapping": "^2.3.5",
        "convert-source-map": "^2.0.0",
        "debug": "^4.1.0",
        "gensync": "^1.0.0-beta.2",
        "json5": "^2.2.3",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/babel"
      }
    },
    "node_modules/@babel/generator": {
      "version": "7.29.1",
      "resolved": "https://registry.npmjs.org/@babel/generator/-/generator-7.29.1.tgz",
      "integrity": "sha512-qsaF+9Qcm2Qv8SRIMMscAvG4O3lJ0F1GuMo5HR/Bp02LopNgnZBC/EkbevHFeGs4ls/oPz9v+Bsmzbkbe+0dUw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/parser": "^7.29.0",
        "@babel/types": "^7.29.0",
        "@jridgewell/gen-mapping": "^0.3.12",
        "@jridgewell/trace-mapping": "^0.3.28",
        "jsesc": "^3.0.2"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-compilation-targets": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-compilation-targets/-/helper-compilation-targets-7.28.6.tgz",
      "integrity": "sha512-JYtls3hqi15fcx5GaSNL7SCTJ2MNmjrkHXg4FSpOA/grxK8KwyZ5bubHsCq8FXCkua6xhuaaBit+3b7+VZRfcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/compat-data": "^7.28.6",
        "@babel/helper-validator-option": "^7.27.1",
        "browserslist": "^4.24.0",
        "lru-cache": "^5.1.1",
        "semver": "^6.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-globals": {
      "version": "7.28.0",
      "resolved": "https://registry.npmjs.org/@babel/helper-globals/-/helper-globals-7.28.0.tgz",
      "integrity": "sha512-+W6cISkXFa1jXsDEdYA8HeevQT/FULhxzR99pxphltZcVaugps53THCeiWA8SguxxpSp3gKPiuYfSWopkLQ4hw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-imports": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-imports/-/helper-module-imports-7.28.6.tgz",
      "integrity": "sha512-l5XkZK7r7wa9LucGw9LwZyyCUscb4x37JWTPz7swwFE/0FMQAGpiWUZn8u9DzkSBWEcK25jmvubfpw2dnAMdbw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/traverse": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-module-transforms": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/helper-module-transforms/-/helper-module-transforms-7.28.6.tgz",
      "integrity": "sha512-67oXFAYr2cDLDVGLXTEABjdBJZ6drElUSI7WKp70NrpyISso3plG9SAGEF6y7zbha/wOzUByWWTJvEDVNIUGcA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-module-imports": "^7.28.6",
        "@babel/helper-validator-identifier": "^7.28.5",
        "@babel/traverse": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      },
      "peerDependencies": {
        "@babel/core": "^7.0.0"
      }
    },
    "node_modules/@babel/helper-string-parser": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-string-parser/-/helper-string-parser-7.27.1.tgz",
      "integrity": "sha512-qMlSxKbpRlAridDExk92nSobyDdpPijUq2DW6oDnUqd0iOGxmQjyqhMIihI9+zv4LPyZdRje2cavWPbCbWm3eA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-identifier": {
      "version": "7.28.5",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-identifier/-/helper-validator-identifier-7.28.5.tgz",
      "integrity": "sha512-qSs4ifwzKJSV39ucNjsvc6WVHs6b7S03sOh2OcHF9UHfVPqWWALUsNUVzhSBiItjRZoLHx7nIarVjqKVusUZ1Q==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helper-validator-option": {
      "version": "7.27.1",
      "resolved": "https://registry.npmjs.org/@babel/helper-validator-option/-/helper-validator-option-7.27.1.tgz",
      "integrity": "sha512-YvjJow9FxbhFFKDSuFnVCe2WxXk1zWc22fFePVNEaWJEu8IrZVlda6N0uHwzZrUM1il7NC9Mlp4MaJYbYd9JSg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/helpers": {
      "version": "7.29.2",
      "resolved": "https://registry.npmjs.org/@babel/helpers/-/helpers-7.29.2.tgz",
      "integrity": "sha512-HoGuUs4sCZNezVEKdVcwqmZN8GoHirLUcLaYVNBK2J0DadGtdcqgr3BCbvH8+XUo4NGjNl3VOtSjEKNzqfFgKw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.29.0"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/parser": {
      "version": "7.29.2",
      "resolved": "https://registry.npmjs.org/@babel/parser/-/parser-7.29.2.tgz",
      "integrity": "sha512-4GgRzy/+fsBa72/RZVJmGKPmZu9Byn8o4MoLpmNe1m8ZfYnz5emHLQz3U4gLud6Zwl0RZIcgiLD7Uq7ySFuDLA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/types": "^7.29.0"
      },
      "bin": {
        "parser": "bin/babel-parser.js"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@babel/runtime": {
      "version": "7.29.2",
      "resolved": "https://registry.npmjs.org/@babel/runtime/-/runtime-7.29.2.tgz",
      "integrity": "sha512-JiDShH45zKHWyGe4ZNVRrCjBz8Nh9TMmZG1kh4QTK8hCBTWBi8Da+i7s1fJw7/lYpM4ccepSNfqzZ/QvABBi5g==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/template": {
      "version": "7.28.6",
      "resolved": "https://registry.npmjs.org/@babel/template/-/template-7.28.6.tgz",
      "integrity": "sha512-YA6Ma2KsCdGb+WC6UpBVFJGXL58MDA6oyONbjyF/+5sBgxY/dwkhLogbMT2GXXyU84/IhRw/2D1Os1B/giz+BQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.28.6",
        "@babel/parser": "^7.28.6",
        "@babel/types": "^7.28.6"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/traverse": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/traverse/-/traverse-7.29.0.tgz",
      "integrity": "sha512-4HPiQr0X7+waHfyXPZpWPfWL/J7dcN1mx9gL6WdQVMbPnF3+ZhSMs8tCxN7oHddJE9fhNE7+lxdnlyemKfJRuA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/code-frame": "^7.29.0",
        "@babel/generator": "^7.29.0",
        "@babel/helper-globals": "^7.28.0",
        "@babel/parser": "^7.29.0",
        "@babel/template": "^7.28.6",
        "@babel/types": "^7.29.0",
        "debug": "^4.3.1"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@babel/types": {
      "version": "7.29.0",
      "resolved": "https://registry.npmjs.org/@babel/types/-/types-7.29.0.tgz",
      "integrity": "sha512-LwdZHpScM4Qz8Xw2iKSzS+cfglZzJGvofQICy7W7v4caru4EaAmyUuO6BGrbyQ2mYV11W0U8j5mBhd14dd3B0A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/helper-string-parser": "^7.27.1",
        "@babel/helper-validator-identifier": "^7.28.5"
      },
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/@csstools/color-helpers": {
      "version": "6.0.2",
      "resolved": "https://registry.npmjs.org/@csstools/color-helpers/-/color-helpers-6.0.2.tgz",
      "integrity": "sha512-LMGQLS9EuADloEFkcTBR3BwV/CGHV7zyDxVRtVDTwdI2Ca4it0CCVTT9wCkxSgokjE5Ho41hEPgb8OEUwoXr6Q==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "license": "MIT-0",
      "engines": {
        "node": ">=20.19.0"
      }
    },
    "node_modules/@csstools/css-calc": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/@csstools/css-calc/-/css-calc-3.1.1.tgz",
      "integrity": "sha512-HJ26Z/vmsZQqs/o3a6bgKslXGFAungXGbinULZO3eMsOyNJHeBBZfup5FiZInOghgoM4Hwnmw+OgbJCNg1wwUQ==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "license": "MIT",
      "engines": {
        "node": ">=20.19.0"
      },
      "peerDependencies": {
        "@csstools/css-parser-algorithms": "^4.0.0",
        "@csstools/css-tokenizer": "^4.0.0"
      }
    },
    "node_modules/@csstools/css-color-parser": {
      "version": "4.0.2",
      "resolved": "https://registry.npmjs.org/@csstools/css-color-parser/-/css-color-parser-4.0.2.tgz",
      "integrity": "sha512-0GEfbBLmTFf0dJlpsNU7zwxRIH0/BGEMuXLTCvFYxuL1tNhqzTbtnFICyJLTNK4a+RechKP75e7w42ClXSnJQw==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "@csstools/color-helpers": "^6.0.2",
        "@csstools/css-calc": "^3.1.1"
      },
      "engines": {
        "node": ">=20.19.0"
      },
      "peerDependencies": {
        "@csstools/css-parser-algorithms": "^4.0.0",
        "@csstools/css-tokenizer": "^4.0.0"
      }
    },
    "node_modules/@csstools/css-parser-algorithms": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/@csstools/css-parser-algorithms/-/css-parser-algorithms-4.0.0.tgz",
      "integrity": "sha512-+B87qS7fIG3L5h3qwJ/IFbjoVoOe/bpOdh9hAjXbvx0o8ImEmUsGXN0inFOnk2ChCFgqkkGFQ+TpM5rbhkKe4w==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "license": "MIT",
      "engines": {
        "node": ">=20.19.0"
      },
      "peerDependencies": {
        "@csstools/css-tokenizer": "^4.0.0"
      }
    },
    "node_modules/@csstools/css-syntax-patches-for-csstree": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/@csstools/css-syntax-patches-for-csstree/-/css-syntax-patches-for-csstree-1.1.1.tgz",
      "integrity": "sha512-BvqN0AMWNAnLk9G8jnUT77D+mUbY/H2b3uDTvg2isJkHaOufUE2R3AOwxWo7VBQKT1lOdwdvorddo2B/lk64+w==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "license": "MIT-0",
      "peerDependencies": {
        "css-tree": "^3.2.1"
      },
      "peerDependenciesMeta": {
        "css-tree": {
          "optional": true
        }
      }
    },
    "node_modules/@csstools/css-tokenizer": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/@csstools/css-tokenizer/-/css-tokenizer-4.0.0.tgz",
      "integrity": "sha512-QxULHAm7cNu72w97JUNCBFODFaXpbDg+dP8b/oWFAZ2MTRppA3U00Y2L1HqaS4J6yBqxwa/Y3nMBaxVKbB/NsA==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/csstools"
        },
        {
          "type": "opencollective",
          "url": "https://opencollective.com/csstools"
        }
      ],
      "license": "MIT",
      "engines": {
        "node": ">=20.19.0"
      }
    },
    "node_modules/@emnapi/core": {
      "version": "1.9.1",
      "resolved": "https://registry.npmjs.org/@emnapi/core/-/core-1.9.1.tgz",
      "integrity": "sha512-mukuNALVsoix/w1BJwFzwXBN/dHeejQtuVzcDsfOEsdpCumXb/E9j8w11h5S54tT1xhifGfbbSm/ICrObRb3KA==",
      "dev": true,
      "license": "MIT",
      "optional": true,
      "dependencies": {
        "@emnapi/wasi-threads": "1.2.0",
        "tslib": "^2.4.0"
      }
    },
    "node_modules/@emnapi/runtime": {
      "version": "1.9.1",
      "resolved": "https://registry.npmjs.org/@emnapi/runtime/-/runtime-1.9.1.tgz",
      "integrity": "sha512-VYi5+ZVLhpgK4hQ0TAjiQiZ6ol0oe4mBx7mVv7IflsiEp0OWoVsp/+f9Vc1hOhE0TtkORVrI1GvzyreqpgWtkA==",
      "dev": true,
      "license": "MIT",
      "optional": true,
      "dependencies": {
        "tslib": "^2.4.0"
      }
    },
    "node_modules/@emnapi/wasi-threads": {
      "version": "1.2.0",
      "resolved": "https://registry.npmjs.org/@emnapi/wasi-threads/-/wasi-threads-1.2.0.tgz",
      "integrity": "sha512-N10dEJNSsUx41Z6pZsXU8FjPjpBEplgH24sfkmITrBED1/U2Esum9F3lfLrMjKHHjmi557zQn7kR9R+XWXu5Rg==",
      "dev": true,
      "license": "MIT",
      "optional": true,
      "dependencies": {
        "tslib": "^2.4.0"
      }
    },
    "node_modules/@eslint-community/eslint-utils": {
      "version": "4.9.1",
      "resolved": "https://registry.npmjs.org/@eslint-community/eslint-utils/-/eslint-utils-4.9.1.tgz",
      "integrity": "sha512-phrYmNiYppR7znFEdqgfWHXR6NCkZEK7hwWDHZUjit/2/U0r6XvkDl0SYnoM51Hq7FhCGdLDT6zxCCOY1hexsQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "eslint-visitor-keys": "^3.4.3"
      },
      "engines": {
        "node": "^12.22.0 || ^14.17.0 || >=16.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      },
      "peerDependencies": {
        "eslint": "^6.0.0 || ^7.0.0 || >=8.0.0"
      }
    },
    "node_modules/@eslint-community/eslint-utils/node_modules/eslint-visitor-keys": {
      "version": "3.4.3",
      "resolved": "https://registry.npmjs.org/eslint-visitor-keys/-/eslint-visitor-keys-3.4.3.tgz",
      "integrity": "sha512-wpc+LXeiyiisxPlEkUzU6svyS1frIO3Mgxj1fdy7Pm8Ygzguax2N3Fa/D/ag1WqbOprdI+uY6wMUl8/a2G+iag==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": "^12.22.0 || ^14.17.0 || >=16.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      }
    },
    "node_modules/@eslint-community/regexpp": {
      "version": "4.12.2",
      "resolved": "https://registry.npmjs.org/@eslint-community/regexpp/-/regexpp-4.12.2.tgz",
      "integrity": "sha512-EriSTlt5OC9/7SXkRSCAhfSxxoSUgBm33OH+IkwbdpgoqsSsUg7y3uh+IICI/Qg4BBWr3U2i39RpmycbxMq4ew==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": "^12.0.0 || ^14.0.0 || >=16.0.0"
      }
    },
    "node_modules/@eslint/config-array": {
      "version": "0.21.2",
      "resolved": "https://registry.npmjs.org/@eslint/config-array/-/config-array-0.21.2.tgz",
      "integrity": "sha512-nJl2KGTlrf9GjLimgIru+V/mzgSK0ABCDQRvxw5BjURL7WfH5uoWmizbH7QB6MmnMBd8cIC9uceWnezL1VZWWw==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "@eslint/object-schema": "^2.1.7",
        "debug": "^4.3.1",
        "minimatch": "^3.1.5"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      }
    },
    "node_modules/@eslint/config-helpers": {
      "version": "0.4.2",
      "resolved": "https://registry.npmjs.org/@eslint/config-helpers/-/config-helpers-0.4.2.tgz",
      "integrity": "sha512-gBrxN88gOIf3R7ja5K9slwNayVcZgK6SOUORm2uBzTeIEfeVaIhOpCtTox3P6R7o2jLFwLFTLnC7kU/RGcYEgw==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "@eslint/core": "^0.17.0"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      }
    },
    "node_modules/@eslint/core": {
      "version": "0.17.0",
      "resolved": "https://registry.npmjs.org/@eslint/core/-/core-0.17.0.tgz",
      "integrity": "sha512-yL/sLrpmtDaFEiUj1osRP4TI2MDz1AddJL+jZ7KSqvBuliN4xqYY54IfdN8qD8Toa6g1iloph1fxQNkjOxrrpQ==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "@types/json-schema": "^7.0.15"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      }
    },
    "node_modules/@eslint/eslintrc": {
      "version": "3.3.5",
      "resolved": "https://registry.npmjs.org/@eslint/eslintrc/-/eslintrc-3.3.5.tgz",
      "integrity": "sha512-4IlJx0X0qftVsN5E+/vGujTRIFtwuLbNsVUe7TO6zYPDR1O6nFwvwhIKEKSrl6dZchmYBITazxKoUYOjdtjlRg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "ajv": "^6.14.0",
        "debug": "^4.3.2",
        "espree": "^10.0.1",
        "globals": "^14.0.0",
        "ignore": "^5.2.0",
        "import-fresh": "^3.2.1",
        "js-yaml": "^4.1.1",
        "minimatch": "^3.1.5",
        "strip-json-comments": "^3.1.1"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      }
    },
    "node_modules/@eslint/eslintrc/node_modules/globals": {
      "version": "14.0.0",
      "resolved": "https://registry.npmjs.org/globals/-/globals-14.0.0.tgz",
      "integrity": "sha512-oahGvuMGQlPw/ivIYBjVSrWAfWLBeku5tpPE2fOPLi+WHffIWbuh2tCjhyQhTBPMf5E9jDEH4FOmTYgYwbKwtQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/@eslint/js": {
      "version": "9.39.4",
      "resolved": "https://registry.npmjs.org/@eslint/js/-/js-9.39.4.tgz",
      "integrity": "sha512-nE7DEIchvtiFTwBw4Lfbu59PG+kCofhjsKaCWzxTpt4lfRjRMqG6uMBzKXuEcyXhOHoUp9riAm7/aWYGhXZ9cw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "url": "https://eslint.org/donate"
      }
    },
    "node_modules/@eslint/object-schema": {
      "version": "2.1.7",
      "resolved": "https://registry.npmjs.org/@eslint/object-schema/-/object-schema-2.1.7.tgz",
      "integrity": "sha512-VtAOaymWVfZcmZbp6E2mympDIHvyjXs/12LqWYjVw6qjrfF+VK+fyG33kChz3nnK+SU5/NeHOqrTEHS8sXO3OA==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      }
    },
    "node_modules/@eslint/plugin-kit": {
      "version": "0.4.1",
      "resolved": "https://registry.npmjs.org/@eslint/plugin-kit/-/plugin-kit-0.4.1.tgz",
      "integrity": "sha512-43/qtrDUokr7LJqoF2c3+RInu/t4zfrpYdoSDfYyhg52rwLV6TnOvdG4fXm7IkSB3wErkcmJS9iEhjVtOSEjjA==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "@eslint/core": "^0.17.0",
        "levn": "^0.4.1"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      }
    },
    "node_modules/@exodus/bytes": {
      "version": "1.15.0",
      "resolved": "https://registry.npmjs.org/@exodus/bytes/-/bytes-1.15.0.tgz",
      "integrity": "sha512-UY0nlA+feH81UGSHv92sLEPLCeZFjXOuHhrIo0HQydScuQc8s0A7kL/UdgwgDq8g8ilksmuoF35YVTNphV2aBQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": "^20.19.0 || ^22.12.0 || >=24.0.0"
      },
      "peerDependencies": {
        "@noble/hashes": "^1.8.0 || ^2.0.0"
      },
      "peerDependenciesMeta": {
        "@noble/hashes": {
          "optional": true
        }
      }
    },
    "node_modules/@humanfs/core": {
      "version": "0.19.1",
      "resolved": "https://registry.npmjs.org/@humanfs/core/-/core-0.19.1.tgz",
      "integrity": "sha512-5DyQ4+1JEUzejeK1JGICcideyfUbGixgS9jNgex5nqkW+cY7WZhxBigmieN5Qnw9ZosSNVC9KQKyb+GUaGyKUA==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=18.18.0"
      }
    },
    "node_modules/@humanfs/node": {
      "version": "0.16.7",
      "resolved": "https://registry.npmjs.org/@humanfs/node/-/node-0.16.7.tgz",
      "integrity": "sha512-/zUx+yOsIrG4Y43Eh2peDeKCxlRt/gET6aHfaKpuq267qXdYDFViVHfMaLyygZOnl0kGWxFIgsBy8QFuTLUXEQ==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "@humanfs/core": "^0.19.1",
        "@humanwhocodes/retry": "^0.4.0"
      },
      "engines": {
        "node": ">=18.18.0"
      }
    },
    "node_modules/@humanwhocodes/module-importer": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/@humanwhocodes/module-importer/-/module-importer-1.0.1.tgz",
      "integrity": "sha512-bxveV4V8v5Yb4ncFTT3rPSgZBOpCkjfK0y4oVVVJwIuDVBRMDXrPyXRL988i5ap9m9bnyEEjWfm5WkBmtffLfA==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=12.22"
      },
      "funding": {
        "type": "github",
        "url": "https://github.com/sponsors/nzakas"
      }
    },
    "node_modules/@humanwhocodes/retry": {
      "version": "0.4.3",
      "resolved": "https://registry.npmjs.org/@humanwhocodes/retry/-/retry-0.4.3.tgz",
      "integrity": "sha512-bV0Tgo9K4hfPCek+aMAn81RppFKv2ySDQeMoSZuvTASywNTnVJCArCZE2FWqpvIatKu7VMRLWlR1EazvVhDyhQ==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=18.18"
      },
      "funding": {
        "type": "github",
        "url": "https://github.com/sponsors/nzakas"
      }
    },
    "node_modules/@jridgewell/gen-mapping": {
      "version": "0.3.13",
      "resolved": "https://registry.npmjs.org/@jridgewell/gen-mapping/-/gen-mapping-0.3.13.tgz",
      "integrity": "sha512-2kkt/7niJ6MgEPxF0bYdQ6etZaA+fQvDcLKckhy1yIQOzaoKjBBjSj63/aLVjYE3qhRt5dvM+uUyfCg6UKCBbA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.0",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/remapping": {
      "version": "2.3.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/remapping/-/remapping-2.3.5.tgz",
      "integrity": "sha512-LI9u/+laYG4Ds1TDKSJW2YPrIlcVYOwi2fUC6xB43lueCjgxV4lffOCZCtYFiH6TNOX+tQKXx97T4IKHbhyHEQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/gen-mapping": "^0.3.5",
        "@jridgewell/trace-mapping": "^0.3.24"
      }
    },
    "node_modules/@jridgewell/resolve-uri": {
      "version": "3.1.2",
      "resolved": "https://registry.npmjs.org/@jridgewell/resolve-uri/-/resolve-uri-3.1.2.tgz",
      "integrity": "sha512-bRISgCIjP20/tbWSPWMEi54QVPRZExkuD9lJL+UIxUKtwVJA8wW1Trb1jMs1RFXo1CBTNZ/5hpC9QvmKWdopKw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/@jridgewell/sourcemap-codec": {
      "version": "1.5.5",
      "resolved": "https://registry.npmjs.org/@jridgewell/sourcemap-codec/-/sourcemap-codec-1.5.5.tgz",
      "integrity": "sha512-cYQ9310grqxueWbl+WuIUIaiUaDcj7WOq5fVhEljNVgRfOUhY9fy2zTvfoqWsnebh8Sl70VScFbICvJnLKB0Og==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@jridgewell/trace-mapping": {
      "version": "0.3.31",
      "resolved": "https://registry.npmjs.org/@jridgewell/trace-mapping/-/trace-mapping-0.3.31.tgz",
      "integrity": "sha512-zzNR+SdQSDJzc8joaeP8QQoCQr8NuYx2dIIytl1QeBEZHJ9uW6hebsrYgbz8hJwUQao3TWCMtmfV8Nu1twOLAw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/resolve-uri": "^3.1.0",
        "@jridgewell/sourcemap-codec": "^1.4.14"
      }
    },
    "node_modules/@napi-rs/wasm-runtime": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/@napi-rs/wasm-runtime/-/wasm-runtime-1.1.1.tgz",
      "integrity": "sha512-p64ah1M1ld8xjWv3qbvFwHiFVWrq1yFvV4f7w+mzaqiR4IlSgkqhcRdHwsGgomwzBH51sRY4NEowLxnaBjcW/A==",
      "dev": true,
      "license": "MIT",
      "optional": true,
      "dependencies": {
        "@emnapi/core": "^1.7.1",
        "@emnapi/runtime": "^1.7.1",
        "@tybys/wasm-util": "^0.10.1"
      },
      "funding": {
        "type": "github",
        "url": "https://github.com/sponsors/Brooooooklyn"
      }
    },
    "node_modules/@oxc-project/types": {
      "version": "0.122.0",
      "resolved": "https://registry.npmjs.org/@oxc-project/types/-/types-0.122.0.tgz",
      "integrity": "sha512-oLAl5kBpV4w69UtFZ9xqcmTi+GENWOcPF7FCrczTiBbmC0ibXxCwyvZGbO39rCVEuLGAZM84DH0pUIyyv/YJzA==",
      "dev": true,
      "license": "MIT",
      "funding": {
        "url": "https://github.com/sponsors/Boshen"
      }
    },
    "node_modules/@rolldown/binding-android-arm64": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-android-arm64/-/binding-android-arm64-1.0.0-rc.11.tgz",
      "integrity": "sha512-SJ+/g+xNnOh6NqYxD0V3uVN4W3VfnrGsC9/hoglicgTNfABFG9JjISvkkU0dNY84MNHLWyOgxP9v9Y9pX4S7+A==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-darwin-arm64": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-darwin-arm64/-/binding-darwin-arm64-1.0.0-rc.11.tgz",
      "integrity": "sha512-7WQgR8SfOPwmDZGFkThUvsmd/nwAWv91oCO4I5LS7RKrssPZmOt7jONN0cW17ydGC1n/+puol1IpoieKqQidmg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-darwin-x64": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-darwin-x64/-/binding-darwin-x64-1.0.0-rc.11.tgz",
      "integrity": "sha512-39Ks6UvIHq4rEogIfQBoBRusj0Q0nPVWIvqmwBLaT6aqQGIakHdESBVOPRRLacy4WwUPIx4ZKzfZ9PMW+IeyUQ==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-freebsd-x64": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-freebsd-x64/-/binding-freebsd-x64-1.0.0-rc.11.tgz",
      "integrity": "sha512-jfsm0ZHfhiqrvWjJAmzsqiIFPz5e7mAoCOPBNTcNgkiid/LaFKiq92+0ojH+nmJmKYkre4t71BWXUZDNp7vsag==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-arm-gnueabihf": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-arm-gnueabihf/-/binding-linux-arm-gnueabihf-1.0.0-rc.11.tgz",
      "integrity": "sha512-zjQaUtSyq1nVe3nxmlSCuR96T1LPlpvmJ0SZy0WJFEsV4kFbXcq2u68L4E6O0XeFj4aex9bEauqjW8UQBeAvfQ==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-arm64-gnu": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-arm64-gnu/-/binding-linux-arm64-gnu-1.0.0-rc.11.tgz",
      "integrity": "sha512-WMW1yE6IOnehTcFE9eipFkm3XN63zypWlrJQ2iF7NrQ9b2LDRjumFoOGJE8RJJTJCTBAdmLMnJ8uVitACUUo1Q==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-arm64-musl": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-arm64-musl/-/binding-linux-arm64-musl-1.0.0-rc.11.tgz",
      "integrity": "sha512-jfndI9tsfm4APzjNt6QdBkYwre5lRPUgHeDHoI7ydKUuJvz3lZeCfMsI56BZj+7BYqiKsJm7cfd/6KYV7ubrBg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-ppc64-gnu": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-ppc64-gnu/-/binding-linux-ppc64-gnu-1.0.0-rc.11.tgz",
      "integrity": "sha512-ZlFgw46NOAGMgcdvdYwAGu2Q+SLFA9LzbJLW+iyMOJyhj5wk6P3KEE9Gct4xWwSzFoPI7JCdYmYMzVtlgQ+zfw==",
      "cpu": [
        "ppc64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-s390x-gnu": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-s390x-gnu/-/binding-linux-s390x-gnu-1.0.0-rc.11.tgz",
      "integrity": "sha512-hIOYmuT6ofM4K04XAZd3OzMySEO4K0/nc9+jmNcxNAxRi6c5UWpqfw3KMFV4MVFWL+jQsSh+bGw2VqmaPMTLyw==",
      "cpu": [
        "s390x"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-x64-gnu": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-x64-gnu/-/binding-linux-x64-gnu-1.0.0-rc.11.tgz",
      "integrity": "sha512-qXBQQO9OvkjjQPLdUVr7Nr2t3QTZI7s4KZtfw7HzBgjbmAPSFwSv4rmET9lLSgq3rH/ndA3ngv3Qb8l2njoPNA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-linux-x64-musl": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-linux-x64-musl/-/binding-linux-x64-musl-1.0.0-rc.11.tgz",
      "integrity": "sha512-/tpFfoSTzUkH9LPY+cYbqZBDyyX62w5fICq9qzsHLL8uTI6BHip3Q9Uzft0wylk/i8OOwKik8OxW+QAhDmzwmg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-openharmony-arm64": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-openharmony-arm64/-/binding-openharmony-arm64-1.0.0-rc.11.tgz",
      "integrity": "sha512-mcp3Rio2w72IvdZG0oQ4bM2c2oumtwHfUfKncUM6zGgz0KgPz4YmDPQfnXEiY5t3+KD/i8HG2rOB/LxdmieK2g==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "openharmony"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-wasm32-wasi": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-wasm32-wasi/-/binding-wasm32-wasi-1.0.0-rc.11.tgz",
      "integrity": "sha512-LXk5Hii1Ph9asuGRjBuz8TUxdc1lWzB7nyfdoRgI0WGPZKmCxvlKk8KfYysqtr4MfGElu/f/pEQRh8fcEgkrWw==",
      "cpu": [
        "wasm32"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "dependencies": {
        "@napi-rs/wasm-runtime": "^1.1.1"
      },
      "engines": {
        "node": ">=14.0.0"
      }
    },
    "node_modules/@rolldown/binding-win32-arm64-msvc": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-win32-arm64-msvc/-/binding-win32-arm64-msvc-1.0.0-rc.11.tgz",
      "integrity": "sha512-dDwf5otnx0XgRY1yqxOC4ITizcdzS/8cQ3goOWv3jFAo4F+xQYni+hnMuO6+LssHHdJW7+OCVL3CoU4ycnh35Q==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/binding-win32-x64-msvc": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/binding-win32-x64-msvc/-/binding-win32-x64-msvc-1.0.0-rc.11.tgz",
      "integrity": "sha512-LN4/skhSggybX71ews7dAj6r2geaMJfm3kMbK2KhFMg9B10AZXnKoLCVVgzhMHL0S+aKtr4p8QbAW8k+w95bAA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      }
    },
    "node_modules/@rolldown/pluginutils": {
      "version": "1.0.0-rc.7",
      "resolved": "https://registry.npmjs.org/@rolldown/pluginutils/-/pluginutils-1.0.0-rc.7.tgz",
      "integrity": "sha512-qujRfC8sFVInYSPPMLQByRh7zhwkGFS4+tyMQ83srV1qrxL4g8E2tyxVVyxd0+8QeBM1mIk9KbWxkegRr76XzA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@standard-schema/spec": {
      "version": "1.1.0",
      "resolved": "https://registry.npmjs.org/@standard-schema/spec/-/spec-1.1.0.tgz",
      "integrity": "sha512-l2aFy5jALhniG5HgqrD6jXLi/rUWrKvqN/qJx6yoJsgKhblVd+iqqU4RCXavm/jPityDo5TCvKMnpjKnOriy0w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@testing-library/dom": {
      "version": "10.4.1",
      "resolved": "https://registry.npmjs.org/@testing-library/dom/-/dom-10.4.1.tgz",
      "integrity": "sha512-o4PXJQidqJl82ckFaXUeoAW+XysPLauYI43Abki5hABd853iMhitooc6znOnczgbTYmEP6U6/y1ZyKAIsvMKGg==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "@babel/code-frame": "^7.10.4",
        "@babel/runtime": "^7.12.5",
        "@types/aria-query": "^5.0.1",
        "aria-query": "5.3.0",
        "dom-accessibility-api": "^0.5.9",
        "lz-string": "^1.5.0",
        "picocolors": "1.1.1",
        "pretty-format": "^27.0.2"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/@testing-library/jest-dom": {
      "version": "6.9.1",
      "resolved": "https://registry.npmjs.org/@testing-library/jest-dom/-/jest-dom-6.9.1.tgz",
      "integrity": "sha512-zIcONa+hVtVSSep9UT3jZ5rizo2BsxgyDYU7WFD5eICBE7no3881HGeb/QkGfsJs6JTkY1aQhT7rIPC7e+0nnA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@adobe/css-tools": "^4.4.0",
        "aria-query": "^5.0.0",
        "css.escape": "^1.5.1",
        "dom-accessibility-api": "^0.6.3",
        "picocolors": "^1.1.1",
        "redent": "^3.0.0"
      },
      "engines": {
        "node": ">=14",
        "npm": ">=6",
        "yarn": ">=1"
      }
    },
    "node_modules/@testing-library/jest-dom/node_modules/dom-accessibility-api": {
      "version": "0.6.3",
      "resolved": "https://registry.npmjs.org/dom-accessibility-api/-/dom-accessibility-api-0.6.3.tgz",
      "integrity": "sha512-7ZgogeTnjuHbo+ct10G9Ffp0mif17idi0IyWNVA/wcwcm7NPOD/WEHVP3n7n3MhXqxoIYm8d6MuZohYWIZ4T3w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@testing-library/react": {
      "version": "16.3.2",
      "resolved": "https://registry.npmjs.org/@testing-library/react/-/react-16.3.2.tgz",
      "integrity": "sha512-XU5/SytQM+ykqMnAnvB2umaJNIOsLF3PVv//1Ew4CTcpz0/BRyy/af40qqrt7SjKpDdT1saBMc42CUok5gaw+g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/runtime": "^7.12.5"
      },
      "engines": {
        "node": ">=18"
      },
      "peerDependencies": {
        "@testing-library/dom": "^10.0.0",
        "@types/react": "^18.0.0 || ^19.0.0",
        "@types/react-dom": "^18.0.0 || ^19.0.0",
        "react": "^18.0.0 || ^19.0.0",
        "react-dom": "^18.0.0 || ^19.0.0"
      },
      "peerDependenciesMeta": {
        "@types/react": {
          "optional": true
        },
        "@types/react-dom": {
          "optional": true
        }
      }
    },
    "node_modules/@tybys/wasm-util": {
      "version": "0.10.1",
      "resolved": "https://registry.npmjs.org/@tybys/wasm-util/-/wasm-util-0.10.1.tgz",
      "integrity": "sha512-9tTaPJLSiejZKx+Bmog4uSubteqTvFrVrURwkmHixBo0G4seD0zUxp98E1DzUBJxLQ3NPwXrGKDiVjwx/DpPsg==",
      "dev": true,
      "license": "MIT",
      "optional": true,
      "dependencies": {
        "tslib": "^2.4.0"
      }
    },
    "node_modules/@types/aria-query": {
      "version": "5.0.4",
      "resolved": "https://registry.npmjs.org/@types/aria-query/-/aria-query-5.0.4.tgz",
      "integrity": "sha512-rfT93uj5s0PRL7EzccGMs3brplhcrghnDoV26NqKhCAS1hVo+WdNsPvE/yb6ilfr5hi2MEk6d5EWJTKdxg8jVw==",
      "dev": true,
      "license": "MIT",
      "peer": true
    },
    "node_modules/@types/chai": {
      "version": "5.2.3",
      "resolved": "https://registry.npmjs.org/@types/chai/-/chai-5.2.3.tgz",
      "integrity": "sha512-Mw558oeA9fFbv65/y4mHtXDs9bPnFMZAL/jxdPFUpOHHIXX91mcgEHbS5Lahr+pwZFR8A7GQleRWeI6cGFC2UA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/deep-eql": "*",
        "assertion-error": "^2.0.1"
      }
    },
    "node_modules/@types/deep-eql": {
      "version": "4.0.2",
      "resolved": "https://registry.npmjs.org/@types/deep-eql/-/deep-eql-4.0.2.tgz",
      "integrity": "sha512-c9h9dVVMigMPc4bwTvC5dxqtqJZwQPePsWjPlpSOnojbor6pGqdk541lfA7AqFQr5pB1BRdq0juY9db81BwyFw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/estree": {
      "version": "1.0.8",
      "resolved": "https://registry.npmjs.org/@types/estree/-/estree-1.0.8.tgz",
      "integrity": "sha512-dWHzHa2WqEXI/O1E9OjrocMTKJl2mSrEolh1Iomrv6U+JuNwaHXsXx9bLu5gG7BUWFIN0skIQJQ/L1rIex4X6w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/json-schema": {
      "version": "7.0.15",
      "resolved": "https://registry.npmjs.org/@types/json-schema/-/json-schema-7.0.15.tgz",
      "integrity": "sha512-5+fP8P8MFNC+AyZCDxrB2pkZFPGzqQWUzpSeuuVLvm8VMcorNYavBqoFcxK8bQz4Qsbn4oUEEem4wDLfcysGHA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/@types/node": {
      "version": "24.12.0",
      "resolved": "https://registry.npmjs.org/@types/node/-/node-24.12.0.tgz",
      "integrity": "sha512-GYDxsZi3ChgmckRT9HPU0WEhKLP08ev/Yfcq2AstjrDASOYCSXeyjDsHg4v5t4jOj7cyDX3vmprafKlWIG9MXQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "undici-types": "~7.16.0"
      }
    },
    "node_modules/@types/react": {
      "version": "19.2.14",
      "resolved": "https://registry.npmjs.org/@types/react/-/react-19.2.14.tgz",
      "integrity": "sha512-ilcTH/UniCkMdtexkoCN0bI7pMcJDvmQFPvuPvmEaYA/NSfFTAgdUSLAoVjaRJm7+6PvcM+q1zYOwS4wTYMF9w==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "csstype": "^3.2.2"
      }
    },
    "node_modules/@types/react-dom": {
      "version": "19.2.3",
      "resolved": "https://registry.npmjs.org/@types/react-dom/-/react-dom-19.2.3.tgz",
      "integrity": "sha512-jp2L/eY6fn+KgVVQAOqYItbF0VY/YApe5Mz2F0aykSO8gx31bYCZyvSeYxCHKvzHG5eZjc+zyaS5BrBWya2+kQ==",
      "dev": true,
      "license": "MIT",
      "peerDependencies": {
        "@types/react": "^19.2.0"
      }
    },
    "node_modules/@typescript-eslint/eslint-plugin": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/eslint-plugin/-/eslint-plugin-8.57.2.tgz",
      "integrity": "sha512-NZZgp0Fm2IkD+La5PR81sd+g+8oS6JwJje+aRWsDocxHkjyRw0J5L5ZTlN3LI1LlOcGL7ph3eaIUmTXMIjLk0w==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@eslint-community/regexpp": "^4.12.2",
        "@typescript-eslint/scope-manager": "8.57.2",
        "@typescript-eslint/type-utils": "8.57.2",
        "@typescript-eslint/utils": "8.57.2",
        "@typescript-eslint/visitor-keys": "8.57.2",
        "ignore": "^7.0.5",
        "natural-compare": "^1.4.0",
        "ts-api-utils": "^2.4.0"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "@typescript-eslint/parser": "^8.57.2",
        "eslint": "^8.57.0 || ^9.0.0 || ^10.0.0",
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/eslint-plugin/node_modules/ignore": {
      "version": "7.0.5",
      "resolved": "https://registry.npmjs.org/ignore/-/ignore-7.0.5.tgz",
      "integrity": "sha512-Hs59xBNfUIunMFgWAbGX5cq6893IbWg4KnrjbYwX3tx0ztorVgTDA6B2sxf8ejHJ4wz8BqGUMYlnzNBer5NvGg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">= 4"
      }
    },
    "node_modules/@typescript-eslint/parser": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/parser/-/parser-8.57.2.tgz",
      "integrity": "sha512-30ScMRHIAD33JJQkgfGW1t8CURZtjc2JpTrq5n2HFhOefbAhb7ucc7xJwdWcrEtqUIYJ73Nybpsggii6GtAHjA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/scope-manager": "8.57.2",
        "@typescript-eslint/types": "8.57.2",
        "@typescript-eslint/typescript-estree": "8.57.2",
        "@typescript-eslint/visitor-keys": "8.57.2",
        "debug": "^4.4.3"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "eslint": "^8.57.0 || ^9.0.0 || ^10.0.0",
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/project-service": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/project-service/-/project-service-8.57.2.tgz",
      "integrity": "sha512-FuH0wipFywXRTHf+bTTjNyuNQQsQC3qh/dYzaM4I4W0jrCqjCVuUh99+xd9KamUfmCGPvbO8NDngo/vsnNVqgw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/tsconfig-utils": "^8.57.2",
        "@typescript-eslint/types": "^8.57.2",
        "debug": "^4.4.3"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/scope-manager": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/scope-manager/-/scope-manager-8.57.2.tgz",
      "integrity": "sha512-snZKH+W4WbWkrBqj4gUNRIGb/jipDW3qMqVJ4C9rzdFc+wLwruxk+2a5D+uoFcKPAqyqEnSb4l2ULuZf95eSkw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/types": "8.57.2",
        "@typescript-eslint/visitor-keys": "8.57.2"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      }
    },
    "node_modules/@typescript-eslint/tsconfig-utils": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/tsconfig-utils/-/tsconfig-utils-8.57.2.tgz",
      "integrity": "sha512-3Lm5DSM+DCowsUOJC+YqHHnKEfFh5CoGkj5Z31NQSNF4l5wdOwqGn99wmwN/LImhfY3KJnmordBq/4+VDe2eKw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/type-utils": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/type-utils/-/type-utils-8.57.2.tgz",
      "integrity": "sha512-Co6ZCShm6kIbAM/s+oYVpKFfW7LBc6FXoPXjTRQ449PPNBY8U0KZXuevz5IFuuUj2H9ss40atTaf9dlGLzbWZg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/types": "8.57.2",
        "@typescript-eslint/typescript-estree": "8.57.2",
        "@typescript-eslint/utils": "8.57.2",
        "debug": "^4.4.3",
        "ts-api-utils": "^2.4.0"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "eslint": "^8.57.0 || ^9.0.0 || ^10.0.0",
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/types": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/types/-/types-8.57.2.tgz",
      "integrity": "sha512-/iZM6FnM4tnx9csuTxspMW4BOSegshwX5oBDznJ7S4WggL7Vczz5d2W11ecc4vRrQMQHXRSxzrCsyG5EsPPTbA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      }
    },
    "node_modules/@typescript-eslint/typescript-estree": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/typescript-estree/-/typescript-estree-8.57.2.tgz",
      "integrity": "sha512-2MKM+I6g8tJxfSmFKOnHv2t8Sk3T6rF20A1Puk0svLK+uVapDZB/4pfAeB7nE83uAZrU6OxW+HmOd5wHVdXwXA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/project-service": "8.57.2",
        "@typescript-eslint/tsconfig-utils": "8.57.2",
        "@typescript-eslint/types": "8.57.2",
        "@typescript-eslint/visitor-keys": "8.57.2",
        "debug": "^4.4.3",
        "minimatch": "^10.2.2",
        "semver": "^7.7.3",
        "tinyglobby": "^0.2.15",
        "ts-api-utils": "^2.4.0"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/typescript-estree/node_modules/balanced-match": {
      "version": "4.0.4",
      "resolved": "https://registry.npmjs.org/balanced-match/-/balanced-match-4.0.4.tgz",
      "integrity": "sha512-BLrgEcRTwX2o6gGxGOCNyMvGSp35YofuYzw9h1IMTRmKqttAZZVU67bdb9Pr2vUHA8+j3i2tJfjO6C6+4myGTA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": "18 || 20 || >=22"
      }
    },
    "node_modules/@typescript-eslint/typescript-estree/node_modules/brace-expansion": {
      "version": "5.0.4",
      "resolved": "https://registry.npmjs.org/brace-expansion/-/brace-expansion-5.0.4.tgz",
      "integrity": "sha512-h+DEnpVvxmfVefa4jFbCf5HdH5YMDXRsmKflpf1pILZWRFlTbJpxeU55nJl4Smt5HQaGzg1o6RHFPJaOqnmBDg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "balanced-match": "^4.0.2"
      },
      "engines": {
        "node": "18 || 20 || >=22"
      }
    },
    "node_modules/@typescript-eslint/typescript-estree/node_modules/minimatch": {
      "version": "10.2.4",
      "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-10.2.4.tgz",
      "integrity": "sha512-oRjTw/97aTBN0RHbYCdtF1MQfvusSIBQM0IZEgzl6426+8jSC0nF1a/GmnVLpfB9yyr6g6FTqWqiZVbxrtaCIg==",
      "dev": true,
      "license": "BlueOak-1.0.0",
      "dependencies": {
        "brace-expansion": "^5.0.2"
      },
      "engines": {
        "node": "18 || 20 || >=22"
      },
      "funding": {
        "url": "https://github.com/sponsors/isaacs"
      }
    },
    "node_modules/@typescript-eslint/typescript-estree/node_modules/semver": {
      "version": "7.7.4",
      "resolved": "https://registry.npmjs.org/semver/-/semver-7.7.4.tgz",
      "integrity": "sha512-vFKC2IEtQnVhpT78h1Yp8wzwrf8CM+MzKMHGJZfBtzhZNycRFnXsHk6E5TxIkkMsgNS7mdX3AGB7x2QM2di4lA==",
      "dev": true,
      "license": "ISC",
      "bin": {
        "semver": "bin/semver.js"
      },
      "engines": {
        "node": ">=10"
      }
    },
    "node_modules/@typescript-eslint/utils": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/utils/-/utils-8.57.2.tgz",
      "integrity": "sha512-krRIbvPK1ju1WBKIefiX+bngPs+odIQUtR7kymzPfo1POVw3jlF+nLkmexdSSd4UCbDcQn+wMBATOOmpBbqgKg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@eslint-community/eslint-utils": "^4.9.1",
        "@typescript-eslint/scope-manager": "8.57.2",
        "@typescript-eslint/types": "8.57.2",
        "@typescript-eslint/typescript-estree": "8.57.2"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "eslint": "^8.57.0 || ^9.0.0 || ^10.0.0",
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/@typescript-eslint/visitor-keys": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/@typescript-eslint/visitor-keys/-/visitor-keys-8.57.2.tgz",
      "integrity": "sha512-zhahknjobV2FiD6Ee9iLbS7OV9zi10rG26odsQdfBO/hjSzUQbkIYgda+iNKK1zNiW2ey+Lf8MU5btN17V3dUw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/types": "8.57.2",
        "eslint-visitor-keys": "^5.0.0"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      }
    },
    "node_modules/@typescript-eslint/visitor-keys/node_modules/eslint-visitor-keys": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/eslint-visitor-keys/-/eslint-visitor-keys-5.0.1.tgz",
      "integrity": "sha512-tD40eHxA35h0PEIZNeIjkHoDR4YjjJp34biM0mDvplBe//mB+IHCqHDGV7pxF+7MklTvighcCPPZC7ynWyjdTA==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": "^20.19.0 || ^22.13.0 || >=24"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      }
    },
    "node_modules/@vitejs/plugin-react": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/@vitejs/plugin-react/-/plugin-react-6.0.1.tgz",
      "integrity": "sha512-l9X/E3cDb+xY3SWzlG1MOGt2usfEHGMNIaegaUGFsLkb3RCn/k8/TOXBcab+OndDI4TBtktT8/9BwwW8Vi9KUQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@rolldown/pluginutils": "1.0.0-rc.7"
      },
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      },
      "peerDependencies": {
        "@rolldown/plugin-babel": "^0.1.7 || ^0.2.0",
        "babel-plugin-react-compiler": "^1.0.0",
        "vite": "^8.0.0"
      },
      "peerDependenciesMeta": {
        "@rolldown/plugin-babel": {
          "optional": true
        },
        "babel-plugin-react-compiler": {
          "optional": true
        }
      }
    },
    "node_modules/@vitest/expect": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/expect/-/expect-4.1.1.tgz",
      "integrity": "sha512-xAV0fqBTk44Rn6SjJReEQkHP3RrqbJo6JQ4zZ7/uVOiJZRarBtblzrOfFIZeYUrukp2YD6snZG6IBqhOoHTm+A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@standard-schema/spec": "^1.1.0",
        "@types/chai": "^5.2.2",
        "@vitest/spy": "4.1.1",
        "@vitest/utils": "4.1.1",
        "chai": "^6.2.2",
        "tinyrainbow": "^3.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/mocker": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/mocker/-/mocker-4.1.1.tgz",
      "integrity": "sha512-h3BOylsfsCLPeceuCPAAJ+BvNwSENgJa4hXoXu4im0bs9Lyp4URc4JYK4pWLZ4pG/UQn7AT92K6IByi6rE6g3A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/spy": "4.1.1",
        "estree-walker": "^3.0.3",
        "magic-string": "^0.30.21"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      },
      "peerDependencies": {
        "msw": "^2.4.9",
        "vite": "^6.0.0 || ^7.0.0 || ^8.0.0"
      },
      "peerDependenciesMeta": {
        "msw": {
          "optional": true
        },
        "vite": {
          "optional": true
        }
      }
    },
    "node_modules/@vitest/pretty-format": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/pretty-format/-/pretty-format-4.1.1.tgz",
      "integrity": "sha512-GM+TEQN5WhOygr1lp7skeVjdLPqqWMHsfzXrcHAqZJi/lIVh63H0kaRCY8MDhNWikx19zBUK8ceaLB7X5AH9NQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "tinyrainbow": "^3.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/runner": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/runner/-/runner-4.1.1.tgz",
      "integrity": "sha512-f7+FPy75vN91QGWsITueq0gedwUZy1fLtHOCMeQpjs8jTekAHeKP80zfDEnhrleviLHzVSDXIWuCIOFn3D3f8A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/utils": "4.1.1",
        "pathe": "^2.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/snapshot": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/snapshot/-/snapshot-4.1.1.tgz",
      "integrity": "sha512-kMVSgcegWV2FibXEx9p9WIKgje58lcTbXgnJixfcg15iK8nzCXhmalL0ZLtTWLW9PH1+1NEDShiFFedB3tEgWg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/pretty-format": "4.1.1",
        "@vitest/utils": "4.1.1",
        "magic-string": "^0.30.21",
        "pathe": "^2.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/spy": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/spy/-/spy-4.1.1.tgz",
      "integrity": "sha512-6Ti/KT5OVaiupdIZEuZN7l3CZcR0cxnxt70Z0//3CtwgObwA6jZhmVBA3yrXSVN3gmwjgd7oDNLlsXz526gpRA==",
      "dev": true,
      "license": "MIT",
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/@vitest/utils": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/@vitest/utils/-/utils-4.1.1.tgz",
      "integrity": "sha512-cNxAlaB3sHoCdL6pj6yyUXv9Gry1NHNg0kFTXdvSIZXLHsqKH7chiWOkwJ5s5+d/oMwcoG9T0bKU38JZWKusrQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/pretty-format": "4.1.1",
        "convert-source-map": "^2.0.0",
        "tinyrainbow": "^3.0.3"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      }
    },
    "node_modules/acorn": {
      "version": "8.16.0",
      "resolved": "https://registry.npmjs.org/acorn/-/acorn-8.16.0.tgz",
      "integrity": "sha512-UVJyE9MttOsBQIDKw1skb9nAwQuR5wuGD3+82K6JgJlm/Y+KI92oNsMNGZCYdDsVtRHSak0pcV5Dno5+4jh9sw==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "acorn": "bin/acorn"
      },
      "engines": {
        "node": ">=0.4.0"
      }
    },
    "node_modules/acorn-jsx": {
      "version": "5.3.2",
      "resolved": "https://registry.npmjs.org/acorn-jsx/-/acorn-jsx-5.3.2.tgz",
      "integrity": "sha512-rq9s+JNhf0IChjtDXxllJ7g41oZk5SlXtp0LHwyA5cejwn7vKmKp4pPri6YEePv2PU65sAsegbXtIinmDFDXgQ==",
      "dev": true,
      "license": "MIT",
      "peerDependencies": {
        "acorn": "^6.0.0 || ^7.0.0 || ^8.0.0"
      }
    },
    "node_modules/agent-base": {
      "version": "7.1.4",
      "resolved": "https://registry.npmjs.org/agent-base/-/agent-base-7.1.4.tgz",
      "integrity": "sha512-MnA+YT8fwfJPgBx3m60MNqakm30XOkyIoH1y6huTQvC0PwZG7ki8NacLBcrPbNoo8vEZy7Jpuk7+jMO+CUovTQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">= 14"
      }
    },
    "node_modules/ajv": {
      "version": "6.14.0",
      "resolved": "https://registry.npmjs.org/ajv/-/ajv-6.14.0.tgz",
      "integrity": "sha512-IWrosm/yrn43eiKqkfkHis7QioDleaXQHdDVPKg0FSwwd/DuvyX79TZnFOnYpB7dcsFAMmtFztZuXPDvSePkFw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "fast-deep-equal": "^3.1.1",
        "fast-json-stable-stringify": "^2.0.0",
        "json-schema-traverse": "^0.4.1",
        "uri-js": "^4.2.2"
      },
      "funding": {
        "type": "github",
        "url": "https://github.com/sponsors/epoberezkin"
      }
    },
    "node_modules/ansi-regex": {
      "version": "5.0.1",
      "resolved": "https://registry.npmjs.org/ansi-regex/-/ansi-regex-5.0.1.tgz",
      "integrity": "sha512-quJQXlTSUGL2LH9SUXo8VwsY4soanhgo6LNSm84E1LBcE8s3O0wpdiRzyR9z/ZZJMlMWv37qOOb9pdJlMUEKFQ==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/ansi-styles": {
      "version": "4.3.0",
      "resolved": "https://registry.npmjs.org/ansi-styles/-/ansi-styles-4.3.0.tgz",
      "integrity": "sha512-zbB9rCJAT1rbjiVDb2hqKFHNYLxgtk8NURxZ3IZwD3F6NtxbXZQCnnSi1Lkx+IDohdPlFp222wVALIheZJQSEg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "color-convert": "^2.0.1"
      },
      "engines": {
        "node": ">=8"
      },
      "funding": {
        "url": "https://github.com/chalk/ansi-styles?sponsor=1"
      }
    },
    "node_modules/argparse": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/argparse/-/argparse-2.0.1.tgz",
      "integrity": "sha512-8+9WqebbFzpX9OR+Wa6O29asIogeRMzcGtAINdpMHHyAg10f05aSFVBbcEqGf/PXw1EjAZ+q2/bEBg3DvurK3Q==",
      "dev": true,
      "license": "Python-2.0"
    },
    "node_modules/aria-query": {
      "version": "5.3.0",
      "resolved": "https://registry.npmjs.org/aria-query/-/aria-query-5.3.0.tgz",
      "integrity": "sha512-b0P0sZPKtyu8HkeRAfCq0IfURZK+SuwMjY1UXGBU27wpAiTwQAIlq56IbIO+ytk/JjS1fMR14ee5WBBfKi5J6A==",
      "dev": true,
      "license": "Apache-2.0",
      "dependencies": {
        "dequal": "^2.0.3"
      }
    },
    "node_modules/assertion-error": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/assertion-error/-/assertion-error-2.0.1.tgz",
      "integrity": "sha512-Izi8RQcffqCeNVgFigKli1ssklIbpHnCYc6AknXGYoB6grJqyeby7jv12JUQgmTAnIDnbck1uxksT4dzN3PWBA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=12"
      }
    },
    "node_modules/balanced-match": {
      "version": "1.0.2",
      "resolved": "https://registry.npmjs.org/balanced-match/-/balanced-match-1.0.2.tgz",
      "integrity": "sha512-3oSeUO0TMV67hN1AmbXsK4yaqU7tjiHlbxRDZOpH0KW9+CeX4bRAaX0Anxt0tx2MrpRpWwQaPwIlISEJhYU5Pw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/baseline-browser-mapping": {
      "version": "2.10.10",
      "resolved": "https://registry.npmjs.org/baseline-browser-mapping/-/baseline-browser-mapping-2.10.10.tgz",
      "integrity": "sha512-sUoJ3IMxx4AyRqO4MLeHlnGDkyXRoUG0/AI9fjK+vS72ekpV0yWVY7O0BVjmBcRtkNcsAO2QDZ4tdKKGoI6YaQ==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "baseline-browser-mapping": "dist/cli.cjs"
      },
      "engines": {
        "node": ">=6.0.0"
      }
    },
    "node_modules/bidi-js": {
      "version": "1.0.3",
      "resolved": "https://registry.npmjs.org/bidi-js/-/bidi-js-1.0.3.tgz",
      "integrity": "sha512-RKshQI1R3YQ+n9YJz2QQ147P66ELpa1FQEg20Dk8oW9t2KgLbpDLLp9aGZ7y8WHSshDknG0bknqGw5/tyCs5tw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "require-from-string": "^2.0.2"
      }
    },
    "node_modules/brace-expansion": {
      "version": "1.1.12",
      "resolved": "https://registry.npmjs.org/brace-expansion/-/brace-expansion-1.1.12.tgz",
      "integrity": "sha512-9T9UjW3r0UW5c1Q7GTwllptXwhvYmEzFhzMfZ9H7FQWt+uZePjZPjBP/W1ZEyZ1twGWom5/56TF4lPcqjnDHcg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "balanced-match": "^1.0.0",
        "concat-map": "0.0.1"
      }
    },
    "node_modules/browserslist": {
      "version": "4.28.1",
      "resolved": "https://registry.npmjs.org/browserslist/-/browserslist-4.28.1.tgz",
      "integrity": "sha512-ZC5Bd0LgJXgwGqUknZY/vkUQ04r8NXnJZ3yYi4vDmSiZmC/pdSN0NbNRPxZpbtO4uAfDUAFffO8IZoM3Gj8IkA==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "baseline-browser-mapping": "^2.9.0",
        "caniuse-lite": "^1.0.30001759",
        "electron-to-chromium": "^1.5.263",
        "node-releases": "^2.0.27",
        "update-browserslist-db": "^1.2.0"
      },
      "bin": {
        "browserslist": "cli.js"
      },
      "engines": {
        "node": "^6 || ^7 || ^8 || ^9 || ^10 || ^11 || ^12 || >=13.7"
      }
    },
    "node_modules/callsites": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/callsites/-/callsites-3.1.0.tgz",
      "integrity": "sha512-P8BjAsXvZS+VIDUI11hHCQEv74YT67YUi5JJFNWIqL235sBmjX4+qx9Muvls5ivyNENctx46xQLQ3aTuE7ssaQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/caniuse-lite": {
      "version": "1.0.30001781",
      "resolved": "https://registry.npmjs.org/caniuse-lite/-/caniuse-lite-1.0.30001781.tgz",
      "integrity": "sha512-RdwNCyMsNBftLjW6w01z8bKEvT6e/5tpPVEgtn22TiLGlstHOVecsX2KHFkD5e/vRnIE4EGzpuIODb3mtswtkw==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/caniuse-lite"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "CC-BY-4.0"
    },
    "node_modules/chai": {
      "version": "6.2.2",
      "resolved": "https://registry.npmjs.org/chai/-/chai-6.2.2.tgz",
      "integrity": "sha512-NUPRluOfOiTKBKvWPtSD4PhFvWCqOi0BGStNWs57X9js7XGTprSmFoz5F0tWhR4WPjNeR9jXqdC7/UpSJTnlRg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/chalk": {
      "version": "4.1.2",
      "resolved": "https://registry.npmjs.org/chalk/-/chalk-4.1.2.tgz",
      "integrity": "sha512-oKnbhFyRIXpUuez8iBMmyEa4nbj4IOQyuhc/wy9kY7/WVPcwIO9VA668Pu8RkO7+0G76SLROeyw9CpQ061i4mA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "ansi-styles": "^4.1.0",
        "supports-color": "^7.1.0"
      },
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/chalk/chalk?sponsor=1"
      }
    },
    "node_modules/color-convert": {
      "version": "2.0.1",
      "resolved": "https://registry.npmjs.org/color-convert/-/color-convert-2.0.1.tgz",
      "integrity": "sha512-RRECPsj7iu/xb5oKYcsFHSppFNnsj/52OVTRKb4zP5onXwVF3zVmmToNcOfGC+CRDpfK/U584fMg38ZHCaElKQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "color-name": "~1.1.4"
      },
      "engines": {
        "node": ">=7.0.0"
      }
    },
    "node_modules/color-name": {
      "version": "1.1.4",
      "resolved": "https://registry.npmjs.org/color-name/-/color-name-1.1.4.tgz",
      "integrity": "sha512-dOy+3AuW3a2wNbZHIuMZpTcgjGuLU/uBL/ubcZF9OXbDo8ff4O8yVp5Bf0efS8uEoYo5q4Fx7dY9OgQGXgAsQA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/concat-map": {
      "version": "0.0.1",
      "resolved": "https://registry.npmjs.org/concat-map/-/concat-map-0.0.1.tgz",
      "integrity": "sha512-/Srv4dswyQNBfohGpz9o6Yb3Gz3SrUDqBH5rTuhGR7ahtlbYKnVxw2bCFMRljaA7EXHaXZ8wsHdodFvbkhKmqg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/convert-source-map": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/convert-source-map/-/convert-source-map-2.0.0.tgz",
      "integrity": "sha512-Kvp459HrV2FEJ1CAsi1Ku+MY3kasH19TFykTz2xWmMeq6bk2NU3XXvfJ+Q61m0xktWwt+1HSYf3JZsTms3aRJg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/cookie": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/cookie/-/cookie-1.1.1.tgz",
      "integrity": "sha512-ei8Aos7ja0weRpFzJnEA9UHJ/7XQmqglbRwnf2ATjcB9Wq874VKH9kfjjirM6UhU2/E5fFYadylyhFldcqSidQ==",
      "license": "MIT",
      "engines": {
        "node": ">=18"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/express"
      }
    },
    "node_modules/cross-spawn": {
      "version": "7.0.6",
      "resolved": "https://registry.npmjs.org/cross-spawn/-/cross-spawn-7.0.6.tgz",
      "integrity": "sha512-uV2QOWP2nWzsy2aMp8aRibhi9dlzF5Hgh5SHaB9OiTGEyDTiJJyx0uy51QXdyWbtAHNua4XJzUKca3OzKUd3vA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "path-key": "^3.1.0",
        "shebang-command": "^2.0.0",
        "which": "^2.0.1"
      },
      "engines": {
        "node": ">= 8"
      }
    },
    "node_modules/css-tree": {
      "version": "3.2.1",
      "resolved": "https://registry.npmjs.org/css-tree/-/css-tree-3.2.1.tgz",
      "integrity": "sha512-X7sjQzceUhu1u7Y/ylrRZFU2FS6LRiFVp6rKLPg23y3x3c3DOKAwuXGDp+PAGjh6CSnCjYeAul8pcT8bAl+lSA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "mdn-data": "2.27.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12.20.0 || ^14.13.0 || >=15.0.0"
      }
    },
    "node_modules/css.escape": {
      "version": "1.5.1",
      "resolved": "https://registry.npmjs.org/css.escape/-/css.escape-1.5.1.tgz",
      "integrity": "sha512-YUifsXXuknHlUsmlgyY0PKzgPOr7/FjCePfHNt0jxm83wHZi44VDMQ7/fGNkjY3/jV1MC+1CmZbaHzugyeRtpg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/cssstyle": {
      "version": "5.3.7",
      "resolved": "https://registry.npmjs.org/cssstyle/-/cssstyle-5.3.7.tgz",
      "integrity": "sha512-7D2EPVltRrsTkhpQmksIu+LxeWAIEk6wRDMJ1qljlv+CKHJM+cJLlfhWIzNA44eAsHXSNe3+vO6DW1yCYx8SuQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@asamuzakjp/css-color": "^4.1.1",
        "@csstools/css-syntax-patches-for-csstree": "^1.0.21",
        "css-tree": "^3.1.0",
        "lru-cache": "^11.2.4"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/cssstyle/node_modules/lru-cache": {
      "version": "11.2.7",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-11.2.7.tgz",
      "integrity": "sha512-aY/R+aEsRelme17KGQa/1ZSIpLpNYYrhcrepKTZgE+W3WM16YMCaPwOHLHsmopZHELU0Ojin1lPVxKR0MihncA==",
      "dev": true,
      "license": "BlueOak-1.0.0",
      "engines": {
        "node": "20 || >=22"
      }
    },
    "node_modules/csstype": {
      "version": "3.2.3",
      "resolved": "https://registry.npmjs.org/csstype/-/csstype-3.2.3.tgz",
      "integrity": "sha512-z1HGKcYy2xA8AGQfwrn0PAy+PB7X/GSj3UVJW9qKyn43xWa+gl5nXmU4qqLMRzWVLFC8KusUX8T/0kCiOYpAIQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/data-urls": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/data-urls/-/data-urls-6.0.1.tgz",
      "integrity": "sha512-euIQENZg6x8mj3fO6o9+fOW8MimUI4PpD/fZBhJfeioZVy9TUpM4UY7KjQNVZFlqwJ0UdzRDzkycB997HEq1BQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "whatwg-mimetype": "^5.0.0",
        "whatwg-url": "^15.1.0"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/data-urls/node_modules/whatwg-mimetype": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/whatwg-mimetype/-/whatwg-mimetype-5.0.0.tgz",
      "integrity": "sha512-sXcNcHOC51uPGF0P/D4NVtrkjSU2fNsm9iog4ZvZJsL3rjoDAzXZhkm2MWt1y+PUdggKAYVoMAIYcs78wJ51Cw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/debug": {
      "version": "4.4.3",
      "resolved": "https://registry.npmjs.org/debug/-/debug-4.4.3.tgz",
      "integrity": "sha512-RGwwWnwQvkVfavKVt22FGLw+xYSdzARwm0ru6DhTVA3umU5hZc28V3kO4stgYryrTlLpuvgI9GiijltAjNbcqA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "ms": "^2.1.3"
      },
      "engines": {
        "node": ">=6.0"
      },
      "peerDependenciesMeta": {
        "supports-color": {
          "optional": true
        }
      }
    },
    "node_modules/decimal.js": {
      "version": "10.6.0",
      "resolved": "https://registry.npmjs.org/decimal.js/-/decimal.js-10.6.0.tgz",
      "integrity": "sha512-YpgQiITW3JXGntzdUmyUR1V812Hn8T1YVXhCu+wO3OpS4eU9l4YdD3qjyiKdV6mvV29zapkMeD390UVEf2lkUg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/deep-is": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/deep-is/-/deep-is-0.1.4.tgz",
      "integrity": "sha512-oIPzksmTg4/MriiaYGO+okXDT7ztn/w3Eptv/+gSIdMdKsJo0u4CfYNFJPy+4SKMuCqGw2wxnA+URMg3t8a/bQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/dequal": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/dequal/-/dequal-2.0.3.tgz",
      "integrity": "sha512-0je+qPKHEMohvfRTCEo3CrPG6cAzAYgmzKyxRiYSSDkS6eGJdyVJm7WaYA5ECaAD9wLB2T4EEeymA5aFVcYXCA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/detect-libc": {
      "version": "2.1.2",
      "resolved": "https://registry.npmjs.org/detect-libc/-/detect-libc-2.1.2.tgz",
      "integrity": "sha512-Btj2BOOO83o3WyH59e8MgXsxEQVcarkUOpEYrubB0urwnN10yQ364rsiByU11nZlqWYZm05i/of7io4mzihBtQ==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/dom-accessibility-api": {
      "version": "0.5.16",
      "resolved": "https://registry.npmjs.org/dom-accessibility-api/-/dom-accessibility-api-0.5.16.tgz",
      "integrity": "sha512-X7BJ2yElsnOJ30pZF4uIIDfBEVgF4XEBxL9Bxhy6dnrm5hkzqmsWHGTiHqRiITNhMyFLyAiWndIJP7Z1NTteDg==",
      "dev": true,
      "license": "MIT",
      "peer": true
    },
    "node_modules/electron-to-chromium": {
      "version": "1.5.321",
      "resolved": "https://registry.npmjs.org/electron-to-chromium/-/electron-to-chromium-1.5.321.tgz",
      "integrity": "sha512-L2C7Q279W2D/J4PLZLk7sebOILDSWos7bMsMNN06rK482umHUrh/3lM8G7IlHFOYip2oAg5nha1rCMxr/rs6ZQ==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/entities": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/entities/-/entities-6.0.1.tgz",
      "integrity": "sha512-aN97NXWF6AWBTahfVOIrB/NShkzi5H7F9r1s9mD3cDj4Ko5f2qhhVoYMibXF7GlLveb/D2ioWay8lxI97Ven3g==",
      "dev": true,
      "license": "BSD-2-Clause",
      "engines": {
        "node": ">=0.12"
      },
      "funding": {
        "url": "https://github.com/fb55/entities?sponsor=1"
      }
    },
    "node_modules/es-module-lexer": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/es-module-lexer/-/es-module-lexer-2.0.0.tgz",
      "integrity": "sha512-5POEcUuZybH7IdmGsD8wlf0AI55wMecM9rVBTI/qEAy2c1kTOm3DjFYjrBdI2K3BaJjJYfYFeRtM0t9ssnRuxw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/escalade": {
      "version": "3.2.0",
      "resolved": "https://registry.npmjs.org/escalade/-/escalade-3.2.0.tgz",
      "integrity": "sha512-WUj2qlxaQtO4g6Pq5c29GTcWGDyd8itL8zTlipgECz3JesAiiOKotd8JU6otB3PACgG6xkJUyVhboMS+bje/jA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/escape-string-regexp": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/escape-string-regexp/-/escape-string-regexp-4.0.0.tgz",
      "integrity": "sha512-TtpcNJ3XAzx3Gq8sWRzJaVajRs0uVxA2YAkdb1jm2YkPz4G6egUFAyA3n5vtEIZefPk5Wa4UXbKuS5fKkJWdgA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/eslint": {
      "version": "9.39.4",
      "resolved": "https://registry.npmjs.org/eslint/-/eslint-9.39.4.tgz",
      "integrity": "sha512-XoMjdBOwe/esVgEvLmNsD3IRHkm7fbKIUGvrleloJXUZgDHig2IPWNniv+GwjyJXzuNqVjlr5+4yVUZjycJwfQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@eslint-community/eslint-utils": "^4.8.0",
        "@eslint-community/regexpp": "^4.12.1",
        "@eslint/config-array": "^0.21.2",
        "@eslint/config-helpers": "^0.4.2",
        "@eslint/core": "^0.17.0",
        "@eslint/eslintrc": "^3.3.5",
        "@eslint/js": "9.39.4",
        "@eslint/plugin-kit": "^0.4.1",
        "@humanfs/node": "^0.16.6",
        "@humanwhocodes/module-importer": "^1.0.1",
        "@humanwhocodes/retry": "^0.4.2",
        "@types/estree": "^1.0.6",
        "ajv": "^6.14.0",
        "chalk": "^4.0.0",
        "cross-spawn": "^7.0.6",
        "debug": "^4.3.2",
        "escape-string-regexp": "^4.0.0",
        "eslint-scope": "^8.4.0",
        "eslint-visitor-keys": "^4.2.1",
        "espree": "^10.4.0",
        "esquery": "^1.5.0",
        "esutils": "^2.0.2",
        "fast-deep-equal": "^3.1.3",
        "file-entry-cache": "^8.0.0",
        "find-up": "^5.0.0",
        "glob-parent": "^6.0.2",
        "ignore": "^5.2.0",
        "imurmurhash": "^0.1.4",
        "is-glob": "^4.0.0",
        "json-stable-stringify-without-jsonify": "^1.0.1",
        "lodash.merge": "^4.6.2",
        "minimatch": "^3.1.5",
        "natural-compare": "^1.4.0",
        "optionator": "^0.9.3"
      },
      "bin": {
        "eslint": "bin/eslint.js"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "url": "https://eslint.org/donate"
      },
      "peerDependencies": {
        "jiti": "*"
      },
      "peerDependenciesMeta": {
        "jiti": {
          "optional": true
        }
      }
    },
    "node_modules/eslint-plugin-react-hooks": {
      "version": "7.0.1",
      "resolved": "https://registry.npmjs.org/eslint-plugin-react-hooks/-/eslint-plugin-react-hooks-7.0.1.tgz",
      "integrity": "sha512-O0d0m04evaNzEPoSW+59Mezf8Qt0InfgGIBJnpC0h3NH/WjUAR7BIKUfysC6todmtiZ/A0oUVS8Gce0WhBrHsA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@babel/core": "^7.24.4",
        "@babel/parser": "^7.24.4",
        "hermes-parser": "^0.25.1",
        "zod": "^3.25.0 || ^4.0.0",
        "zod-validation-error": "^3.5.0 || ^4.0.0"
      },
      "engines": {
        "node": ">=18"
      },
      "peerDependencies": {
        "eslint": "^3.0.0 || ^4.0.0 || ^5.0.0 || ^6.0.0 || ^7.0.0 || ^8.0.0-0 || ^9.0.0"
      }
    },
    "node_modules/eslint-plugin-react-refresh": {
      "version": "0.5.2",
      "resolved": "https://registry.npmjs.org/eslint-plugin-react-refresh/-/eslint-plugin-react-refresh-0.5.2.tgz",
      "integrity": "sha512-hmgTH57GfzoTFjVN0yBwTggnsVUF2tcqi7RJZHqi9lIezSs4eFyAMktA68YD4r5kNw1mxyY4dmkyoFDb3FIqrA==",
      "dev": true,
      "license": "MIT",
      "peerDependencies": {
        "eslint": "^9 || ^10"
      }
    },
    "node_modules/eslint-scope": {
      "version": "8.4.0",
      "resolved": "https://registry.npmjs.org/eslint-scope/-/eslint-scope-8.4.0.tgz",
      "integrity": "sha512-sNXOfKCn74rt8RICKMvJS7XKV/Xk9kA7DyJr8mJik3S7Cwgy3qlkkmyS2uQB3jiJg6VNdZd/pDBJu0nvG2NlTg==",
      "dev": true,
      "license": "BSD-2-Clause",
      "dependencies": {
        "esrecurse": "^4.3.0",
        "estraverse": "^5.2.0"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      }
    },
    "node_modules/eslint-visitor-keys": {
      "version": "4.2.1",
      "resolved": "https://registry.npmjs.org/eslint-visitor-keys/-/eslint-visitor-keys-4.2.1.tgz",
      "integrity": "sha512-Uhdk5sfqcee/9H/rCOJikYz67o0a2Tw2hGRPOG2Y1R2dg7brRe1uG0yaNQDHu+TO/uQPF/5eCapvYSmHUjt7JQ==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      }
    },
    "node_modules/espree": {
      "version": "10.4.0",
      "resolved": "https://registry.npmjs.org/espree/-/espree-10.4.0.tgz",
      "integrity": "sha512-j6PAQ2uUr79PZhBjP5C5fhl8e39FmRnOjsD5lGnWrFU8i2G776tBK7+nP8KuQUTTyAZUwfQqXAgrVH5MbH9CYQ==",
      "dev": true,
      "license": "BSD-2-Clause",
      "dependencies": {
        "acorn": "^8.15.0",
        "acorn-jsx": "^5.3.2",
        "eslint-visitor-keys": "^4.2.1"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "url": "https://opencollective.com/eslint"
      }
    },
    "node_modules/esquery": {
      "version": "1.7.0",
      "resolved": "https://registry.npmjs.org/esquery/-/esquery-1.7.0.tgz",
      "integrity": "sha512-Ap6G0WQwcU/LHsvLwON1fAQX9Zp0A2Y6Y/cJBl9r/JbW90Zyg4/zbG6zzKa2OTALELarYHmKu0GhpM5EO+7T0g==",
      "dev": true,
      "license": "BSD-3-Clause",
      "dependencies": {
        "estraverse": "^5.1.0"
      },
      "engines": {
        "node": ">=0.10"
      }
    },
    "node_modules/esrecurse": {
      "version": "4.3.0",
      "resolved": "https://registry.npmjs.org/esrecurse/-/esrecurse-4.3.0.tgz",
      "integrity": "sha512-KmfKL3b6G+RXvP8N1vr3Tq1kL/oCFgn2NYXEtqP8/L3pKapUA4G8cFVaoF3SU323CD4XypR/ffioHmkti6/Tag==",
      "dev": true,
      "license": "BSD-2-Clause",
      "dependencies": {
        "estraverse": "^5.2.0"
      },
      "engines": {
        "node": ">=4.0"
      }
    },
    "node_modules/estraverse": {
      "version": "5.3.0",
      "resolved": "https://registry.npmjs.org/estraverse/-/estraverse-5.3.0.tgz",
      "integrity": "sha512-MMdARuVEQziNTeJD8DgMqmhwR11BRQ/cBP+pLtYdSTnf3MIO8fFeiINEbX36ZdNlfU/7A9f3gUw49B3oQsvwBA==",
      "dev": true,
      "license": "BSD-2-Clause",
      "engines": {
        "node": ">=4.0"
      }
    },
    "node_modules/estree-walker": {
      "version": "3.0.3",
      "resolved": "https://registry.npmjs.org/estree-walker/-/estree-walker-3.0.3.tgz",
      "integrity": "sha512-7RUKfXgSMMkzt6ZuXmqapOurLGPPfgj6l9uRZ7lRGolvk0y2yocc35LdcxKC5PQZdn2DMqioAQ2NoWcrTKmm6g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@types/estree": "^1.0.0"
      }
    },
    "node_modules/esutils": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/esutils/-/esutils-2.0.3.tgz",
      "integrity": "sha512-kVscqXk4OCp68SZ0dkgEKVi6/8ij300KBWTJq32P/dYeWTSwK41WyTxalN1eRmA5Z9UU/LX9D7FWSmV9SAYx6g==",
      "dev": true,
      "license": "BSD-2-Clause",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/expect-type": {
      "version": "1.3.0",
      "resolved": "https://registry.npmjs.org/expect-type/-/expect-type-1.3.0.tgz",
      "integrity": "sha512-knvyeauYhqjOYvQ66MznSMs83wmHrCycNEN6Ao+2AeYEfxUIkuiVxdEa1qlGEPK+We3n0THiDciYSsCcgW/DoA==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=12.0.0"
      }
    },
    "node_modules/fast-deep-equal": {
      "version": "3.1.3",
      "resolved": "https://registry.npmjs.org/fast-deep-equal/-/fast-deep-equal-3.1.3.tgz",
      "integrity": "sha512-f3qQ9oQy9j2AhBe/H9VC91wLmKBCCU/gDOnKNAYG5hswO7BLKj09Hc5HYNz9cGI++xlpDCIgDaitVs03ATR84Q==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/fast-json-stable-stringify": {
      "version": "2.1.0",
      "resolved": "https://registry.npmjs.org/fast-json-stable-stringify/-/fast-json-stable-stringify-2.1.0.tgz",
      "integrity": "sha512-lhd/wF+Lk98HZoTCtlVraHtfh5XYijIjalXck7saUtuanSDyLMxnHhSXEDJqHxD7msR8D0uCmqlkwjCV8xvwHw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/fast-levenshtein": {
      "version": "2.0.6",
      "resolved": "https://registry.npmjs.org/fast-levenshtein/-/fast-levenshtein-2.0.6.tgz",
      "integrity": "sha512-DCXu6Ifhqcks7TZKY3Hxp3y6qphY5SJZmrWMDrKcERSOXWQdMhU9Ig/PYrzyw/ul9jOIyh0N4M0tbC5hodg8dw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/fdir": {
      "version": "6.5.0",
      "resolved": "https://registry.npmjs.org/fdir/-/fdir-6.5.0.tgz",
      "integrity": "sha512-tIbYtZbucOs0BRGqPJkshJUYdL+SDH7dVM8gjy+ERp3WAUjLEFJE+02kanyHtwjWOnwrKYBiwAmM0p4kLJAnXg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=12.0.0"
      },
      "peerDependencies": {
        "picomatch": "^3 || ^4"
      },
      "peerDependenciesMeta": {
        "picomatch": {
          "optional": true
        }
      }
    },
    "node_modules/file-entry-cache": {
      "version": "8.0.0",
      "resolved": "https://registry.npmjs.org/file-entry-cache/-/file-entry-cache-8.0.0.tgz",
      "integrity": "sha512-XXTUwCvisa5oacNGRP9SfNtYBNAMi+RPwBFmblZEF7N7swHYQS6/Zfk7SRwx4D5j3CH211YNRco1DEMNVfZCnQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "flat-cache": "^4.0.0"
      },
      "engines": {
        "node": ">=16.0.0"
      }
    },
    "node_modules/find-up": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/find-up/-/find-up-5.0.0.tgz",
      "integrity": "sha512-78/PXT1wlLLDgTzDs7sjq9hzz0vXD+zn+7wypEe4fXQxCmdmqfGsEPQxmiCSQI3ajFV91bVSsvNtrJRiW6nGng==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "locate-path": "^6.0.0",
        "path-exists": "^4.0.0"
      },
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/flat-cache": {
      "version": "4.0.1",
      "resolved": "https://registry.npmjs.org/flat-cache/-/flat-cache-4.0.1.tgz",
      "integrity": "sha512-f7ccFPK3SXFHpx15UIGyRJ/FJQctuKZ0zVuN3frBo4HnK3cay9VEW0R6yPYFHC0AgqhukPzKjq22t5DmAyqGyw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "flatted": "^3.2.9",
        "keyv": "^4.5.4"
      },
      "engines": {
        "node": ">=16"
      }
    },
    "node_modules/flatted": {
      "version": "3.4.2",
      "resolved": "https://registry.npmjs.org/flatted/-/flatted-3.4.2.tgz",
      "integrity": "sha512-PjDse7RzhcPkIJwy5t7KPWQSZ9cAbzQXcafsetQoD7sOJRQlGikNbx7yZp2OotDnJyrDcbyRq3Ttb18iYOqkxA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/fsevents": {
      "version": "2.3.3",
      "resolved": "https://registry.npmjs.org/fsevents/-/fsevents-2.3.3.tgz",
      "integrity": "sha512-5xoDfX+fL7faATnagmWPpbFtwh/R77WmMMqqHGS65C3vvB0YHrgF+B1YmZ3441tMj5n63k0212XNoJwzlhffQw==",
      "dev": true,
      "hasInstallScript": true,
      "license": "MIT",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": "^8.16.0 || ^10.6.0 || >=11.0.0"
      }
    },
    "node_modules/gensync": {
      "version": "1.0.0-beta.2",
      "resolved": "https://registry.npmjs.org/gensync/-/gensync-1.0.0-beta.2.tgz",
      "integrity": "sha512-3hN7NaskYvMDLQY55gnW3NQ+mesEAepTqlg+VEbj7zzqEMBVNhzcGYYeqFo/TlYz6eQiFcp1HcsCZO+nGgS8zg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6.9.0"
      }
    },
    "node_modules/glob-parent": {
      "version": "6.0.2",
      "resolved": "https://registry.npmjs.org/glob-parent/-/glob-parent-6.0.2.tgz",
      "integrity": "sha512-XxwI8EOhVQgWp6iDL+3b0r86f4d6AX6zSU55HfB4ydCEuXLXc5FcYeOu+nnGftS4TEju/11rt4KJPTMgbfmv4A==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "is-glob": "^4.0.3"
      },
      "engines": {
        "node": ">=10.13.0"
      }
    },
    "node_modules/globals": {
      "version": "17.4.0",
      "resolved": "https://registry.npmjs.org/globals/-/globals-17.4.0.tgz",
      "integrity": "sha512-hjrNztw/VajQwOLsMNT1cbJiH2muO3OROCHnbehc8eY5JyD2gqz4AcMHPqgaOR59DjgUjYAYLeH699g/eWi2jw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/has-flag": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/has-flag/-/has-flag-4.0.0.tgz",
      "integrity": "sha512-EykJT/Q1KjTWctppgIAgfSO0tKVuZUjhgMr17kqTumMl6Afv3EISleU7qZUzoXDFTAHTDC4NOoG/ZxU3EvlMPQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/hermes-estree": {
      "version": "0.25.1",
      "resolved": "https://registry.npmjs.org/hermes-estree/-/hermes-estree-0.25.1.tgz",
      "integrity": "sha512-0wUoCcLp+5Ev5pDW2OriHC2MJCbwLwuRx+gAqMTOkGKJJiBCLjtrvy4PWUGn6MIVefecRpzoOZ/UV6iGdOr+Cw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/hermes-parser": {
      "version": "0.25.1",
      "resolved": "https://registry.npmjs.org/hermes-parser/-/hermes-parser-0.25.1.tgz",
      "integrity": "sha512-6pEjquH3rqaI6cYAXYPcz9MS4rY6R4ngRgrgfDshRptUZIc3lw0MCIJIGDj9++mfySOuPTHB4nrSW99BCvOPIA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "hermes-estree": "0.25.1"
      }
    },
    "node_modules/html-encoding-sniffer": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/html-encoding-sniffer/-/html-encoding-sniffer-6.0.0.tgz",
      "integrity": "sha512-CV9TW3Y3f8/wT0BRFc1/KAVQ3TUHiXmaAb6VW9vtiMFf7SLoMd1PdAc4W3KFOFETBJUb90KatHqlsZMWV+R9Gg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@exodus/bytes": "^1.6.0"
      },
      "engines": {
        "node": "^20.19.0 || ^22.12.0 || >=24.0.0"
      }
    },
    "node_modules/http-proxy-agent": {
      "version": "7.0.2",
      "resolved": "https://registry.npmjs.org/http-proxy-agent/-/http-proxy-agent-7.0.2.tgz",
      "integrity": "sha512-T1gkAiYYDWYx3V5Bmyu7HcfcvL7mUrTWiM6yOfa3PIphViJ/gFPbvidQ+veqSOHci/PxBcDabeUNCzpOODJZig==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "agent-base": "^7.1.0",
        "debug": "^4.3.4"
      },
      "engines": {
        "node": ">= 14"
      }
    },
    "node_modules/https-proxy-agent": {
      "version": "7.0.6",
      "resolved": "https://registry.npmjs.org/https-proxy-agent/-/https-proxy-agent-7.0.6.tgz",
      "integrity": "sha512-vK9P5/iUfdl95AI+JVyUuIcVtd4ofvtrOr3HNtM2yxC9bnMbEdp3x01OhQNnjb8IJYi38VlTE3mBXwcfvywuSw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "agent-base": "^7.1.2",
        "debug": "4"
      },
      "engines": {
        "node": ">= 14"
      }
    },
    "node_modules/ignore": {
      "version": "5.3.2",
      "resolved": "https://registry.npmjs.org/ignore/-/ignore-5.3.2.tgz",
      "integrity": "sha512-hsBTNUqQTDwkWtcdYI2i06Y/nUBEsNEDJKjWdigLvegy8kDuJAS8uRlpkkcQpyEXL0Z/pjDy5HBmMjRCJ2gq+g==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">= 4"
      }
    },
    "node_modules/import-fresh": {
      "version": "3.3.1",
      "resolved": "https://registry.npmjs.org/import-fresh/-/import-fresh-3.3.1.tgz",
      "integrity": "sha512-TR3KfrTZTYLPB6jUjfx6MF9WcWrHL9su5TObK4ZkYgBdWKPOFoSoQIdEuTuR82pmtxH2spWG9h6etwfr1pLBqQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "parent-module": "^1.0.0",
        "resolve-from": "^4.0.0"
      },
      "engines": {
        "node": ">=6"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/imurmurhash": {
      "version": "0.1.4",
      "resolved": "https://registry.npmjs.org/imurmurhash/-/imurmurhash-0.1.4.tgz",
      "integrity": "sha512-JmXMZ6wuvDmLiHEml9ykzqO6lwFbof0GG4IkcGaENdCRDDmMVnny7s5HsIgHCbaq0w2MyPhDqkhTUgS2LU2PHA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.8.19"
      }
    },
    "node_modules/indent-string": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/indent-string/-/indent-string-4.0.0.tgz",
      "integrity": "sha512-EdDDZu4A2OyIK7Lr/2zG+w5jmbuk1DVBnEwREQvBzspBJkCEbRa8GxU1lghYcaGJCnRWibjDXlq779X1/y5xwg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/is-extglob": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/is-extglob/-/is-extglob-2.1.1.tgz",
      "integrity": "sha512-SbKbANkN603Vi4jEZv49LeVJMn4yGwsbzZworEoyEiutsN3nJYdbO36zfhGJ6QEDpOZIFkDtnq5JRxmvl3jsoQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/is-glob": {
      "version": "4.0.3",
      "resolved": "https://registry.npmjs.org/is-glob/-/is-glob-4.0.3.tgz",
      "integrity": "sha512-xelSayHH36ZgE7ZWhli7pW34hNbNl8Ojv5KVmkJD4hBdD3th8Tfk9vYasLM+mXWOZhFkgZfxhLSnrwRr4elSSg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "is-extglob": "^2.1.1"
      },
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/is-potential-custom-element-name": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/is-potential-custom-element-name/-/is-potential-custom-element-name-1.0.1.tgz",
      "integrity": "sha512-bCYeRA2rVibKZd+s2625gGnGF/t7DSqDs4dP7CrLA1m7jKWz6pps0LpYLJN8Q64HtmPKJ1hrN3nzPNKFEKOUiQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/isexe": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/isexe/-/isexe-2.0.0.tgz",
      "integrity": "sha512-RHxMLp9lnKHGHRng9QFhRCMbYAcVpn69smSGcq3f36xjgVVWThj4qqLbTLlq7Ssj8B+fIQ1EuCEGI2lKsyQeIw==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/js-tokens": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/js-tokens/-/js-tokens-4.0.0.tgz",
      "integrity": "sha512-RdJUflcE3cUzKiMqQgsCu06FPu9UdIJO0beYbPhHN4k6apgJtifcoCtT9bcxOpYBtpD2kCM6Sbzg4CausW/PKQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/js-yaml": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/js-yaml/-/js-yaml-4.1.1.tgz",
      "integrity": "sha512-qQKT4zQxXl8lLwBtHMWwaTcGfFOZviOJet3Oy/xmGk2gZH677CJM9EvtfdSkgWcATZhj/55JZ0rmy3myCT5lsA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "argparse": "^2.0.1"
      },
      "bin": {
        "js-yaml": "bin/js-yaml.js"
      }
    },
    "node_modules/jsdom": {
      "version": "27.4.0",
      "resolved": "https://registry.npmjs.org/jsdom/-/jsdom-27.4.0.tgz",
      "integrity": "sha512-mjzqwWRD9Y1J1KUi7W97Gja1bwOOM5Ug0EZ6UDK3xS7j7mndrkwozHtSblfomlzyB4NepioNt+B2sOSzczVgtQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@acemir/cssom": "^0.9.28",
        "@asamuzakjp/dom-selector": "^6.7.6",
        "@exodus/bytes": "^1.6.0",
        "cssstyle": "^5.3.4",
        "data-urls": "^6.0.0",
        "decimal.js": "^10.6.0",
        "html-encoding-sniffer": "^6.0.0",
        "http-proxy-agent": "^7.0.2",
        "https-proxy-agent": "^7.0.6",
        "is-potential-custom-element-name": "^1.0.1",
        "parse5": "^8.0.0",
        "saxes": "^6.0.0",
        "symbol-tree": "^3.2.4",
        "tough-cookie": "^6.0.0",
        "w3c-xmlserializer": "^5.0.0",
        "webidl-conversions": "^8.0.0",
        "whatwg-mimetype": "^4.0.0",
        "whatwg-url": "^15.1.0",
        "ws": "^8.18.3",
        "xml-name-validator": "^5.0.0"
      },
      "engines": {
        "node": "^20.19.0 || ^22.12.0 || >=24.0.0"
      },
      "peerDependencies": {
        "canvas": "^3.0.0"
      },
      "peerDependenciesMeta": {
        "canvas": {
          "optional": true
        }
      }
    },
    "node_modules/jsesc": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/jsesc/-/jsesc-3.1.0.tgz",
      "integrity": "sha512-/sM3dO2FOzXjKQhJuo0Q173wf2KOo8t4I8vHy6lF9poUp7bKT0/NHE8fPX23PwfhnykfqnC2xRxOnVw5XuGIaA==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "jsesc": "bin/jsesc"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/json-buffer": {
      "version": "3.0.1",
      "resolved": "https://registry.npmjs.org/json-buffer/-/json-buffer-3.0.1.tgz",
      "integrity": "sha512-4bV5BfR2mqfQTJm+V5tPPdf+ZpuhiIvTuAB5g8kcrXOZpTT/QwwVRWBywX1ozr6lEuPdbHxwaJlm9G6mI2sfSQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/json-schema-traverse": {
      "version": "0.4.1",
      "resolved": "https://registry.npmjs.org/json-schema-traverse/-/json-schema-traverse-0.4.1.tgz",
      "integrity": "sha512-xbbCH5dCYU5T8LcEhhuh7HJ88HXuW3qsI3Y0zOZFKfZEHcpWiHU/Jxzk629Brsab/mMiHQti9wMP+845RPe3Vg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/json-stable-stringify-without-jsonify": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/json-stable-stringify-without-jsonify/-/json-stable-stringify-without-jsonify-1.0.1.tgz",
      "integrity": "sha512-Bdboy+l7tA3OGW6FjyFHWkP5LuByj1Tk33Ljyq0axyzdk9//JSi2u3fP1QSmd1KNwq6VOKYGlAu87CisVir6Pw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/json5": {
      "version": "2.2.3",
      "resolved": "https://registry.npmjs.org/json5/-/json5-2.2.3.tgz",
      "integrity": "sha512-XmOWe7eyHYH14cLdVPoyg+GOH3rYX++KpzrylJwSW98t3Nk+U8XOl8FWKOgwtzdb8lXGf6zYwDUzeHMWfxasyg==",
      "dev": true,
      "license": "MIT",
      "bin": {
        "json5": "lib/cli.js"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/keyv": {
      "version": "4.5.4",
      "resolved": "https://registry.npmjs.org/keyv/-/keyv-4.5.4.tgz",
      "integrity": "sha512-oxVHkHR/EJf2CNXnWxRLW6mg7JyCCUcG0DtEGmL2ctUo1PNTin1PUil+r/+4r5MpVgC/fn1kjsx7mjSujKqIpw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "json-buffer": "3.0.1"
      }
    },
    "node_modules/levn": {
      "version": "0.4.1",
      "resolved": "https://registry.npmjs.org/levn/-/levn-0.4.1.tgz",
      "integrity": "sha512-+bT2uH4E5LGE7h/n3evcS/sQlJXCpIp6ym8OWJ5eV6+67Dsql/LaaT7qJBAt2rzfoa/5QBGBhxDix1dMt2kQKQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "prelude-ls": "^1.2.1",
        "type-check": "~0.4.0"
      },
      "engines": {
        "node": ">= 0.8.0"
      }
    },
    "node_modules/lightningcss": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss/-/lightningcss-1.32.0.tgz",
      "integrity": "sha512-NXYBzinNrblfraPGyrbPoD19C1h9lfI/1mzgWYvXUTe414Gz/X1FD2XBZSZM7rRTrMA8JL3OtAaGifrIKhQ5yQ==",
      "dev": true,
      "license": "MPL-2.0",
      "dependencies": {
        "detect-libc": "^2.0.3"
      },
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      },
      "optionalDependencies": {
        "lightningcss-android-arm64": "1.32.0",
        "lightningcss-darwin-arm64": "1.32.0",
        "lightningcss-darwin-x64": "1.32.0",
        "lightningcss-freebsd-x64": "1.32.0",
        "lightningcss-linux-arm-gnueabihf": "1.32.0",
        "lightningcss-linux-arm64-gnu": "1.32.0",
        "lightningcss-linux-arm64-musl": "1.32.0",
        "lightningcss-linux-x64-gnu": "1.32.0",
        "lightningcss-linux-x64-musl": "1.32.0",
        "lightningcss-win32-arm64-msvc": "1.32.0",
        "lightningcss-win32-x64-msvc": "1.32.0"
      }
    },
    "node_modules/lightningcss-android-arm64": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-android-arm64/-/lightningcss-android-arm64-1.32.0.tgz",
      "integrity": "sha512-YK7/ClTt4kAK0vo6w3X+Pnm0D2cf2vPHbhOXdoNti1Ga0al1P4TBZhwjATvjNwLEBCnKvjJc2jQgHXH0NEwlAg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "android"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-darwin-arm64": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-darwin-arm64/-/lightningcss-darwin-arm64-1.32.0.tgz",
      "integrity": "sha512-RzeG9Ju5bag2Bv1/lwlVJvBE3q6TtXskdZLLCyfg5pt+HLz9BqlICO7LZM7VHNTTn/5PRhHFBSjk5lc4cmscPQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-darwin-x64": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-darwin-x64/-/lightningcss-darwin-x64-1.32.0.tgz",
      "integrity": "sha512-U+QsBp2m/s2wqpUYT/6wnlagdZbtZdndSmut/NJqlCcMLTWp5muCrID+K5UJ6jqD2BFshejCYXniPDbNh73V8w==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "darwin"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-freebsd-x64": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-freebsd-x64/-/lightningcss-freebsd-x64-1.32.0.tgz",
      "integrity": "sha512-JCTigedEksZk3tHTTthnMdVfGf61Fky8Ji2E4YjUTEQX14xiy/lTzXnu1vwiZe3bYe0q+SpsSH/CTeDXK6WHig==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "freebsd"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-linux-arm-gnueabihf": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-linux-arm-gnueabihf/-/lightningcss-linux-arm-gnueabihf-1.32.0.tgz",
      "integrity": "sha512-x6rnnpRa2GL0zQOkt6rts3YDPzduLpWvwAF6EMhXFVZXD4tPrBkEFqzGowzCsIWsPjqSK+tyNEODUBXeeVHSkw==",
      "cpu": [
        "arm"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-linux-arm64-gnu": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-linux-arm64-gnu/-/lightningcss-linux-arm64-gnu-1.32.0.tgz",
      "integrity": "sha512-0nnMyoyOLRJXfbMOilaSRcLH3Jw5z9HDNGfT/gwCPgaDjnx0i8w7vBzFLFR1f6CMLKF8gVbebmkUN3fa/kQJpQ==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-linux-arm64-musl": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-linux-arm64-musl/-/lightningcss-linux-arm64-musl-1.32.0.tgz",
      "integrity": "sha512-UpQkoenr4UJEzgVIYpI80lDFvRmPVg6oqboNHfoH4CQIfNA+HOrZ7Mo7KZP02dC6LjghPQJeBsvXhJod/wnIBg==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-linux-x64-gnu": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-linux-x64-gnu/-/lightningcss-linux-x64-gnu-1.32.0.tgz",
      "integrity": "sha512-V7Qr52IhZmdKPVr+Vtw8o+WLsQJYCTd8loIfpDaMRWGUZfBOYEJeyJIkqGIDMZPwPx24pUMfwSxxI8phr/MbOA==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-linux-x64-musl": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-linux-x64-musl/-/lightningcss-linux-x64-musl-1.32.0.tgz",
      "integrity": "sha512-bYcLp+Vb0awsiXg/80uCRezCYHNg1/l3mt0gzHnWV9XP1W5sKa5/TCdGWaR/zBM2PeF/HbsQv/j2URNOiVuxWg==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "linux"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-win32-arm64-msvc": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-win32-arm64-msvc/-/lightningcss-win32-arm64-msvc-1.32.0.tgz",
      "integrity": "sha512-8SbC8BR40pS6baCM8sbtYDSwEVQd4JlFTOlaD3gWGHfThTcABnNDBda6eTZeqbofalIJhFx0qKzgHJmcPTnGdw==",
      "cpu": [
        "arm64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/lightningcss-win32-x64-msvc": {
      "version": "1.32.0",
      "resolved": "https://registry.npmjs.org/lightningcss-win32-x64-msvc/-/lightningcss-win32-x64-msvc-1.32.0.tgz",
      "integrity": "sha512-Amq9B/SoZYdDi1kFrojnoqPLxYhQ4Wo5XiL8EVJrVsB8ARoC1PWW6VGtT0WKCemjy8aC+louJnjS7U18x3b06Q==",
      "cpu": [
        "x64"
      ],
      "dev": true,
      "license": "MPL-2.0",
      "optional": true,
      "os": [
        "win32"
      ],
      "engines": {
        "node": ">= 12.0.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/parcel"
      }
    },
    "node_modules/locate-path": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/locate-path/-/locate-path-6.0.0.tgz",
      "integrity": "sha512-iPZK6eYjbxRu3uB4/WZ3EsEIMJFMqAoopl3R+zuq0UjcAm/MO6KCweDgPfP3elTztoKP3KtnVHxTn2NHBSDVUw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "p-locate": "^5.0.0"
      },
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/lodash.merge": {
      "version": "4.6.2",
      "resolved": "https://registry.npmjs.org/lodash.merge/-/lodash.merge-4.6.2.tgz",
      "integrity": "sha512-0KpjqXRVvrYyCsX1swR/XTK0va6VQkQM6MNo7PqW77ByjAhoARA8EfrP1N4+KlKj8YS0ZUCtRT/YUuhyYDujIQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/lru-cache": {
      "version": "5.1.1",
      "resolved": "https://registry.npmjs.org/lru-cache/-/lru-cache-5.1.1.tgz",
      "integrity": "sha512-KpNARQA3Iwv+jTA0utUVVbrh+Jlrr1Fv0e56GGzAFOXN7dk/FviaDW8LHmK52DlcH4WP2n6gI8vN1aesBFgo9w==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "yallist": "^3.0.2"
      }
    },
    "node_modules/lucide-react": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/lucide-react/-/lucide-react-1.0.1.tgz",
      "integrity": "sha512-lih7tKEczCYOQjVEzpFuxEuNzlwf+1yhvlMlEkGWJM3va8Pugv8bYXc/pRtcjPncaP7k84X0Pt/71ufxvqEPtQ==",
      "license": "ISC",
      "peerDependencies": {
        "react": "^16.5.1 || ^17.0.0 || ^18.0.0 || ^19.0.0"
      }
    },
    "node_modules/lz-string": {
      "version": "1.5.0",
      "resolved": "https://registry.npmjs.org/lz-string/-/lz-string-1.5.0.tgz",
      "integrity": "sha512-h5bgJWpxJNswbU7qCrV0tIKQCaS3blPDrqKWx+QxzuzL1zGUzij9XCWLrSLsJPu5t+eWA/ycetzYAO5IOMcWAQ==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "bin": {
        "lz-string": "bin/bin.js"
      }
    },
    "node_modules/magic-string": {
      "version": "0.30.21",
      "resolved": "https://registry.npmjs.org/magic-string/-/magic-string-0.30.21.tgz",
      "integrity": "sha512-vd2F4YUyEXKGcLHoq+TEyCjxueSeHnFxyyjNp80yg0XV4vUhnDer/lvvlqM/arB5bXQN5K2/3oinyCRyx8T2CQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@jridgewell/sourcemap-codec": "^1.5.5"
      }
    },
    "node_modules/mdn-data": {
      "version": "2.27.1",
      "resolved": "https://registry.npmjs.org/mdn-data/-/mdn-data-2.27.1.tgz",
      "integrity": "sha512-9Yubnt3e8A0OKwxYSXyhLymGW4sCufcLG6VdiDdUGVkPhpqLxlvP5vl1983gQjJl3tqbrM731mjaZaP68AgosQ==",
      "dev": true,
      "license": "CC0-1.0"
    },
    "node_modules/min-indent": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/min-indent/-/min-indent-1.0.1.tgz",
      "integrity": "sha512-I9jwMn07Sy/IwOj3zVkVik2JTvgpaykDZEigL6Rx6N9LbMywwUSMtxET+7lVoDLLd3O3IXwJwvuuns8UB/HeAg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=4"
      }
    },
    "node_modules/minimatch": {
      "version": "3.1.5",
      "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-3.1.5.tgz",
      "integrity": "sha512-VgjWUsnnT6n+NUk6eZq77zeFdpW2LWDzP6zFGrCbHXiYNul5Dzqk2HHQ5uFH2DNW5Xbp8+jVzaeNt94ssEEl4w==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "brace-expansion": "^1.1.7"
      },
      "engines": {
        "node": "*"
      }
    },
    "node_modules/ms": {
      "version": "2.1.3",
      "resolved": "https://registry.npmjs.org/ms/-/ms-2.1.3.tgz",
      "integrity": "sha512-6FlzubTLZG3J2a/NVCAleEhjzq5oxgHyaCU9yYXvcLsvoVaHJq/s5xXI6/XXP6tz7R9xAOtHnSO/tXtF3WRTlA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/nanoid": {
      "version": "3.3.11",
      "resolved": "https://registry.npmjs.org/nanoid/-/nanoid-3.3.11.tgz",
      "integrity": "sha512-N8SpfPUnUp1bK+PMYW8qSWdl9U+wwNWI4QKxOYDy9JAro3WMX7p2OeVRF9v+347pnakNevPmiHhNmZ2HbFA76w==",
      "dev": true,
      "funding": [
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "bin": {
        "nanoid": "bin/nanoid.cjs"
      },
      "engines": {
        "node": "^10 || ^12 || ^13.7 || ^14 || >=15.0.1"
      }
    },
    "node_modules/natural-compare": {
      "version": "1.4.0",
      "resolved": "https://registry.npmjs.org/natural-compare/-/natural-compare-1.4.0.tgz",
      "integrity": "sha512-OWND8ei3VtNC9h7V60qff3SVobHr996CTwgxubgyQYEpg290h9J0buyECNNJexkFm5sOajh5G116RYA1c8ZMSw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/node-releases": {
      "version": "2.0.36",
      "resolved": "https://registry.npmjs.org/node-releases/-/node-releases-2.0.36.tgz",
      "integrity": "sha512-TdC8FSgHz8Mwtw9g5L4gR/Sh9XhSP/0DEkQxfEFXOpiul5IiHgHan2VhYYb6agDSfp4KuvltmGApc8HMgUrIkA==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/obug": {
      "version": "2.1.1",
      "resolved": "https://registry.npmjs.org/obug/-/obug-2.1.1.tgz",
      "integrity": "sha512-uTqF9MuPraAQ+IsnPf366RG4cP9RtUi7MLO1N3KEc+wb0a6yKpeL0lmk2IB1jY5KHPAlTc6T/JRdC/YqxHNwkQ==",
      "dev": true,
      "funding": [
        "https://github.com/sponsors/sxzz",
        "https://opencollective.com/debug"
      ],
      "license": "MIT"
    },
    "node_modules/optionator": {
      "version": "0.9.4",
      "resolved": "https://registry.npmjs.org/optionator/-/optionator-0.9.4.tgz",
      "integrity": "sha512-6IpQ7mKUxRcZNLIObR0hz7lxsapSSIYNZJwXPGeF0mTVqGKFIXj1DQcMoT22S3ROcLyY/rz0PWaWZ9ayWmad9g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "deep-is": "^0.1.3",
        "fast-levenshtein": "^2.0.6",
        "levn": "^0.4.1",
        "prelude-ls": "^1.2.1",
        "type-check": "^0.4.0",
        "word-wrap": "^1.2.5"
      },
      "engines": {
        "node": ">= 0.8.0"
      }
    },
    "node_modules/p-limit": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/p-limit/-/p-limit-3.1.0.tgz",
      "integrity": "sha512-TYOanM3wGwNGsZN2cVTYPArw454xnXj5qmWF1bEoAc4+cU/ol7GVh7odevjp1FNHduHc3KZMcFduxU5Xc6uJRQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "yocto-queue": "^0.1.0"
      },
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/p-locate": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/p-locate/-/p-locate-5.0.0.tgz",
      "integrity": "sha512-LaNjtRWUBY++zB5nE/NwcaoMylSPk+S+ZHNB1TzdbMJMny6dynpAGt7X/tl/QYq3TIeE6nxHppbo2LGymrG5Pw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "p-limit": "^3.0.2"
      },
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/parent-module": {
      "version": "1.0.1",
      "resolved": "https://registry.npmjs.org/parent-module/-/parent-module-1.0.1.tgz",
      "integrity": "sha512-GQ2EWRpQV8/o+Aw8YqtfZZPfNRWZYkbidE9k5rpl/hC3vtHHBfGm2Ifi6qWV+coDGkrUKZAxE3Lot5kcsRlh+g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "callsites": "^3.0.0"
      },
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/parse5": {
      "version": "8.0.0",
      "resolved": "https://registry.npmjs.org/parse5/-/parse5-8.0.0.tgz",
      "integrity": "sha512-9m4m5GSgXjL4AjumKzq1Fgfp3Z8rsvjRNbnkVwfu2ImRqE5D0LnY2QfDen18FSY9C573YU5XxSapdHZTZ2WolA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "entities": "^6.0.0"
      },
      "funding": {
        "url": "https://github.com/inikulin/parse5?sponsor=1"
      }
    },
    "node_modules/path-exists": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/path-exists/-/path-exists-4.0.0.tgz",
      "integrity": "sha512-ak9Qy5Q7jYb2Wwcey5Fpvg2KoAc/ZIhLSLOSBmRmygPsGwkVVt0fZa0qrtMz+m6tJTAHfZQ8FnmB4MG4LWy7/w==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/path-key": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/path-key/-/path-key-3.1.1.tgz",
      "integrity": "sha512-ojmeN0qd+y0jszEtoY48r0Peq5dwMEkIlCOu6Q5f41lfkswXuKtYrhgoTpLnyIcHm24Uhqx+5Tqm2InSwLhE6Q==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/pathe": {
      "version": "2.0.3",
      "resolved": "https://registry.npmjs.org/pathe/-/pathe-2.0.3.tgz",
      "integrity": "sha512-WUjGcAqP1gQacoQe+OBJsFA7Ld4DyXuUIjZ5cc75cLHvJ7dtNsTugphxIADwspS+AraAUePCKrSVtPLFj/F88w==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/picocolors": {
      "version": "1.1.1",
      "resolved": "https://registry.npmjs.org/picocolors/-/picocolors-1.1.1.tgz",
      "integrity": "sha512-xceH2snhtb5M9liqDsmEw56le376mTZkEX/jEb/RxNFyegNul7eNslCXP9FDj/Lcu0X8KEyMceP2ntpaHrDEVA==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/picomatch": {
      "version": "4.0.4",
      "resolved": "https://registry.npmjs.org/picomatch/-/picomatch-4.0.4.tgz",
      "integrity": "sha512-QP88BAKvMam/3NxH6vj2o21R6MjxZUAd6nlwAS/pnGvN9IVLocLHxGYIzFhg6fUQ+5th6P4dv4eW9jX3DSIj7A==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=12"
      },
      "funding": {
        "url": "https://github.com/sponsors/jonschlinkert"
      }
    },
    "node_modules/postcss": {
      "version": "8.5.8",
      "resolved": "https://registry.npmjs.org/postcss/-/postcss-8.5.8.tgz",
      "integrity": "sha512-OW/rX8O/jXnm82Ey1k44pObPtdblfiuWnrd8X7GJ7emImCOstunGbXUpp7HdBrFQX6rJzn3sPT397Wp5aCwCHg==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/postcss/"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/postcss"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "nanoid": "^3.3.11",
        "picocolors": "^1.1.1",
        "source-map-js": "^1.2.1"
      },
      "engines": {
        "node": "^10 || ^12 || >=14"
      }
    },
    "node_modules/prelude-ls": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/prelude-ls/-/prelude-ls-1.2.1.tgz",
      "integrity": "sha512-vkcDPrRZo1QZLbn5RLGPpg/WmIQ65qoWWhcGKf/b5eplkkarX0m9z8ppCat4mlOqUsWpyNuYgO3VRyrYHSzX5g==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">= 0.8.0"
      }
    },
    "node_modules/pretty-format": {
      "version": "27.5.1",
      "resolved": "https://registry.npmjs.org/pretty-format/-/pretty-format-27.5.1.tgz",
      "integrity": "sha512-Qb1gy5OrP5+zDf2Bvnzdl3jsTf1qXVMazbvCoKhtKqVs4/YK4ozX4gKQJJVyNe+cajNPn0KoC0MC3FUmaHWEmQ==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "dependencies": {
        "ansi-regex": "^5.0.1",
        "ansi-styles": "^5.0.0",
        "react-is": "^17.0.1"
      },
      "engines": {
        "node": "^10.13.0 || ^12.13.0 || ^14.15.0 || >=15.0.0"
      }
    },
    "node_modules/pretty-format/node_modules/ansi-styles": {
      "version": "5.2.0",
      "resolved": "https://registry.npmjs.org/ansi-styles/-/ansi-styles-5.2.0.tgz",
      "integrity": "sha512-Cxwpt2SfTzTtXcfOlzGEee8O+c+MmUgGrNiBcXnuWxuFJHe6a5Hz7qwhwe5OgaSYI0IJvkLqWX1ASG+cJOkEiA==",
      "dev": true,
      "license": "MIT",
      "peer": true,
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/chalk/ansi-styles?sponsor=1"
      }
    },
    "node_modules/punycode": {
      "version": "2.3.1",
      "resolved": "https://registry.npmjs.org/punycode/-/punycode-2.3.1.tgz",
      "integrity": "sha512-vYt7UD1U9Wg6138shLtLOvdAu+8DsC/ilFtEVHcH+wydcSpNE20AfSOduf6MkRFahL5FY7X1oU7nKVZFtfq8Fg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=6"
      }
    },
    "node_modules/react": {
      "version": "19.2.4",
      "resolved": "https://registry.npmjs.org/react/-/react-19.2.4.tgz",
      "integrity": "sha512-9nfp2hYpCwOjAN+8TZFGhtWEwgvWHXqESH8qT89AT/lWklpLON22Lc8pEtnpsZz7VmawabSU0gCjnj8aC0euHQ==",
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/react-dom": {
      "version": "19.2.4",
      "resolved": "https://registry.npmjs.org/react-dom/-/react-dom-19.2.4.tgz",
      "integrity": "sha512-AXJdLo8kgMbimY95O2aKQqsz2iWi9jMgKJhRBAxECE4IFxfcazB2LmzloIoibJI3C12IlY20+KFaLv+71bUJeQ==",
      "license": "MIT",
      "dependencies": {
        "scheduler": "^0.27.0"
      },
      "peerDependencies": {
        "react": "^19.2.4"
      }
    },
    "node_modules/react-is": {
      "version": "17.0.2",
      "resolved": "https://registry.npmjs.org/react-is/-/react-is-17.0.2.tgz",
      "integrity": "sha512-w2GsyukL62IJnlaff/nRegPQR94C/XXamvMWmSHRJ4y7Ts/4ocGRmTHvOs8PSE6pB3dWOrD/nueuU5sduBsQ4w==",
      "dev": true,
      "license": "MIT",
      "peer": true
    },
    "node_modules/react-router": {
      "version": "7.13.2",
      "resolved": "https://registry.npmjs.org/react-router/-/react-router-7.13.2.tgz",
      "integrity": "sha512-tX1Aee+ArlKQP+NIUd7SE6Li+CiGKwQtbS+FfRxPX6Pe4vHOo6nr9d++u5cwg+Z8K/x8tP+7qLmujDtfrAoUJA==",
      "license": "MIT",
      "dependencies": {
        "cookie": "^1.0.1",
        "set-cookie-parser": "^2.6.0"
      },
      "engines": {
        "node": ">=20.0.0"
      },
      "peerDependencies": {
        "react": ">=18",
        "react-dom": ">=18"
      },
      "peerDependenciesMeta": {
        "react-dom": {
          "optional": true
        }
      }
    },
    "node_modules/react-router-dom": {
      "version": "7.13.2",
      "resolved": "https://registry.npmjs.org/react-router-dom/-/react-router-dom-7.13.2.tgz",
      "integrity": "sha512-aR7SUORwTqAW0JDeiWF07e9SBE9qGpByR9I8kJT5h/FrBKxPMS6TiC7rmVO+gC0q52Bx7JnjWe8Z1sR9faN4YA==",
      "license": "MIT",
      "dependencies": {
        "react-router": "7.13.2"
      },
      "engines": {
        "node": ">=20.0.0"
      },
      "peerDependencies": {
        "react": ">=18",
        "react-dom": ">=18"
      }
    },
    "node_modules/redent": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/redent/-/redent-3.0.0.tgz",
      "integrity": "sha512-6tDA8g98We0zd0GvVeMT9arEOnTw9qM03L9cJXaCjrip1OO764RDBLBfrB4cwzNGDj5OA5ioymC9GkizgWJDUg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "indent-string": "^4.0.0",
        "strip-indent": "^3.0.0"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/require-from-string": {
      "version": "2.0.2",
      "resolved": "https://registry.npmjs.org/require-from-string/-/require-from-string-2.0.2.tgz",
      "integrity": "sha512-Xf0nWe6RseziFMu+Ap9biiUbmplq6S9/p+7w7YXP/JBHhrUDDUhwa+vANyubuqfZWTveU//DYVGsDG7RKL/vEw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/resolve-from": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/resolve-from/-/resolve-from-4.0.0.tgz",
      "integrity": "sha512-pb/MYmXstAkysRFx8piNI1tGFNQIFA3vkE3Gq4EuA1dF6gHp/+vgZqsCGJapvy8N3Q+4o7FwvquPJcnZ7RYy4g==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=4"
      }
    },
    "node_modules/rolldown": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/rolldown/-/rolldown-1.0.0-rc.11.tgz",
      "integrity": "sha512-NRjoKMusSjfRbSYiH3VSumlkgFe7kYAa3pzVOsVYVFY3zb5d7nS+a3KGQ7hJKXuYWbzJKPVQ9Wxq2UvyK+ENpw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@oxc-project/types": "=0.122.0",
        "@rolldown/pluginutils": "1.0.0-rc.11"
      },
      "bin": {
        "rolldown": "bin/cli.mjs"
      },
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      },
      "optionalDependencies": {
        "@rolldown/binding-android-arm64": "1.0.0-rc.11",
        "@rolldown/binding-darwin-arm64": "1.0.0-rc.11",
        "@rolldown/binding-darwin-x64": "1.0.0-rc.11",
        "@rolldown/binding-freebsd-x64": "1.0.0-rc.11",
        "@rolldown/binding-linux-arm-gnueabihf": "1.0.0-rc.11",
        "@rolldown/binding-linux-arm64-gnu": "1.0.0-rc.11",
        "@rolldown/binding-linux-arm64-musl": "1.0.0-rc.11",
        "@rolldown/binding-linux-ppc64-gnu": "1.0.0-rc.11",
        "@rolldown/binding-linux-s390x-gnu": "1.0.0-rc.11",
        "@rolldown/binding-linux-x64-gnu": "1.0.0-rc.11",
        "@rolldown/binding-linux-x64-musl": "1.0.0-rc.11",
        "@rolldown/binding-openharmony-arm64": "1.0.0-rc.11",
        "@rolldown/binding-wasm32-wasi": "1.0.0-rc.11",
        "@rolldown/binding-win32-arm64-msvc": "1.0.0-rc.11",
        "@rolldown/binding-win32-x64-msvc": "1.0.0-rc.11"
      }
    },
    "node_modules/rolldown/node_modules/@rolldown/pluginutils": {
      "version": "1.0.0-rc.11",
      "resolved": "https://registry.npmjs.org/@rolldown/pluginutils/-/pluginutils-1.0.0-rc.11.tgz",
      "integrity": "sha512-xQO9vbwBecJRv9EUcQ/y0dzSTJgA7Q6UVN7xp6B81+tBGSLVAK03yJ9NkJaUA7JFD91kbjxRSC/mDnmvXzbHoQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/saxes": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/saxes/-/saxes-6.0.0.tgz",
      "integrity": "sha512-xAg7SOnEhrm5zI3puOOKyy1OMcMlIJZYNJY7xLBwSze0UjhPLnWfj2GF2EpT0jmzaJKIWKHLsaSSajf35bcYnA==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "xmlchars": "^2.2.0"
      },
      "engines": {
        "node": ">=v12.22.7"
      }
    },
    "node_modules/scheduler": {
      "version": "0.27.0",
      "resolved": "https://registry.npmjs.org/scheduler/-/scheduler-0.27.0.tgz",
      "integrity": "sha512-eNv+WrVbKu1f3vbYJT/xtiF5syA5HPIMtf9IgY/nKg0sWqzAUEvqY/xm7OcZc/qafLx/iO9FgOmeSAp4v5ti/Q==",
      "license": "MIT"
    },
    "node_modules/semver": {
      "version": "6.3.1",
      "resolved": "https://registry.npmjs.org/semver/-/semver-6.3.1.tgz",
      "integrity": "sha512-BR7VvDCVHO+q2xBEWskxS6DJE1qRnb7DxzUrogb71CWoSficBxYsiAGd+Kl0mmq/MprG9yArRkyrQxTO6XjMzA==",
      "dev": true,
      "license": "ISC",
      "bin": {
        "semver": "bin/semver.js"
      }
    },
    "node_modules/set-cookie-parser": {
      "version": "2.7.2",
      "resolved": "https://registry.npmjs.org/set-cookie-parser/-/set-cookie-parser-2.7.2.tgz",
      "integrity": "sha512-oeM1lpU/UvhTxw+g3cIfxXHyJRc/uidd3yK1P242gzHds0udQBYzs3y8j4gCCW+ZJ7ad0yctld8RYO+bdurlvw==",
      "license": "MIT"
    },
    "node_modules/shebang-command": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/shebang-command/-/shebang-command-2.0.0.tgz",
      "integrity": "sha512-kHxr2zZpYtdmrN1qDjrrX/Z1rR1kG8Dx+gkpK1G4eXmvXswmcE1hTWBWYUzlraYw1/yZp6YuDY77YtvbN0dmDA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "shebang-regex": "^3.0.0"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/shebang-regex": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/shebang-regex/-/shebang-regex-3.0.0.tgz",
      "integrity": "sha512-7++dFhtcx3353uBaq8DDR4NuxBetBzC7ZQOhmTQInHEd6bSrXdiEyzCvG07Z44UYdLShWUyXt5M/yhz8ekcb1A==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/siginfo": {
      "version": "2.0.0",
      "resolved": "https://registry.npmjs.org/siginfo/-/siginfo-2.0.0.tgz",
      "integrity": "sha512-ybx0WO1/8bSBLEWXZvEd7gMW3Sn3JFlW3TvX1nREbDLRNQNaeNN8WK0meBwPdAaOI7TtRRRJn/Es1zhrrCHu7g==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/source-map-js": {
      "version": "1.2.1",
      "resolved": "https://registry.npmjs.org/source-map-js/-/source-map-js-1.2.1.tgz",
      "integrity": "sha512-UXWMKhLOwVKb728IUtQPXxfYU+usdybtUrK/8uGE8CQMvrhOpwvzDBwj0QhSL7MQc7vIsISBG8VQ8+IDQxpfQA==",
      "dev": true,
      "license": "BSD-3-Clause",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/stackback": {
      "version": "0.0.2",
      "resolved": "https://registry.npmjs.org/stackback/-/stackback-0.0.2.tgz",
      "integrity": "sha512-1XMJE5fQo1jGH6Y/7ebnwPOBEkIEnT4QF32d5R1+VXdXveM0IBMJt8zfaxX1P3QhVwrYe+576+jkANtSS2mBbw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/std-env": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/std-env/-/std-env-4.0.0.tgz",
      "integrity": "sha512-zUMPtQ/HBY3/50VbpkupYHbRroTRZJPRLvreamgErJVys0ceuzMkD44J/QjqhHjOzK42GQ3QZIeFG1OYfOtKqQ==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/strip-indent": {
      "version": "3.0.0",
      "resolved": "https://registry.npmjs.org/strip-indent/-/strip-indent-3.0.0.tgz",
      "integrity": "sha512-laJTa3Jb+VQpaC6DseHhF7dXVqHTfJPCRDaEbid/drOhgitgYku/letMUqOXFoWV0zIIUbjpdH2t+tYj4bQMRQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "min-indent": "^1.0.0"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/strip-json-comments": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/strip-json-comments/-/strip-json-comments-3.1.1.tgz",
      "integrity": "sha512-6fPc+R4ihwqP6N/aIv2f1gMH8lOVtWQHoqC4yK6oSDVVocumAsfCqjkXnqiYMhmMwS/mEHLp7Vehlt3ql6lEig==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=8"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/supports-color": {
      "version": "7.2.0",
      "resolved": "https://registry.npmjs.org/supports-color/-/supports-color-7.2.0.tgz",
      "integrity": "sha512-qpCAvRl9stuOHveKsn7HncJRvv501qIacKzQlO/+Lwxc9+0q2wLyv4Dfvt80/DPn2pqOBsJdDiogXGR9+OvwRw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "has-flag": "^4.0.0"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/symbol-tree": {
      "version": "3.2.4",
      "resolved": "https://registry.npmjs.org/symbol-tree/-/symbol-tree-3.2.4.tgz",
      "integrity": "sha512-9QNk5KwDF+Bvz+PyObkmSYjI5ksVUYtjW7AU22r2NKcfLJcXp96hkDWU3+XndOsUb+AQ9QhfzfCT2O+CNWT5Tw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/tinybench": {
      "version": "2.9.0",
      "resolved": "https://registry.npmjs.org/tinybench/-/tinybench-2.9.0.tgz",
      "integrity": "sha512-0+DUvqWMValLmha6lr4kD8iAMK1HzV0/aKnCtWb9v9641TnP/MFb7Pc2bxoxQjTXAErryXVgUOfv2YqNllqGeg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/tinyexec": {
      "version": "1.0.4",
      "resolved": "https://registry.npmjs.org/tinyexec/-/tinyexec-1.0.4.tgz",
      "integrity": "sha512-u9r3uZC0bdpGOXtlxUIdwf9pkmvhqJdrVCH9fapQtgy/OeTTMZ1nqH7agtvEfmGui6e1XxjcdrlxvxJvc3sMqw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/tinyglobby": {
      "version": "0.2.15",
      "resolved": "https://registry.npmjs.org/tinyglobby/-/tinyglobby-0.2.15.tgz",
      "integrity": "sha512-j2Zq4NyQYG5XMST4cbs02Ak8iJUdxRM0XI5QyxXuZOzKOINmWurp3smXu3y5wDcJrptwpSjgXHzIQxR0omXljQ==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "fdir": "^6.5.0",
        "picomatch": "^4.0.3"
      },
      "engines": {
        "node": ">=12.0.0"
      },
      "funding": {
        "url": "https://github.com/sponsors/SuperchupuDev"
      }
    },
    "node_modules/tinyrainbow": {
      "version": "3.1.0",
      "resolved": "https://registry.npmjs.org/tinyrainbow/-/tinyrainbow-3.1.0.tgz",
      "integrity": "sha512-Bf+ILmBgretUrdJxzXM0SgXLZ3XfiaUuOj/IKQHuTXip+05Xn+uyEYdVg0kYDipTBcLrCVyUzAPz7QmArb0mmw==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=14.0.0"
      }
    },
    "node_modules/tldts": {
      "version": "7.0.27",
      "resolved": "https://registry.npmjs.org/tldts/-/tldts-7.0.27.tgz",
      "integrity": "sha512-I4FZcVFcqCRuT0ph6dCDpPuO4Xgzvh+spkcTr1gK7peIvxWauoloVO0vuy1FQnijT63ss6AsHB6+OIM4aXHbPg==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "tldts-core": "^7.0.27"
      },
      "bin": {
        "tldts": "bin/cli.js"
      }
    },
    "node_modules/tldts-core": {
      "version": "7.0.27",
      "resolved": "https://registry.npmjs.org/tldts-core/-/tldts-core-7.0.27.tgz",
      "integrity": "sha512-YQ7uPjgWUibIK6DW5lrKujGwUKhLevU4hcGbP5O6TcIUb+oTjJYJVWPS4nZsIHrEEEG6myk/oqAJUEQmpZrHsg==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/tough-cookie": {
      "version": "6.0.1",
      "resolved": "https://registry.npmjs.org/tough-cookie/-/tough-cookie-6.0.1.tgz",
      "integrity": "sha512-LktZQb3IeoUWB9lqR5EWTHgW/VTITCXg4D21M+lvybRVdylLrRMnqaIONLVb5mav8vM19m44HIcGq4qASeu2Qw==",
      "dev": true,
      "license": "BSD-3-Clause",
      "dependencies": {
        "tldts": "^7.0.5"
      },
      "engines": {
        "node": ">=16"
      }
    },
    "node_modules/tr46": {
      "version": "6.0.0",
      "resolved": "https://registry.npmjs.org/tr46/-/tr46-6.0.0.tgz",
      "integrity": "sha512-bLVMLPtstlZ4iMQHpFHTR7GAGj2jxi8Dg0s2h2MafAE4uSWF98FC/3MomU51iQAMf8/qDUbKWf5GxuvvVcXEhw==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "punycode": "^2.3.1"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/ts-api-utils": {
      "version": "2.5.0",
      "resolved": "https://registry.npmjs.org/ts-api-utils/-/ts-api-utils-2.5.0.tgz",
      "integrity": "sha512-OJ/ibxhPlqrMM0UiNHJ/0CKQkoKF243/AEmplt3qpRgkW8VG7IfOS41h7V8TjITqdByHzrjcS/2si+y4lIh8NA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18.12"
      },
      "peerDependencies": {
        "typescript": ">=4.8.4"
      }
    },
    "node_modules/tslib": {
      "version": "2.8.1",
      "resolved": "https://registry.npmjs.org/tslib/-/tslib-2.8.1.tgz",
      "integrity": "sha512-oJFu94HQb+KVduSUQL7wnpmqnfmLsOA/nAh6b6EH0wCEoK0/mPeXU6c3wKDV83MkOuHPRHtSXKKU99IBazS/2w==",
      "dev": true,
      "license": "0BSD",
      "optional": true
    },
    "node_modules/type-check": {
      "version": "0.4.0",
      "resolved": "https://registry.npmjs.org/type-check/-/type-check-0.4.0.tgz",
      "integrity": "sha512-XleUoc9uwGXqjWwXaUTZAmzMcFZ5858QA2vvx1Ur5xIcixXIP+8LnFDgRplU30us6teqdlskFfu+ae4K79Ooew==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "prelude-ls": "^1.2.1"
      },
      "engines": {
        "node": ">= 0.8.0"
      }
    },
    "node_modules/typescript": {
      "version": "5.9.3",
      "resolved": "https://registry.npmjs.org/typescript/-/typescript-5.9.3.tgz",
      "integrity": "sha512-jl1vZzPDinLr9eUt3J/t7V6FgNEw9QjvBPdysz9KfQDD41fQrC2Y4vKQdiaUpFT4bXlb1RHhLpp8wtm6M5TgSw==",
      "dev": true,
      "license": "Apache-2.0",
      "bin": {
        "tsc": "bin/tsc",
        "tsserver": "bin/tsserver"
      },
      "engines": {
        "node": ">=14.17"
      }
    },
    "node_modules/typescript-eslint": {
      "version": "8.57.2",
      "resolved": "https://registry.npmjs.org/typescript-eslint/-/typescript-eslint-8.57.2.tgz",
      "integrity": "sha512-VEPQ0iPgWO/sBaZOU1xo4nuNdODVOajPnTIbog2GKYr31nIlZ0fWPoCQgGfF3ETyBl1vn63F/p50Um9Z4J8O8A==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@typescript-eslint/eslint-plugin": "8.57.2",
        "@typescript-eslint/parser": "8.57.2",
        "@typescript-eslint/typescript-estree": "8.57.2",
        "@typescript-eslint/utils": "8.57.2"
      },
      "engines": {
        "node": "^18.18.0 || ^20.9.0 || >=21.1.0"
      },
      "funding": {
        "type": "opencollective",
        "url": "https://opencollective.com/typescript-eslint"
      },
      "peerDependencies": {
        "eslint": "^8.57.0 || ^9.0.0 || ^10.0.0",
        "typescript": ">=4.8.4 <6.0.0"
      }
    },
    "node_modules/undici-types": {
      "version": "7.16.0",
      "resolved": "https://registry.npmjs.org/undici-types/-/undici-types-7.16.0.tgz",
      "integrity": "sha512-Zz+aZWSj8LE6zoxD+xrjh4VfkIG8Ya6LvYkZqtUQGJPZjYl53ypCaUwWqo7eI0x66KBGeRo+mlBEkMSeSZ38Nw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/update-browserslist-db": {
      "version": "1.2.3",
      "resolved": "https://registry.npmjs.org/update-browserslist-db/-/update-browserslist-db-1.2.3.tgz",
      "integrity": "sha512-Js0m9cx+qOgDxo0eMiFGEueWztz+d4+M3rGlmKPT+T4IS/jP4ylw3Nwpu6cpTTP8R1MAC1kF4VbdLt3ARf209w==",
      "dev": true,
      "funding": [
        {
          "type": "opencollective",
          "url": "https://opencollective.com/browserslist"
        },
        {
          "type": "tidelift",
          "url": "https://tidelift.com/funding/github/npm/browserslist"
        },
        {
          "type": "github",
          "url": "https://github.com/sponsors/ai"
        }
      ],
      "license": "MIT",
      "dependencies": {
        "escalade": "^3.2.0",
        "picocolors": "^1.1.1"
      },
      "bin": {
        "update-browserslist-db": "cli.js"
      },
      "peerDependencies": {
        "browserslist": ">= 4.21.0"
      }
    },
    "node_modules/uri-js": {
      "version": "4.4.1",
      "resolved": "https://registry.npmjs.org/uri-js/-/uri-js-4.4.1.tgz",
      "integrity": "sha512-7rKUyy33Q1yc98pQ1DAmLtwX109F7TIfWlW1Ydo8Wl1ii1SeHieeh0HHfPeL2fMXK6z0s8ecKs9frCuLJvndBg==",
      "dev": true,
      "license": "BSD-2-Clause",
      "dependencies": {
        "punycode": "^2.1.0"
      }
    },
    "node_modules/vite": {
      "version": "8.0.2",
      "resolved": "https://registry.npmjs.org/vite/-/vite-8.0.2.tgz",
      "integrity": "sha512-1gFhNi+bHhRE/qKZOJXACm6tX4bA3Isy9KuKF15AgSRuRazNBOJfdDemPBU16/mpMxApDPrWvZ08DcLPEoRnuA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "lightningcss": "^1.32.0",
        "picomatch": "^4.0.3",
        "postcss": "^8.5.8",
        "rolldown": "1.0.0-rc.11",
        "tinyglobby": "^0.2.15"
      },
      "bin": {
        "vite": "bin/vite.js"
      },
      "engines": {
        "node": "^20.19.0 || >=22.12.0"
      },
      "funding": {
        "url": "https://github.com/vitejs/vite?sponsor=1"
      },
      "optionalDependencies": {
        "fsevents": "~2.3.3"
      },
      "peerDependencies": {
        "@types/node": "^20.19.0 || >=22.12.0",
        "@vitejs/devtools": "^0.1.0",
        "esbuild": "^0.27.0",
        "jiti": ">=1.21.0",
        "less": "^4.0.0",
        "sass": "^1.70.0",
        "sass-embedded": "^1.70.0",
        "stylus": ">=0.54.8",
        "sugarss": "^5.0.0",
        "terser": "^5.16.0",
        "tsx": "^4.8.1",
        "yaml": "^2.4.2"
      },
      "peerDependenciesMeta": {
        "@types/node": {
          "optional": true
        },
        "@vitejs/devtools": {
          "optional": true
        },
        "esbuild": {
          "optional": true
        },
        "jiti": {
          "optional": true
        },
        "less": {
          "optional": true
        },
        "sass": {
          "optional": true
        },
        "sass-embedded": {
          "optional": true
        },
        "stylus": {
          "optional": true
        },
        "sugarss": {
          "optional": true
        },
        "terser": {
          "optional": true
        },
        "tsx": {
          "optional": true
        },
        "yaml": {
          "optional": true
        }
      }
    },
    "node_modules/vitest": {
      "version": "4.1.1",
      "resolved": "https://registry.npmjs.org/vitest/-/vitest-4.1.1.tgz",
      "integrity": "sha512-yF+o4POL41rpAzj5KVILUxm1GCjKnELvaqmU9TLLUbMfDzuN0UpUR9uaDs+mCtjPe+uYPksXDRLQGGPvj1cTmA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "@vitest/expect": "4.1.1",
        "@vitest/mocker": "4.1.1",
        "@vitest/pretty-format": "4.1.1",
        "@vitest/runner": "4.1.1",
        "@vitest/snapshot": "4.1.1",
        "@vitest/spy": "4.1.1",
        "@vitest/utils": "4.1.1",
        "es-module-lexer": "^2.0.0",
        "expect-type": "^1.3.0",
        "magic-string": "^0.30.21",
        "obug": "^2.1.1",
        "pathe": "^2.0.3",
        "picomatch": "^4.0.3",
        "std-env": "^4.0.0-rc.1",
        "tinybench": "^2.9.0",
        "tinyexec": "^1.0.2",
        "tinyglobby": "^0.2.15",
        "tinyrainbow": "^3.0.3",
        "vite": "^6.0.0 || ^7.0.0 || ^8.0.0",
        "why-is-node-running": "^2.3.0"
      },
      "bin": {
        "vitest": "vitest.mjs"
      },
      "engines": {
        "node": "^20.0.0 || ^22.0.0 || >=24.0.0"
      },
      "funding": {
        "url": "https://opencollective.com/vitest"
      },
      "peerDependencies": {
        "@edge-runtime/vm": "*",
        "@opentelemetry/api": "^1.9.0",
        "@types/node": "^20.0.0 || ^22.0.0 || >=24.0.0",
        "@vitest/browser-playwright": "4.1.1",
        "@vitest/browser-preview": "4.1.1",
        "@vitest/browser-webdriverio": "4.1.1",
        "@vitest/ui": "4.1.1",
        "happy-dom": "*",
        "jsdom": "*",
        "vite": "^6.0.0 || ^7.0.0 || ^8.0.0"
      },
      "peerDependenciesMeta": {
        "@edge-runtime/vm": {
          "optional": true
        },
        "@opentelemetry/api": {
          "optional": true
        },
        "@types/node": {
          "optional": true
        },
        "@vitest/browser-playwright": {
          "optional": true
        },
        "@vitest/browser-preview": {
          "optional": true
        },
        "@vitest/browser-webdriverio": {
          "optional": true
        },
        "@vitest/ui": {
          "optional": true
        },
        "happy-dom": {
          "optional": true
        },
        "jsdom": {
          "optional": true
        },
        "vite": {
          "optional": false
        }
      }
    },
    "node_modules/w3c-xmlserializer": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/w3c-xmlserializer/-/w3c-xmlserializer-5.0.0.tgz",
      "integrity": "sha512-o8qghlI8NZHU1lLPrpi2+Uq7abh4GGPpYANlalzWxyWteJOCsr/P+oPBA49TOLu5FTZO4d3F9MnWJfiMo4BkmA==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "xml-name-validator": "^5.0.0"
      },
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/webidl-conversions": {
      "version": "8.0.1",
      "resolved": "https://registry.npmjs.org/webidl-conversions/-/webidl-conversions-8.0.1.tgz",
      "integrity": "sha512-BMhLD/Sw+GbJC21C/UgyaZX41nPt8bUTg+jWyDeg7e7YN4xOM05YPSIXceACnXVtqyEw/LMClUQMtMZ+PGGpqQ==",
      "dev": true,
      "license": "BSD-2-Clause",
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/whatwg-mimetype": {
      "version": "4.0.0",
      "resolved": "https://registry.npmjs.org/whatwg-mimetype/-/whatwg-mimetype-4.0.0.tgz",
      "integrity": "sha512-QaKxh0eNIi2mE9p2vEdzfagOKHCcj1pJ56EEHGQOVxp8r9/iszLUUV7v89x9O1p/T+NlTM5W7jW6+cz4Fq1YVg==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/whatwg-url": {
      "version": "15.1.0",
      "resolved": "https://registry.npmjs.org/whatwg-url/-/whatwg-url-15.1.0.tgz",
      "integrity": "sha512-2ytDk0kiEj/yu90JOAp44PVPUkO9+jVhyf+SybKlRHSDlvOOZhdPIrr7xTH64l4WixO2cP+wQIcgujkGBPPz6g==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "tr46": "^6.0.0",
        "webidl-conversions": "^8.0.0"
      },
      "engines": {
        "node": ">=20"
      }
    },
    "node_modules/which": {
      "version": "2.0.2",
      "resolved": "https://registry.npmjs.org/which/-/which-2.0.2.tgz",
      "integrity": "sha512-BLI3Tl1TW3Pvl70l3yq3Y64i+awpwXqsGBYWkkqMtnbXgrMD+yj7rhW0kuEDxzJaYXGjEW5ogapKNMEKNMjibA==",
      "dev": true,
      "license": "ISC",
      "dependencies": {
        "isexe": "^2.0.0"
      },
      "bin": {
        "node-which": "bin/node-which"
      },
      "engines": {
        "node": ">= 8"
      }
    },
    "node_modules/why-is-node-running": {
      "version": "2.3.0",
      "resolved": "https://registry.npmjs.org/why-is-node-running/-/why-is-node-running-2.3.0.tgz",
      "integrity": "sha512-hUrmaWBdVDcxvYqnyh09zunKzROWjbZTiNy8dBEjkS7ehEDQibXJ7XvlmtbwuTclUiIyN+CyXQD4Vmko8fNm8w==",
      "dev": true,
      "license": "MIT",
      "dependencies": {
        "siginfo": "^2.0.0",
        "stackback": "0.0.2"
      },
      "bin": {
        "why-is-node-running": "cli.js"
      },
      "engines": {
        "node": ">=8"
      }
    },
    "node_modules/word-wrap": {
      "version": "1.2.5",
      "resolved": "https://registry.npmjs.org/word-wrap/-/word-wrap-1.2.5.tgz",
      "integrity": "sha512-BN22B5eaMMI9UMtjrGd5g5eCYPpCPDUy0FJXbYsaT5zYxjFOckS53SQDE3pWkVoWpHXVb3BrYcEN4Twa55B5cA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=0.10.0"
      }
    },
    "node_modules/ws": {
      "version": "8.20.0",
      "resolved": "https://registry.npmjs.org/ws/-/ws-8.20.0.tgz",
      "integrity": "sha512-sAt8BhgNbzCtgGbt2OxmpuryO63ZoDk/sqaB/znQm94T4fCEsy/yV+7CdC1kJhOU9lboAEU7R3kquuycDoibVA==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=10.0.0"
      },
      "peerDependencies": {
        "bufferutil": "^4.0.1",
        "utf-8-validate": ">=5.0.2"
      },
      "peerDependenciesMeta": {
        "bufferutil": {
          "optional": true
        },
        "utf-8-validate": {
          "optional": true
        }
      }
    },
    "node_modules/xml-name-validator": {
      "version": "5.0.0",
      "resolved": "https://registry.npmjs.org/xml-name-validator/-/xml-name-validator-5.0.0.tgz",
      "integrity": "sha512-EvGK8EJ3DhaHfbRlETOWAS5pO9MZITeauHKJyb8wyajUfQUenkIg2MvLDTZ4T/TgIcm3HU0TFBgWWboAZ30UHg==",
      "dev": true,
      "license": "Apache-2.0",
      "engines": {
        "node": ">=18"
      }
    },
    "node_modules/xmlchars": {
      "version": "2.2.0",
      "resolved": "https://registry.npmjs.org/xmlchars/-/xmlchars-2.2.0.tgz",
      "integrity": "sha512-JZnDKK8B0RCDw84FNdDAIpZK+JuJw+s7Lz8nksI7SIuU3UXJJslUthsi+uWBUYOwPFwW7W7PRLRfUKpxjtjFCw==",
      "dev": true,
      "license": "MIT"
    },
    "node_modules/yallist": {
      "version": "3.1.1",
      "resolved": "https://registry.npmjs.org/yallist/-/yallist-3.1.1.tgz",
      "integrity": "sha512-a4UGQaWPH59mOXUYnAG2ewncQS4i4F43Tv3JoAM+s2VDAmS9NsK8GpDMLrCHPksFT7h3K6TOoUNn2pb7RoXx4g==",
      "dev": true,
      "license": "ISC"
    },
    "node_modules/yocto-queue": {
      "version": "0.1.0",
      "resolved": "https://registry.npmjs.org/yocto-queue/-/yocto-queue-0.1.0.tgz",
      "integrity": "sha512-rVksvsnNCdJ/ohGc6xgPwyN8eheCxsiLM8mxuE/t/mOVqJewPuO1miLpTHQiRgTKCLexL4MeAFVagts7HmNZ2Q==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=10"
      },
      "funding": {
        "url": "https://github.com/sponsors/sindresorhus"
      }
    },
    "node_modules/zod": {
      "version": "4.3.6",
      "resolved": "https://registry.npmjs.org/zod/-/zod-4.3.6.tgz",
      "integrity": "sha512-rftlrkhHZOcjDwkGlnUtZZkvaPHCsDATp4pGpuOOMDaTdDDXF91wuVDJoWoPsKX/3YPQ5fHuF3STjcYyKr+Qhg==",
      "dev": true,
      "license": "MIT",
      "funding": {
        "url": "https://github.com/sponsors/colinhacks"
      }
    },
    "node_modules/zod-validation-error": {
      "version": "4.0.2",
      "resolved": "https://registry.npmjs.org/zod-validation-error/-/zod-validation-error-4.0.2.tgz",
      "integrity": "sha512-Q6/nZLe6jxuU80qb/4uJ4t5v2VEZ44lzQjPDhYJNztRQ4wyWc6VF3D3Kb/fAuPetZQnhS3hnajCf9CsWesghLQ==",
      "dev": true,
      "license": "MIT",
      "engines": {
        "node": ">=18.0.0"
      },
      "peerDependencies": {
        "zod": "^3.25.0 || ^4.0.0"
      }
    }
  }
}
```

### `frontend/package.json`

```json
{
  "name": "frontend",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "lint": "eslint .",
    "preview": "vite preview",
    "test": "vitest run"
  },
  "dependencies": {
    "lucide-react": "^1.0.1",
    "react": "^19.2.4",
    "react-dom": "^19.2.4",
    "react-router-dom": "^7.9.6"
  },
  "devDependencies": {
    "@eslint/js": "^9.39.4",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.0",
    "@types/node": "^24.12.0",
    "@types/react": "^19.2.14",
    "@types/react-dom": "^19.2.3",
    "@vitejs/plugin-react": "^6.0.1",
    "eslint": "^9.39.4",
    "eslint-plugin-react-hooks": "^7.0.1",
    "eslint-plugin-react-refresh": "^0.5.2",
    "globals": "^17.4.0",
    "jsdom": "^27.0.1",
    "typescript": "~5.9.3",
    "typescript-eslint": "^8.57.0",
    "vite": "^8.0.1",
    "vitest": "^4.0.0"
  }
}
```

### `frontend/src/App.css`

```css
.counter {
  font-size: 16px;
  padding: 5px 10px;
  border-radius: 5px;
  color: var(--accent);
  background: var(--accent-bg);
  border: 2px solid transparent;
  transition: border-color 0.3s;
  margin-bottom: 24px;

  &:hover {
    border-color: var(--accent-border);
  }
  &:focus-visible {
    outline: 2px solid var(--accent);
    outline-offset: 2px;
  }
}

.hero {
  position: relative;

  .base,
  .framework,
  .vite {
    inset-inline: 0;
    margin: 0 auto;
  }

  .base {
    width: 170px;
    position: relative;
    z-index: 0;
  }

  .framework,
  .vite {
    position: absolute;
  }

  .framework {
    z-index: 1;
    top: 34px;
    height: 28px;
    transform: perspective(2000px) rotateZ(300deg) rotateX(44deg) rotateY(39deg)
      scale(1.4);
  }

  .vite {
    z-index: 0;
    top: 107px;
    height: 26px;
    width: auto;
    transform: perspective(2000px) rotateZ(300deg) rotateX(40deg) rotateY(39deg)
      scale(0.8);
  }
}

#center {
  display: flex;
  flex-direction: column;
  gap: 25px;
  place-content: center;
  place-items: center;
  flex-grow: 1;

  @media (max-width: 1024px) {
    padding: 32px 20px 24px;
    gap: 18px;
  }
}

#next-steps {
  display: flex;
  border-top: 1px solid var(--border);
  text-align: left;

  & > div {
    flex: 1 1 0;
    padding: 32px;
    @media (max-width: 1024px) {
      padding: 24px 20px;
    }
  }

  .icon {
    margin-bottom: 16px;
    width: 22px;
    height: 22px;
  }

  @media (max-width: 1024px) {
    flex-direction: column;
    text-align: center;
  }
}

#docs {
  border-right: 1px solid var(--border);

  @media (max-width: 1024px) {
    border-right: none;
    border-bottom: 1px solid var(--border);
  }
}

#next-steps ul {
  list-style: none;
  padding: 0;
  display: flex;
  gap: 8px;
  margin: 32px 0 0;

  .logo {
    height: 18px;
  }

  a {
    color: var(--text-h);
    font-size: 16px;
    border-radius: 6px;
    background: var(--social-bg);
    display: flex;
    padding: 6px 12px;
    align-items: center;
    gap: 8px;
    text-decoration: none;
    transition: box-shadow 0.3s;

    &:hover {
      box-shadow: var(--shadow);
    }
    .button-icon {
      height: 18px;
      width: 18px;
    }
  }

  @media (max-width: 1024px) {
    margin-top: 20px;
    flex-wrap: wrap;
    justify-content: center;

    li {
      flex: 1 1 calc(50% - 8px);
    }

    a {
      width: 100%;
      justify-content: center;
      box-sizing: border-box;
    }
  }
}

#spacer {
  height: 88px;
  border-top: 1px solid var(--border);
  @media (max-width: 1024px) {
    height: 48px;
  }
}

.ticks {
  position: relative;
  width: 100%;

  &::before,
  &::after {
    content: '';
    position: absolute;
    top: -4.5px;
    border: 5px solid transparent;
  }

  &::before {
    left: 0;
    border-left-color: var(--border);
  }
  &::after {
    right: 0;
    border-right-color: var(--border);
  }
}
```

### `frontend/src/App.tsx`

```tsx
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles/responsive.css'
import { HomePage } from './pages/home/HomePage'
import { NearbyPage } from './pages/nearby/NearbyPage'
import { OpenNowPage } from './pages/open-now/OpenNowPage'
import { PlaceDetailPage } from './pages/places/PlaceDetailPage'
import { PlacesListPage } from './pages/places/PlacesListPage'
import { WalkRoutePage } from './pages/routes/WalkRoutePage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/places" element={<PlacesListPage />} />
        <Route path="/places/:slug" element={<PlaceDetailPage />} />
        <Route path="/open-now" element={<OpenNowPage />} />
        <Route path="/nearby" element={<NearbyPage />} />
        <Route path="/walk-route" element={<WalkRoutePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
```

### `frontend/src/api/nearby/nearby.api.ts`

```ts
import { buildApiUrl } from '../../shared/api/http'

export type NearbyPlace = {
  id: number
  slug: string
  title: string
  city_id: number
  category_id: number | null
  category: string
  address: string
  lat: number
  lng: number
  distance_km: number
}

export const getNearbyPlaces = async (
  lat: number,
  lng: number,
  radiusKm = 3,
): Promise<NearbyPlace[]> => {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_km: String(radiusKm),
  })

  const response = await fetch(buildApiUrl(`/nearby/?${params.toString()}`))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: NearbyPlace[] = await response.json()
  return data
}
```

### `frontend/src/api/open-now/openNow.api.ts`

```ts
import { buildApiUrl } from '../../shared/api/http'

export type OpenNowPlace = {
  id: number
  slug: string
  title: string
  city_id: number
  category_id: number | null
  category: string
  address: string
  open_time: string
  close_time: string
}

export const getOpenNowPlaces = async (citySlug: string): Promise<OpenNowPlace[]> => {
  const params = new URLSearchParams({ city_slug: citySlug })
  const response = await fetch(buildApiUrl(`/open-now/?${params.toString()}`))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: OpenNowPlace[] = await response.json()
  return data
}
```

### `frontend/src/api/places/places.api.test.ts`

```ts
import { afterEach, describe, expect, it, vi } from 'vitest'
import { getPlacesByCity } from './places.api'

describe('getPlacesByCity', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns places when response is ok', async () => {
    const mockData = [
      {
        id: 1,
        slug: 'mesto',
        title: 'Тестовое место',
        short_description: null,
        category: 'museum',
        address: 'Адрес 1',
      },
    ]

    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(
        new Response(JSON.stringify(mockData), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }),
      )

    const result = await getPlacesByCity('zelenogradsk')

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/places/?city_slug=zelenogradsk',
    )
    expect(result).toEqual(mockData)
  })

  it('throws error when response is not ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 500 }))

    await expect(getPlacesByCity('zelenogradsk')).rejects.toThrow('HTTP 500')
  })
})
```

### `frontend/src/api/places/places.api.ts`

```ts
import type { Place, PlaceDetail } from '../../entities/place/model/types'
import { buildPlaceBySlugUrl, buildPlacesUrl } from '../../shared/api/endpoints'
import { buildApiUrl } from '../../shared/api/http'

type PlacesResponse = {
  items: Place[]
  total: number
  limit: number
  offset: number
}

export const getPlacesByCity = async (citySlug: string): Promise<Place[]> => {
  const response = await fetch(buildApiUrl(buildPlacesUrl(citySlug)))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: PlacesResponse = await response.json()
  return data.items
}

export const getPlaceBySlug = async (slug: string): Promise<PlaceDetail> => {
  const response = await fetch(buildApiUrl(buildPlaceBySlugUrl(slug)))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: PlaceDetail = await response.json()
  return data
}
```

### `frontend/src/components/places/PlaceCard.tsx`

```tsx
import { ArrowUpRight, MapPin } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Badge } from '../../components/ui/Badge'
import type { Place } from '../../entities/place/model/types'

type PlaceCardProps = {
  place: Place
}

const categoryLabelMap: Record<string, string> = {
  cafe: 'Cafe',
  walk: 'Walk',
}

export const PlaceCard = ({ place }: PlaceCardProps) => {
  const categoryLabel = categoryLabelMap[place.category] ?? place.category

  return (
    <article
      style={{
        background: 'rgba(255, 255, 255, 0.88)',
        borderRadius: '28px',
        overflow: 'hidden',
        border: '1px solid rgba(148, 163, 184, 0.18)',
        boxShadow: '0 18px 40px rgba(15, 23, 42, 0.08)',
        backdropFilter: 'blur(12px)',
        transition: 'transform 0.18s ease, box-shadow 0.18s ease',
      }}
    >
      {place.image_url ? (
        <img
          src={place.image_url}
          alt={place.title}
          style={{
            width: '100%',
            height: '188px',
            objectFit: 'cover',
            display: 'block',
            background: '#e2e8f0',
          }}
        />
      ) : (
        <div
          style={{
            height: '188px',
            background:
              'radial-gradient(circle at top right, rgba(96, 165, 250, 0.35), transparent 30%), linear-gradient(135deg, #dbeafe 0%, #e2e8f0 100%)',
          }}
        />
      )}

      <div className="place-card-body" style={{ padding: '22px' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
          }}
        >
          <Badge variant="brand" uppercase>
            {categoryLabel}
          </Badge>

          <Link
            to={`/places/${place.slug}`}
            aria-label={`Открыть ${place.title}`}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '36px',
              height: '36px',
              borderRadius: '999px',
              background: '#f8fafc',
              color: '#0f172a',
              border: '1px solid #e2e8f0',
              textDecoration: 'none',
            }}
          >
            <ArrowUpRight size={16} />
          </Link>
        </div>

        <h3 className="place-card-title">
          <Link className="place-card-link" to={`/places/${place.slug}`}>
            {place.title}
          </Link>
        </h3>

        <div
          style={{
            marginTop: '12px',
            display: 'flex',
            gap: '8px',
            alignItems: 'flex-start',
            color: '#64748b',
            fontSize: '14px',
            lineHeight: 1.55,
          }}
        >
          <MapPin size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
          <span>{place.address}</span>
        </div>

        {place.short_description && (
          <p
            style={{
              margin: '16px 0 0',
              color: '#475569',
              fontSize: '15px',
              lineHeight: 1.65,
            }}
          >
            {place.short_description}
          </p>
        )}

        <div
          style={{
            marginTop: '18px',
            paddingTop: '14px',
            borderTop: '1px solid #e2e8f0',
          }}
        >
          <Link className="place-card-link-secondary" to={`/places/${place.slug}`}>
            Подробнее
          </Link>
        </div>
      </div>
    </article>
  )
}
```

### `frontend/src/components/ui/AppHeader.tsx`

```tsx
import { Compass, MapPinned } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { AppLink } from './AppLink'

const navLinkStyle = ({ isActive }: { isActive: boolean }) => ({
  color: isActive ? '#0f172a' : '#64748b',
  textDecoration: 'none',
  fontWeight: isActive ? 700 : 600,
  fontSize: '14px',
})

export const AppHeader = () => {
  return (
    <header
      className="app-header home-header"
      style={{
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
        }}
      >
        <div
          style={{
            width: '46px',
            height: '46px',
            borderRadius: '16px',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background:
              'linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(99, 102, 241, 0.2))',
            color: '#1d4ed8',
            border: '1px solid rgba(37, 99, 235, 0.12)',
          }}
        >
          <Compass size={22} />
        </div>

        <div>
          <div
            style={{
              fontSize: '14px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#64748b',
            }}
          >
            City Guide
          </div>

          <div
            style={{
              marginTop: '2px',
              fontSize: '22px',
              fontWeight: 800,
              color: '#0f172a',
              letterSpacing: '-0.03em',
            }}
          >
            Zelenogradsk
          </div>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <nav
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '14px',
            padding: '10px 14px',
            borderRadius: '999px',
            background: 'rgba(255, 255, 255, 0.78)',
            border: '1px solid rgba(148, 163, 184, 0.18)',
          }}
        >
          <NavLink to="/" style={navLinkStyle} end>
            Home
          </NavLink>

          <NavLink to="/places" style={navLinkStyle}>
            Places
          </NavLink>

          <NavLink to="/open-now" style={navLinkStyle}>
            Open Now
          </NavLink>

          <NavLink to="/nearby" style={navLinkStyle}>
            Nearby
          </NavLink>

          <NavLink to="/walk-route" style={navLinkStyle}>
            Walk Route
          </NavLink>
        </nav>

        <AppLink to="/places" variant="ghost">
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
            <MapPinned size={16} />
            Все места
          </span>
        </AppLink>
      </div>
    </header>
  )
}
```

### `frontend/src/components/ui/AppLink.tsx`

```tsx
import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

type AppLinkProps = {
  to: string
  children: ReactNode
  variant?: 'primary' | 'secondary' | 'ghost'
}

const styles = {
  base: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textDecoration: 'none',
    fontWeight: 600,
    transition: 'all 0.18s ease',
    cursor: 'pointer',
  },
  primary: {
    minHeight: '44px',
    padding: '0 16px',
    borderRadius: '14px',
    border: '1px solid rgba(255, 255, 255, 0.14)',
    background: 'rgba(255, 255, 255, 0.08)',
    color: '#ffffff',
    fontSize: '14px',
    backdropFilter: 'blur(10px)',
  },
  secondary: {
    color: '#2563eb',
    fontSize: '14px',
  },
  ghost: {
    minHeight: '40px',
    padding: '0 14px',
    borderRadius: '999px',
    background: 'rgba(255, 255, 255, 0.78)',
    border: '1px solid rgba(148, 163, 184, 0.18)',
    color: '#334155',
    fontSize: '14px',
  },
} as const

export const AppLink = ({ to, children, variant = 'secondary' }: AppLinkProps) => {
  const style = {
    ...styles.base,
    ...styles[variant],
  }

  return (
    <Link to={to} style={style}>
      {children}
    </Link>
  )
}
```

### `frontend/src/components/ui/Badge.tsx`

```tsx
import type { CSSProperties, ReactNode } from 'react'

type BadgeVariant = 'neutral' | 'brand' | 'success'

type BadgeProps = {
  children: ReactNode
  variant?: BadgeVariant
  uppercase?: boolean
}

const baseStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '7px 11px',
  borderRadius: '999px',
  fontSize: '12px',
  fontWeight: 800,
  letterSpacing: '0.06em',
}

const variantStyles: Record<BadgeVariant, CSSProperties> = {
  neutral: {
    background: '#f1f5f9',
    color: '#334155',
  },
  brand: {
    background: '#eff6ff',
    color: '#2563eb',
  },
  success: {
    background: '#dcfce7',
    color: '#166534',
  },
}

export const Badge = ({ children, variant = 'neutral', uppercase = false }: BadgeProps) => {
  return (
    <span
      style={{
        ...baseStyle,
        ...variantStyles[variant],
        textTransform: uppercase ? 'uppercase' : 'none',
      }}
    >
      {children}
    </span>
  )
}
```

### `frontend/src/components/ui/EmptyState.tsx`

```tsx
import { SurfaceCard } from './SurfaceCard'

type EmptyStateProps = {
  message: string
}

export const EmptyState = ({ message }: EmptyStateProps) => {
  return (
    <SurfaceCard
      style={{
        background: '#ffffff',
        border: '1px dashed #cbd5e1',
        color: '#475569',
        padding: '20px',
      }}
    >
      {message}
    </SurfaceCard>
  )
}
```

### `frontend/src/components/ui/PageBreadcrumbs.tsx`

```tsx
import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'

type BreadcrumbItem = {
  label: string
  to?: string
}

type PageBreadcrumbsProps = {
  items: BreadcrumbItem[]
  right?: ReactNode
}

export const PageBreadcrumbs = ({ items, right }: PageBreadcrumbsProps) => {
  return (
    <header
      className="app-header places-header"
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
        {items.map((item, index) => {
          const isLast = index === items.length - 1

          return (
            <div
              key={`${item.label}-${index}`}
              style={{ display: 'flex', alignItems: 'center', gap: '12px' }}
            >
              {item.to && !isLast ? (
                <Link
                  to={item.to}
                  style={{ color: '#2563eb', textDecoration: 'none', fontWeight: 600 }}
                >
                  {item.label}
                </Link>
              ) : (
                <span style={{ fontWeight: 700, color: '#0f172a' }}>{item.label}</span>
              )}

              {!isLast ? <span style={{ color: '#94a3b8' }}>/</span> : null}
            </div>
          )
        })}
      </div>

      {right ? <div>{right}</div> : null}
    </header>
  )
}
```

### `frontend/src/components/ui/SectionHeader.tsx`

```tsx
import type { ReactNode } from 'react'

type SectionHeaderProps = {
  eyebrow?: string
  title: string
  description?: string
  right?: ReactNode
}

export const SectionHeader = ({
  eyebrow,
  title,
  description,
  right,
}: SectionHeaderProps) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-end',
        justifyContent: 'space-between',
        gap: '16px',
        flexWrap: 'wrap',
      }}
    >
      <div>
        {eyebrow ? (
          <div
            style={{
              fontSize: '13px',
              fontWeight: 700,
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              color: '#64748b',
            }}
          >
            {eyebrow}
          </div>
        ) : null}

        <h2
          style={{
            margin: eyebrow ? '8px 0 0' : '0',
            fontSize: '42px',
            lineHeight: 0.98,
            letterSpacing: '-0.05em',
            fontWeight: 800,
            color: '#0f172a',
          }}
        >
          {title}
        </h2>

        {description ? (
          <p
            style={{
              marginTop: '10px',
              color: '#64748b',
              fontSize: '16px',
              lineHeight: 1.6,
              maxWidth: '760px',
            }}
          >
            {description}
          </p>
        ) : null}
      </div>

      {right ? <div>{right}</div> : null}
    </div>
  )
}
```

### `frontend/src/components/ui/SurfaceCard.tsx`

```tsx
import type { CSSProperties, ReactNode } from 'react'

type SurfaceCardProps = {
  children: ReactNode
  style?: CSSProperties
}

const baseStyle: CSSProperties = {
  background: 'rgba(255, 255, 255, 0.88)',
  borderRadius: '24px',
  border: '1px solid rgba(148, 163, 184, 0.18)',
  boxShadow: '0 14px 30px rgba(15, 23, 42, 0.05)',
  backdropFilter: 'blur(12px)',
}

export const SurfaceCard = ({ children, style }: SurfaceCardProps) => {
  return <div style={{ ...baseStyle, ...style }}>{children}</div>
}
```

### `frontend/src/entities/place/model/types.ts`

```ts
export type Place = {
  id: number
  slug: string
  title: string
  short_description: string | null
  image_url?: string | null
  category: string
  address: string
}

export type PlaceDetail = Place & {
  lat?: number
  lng?: number
  price_level?: number
  dog_friendly?: boolean
  family_friendly?: boolean
  indoor?: boolean
  outdoor?: boolean
  is_active?: boolean
}
```

### `frontend/src/features/place-search/model/filterPlaces.test.ts`

```ts
import { describe, expect, it } from 'vitest'
import type { Place } from '../../../entities/place/model/types'
import { filterPlaces } from './filterPlaces'

const places: Place[] = [
  {
    id: 1,
    slug: 'a',
    title: 'Кафе у моря',
    short_description: null,
    category: 'cafe',
    address: 'ул. Морская, 1',
  },
  {
    id: 2,
    slug: 'b',
    title: 'Музей истории',
    short_description: null,
    category: 'museum',
    address: 'ул. Ленина, 10',
  },
]

describe('filterPlaces', () => {
  it('returns all places for empty search', () => {
    expect(filterPlaces(places, '')).toHaveLength(2)
  })

  it('filters by title/category/address', () => {
    expect(filterPlaces(places, 'музей')).toHaveLength(1)
    expect(filterPlaces(places, 'cafe')).toHaveLength(1)
    expect(filterPlaces(places, 'морская')).toHaveLength(1)
  })
})
```

### `frontend/src/features/place-search/model/filterPlaces.ts`

```ts
import type { Place } from '../../../entities/place/model/types'

export const filterPlaces = (places: Place[], search: string): Place[] => {
  const normalizedSearch = search.trim().toLowerCase()

  if (!normalizedSearch) {
    return places
  }

  return places.filter((place) => {
    return (
      place.title.toLowerCase().includes(normalizedSearch) ||
      place.category.toLowerCase().includes(normalizedSearch) ||
      place.address.toLowerCase().includes(normalizedSearch)
    )
  })
}
```

### `frontend/src/index.css`

```css
:root {
  --text: #6b6375;
  --text-h: #08060d;
  --bg: #fff;
  --border: #e5e4e7;
  --code-bg: #f4f3ec;
  --accent: #aa3bff;
  --accent-bg: rgba(170, 59, 255, 0.1);
  --accent-border: rgba(170, 59, 255, 0.5);
  --social-bg: rgba(244, 243, 236, 0.5);
  --shadow:
    rgba(0, 0, 0, 0.1) 0 10px 15px -3px, rgba(0, 0, 0, 0.05) 0 4px 6px -2px;

  --sans: system-ui, 'Segoe UI', Roboto, sans-serif;
  --heading: system-ui, 'Segoe UI', Roboto, sans-serif;
  --mono: ui-monospace, Consolas, monospace;

  font: 18px/145% var(--sans);
  letter-spacing: 0.18px;
  color-scheme: light dark;
  color: var(--text);
  background: var(--bg);
  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;

  @media (max-width: 1024px) {
    font-size: 16px;
  }
}

@media (prefers-color-scheme: dark) {
  :root {
    --text: #9ca3af;
    --text-h: #f3f4f6;
    --bg: #16171d;
    --border: #2e303a;
    --code-bg: #1f2028;
    --accent: #c084fc;
    --accent-bg: rgba(192, 132, 252, 0.15);
    --accent-border: rgba(192, 132, 252, 0.5);
    --social-bg: rgba(47, 48, 58, 0.5);
    --shadow:
      rgba(0, 0, 0, 0.4) 0 10px 15px -3px, rgba(0, 0, 0, 0.25) 0 4px 6px -2px;
  }

  #social .button-icon {
    filter: invert(1) brightness(2);
  }
}

#root {
  width: 100%;
  max-width: 100%;
  margin: 0;
  text-align: left;
  min-height: 100svh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
}

body {
  margin: 0;
}

h1,
h2 {
  font-family: var(--heading);
  font-weight: 500;
  color: var(--text-h);
}

h1 {
  font-size: 56px;
  letter-spacing: -1.68px;
  margin: 32px 0;
  @media (max-width: 1024px) {
    font-size: 36px;
    margin: 20px 0;
  }
}
h2 {
  font-size: 24px;
  line-height: 118%;
  letter-spacing: -0.24px;
  margin: 0 0 8px;
  @media (max-width: 1024px) {
    font-size: 20px;
  }
}
p {
  margin: 0;
}

code,
.counter {
  font-family: var(--mono);
  display: inline-flex;
  border-radius: 4px;
  color: var(--text-h);
}

code {
  font-size: 15px;
  line-height: 135%;
  padding: 4px 8px;
  background: var(--code-bg);
}
```

### `frontend/src/main.tsx`

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

### `frontend/src/pages/home/HomePage.test.tsx`

```tsx
/* @vitest-environment jsdom */
import '@testing-library/jest-dom/vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { HomePage } from './HomePage'
import { getPlacesByCity } from '../../api/places/places.api'

vi.mock('../../api/places/places.api', () => ({
  getPlacesByCity: vi.fn(),
}))

const mockedGetPlacesByCity = vi.mocked(getPlacesByCity)

describe('HomePage', () => {
  afterEach(() => {
    vi.clearAllMocks()
  })

  it('renders main heading, places count and place card after loading', async () => {
    mockedGetPlacesByCity.mockResolvedValueOnce([
      {
        id: 1,
        slug: 'mesto-1',
        title: 'Кофейня у моря',
        short_description: 'Вкусный кофе',
        category: 'cafe',
        address: 'ул. Морская, 1',
      },
      {
        id: 2,
        slug: 'mesto-2',
        title: 'Музей янтаря',
        short_description: null,
        category: 'museum',
        address: 'ул. Центральная, 5',
      },
    ])

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', { name: 'Найди куда сходить в Зеленоградске' }),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('2 найдено')).toBeInTheDocument()
    })

    expect(screen.getByText('Кофейня у моря')).toBeInTheDocument()
  })

  it('renders error state when places loading fails', async () => {
    mockedGetPlacesByCity.mockRejectedValueOnce(new Error('network error'))

    render(
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>,
    )

    await waitFor(() => {
      expect(screen.getByText('Не удалось загрузить places с backend')).toBeInTheDocument()
    })
  })
})
```

### `frontend/src/pages/home/HomePage.tsx`

```tsx
import { useEffect, useMemo, useState } from 'react'
import { getPlacesByCity } from '../../api/places/places.api'
import { AppHeader } from '../../components/ui/AppHeader'
import type { Place } from '../../entities/place/model/types'
import { filterPlaces } from '../../features/place-search/model/filterPlaces'
import { HomeHero } from '../../widgets/home/HomeHero'
import { HomeStats } from '../../widgets/home/HomeStats'
import { PlacesSection } from '../../widgets/home/PlacesSection'

export const HomePage = () => {
  const [places, setPlaces] = useState<Place[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    const loadPlaces = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await getPlacesByCity('zelenogradsk')
        setPlaces(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить places с backend')
      } finally {
        setLoading(false)
      }
    }

    loadPlaces()
  }, [])

  const filteredPlaces = useMemo(() => filterPlaces(places, search), [places, search])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />
        <HomeHero search={search} onSearchChange={setSearch} />
        <HomeStats loading={loading} placesCount={filteredPlaces.length} />
        <PlacesSection loading={loading} error={error} places={filteredPlaces} />
      </div>
    </div>
  )
}
```

### `frontend/src/pages/nearby/NearbyPage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getNearbyPlaces, type NearbyPlace } from '../../api/nearby/nearby.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'

const FALLBACK_LAT = 54.9587
const FALLBACK_LNG = 20.475
const RADIUS_OPTIONS = [0.1, 0.3, 1]

export const NearbyPage = () => {
  const [places, setPlaces] = useState<NearbyPlace[]>([])
  const [radiusKm, setRadiusKm] = useState(0.3)
  const [lat, setLat] = useState(FALLBACK_LAT)
  const [lng, setLng] = useState(FALLBACK_LNG)
  const [locationLabel, setLocationLabel] = useState('Тестовая точка')
  const [loading, setLoading] = useState(true)
  const [locating, setLocating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPlaces = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await getNearbyPlaces(lat, lng, radiusKm)
        setPlaces(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить nearby с backend')
      } finally {
        setLoading(false)
      }
    }

    loadPlaces()
  }, [lat, lng, radiusKm])

  const handleUseMyLocation = () => {
    if (!navigator.geolocation) {
      setError('Браузер не поддерживает геолокацию')
      return
    }

    setLocating(true)
    setError(null)

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLat(Number(position.coords.latitude.toFixed(6)))
        setLng(Number(position.coords.longitude.toFixed(6)))
        setLocationLabel('Моя геолокация')
        setLocating(false)
      },
      () => {
        setError('Не удалось получить геолокацию. Оставили тестовую точку.')
        setLocating(false)
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      },
    )
  }

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Nearby' },
          ]}
          right={
            <div style={{ color: '#64748b' }}>
              {loading ? 'Загрузка...' : `${places.length} рядом`}
            </div>
          }
        />

        <section className="places-list-panel">
          <SectionHeader
            title="Nearby"
            description="Места рядом с вашей точкой. По умолчанию используется тестовая точка в Зеленоградске."
          />

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            <Badge variant="brand">{locationLabel}</Badge>
            <Badge variant="neutral">lat: {lat}</Badge>
            <Badge variant="neutral">lng: {lng}</Badge>
          </div>

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            {RADIUS_OPTIONS.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setRadiusKm(value)}
                style={{
                  minHeight: '40px',
                  padding: '0 14px',
                  borderRadius: '999px',
                  border:
                    value === radiusKm
                      ? '1px solid rgba(37, 99, 235, 0.18)'
                      : '1px solid rgba(148, 163, 184, 0.18)',
                  background: value === radiusKm ? '#eff6ff' : 'rgba(255, 255, 255, 0.78)',
                  color: value === radiusKm ? '#2563eb' : '#334155',
                  fontSize: '14px',
                  fontWeight: 700,
                  cursor: 'pointer',
                }}
              >
                {value} km
              </button>
            ))}

            <button
              type="button"
              onClick={handleUseMyLocation}
              disabled={locating}
              style={{
                minHeight: '40px',
                padding: '0 14px',
                borderRadius: '999px',
                border: '1px solid rgba(37, 99, 235, 0.18)',
                background: '#eff6ff',
                color: '#2563eb',
                fontSize: '14px',
                fontWeight: 700,
                cursor: locating ? 'default' : 'pointer',
                opacity: locating ? 0.7 : 1,
              }}
            >
              {locating ? 'Определяем...' : 'Использовать мою геолокацию'}
            </button>
          </div>
        </section>

        {error && (
          <section style={{ marginTop: '16px' }}>
            <div
              style={{
                background: '#fee2e2',
                color: '#991b1b',
                borderRadius: '16px',
                padding: '16px',
              }}
            >
              {error}
            </div>
          </section>
        )}

        {!loading && !error && places.length === 0 && (
          <section style={{ marginTop: '16px' }}>
            <EmptyState message="Рядом ничего не найдено." />
          </section>
        )}

        {!error && places.length > 0 && (
          <section className="places-grid" style={{ marginTop: '18px' }}>
            {places.map((place) => (
              <SurfaceCard
                key={place.id}
                style={{
                  padding: '20px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '10px',
                    flexWrap: 'wrap',
                  }}
                >
                  <Badge variant="brand" uppercase>
                    {place.category}
                  </Badge>

                  <Badge variant="success">{place.distance_km} km</Badge>
                </div>

                <h3 style={{ marginTop: '14px', marginBottom: '8px' }}>{place.title}</h3>
                <p style={{ margin: 0, color: '#64748b' }}>{place.address}</p>

                <div style={{ marginTop: '14px' }}>
                  <Link className="place-card-link-secondary" to={`/places/${place.slug}`}>
                    Подробнее
                  </Link>
                </div>
              </SurfaceCard>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
```

### `frontend/src/pages/open-now/OpenNowPage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { getOpenNowPlaces, type OpenNowPlace } from '../../api/open-now/openNow.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { EmptyState } from '../../components/ui/EmptyState'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'

export const OpenNowPage = () => {
  const [places, setPlaces] = useState<OpenNowPlace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPlaces = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await getOpenNowPlaces('zelenogradsk')
        setPlaces(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить open-now с backend')
      } finally {
        setLoading(false)
      }
    }

    loadPlaces()
  }, [])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Open Now' },
          ]}
          right={
            <div style={{ color: '#64748b' }}>
              {loading ? 'Загрузка...' : `${places.length} открыто сейчас`}
            </div>
          }
        />

        <section className="places-list-panel">
          <SectionHeader
            title="Open Now"
            description="Места Зеленоградска, которые открыты прямо сейчас."
          />
        </section>

        {error && (
          <section style={{ marginTop: '16px' }}>
            <div
              style={{
                background: '#fee2e2',
                color: '#991b1b',
                borderRadius: '16px',
                padding: '16px',
              }}
            >
              {error}
            </div>
          </section>
        )}

        {!loading && !error && places.length === 0 && (
          <section style={{ marginTop: '16px' }}>
            <EmptyState message="Сейчас нет мест, которые отмечены как открытые." />
          </section>
        )}

        {!error && places.length > 0 && (
          <section className="places-grid" style={{ marginTop: '18px' }}>
            {places.map((place) => (
              <SurfaceCard
                key={place.id}
                style={{
                  padding: '20px',
                }}
              >
                <Badge variant="success" uppercase>
                  open now
                </Badge>

                <h3 style={{ marginTop: '14px', marginBottom: '8px' }}>{place.title}</h3>
                <p style={{ margin: 0, color: '#64748b' }}>{place.address}</p>
                <p style={{ marginTop: '12px', color: '#334155', fontWeight: 600 }}>
                  {place.open_time} — {place.close_time}
                </p>

                <div style={{ marginTop: '14px' }}>
                  <Link className="place-card-link-secondary" to={`/places/${place.slug}`}>
                    Подробнее
                  </Link>
                </div>
              </SurfaceCard>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
```

### `frontend/src/pages/places/PlaceDetailPage.tsx`

```tsx
import { Compass, MapPin } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getPlaceBySlug } from '../../api/places/places.api'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import type { PlaceDetail } from '../../entities/place/model/types'

const BooleanBadge = ({ label, value }: { label: string; value: boolean | undefined }) => {
  if (value === undefined) {
    return null
  }

  return (
    <Badge variant={value ? 'success' : 'neutral'}>
      {label}: {value ? 'да' : 'нет'}
    </Badge>
  )
}

export const PlaceDetailPage = () => {
  const { slug } = useParams<{ slug: string }>()
  const [place, setPlace] = useState<PlaceDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadPlace = async () => {
      if (!slug) {
        setError('Некорректный slug места')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError(null)
        const data = await getPlaceBySlug(slug)
        setPlace(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить место')
      } finally {
        setLoading(false)
      }
    }

    loadPlace()
  }, [slug])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Places', to: '/places' },
            { label: 'Detail' },
          ]}
        />

        {loading && (
          <section className="places-list-panel">
            <p style={{ color: '#64748b' }}>Загрузка места...</p>
          </section>
        )}

        {error && !loading && (
          <section className="places-list-panel">
            <div
              style={{
                background: '#fee2e2',
                color: '#991b1b',
                borderRadius: '16px',
                padding: '16px',
              }}
            >
              {error}
            </div>
          </section>
        )}

        {!loading && !error && place && (
          <>
            <section
              style={{
                position: 'relative',
                overflow: 'hidden',
                borderRadius: '32px',
                background:
                  'radial-gradient(circle at top right, rgba(96, 165, 250, 0.22), transparent 24%), linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                boxShadow: '0 20px 40px rgba(15, 23, 42, 0.06)',
              }}
            >
              {place.image_url ? (
                <img
                  src={place.image_url}
                  alt={place.title}
                  style={{
                    width: '100%',
                    height: '320px',
                    objectFit: 'cover',
                    display: 'block',
                    background: '#e2e8f0',
                  }}
                />
              ) : (
                <div
                  style={{
                    height: '220px',
                    background:
                      'radial-gradient(circle at top right, rgba(96, 165, 250, 0.22), transparent 24%), linear-gradient(135deg, #ffffff 0%, #f8fafc 100%)',
                  }}
                />
              )}

              <div style={{ padding: '36px' }}>
                <div
                  style={{
                    width: '56px',
                    height: '56px',
                    borderRadius: '18px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    background:
                      'linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(99, 102, 241, 0.2))',
                    color: '#1d4ed8',
                    border: '1px solid rgba(37, 99, 235, 0.12)',
                  }}
                >
                  <Compass size={24} />
                </div>

                <div style={{ marginTop: '18px' }}>
                  <Badge variant="brand" uppercase>
                    {place.category}
                  </Badge>
                </div>

                <SectionHeader
                  title={place.title}
                  description={place.short_description ?? 'Описание пока не добавлено.'}
                />

                <div
                  style={{
                    marginTop: '16px',
                    display: 'flex',
                    gap: '10px',
                    alignItems: 'flex-start',
                    color: '#64748b',
                    fontSize: '18px',
                    lineHeight: 1.6,
                    maxWidth: '760px',
                  }}
                >
                  <MapPin size={18} style={{ marginTop: '5px', flexShrink: 0 }} />
                  <span>{place.address}</span>
                </div>
              </div>
            </section>

            <section
              className="places-list-panel"
              style={{
                marginTop: '20px',
              }}
            >
              <SectionHeader eyebrow="Quick facts" title="Детали места" />

              <div
                style={{
                  marginTop: '16px',
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '10px',
                }}
              >
                <BooleanBadge label="С собакой" value={place.dog_friendly} />
                <BooleanBadge label="С семьей" value={place.family_friendly} />
                <BooleanBadge label="В помещении" value={place.indoor} />
                <BooleanBadge label="На улице" value={place.outdoor} />
                <BooleanBadge label="Активно" value={place.is_active} />

                {place.price_level !== undefined && (
                  <Badge variant="neutral">Цена: {place.price_level}</Badge>
                )}
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  )
}
```

### `frontend/src/pages/places/PlacesListPage.tsx`

```tsx
import { Search } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getPlacesByCity } from '../../api/places/places.api'
import { PlaceCard } from '../../components/places/PlaceCard'
import { AppHeader } from '../../components/ui/AppHeader'
import { EmptyState } from '../../components/ui/EmptyState'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'
import type { Place } from '../../entities/place/model/types'
import { filterPlaces } from '../../features/place-search/model/filterPlaces'

const FILTER_CHIPS = [
  { label: 'Все', value: '' },
  { label: 'Cafe', value: 'cafe' },
  { label: 'Walk', value: 'walk' },
  { label: 'Dog-friendly', value: 'dog' },
  { label: 'Море', value: 'море' },
]

export const PlacesListPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const queryValue = searchParams.get('q') ?? ''

  const [places, setPlaces] = useState<Place[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState(queryValue)

  useEffect(() => {
    const loadPlaces = async () => {
      try {
        setLoading(true)
        setError(null)
        const data = await getPlacesByCity('zelenogradsk')
        setPlaces(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить places с backend')
      } finally {
        setLoading(false)
      }
    }

    loadPlaces()
  }, [])

  useEffect(() => {
    setSearch(queryValue)
  }, [queryValue])

  const filteredPlaces = useMemo(() => filterPlaces(places, search), [places, search])
  const isEmpty = !loading && !error && filteredPlaces.length === 0

  const handleChipClick = (value: string) => {
    setSearch(value)

    if (value) {
      setSearchParams({ q: value })
      return
    }

    setSearchParams({})
  }

  const handleSearchChange = (value: string) => {
    setSearch(value)

    const trimmed = value.trim()

    if (trimmed) {
      setSearchParams({ q: trimmed })
      return
    }

    setSearchParams({})
  }

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Places List' },
          ]}
          right={
            <div style={{ color: '#64748b' }}>
              {loading ? 'Загрузка...' : `${filteredPlaces.length} мест`}
            </div>
          }
        />

        <section className="places-list-panel">
          <SectionHeader
            title="Places"
            description="Список мест Зеленоградска на основе текущих данных backend."
          />

          <div className="places-search">
            <Search size={18} color="#64748b" />
            <input
              type="text"
              placeholder="Поиск мест, категорий и адресов..."
              value={search}
              onChange={(event) => handleSearchChange(event.target.value)}
            />
          </div>

          <div
            style={{
              marginTop: '16px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            {FILTER_CHIPS.map((chip) => {
              const isActive = search.trim().toLowerCase() === chip.value.toLowerCase()

              return (
                <button
                  key={chip.label}
                  type="button"
                  onClick={() => handleChipClick(chip.value)}
                  style={{
                    minHeight: '40px',
                    padding: '0 14px',
                    borderRadius: '999px',
                    border: isActive
                      ? '1px solid rgba(37, 99, 235, 0.18)'
                      : '1px solid rgba(148, 163, 184, 0.18)',
                    background: isActive ? '#eff6ff' : 'rgba(255, 255, 255, 0.78)',
                    color: isActive ? '#2563eb' : '#334155',
                    fontSize: '14px',
                    fontWeight: 700,
                    cursor: 'pointer',
                  }}
                >
                  {chip.label}
                </button>
              )
            })}
          </div>
        </section>

        {error && (
          <section style={{ marginTop: '16px' }}>
            <SurfaceCard style={{ background: '#fee2e2', color: '#991b1b', padding: '16px' }}>
              {error}
            </SurfaceCard>
          </section>
        )}

        {isEmpty && (
          <section style={{ marginTop: '16px' }}>
            <EmptyState message="По вашему запросу ничего не найдено." />
          </section>
        )}

        {!error && !isEmpty && (
          <section className="places-grid" style={{ marginTop: '18px' }}>
            {filteredPlaces.map((place) => (
              <PlaceCard key={place.id} place={place} />
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
```

### `frontend/src/pages/routes/RoutesPage.tsx`

```tsx
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'

const routePoints = [
  {
    id: 1,
    title: 'Курортный проспект',
    description: 'Старт прогулки по центральной части города с архитектурой и туристической атмосферой.',
    duration: '15 мин',
  },
  {
    id: 2,
    title: 'Променад',
    description: 'Выход к морю, прогулка вдоль берега и обзор ключевых точек на набережной.',
    duration: '25 мин',
  },
  {
    id: 3,
    title: 'Пирс и видовая точка',
    description: 'Финальная остановка с открытым видом и хорошей точкой для паузы.',
    duration: '20 мин',
  },
]

export const WalkRoutePage = () => {
  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Walk Route' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow="Walking route"
            title="Пешая прогулка по достопримечательностям"
            description="Черновой MVP-экран под маршрутный сценарий. Позже сюда добавим реальные маршруты, общественный транспорт, длительность, расстояние и построение пути."
          />

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            <Badge variant="brand">Зеленоградск</Badge>
            <Badge variant="neutral">Пешком</Badge>
            <Badge variant="neutral">≈ 60 мин</Badge>
            <Badge variant="neutral">3 точки</Badge>
          </div>
        </section>

        <section
          style={{
            marginTop: '18px',
            display: 'grid',
            gap: '16px',
          }}
        >
          {routePoints.map((point, index) => (
            <SurfaceCard
              key={point.id}
              style={{
                padding: '20px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  justifyContent: 'space-between',
                  gap: '12px',
                  flexWrap: 'wrap',
                }}
              >
                <div>
                  <div
                    style={{
                      fontSize: '13px',
                      fontWeight: 700,
                      letterSpacing: '0.08em',
                      textTransform: 'uppercase',
                      color: '#64748b',
                    }}
                  >
                    Точка {index + 1}
                  </div>

                  <h3
                    style={{
                      margin: '8px 0 0',
                      fontSize: '26px',
                      lineHeight: 1.05,
                      letterSpacing: '-0.04em',
                      color: '#0f172a',
                    }}
                  >
                    {point.title}
                  </h3>
                </div>

                <Badge variant="success">{point.duration}</Badge>
              </div>

              <p
                style={{
                  marginTop: '14px',
                  color: '#475569',
                  fontSize: '15px',
                  lineHeight: 1.6,
                }}
              >
                {point.description}
              </p>
            </SurfaceCard>
          ))}
        </section>
      </div>
    </div>
  )
}
```

### `frontend/src/pages/routes/WalkRoutePage.tsx`

```tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AppHeader } from '../../components/ui/AppHeader'
import { Badge } from '../../components/ui/Badge'
import { PageBreadcrumbs } from '../../components/ui/PageBreadcrumbs'
import { SectionHeader } from '../../components/ui/SectionHeader'
import { SurfaceCard } from '../../components/ui/SurfaceCard'

type RoutePoint = {
  place_id: number
  position: number
  place_slug?: string | null
  place_title?: string | null
}

type RouteDetail = {
  id: number
  city_id: number
  slug: string
  title: string
  short_description?: string | null
  duration_minutes?: number | null
  is_active: boolean
  points: RoutePoint[]
}

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export const WalkRoutePage = () => {
  const [route, setRoute] = useState<RouteDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadRoute = async () => {
      try {
        setLoading(true)
        setError(null)

        const response = await fetch(
          `${API_BASE_URL}/routes/by-slug/seaside-walk-zelenogradsk`,
        )

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`)
        }

        const data: RouteDetail = await response.json()
        setRoute(data)
      } catch (err) {
        console.error(err)
        setError('Не удалось загрузить маршрут с backend')
      } finally {
        setLoading(false)
      }
    }

    loadRoute()
  }, [])

  return (
    <div className="app-screen">
      <div className="app-container">
        <AppHeader />

        <PageBreadcrumbs
          items={[
            { label: 'Home', to: '/' },
            { label: 'Walk Route' },
          ]}
        />

        <section className="places-list-panel">
          <SectionHeader
            eyebrow="Walking route"
            title={loading ? 'Загрузка маршрута...' : route?.title ?? 'Маршрут прогулки'}
            description={
              error ||
              route?.short_description ||
              'Пешая прогулка по достопримечательностям города.'
            }
          />

          <div
            style={{
              marginTop: '18px',
              display: 'flex',
              gap: '10px',
              flexWrap: 'wrap',
            }}
          >
            <Badge variant="brand">Зеленоградск</Badge>
            <Badge variant="neutral">Пешком</Badge>
            <Badge variant="neutral">
              {route?.duration_minutes ? `≈ ${route.duration_minutes} мин` : 'Маршрут'}
            </Badge>
            <Badge variant="neutral">
              {route ? `${route.points.length} точки` : '...'}
            </Badge>
          </div>
        </section>

        {error && (
          <section style={{ marginTop: '18px' }}>
            <SurfaceCard style={{ padding: '20px' }}>
              <p style={{ margin: 0, color: '#b91c1c' }}>{error}</p>
            </SurfaceCard>
          </section>
        )}

        {!error && (
          <section
            style={{
              marginTop: '18px',
              display: 'grid',
              gap: '16px',
            }}
          >
            {(route?.points ?? []).map((point, index) => (
              <SurfaceCard
                key={`${point.place_id}-${point.position}`}
                style={{
                  padding: '20px',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    justifyContent: 'space-between',
                    gap: '12px',
                    flexWrap: 'wrap',
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: '13px',
                        fontWeight: 700,
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                        color: '#64748b',
                      }}
                    >
                      Точка {index + 1}
                    </div>

                    {point.place_slug ? (
                      <Link
                        to={`/places/${point.place_slug}`}
                        style={{
                          display: 'inline-block',
                          marginTop: '8px',
                          fontSize: '26px',
                          lineHeight: 1.05,
                          letterSpacing: '-0.04em',
                          color: '#0f172a',
                          textDecoration: 'none',
                          fontWeight: 700,
                        }}
                      >
                        {point.place_title ?? `Place #${point.place_id}`}
                      </Link>
                    ) : (
                      <h3
                        style={{
                          margin: '8px 0 0',
                          fontSize: '26px',
                          lineHeight: 1.05,
                          letterSpacing: '-0.04em',
                          color: '#0f172a',
                        }}
                      >
                        {point.place_title ?? `Place #${point.place_id}`}
                      </h3>
                    )}
                  </div>

                  <Badge variant="success">#{point.position}</Badge>
                </div>

                {point.place_slug && (
                  <p
                    style={{
                      marginTop: '14px',
                      color: '#475569',
                      fontSize: '15px',
                      lineHeight: 1.6,
                    }}
                  >
                    <Link
                      to={`/places/${point.place_slug}`}
                      style={{
                        color: '#2563eb',
                        textDecoration: 'none',
                        fontWeight: 600,
                      }}
                    >
                      Открыть точку маршрута
                    </Link>
                  </p>
                )}
              </SurfaceCard>
            ))}
          </section>
        )}
      </div>
    </div>
  )
}
```

### `frontend/src/shared/api/endpoints.test.ts`

```ts
import { describe, expect, it } from 'vitest'
import { buildPlacesUrl } from './endpoints'

describe('buildPlacesUrl', () => {
  it('builds URL with city_slug query', () => {
    expect(buildPlacesUrl('zelenogradsk')).toBe('/places/?city_slug=zelenogradsk')
  })
})
```

### `frontend/src/shared/api/endpoints.ts`

```ts
export const endpoints = {
  places: '/places/',
  placeBySlug: '/places/by-slug',
}

export const buildPlacesUrl = (citySlug: string): string => {
  const params = new URLSearchParams({ city_slug: citySlug })
  return `${endpoints.places}?${params.toString()}`
}

export const buildPlaceBySlugUrl = (slug: string): string => {
  return `${endpoints.placeBySlug}/${encodeURIComponent(slug)}`
}
```

### `frontend/src/shared/api/http.ts`

```ts
import { env } from '../config/env'

export const buildApiUrl = (path: string): string => {
  return `${env.apiBaseUrl}${path}`
}
```

### `frontend/src/shared/config/env.ts`

```ts
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000'

export const env = {
  apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL,
}
```

### `frontend/src/styles/responsive.css`

```css
.app-screen {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(37, 99, 235, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  color: #0f172a;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.app-container {
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 40px;
  box-sizing: border-box;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.home-header {
  margin-bottom: 24px;
}

.places-header {
  margin-bottom: 20px;
}

.home-badge {
  display: inline-flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.22);
  backdrop-filter: blur(12px);
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}

.hero-section {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 20%, rgba(96, 165, 250, 0.35), transparent 22%),
    radial-gradient(circle at 80% 0%, rgba(167, 139, 250, 0.25), transparent 20%),
    linear-gradient(135deg, #0f172a 0%, #172554 45%, #1e293b 100%);
  color: #ffffff;
  border-radius: 32px;
  padding: 40px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 24px 60px rgba(15, 23, 42, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.hero-title {
  margin: 18px 0 0;
  font-size: 60px;
  line-height: 0.96;
  letter-spacing: -0.05em;
  max-width: 760px;
  color: #ffffff;
  font-weight: 800;
}

.hero-text {
  margin: 18px 0 0;
  max-width: 720px;
  color: rgba(255, 255, 255, 0.76);
  font-size: 19px;
  line-height: 1.6;
}

.hero-search {
  margin-top: 28px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 18px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
}

.hero-search input,
.places-search input {
  border: none;
  outline: none;
  width: 100%;
  background: transparent;
  color: #0f172a;
  font-family: inherit;
}

.hero-search input {
  font-size: 16px;
}

.hero-cta-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  backdrop-filter: blur(10px);
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.hero-cta-link:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.24);
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
}

.stats-grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.places-section {
  margin-top: 30px;
}

.places-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.section-link {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  transition: color 0.18s ease, opacity 0.18s ease;
}

.section-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.places-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.places-list-panel {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-radius: 28px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 26px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.places-list-title {
  margin: 0;
  font-size: 44px;
  line-height: 0.98;
  letter-spacing: -0.05em;
  font-weight: 800;
  color: #0f172a;
}

.places-search {
  margin-top: 18px;
  background: #f8fafc;
  border-radius: 18px;
  border: 1px solid #dbe3ee;
  padding: 13px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.places-search:focus-within {
  border-color: rgba(37, 99, 235, 0.32);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

.places-search input {
  font-size: 15px;
}

.place-card-body {
  padding: 22px;
}

.place-card-title {
  margin: 14px 0 0;
  font-size: 30px;
  line-height: 1.05;
  letter-spacing: -0.04em;
  font-weight: 800;
  color: #0f172a;
}

.place-card-link {
  color: #0f172a;
  text-decoration: none;
  transition: color 0.18s ease;
}

.place-card-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.place-card-link-secondary {
  color: #2563eb;
  text-decoration: none;
  font-weight: 700;
  font-size: 14px;
  transition: color 0.18s ease, opacity 0.18s ease;
}

.place-card-link-secondary:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

button {
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    color 0.18s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

@media (max-width: 1024px) {
  .app-container {
    padding: 22px 18px 32px;
  }

  .hero-section {
    border-radius: 26px;
    padding: 30px;
  }

  .hero-title {
    font-size: 44px;
  }

  .hero-text {
    font-size: 17px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .places-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .places-list-title {
    font-size: 36px;
  }

  .place-card-title {
    font-size: 24px;
  }
}

@media (max-width: 640px) {
  .app-container {
    padding: 14px 14px 24px;
  }

  .app-header,
  .places-section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .home-header {
    margin-bottom: 18px;
  }

  .hero-section {
    border-radius: 22px;
    padding: 20px;
  }

  .hero-title {
    font-size: 34px;
    line-height: 1.02;
  }

  .hero-text {
    font-size: 15px;
  }

  .hero-search {
    margin-top: 18px;
    padding: 12px 13px;
    border-radius: 16px;
  }

  .hero-cta-link {
    width: 100%;
    box-sizing: border-box;
  }

  .stats-grid,
  .places-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .places-list-panel {
    border-radius: 22px;
    padding: 18px;
  }

  .places-list-title {
    font-size: 30px;
  }

  .place-card-title {
    font-size: 22px;
  }

  .place-card-body {
    padding: 18px;
  }
}
.app-screen {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(37, 99, 235, 0.08), transparent 28%),
    linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
  color: #0f172a;
  font-family:
    Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

.app-container {
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 40px;
  box-sizing: border-box;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.home-header {
  margin-bottom: 24px;
}

.places-header {
  margin-bottom: 20px;
}

.home-badge {
  display: inline-flex;
  align-items: center;
  padding: 10px 14px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.22);
  backdrop-filter: blur(12px);
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  white-space: nowrap;
}

.hero-section {
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 20% 20%, rgba(96, 165, 250, 0.35), transparent 22%),
    radial-gradient(circle at 80% 0%, rgba(167, 139, 250, 0.25), transparent 20%),
    linear-gradient(135deg, #0f172a 0%, #172554 45%, #1e293b 100%);
  color: #ffffff;
  border-radius: 32px;
  padding: 40px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow:
    0 24px 60px rgba(15, 23, 42, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
}

.hero-title {
  margin: 18px 0 0;
  font-size: 60px;
  line-height: 0.96;
  letter-spacing: -0.05em;
  max-width: 760px;
  color: #ffffff;
  font-weight: 800;
}

.hero-text {
  margin: 18px 0 0;
  max-width: 720px;
  color: rgba(255, 255, 255, 0.76);
  font-size: 19px;
  line-height: 1.6;
}

.hero-search {
  margin-top: 28px;
  background: rgba(255, 255, 255, 0.96);
  border-radius: 18px;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  gap: 12px;
  border: 1px solid rgba(255, 255, 255, 0.7);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.12);
}

.hero-search input,
.places-search input {
  border: none;
  outline: none;
  width: 100%;
  background: transparent;
  color: #0f172a;
  font-family: inherit;
}

.hero-search input {
  font-size: 16px;
}

.hero-cta-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 44px;
  padding: 0 16px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff;
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  backdrop-filter: blur(10px);
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.hero-cta-link:hover {
  background: rgba(255, 255, 255, 0.14);
  border-color: rgba(255, 255, 255, 0.24);
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.18);
}

.stats-grid {
  margin-top: 22px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.places-section {
  margin-top: 30px;
}

.places-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.section-link {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
  font-size: 14px;
  white-space: nowrap;
  transition: color 0.18s ease, opacity 0.18s ease;
}

.section-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.places-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 20px;
}

.places-list-panel {
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(14px);
  border-radius: 28px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 26px;
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.06);
}

.places-list-title {
  margin: 0;
  font-size: 44px;
  line-height: 0.98;
  letter-spacing: -0.05em;
  font-weight: 800;
  color: #0f172a;
}

.places-search {
  margin-top: 18px;
  background: #f8fafc;
  border-radius: 18px;
  border: 1px solid #dbe3ee;
  padding: 13px 14px;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.places-search:focus-within {
  border-color: rgba(37, 99, 235, 0.32);
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

.places-search input {
  font-size: 15px;
}

.place-card-body {
  padding: 22px;
}

.place-card-title {
  margin: 14px 0 0;
  font-size: 30px;
  line-height: 1.05;
  letter-spacing: -0.04em;
  font-weight: 800;
  color: #0f172a;
}

.place-card-link {
  color: #0f172a;
  text-decoration: none;
  transition: color 0.18s ease;
}

.place-card-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

.place-card-link-secondary {
  color: #2563eb;
  text-decoration: none;
  font-weight: 700;
  font-size: 14px;
  transition: color 0.18s ease, opacity 0.18s ease;
}

.place-card-link-secondary:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

button {
  transition:
    transform 0.18s ease,
    background 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    color 0.18s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(15, 23, 42, 0.08);
}

@media (max-width: 1024px) {
  .app-container {
    padding: 22px 18px 32px;
  }

  .hero-section {
    border-radius: 26px;
    padding: 30px;
  }

  .hero-title {
    font-size: 44px;
  }

  .hero-text {
    font-size: 17px;
  }

  .stats-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .places-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .places-list-title {
    font-size: 36px;
  }

  .place-card-title {
    font-size: 24px;
  }
}

@media (max-width: 640px) {
  .app-container {
    padding: 14px 14px 24px;
  }

  .app-header,
  .places-section-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .home-header {
    margin-bottom: 18px;
  }

  .hero-section {
    border-radius: 22px;
    padding: 20px;
  }

  .hero-title {
    font-size: 34px;
    line-height: 1.02;
  }

  .hero-text {
    font-size: 15px;
  }

  .hero-search {
    margin-top: 18px;
    padding: 12px 13px;
    border-radius: 16px;
  }

  .hero-cta-link {
    width: 100%;
    box-sizing: border-box;
  }

  .stats-grid,
  .places-grid {
    grid-template-columns: 1fr;
    gap: 14px;
  }

  .places-list-panel {
    border-radius: 22px;
    padding: 18px;
  }

  .places-list-title {
    font-size: 30px;
  }

  .place-card-title {
    font-size: 22px;
  }

  .place-card-body {
    padding: 18px;
  }
}
```

### `frontend/src/widgets/home/HomeHero.tsx`

```tsx
import { Search, Sparkles } from 'lucide-react'
import { AppLink } from '../../components/ui/AppLink'

type HomeHeroProps = {
  search: string
  onSearchChange: (value: string) => void
}

export const HomeHero = ({ search, onSearchChange }: HomeHeroProps) => {
  const normalizedSearch = search.trim()
  const placesLink = normalizedSearch
    ? `/places?q=${encodeURIComponent(normalizedSearch)}`
    : '/places'

  return (
    <section className="hero-section">
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 12px',
          borderRadius: '999px',
          background: 'rgba(255,255,255,0.12)',
          fontSize: '14px',
        }}
      >
        <Sparkles size={16} />
        Городской гид нового формата
      </div>

      <h1 className="hero-title">Найди куда сходить в Зеленоградске</h1>

      <p className="hero-text">
        Places, nearby, открыто сейчас, прогулочные маршруты, подборки и
        сценарии отдыха в одном интерфейсе.
      </p>

      <div className="hero-search">
        <Search size={20} color="#64748b" />
        <input
          type="text"
          placeholder="Поиск мест, кафе, музеев, адресов..."
          value={search}
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </div>

      <div
        style={{
          marginTop: '16px',
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <AppLink to={placesLink} variant="primary">
          Искать места
        </AppLink>

        <AppLink to="/nearby" variant="primary">
          Рядом
        </AppLink>

        <AppLink to="/open-now" variant="primary">
          Открыто сейчас
        </AppLink>

        <AppLink to="/walk-route" variant="primary">
          Маршрут прогулки
        </AppLink>
      </div>
    </section>
  )
}
```

### `frontend/src/widgets/home/HomeStats.tsx`

```tsx
import { ArrowRight, Clock3, MapPinned, Route, Trees } from 'lucide-react'
import { AppLink } from '../../components/ui/AppLink'
import { SurfaceCard } from '../../components/ui/SurfaceCard'

type HomeStatsProps = {
  loading: boolean
  placesCount: number
}

const topRowStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '12px',
} as const

const iconWrapStyle = {
  width: '38px',
  height: '38px',
  borderRadius: '14px',
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: '#eff6ff',
  color: '#2563eb',
  border: '1px solid rgba(37, 99, 235, 0.12)',
} as const

const arrowStyle = {
  color: '#94a3b8',
} as const

export const HomeStats = ({ loading, placesCount }: HomeStatsProps) => {
  return (
    <section className="stats-grid">
      <AppLink to="/places" variant="secondary">
        <SurfaceCard style={{ padding: '20px' }}>
          <div style={topRowStyle}>
            <div style={iconWrapStyle}>
              <MapPinned size={18} />
            </div>
            <ArrowRight size={16} style={arrowStyle} />
          </div>

          <div style={{ marginTop: '16px', color: '#64748b', fontSize: '13px', fontWeight: 600 }}>
            Places
          </div>

          <div style={{ marginTop: '8px', fontSize: '34px', fontWeight: 800, color: '#0f172a', lineHeight: 1 }}>
            {loading ? '...' : placesCount}
          </div>

          <div style={{ marginTop: '10px', color: '#64748b', fontSize: '14px', lineHeight: 1.5 }}>
            Полный каталог мест и сценариев по городу.
          </div>
        </SurfaceCard>
      </AppLink>

      <AppLink to="/open-now" variant="secondary">
        <SurfaceCard style={{ padding: '20px' }}>
          <div style={topRowStyle}>
            <div style={iconWrapStyle}>
              <Clock3 size={18} />
            </div>
            <ArrowRight size={16} style={arrowStyle} />
          </div>

          <div style={{ marginTop: '16px', color: '#64748b', fontSize: '13px', fontWeight: 600 }}>
            Open now
          </div>

          <div style={{ marginTop: '8px', fontSize: '28px', fontWeight: 800, color: '#0f172a', lineHeight: 1.1 }}>
            Открыто сейчас
          </div>

          <div style={{ marginTop: '10px', color: '#64748b', fontSize: '14px', lineHeight: 1.5 }}>
            Быстрый вход в места, доступные прямо сейчас.
          </div>
        </SurfaceCard>
      </AppLink>

      <AppLink to="/nearby" variant="secondary">
        <SurfaceCard style={{ padding: '20px' }}>
          <div style={topRowStyle}>
            <div style={iconWrapStyle}>
              <Trees size={18} />
            </div>
            <ArrowRight size={16} style={arrowStyle} />
          </div>

          <div style={{ marginTop: '16px', color: '#64748b', fontSize: '13px', fontWeight: 600 }}>
            Nearby
          </div>

          <div style={{ marginTop: '8px', fontSize: '28px', fontWeight: 800, color: '#0f172a', lineHeight: 1.1 }}>
            Рядом
          </div>

          <div style={{ marginTop: '10px', color: '#64748b', fontSize: '14px', lineHeight: 1.5 }}>
            Поиск точек рядом с вами или тестовой локацией.
          </div>
        </SurfaceCard>
      </AppLink>

      <AppLink to="/walk-route" variant="secondary">
        <SurfaceCard style={{ padding: '20px' }}>
          <div style={topRowStyle}>
            <div style={iconWrapStyle}>
              <Route size={18} />
            </div>
            <ArrowRight size={16} style={arrowStyle} />
          </div>

          <div style={{ marginTop: '16px', color: '#64748b', fontSize: '13px', fontWeight: 600 }}>
            Walk Route
          </div>

          <div style={{ marginTop: '8px', fontSize: '28px', fontWeight: 800, color: '#0f172a', lineHeight: 1.1 }}>
            Маршрут прогулки
          </div>

          <div style={{ marginTop: '10px', color: '#64748b', fontSize: '14px', lineHeight: 1.5 }}>
            Пешая прогулка по достопримечательностям и ключевым точкам.
          </div>
        </SurfaceCard>
      </AppLink>
    </section>
  )
}
```

### `frontend/src/widgets/home/PlacesSection.tsx`

```tsx
import { Link } from 'react-router-dom'
import { PlaceCard } from '../../components/places/PlaceCard'
import { SectionHeader } from '../../components/ui/SectionHeader'
import type { Place } from '../../entities/place/model/types'

type PlacesSectionProps = {
  loading: boolean
  error: string | null
  places: Place[]
}

export const PlacesSection = ({ loading, error, places }: PlacesSectionProps) => {
  return (
    <section
      className="places-section"
      style={{
        marginTop: '34px',
      }}
    >
      <SectionHeader
        eyebrow="Discover"
        title="Места"
        description="Подборка точек, которые можно использовать как основу для прогулок, быстрых выходов и сценариев по городу."
        right={
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '14px',
              flexWrap: 'wrap',
            }}
          >
            <div
              style={{
                padding: '10px 14px',
                borderRadius: '999px',
                background: 'rgba(255, 255, 255, 0.82)',
                border: '1px solid rgba(148, 163, 184, 0.18)',
                color: '#475569',
                fontSize: '14px',
                fontWeight: 600,
              }}
            >
              {loading ? 'Загрузка...' : `${places.length} найдено`}
            </div>

            <Link className="section-link" to="/places">
              Смотреть все места
            </Link>
          </div>
        }
      />

      {error && (
        <div
          style={{
            marginTop: '20px',
            background: '#fee2e2',
            color: '#991b1b',
            borderRadius: '18px',
            padding: '16px',
          }}
        >
          {error}
        </div>
      )}

      {!error && (
        <div className="places-grid" style={{ marginTop: '20px' }}>
          {places.slice(0, 6).map((place) => (
            <PlaceCard key={place.id} place={place} />
          ))}
        </div>
      )}
    </section>
  )
}
```

### `frontend/tsconfig.app.json`

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.app.tsbuildinfo",
    "target": "ES2023",
    "useDefineForClassFields": true,
    "lib": ["ES2023", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "types": ["vite/client"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["src"]
}
```

### `frontend/tsconfig.json`

```json
{
  "files": [],
  "references": [
    { "path": "./tsconfig.app.json" },
    { "path": "./tsconfig.node.json" }
  ]
}
```

### `frontend/tsconfig.node.json`

```json
{
  "compilerOptions": {
    "tsBuildInfoFile": "./node_modules/.tmp/tsconfig.node.tsbuildinfo",
    "target": "ES2023",
    "lib": ["ES2023"],
    "module": "ESNext",
    "types": ["node"],
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "verbatimModuleSyntax": true,
    "moduleDetection": "force",
    "noEmit": true,

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "erasableSyntaxOnly": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedSideEffectImports": true
  },
  "include": ["vite.config.ts"]
}
```

### `frontend/vite.config.ts`

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
})
```

### `main.py`

```py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers.ai import router as ai_router
from routers.categories import router as categories_router
from routers.cities import router as cities_router
from routers.collection_places import router as collection_places_router
from routers.collections import router as collections_router
from routers.nearby import router as nearby_router
from routers.open_now import router as open_now_router
from routers.place_search import router as place_search_router
from routers.place_seed_dry_run import router as place_seed_dry_run_router
from routers.place_seed_validation import router as place_seed_validation_router
from routers.place_tags import router as place_tags_router
from routers.place_taxonomy import router as place_taxonomy_router
from routers.place_taxonomy_diagnostics import router as place_taxonomy_diagnostics_router
from routers.places import router as places_router
from routers.route_places import router as route_places_router
from routers.routes import router as routes_router
from routers.tags import router as tags_router

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        settings.backend_base_url,
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ai_router)
app.include_router(categories_router)
app.include_router(cities_router)
app.include_router(collections_router)
app.include_router(collection_places_router)
app.include_router(nearby_router)
app.include_router(open_now_router)
app.include_router(place_search_router)
app.include_router(place_seed_dry_run_router)
app.include_router(place_seed_validation_router)
app.include_router(place_taxonomy_router)
app.include_router(place_taxonomy_diagnostics_router)
app.include_router(places_router)
app.include_router(routes_router)
app.include_router(route_places_router)
app.include_router(tags_router)
app.include_router(place_tags_router)


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "city-guide-api"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

### `migrations/env.py`

```py
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from core.config import settings
from db.base import Base
import models.category  # noqa: F401
import models.city  # noqa: F401
import models.collection  # noqa: F401
import models.collection_place  # noqa: F401
import models.place  # noqa: F401
import models.place_schedule  # noqa: F401
import models.place_tag  # noqa: F401
import models.route  # noqa: F401
import models.route_place  # noqa: F401
import models.tag  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url.replace("%", "%%"))

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### `migrations/versions/1e31cbdc17df_add_category_model.py`

```py
"""add_category_model

Revision ID: 1e31cbdc17df
Revises: 784d6d2f3828
Create Date: 2026-03-23 21:29:01.843263

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e31cbdc17df'
down_revision: Union[str, None] = '784d6d2f3828'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('categories',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_categories_code'), 'categories', ['code'], unique=True)
    op.create_index(op.f('ix_categories_id'), 'categories', ['id'], unique=False)
    op.create_index(op.f('ix_categories_name'), 'categories', ['name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_categories_name'), table_name='categories')
    op.drop_index(op.f('ix_categories_id'), table_name='categories')
    op.drop_index(op.f('ix_categories_code'), table_name='categories')
    op.drop_table('categories')
    # ### end Alembic commands ###
```

### `migrations/versions/281a07116c51_add_route_models.py`

```py
"""add_route_models

Revision ID: 281a07116c51
Revises: 3607cc80012d
Create Date: 2026-03-23 22:39:41.623805

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '281a07116c51'
down_revision: Union[str, None] = '3607cc80012d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('routes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('short_description', sa.Text(), nullable=True),
    sa.Column('duration_minutes', sa.Integer(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_routes_city_id'), 'routes', ['city_id'], unique=False)
    op.create_index(op.f('ix_routes_id'), 'routes', ['id'], unique=False)
    op.create_index(op.f('ix_routes_slug'), 'routes', ['slug'], unique=True)
    op.create_index(op.f('ix_routes_title'), 'routes', ['title'], unique=False)
    op.create_table('route_places',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('route_id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.ForeignKeyConstraint(['route_id'], ['routes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_route_places_id'), 'route_places', ['id'], unique=False)
    op.create_index(op.f('ix_route_places_place_id'), 'route_places', ['place_id'], unique=False)
    op.create_index(op.f('ix_route_places_route_id'), 'route_places', ['route_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_route_places_route_id'), table_name='route_places')
    op.drop_index(op.f('ix_route_places_place_id'), table_name='route_places')
    op.drop_index(op.f('ix_route_places_id'), table_name='route_places')
    op.drop_table('route_places')
    op.drop_index(op.f('ix_routes_title'), table_name='routes')
    op.drop_index(op.f('ix_routes_slug'), table_name='routes')
    op.drop_index(op.f('ix_routes_id'), table_name='routes')
    op.drop_index(op.f('ix_routes_city_id'), table_name='routes')
    op.drop_table('routes')
    # ### end Alembic commands ###
```

### `migrations/versions/3000b4f577bc_add_tag_model.py`

```py
"""add_tag_model

Revision ID: 3000b4f577bc
Revises: 4a31a10f9e37
Create Date: 2026-03-23 22:03:57.905189

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3000b4f577bc'
down_revision: Union[str, None] = '4a31a10f9e37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tags_code'), 'tags', ['code'], unique=True)
    op.create_index(op.f('ix_tags_id'), 'tags', ['id'], unique=False)
    op.create_index(op.f('ix_tags_name'), 'tags', ['name'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_tags_name'), table_name='tags')
    op.drop_index(op.f('ix_tags_id'), table_name='tags')
    op.drop_index(op.f('ix_tags_code'), table_name='tags')
    op.drop_table('tags')
    # ### end Alembic commands ###
```

### `migrations/versions/3607cc80012d_add_collection_models.py`

```py
"""add_collection_models

Revision ID: 3607cc80012d
Revises: ac1e9bce72eb
Create Date: 2026-03-23 22:25:59.999919

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3607cc80012d'
down_revision: Union[str, None] = 'ac1e9bce72eb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('collections',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('city_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=255), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('short_description', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['city_id'], ['cities.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_collections_city_id'), 'collections', ['city_id'], unique=False)
    op.create_index(op.f('ix_collections_id'), 'collections', ['id'], unique=False)
    op.create_index(op.f('ix_collections_slug'), 'collections', ['slug'], unique=True)
    op.create_index(op.f('ix_collections_title'), 'collections', ['title'], unique=False)
    op.create_table('collection_places',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('collection_id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['collection_id'], ['collections.id'], ),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_collection_places_collection_id'), 'collection_places', ['collection_id'], unique=False)
    op.create_index(op.f('ix_collection_places_id'), 'collection_places', ['id'], unique=False)
    op.create_index(op.f('ix_collection_places_place_id'), 'collection_places', ['place_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_collection_places_place_id'), table_name='collection_places')
    op.drop_index(op.f('ix_collection_places_id'), table_name='collection_places')
    op.drop_index(op.f('ix_collection_places_collection_id'), table_name='collection_places')
    op.drop_table('collection_places')
    op.drop_index(op.f('ix_collections_title'), table_name='collections')
    op.drop_index(op.f('ix_collections_slug'), table_name='collections')
    op.drop_index(op.f('ix_collections_id'), table_name='collections')
    op.drop_index(op.f('ix_collections_city_id'), table_name='collections')
    op.drop_table('collections')
    # ### end Alembic commands ###
```

### `migrations/versions/3fb51e7943f5_add_place_schedule_model.py`

```py
"""add_place_schedule_model

Revision ID: 3fb51e7943f5
Revises: 281a07116c51
Create Date: 2026-03-23 23:39:54.196577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3fb51e7943f5'
down_revision: Union[str, None] = '281a07116c51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('place_schedules',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('weekday', sa.String(length=10), nullable=False),
    sa.Column('open_time', sa.Time(), nullable=True),
    sa.Column('close_time', sa.Time(), nullable=True),
    sa.Column('is_closed', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_place_schedules_id'), 'place_schedules', ['id'], unique=False)
    op.create_index(op.f('ix_place_schedules_place_id'), 'place_schedules', ['place_id'], unique=False)
    op.create_index(op.f('ix_place_schedules_weekday'), 'place_schedules', ['weekday'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_place_schedules_weekday'), table_name='place_schedules')
    op.drop_index(op.f('ix_place_schedules_place_id'), table_name='place_schedules')
    op.drop_index(op.f('ix_place_schedules_id'), table_name='place_schedules')
    op.drop_table('place_schedules')
    # ### end Alembic commands ###
```

### `migrations/versions/4a31a10f9e37_add_category_id_to_places.py`

```py
"""add_category_id_to_places"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4a31a10f9e37"
down_revision: Union[str, None] = "1e31cbdc17df"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Добавляем новую колонку category_id в places.
    op.add_column("places", sa.Column("category_id", sa.Integer(), nullable=True))

    # Заполняем category_id на основе старого строкового поля category.
    op.execute(
        """
        UPDATE places
        SET category_id = categories.id
        FROM categories
        WHERE places.category = categories.code
        """
    )

    # Создаем индекс для ускорения фильтрации по category_id.
    op.create_index(op.f("ix_places_category_id"), "places", ["category_id"], unique=False)

    # Добавляем внешний ключ на таблицу categories.
    op.create_foreign_key(
        "fk_places_category_id_categories",
        "places",
        "categories",
        ["category_id"],
        ["id"],
    )


def downgrade() -> None:
    # Удаляем внешний ключ, индекс и колонку category_id при откате миграции.
    op.drop_constraint("fk_places_category_id_categories", "places", type_="foreignkey")
    op.drop_index(op.f("ix_places_category_id"), table_name="places")
    op.drop_column("places", "category_id")
```

### `migrations/versions/784d6d2f3828_add_slug_to_places.py`

```py
"""add_slug_to_places"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "784d6d2f3828"
down_revision: Union[str, None] = "d7f42a463fe3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Сначала добавляем slug как nullable, чтобы миграция прошла на существующих данных.
    op.add_column("places", sa.Column("slug", sa.String(length=255), nullable=True))

    # Заполняем slug для уже существующих записей.
    op.execute("UPDATE places SET slug = 'place-' || id WHERE slug IS NULL")

    # Делаем поле обязательным после заполнения.
    op.alter_column("places", "slug", nullable=False)

    # Добавляем уникальный индекс для быстрых запросов и защиты от дублей.
    op.create_index(op.f("ix_places_slug"), "places", ["slug"], unique=True)


def downgrade() -> None:
    # Удаляем индекс и колонку slug при откате миграции.
    op.drop_index(op.f("ix_places_slug"), table_name="places")
    op.drop_column("places", "slug")
```

### `migrations/versions/9c8e4b1a2f10_add_image_url_to_places.py`

```py
"""add_image_url_to_places

Revision ID: 9c8e4b1a2f10
Revises: 3fb51e7943f5
Create Date: 2026-04-03 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c8e4b1a2f10"
down_revision: Union[str, None] = "3fb51e7943f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("places", sa.Column("image_url", sa.String(length=1000), nullable=True))


def downgrade() -> None:
    op.drop_column("places", "image_url")
```

### `migrations/versions/ac1e9bce72eb_add_place_tag_model.py`

```py
"""add_place_tag_model

Revision ID: ac1e9bce72eb
Revises: 3000b4f577bc
Create Date: 2026-03-23 22:10:20.435266

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac1e9bce72eb'
down_revision: Union[str, None] = '3000b4f577bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('place_tags',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('place_id', sa.Integer(), nullable=False),
    sa.Column('tag_id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['place_id'], ['places.id'], ),
    sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_place_tags_id'), 'place_tags', ['id'], unique=False)
    op.create_index(op.f('ix_place_tags_place_id'), 'place_tags', ['place_id'], unique=False)
    op.create_index(op.f('ix_place_tags_tag_id'), 'place_tags', ['tag_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_place_tags_tag_id'), table_name='place_tags')
    op.drop_index(op.f('ix_place_tags_place_id'), table_name='place_tags')
    op.drop_index(op.f('ix_place_tags_id'), table_name='place_tags')
    op.drop_table('place_tags')
    # ### end Alembic commands ###
```

### `migrations/versions/d7f42a463fe3_add_city_model.py`

```py
"""add_city_model

Revision ID: d7f42a463fe3
Revises: e48f13974bc8
Create Date: 2026-03-23 20:54:32.030829

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7f42a463fe3'
down_revision: Union[str, None] = 'e48f13974bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('cities',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('region', sa.String(length=255), nullable=True),
    sa.Column('country', sa.String(length=100), nullable=False),
    sa.Column('timezone', sa.String(length=100), nullable=False),
    sa.Column('center_lat', sa.Float(), nullable=True),
    sa.Column('center_lng', sa.Float(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cities_id'), 'cities', ['id'], unique=False)
    op.create_index(op.f('ix_cities_name'), 'cities', ['name'], unique=False)
    op.create_index(op.f('ix_cities_slug'), 'cities', ['slug'], unique=True)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_cities_slug'), table_name='cities')
    op.drop_index(op.f('ix_cities_name'), table_name='cities')
    op.drop_index(op.f('ix_cities_id'), table_name='cities')
    op.drop_table('cities')
    # ### end Alembic commands ###
```

### `migrations/versions/e48f13974bc8_init_place_model.py`

```py
"""init_place_model

Revision ID: e48f13974bc8
Revises: 
Create Date: 2026-03-23 20:45:58.142394

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e48f13974bc8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index(op.f('ix_places_city_id'), 'places', ['city_id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_places_city_id'), table_name='places')
    # ### end Alembic commands ###
```

### `models/__init__.py`

```py

```

### `models/category.py`

```py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель категории места.
# Нужна для хранения справочника категорий: cafe, walk, museum и т.д.
class Category(Base):
    __tablename__ = "categories"

    # Уникальный идентификатор категории.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Уникальный код категории для внутреннего использования.
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название категории на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Признак активности категории.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь категории с местами.
    places = relationship("Place", back_populates="category_ref")
```

### `models/city.py`

```py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель города.
# Нужна для масштабирования проекта на несколько городов.
class City(Base):
    __tablename__ = "cities"

    # Уникальный идентификатор города.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Человекочитаемый код города для URL и внутреннего использования.
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название города на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Регион, к которому относится город.
    region: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Страна.
    country: Mapped[str] = mapped_column(String(100), nullable=False, default="Россия")

    # Часовой пояс города.
    timezone: Mapped[str] = mapped_column(String(100), nullable=False, default="Europe/Kaliningrad")

    # Координаты центра города.
    center_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    center_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Признак активности города.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь города с местами.
    places = relationship("Place", back_populates="city")

    # Связь города с подборками.
    collections = relationship("Collection", back_populates="city")

    # Связь города с маршрутами.
    routes = relationship("Route", back_populates="city")
```

### `models/collection.py`

```py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель подборки.
# Нужна для ручных сценариев и тематических наборов мест.
class Collection(Base):
    __tablename__ = "collections"

    # Уникальный идентификатор подборки.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор города, к которому относится подборка.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)

    # Уникальный slug подборки для URL.
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Название подборки.
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Короткое описание подборки.
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Признак активности подборки.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь подборки с городом.
    city = relationship("City", back_populates="collections")

    # Связь подборки с местами через collection_places.
    collection_places = relationship("CollectionPlace", back_populates="collection")
```

### `models/collection_place.py`

```py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Таблица связи подборок и мест.
# Нужна для хранения списка мест внутри подборки.
class CollectionPlace(Base):
    __tablename__ = "collection_places"

    # Уникальный идентификатор связи.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор подборки.
    collection_id: Mapped[int] = mapped_column(ForeignKey("collections.id"), nullable=False, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # Порядок места внутри подборки.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь с подборкой.
    collection = relationship("Collection", back_populates="collection_places")

    # Связь с местом.
    place = relationship("Place", back_populates="collection_places")
```

### `models/place.py`

```py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель места для городского гида.
# Хранит базовую информацию о точке на карте.
class Place(Base):
    __tablename__ = "places"

    # Уникальный идентификатор места.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор города, к которому относится место.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True, default=1)

    # Идентификатор категории места.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True,
        index=True,
    )

    # Человекочитаемый идентификатор для URL.
    slug: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)

    # Название места.
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Короткое описание места.
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ссылка на изображение/обложку места.
    image_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Категория места в строковом виде.
    # Пока оставляем для обратной совместимости.
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Адрес или ориентир места.
    address: Mapped[str] = mapped_column(String(255), nullable=False)

    # Географическая широта.
    lat: Mapped[float] = mapped_column(Float, nullable=False)

    # Географическая долгота.
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Условный ценовой уровень.
    price_level: Mapped[int] = mapped_column(Integer, default=1)

    # Признак, что место подходит для посещения с собакой.
    dog_friendly: Mapped[bool] = mapped_column(Boolean, default=False)

    # Признак, что место подходит для семей с детьми.
    family_friendly: Mapped[bool] = mapped_column(Boolean, default=False)

    # Признак indoor-места.
    indoor: Mapped[bool] = mapped_column(Boolean, default=False)

    # Признак outdoor-места.
    outdoor: Mapped[bool] = mapped_column(Boolean, default=False)

    # Признак активности записи.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь места с городом.
    city = relationship("City", back_populates="places")

    # Связь места с категорией.
    category_ref = relationship("Category", back_populates="places")

    # Связь места с тегами через таблицу place_tags.
    place_tags = relationship("PlaceTag", back_populates="place")

    # Связь места с расписанием.
    schedules = relationship("PlaceSchedule", back_populates="place")

    # Связь места с подборками через collection_places.
    collection_places = relationship("CollectionPlace", back_populates="place")

    # Связь места с маршрутами через route_places.
    route_places = relationship("RoutePlace", back_populates="place")
```

### `models/place_schedule.py`

```py
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель расписания места.
# Нужна для проверки, открыто ли место в конкретный день и время.
class PlaceSchedule(Base):
    __tablename__ = "place_schedules"

    # Уникальный идентификатор записи расписания.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # День недели в формате: mon, tue, wed, thu, fri, sat, sun.
    weekday: Mapped[str] = mapped_column(String(10), nullable=False, index=True)

    # Время открытия.
    open_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Время закрытия.
    close_time: Mapped[time | None] = mapped_column(Time, nullable=True)

    # Признак, что в этот день место закрыто.
    is_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь расписания с местом.
    place = relationship("Place", back_populates="schedules")
```

### `models/place_tag.py`

```py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Таблица связи мест и тегов.
# Нужна для many-to-many связи между places и tags.
class PlaceTag(Base):
    __tablename__ = "place_tags"

    # Уникальный идентификатор связи.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # Идентификатор тега.
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), nullable=False, index=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь с местом.
    place = relationship("Place", back_populates="place_tags")

    # Связь с тегом.
    tag = relationship("Tag", back_populates="place_tags")
```

### `models/route.py`

```py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель маршрута.
# Нужна для хранения готовых сценариев прогулок и последовательностей мест.
class Route(Base):
    __tablename__ = "routes"

    # Уникальный идентификатор маршрута.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор города, к которому относится маршрут.
    city_id: Mapped[int] = mapped_column(ForeignKey("cities.id"), nullable=False, index=True)

    # Уникальный slug маршрута для URL.
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # Название маршрута.
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Короткое описание маршрута.
    short_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Примерная длительность маршрута в минутах.
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Признак активности маршрута.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь маршрута с городом.
    city = relationship("City", back_populates="routes")

    # Связь маршрута с точками через route_places.
    route_places = relationship("RoutePlace", back_populates="route")
```

### `models/route_place.py`

```py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Таблица связи маршрутов и мест.
# Нужна для хранения списка точек внутри маршрута.
class RoutePlace(Base):
    __tablename__ = "route_places"

    # Уникальный идентификатор связи.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Идентификатор маршрута.
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False, index=True)

    # Идентификатор места.
    place_id: Mapped[int] = mapped_column(ForeignKey("places.id"), nullable=False, index=True)

    # Порядок точки внутри маршрута.
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Связь с маршрутом.
    route = relationship("Route", back_populates="route_places")

    # Связь с местом.
    place = relationship("Place", back_populates="route_places")
```

### `models/tag.py`

```py
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


# Модель тега.
# Нужна для сценарной и тематической фильтрации мест.
class Tag(Base):
    __tablename__ = "tags"

    # Уникальный идентификатор тега.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    # Уникальный код тега для внутреннего использования.
    code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    # Название тега на русском языке.
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Признак активности тега.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Дата и время создания записи.
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Дата и время последнего обновления записи.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    # Связь тега со связями place_tags.
    place_tags = relationship("PlaceTag", back_populates="tag")
```

### `routers/__init__.py`

```py

```

### `routers/ai.py`

```py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.ai import AIQueryRequest
from services.ai_service import process_ai_query

router = APIRouter(prefix="/ai", tags=["ai"])


# Тестовый endpoint для будущего AI-слоя.
@router.get("/health")
def ai_health() -> dict[str, str]:
    return {"status": "ai router ready"}


# Endpoint для приема AI-запроса.
@router.post("/query")
def ai_query(
    payload: AIQueryRequest,
    db: Session = Depends(get_db),
) -> dict:
    return process_ai_query(
        query=payload.query,
        db=db,
        lat=payload.lat,
        lng=payload.lng,
    )
```

### `routers/categories.py`

```py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.category import CategoryRead
from services.category_service import (
    get_categories,
    get_category_by_code,
    get_category_by_id,
)

router = APIRouter(prefix="/categories", tags=["categories"])


# Возвращает список всех категорий из базы.
@router.get("/", response_model=list[CategoryRead])
def read_categories(db: Session = Depends(get_db)) -> list[CategoryRead]:
    return get_categories(db)


# Возвращает одну категорию по идентификатору.
@router.get("/{category_id}", response_model=CategoryRead)
def read_category(category_id: int, db: Session = Depends(get_db)) -> CategoryRead:
    category = get_category_by_id(db, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


# Возвращает одну категорию по коду.
@router.get("/by-code/{code}", response_model=CategoryRead)
def read_category_by_code(code: str, db: Session = Depends(get_db)) -> CategoryRead:
    category = get_category_by_code(db, code)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
```

### `routers/cities.py`

```py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.city import CityRead
from services.city_service import get_cities, get_city_by_id, get_city_by_slug

router = APIRouter(prefix="/cities", tags=["cities"])


# Возвращает список всех городов из базы.
@router.get("/", response_model=list[CityRead])
def read_cities(db: Session = Depends(get_db)) -> list[CityRead]:
    return get_cities(db)


# Возвращает один город по его идентификатору.
@router.get("/{city_id}", response_model=CityRead)
def read_city(city_id: int, db: Session = Depends(get_db)) -> CityRead:
    city = get_city_by_id(db, city_id)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city


# Возвращает один город по его slug.
@router.get("/by-slug/{slug}", response_model=CityRead)
def read_city_by_slug(slug: str, db: Session = Depends(get_db)) -> CityRead:
    city = get_city_by_slug(db, slug)
    if city is None:
        raise HTTPException(status_code=404, detail="City not found")
    return city
```

### `routers/collection_places.py`

```py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.collection_place import CollectionPlaceRead
from services.collection_place_service import (
    get_collection_places,
    get_collection_places_by_collection_id,
)

router = APIRouter(prefix="/collection-places", tags=["collection-places"])


# Возвращает список всех связей подборок и мест.
# Если передан collection_id, возвращает связи только для выбранной подборки.
@router.get("/", response_model=list[CollectionPlaceRead])
def read_collection_places(
    collection_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CollectionPlaceRead]:
    if collection_id is not None:
        return get_collection_places_by_collection_id(db, collection_id)
    return get_collection_places(db)
```

### `routers/collections.py`

```py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.collection import CollectionRead
from services.collection_service import (
    get_collection_by_id,
    get_collection_by_slug,
    get_collections,
    get_collections_by_city_id,
)

router = APIRouter(prefix="/collections", tags=["collections"])


# Возвращает список всех подборок.
# Если передан city_id, возвращает подборки только выбранного города.
@router.get("/", response_model=list[CollectionRead])
def read_collections(
    city_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[CollectionRead]:
    if city_id is not None:
        return get_collections_by_city_id(db, city_id)
    return get_collections(db)


# Возвращает одну подборку по идентификатору.
@router.get("/{collection_id}", response_model=CollectionRead)
def read_collection(collection_id: int, db: Session = Depends(get_db)) -> CollectionRead:
    collection = get_collection_by_id(db, collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


# Возвращает одну подборку по slug.
@router.get("/by-slug/{slug}", response_model=CollectionRead)
def read_collection_by_slug(slug: str, db: Session = Depends(get_db)) -> CollectionRead:
    collection = get_collection_by_slug(db, slug)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection
```

### `routers/nearby.py`

```py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.nearby import NearbyPlaceRead
from services.nearby_service import get_nearby_places

router = APIRouter(prefix="/nearby", tags=["nearby"])


# Возвращает список мест рядом с переданной точкой.
@router.get("/", response_model=list[NearbyPlaceRead])
def read_nearby_places(
    lat: float = Query(...),
    lng: float = Query(...),
    radius_km: float = Query(default=3.0),
    db: Session = Depends(get_db),
) -> list[NearbyPlaceRead]:
    return get_nearby_places(
        db=db,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )
```

### `routers/open_now.py`

```py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.open_now import OpenNowPlaceRead
from services.open_now_service import get_open_now_places

router = APIRouter(prefix="/open-now", tags=["open-now"])


# Возвращает список мест, которые открыты сейчас в выбранном городе.
@router.get("/", response_model=list[OpenNowPlaceRead])
def read_open_now_places(
    city_slug: str = Query(...),
    db: Session = Depends(get_db),
) -> list[OpenNowPlaceRead]:
    return get_open_now_places(
        db=db,
        city_slug=city_slug,
    )
```

### `routers/place_search.py`

```py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_search_response import PlaceSearchResponse
from services.place_search_response_service import build_place_search_response
from services.place_service import get_places, get_places_total

router = APIRouter(prefix="/places/search", tags=["place-search"])


# Возвращает список мест по текстовому запросу и дополнительным фильтрам.
@router.get("/", response_model=PlaceSearchResponse)
def search_places(
    q: str = Query(...),
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    tag_id: int | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="title"),
    sort_order: str = Query(default="asc"),
    db: Session = Depends(get_db),
) -> PlaceSearchResponse:
    items = get_places(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
        category_id=category_id,
        tag_id=tag_id,
        q=q,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total = get_places_total(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
        category_id=category_id,
        tag_id=tag_id,
        q=q,
    )

    return build_place_search_response(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
```

### `routers/place_seed_dry_run.py`

```py
from fastapi import APIRouter

from schemas.place_seed_dry_run_request import PlaceSeedDryRunRequest
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from services.place_seed_dry_run_service import run_place_seed_dry_run

router = APIRouter(
    prefix="/place-seed/dry-run",
    tags=["place-seed-dry-run"],
)


@router.post("/", response_model=PlaceSeedImportSummary)
def dry_run_place_seed_payload(
    payload: PlaceSeedDryRunRequest,
) -> PlaceSeedImportSummary:
    """
    Выполняет dry-run seed-элементов мест без записи в БД.

    Нужен для:
    - проверки seed-файлов перед импортом
    - ручной валидации больших пакетов данных
    - AI enrichment pipeline
    """
    return run_place_seed_dry_run(payload.items)
```

### `routers/place_seed_validation.py`

```py
from fastapi import APIRouter

from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_seed_validation_request import PlaceSeedValidationRequest
from services.place_seed_bulk_validation_service import validate_place_seed_items

router = APIRouter(
    prefix="/place-seed/validate",
    tags=["place-seed-validation"],
)


@router.post("/", response_model=PlaceSeedBulkValidationResponse)
def validate_place_seed_payload(
    payload: PlaceSeedValidationRequest,
) -> PlaceSeedBulkValidationResponse:
    """
    Валидирует список seed-элементов мест и возвращает общий результат.

    Нужен для:
    - bulk seed import
    - ручной проверки seed-файлов
    - AI enrichment pipeline
    - pre-ingest validation
    """
    return validate_place_seed_items(payload.items)
```

### `routers/place_tags.py`

```py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place_tag import PlaceTagRead
from services.place_tag_service import get_place_tags, get_place_tags_by_place_id

router = APIRouter(prefix="/place-tags", tags=["place-tags"])


# Возвращает список всех связей мест и тегов.
# Если передан place_id, возвращает связи только для выбранного места.
@router.get("/", response_model=list[PlaceTagRead])
def read_place_tags(
    place_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[PlaceTagRead]:
    if place_id is not None:
        return get_place_tags_by_place_id(db, place_id)
    return get_place_tags(db)
```

### `routers/place_taxonomy.py`

```py
from fastapi import APIRouter

from schemas.place_taxonomy_response import PlaceTaxonomyResponse
from services.place_taxonomy_response_service import build_place_taxonomy_response

router = APIRouter(prefix="/place-taxonomy", tags=["place-taxonomy"])


@router.get("/", response_model=PlaceTaxonomyResponse)
def read_place_taxonomy() -> PlaceTaxonomyResponse:
    """
    Возвращает каноничную таксономию City GO.

    Нужна для:
    - seed-данных
    - frontend filters
    - Telegram bot
    - AI / recommendation layer
    """
    return build_place_taxonomy_response()
```

### `routers/place_taxonomy_diagnostics.py`

```py
from fastapi import APIRouter

from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_diagnostics_service import (
    get_invalid_place_taxonomy_values,
)

router = APIRouter(
    prefix="/place-taxonomy/diagnostics",
    tags=["place-taxonomy-diagnostics"],
)


@router.post("/", response_model=PlaceTaxonomyDiagnosticsResponse)
def validate_place_taxonomy_payload(
    payload: PlaceTaxonomyPayload,
) -> PlaceTaxonomyDiagnosticsResponse:
    """
    Проверяет taxonomy payload и возвращает только невалидные значения.

    Нужен для:
    - seed-данных
    - импорта
    - AI enrichment pipeline
    - ручной проверки payload перед записью
    """
    return get_invalid_place_taxonomy_values(payload)
```

### `routers/places.py`

```py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.place import PlaceCreate, PlaceRead, PlaceUpdate
from schemas.place_search_response import PlaceSearchResponse
from services.place_search_response_service import build_place_search_response
from services.place_service import (
    create_place,
    delete_place,
    get_place_by_id,
    get_place_by_slug,
    get_places,
    get_places_total,
    update_place,
)

router = APIRouter(prefix="/places", tags=["places"])


# Возвращает список мест из базы с учетом фильтров.
@router.get("/", response_model=PlaceSearchResponse)
def read_places(
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    category_id: int | None = Query(default=None),
    tag_id: int | None = Query(default=None),
    q: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    sort_by: str = Query(default="title"),
    sort_order: str = Query(default="asc"),
    db: Session = Depends(get_db),
) -> PlaceSearchResponse:
    items = get_places(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
        category_id=category_id,
        tag_id=tag_id,
        q=q,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    total = get_places_total(
        db=db,
        city_id=city_id,
        city_slug=city_slug,
        category_id=category_id,
        tag_id=tag_id,
        q=q,
    )

    return build_place_search_response(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


# Возвращает одно место по его идентификатору.
@router.get("/{place_id}", response_model=PlaceRead)
def read_place(place_id: int, db: Session = Depends(get_db)) -> PlaceRead:
    place = get_place_by_id(db, place_id)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


# Возвращает одно место по его slug.
@router.get("/by-slug/{slug}", response_model=PlaceRead)
def read_place_by_slug(slug: str, db: Session = Depends(get_db)) -> PlaceRead:
    place = get_place_by_slug(db, slug)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


# Создает новое место в базе.
@router.post("/", response_model=PlaceRead)
def create_new_place(
    place_in: PlaceCreate,
    db: Session = Depends(get_db),
) -> PlaceRead:
    return create_place(db, place_in)


# Обновляет существующее место по идентификатору.
@router.put("/{place_id}", response_model=PlaceRead)
def update_existing_place(
    place_id: int,
    place_in: PlaceUpdate,
    db: Session = Depends(get_db),
) -> PlaceRead:
    place = update_place(db, place_id, place_in)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return place


# Удаляет место по идентификатору.
@router.delete("/{place_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_place(place_id: int, db: Session = Depends(get_db)) -> None:
    deleted = delete_place(db, place_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Place not found")
```

### `routers/route_places.py`

```py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route_place import RoutePlaceRead
from services.route_place_service import get_route_places, get_route_places_by_route_id

router = APIRouter(prefix="/route-places", tags=["route-places"])


# Возвращает список всех связей маршрутов и мест.
# Если передан route_id, возвращает связи только для выбранного маршрута.
@router.get("/", response_model=list[RoutePlaceRead])
def read_route_places(
    route_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RoutePlaceRead]:
    if route_id is not None:
        return get_route_places_by_route_id(db, route_id)
    return get_route_places(db)
```

### `routers/routes.py`

```py
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.route import RouteDetailRead, RouteRead
from services.route_service import (
    build_route_points,
    get_route_by_id,
    get_route_by_slug,
    get_routes,
    get_routes_by_city_id,
    get_routes_by_city_slug,
)

router = APIRouter(prefix="/routes", tags=["routes"])


@router.get("/", response_model=list[RouteRead])
def read_routes(
    city_id: int | None = Query(default=None),
    city_slug: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[RouteRead]:
    if city_slug is not None:
        return get_routes_by_city_slug(db, city_slug)

    if city_id is not None:
        return get_routes_by_city_id(db, city_id)

    return get_routes(db)


@router.get("/{route_id}", response_model=RouteDetailRead)
def read_route(route_id: int, db: Session = Depends(get_db)) -> RouteDetailRead:
    route = get_route_by_id(db, route_id)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    return RouteDetailRead(
        id=route.id,
        city_id=route.city_id,
        slug=route.slug,
        title=route.title,
        short_description=route.short_description,
        duration_minutes=route.duration_minutes,
        is_active=route.is_active,
        created_at=route.created_at,
        updated_at=route.updated_at,
        points=build_route_points(route),
    )


@router.get("/by-slug/{slug}", response_model=RouteDetailRead)
def read_route_by_slug(slug: str, db: Session = Depends(get_db)) -> RouteDetailRead:
    route = get_route_by_slug(db, slug)
    if route is None:
        raise HTTPException(status_code=404, detail="Route not found")

    return RouteDetailRead(
        id=route.id,
        city_id=route.city_id,
        slug=route.slug,
        title=route.title,
        short_description=route.short_description,
        duration_minutes=route.duration_minutes,
        is_active=route.is_active,
        created_at=route.created_at,
        updated_at=route.updated_at,
        points=build_route_points(route),
    )
```

### `routers/tags.py`

```py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.dependencies import get_db
from schemas.tag import TagRead
from services.tag_service import get_tag_by_code, get_tag_by_id, get_tags

router = APIRouter(prefix="/tags", tags=["tags"])


# Возвращает список всех тегов из базы.
@router.get("/", response_model=list[TagRead])
def read_tags(db: Session = Depends(get_db)) -> list[TagRead]:
    return get_tags(db)


# Возвращает один тег по идентификатору.
@router.get("/{tag_id}", response_model=TagRead)
def read_tag(tag_id: int, db: Session = Depends(get_db)) -> TagRead:
    tag = get_tag_by_id(db, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


# Возвращает один тег по коду.
@router.get("/by-code/{code}", response_model=TagRead)
def read_tag_by_code(code: str, db: Session = Depends(get_db)) -> TagRead:
    tag = get_tag_by_code(db, code)
    if tag is None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag
```

### `schemas/__init__.py`

```py

```

### `schemas/ai.py`

```py
from pydantic import BaseModel


# Схема входящего AI-запроса.
# Содержит текстовый запрос пользователя и опциональные координаты.
class AIQueryRequest(BaseModel):
    query: str
    lat: float | None = None
    lng: float | None = None
```

### `schemas/category.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема категории.
# Используется для чтения данных о категории.
class CategoryBase(BaseModel):
    code: str
    name: str
    is_active: bool = True


# Схема для чтения категории из базы данных.
class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/city.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема города.
# Содержит общие поля для чтения данных о городе.
class CityBase(BaseModel):
    slug: str
    name: str
    region: str | None = None
    country: str = "Россия"
    timezone: str = "Europe/Kaliningrad"
    center_lat: float | None = None
    center_lng: float | None = None
    is_active: bool = True


# Схема для чтения города из базы данных.
class CityRead(CityBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/collection.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема подборки.
# Используется для чтения данных о подборке.
class CollectionBase(BaseModel):
    city_id: int
    slug: str
    title: str
    short_description: str | None = None
    is_active: bool = True


# Схема для чтения подборки из базы данных.
class CollectionRead(CollectionBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/collection_place.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема связи подборки и места.
class CollectionPlaceBase(BaseModel):
    collection_id: int
    place_id: int
    position: int = 1


# Схема для чтения связи подборки и места из базы данных.
class CollectionPlaceRead(CollectionPlaceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/nearby.py`

```py
from pydantic import BaseModel


# Схема ответа для nearby-поиска.
class NearbyPlaceRead(BaseModel):
    id: int
    slug: str
    title: str
    city_id: int
    category_id: int | None = None
    category: str
    address: str
    lat: float
    lng: float
    distance_km: float
```

### `schemas/open_now.py`

```py
from pydantic import BaseModel


# Схема ответа для списка мест, которые открыты сейчас.
class OpenNowPlaceRead(BaseModel):
    id: int
    slug: str
    title: str
    city_id: int
    category_id: int | None = None
    category: str
    address: str
    open_time: str
    close_time: str
```

### `schemas/pagination.py`

```py
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """
    Параметры пагинации для list/search endpoint'ов.
    """

    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

### `schemas/place.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема места.
# Содержит общие поля, которые используются при создании и чтении.
class PlaceBase(BaseModel):
    city_id: int = 1
    category_id: int | None = None
    slug: str
    title: str
    short_description: str | None = None
    image_url: str | None = None
    category: str
    address: str
    lat: float
    lng: float
    price_level: int = 1
    dog_friendly: bool = False
    family_friendly: bool = False
    indoor: bool = False
    outdoor: bool = False
    is_active: bool = True


# Схема для создания нового места.
class PlaceCreate(PlaceBase):
    pass


# Схема для обновления существующего места.
class PlaceUpdate(PlaceBase):
    pass


# Схема для чтения места из базы данных.
class PlaceRead(PlaceBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/place_list_params.py`

```py
from pydantic import BaseModel

from schemas.pagination import PaginationParams


class PlaceListParams(PaginationParams):
    """
    Параметры list/search для мест.

    Объединяет:
    - фильтры places
    - текстовый поиск
    - пагинацию
    """

    city_id: int | None = None
    city_slug: str | None = None
    category_id: int | None = None
    tag_id: int | None = None
    q: str | None = None
```

### `schemas/place_query_params.py`

```py
from schemas.place_list_params import PlaceListParams
from schemas.sorting import SortingParams


class PlaceQueryParams(PlaceListParams, SortingParams):
    """
    Единые параметры запроса для places/search сценариев.

    Объединяет:
    - фильтры
    - текстовый поиск
    - пагинацию
    - сортировку
    """

    pass
```

### `schemas/place_search.py`

```py
from pydantic import BaseModel


class PlaceSearchParams(BaseModel):
    """
    Параметры поиска мест.

    Это подготовка под более чистую search-логику:
    позже можно будет использовать и в API, и в сервисах, и в AI-layer.
    """

    city_id: int | None = None
    city_slug: str | None = None
    category_id: int | None = None
    tag_id: int | None = None
    q: str | None = None
```

### `schemas/place_search_response.py`

```py
from pydantic import BaseModel

from schemas.place import PlaceRead


class PlaceSearchResponse(BaseModel):
    """
    Стандартный ответ для list/search сценариев по местам.

    Пока это подготовка под следующий шаг:
    позже можно будет перевести /places/ и /places/search/
    с list[PlaceRead] на более стабильный контракт с метаданными.
    """

    items: list[PlaceRead]
    total: int
    limit: int
    offset: int
```

### `schemas/place_seed_bulk_validation_response.py`

```py
from pydantic import BaseModel, Field

from schemas.place_seed_validation_response import PlaceSeedValidationResponse


class PlaceSeedBulkValidationResponse(BaseModel):
    """
    Результат bulk-валидации seed-элементов мест.
    """

    total: int
    valid_count: int
    invalid_count: int
    items: list[PlaceSeedValidationResponse] = Field(default_factory=list)
```

### `schemas/place_seed_dry_run_request.py`

```py
from pydantic import BaseModel, Field

from schemas.place_seed_item import PlaceSeedItem


class PlaceSeedDryRunRequest(BaseModel):
    """
    Стандартный request payload для dry-run seed-проверки мест.

    Это заготовка под более стабильный контракт:
    позже сюда можно добавить metadata, source_batch_id и dry-run options.
    """

    items: list[PlaceSeedItem] = Field(default_factory=list)
```

### `schemas/place_seed_import_summary.py`

```py
from pydantic import BaseModel, Field


class PlaceSeedImportSummary(BaseModel):
    """
    Краткая сводка по seed-импорту мест.

    Пока это заготовка под следующий шаг:
    - dry-run import
    - import pipeline
    - admin/import diagnostics
    """

    total: int = 0
    created: int = 0
    updated: int = 0
    skipped: int = 0
    invalid: int = 0
    errors: list[str] = Field(default_factory=list)
```

### `schemas/place_seed_item.py`

```py
from pydantic import BaseModel, Field

from schemas.place_taxonomy_payload import PlaceTaxonomyPayload


class PlaceSeedItem(BaseModel):
    """
    Каноничный seed-элемент места.

    Это подготовка под:
    - seed import
    - bulk validation
    - AI enrichment pipeline
    """

    title: str
    slug: str
    city_slug: str
    category: str
    address: str | None = None
    short_description: str | None = None
    taxonomy: PlaceTaxonomyPayload
    source: str | None = None
    source_url: str | None = None
    lat: float | None = None
    lng: float | None = None
    is_active: bool = True
```

### `schemas/place_seed_validation_request.py`

```py
from pydantic import BaseModel, Field

from schemas.place_seed_item import PlaceSeedItem


class PlaceSeedValidationRequest(BaseModel):
    """
    Стандартный request payload для bulk-валидации seed-элементов мест.

    Это заготовка под более стабильный контракт:
    позже сюда можно добавить metadata, source_batch_id и validation options.
    """

    items: list[PlaceSeedItem] = Field(default_factory=list)
```

### `schemas/place_seed_validation_response.py`

```py
from pydantic import BaseModel, Field

from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


class PlaceSeedValidationResponse(BaseModel):
    """
    Результат валидации одного seed-элемента места.
    """

    is_valid: bool
    title: str
    slug: str
    city_slug: str
    taxonomy_diagnostics: PlaceTaxonomyDiagnosticsResponse
    errors: list[str] = Field(default_factory=list)
```

### `schemas/place_tag.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема связи места и тега.
class PlaceTagBase(BaseModel):
    place_id: int
    tag_id: int


# Схема для чтения связи места и тега из базы данных.
class PlaceTagRead(PlaceTagBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/place_taxonomy_diagnostics_response.py`

```py
from pydantic import BaseModel


class PlaceTaxonomyDiagnosticsResponse(BaseModel):
    """
    Стандартный ответ диагностики taxonomy payload.

    Возвращает только невалидные значения по каждому слою таксономии.
    """

    category: str | None = None
    tags: list[str] = []
    scenario_tags: list[str] = []
    vibe_tags: list[str] = []
    restriction_tags: list[str] = []
```

### `schemas/place_taxonomy_payload.py`

```py
from pydantic import BaseModel, Field


class PlaceTaxonomyPayload(BaseModel):
    """
    Каноничный payload для таксономии места.

    Используем как заготовку для:
    - seed-данных
    - импорта
    - AI enrichment
    - будущей backend-валидации
    """

    category: str
    tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    restriction_tags: list[str] = Field(default_factory=list)
```

### `schemas/place_taxonomy_response.py`

```py
from pydantic import BaseModel, Field


class PlaceTaxonomyResponse(BaseModel):
    """
    Стандартный ответ для каноничной таксономии City GO.
    """

    categories: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    scenario_tags: list[str] = Field(default_factory=list)
    vibe_tags: list[str] = Field(default_factory=list)
    restriction_tags: list[str] = Field(default_factory=list)
    user_signals: list[str] = Field(default_factory=list)
```

### `schemas/route.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoutePointRead(BaseModel):
    place_id: int
    position: int
    place_slug: str | None = None
    place_title: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RouteBase(BaseModel):
    city_id: int
    slug: str
    title: str
    short_description: str | None = None
    duration_minutes: int | None = None
    is_active: bool = True


class RouteRead(RouteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RouteDetailRead(RouteRead):
    points: list[RoutePointRead] = []
```

### `schemas/route_place.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема связи маршрута и места.
class RoutePlaceBase(BaseModel):
    route_id: int
    place_id: int
    position: int = 1


# Схема для чтения связи маршрута и места из базы данных.
class RoutePlaceRead(RoutePlaceBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `schemas/sorting.py`

```py
from typing import Literal

from pydantic import BaseModel


class SortingParams(BaseModel):
    """
    Параметры сортировки для list/search endpoint'ов.
    """

    sort_by: Literal["title", "created_at"] = "title"
    sort_order: Literal["asc", "desc"] = "asc"
```

### `schemas/tag.py`

```py
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# Базовая схема тега.
# Используется для чтения данных о теге.
class TagBase(BaseModel):
    code: str
    name: str
    is_active: bool = True


# Схема для чтения тега из базы данных.
class TagRead(TagBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### `scripts/seed_minimal_data.py`

```py
from datetime import datetime, time

from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag


SEED_DATA = {
    "cities": [
        {
            "slug": "zelenogradsk",
            "name": "Зеленоградск",
            "region": "Калининградская область",
            "country": "Россия",
            "timezone": "Europe/Kaliningrad",
            "center_lat": 54.9587,
            "center_lng": 20.4750,
        },
        {
            "slug": "kaliningrad",
            "name": "Калининград",
            "region": "Калининградская область",
            "country": "Россия",
            "timezone": "Europe/Kaliningrad",
            "center_lat": 54.7104,
            "center_lng": 20.4522,
        },
    ],
    "categories": [
        {"code": "cafe", "name": "Кафе"},
        {"code": "walk", "name": "Прогулка"},
    ],
    "places": [
        {
            "city_slug": "zelenogradsk",
            "category_code": "cafe",
            "slug": "balt-zelenogradsk",
            "title": "Balt",
            "short_description": "Гастро-точка в центре Зеленоградска.",
            "image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=80",
            "category": "cafe",
            "address": "Зеленоградск, центр города",
            "lat": 54.9594,
            "lng": 20.4761,
            "price_level": 3,
            "dog_friendly": False,
            "family_friendly": True,
            "indoor": True,
            "outdoor": False,
        },
        {
            "city_slug": "zelenogradsk",
            "category_code": "walk",
            "slug": "promenade-zelenogradsk",
            "title": "Променад",
            "short_description": "Пешеходная прогулка вдоль моря.",
            "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
            "category": "walk",
            "address": "Зеленоградск, променад",
            "lat": 54.9585,
            "lng": 20.4748,
            "price_level": 1,
            "dog_friendly": True,
            "family_friendly": True,
            "indoor": False,
            "outdoor": True,
        },
        {
            "city_slug": "kaliningrad",
            "category_code": "walk",
            "slug": "kant-island-kaliningrad",
            "title": "Остров Канта",
            "short_description": "Прогулочная и туристическая точка в центре Калининграда.",
            "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
            "category": "walk",
            "address": "Калининград, остров Канта",
            "lat": 54.7066,
            "lng": 20.5124,
            "price_level": 1,
            "dog_friendly": True,
            "family_friendly": True,
            "indoor": False,
            "outdoor": True,
        },
    ],
    "routes": [
        {
            "city_slug": "zelenogradsk",
            "slug": "seaside-walk-zelenogradsk",
            "title": "Пешая прогулка по Зеленоградску",
            "short_description": "Короткий прогулочный маршрут по центру и променаду.",
            "duration_minutes": 60,
            "points": [
                {"place_slug": "balt-zelenogradsk", "position": 1},
                {"place_slug": "promenade-zelenogradsk", "position": 2},
            ],
        },
        {
            "city_slug": "kaliningrad",
            "slug": "kant-walk-kaliningrad",
            "title": "Прогулка к острову Канта",
            "short_description": "Базовый туристический маршрут по центральной точке Калининграда.",
            "duration_minutes": 45,
            "points": [
                {"place_slug": "kant-island-kaliningrad", "position": 1},
            ],
        },
    ],
}


def get_or_create_city(db, item: dict) -> City:
    city = db.query(City).filter(City.slug == item["slug"]).first()
    if city:
        return city

    city = City(
        slug=item["slug"],
        name=item["name"],
        region=item.get("region"),
        country=item.get("country", "Россия"),
        timezone=item.get("timezone", "Europe/Kaliningrad"),
        center_lat=item.get("center_lat"),
        center_lng=item.get("center_lng"),
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(city)
    db.flush()
    return city


def get_or_create_category(db, item: dict) -> Category:
    category = db.query(Category).filter(Category.code == item["code"]).first()
    if category:
        return category

    category = Category(
        code=item["code"],
        name=item["name"],
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(category)
    db.flush()
    return category


def get_or_create_place(db, item: dict, city_id: int, category_id: int) -> Place:
    place = db.query(Place).filter(Place.slug == item["slug"]).first()
    if place:
        return place

    place = Place(
        city_id=city_id,
        category_id=category_id,
        slug=item["slug"],
        title=item["title"],
        short_description=item["short_description"],
        image_url=item.get("image_url"),
        category=item["category"],
        address=item["address"],
        lat=item["lat"],
        lng=item["lng"],
        price_level=item["price_level"],
        dog_friendly=item["dog_friendly"],
        family_friendly=item["family_friendly"],
        indoor=item["indoor"],
        outdoor=item["outdoor"],
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(place)
    db.flush()
    return place


def ensure_schedule(db, place_id: int) -> None:
    existing = db.query(PlaceSchedule).filter(PlaceSchedule.place_id == place_id).first()
    if existing:
        return

    for weekday in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        db.add(
            PlaceSchedule(
                place_id=place_id,
                weekday=weekday,
                open_time=time(9, 0),
                close_time=time(23, 0),
                is_closed=False,
                created_at=datetime.utcnow(),
            )
        )


def get_or_create_route(db, item: dict, city_id: int) -> Route:
    route = db.query(Route).filter(Route.slug == item["slug"]).first()
    if route:
        return route

    route = Route(
        city_id=city_id,
        slug=item["slug"],
        title=item["title"],
        short_description=item.get("short_description"),
        duration_minutes=item.get("duration_minutes"),
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(route)
    db.flush()
    return route


def ensure_route_points(db, route: Route, item: dict, place_map: dict[str, Place]) -> None:
    existing = db.query(RoutePlace).filter(RoutePlace.route_id == route.id).first()
    if existing:
        return

    for point in item["points"]:
        place = place_map[point["place_slug"]]
        db.add(
            RoutePlace(
                route_id=route.id,
                place_id=place.id,
                position=point["position"],
                created_at=datetime.utcnow(),
            )
        )


def main() -> None:
    db = SessionLocal()

    try:
        city_map: dict[str, City] = {}
        category_map: dict[str, Category] = {}
        place_map: dict[str, Place] = {}

        for city_item in SEED_DATA["cities"]:
            city = get_or_create_city(db, city_item)
            city_map[city.slug] = city

        for category_item in SEED_DATA["categories"]:
            category = get_or_create_category(db, category_item)
            category_map[category.code] = category

        for place_item in SEED_DATA["places"]:
            city = city_map[place_item["city_slug"]]
            category = category_map[place_item["category_code"]]

            place = get_or_create_place(
                db=db,
                item=place_item,
                city_id=city.id,
                category_id=category.id,
            )
            ensure_schedule(db, place.id)
            place_map[place.slug] = place

        for route_item in SEED_DATA["routes"]:
            city = city_map[route_item["city_slug"]]
            route = get_or_create_route(db, route_item, city.id)
            ensure_route_points(db, route, route_item, place_map)

        db.commit()
        print("Minimal multi-city seed with routes completed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
```

### `services/__init__.py`

```py
def place_seed_bulk_validation_service():
    return None
```

### `services/ai_dictionaries.py`

```py
# Словарь городов для простого извлечения city_slug из текста запроса.
CITY_KEYWORDS = {
    "zelenogradsk": [
        "зеленоградск",
    ],
}


# Словарь категорий для простого извлечения category_id из текста запроса.
CATEGORY_KEYWORDS = {
    1: [
        "прогулк",
        "погулять",
        "пройтись",
    ],
    2: [
        "кафе",
        "кофе",
        "поесть",
        "поесть где",
    ],
    3: [
        "музе",
        "музей",
    ],
}


# Словарь тегов для простого извлечения tag_id из текста запроса.
TAG_KEYWORDS = {
    1: [
        "с собак",
        "dog-friendly",
        "dog friendly",
    ],
    2: [
        "тихо",
        "тихие",
        "тихий",
        "спокойно",
        "спокойные",
    ],
    3: [
        "романт",
        "свидан",
    ],
}


# Словарь интентов для базового разбора пользовательского запроса.
INTENT_KEYWORDS = {
    "collections": [
        "подборк",
        "впервые",
        "что посмотреть",
        "куда сходить",
    ],
    "routes": [
        "маршрут",
        "прогулк",
        "путь",
    ],
    "open_now": [
        "открыто",
        "сейчас",
    ],
    "nearby": [
        "рядом",
        "поблизости",
        "недалеко",
    ],
}
```

### `services/ai_service.py`

```py
from sqlalchemy.orm import Session

from services.ai_dictionaries import (
    CATEGORY_KEYWORDS,
    CITY_KEYWORDS,
    INTENT_KEYWORDS,
    TAG_KEYWORDS,
)
from services.collection_service import get_collections_by_city_id
from services.nearby_service import get_nearby_places
from services.open_now_service import get_open_now_places
from services.place_detail_service import get_place_detail_by_slug
from services.place_service import get_places
from services.route_service import get_routes_by_city_id


def detect_city_slug(query: str) -> str | None:
    normalized_query = query.lower()

    for city_slug, keywords in CITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return city_slug

    return None


def detect_city_id(city_slug: str | None) -> int | None:
    if city_slug == "zelenogradsk":
        return 1

    return None


def detect_category_id(query: str) -> int | None:
    normalized_query = query.lower()

    for category_id, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return category_id

    return None


def detect_tag_id(query: str) -> int | None:
    normalized_query = query.lower()

    for tag_id, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return tag_id

    return None


def detect_place_slug(query: str) -> str | None:
    normalized_query = query.lower()

    if "place-5" in normalized_query:
        return "place-5"

    return None


def detect_intent(query: str) -> str:
    normalized_query = query.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return intent

    return "unknown"


def filter_places_for_ai(places: list) -> list:
    filtered = []

    for place in places:
        title = (place.title or "").lower()
        slug = (place.slug or "").lower()

        if "seed" in slug:
            continue
        if "point" in slug:
            continue
        if "точка" in title:
            continue
        if "зона" in title:
            continue
        if "кластер" in title:
            continue

        filtered.append(place)

    return filtered


def rank_places_for_ai(places: list, query: str) -> list:
    normalized_query = query.lower()

    wants_quiet = any(
        word in normalized_query
        for word in ["тихо", "тихие", "тихий", "спокойно", "спокойные"]
    )
    wants_romantic = any(word in normalized_query for word in ["романт", "свидан"])
    wants_dog = any(
        word in normalized_query for word in ["с собак", "dog-friendly", "dog friendly"]
    )

    def score(place) -> tuple:
        title = (place.title or "").lower()
        category = (place.category or "").lower()
        address = (place.address or "").lower()
        slug = (place.slug or "").lower()

        relevance_bonus = 0

        if wants_quiet:
            if category == "museum":
                relevance_bonus -= 4
            if "музей" in title:
                relevance_bonus -= 3
            if "quiet" in slug or "тих" in title or "спокой" in title or "спокой" in address:
                relevance_bonus -= 4
            if "кафе" in title or "кофейня" in title:
                relevance_bonus -= 1
            if "семейн" in title:
                relevance_bonus += 2
            if "информационно-туристический" in title:
                relevance_bonus += 4
            if "променад" in title:
                relevance_bonus += 2

        if wants_romantic:
            if category == "cafe":
                relevance_bonus -= 3
            if "у моря" in address:
                relevance_bonus -= 2
            if category == "walk":
                relevance_bonus -= 1

        if wants_dog:
            if place.dog_friendly:
                relevance_bonus -= 4
            else:
                relevance_bonus += 3

        return (
            relevance_bonus,
            place.price_level if place.price_level is not None else 99,
            place.id,
        )

    return sorted(places, key=score)


def process_ai_query(
    query: str,
    db: Session,
    lat: float | None = None,
    lng: float | None = None,
) -> dict:
    city_slug = detect_city_slug(query)
    city_id = detect_city_id(city_slug)
    category_id = detect_category_id(query)
    tag_id = detect_tag_id(query)
    place_slug = detect_place_slug(query)
    intent = detect_intent(query)

    if place_slug is not None:
        place = get_place_detail_by_slug(db=db, slug=place_slug)

        return {
            "status": "accepted",
            "intent": "place_detail",
            "city_slug": city_slug,
            "place_slug": place_slug,
            "query": query,
            "message": "Определен сценарий place_detail. Возвращены детали места.",
            "results": place,
        }

    if category_id is not None or tag_id is not None:
        places = get_places(
            db=db,
            city_id=city_id,
            city_slug=city_slug,
            category_id=category_id,
            tag_id=tag_id,
        )

        filtered_places = filter_places_for_ai(places)
        ranked_places = rank_places_for_ai(filtered_places, query)[:10]

        results = [
            {
                "id": place.id,
                "slug": place.slug,
                "title": place.title,
                "city_id": place.city_id,
                "category_id": place.category_id,
                "category": place.category,
                "address": place.address,
            }
            for place in ranked_places
        ]

        return {
            "status": "accepted",
            "intent": "places_filtered",
            "city_slug": city_slug,
            "category_id": category_id,
            "tag_id": tag_id,
            "query": query,
            "message": "Определен сценарий places_filtered. Возвращены лучшие места по категории и/или тегу.",
            "results": results,
        }

    if intent == "collections":
        collections = get_collections_by_city_id(db=db, city_id=city_id or 1)

        results = [
            {
                "id": collection.id,
                "slug": collection.slug,
                "title": collection.title,
                "city_id": collection.city_id,
                "short_description": collection.short_description,
                "is_active": collection.is_active,
            }
            for collection in collections
        ]

        return {
            "status": "accepted",
            "intent": "collections",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий collections. Возвращены подборки по городу.",
            "results": results,
        }

    if intent == "routes":
        routes = get_routes_by_city_id(db=db, city_id=city_id or 1)

        results = [
            {
                "id": route.id,
                "slug": route.slug,
                "title": route.title,
                "city_id": route.city_id,
                "short_description": route.short_description,
                "duration_minutes": route.duration_minutes,
                "is_active": route.is_active,
            }
            for route in routes
        ]

        return {
            "status": "accepted",
            "intent": "routes",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий routes. Возвращены маршруты по городу.",
            "results": results,
        }

    if intent == "open_now":
        open_now_places = get_open_now_places(
            db=db,
            city_slug=city_slug or "zelenogradsk",
        )

        return {
            "status": "accepted",
            "intent": "open_now",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий open_now. Возвращены места, открытые сейчас.",
            "results": open_now_places,
        }

    if intent == "nearby":
        nearby_places = get_nearby_places(
            db=db,
            lat=lat or 54.9586,
            lng=lng or 20.4751,
            radius_km=3.0,
        )

        return {
            "status": "accepted",
            "intent": "nearby",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий nearby. Возвращены ближайшие места.",
            "results": nearby_places,
        }

    return {
        "status": "accepted",
        "intent": "unknown",
        "city_slug": city_slug,
        "query": query,
        "message": "Интент пока не распознан. Нужна дальнейшая логика разбора запроса.",
        "results": [],
    }
```

### `services/category_service.py`

```py
from sqlalchemy.orm import Session

from models.category import Category


# Возвращает список всех категорий из базы данных.
def get_categories(db: Session) -> list[Category]:
    return db.query(Category).all()


# Возвращает одну категорию по ее идентификатору.
def get_category_by_id(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


# Возвращает одну категорию по ее коду.
def get_category_by_code(db: Session, code: str) -> Category | None:
    return db.query(Category).filter(Category.code == code).first()
```

### `services/city_service.py`

```py
from sqlalchemy.orm import Session

from models.city import City


# Возвращает список всех городов из базы данных.
def get_cities(db: Session) -> list[City]:
    return db.query(City).all()


# Возвращает один город по его идентификатору.
def get_city_by_id(db: Session, city_id: int) -> City | None:
    return db.query(City).filter(City.id == city_id).first()


# Возвращает один город по его slug.
def get_city_by_slug(db: Session, slug: str) -> City | None:
    return db.query(City).filter(City.slug == slug).first()
```

### `services/collection_place_service.py`

```py
from sqlalchemy.orm import Session

from models.collection_place import CollectionPlace


# Возвращает список всех связей подборок и мест.
def get_collection_places(db: Session) -> list[CollectionPlace]:
    return db.query(CollectionPlace).all()


# Возвращает список связей по идентификатору подборки.
def get_collection_places_by_collection_id(
    db: Session,
    collection_id: int,
) -> list[CollectionPlace]:
    return (
        db.query(CollectionPlace)
        .filter(CollectionPlace.collection_id == collection_id)
        .order_by(CollectionPlace.position.asc())
        .all()
    )
```

### `services/collection_service.py`

```py
from sqlalchemy.orm import Session

from models.collection import Collection


# Возвращает список всех подборок из базы данных.
def get_collections(db: Session) -> list[Collection]:
    return db.query(Collection).all()


# Возвращает список подборок конкретного города.
def get_collections_by_city_id(db: Session, city_id: int) -> list[Collection]:
    return db.query(Collection).filter(Collection.city_id == city_id).all()


# Возвращает одну подборку по ее идентификатору.
def get_collection_by_id(db: Session, collection_id: int) -> Collection | None:
    return db.query(Collection).filter(Collection.id == collection_id).first()


# Возвращает одну подборку по ее slug.
def get_collection_by_slug(db: Session, slug: str) -> Collection | None:
    return db.query(Collection).filter(Collection.slug == slug).first()
```

### `services/nearby_service.py`

```py
from math import atan2, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from models.place import Place


# Вычисляет расстояние между двумя точками на земле в километрах.
def haversine_distance(
    lat1: float,
    lng1: float,
    lat2: float,
    lng2: float,
) -> float:
    earth_radius_km = 6371.0

    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return earth_radius_km * c


# Возвращает список мест рядом с переданной точкой.
def get_nearby_places(
    db: Session,
    lat: float,
    lng: float,
    radius_km: float = 3.0,
) -> list[dict]:
    places = db.query(Place).all()
    results: list[dict] = []

    for place in places:
        distance_km = haversine_distance(lat, lng, place.lat, place.lng)
        if distance_km <= radius_km:
            results.append(
                {
                    "id": place.id,
                    "slug": place.slug,
                    "title": place.title,
                    "city_id": place.city_id,
                    "category_id": place.category_id,
                    "category": place.category,
                    "address": place.address,
                    "lat": place.lat,
                    "lng": place.lng,
                    "distance_km": round(distance_km, 3),
                }
            )

    results.sort(key=lambda item: item["distance_km"])
    return results
```

### `services/open_now_service.py`

```py
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.place_schedule import PlaceSchedule


# Возвращает код текущего дня недели.
def get_weekday_code(dt: datetime) -> str:
    weekday_map = {
        0: "mon",
        1: "tue",
        2: "wed",
        3: "thu",
        4: "fri",
        5: "sat",
        6: "sun",
    }
    return weekday_map[dt.weekday()]


# Возвращает список мест, которые открыты сейчас в выбранном городе.
def get_open_now_places(
    db: Session,
    city_slug: str,
) -> list[dict]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []

    now = datetime.now(ZoneInfo(city.timezone))
    weekday_code = get_weekday_code(now)
    current_time = now.time()

    places = (
        db.query(Place)
        .join(PlaceSchedule, Place.id == PlaceSchedule.place_id)
        .filter(Place.city_id == city.id)
        .filter(PlaceSchedule.weekday == weekday_code)
        .filter(PlaceSchedule.is_closed.is_(False))
        .all()
    )

    results: list[dict] = []

    for place in places:
        schedule = (
            db.query(PlaceSchedule)
            .filter(PlaceSchedule.place_id == place.id)
            .filter(PlaceSchedule.weekday == weekday_code)
            .first()
        )

        if schedule is None:
            continue

        if schedule.open_time is None or schedule.close_time is None:
            continue

        if schedule.open_time <= current_time <= schedule.close_time:
            results.append(
                {
                    "id": place.id,
                    "slug": place.slug,
                    "title": place.title,
                    "city_id": place.city_id,
                    "category_id": place.category_id,
                    "category": place.category,
                    "address": place.address,
                    "open_time": schedule.open_time.strftime("%H:%M"),
                    "close_time": schedule.close_time.strftime("%H:%M"),
                }
            )

    return results
```

### `services/pagination_service.py`

```py
from schemas.pagination import PaginationParams


def normalize_pagination_params(params: PaginationParams) -> PaginationParams:
    """
    Нормализует параметры пагинации.

    Пока это просто единая точка входа.
    Позже сюда можно добавить:
    - project-wide defaults
    - max-limit rules by endpoint
    - soft caps
    """
    return PaginationParams(
        limit=params.limit,
        offset=params.offset,
    )
```

### `services/place_count_service.py`

```py
from sqlalchemy.orm import Query


def get_query_total(query: Query) -> int:
    """
    Возвращает общее количество строк в запросе
    без учета limit / offset / order_by.
    """
    total_query = (
        query.enable_assertions(False)
        .order_by(None)
        .limit(None)
        .offset(None)
    )
    return total_query.count()
```

### `services/place_detail_service.py`

```py
from sqlalchemy.orm import Session

from models.place import Place
from models.place_tag import PlaceTag
from models.tag import Tag


# Возвращает детальную информацию о месте по slug.
# Дополнительно подтягивает связанные теги.
def get_place_detail_by_slug(db: Session, slug: str) -> dict | None:
    place = db.query(Place).filter(Place.slug == slug).first()
    if place is None:
        return None

    tags = (
        db.query(Tag)
        .join(PlaceTag, Tag.id == PlaceTag.tag_id)
        .filter(PlaceTag.place_id == place.id)
        .all()
    )

    return {
        "id": place.id,
        "slug": place.slug,
        "title": place.title,
        "city_id": place.city_id,
        "category_id": place.category_id,
        "category": place.category,
        "short_description": place.short_description,
        "address": place.address,
        "lat": place.lat,
        "lng": place.lng,
        "price_level": place.price_level,
        "dog_friendly": place.dog_friendly,
        "family_friendly": place.family_friendly,
        "indoor": place.indoor,
        "outdoor": place.outdoor,
        "is_active": place.is_active,
        "tags": [
            {
                "id": tag.id,
                "code": tag.code,
                "name": tag.name,
            }
            for tag in tags
        ],
    }
```

### `services/place_filters_service.py`

```py
from sqlalchemy.orm import Query, Session

from models.city import City
from models.place import Place
from models.place_tag import PlaceTag


def apply_place_filters(
    db: Session,
    query: Query,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
) -> Query | None:
    """
    Применяет базовые фильтры к query мест.

    Возвращает:
    - Query, если фильтры применены успешно
    - None, если city_slug передан, но город не найден
    """
    # Фильтруем по городу через city_id.
    if city_id is not None:
        query = query.filter(Place.city_id == city_id)

    # Фильтруем по городу через city_slug.
    if city_slug is not None:
        city = db.query(City).filter(City.slug == city_slug).first()
        if city is None:
            return None
        query = query.filter(Place.city_id == city.id)

    # Фильтруем по категории.
    if category_id is not None:
        query = query.filter(Place.category_id == category_id)

    # Фильтруем по тегу через таблицу связей.
    if tag_id is not None:
        query = query.join(PlaceTag, Place.id == PlaceTag.place_id).filter(
            PlaceTag.tag_id == tag_id
        )

    return query
```

### `services/place_list_params_service.py`

```py
from schemas.place_list_params import PlaceListParams
from schemas.place_search import PlaceSearchParams
from schemas.pagination import PaginationParams
from services.place_search_params_service import normalize_place_search_params
from services.pagination_service import normalize_pagination_params


def normalize_place_list_params(params: PlaceListParams) -> PlaceListParams:
    """
    Нормализует объединенные параметры списка мест.

    Объединяет:
    - нормализацию search-параметров
    - нормализацию pagination-параметров
    """
    normalized_search = normalize_place_search_params(
        PlaceSearchParams(
            city_id=params.city_id,
            city_slug=params.city_slug,
            category_id=params.category_id,
            tag_id=params.tag_id,
            q=params.q,
        )
    )

    normalized_pagination = normalize_pagination_params(
        PaginationParams(
            limit=params.limit,
            offset=params.offset,
        )
    )

    return PlaceListParams(
        city_id=normalized_search.city_id,
        city_slug=normalized_search.city_slug,
        category_id=normalized_search.category_id,
        tag_id=normalized_search.tag_id,
        q=normalized_search.q,
        limit=normalized_pagination.limit,
        offset=normalized_pagination.offset,
    )
```

### `services/place_query_params_service.py`

```py
from schemas.place_query_params import PlaceQueryParams
from schemas.place_list_params import PlaceListParams
from schemas.sorting import SortingParams
from services.place_list_params_service import normalize_place_list_params
from services.sorting_service import normalize_sorting_params


def normalize_place_query_params(params: PlaceQueryParams) -> PlaceQueryParams:
    """
    Нормализует единые параметры запроса по местам.

    Объединяет:
    - нормализацию list/search-параметров
    - нормализацию sorting-параметров
    """
    normalized_list = normalize_place_list_params(
        PlaceListParams(
            city_id=params.city_id,
            city_slug=params.city_slug,
            category_id=params.category_id,
            tag_id=params.tag_id,
            q=params.q,
            limit=params.limit,
            offset=params.offset,
        )
    )

    normalized_sorting = normalize_sorting_params(
        SortingParams(
            sort_by=params.sort_by,
            sort_order=params.sort_order,
        )
    )

    return PlaceQueryParams(
        city_id=normalized_list.city_id,
        city_slug=normalized_list.city_slug,
        category_id=normalized_list.category_id,
        tag_id=normalized_list.tag_id,
        q=normalized_list.q,
        limit=normalized_list.limit,
        offset=normalized_list.offset,
        sort_by=normalized_sorting.sort_by,
        sort_order=normalized_sorting.sort_order,
    )
```

### `services/place_search_params_service.py`

```py
from schemas.place_search import PlaceSearchParams


def normalize_place_search_params(params: PlaceSearchParams) -> PlaceSearchParams:
    """
    Нормализует параметры поиска мест.

    Пока:
    - обрезаем пробелы у q
    - пустую строку превращаем в None

    Позже сюда можно добавить:
    - lower()
    - alias-логику
    - валидацию конфликтующих фильтров
    """
    q = params.q.strip() if params.q else None

    if q == "":
        q = None

    return PlaceSearchParams(
        city_id=params.city_id,
        city_slug=params.city_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
        q=q,
    )
```

### `services/place_search_response_service.py`

```py
from schemas.place_search_response import PlaceSearchResponse


def build_place_search_response(
    items,
    total: int,
    limit: int,
    offset: int,
) -> PlaceSearchResponse:
    """
    Собирает стандартный ответ для list/search сценариев по местам.
    """
    return PlaceSearchResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
```

### `services/place_search_service.py`

```py
from sqlalchemy import or_
from sqlalchemy.orm import Query

from models.place import Place


# Добавляет текстовый поиск по месту.
def apply_place_text_search(query: Query, q: str | None) -> Query:
    """
    Добавляет текстовый поиск по полям Place.

    Пока ищем по:
    - title
    - slug

    Позже сюда можно добавить:
    - short_description
    - full_description
    - address
    """
    if not q:
        return query

    search_value = f"%{q.strip()}%"

    return query.filter(
        or_(
            Place.title.ilike(search_value),
            Place.slug.ilike(search_value),
        )
    )
```

### `services/place_seed_bulk_validation_service.py`

```py
from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_seed_item import PlaceSeedItem
from services.place_seed_validation_service import validate_place_seed_item


def validate_place_seed_items(
    items: list[PlaceSeedItem],
) -> PlaceSeedBulkValidationResponse:
    """
    Валидирует список seed-элементов мест и собирает общий результат.
    """
    results = [validate_place_seed_item(item) for item in items]

    valid_count = sum(1 for item in results if item.is_valid)
    invalid_count = len(results) - valid_count

    return PlaceSeedBulkValidationResponse(
        total=len(results),
        valid_count=valid_count,
        invalid_count=invalid_count,
        items=results,
    )
```

### `services/place_seed_dry_run_service.py`

```py
from schemas.place_seed_import_summary import PlaceSeedImportSummary
from schemas.place_seed_item import PlaceSeedItem
from services.place_seed_import_summary_service import (
    build_place_seed_import_summary,
)
from services.place_seed_validation_service import validate_place_seed_item


def run_place_seed_dry_run(items: list[PlaceSeedItem]) -> PlaceSeedImportSummary:
    """
    Выполняет dry-run проверку seed-элементов мест без записи в БД.

    Логика текущего MVP:
    - валидные элементы считаем как skipped
    - невалидные считаем как invalid
    - created / updated пока не трогаем, так как записи в БД нет
    """
    invalid = 0
    skipped = 0
    errors: list[str] = []

    for index, item in enumerate(items, start=1):
        result = validate_place_seed_item(item)

        if result.is_valid:
            skipped += 1
            continue

        invalid += 1
        slug_for_error = item.slug.strip() if item.slug and item.slug.strip() else "<empty-slug>"
        errors.append(f"item {index}: {slug_for_error} is invalid")

    return build_place_seed_import_summary(
        total=len(items),
        created=0,
        updated=0,
        skipped=skipped,
        invalid=invalid,
        errors=errors,
    )
```

### `services/place_seed_import_summary_service.py`

```py
from schemas.place_seed_import_summary import PlaceSeedImportSummary


def build_place_seed_import_summary(
    total: int,
    created: int = 0,
    updated: int = 0,
    skipped: int = 0,
    invalid: int = 0,
    errors: list[str] | None = None,
) -> PlaceSeedImportSummary:
    """
    Собирает стандартную сводку по seed-импорту мест.
    """
    return PlaceSeedImportSummary(
        total=total,
        created=created,
        updated=updated,
        skipped=skipped,
        invalid=invalid,
        errors=errors or [],
    )
```

### `services/place_seed_validation_service.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_seed_validation_response import PlaceSeedValidationResponse
from services.place_taxonomy_diagnostics_service import (
    get_invalid_place_taxonomy_values,
)


def validate_place_seed_item(item: PlaceSeedItem) -> PlaceSeedValidationResponse:
    """
    Валидирует один seed-элемент места.

    Сейчас проверяем:
    - обязательные текстовые поля не пустые
    - taxonomy проходит каноничную диагностику

    Позже сюда можно добавить:
    - проверку city_slug по БД
    - проверку уникальности slug
    - проверку lat/lng pair
    - проверку source/source_url
    """
    errors: list[str] = []

    if not item.title.strip():
        errors.append("title is empty")

    if not item.slug.strip():
        errors.append("slug is empty")

    if not item.city_slug.strip():
        errors.append("city_slug is empty")

    taxonomy_diagnostics = get_invalid_place_taxonomy_values(item.taxonomy)

    has_invalid_taxonomy = any(
        [
            taxonomy_diagnostics.category is not None,
            len(taxonomy_diagnostics.tags) > 0,
            len(taxonomy_diagnostics.scenario_tags) > 0,
            len(taxonomy_diagnostics.vibe_tags) > 0,
            len(taxonomy_diagnostics.restriction_tags) > 0,
        ]
    )

    is_valid = len(errors) == 0 and not has_invalid_taxonomy

    return PlaceSeedValidationResponse(
        is_valid=is_valid,
        title=item.title,
        slug=item.slug,
        city_slug=item.city_slug,
        taxonomy_diagnostics=taxonomy_diagnostics,
        errors=errors,
    )
```

### `services/place_service.py`

```py
from sqlalchemy.orm import Session

from models.place import Place
from schemas.place import PlaceCreate, PlaceUpdate
from schemas.place_query_params import PlaceQueryParams
from services.place_count_service import get_query_total
from services.place_filters_service import apply_place_filters
from services.place_query_params_service import normalize_place_query_params
from services.place_search_service import apply_place_text_search
from services.place_sorting_service import apply_place_sorting


# Возвращает список мест с учетом переданных фильтров.
def get_places(
    db: Session,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "title",
    sort_order: str = "asc",
) -> list[Place]:
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )

    query = db.query(Place)

    # Базовые фильтры.
    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return []

    # Текстовый поиск по title / slug.
    query = apply_place_text_search(query, params.q)

    # Сортировка.
    query = apply_place_sorting(
        query=query,
        params=params,
    )

    # Базовая пагинация.
    query = query.offset(params.offset).limit(params.limit)

    return query.all()


def get_places_total(
    db: Session,
    city_id: int | None = None,
    city_slug: str | None = None,
    category_id: int | None = None,
    tag_id: int | None = None,
    q: str | None = None,
) -> int:
    """
    Возвращает общее количество мест по тем же фильтрам,
    но без применения limit / offset.
    """
    params = normalize_place_query_params(
        PlaceQueryParams(
            city_id=city_id,
            city_slug=city_slug,
            category_id=category_id,
            tag_id=tag_id,
            q=q,
        )
    )

    query = db.query(Place)

    query = apply_place_filters(
        db=db,
        query=query,
        city_id=params.city_id,
        city_slug=params.city_slug,
        category_id=params.category_id,
        tag_id=params.tag_id,
    )
    if query is None:
        return 0

    query = apply_place_text_search(query, params.q)

    return get_query_total(query)


# Возвращает одно место по его идентификатору.
def get_place_by_id(db: Session, place_id: int) -> Place | None:
    return db.query(Place).filter(Place.id == place_id).first()


# Возвращает одно место по его slug.
def get_place_by_slug(db: Session, slug: str) -> Place | None:
    return db.query(Place).filter(Place.slug == slug).first()


# Создает новое место, сохраняет его в базе и возвращает результат.
def create_place(db: Session, place_in: PlaceCreate) -> Place:
    place = Place(**place_in.model_dump())
    db.add(place)
    db.commit()
    db.refresh(place)
    return place


# Обновляет существующее место и возвращает его после сохранения.
def update_place(db: Session, place_id: int, place_in: PlaceUpdate) -> Place | None:
    place = get_place_by_id(db, place_id)
    if place is None:
        return None

    for field, value in place_in.model_dump().items():
        setattr(place, field, value)

    db.commit()
    db.refresh(place)
    return place


# Удаляет место по идентификатору.
def delete_place(db: Session, place_id: int) -> bool:
    place = get_place_by_id(db, place_id)
    if place is None:
        return False

    db.delete(place)
    db.commit()
    return True
```

### `services/place_sorting_service.py`

```py
from sqlalchemy import asc, desc
from sqlalchemy.orm import Query

from models.place import Place
from schemas.sorting import SortingParams
from services.sorting_service import normalize_sorting_params


def apply_place_sorting(query: Query, params: SortingParams) -> Query:
    """
    Применяет сортировку к query мест.

    Поддерживаемые поля:
    - title
    - created_at
    """
    normalized = normalize_sorting_params(params)

    sort_fields = {
        "title": Place.title,
        "created_at": Place.created_at,
    }

    column = sort_fields[normalized.sort_by]
    order_func = asc if normalized.sort_order == "asc" else desc

    return query.order_by(order_func(column))
```

### `services/place_tag_service.py`

```py
from sqlalchemy.orm import Session

from models.place_tag import PlaceTag


# Возвращает список всех связей мест и тегов.
def get_place_tags(db: Session) -> list[PlaceTag]:
    return db.query(PlaceTag).all()


# Возвращает список связей по идентификатору места.
def get_place_tags_by_place_id(db: Session, place_id: int) -> list[PlaceTag]:
    return db.query(PlaceTag).filter(PlaceTag.place_id == place_id).all()


# Создает новую связь места и тега.
def create_place_tag(db: Session, place_id: int, tag_id: int) -> PlaceTag:
    place_tag = PlaceTag(place_id=place_id, tag_id=tag_id)
    db.add(place_tag)
    db.commit()
    db.refresh(place_tag)
    return place_tag
```

### `services/place_taxonomy_diagnostics_response_service.py`

```py
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


def build_place_taxonomy_diagnostics_response(
    category: str | None,
    tags: list[str],
    scenario_tags: list[str],
    vibe_tags: list[str],
    restriction_tags: list[str],
) -> PlaceTaxonomyDiagnosticsResponse:
    """
    Собирает стандартный ответ диагностики taxonomy payload.
    """
    return PlaceTaxonomyDiagnosticsResponse(
        category=category,
        tags=tags,
        scenario_tags=scenario_tags,
        vibe_tags=vibe_tags,
        restriction_tags=restriction_tags,
    )
```

### `services/place_taxonomy_diagnostics_service.py`

```py
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)
from services.place_taxonomy_diagnostics_response_service import (
    build_place_taxonomy_diagnostics_response,
)
from services.place_taxonomy_service import (
    is_valid_place_category,
    is_valid_place_restriction_tag,
    is_valid_place_scenario_tag,
    is_valid_place_tag,
    is_valid_place_vibe_tag,
)


def get_invalid_place_taxonomy_values(
    payload: PlaceTaxonomyPayload,
) -> PlaceTaxonomyDiagnosticsResponse:
    """
    Возвращает невалидные значения таксономии места.

    Нужен для:
    - импорта seed-данных
    - админских проверок
    - AI enrichment pipeline
    - отладки перед записью в БД
    """
    invalid_category = None if is_valid_place_category(payload.category) else payload.category

    invalid_tags = [value for value in payload.tags if not is_valid_place_tag(value)]
    invalid_scenario_tags = [
        value for value in payload.scenario_tags if not is_valid_place_scenario_tag(value)
    ]
    invalid_vibe_tags = [
        value for value in payload.vibe_tags if not is_valid_place_vibe_tag(value)
    ]
    invalid_restriction_tags = [
        value
        for value in payload.restriction_tags
        if not is_valid_place_restriction_tag(value)
    ]

    return build_place_taxonomy_diagnostics_response(
        category=invalid_category,
        tags=invalid_tags,
        scenario_tags=invalid_scenario_tags,
        vibe_tags=invalid_vibe_tags,
        restriction_tags=invalid_restriction_tags,
    )
```

### `services/place_taxonomy_payload_service.py`

```py
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_service import (
    is_valid_place_category,
    is_valid_place_restriction_tag,
    is_valid_place_scenario_tag,
    is_valid_place_tag,
    is_valid_place_vibe_tag,
    validate_tag_list,
)


def normalize_place_taxonomy_payload(
    payload: PlaceTaxonomyPayload,
) -> PlaceTaxonomyPayload:
    """
    Нормализует и очищает таксономию места по каноничным правилам.

    Правила:
    - category оставляем только если она валидна
    - tags / scenario_tags / vibe_tags / restriction_tags
      очищаем от невалидных значений и дублей
    """
    category = payload.category if is_valid_place_category(payload.category) else ""

    return PlaceTaxonomyPayload(
        category=category,
        tags=validate_tag_list(payload.tags, is_valid_place_tag),
        scenario_tags=validate_tag_list(
            payload.scenario_tags,
            is_valid_place_scenario_tag,
        ),
        vibe_tags=validate_tag_list(payload.vibe_tags, is_valid_place_vibe_tag),
        restriction_tags=validate_tag_list(
            payload.restriction_tags,
            is_valid_place_restriction_tag,
        ),
    )
```

### `services/place_taxonomy_response_service.py`

```py
from core.place_taxonomy import (
    PLACE_CATEGORIES,
    PLACE_RESTRICTION_TAGS,
    PLACE_SCENARIO_TAGS,
    PLACE_TAGS,
    PLACE_VIBE_TAGS,
    USER_SIGNALS,
)
from schemas.place_taxonomy_response import PlaceTaxonomyResponse


def build_place_taxonomy_response() -> PlaceTaxonomyResponse:
    """
    Собирает стандартный ответ для каноничной таксономии City GO.
    """
    return PlaceTaxonomyResponse(
        categories=PLACE_CATEGORIES,
        tags=PLACE_TAGS,
        scenario_tags=PLACE_SCENARIO_TAGS,
        vibe_tags=PLACE_VIBE_TAGS,
        restriction_tags=PLACE_RESTRICTION_TAGS,
        user_signals=USER_SIGNALS,
    )
```

### `services/place_taxonomy_service.py`

```py
"""
Сервис работы с каноничной таксономией City GO.
"""

from core.place_taxonomy import (
    PLACE_CATEGORIES,
    PLACE_RESTRICTION_TAGS,
    PLACE_SCENARIO_TAGS,
    PLACE_TAGS,
    PLACE_VIBE_TAGS,
)


def is_valid_place_category(value: str) -> bool:
    """
    Проверяет, что категория места входит в канон.
    """
    return value in PLACE_CATEGORIES


def is_valid_place_tag(value: str) -> bool:
    """
    Проверяет, что обычный тег места входит в канон.
    """
    return value in PLACE_TAGS


def is_valid_place_scenario_tag(value: str) -> bool:
    """
    Проверяет, что сценарный тег входит в канон.
    """
    return value in PLACE_SCENARIO_TAGS


def is_valid_place_vibe_tag(value: str) -> bool:
    """
    Проверяет, что vibe-тег входит в канон.
    """
    return value in PLACE_VIBE_TAGS


def is_valid_place_restriction_tag(value: str) -> bool:
    """
    Проверяет, что restriction-тег входит в канон.
    """
    return value in PLACE_RESTRICTION_TAGS


def validate_tag_list(values: list[str], validator) -> list[str]:
    """
    Возвращает только валидные значения из списка.

    Дубликаты убираются с сохранением порядка.
    """
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        if value in seen:
            continue
        if validator(value):
            result.append(value)
            seen.add(value)

    return result
```

### `services/route_place_service.py`

```py
from sqlalchemy.orm import Session

from models.route_place import RoutePlace


# Возвращает список всех связей маршрутов и мест.
def get_route_places(db: Session) -> list[RoutePlace]:
    return db.query(RoutePlace).all()


# Возвращает список связей по идентификатору маршрута.
def get_route_places_by_route_id(db: Session, route_id: int) -> list[RoutePlace]:
    return (
        db.query(RoutePlace)
        .filter(RoutePlace.route_id == route_id)
        .order_by(RoutePlace.position.asc())
        .all()
    )
```

### `services/route_service.py`

```py
from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.route import Route
from models.route_place import RoutePlace


def get_routes(db: Session) -> list[Route]:
    return db.query(Route).all()


def get_routes_by_city_id(db: Session, city_id: int) -> list[Route]:
    return db.query(Route).filter(Route.city_id == city_id).all()


def get_routes_by_city_slug(db: Session, city_slug: str) -> list[Route]:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return []

    return db.query(Route).filter(Route.city_id == city.id).all()


def get_route_by_id(db: Session, route_id: int) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.id == route_id)
        .first()
    )

    if route is None:
        return None

    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


def get_route_by_slug(db: Session, slug: str) -> Route | None:
    route = (
        db.query(Route)
        .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
        .filter(Route.slug == slug)
        .first()
    )

    if route is None:
        return None

    route.route_places = sorted(route.route_places, key=lambda item: item.position)
    return route


def build_route_points(route: Route) -> list[dict]:
    points: list[dict] = []

    for item in sorted(route.route_places, key=lambda row: row.position):
        place = item.place

        points.append(
            {
                "place_id": item.place_id,
                "position": item.position,
                "place_slug": place.slug if place else None,
                "place_title": place.title if place else None,
            }
        )

    return points
```

### `services/sorting_service.py`

```py
from schemas.sorting import SortingParams


def normalize_sorting_params(params: SortingParams) -> SortingParams:
    """
    Нормализует параметры сортировки.

    Пока это единая точка входа.
    Позже сюда можно добавить:
    - endpoint-specific defaults
    - alias mapping
    - compatibility rules
    """
    return SortingParams(
        sort_by=params.sort_by,
        sort_order=params.sort_order,
    )
```

### `services/tag_service.py`

```py
from sqlalchemy.orm import Session

from models.tag import Tag


# Возвращает список всех тегов из базы данных.
def get_tags(db: Session) -> list[Tag]:
    return db.query(Tag).all()


# Возвращает один тег по его идентификатору.
def get_tag_by_id(db: Session, tag_id: int) -> Tag | None:
    return db.query(Tag).filter(Tag.id == tag_id).first()


# Возвращает один тег по его коду.
def get_tag_by_code(db: Session, code: str) -> Tag | None:
    return db.query(Tag).filter(Tag.code == code).first()
```

### `telegram_bot/__init__.py`

```py
# Пакет Telegram-бота City GO.
```

### `telegram_bot/handlers/__init__.py`

```py
# Пакет с хендлерами Telegram-бота City GO.
```

### `telegram_bot/handlers/address.py`

```py
"""
Хендлер ручного ввода адреса для Telegram-бота City GO.

Текущая логика:
- пользователь нажимает кнопку "Ввести адрес"
- бот переходит в состояние ожидания адреса
- пользователь отправляет адрес текстом
- бот сохраняет адрес в памяти процесса

Пока без геокодинга.
"""

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.address_context import save_user_address
from telegram_bot.services.messages import (
    ADDRESS_CANCELLED_TEXT,
    ADDRESS_EMPTY_TEXT,
    ADDRESS_HINT_TEXT,
    ADDRESS_SAVED_TEMPLATE,
)
from telegram_bot.states.address_state import AddressInputState


router = Router()


@router.message(F.text == "Ввести адрес")
async def manual_address_entry_handler(message: Message, state: FSMContext) -> None:
    """
    Вход в сценарий ручного ввода адреса.
    """
    await state.set_state(AddressInputState.waiting_for_address)

    await message.answer(
        ADDRESS_HINT_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(
    AddressInputState.waiting_for_address,
    F.text.in_({"Отмена", "отмена", "/cancel"}),
)
async def manual_address_cancel_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Отмена сценария ручного ввода адреса.
    """
    await state.clear()

    await message.answer(
        ADDRESS_CANCELLED_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(AddressInputState.waiting_for_address)
async def manual_address_value_handler(
    message: Message,
    state: FSMContext,
) -> None:
    """
    Принимает адрес пользователя в виде текста.
    """
    raw_address = (message.text or "").strip()

    if not raw_address:
        await message.answer(
            ADDRESS_EMPTY_TEXT,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    if message.from_user:
        save_user_address(
            user_id=message.from_user.id,
            raw_address=raw_address,
        )

    await state.clear()

    await message.answer(
        ADDRESS_SAVED_TEMPLATE.format(raw_address=raw_address),
        reply_markup=get_main_menu_keyboard(),
    )
```

### `telegram_bot/handlers/health.py`

```py
"""
Хендлер проверки состояния backend для Telegram-бота City GO.
"""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.services.api_client import CityGoApiClient


router = Router()


@router.message(Command("health"))
async def health_handler(message: Message) -> None:
    """
    Проверяет состояние backend через API client.
    """
    client = CityGoApiClient()
    result = await client.get_health()

    if result["ok"]:
        await message.answer(
            (
                "<b>Проверка backend</b>\n\n"
                f"Статус: <b>{result['status']}</b>\n"
                f"URL: <b>{result['base_url']}</b>"
            )
        )
        return

    await message.answer(
        (
            "<b>Проверка backend</b>\n\n"
            "Backend сейчас недоступен.\n"
            f"URL: <b>{result['base_url']}</b>\n"
            f"Ошибка: <b>{result['error']}</b>"
        )
    )
```

### `telegram_bot/handlers/location.py`

```py
"""
Хендлер геолокации для Telegram-бота City GO.
"""

from aiogram import Router
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.messages import (
    BACKEND_ERROR_TEMPLATE,
    NEARBY_EMPTY_TEMPLATE,
    NEARBY_RESULT_HEADER_TEMPLATE,
    RESULT_ITEM_TEMPLATE,
)
from telegram_bot.services.user_context import save_user_location


router = Router()


def _extract_title(item: dict) -> str:
    """
    Пытается безопасно достать название места из ответа backend.
    """
    return (
        item.get("title")
        or item.get("name")
        or item.get("place_name")
        or f"Place #{item.get('id', 'unknown')}"
    )


@router.message(lambda message: message.location is not None)
async def location_handler(message: Message) -> None:
    """
    Принимает геолокацию пользователя, сохраняет ее
    и запрашивает nearby places.
    """
    if not message.location:
        await message.answer(
            "Не удалось получить геолокацию.",
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lat = message.location.latitude
    lng = message.location.longitude
    radius_km = 3.0

    if message.from_user:
        save_user_location(
            user_id=message.from_user.id,
            lat=lat,
            lng=lng,
        )

    client = CityGoApiClient()
    result = await client.get_nearby_places(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            NEARBY_EMPTY_TEMPLATE.format(
                lat=lat,
                lng=lng,
                radius_km=radius_km,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = [
        NEARBY_RESULT_HEADER_TEMPLATE.format(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        )
    ]
    for item in items[:10]:
        lines.append(RESULT_ITEM_TEMPLATE.format(title=_extract_title(item)))

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )
```

### `telegram_bot/handlers/menu.py`

```py
"""
Хендлеры кнопок главного меню Telegram-бота City GO.
"""

from aiogram import F, Router
from aiogram.types import Message

from core.config import settings
from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.api_client import CityGoApiClient
from telegram_bot.services.messages import (
    BACKEND_ERROR_TEMPLATE,
    COFFEE_EMPTY_TEMPLATE,
    COFFEE_LOADING_TEXT,
    COFFEE_RESULT_HEADER_TEMPLATE,
    DOG_FRIENDLY_EMPTY_TEMPLATE,
    DOG_FRIENDLY_LOADING_TEXT,
    DOG_FRIENDLY_RESULT_HEADER_TEMPLATE,
    FOOD_EMPTY_TEMPLATE,
    FOOD_LOADING_TEXT,
    FOOD_RESULT_HEADER_TEMPLATE,
    NEARBY_EMPTY_TEMPLATE,
    NEARBY_RESULT_HEADER_TEMPLATE,
    NEARBY_STUB_TEXT,
    OPEN_NOW_EMPTY_TEMPLATE,
    OPEN_NOW_LOADING_TEXT,
    OPEN_NOW_RESULT_HEADER_TEMPLATE,
    RESULT_ITEM_TEMPLATE,
    WALKS_EMPTY_TEMPLATE,
    WALKS_LOADING_TEXT,
    WALKS_RESULT_HEADER_TEMPLATE,
)
from telegram_bot.services.user_context import get_user_location


router = Router()


def _extract_title(item: dict) -> str:
    """
    Пытается безопасно достать название места из ответа backend.
    """
    return (
        item.get("title")
        or item.get("name")
        or item.get("place_name")
        or f"Place #{item.get('id', 'unknown')}"
    )


def _build_result_lines(header: str, items: list[dict]) -> list[str]:
    """
    Собирает список строк для ответа пользователю.
    """
    lines = [header]
    for item in items[:10]:
        lines.append(RESULT_ITEM_TEMPLATE.format(title=_extract_title(item)))
    return lines


@router.message(F.text == "Что рядом")
async def nearby_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Что рядом'.

    Если геолокация уже была отправлена ранее, используем ее.
    Если геолокации нет, не упираемся в тупик:
    объясняем, что можно отправить геолокацию,
    и оставляем пользователю альтернативные сценарии через меню.
    """
    if not message.from_user:
        await message.answer(
            NEARBY_STUB_TEXT,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    user_location = get_user_location(message.from_user.id)

    if not user_location:
        await message.answer(
            NEARBY_STUB_TEXT,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lat = user_location["lat"]
    lng = user_location["lng"]
    radius_km = 3.0

    client = CityGoApiClient()
    result = await client.get_nearby_places(
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            NEARBY_EMPTY_TEMPLATE.format(
                lat=lat,
                lng=lng,
                radius_km=radius_km,
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = _build_result_lines(
        header=NEARBY_RESULT_HEADER_TEMPLATE.format(
            lat=lat,
            lng=lng,
            radius_km=radius_km,
        ),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "Что открыто")
async def open_now_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Что открыто'.
    Использует default_city_slug из настроек проекта.
    """
    city_slug = settings.default_city_slug

    await message.answer(
        OPEN_NOW_LOADING_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )

    client = CityGoApiClient()
    result = await client.get_open_now_places(city_slug=city_slug)

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            OPEN_NOW_EMPTY_TEMPLATE.format(city_slug=city_slug),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = _build_result_lines(
        header=OPEN_NOW_RESULT_HEADER_TEMPLATE.format(city_slug=city_slug),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "Где кофе")
async def coffee_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Где кофе'.
    Использует общий /places/ endpoint с фильтрами из настроек.
    """
    city_slug = settings.default_city_slug

    await message.answer(
        COFFEE_LOADING_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )

    client = CityGoApiClient()
    result = await client.get_coffee_places()

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            COFFEE_EMPTY_TEMPLATE.format(city_slug=city_slug),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = _build_result_lines(
        header=COFFEE_RESULT_HEADER_TEMPLATE.format(city_slug=city_slug),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "Где поесть")
async def food_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Где поесть'.
    Использует общий /places/ endpoint с фильтрами из настроек.
    """
    city_slug = settings.default_city_slug

    await message.answer(
        FOOD_LOADING_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )

    client = CityGoApiClient()
    result = await client.get_food_places()

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            FOOD_EMPTY_TEMPLATE.format(city_slug=city_slug),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = _build_result_lines(
        header=FOOD_RESULT_HEADER_TEMPLATE.format(city_slug=city_slug),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "Куда погулять")
async def walks_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Куда погулять'.
    Использует общий /places/ endpoint с фильтрами из настроек.
    """
    city_slug = settings.default_city_slug

    await message.answer(
        WALKS_LOADING_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )

    client = CityGoApiClient()
    result = await client.get_walk_places()

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            WALKS_EMPTY_TEMPLATE.format(city_slug=city_slug),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = _build_result_lines(
        header=WALKS_RESULT_HEADER_TEMPLATE.format(city_slug=city_slug),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "С собакой")
async def dog_friendly_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'С собакой'.
    Использует общий /places/ endpoint с фильтрами из настроек.
    """
    city_slug = settings.default_city_slug

    await message.answer(
        DOG_FRIENDLY_LOADING_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )

    client = CityGoApiClient()
    result = await client.get_dog_friendly_places()

    if not result["ok"]:
        await message.answer(
            BACKEND_ERROR_TEMPLATE.format(
                base_url=result["base_url"],
                error=result["error"],
            ),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    items = result["items"]

    if not items:
        await message.answer(
            DOG_FRIENDLY_EMPTY_TEMPLATE.format(city_slug=city_slug),
            reply_markup=get_main_menu_keyboard(),
        )
        return

    lines = _build_result_lines(
        header=DOG_FRIENDLY_RESULT_HEADER_TEMPLATE.format(city_slug=city_slug),
        items=items,
    )

    await message.answer(
        "\n".join(lines),
        reply_markup=get_main_menu_keyboard(),
    )
```

### `telegram_bot/handlers/start.py`

```py
"""
Стартовые хендлеры Telegram-бота City GO.
"""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from telegram_bot.keyboards.main_menu import get_main_menu_keyboard
from telegram_bot.services.messages import (
    HELP_TEXT,
    MAIN_MENU_REOPENED,
    MVP_FALLBACK_TEMPLATE,
    ONLY_TEXT_MESSAGE,
    WELCOME_TEXT,
)


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Обрабатывает команду /start.
    """
    await message.answer(
        WELCOME_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """
    Обрабатывает команду /help.
    """
    await message.answer(
        HELP_TEXT,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message(F.text == "Помощь")
async def help_button_handler(message: Message) -> None:
    """
    Обрабатывает кнопку 'Помощь'.
    """
    await cmd_help(message)


@router.message(F.text == "Главное меню")
async def main_menu_button_handler(message: Message) -> None:
    """
    Повторно показывает главное меню.
    """
    await message.answer(
        MAIN_MENU_REOPENED,
        reply_markup=get_main_menu_keyboard(),
    )


@router.message()
async def fallback_message_handler(message: Message) -> None:
    """
    Временная заглушка для всех остальных текстовых сообщений.
    Позже сюда подключим AI intent parsing и вызовы backend API.
    """
    user_text = (message.text or "").strip()

    if not user_text:
        await message.answer(
            ONLY_TEXT_MESSAGE,
            reply_markup=get_main_menu_keyboard(),
        )
        return

    await message.answer(
        MVP_FALLBACK_TEMPLATE.format(user_text=user_text),
        reply_markup=get_main_menu_keyboard(),
    )
```

### `telegram_bot/keyboards/__init__.py`

```py
# Пакет с клавиатурами Telegram-бота City GO.
```

### `telegram_bot/keyboards/main_menu.py`

```py
"""
Клавиатуры главного меню для Telegram-бота City GO.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu_keyboard() -> ReplyKeyboardMarkup:
    """
    Возвращает основную reply-клавиатуру для MVP-бота.
    """
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="Что рядом"),
                KeyboardButton(text="Что открыто"),
            ],
            [
                KeyboardButton(text="Где кофе"),
                KeyboardButton(text="Где поесть"),
            ],
            [
                KeyboardButton(text="Куда погулять"),
                KeyboardButton(text="С собакой"),
            ],
            [
                KeyboardButton(text="Отправить геолокацию", request_location=True),
                KeyboardButton(text="Ввести адрес"),
            ],
            [
                KeyboardButton(text="Помощь"),
                KeyboardButton(text="Главное меню"),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Напиши, что ищешь...",
    )
```

### `telegram_bot/services/__init__.py`

```py
# Пакет сервисов Telegram-бота City GO.
```

### `telegram_bot/services/address_context.py`

```py
"""
Простое in-memory хранилище адресов для Telegram-бота City GO.

Важно:
- это временное решение для MVP;
- данные живут только пока запущен процесс бота;
- позже можно заменить на Redis / БД.
"""

from typing import TypedDict


class UserAddress(TypedDict):
    """
    Последний введенный адрес пользователя.
    """

    raw_address: str


USER_ADDRESSES: dict[int, UserAddress] = {}


def save_user_address(user_id: int, raw_address: str) -> None:
    """
    Сохраняет последний введенный адрес пользователя.
    """
    USER_ADDRESSES[user_id] = {
        "raw_address": raw_address,
    }


def get_user_address(user_id: int) -> UserAddress | None:
    """
    Возвращает последний сохраненный адрес пользователя.
    """
    return USER_ADDRESSES.get(user_id)
```

### `telegram_bot/services/api_client.py`

```py
"""
API-клиент для работы Telegram-бота с backend City GO.
"""

from typing import Any

import httpx

from core.config import settings


class CityGoApiClient:
    """
    API-клиент для Telegram-бота.
    Работает с backend City GO через HTTP.
    """

    def __init__(self, base_url: str | None = None) -> None:
        """
        Сохраняет базовый URL backend API.
        """
        self.base_url = (base_url or settings.backend_base_url).rstrip("/")

    async def get_health(self) -> dict[str, Any]:
        """
        Проверяет backend через endpoint /health.
        """
        url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url)
                response.raise_for_status()

            data = response.json()

            return {
                "status": data.get("status", "unknown"),
                "base_url": self.base_url,
                "ok": True,
            }
        except Exception as exc:
            return {
                "status": "error",
                "base_url": self.base_url,
                "ok": False,
                "error": str(exc),
            }

    async def get_nearby_places(
        self,
        lat: float,
        lng: float,
        radius_km: float = 3.0,
    ) -> dict[str, Any]:
        """
        Получает список мест рядом через backend endpoint /nearby/.
        """
        url = f"{self.base_url}/nearby/"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    params={
                        "lat": lat,
                        "lng": lng,
                        "radius_km": radius_km,
                    },
                )
                response.raise_for_status()

            data = response.json()

            return {
                "ok": True,
                "base_url": self.base_url,
                "items": data,
            }
        except Exception as exc:
            return {
                "ok": False,
                "base_url": self.base_url,
                "items": [],
                "error": str(exc),
            }

    async def get_open_now_places(self, city_slug: str) -> dict[str, Any]:
        """
        Получает список мест, которые открыты сейчас, через backend endpoint /open-now/.
        """
        url = f"{self.base_url}/open-now/"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    params={
                        "city_slug": city_slug,
                    },
                )
                response.raise_for_status()

            data = response.json()

            return {
                "ok": True,
                "base_url": self.base_url,
                "items": data,
            }
        except Exception as exc:
            return {
                "ok": False,
                "base_url": self.base_url,
                "items": [],
                "error": str(exc),
            }

    async def get_places(
        self,
        city_slug: str | None = None,
        category_id: int | None = None,
        tag_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Получает список мест через backend endpoint /places/.
        """
        url = f"{self.base_url}/places/"

        params: dict[str, Any] = {}

        if city_slug is not None:
            params["city_slug"] = city_slug

        if category_id is not None:
            params["category_id"] = category_id

        if tag_id is not None:
            params["tag_id"] = tag_id

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()

            data = response.json()

            return {
                "ok": True,
                "base_url": self.base_url,
                "items": data,
            }
        except Exception as exc:
            return {
                "ok": False,
                "base_url": self.base_url,
                "items": [],
                "error": str(exc),
            }

    async def get_coffee_places(self) -> dict[str, Any]:
        """
        Получает места для сценария 'Где кофе'.
        """
        return await self.get_places(
            city_slug=settings.default_city_slug,
            category_id=settings.coffee_category_id,
            tag_id=settings.coffee_tag_id,
        )

    async def get_food_places(self) -> dict[str, Any]:
        """
        Получает места для сценария 'Где поесть'.
        """
        return await self.get_places(
            city_slug=settings.default_city_slug,
            category_id=settings.food_category_id,
            tag_id=settings.food_tag_id,
        )

    async def get_walk_places(self) -> dict[str, Any]:
        """
        Получает места для сценария 'Куда погулять'.
        """
        return await self.get_places(
            city_slug=settings.default_city_slug,
            category_id=settings.walks_category_id,
            tag_id=settings.walks_tag_id,
        )

    async def get_dog_friendly_places(self) -> dict[str, Any]:
        """
        Получает места для сценария 'С собакой'.
        """
        return await self.get_places(
            city_slug=settings.default_city_slug,
            category_id=settings.dog_friendly_category_id,
            tag_id=settings.dog_friendly_tag_id,
        )
```

### `telegram_bot/services/messages.py`

```py
"""
Тексты сообщений для Telegram-бота City GO.
"""

WELCOME_TEXT = (
    "Привет! 👋\n\n"
    "<b>City GO</b> — городской помощник, который помогает быстро понять:\n"
    "• что рядом\n"
    "• что открыто сейчас\n"
    "• где выпить кофе\n"
    "• где поесть\n"
    "• куда пойти гулять\n\n"
    "Это пока MVP-версия бота."
)

HELP_TEXT = (
    "<b>Что умеет бот сейчас:</b>\n\n"
    "• показать главное меню\n"
    "• принять простой текстовый запрос\n"
    "• проверить backend через /health\n"
    "• сходить в nearby, open now, coffee, food, walks и dog-friendly через backend API\n"
    "• принять ручной адрес как fallback-сценарий\n\n"
    "Следующим шагом сюда подключим AI-lite поиск и геокодинг адреса."
)

ONLY_TEXT_MESSAGE = "Я пока работаю только с текстовыми сообщениями."

MAIN_MENU_REOPENED = "Главное меню открыто 👇"

MVP_FALLBACK_TEMPLATE = (
    "Принял запрос:\n"
    "<b>{user_text}</b>\n\n"
    "Пока это MVP-каркас. Следующий шаг — подключить backend и обработку интентов."
)

NEARBY_STUB_TEXT = (
    "Чтобы показать места рядом, сначала отправь геолокацию.\n\n"
    "Нажми кнопку <b>Отправить геолокацию</b> в меню ниже.\n\n"
    "Если не хочешь делиться геолокацией — это ок.\n"
    "Можно нажать <b>Ввести адрес</b> и отправить адрес вручную.\n\n"
    "Пока также доступны сценарии:\n"
    "• что открыто\n"
    "• где кофе\n"
    "• где поесть\n"
    "• куда погулять"
)

ADDRESS_HINT_TEXT = (
    "<b>Ручной ввод адреса</b>\n\n"
    "Отправь адрес одним сообщением.\n\n"
    "Формат:\n"
    "• город\n"
    "• улица\n"
    "• дом — опционально\n\n"
    "Пример:\n"
    "<b>Зеленоградск, Курортный проспект, 12</b>"
)

ADDRESS_SAVED_TEMPLATE = (
    "<b>Адрес сохранен</b>\n\n"
    "{raw_address}\n\n"
    "Пока это MVP-режим:\n"
    "• адрес принят\n"
    "• сохранился в памяти бота\n"
    "• позже сюда подключим геокодинг и nearby-поиск по адресу"
)

ADDRESS_EMPTY_TEXT = (
    "Я не получил адрес.\n\n"
    "Попробуй отправить его текстом, например:\n"
    "<b>Зеленоградск, Курортный проспект, 12</b>"
)

ADDRESS_CANCELLED_TEXT = (
    "Ввод адреса отменен.\n"
    "Можно продолжить через главное меню 👇"
)

OPEN_NOW_LOADING_TEXT = "Смотрю, что открыто сейчас..."
COFFEE_LOADING_TEXT = "Ищу, где выпить кофе..."
FOOD_LOADING_TEXT = "Ищу, где поесть..."
WALKS_LOADING_TEXT = "Ищу, куда можно пойти погулять..."
DOG_FRIENDLY_LOADING_TEXT = "Ищу места, куда можно с собакой..."

BACKEND_ERROR_TEMPLATE = (
    "<b>Backend сейчас недоступен</b>\n\n"
    "URL: <b>{base_url}</b>\n"
    "Ошибка: <b>{error}</b>"
)

OPEN_NOW_EMPTY_TEMPLATE = (
    "Сейчас не нашел открытых мест для города:\n"
    "<b>{city_slug}</b>"
)

NEARBY_EMPTY_TEMPLATE = (
    "Рядом ничего не найдено.\n\n"
    "Координаты:\n"
    "lat: <b>{lat}</b>\n"
    "lng: <b>{lng}</b>\n"
    "radius_km: <b>{radius_km}</b>"
)

COFFEE_EMPTY_TEMPLATE = (
    "Не нашел места с кофе по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

FOOD_EMPTY_TEMPLATE = (
    "Не нашел места, где поесть, по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

WALKS_EMPTY_TEMPLATE = (
    "Не нашел места для прогулки по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

DOG_FRIENDLY_EMPTY_TEMPLATE = (
    "Не нашел dog-friendly места по текущим фильтрам.\n\n"
    "Город: <b>{city_slug}</b>"
)

OPEN_NOW_RESULT_HEADER_TEMPLATE = (
    "<b>Открыто сейчас</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

NEARBY_RESULT_HEADER_TEMPLATE = (
    "<b>Места рядом</b>\n"
    "lat: <b>{lat}</b>\n"
    "lng: <b>{lng}</b>\n"
    "radius_km: <b>{radius_km}</b>\n\n"
)

COFFEE_RESULT_HEADER_TEMPLATE = (
    "<b>Где кофе</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

FOOD_RESULT_HEADER_TEMPLATE = (
    "<b>Где поесть</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

WALKS_RESULT_HEADER_TEMPLATE = (
    "<b>Куда погулять</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

DOG_FRIENDLY_RESULT_HEADER_TEMPLATE = (
    "<b>С собакой</b>\n"
    "Город: <b>{city_slug}</b>\n\n"
)

RESULT_ITEM_TEMPLATE = "• <b>{title}</b>"
```

### `telegram_bot/services/user_context.py`

```py
"""
Простое in-memory хранилище пользовательского контекста для Telegram-бота City GO.

Важно:
- это временное решение для MVP;
- данные живут только пока запущен процесс бота;
- позже можно заменить на Redis / БД.
"""

from typing import TypedDict


class UserLocation(TypedDict):
    """
    Координаты пользователя.
    """
    lat: float
    lng: float


# Временное хранилище по user_id.
USER_LOCATIONS: dict[int, UserLocation] = {}


def save_user_location(user_id: int, lat: float, lng: float) -> None:
    """
    Сохраняет последнюю геолокацию пользователя.
    """
    USER_LOCATIONS[user_id] = {
        "lat": lat,
        "lng": lng,
    }


def get_user_location(user_id: int) -> UserLocation | None:
    """
    Возвращает последнюю сохраненную геолокацию пользователя.
    """
    return USER_LOCATIONS.get(user_id)
```

### `telegram_bot/states/__init__.py`

```py
# Пакет состояний Telegram-бота City GO.
```

### `telegram_bot/states/address_state.py`

```py
"""
FSM-состояния для ручного ввода адреса в Telegram-боте City GO.
"""

from aiogram.fsm.state import State, StatesGroup


class AddressInputState(StatesGroup):
    """
    Состояния сценария ручного ввода адреса.
    """

    waiting_for_address = State()
```

### `telegram_bot_main.py`

```py
"""
Отдельная точка входа для Telegram-бота City GO.

Важно:
- этот файл НЕ заменяет текущий main.py FastAPI;
- backend и bot живут отдельно;
- позже бот можно будет подключить к существующим services / api.
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import settings
from telegram_bot.handlers.address import router as address_router
from telegram_bot.handlers.health import router as health_router
from telegram_bot.handlers.location import router as location_router
from telegram_bot.handlers.menu import router as menu_router
from telegram_bot.handlers.start import router as start_router


async def main() -> None:
    """
    Основной запуск Telegram-бота.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    if not settings.bot_token:
        raise ValueError(
            "BOT_TOKEN пустой. Заполни его в .env перед запуском Telegram-бота."
        )

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    dp = Dispatcher()

    # Порядок важен:
    # 1. health-команды
    # 2. геолокация
    # 3. ручной ввод адреса
    # 4. кнопки меню
    # 5. стартовые команды и fallback
    dp.include_router(health_router)
    dp.include_router(location_router)
    dp.include_router(address_router)
    dp.include_router(menu_router)
    dp.include_router(start_router)

    logging.info("Telegram bot is starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Telegram bot stopped manually.")
```

### `tests/test_pagination_service.py`

```py
from schemas.pagination import PaginationParams
from services.pagination_service import normalize_pagination_params


def test_normalize_pagination_params_keeps_values() -> None:
    params = PaginationParams(limit=10, offset=20)

    normalized = normalize_pagination_params(params)

    assert normalized.limit == 10
    assert normalized.offset == 20


def test_pagination_params_default_values() -> None:
    params = PaginationParams()

    normalized = normalize_pagination_params(params)

    assert normalized.limit == 20
    assert normalized.offset == 0
```

### `tests/test_place_count_service.py`

```py
from sqlalchemy import Column, Integer, MetaData, Table, create_engine
from sqlalchemy.orm import sessionmaker

from services.place_count_service import get_query_total


def test_get_query_total_returns_total_before_pagination() -> None:
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData()

    test_items = Table(
        "test_items",
        metadata,
        Column("id", Integer, primary_key=True),
    )

    metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    db.execute(
        test_items.insert(),
        [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}, {"id": 5}],
    )
    db.commit()

    query = db.query(test_items).limit(2).offset(2)

    total = get_query_total(query)

    assert total == 5
```

### `tests/test_place_filters_service.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_filters_service import apply_place_filters


def test_apply_place_filters_by_city_slug_returns_filtered_query() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    tag = Tag(id=1, code="pet_friendly", name="Pet Friendly")
    city_1 = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    city_2 = City(
        id=2,
        name="Kaliningrad",
        slug="kaliningrad",
    )
    db.add_all([category, tag, city_1, city_2])
    db.commit()

    place_1 = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    place_2 = Place(
        title="Walk Route",
        slug="walk-route",
        city_id=2,
        category_id=1,
        category="coffee",
        address="Addr 2",
        lat=54.71,
        lng=20.51,
    )
    db.add_all([place_1, place_2])
    db.commit()

    query = db.query(Place)
    filtered_query = apply_place_filters(
        query=query,
        city_id=None,
        city_slug="zelenogradsk",
        category_id=None,
        tag_id=None,
        db=db,
    )

    assert filtered_query is not None

    items = filtered_query.all()
    assert len(items) == 1
    assert items[0].slug == "coffee-point"


def test_apply_place_filters_returns_none_for_unknown_city_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    tag = Tag(id=1, code="pet_friendly", name="Pet Friendly")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, tag, city])
    db.commit()

    query = db.query(Place)
    filtered_query = apply_place_filters(
        query=query,
        city_id=None,
        city_slug="unknown-city",
        category_id=None,
        tag_id=None,
        db=db,
    )

    assert filtered_query is None
```

### `tests/test_place_list_params_schema.py`

```py
import pytest
from pydantic import ValidationError

from schemas.place_list_params import PlaceListParams


def test_place_list_params_defaults() -> None:
    params = PlaceListParams()

    assert params.limit == 20
    assert params.offset == 0
    assert params.q is None


def test_place_list_params_rejects_zero_limit() -> None:
    with pytest.raises(ValidationError):
        PlaceListParams(limit=0)


def test_place_list_params_rejects_negative_offset() -> None:
    with pytest.raises(ValidationError):
        PlaceListParams(offset=-1)
```

### `tests/test_place_list_params_service.py`

```py
from schemas.place_list_params import PlaceListParams
from services.place_list_params_service import normalize_place_list_params


def test_normalize_place_list_params_combines_search_and_pagination() -> None:
    params = PlaceListParams(
        city_slug="zelenogradsk",
        category_id=2,
        tag_id=3,
        q="  coffee  ",
        limit=10,
        offset=20,
    )

    normalized = normalize_place_list_params(params)

    assert normalized.city_slug == "zelenogradsk"
    assert normalized.category_id == 2
    assert normalized.tag_id == 3
    assert normalized.q == "coffee"
    assert normalized.limit == 10
    assert normalized.offset == 20


def test_normalize_place_list_params_converts_blank_q_to_none() -> None:
    params = PlaceListParams(q="   ")

    normalized = normalize_place_list_params(params)

    assert normalized.q is None
    assert normalized.limit == 20
    assert normalized.offset == 0
```

### `tests/test_place_query_params_service.py`

```py
from schemas.place_query_params import PlaceQueryParams
from services.place_query_params_service import normalize_place_query_params


def test_normalize_place_query_params_combines_list_and_sorting() -> None:
    params = PlaceQueryParams(
        city_slug="zelenogradsk",
        category_id=2,
        tag_id=3,
        q="  coffee  ",
        limit=10,
        offset=20,
        sort_by="created_at",
        sort_order="desc",
    )

    normalized = normalize_place_query_params(params)

    assert normalized.city_slug == "zelenogradsk"
    assert normalized.category_id == 2
    assert normalized.tag_id == 3
    assert normalized.q == "coffee"
    assert normalized.limit == 10
    assert normalized.offset == 20
    assert normalized.sort_by == "created_at"
    assert normalized.sort_order == "desc"


def test_normalize_place_query_params_uses_defaults() -> None:
    params = PlaceQueryParams()

    normalized = normalize_place_query_params(params)

    assert normalized.q is None
    assert normalized.limit == 20
    assert normalized.offset == 0
    assert normalized.sort_by == "title"
    assert normalized.sort_order == "asc"
```

### `tests/test_place_search_params_service.py`

```py
from schemas.place_search import PlaceSearchParams
from services.place_search_params_service import normalize_place_search_params


def test_normalize_place_search_params_trims_q() -> None:
    params = PlaceSearchParams(q="  coffee  ")

    normalized = normalize_place_search_params(params)

    assert normalized.q == "coffee"


def test_normalize_place_search_params_converts_empty_q_to_none() -> None:
    params = PlaceSearchParams(q="   ")

    normalized = normalize_place_search_params(params)

    assert normalized.q is None


def test_normalize_place_search_params_keeps_other_filters() -> None:
    params = PlaceSearchParams(
        city_id=1,
        city_slug="zelenogradsk",
        category_id=2,
        tag_id=3,
        q="walk",
    )

    normalized = normalize_place_search_params(params)

    assert normalized.city_id == 1
    assert normalized.city_slug == "zelenogradsk"
    assert normalized.category_id == 2
    assert normalized.tag_id == 3
    assert normalized.q == "walk"
```

### `tests/test_place_search_response_schema.py`

```py
import pytest
from pydantic import ValidationError

from schemas.place_search_response import PlaceSearchResponse


def test_place_search_response_accepts_valid_payload() -> None:
    response = PlaceSearchResponse(
        items=[],
        total=0,
        limit=20,
        offset=0,
    )

    assert response.items == []
    assert response.total == 0
    assert response.limit == 20
    assert response.offset == 0


def test_place_search_response_requires_total() -> None:
    with pytest.raises(ValidationError):
        PlaceSearchResponse(
            items=[],
            limit=20,
            offset=0,
        )
```

### `tests/test_place_search_response_service.py`

```py
from datetime import datetime

from services.place_search_response_service import build_place_search_response


def test_build_place_search_response_returns_expected_structure() -> None:
    items = [
        {
            "id": 1,
            "title": "Coffee Point",
            "slug": "coffee-point",
            "city_id": 1,
            "category_id": 2,
            "short_description": "Good coffee place",
            "category": "coffee",
            "address": "Kurortny Prospekt 12",
            "lat": 54.964,
            "lng": 20.475,
            "price_level": 1,
            "dog_friendly": False,
            "family_friendly": False,
            "indoor": False,
            "outdoor": False,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    ]

    response = build_place_search_response(
        items=items,
        total=1,
        limit=20,
        offset=0,
    )

    assert response.total == 1
    assert response.limit == 20
    assert response.offset == 0
    assert len(response.items) == 1
    assert response.items[0].id == 1
    assert response.items[0].title == "Coffee Point"
    assert response.items[0].slug == "coffee-point"
```

### `tests/test_place_search_response_total.py`

```py
from datetime import datetime

from services.place_search_response_service import build_place_search_response


def test_build_place_search_response_keeps_total_separate_from_items_count() -> None:
    items = [
        {
            "id": 1,
            "title": "Coffee Point",
            "slug": "coffee-point",
            "city_id": 1,
            "category_id": 2,
            "short_description": "Good coffee place",
            "category": "coffee",
            "address": "Kurortny Prospekt 12",
            "lat": 54.964,
            "lng": 20.475,
            "price_level": 1,
            "dog_friendly": False,
            "family_friendly": False,
            "indoor": False,
            "outdoor": False,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    ]

    response = build_place_search_response(
        items=items,
        total=25,
        limit=10,
        offset=10,
    )

    assert response.total == 25
    assert response.limit == 10
    assert response.offset == 10
    assert len(response.items) == 1
    assert response.items[0].id == 1
    assert response.items[0].title == "Coffee Point"
```

### `tests/test_place_search_router.py`

```py
from datetime import datetime

from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_search_places_returns_structured_response(monkeypatch) -> None:
    expected_items = [
        {
            "id": 1,
            "title": "Coffee Point",
            "slug": "coffee-point",
            "city_id": 1,
            "category_id": 2,
            "short_description": "Good coffee place",
            "category": "coffee",
            "address": "Kurortny Prospekt 12",
            "lat": 54.964,
            "lng": 20.475,
            "price_level": 1,
            "dog_friendly": False,
            "family_friendly": False,
            "indoor": False,
            "outdoor": False,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
    ]

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by="title",
        sort_order="asc",
    ):
        assert city_slug == "zelenogradsk"
        assert q == "coffee"
        assert limit == 20
        assert offset == 0
        return expected_items

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        assert city_slug == "zelenogradsk"
        assert q == "coffee"
        return 1

    def fake_get_db():
        yield object()

    monkeypatch.setattr("routers.place_search.get_places", fake_get_places)
    monkeypatch.setattr("routers.place_search.get_places_total", fake_get_places_total)
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "city_slug": "zelenogradsk",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 20
    assert data["offset"] == 0
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "coffee-point"
    assert data["items"][0]["title"] == "Coffee Point"

    app.dependency_overrides.clear()
```

### `tests/test_place_search_router_empty_result.py`

```py
from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_search_places_returns_empty_structured_response() -> None:
    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by='title',
        sort_order='asc',
    ):
        return []

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 0

    def fake_get_db():
        yield object()

    from routers import place_search

    original_get_places = place_search.get_places
    original_get_places_total = place_search.get_places_total
    place_search.get_places = fake_get_places
    place_search.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/search/",
        params={
            "q": "unknown",
            "city_slug": "zelenogradsk",
        },
    )

    place_search.get_places = original_get_places
    place_search.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }
```

### `tests/test_place_search_router_filters.py`

```py
from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_search_places_passes_all_filters() -> None:
    captured: dict[str, object] = {}

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by="title",
        sort_order="asc",
    ):
        captured["city_id"] = city_id
        captured["city_slug"] = city_slug
        captured["category_id"] = category_id
        captured["tag_id"] = tag_id
        captured["q"] = q
        captured["limit"] = limit
        captured["offset"] = offset
        captured["sort_by"] = sort_by
        captured["sort_order"] = sort_order
        return []

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 0

    def fake_get_db():
        yield object()

    from routers import place_search

    original_get_places = place_search.get_places
    original_get_places_total = place_search.get_places_total

    place_search.get_places = fake_get_places
    place_search.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "city_id": 1,
            "city_slug": "zelenogradsk",
            "category_id": 2,
            "tag_id": 3,
            "limit": 5,
            "offset": 10,
        },
    )

    place_search.get_places = original_get_places
    place_search.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["city_id"] == 1
    assert captured["city_slug"] == "zelenogradsk"
    assert captured["category_id"] == 2
    assert captured["tag_id"] == 3
    assert captured["q"] == "coffee"
    assert captured["limit"] == 5
    assert captured["offset"] == 10
    assert captured["sort_by"] == "title"
    assert captured["sort_order"] == "asc"
```

### `tests/test_place_search_router_pagination.py`

```py
from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_search_places_passes_limit_and_offset_and_returns_structured_response() -> None:
    captured: dict[str, int] = {}

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by='title',
        sort_order='asc',
    ):
        captured["limit"] = limit
        captured["offset"] = offset
        return []

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 0

    def fake_get_db():
        yield object()

    from routers import place_search

    original_get_places = place_search.get_places
    original_get_places_total = place_search.get_places_total
    place_search.get_places = fake_get_places
    place_search.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "limit": 5,
            "offset": 10,
        },
    )

    place_search.get_places = original_get_places
    place_search.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["limit"] == 5
    assert captured["offset"] == 10
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 5,
        "offset": 10,
    }
```

### `tests/test_place_search_router_validation.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_search_places_requires_q() -> None:
    client = TestClient(app)

    response = client.get("/places/search/")

    assert response.status_code == 422
```

### `tests/test_place_search_service.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_places


def test_get_places_filters_by_q_on_title_and_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    place_1 = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    place_2 = Place(
        title="Walk Route",
        slug="walk-route",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 2",
        lat=54.96,
        lng=20.49,
    )
    db.add_all([place_1, place_2])
    db.commit()

    items = get_places(db=db, q="coffee")

    assert len(items) == 1
    assert items[0].slug == "coffee-point"
```

### `tests/test_place_search_service_city_slug.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_places


def test_get_places_returns_empty_list_for_unknown_city_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    place = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    db.add(place)
    db.commit()

    items = get_places(db=db, city_slug="unknown-city")

    assert items == []
```

### `tests/test_place_seed_bulk_validation_response_schema.py`

```py
from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)
from schemas.place_seed_validation_response import PlaceSeedValidationResponse


def test_place_seed_bulk_validation_response_defaults() -> None:
    response = PlaceSeedBulkValidationResponse(
        total=0,
        valid_count=0,
        invalid_count=0,
    )

    assert response.total == 0
    assert response.valid_count == 0
    assert response.invalid_count == 0
    assert response.items == []


def test_place_seed_bulk_validation_response_accepts_items() -> None:
    item = PlaceSeedValidationResponse(
        is_valid=True,
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(),
        errors=[],
    )

    response = PlaceSeedBulkValidationResponse(
        total=1,
        valid_count=1,
        invalid_count=0,
        items=[item],
    )

    assert response.total == 1
    assert response.valid_count == 1
    assert response.invalid_count == 0
    assert len(response.items) == 1
    assert response.items[0].title == "Coffee Point"
```

### `tests/test_place_seed_bulk_validation_response_totals.py`

```py
from schemas.place_seed_bulk_validation_response import (
    PlaceSeedBulkValidationResponse,
)
from schemas.place_seed_validation_response import PlaceSeedValidationResponse
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


def test_place_seed_bulk_validation_response_keeps_counts_independent_from_items_length() -> None:
    item = PlaceSeedValidationResponse(
        is_valid=True,
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(),
        errors=[],
    )

    response = PlaceSeedBulkValidationResponse(
        total=10,
        valid_count=7,
        invalid_count=3,
        items=[item],
    )

    assert response.total == 10
    assert response.valid_count == 7
    assert response.invalid_count == 3
    assert len(response.items) == 1
```

### `tests/test_place_seed_bulk_validation_service.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_bulk_validation_service import validate_place_seed_items


def test_validate_place_seed_items_returns_bulk_stats() -> None:
    items = [
        PlaceSeedItem(
            title="Coffee Point",
            slug="coffee-point",
            city_slug="zelenogradsk",
            category="coffee",
            address="Kurortny Prospekt 12",
            short_description="Good coffee place",
            taxonomy=PlaceTaxonomyPayload(
                category="coffee",
                tags=["pet_friendly", "quiet"],
                scenario_tags=["coffee_now", "with_dog"],
                vibe_tags=["cozy"],
                restriction_tags=[],
            ),
            source="manual",
            source_url=None,
            lat=54.964,
            lng=20.475,
            is_active=True,
        ),
        PlaceSeedItem(
            title=" ",
            slug="bad-place",
            city_slug="zelenogradsk",
            category="food",
            address=None,
            short_description=None,
            taxonomy=PlaceTaxonomyPayload(
                category="bad_category",
                tags=["bad_tag"],
                scenario_tags=[],
                vibe_tags=[],
                restriction_tags=[],
            ),
            source=None,
            source_url=None,
            lat=None,
            lng=None,
            is_active=True,
        ),
    ]

    result = validate_place_seed_items(items)

    assert result.total == 2
    assert result.valid_count == 1
    assert result.invalid_count == 1
    assert len(result.items) == 2
    assert result.items[0].is_valid is True
    assert result.items[1].is_valid is False
```

### `tests/test_place_seed_dry_run_request_schema.py`

```py
from schemas.place_seed_dry_run_request import PlaceSeedDryRunRequest


def test_place_seed_dry_run_request_defaults() -> None:
    request = PlaceSeedDryRunRequest()

    assert request.items == []


def test_place_seed_dry_run_request_accepts_items() -> None:
    request = PlaceSeedDryRunRequest(
        items=[
            {
                "title": "Coffee Point",
                "slug": "coffee-point",
                "city_slug": "zelenogradsk",
                "category": "coffee",
                "taxonomy": {
                    "category": "coffee",
                    "tags": [],
                    "scenario_tags": [],
                    "vibe_tags": [],
                    "restriction_tags": [],
                },
            }
        ]
    )

    assert len(request.items) == 1
    assert request.items[0].title == "Coffee Point"
    assert request.items[0].slug == "coffee-point"
```

### `tests/test_place_seed_dry_run_router.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_dry_run_place_seed_payload_returns_summary() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
        json={
            "items": [
                {
                    "title": "Coffee Point",
                    "slug": "coffee-point",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": "Kurortny Prospekt 12",
                    "short_description": "Good coffee place",
                    "taxonomy": {
                        "category": "coffee",
                        "tags": ["pet_friendly", "quiet"],
                        "scenario_tags": ["coffee_now", "with_dog"],
                        "vibe_tags": ["cozy"],
                        "restriction_tags": [],
                    },
                    "source": "manual",
                    "source_url": None,
                    "lat": 54.964,
                    "lng": 20.475,
                    "is_active": True,
                },
                {
                    "title": " ",
                    "slug": "bad-place",
                    "city_slug": "zelenogradsk",
                    "category": "food",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["created"] == 0
    assert response.json()["updated"] == 0
    assert response.json()["skipped"] == 1
    assert response.json()["invalid"] == 1
    assert len(response.json()["errors"]) == 1
```

### `tests/test_place_seed_dry_run_router_all_invalid.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_dry_run_place_seed_payload_returns_invalid_for_all_invalid_items() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
        json={
            "items": [
                {
                    "title": " ",
                    "slug": "bad-place-1",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                },
                {
                    "title": " ",
                    "slug": "bad-place-2",
                    "city_slug": "zelenogradsk",
                    "category": "walk",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["created"] == 0
    assert response.json()["updated"] == 0
    assert response.json()["skipped"] == 0
    assert response.json()["invalid"] == 2
    assert len(response.json()["errors"]) == 2
```

### `tests/test_place_seed_dry_run_router_all_valid.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_dry_run_place_seed_payload_returns_skipped_for_all_valid_items() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
        json={
            "items": [
                {
                    "title": "Coffee Point",
                    "slug": "coffee-point",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": "Kurortny Prospekt 12",
                    "short_description": "Good coffee place",
                    "taxonomy": {
                        "category": "coffee",
                        "tags": ["pet_friendly", "quiet"],
                        "scenario_tags": ["coffee_now", "with_dog"],
                        "vibe_tags": ["cozy"],
                        "restriction_tags": [],
                    },
                    "source": "manual",
                    "source_url": None,
                    "lat": 54.964,
                    "lng": 20.475,
                    "is_active": True,
                },
                {
                    "title": "Walk Route",
                    "slug": "walk-route",
                    "city_slug": "zelenogradsk",
                    "category": "walk",
                    "address": "Promenade",
                    "short_description": "Nice walk by the sea",
                    "taxonomy": {
                        "category": "walk",
                        "tags": ["outdoor", "photo_spot"],
                        "scenario_tags": ["walk_now", "weekend_plan"],
                        "vibe_tags": ["calm"],
                        "restriction_tags": [],
                    },
                    "source": "manual",
                    "source_url": None,
                    "lat": 54.965,
                    "lng": 20.476,
                    "is_active": True,
                },
            ]
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 2,
        "created": 0,
        "updated": 0,
        "skipped": 2,
        "invalid": 0,
        "errors": [],
    }
```

### `tests/test_place_seed_dry_run_router_empty_list.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_dry_run_place_seed_payload_returns_empty_summary_for_empty_list() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
        json={"items": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "errors": [],
    }
```

### `tests/test_place_seed_dry_run_service.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dry_run_service import run_place_seed_dry_run


def test_run_place_seed_dry_run_counts_valid_as_skipped_and_invalid_as_invalid() -> None:
    items = [
        PlaceSeedItem(
            title="Coffee Point",
            slug="coffee-point",
            city_slug="zelenogradsk",
            category="coffee",
            address="Kurortny Prospekt 12",
            short_description="Good coffee place",
            taxonomy=PlaceTaxonomyPayload(
                category="coffee",
                tags=["pet_friendly", "quiet"],
                scenario_tags=["coffee_now", "with_dog"],
                vibe_tags=["cozy"],
                restriction_tags=[],
            ),
            source="manual",
            source_url=None,
            lat=54.964,
            lng=20.475,
            is_active=True,
        ),
        PlaceSeedItem(
            title=" ",
            slug="bad-place",
            city_slug="zelenogradsk",
            category="food",
            address=None,
            short_description=None,
            taxonomy=PlaceTaxonomyPayload(
                category="bad_category",
                tags=["bad_tag"],
                scenario_tags=[],
                vibe_tags=[],
                restriction_tags=[],
            ),
            source=None,
            source_url=None,
            lat=None,
            lng=None,
            is_active=True,
        ),
    ]

    result = run_place_seed_dry_run(items)

    assert result.total == 2
    assert result.created == 0
    assert result.updated == 0
    assert result.skipped == 1
    assert result.invalid == 1
    assert len(result.errors) == 1
    assert "bad-place" in result.errors[0]


def test_run_place_seed_dry_run_returns_empty_summary_for_empty_list() -> None:
    result = run_place_seed_dry_run([])

    assert result.total == 0
    assert result.created == 0
    assert result.updated == 0
    assert result.skipped == 0
    assert result.invalid == 0
    assert result.errors == []
```

### `tests/test_place_seed_dry_run_service_empty_slug.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dry_run_service import run_place_seed_dry_run


def test_run_place_seed_dry_run_uses_placeholder_for_empty_slug_in_errors() -> None:
    items = [
        PlaceSeedItem(
            title=" ",
            slug=" ",
            city_slug="zelenogradsk",
            category="coffee",
            address=None,
            short_description=None,
            taxonomy=PlaceTaxonomyPayload(
                category="bad_category",
                tags=["bad_tag"],
                scenario_tags=[],
                vibe_tags=[],
                restriction_tags=[],
            ),
            source=None,
            source_url=None,
            lat=None,
            lng=None,
            is_active=True,
        )
    ]

    result = run_place_seed_dry_run(items)

    assert result.total == 1
    assert result.invalid == 1
    assert len(result.errors) == 1
    assert "<empty-slug>" in result.errors[0]
```

### `tests/test_place_seed_dry_run_service_error_count.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_dry_run_service import run_place_seed_dry_run


def test_run_place_seed_dry_run_returns_one_error_per_invalid_item() -> None:
    items = [
        PlaceSeedItem(
            title=" ",
            slug="bad-place-1",
            city_slug="zelenogradsk",
            category="coffee",
            address=None,
            short_description=None,
            taxonomy=PlaceTaxonomyPayload(
                category="bad_category",
                tags=["bad_tag"],
                scenario_tags=[],
                vibe_tags=[],
                restriction_tags=[],
            ),
            source=None,
            source_url=None,
            lat=None,
            lng=None,
            is_active=True,
        ),
        PlaceSeedItem(
            title=" ",
            slug="bad-place-2",
            city_slug="zelenogradsk",
            category="food",
            address=None,
            short_description=None,
            taxonomy=PlaceTaxonomyPayload(
                category="bad_category",
                tags=["bad_tag"],
                scenario_tags=[],
                vibe_tags=[],
                restriction_tags=[],
            ),
            source=None,
            source_url=None,
            lat=None,
            lng=None,
            is_active=True,
        ),
    ]

    result = run_place_seed_dry_run(items)

    assert result.total == 2
    assert result.invalid == 2
    assert len(result.errors) == 2
    assert "bad-place-1" in result.errors[0]
    assert "bad-place-2" in result.errors[1]
```

### `tests/test_place_seed_import_summary_schema.py`

```py
from schemas.place_seed_import_summary import PlaceSeedImportSummary


def test_place_seed_import_summary_defaults() -> None:
    summary = PlaceSeedImportSummary()

    assert summary.total == 0
    assert summary.created == 0
    assert summary.updated == 0
    assert summary.skipped == 0
    assert summary.invalid == 0
    assert summary.errors == []


def test_place_seed_import_summary_accepts_values() -> None:
    summary = PlaceSeedImportSummary(
        total=10,
        created=4,
        updated=3,
        skipped=2,
        invalid=1,
        errors=["row 7 invalid"],
    )

    assert summary.total == 10
    assert summary.created == 4
    assert summary.updated == 3
    assert summary.skipped == 2
    assert summary.invalid == 1
    assert summary.errors == ["row 7 invalid"]
```

### `tests/test_place_seed_import_summary_service.py`

```py
from services.place_seed_import_summary_service import (
    build_place_seed_import_summary,
)


def test_build_place_seed_import_summary_defaults_errors_to_empty_list() -> None:
    summary = build_place_seed_import_summary(total=5)

    assert summary.total == 5
    assert summary.created == 0
    assert summary.updated == 0
    assert summary.skipped == 0
    assert summary.invalid == 0
    assert summary.errors == []


def test_build_place_seed_import_summary_accepts_all_values() -> None:
    summary = build_place_seed_import_summary(
        total=10,
        created=4,
        updated=3,
        skipped=2,
        invalid=1,
        errors=["row 7 invalid"],
    )

    assert summary.total == 10
    assert summary.created == 4
    assert summary.updated == 3
    assert summary.skipped == 2
    assert summary.invalid == 1
    assert summary.errors == ["row 7 invalid"]
```

### `tests/test_place_seed_item_schema.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload


def test_place_seed_item_accepts_minimal_valid_payload() -> None:
    item = PlaceSeedItem(
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        category="coffee",
        taxonomy=PlaceTaxonomyPayload(category="coffee"),
    )

    assert item.title == "Coffee Point"
    assert item.slug == "coffee-point"
    assert item.city_slug == "zelenogradsk"
    assert item.category == "coffee"
    assert item.is_active is True
    assert item.address is None
    assert item.short_description is None
    assert item.source is None
    assert item.source_url is None
    assert item.lat is None
    assert item.lng is None


def test_place_seed_item_accepts_full_payload() -> None:
    item = PlaceSeedItem(
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        category="coffee",
        address="Kurortny Prospekt 12",
        short_description="Good coffee place",
        taxonomy=PlaceTaxonomyPayload(
            category="coffee",
            tags=["pet_friendly", "quiet"],
            scenario_tags=["coffee_now", "with_dog"],
            vibe_tags=["cozy"],
            restriction_tags=["cash_only"],
        ),
        source="manual",
        source_url="https://example.com",
        lat=54.964,
        lng=20.475,
        is_active=False,
    )

    assert item.address == "Kurortny Prospekt 12"
    assert item.short_description == "Good coffee place"
    assert item.taxonomy.category == "coffee"
    assert item.source == "manual"
    assert item.source_url == "https://example.com"
    assert item.lat == 54.964
    assert item.lng == 20.475
    assert item.is_active is False
```

### `tests/test_place_seed_validation_request_schema.py`

```py
from schemas.place_seed_validation_request import PlaceSeedValidationRequest


def test_place_seed_validation_request_defaults() -> None:
    request = PlaceSeedValidationRequest()

    assert request.items == []


def test_place_seed_validation_request_accepts_items() -> None:
    request = PlaceSeedValidationRequest(
        items=[
            {
                "title": "Coffee Point",
                "slug": "coffee-point",
                "city_slug": "zelenogradsk",
                "category": "coffee",
                "taxonomy": {
                    "category": "coffee",
                    "tags": [],
                    "scenario_tags": [],
                    "vibe_tags": [],
                    "restriction_tags": [],
                },
            }
        ]
    )

    assert len(request.items) == 1
    assert request.items[0].title == "Coffee Point"
    assert request.items[0].slug == "coffee-point"
```

### `tests/test_place_seed_validation_response_schema.py`

```py
from schemas.place_seed_validation_response import PlaceSeedValidationResponse
from schemas.place_taxonomy_diagnostics_response import (
    PlaceTaxonomyDiagnosticsResponse,
)


def test_place_seed_validation_response_accepts_valid_payload() -> None:
    response = PlaceSeedValidationResponse(
        is_valid=True,
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(),
        errors=[],
    )

    assert response.is_valid is True
    assert response.title == "Coffee Point"
    assert response.slug == "coffee-point"
    assert response.city_slug == "zelenogradsk"
    assert response.errors == []


def test_place_seed_validation_response_accepts_errors() -> None:
    response = PlaceSeedValidationResponse(
        is_valid=False,
        title=" ",
        slug=" ",
        city_slug=" ",
        taxonomy_diagnostics=PlaceTaxonomyDiagnosticsResponse(
            category="bad_category",
            tags=["bad_tag"],
            scenario_tags=[],
            vibe_tags=[],
            restriction_tags=[],
        ),
        errors=["title is empty", "slug is empty", "city_slug is empty"],
    )

    assert response.is_valid is False
    assert response.taxonomy_diagnostics.category == "bad_category"
    assert response.taxonomy_diagnostics.tags == ["bad_tag"]
    assert "title is empty" in response.errors
```

### `tests/test_place_seed_validation_router.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_bulk_result() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        json={
            "items": [
                {
                    "title": "Coffee Point",
                    "slug": "coffee-point",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": "Kurortny Prospekt 12",
                    "short_description": "Good coffee place",
                    "taxonomy": {
                        "category": "coffee",
                        "tags": ["pet_friendly", "quiet"],
                        "scenario_tags": ["coffee_now", "with_dog"],
                        "vibe_tags": ["cozy"],
                        "restriction_tags": [],
                    },
                    "source": "manual",
                    "source_url": None,
                    "lat": 54.964,
                    "lng": 20.475,
                    "is_active": True,
                },
                {
                    "title": " ",
                    "slug": "bad-place",
                    "city_slug": "zelenogradsk",
                    "category": "food",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                },
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 2
    assert data["valid_count"] == 1
    assert data["invalid_count"] == 1
    assert len(data["items"]) == 2
    assert data["items"][0]["is_valid"] is True
    assert data["items"][1]["is_valid"] is False
```

### `tests/test_place_seed_validation_router_empty_list.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_empty_bulk_result_for_empty_list() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        json={"items": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "items": [],
    }
```

### `tests/test_place_seed_validation_router_invalid_payload.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_invalid_result_for_empty_required_fields() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        json={
            "items": [
                {
                    "title": " ",
                    "slug": " ",
                    "city_slug": " ",
                    "category": "coffee",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "coffee",
                        "tags": [],
                        "scenario_tags": [],
                        "vibe_tags": [],
                        "restriction_tags": [],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["valid_count"] == 0
    assert data["invalid_count"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["is_valid"] is False
    assert "title is empty" in data["items"][0]["errors"]
    assert "slug is empty" in data["items"][0]["errors"]
    assert "city_slug is empty" in data["items"][0]["errors"]
```

### `tests/test_place_seed_validation_router_taxonomy_errors.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_taxonomy_errors() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        json={
            "items": [
                {
                    "title": "Coffee Point",
                    "slug": "coffee-point",
                    "city_slug": "zelenogradsk",
                    "category": "coffee",
                    "address": None,
                    "short_description": None,
                    "taxonomy": {
                        "category": "bad_category",
                        "tags": ["bad_tag"],
                        "scenario_tags": ["bad_scenario"],
                        "vibe_tags": ["bad_vibe"],
                        "restriction_tags": ["bad_restriction"],
                    },
                    "source": None,
                    "source_url": None,
                    "lat": None,
                    "lng": None,
                    "is_active": True,
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["valid_count"] == 0
    assert data["invalid_count"] == 1
    assert len(data["items"]) == 1

    item = data["items"][0]
    assert item["is_valid"] is False
    assert item["taxonomy_diagnostics"] == {
        "category": "bad_category",
        "tags": ["bad_tag"],
        "scenario_tags": ["bad_scenario"],
        "vibe_tags": ["bad_vibe"],
        "restriction_tags": ["bad_restriction"],
    }
```

### `tests/test_place_seed_validation_service.py`

```py
from schemas.place_seed_item import PlaceSeedItem
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_seed_validation_service import validate_place_seed_item


def test_validate_place_seed_item_returns_valid_for_clean_seed() -> None:
    item = PlaceSeedItem(
        title="Coffee Point",
        slug="coffee-point",
        city_slug="zelenogradsk",
        category="coffee",
        address="Kurortny Prospekt 12",
        short_description="Good coffee place",
        taxonomy=PlaceTaxonomyPayload(
            category="coffee",
            tags=["pet_friendly", "quiet"],
            scenario_tags=["coffee_now", "with_dog"],
            vibe_tags=["cozy"],
            restriction_tags=[],
        ),
        source="manual",
        source_url=None,
        lat=54.964,
        lng=20.475,
        is_active=True,
    )

    result = validate_place_seed_item(item)

    assert result.is_valid is True
    assert result.errors == []
    assert result.taxonomy_diagnostics.category is None
    assert result.taxonomy_diagnostics.tags == []
    assert result.taxonomy_diagnostics.scenario_tags == []
    assert result.taxonomy_diagnostics.vibe_tags == []
    assert result.taxonomy_diagnostics.restriction_tags == []


def test_validate_place_seed_item_returns_errors_for_empty_fields_and_bad_taxonomy() -> None:
    item = PlaceSeedItem(
        title=" ",
        slug=" ",
        city_slug=" ",
        category="coffee",
        address=None,
        short_description=None,
        taxonomy=PlaceTaxonomyPayload(
            category="bad_category",
            tags=["bad_tag"],
            scenario_tags=["bad_scenario"],
            vibe_tags=["bad_vibe"],
            restriction_tags=["bad_restriction"],
        ),
        source=None,
        source_url=None,
        lat=None,
        lng=None,
        is_active=True,
    )

    result = validate_place_seed_item(item)

    assert result.is_valid is False
    assert "title is empty" in result.errors
    assert "slug is empty" in result.errors
    assert "city_slug is empty" in result.errors
    assert result.taxonomy_diagnostics.category == "bad_category"
    assert result.taxonomy_diagnostics.tags == ["bad_tag"]
    assert result.taxonomy_diagnostics.scenario_tags == ["bad_scenario"]
    assert result.taxonomy_diagnostics.vibe_tags == ["bad_vibe"]
    assert result.taxonomy_diagnostics.restriction_tags == ["bad_restriction"]
```

### `tests/test_place_service_pagination.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_places


def test_get_places_applies_limit_and_offset() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    places = [
        Place(
            title=f"Place {index}",
            slug=f"place-{index}",
            city_id=1,
            category_id=1,
            category="coffee",
            address=f"Addr {index}",
            lat=54.95 + index / 1000,
            lng=20.48 + index / 1000,
        )
        for index in range(1, 6)
    ]
    db.add_all(places)
    db.commit()

    items = get_places(db=db, limit=2, offset=2)

    assert len(items) == 2
    assert items[0].slug == "place-3"
    assert items[1].slug == "place-4"
```

### `tests/test_place_service_total.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_places_total


def test_get_places_total_returns_total_with_filters_and_search() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    place_1 = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    place_2 = Place(
        title="Coffee House",
        slug="coffee-house",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 2",
        lat=54.96,
        lng=20.49,
    )
    place_3 = Place(
        title="Walk Route",
        slug="walk-route",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 3",
        lat=54.97,
        lng=20.50,
    )
    db.add_all([place_1, place_2, place_3])
    db.commit()

    total = get_places_total(
        db=db,
        city_slug="zelenogradsk",
        q="coffee",
    )

    assert total == 2


def test_get_places_total_returns_zero_for_unknown_city_slug() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    place = Place(
        title="Coffee Point",
        slug="coffee-point",
        city_id=1,
        category_id=1,
        category="coffee",
        address="Addr 1",
        lat=54.95,
        lng=20.48,
    )
    db.add(place)
    db.commit()

    total = get_places_total(
        db=db,
        city_slug="unknown-city",
    )

    assert total == 0
```

### `tests/test_place_service_total_independent_from_pagination.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.place_service import get_places_total


def test_get_places_total_is_not_affected_by_limit_and_offset() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    places = [
        Place(
            title=f"Coffee {index}",
            slug=f"coffee-{index}",
            city_id=1,
            category_id=1,
            category="coffee",
            address=f"Addr {index}",
            lat=54.95 + index / 1000,
            lng=20.48 + index / 1000,
        )
        for index in range(1, 6)
    ]
    db.add_all(places)
    db.commit()

    total = get_places_total(
        db=db,
        city_slug="zelenogradsk",
        q="coffee",
    )

    assert total == 5
```

### `tests/test_place_sorting_service.py`

```py
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.base import Base
from models.category import Category
from models.city import City
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from schemas.sorting import SortingParams
from services.place_sorting_service import apply_place_sorting


def test_apply_place_sorting_by_title_asc() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    db.add_all(
        [
            Place(
                title="Bravo",
                slug="bravo",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 1",
                lat=54.95,
                lng=20.48,
            ),
            Place(
                title="Alpha",
                slug="alpha",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 2",
                lat=54.96,
                lng=20.49,
            ),
        ]
    )
    db.commit()

    query = db.query(Place)
    sorted_query = apply_place_sorting(
        query,
        SortingParams(sort_by="title", sort_order="asc"),
    )
    items = sorted_query.all()

    assert len(items) == 2
    assert items[0].title == "Alpha"
    assert items[1].title == "Bravo"


def test_apply_place_sorting_by_title_desc() -> None:
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(bind=engine)

    Base.metadata.create_all(bind=engine)

    db: Session = TestingSessionLocal()

    category = Category(id=1, code="coffee", name="Coffee")
    city = City(
        id=1,
        name="Zelenogradsk",
        slug="zelenogradsk",
    )
    db.add_all([category, city])
    db.commit()

    db.add_all(
        [
            Place(
                title="Bravo",
                slug="bravo",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 1",
                lat=54.95,
                lng=20.48,
            ),
            Place(
                title="Alpha",
                slug="alpha",
                city_id=1,
                category_id=1,
                category="coffee",
                address="Addr 2",
                lat=54.96,
                lng=20.49,
            ),
        ]
    )
    db.commit()

    query = db.query(Place)
    sorted_query = apply_place_sorting(
        query,
        SortingParams(sort_by="title", sort_order="desc"),
    )
    items = sorted_query.all()

    assert len(items) == 2
    assert items[0].title == "Bravo"
    assert items[1].title == "Alpha"
```

### `tests/test_place_taxonomy_diagnostics_router.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_validate_place_taxonomy_payload_returns_invalid_values() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-taxonomy/diagnostics/",
        json={
            "category": "invalid_category",
            "tags": ["pet_friendly", "bad_tag"],
            "scenario_tags": ["with_dog", "bad_scenario"],
            "vibe_tags": ["cozy", "bad_vibe"],
            "restriction_tags": ["cash_only", "bad_restriction"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "category": "invalid_category",
        "tags": ["bad_tag"],
        "scenario_tags": ["bad_scenario"],
        "vibe_tags": ["bad_vibe"],
        "restriction_tags": ["bad_restriction"],
    }


def test_validate_place_taxonomy_payload_returns_empty_invalid_values_for_valid_payload() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-taxonomy/diagnostics/",
        json={
            "category": "coffee",
            "tags": ["pet_friendly", "quiet"],
            "scenario_tags": ["coffee_now", "with_dog"],
            "vibe_tags": ["cozy", "local_favorite"],
            "restriction_tags": ["cash_only"],
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "category": None,
        "tags": [],
        "scenario_tags": [],
        "vibe_tags": [],
        "restriction_tags": [],
    }
```

### `tests/test_place_taxonomy_diagnostics_service.py`

```py
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_diagnostics_service import (
    get_invalid_place_taxonomy_values,
)


def test_get_invalid_place_taxonomy_values_returns_empty_invalid_lists_for_valid_payload() -> None:
    payload = PlaceTaxonomyPayload(
        category="coffee",
        tags=["pet_friendly", "quiet"],
        scenario_tags=["coffee_now", "with_dog"],
        vibe_tags=["cozy", "local_favorite"],
        restriction_tags=["cash_only"],
    )

    result = get_invalid_place_taxonomy_values(payload)

    assert result.category is None
    assert result.tags == []
    assert result.scenario_tags == []
    assert result.vibe_tags == []
    assert result.restriction_tags == []


def test_get_invalid_place_taxonomy_values_returns_only_invalid_values() -> None:
    payload = PlaceTaxonomyPayload(
        category="invalid_category",
        tags=["pet_friendly", "bad_tag"],
        scenario_tags=["with_dog", "bad_scenario"],
        vibe_tags=["cozy", "bad_vibe"],
        restriction_tags=["cash_only", "bad_restriction"],
    )

    result = get_invalid_place_taxonomy_values(payload)

    assert result.category == "invalid_category"
    assert result.tags == ["bad_tag"]
    assert result.scenario_tags == ["bad_scenario"]
    assert result.vibe_tags == ["bad_vibe"]
    assert result.restriction_tags == ["bad_restriction"]
```

### `tests/test_place_taxonomy_payload_schema.py`

```py
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload


def test_place_taxonomy_payload_defaults() -> None:
    payload = PlaceTaxonomyPayload(category="coffee")

    assert payload.category == "coffee"
    assert payload.tags == []
    assert payload.scenario_tags == []
    assert payload.vibe_tags == []
    assert payload.restriction_tags == []


def test_place_taxonomy_payload_accepts_full_payload() -> None:
    payload = PlaceTaxonomyPayload(
        category="food",
        tags=["local_food", "quiet"],
        scenario_tags=["food_now", "evening_plan"],
        vibe_tags=["authentic", "cozy"],
        restriction_tags=["reservation_needed"],
    )

    assert payload.category == "food"
    assert payload.tags == ["local_food", "quiet"]
    assert payload.scenario_tags == ["food_now", "evening_plan"]
    assert payload.vibe_tags == ["authentic", "cozy"]
    assert payload.restriction_tags == ["reservation_needed"]
```

### `tests/test_place_taxonomy_payload_service.py`

```py
from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
from services.place_taxonomy_payload_service import normalize_place_taxonomy_payload


def test_normalize_place_taxonomy_payload_keeps_valid_values() -> None:
    payload = PlaceTaxonomyPayload(
        category="coffee",
        tags=["pet_friendly", "quiet"],
        scenario_tags=["coffee_now", "with_dog"],
        vibe_tags=["cozy", "local_favorite"],
        restriction_tags=["cash_only"],
    )

    normalized = normalize_place_taxonomy_payload(payload)

    assert normalized.category == "coffee"
    assert normalized.tags == ["pet_friendly", "quiet"]
    assert normalized.scenario_tags == ["coffee_now", "with_dog"]
    assert normalized.vibe_tags == ["cozy", "local_favorite"]
    assert normalized.restriction_tags == ["cash_only"]


def test_normalize_place_taxonomy_payload_filters_invalid_and_duplicates() -> None:
    payload = PlaceTaxonomyPayload(
        category="invalid_category",
        tags=["pet_friendly", "pet_friendly", "bad_tag"],
        scenario_tags=["with_dog", "bad_scenario"],
        vibe_tags=["cozy", "bad_vibe"],
        restriction_tags=["cash_only", "bad_restriction"],
    )

    normalized = normalize_place_taxonomy_payload(payload)

    assert normalized.category == ""
    assert normalized.tags == ["pet_friendly"]
    assert normalized.scenario_tags == ["with_dog"]
    assert normalized.vibe_tags == ["cozy"]
    assert normalized.restriction_tags == ["cash_only"]
```

### `tests/test_place_taxonomy_response_schema.py`

```py
from schemas.place_taxonomy_response import PlaceTaxonomyResponse


def test_place_taxonomy_response_defaults() -> None:
    response = PlaceTaxonomyResponse()

    assert response.categories == []
    assert response.tags == []
    assert response.scenario_tags == []
    assert response.vibe_tags == []
    assert response.restriction_tags == []
    assert response.user_signals == []


def test_place_taxonomy_response_accepts_full_payload() -> None:
    response = PlaceTaxonomyResponse(
        categories=["coffee", "food"],
        tags=["pet_friendly", "quiet"],
        scenario_tags=["with_dog", "coffee_now"],
        vibe_tags=["cozy", "local_favorite"],
        restriction_tags=["cash_only"],
        user_signals=["view_place", "save_place"],
    )

    assert response.categories == ["coffee", "food"]
    assert response.tags == ["pet_friendly", "quiet"]
    assert response.scenario_tags == ["with_dog", "coffee_now"]
    assert response.vibe_tags == ["cozy", "local_favorite"]
    assert response.restriction_tags == ["cash_only"]
    assert response.user_signals == ["view_place", "save_place"]
```

### `tests/test_place_taxonomy_response_service.py`

```py
from services.place_taxonomy_response_service import build_place_taxonomy_response


def test_build_place_taxonomy_response_returns_expected_structure() -> None:
    response = build_place_taxonomy_response()

    assert "coffee" in response.categories
    assert "pet_friendly" in response.tags
    assert "with_dog" in response.scenario_tags
    assert "cozy" in response.vibe_tags
    assert "cash_only" in response.restriction_tags
    assert "view_place" in response.user_signals
```

### `tests/test_place_taxonomy_router.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_read_place_taxonomy_returns_canonical_structure() -> None:
    client = TestClient(app)

    response = client.get("/place-taxonomy/")

    assert response.status_code == 200

    data = response.json()

    assert "categories" in data
    assert "tags" in data
    assert "scenario_tags" in data
    assert "vibe_tags" in data
    assert "restriction_tags" in data
    assert "user_signals" in data

    assert "coffee" in data["categories"]
    assert "pet_friendly" in data["tags"]
    assert "with_dog" in data["scenario_tags"]
    assert "cozy" in data["vibe_tags"]
    assert "cash_only" in data["restriction_tags"]
    assert "view_place" in data["user_signals"]
```

### `tests/test_place_taxonomy_service.py`

```py
from services.place_taxonomy_service import (
    is_valid_place_category,
    is_valid_place_restriction_tag,
    is_valid_place_scenario_tag,
    is_valid_place_tag,
    is_valid_place_vibe_tag,
    validate_tag_list,
)


def test_is_valid_place_category() -> None:
    assert is_valid_place_category("coffee") is True
    assert is_valid_place_category("coworking") is False


def test_is_valid_place_tag() -> None:
    assert is_valid_place_tag("pet_friendly") is True
    assert is_valid_place_tag("dog_friendly") is False


def test_is_valid_place_scenario_tag() -> None:
    assert is_valid_place_scenario_tag("with_dog") is True
    assert is_valid_place_scenario_tag("dog_walk_now") is False


def test_is_valid_place_vibe_tag() -> None:
    assert is_valid_place_vibe_tag("cozy") is True
    assert is_valid_place_vibe_tag("luxury") is False


def test_is_valid_place_restriction_tag() -> None:
    assert is_valid_place_restriction_tag("cash_only") is True
    assert is_valid_place_restriction_tag("pets_inside_only") is False


def test_validate_tag_list_filters_invalid_and_removes_duplicates() -> None:
    values = [
        "pet_friendly",
        "quiet",
        "pet_friendly",
        "invalid_tag",
        "budget",
    ]

    result = validate_tag_list(values, is_valid_place_tag)

    assert result == [
        "pet_friendly",
        "quiet",
        "budget",
    ]
```

### `tests/test_places_router_empty_result.py`

```py
from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_read_places_returns_empty_structured_response() -> None:
    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by='title',
        sort_order='asc',
    ):
        return []

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 0

    def fake_get_db():
        yield object()

    from routers import places

    original_get_places = places.get_places
    original_get_places_total = places.get_places_total
    places.get_places = fake_get_places
    places.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get("/places/")

    places.get_places = original_get_places
    places.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 20,
        "offset": 0,
    }
```

### `tests/test_places_router_filters.py`

```py
from datetime import datetime

from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_read_places_passes_all_filters_and_returns_structured_response() -> None:
    captured: dict[str, object] = {}

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by="title",
        sort_order="asc",
    ):
        captured["city_id"] = city_id
        captured["city_slug"] = city_slug
        captured["category_id"] = category_id
        captured["tag_id"] = tag_id
        captured["q"] = q
        captured["limit"] = limit
        captured["offset"] = offset
        captured["sort_by"] = sort_by
        captured["sort_order"] = sort_order
        return [
            {
                "id": 1,
                "title": "Coffee Point",
                "slug": "coffee-point",
                "city_id": 1,
                "category_id": 2,
                "short_description": "Good coffee place",
                "category": "coffee",
                "address": "Kurortny Prospekt 12",
                "lat": 54.964,
                "lng": 20.475,
                "price_level": 1,
                "dog_friendly": False,
                "family_friendly": False,
                "indoor": False,
                "outdoor": False,
                "is_active": True,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        ]

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 1

    def fake_get_db():
        yield object()

    from routers import places

    original_get_places = places.get_places
    original_get_places_total = places.get_places_total
    places.get_places = fake_get_places
    places.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/",
        params={
            "city_id": 1,
            "city_slug": "zelenogradsk",
            "category_id": 2,
            "tag_id": 3,
            "q": "coffee",
            "limit": 5,
            "offset": 10,
        },
    )

    places.get_places = original_get_places
    places.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert data["limit"] == 5
    assert data["offset"] == 10
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "coffee-point"
    assert data["items"][0]["title"] == "Coffee Point"

    assert captured["city_id"] == 1
    assert captured["city_slug"] == "zelenogradsk"
    assert captured["category_id"] == 2
    assert captured["tag_id"] == 3
    assert captured["q"] == "coffee"
    assert captured["limit"] == 5
    assert captured["offset"] == 10
    assert captured["sort_by"] == "title"
    assert captured["sort_order"] == "asc"
```

### `tests/test_places_router_pagination.py`

```py
from fastapi.testclient import TestClient

from db.dependencies import get_db
from main import app


def test_read_places_passes_limit_and_offset_and_returns_structured_response() -> None:
    captured: dict[str, int] = {}

    def fake_get_places(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
        limit=20,
        offset=0,
        sort_by='title',
        sort_order='asc',
    ):
        captured["limit"] = limit
        captured["offset"] = offset
        return []

    def fake_get_places_total(
        db,
        city_id=None,
        city_slug=None,
        category_id=None,
        tag_id=None,
        q=None,
    ):
        return 0

    def fake_get_db():
        yield object()

    from routers import places

    original_get_places = places.get_places
    original_get_places_total = places.get_places_total
    places.get_places = fake_get_places
    places.get_places_total = fake_get_places_total
    app.dependency_overrides[get_db] = fake_get_db

    client = TestClient(app)
    response = client.get(
        "/places/",
        params={
            "limit": 7,
            "offset": 14,
        },
    )

    places.get_places = original_get_places
    places.get_places_total = original_get_places_total
    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert captured["limit"] == 7
    assert captured["offset"] == 14
    assert response.json() == {
        "items": [],
        "total": 0,
        "limit": 7,
        "offset": 14,
    }
```

### `tests/test_places_router_validation.py`

```py
from fastapi.testclient import TestClient

from main import app


def test_read_places_rejects_limit_less_than_one() -> None:
    client = TestClient(app)

    response = client.get(
        "/places/",
        params={
            "limit": 0,
        },
    )

    assert response.status_code == 422


def test_read_places_rejects_negative_offset() -> None:
    client = TestClient(app)

    response = client.get(
        "/places/",
        params={
            "offset": -1,
        },
    )

    assert response.status_code == 422


def test_search_places_rejects_limit_more_than_one_hundred() -> None:
    client = TestClient(app)

    response = client.get(
        "/places/search/",
        params={
            "q": "coffee",
            "limit": 101,
        },
    )

    assert response.status_code == 422
```

### `tests/test_sorting_service.py`

```py
from schemas.sorting import SortingParams
from services.sorting_service import normalize_sorting_params


def test_normalize_sorting_params_keeps_values() -> None:
    params = SortingParams(
        sort_by="created_at",
        sort_order="desc",
    )

    normalized = normalize_sorting_params(params)

    assert normalized.sort_by == "created_at"
    assert normalized.sort_order == "desc"


def test_sorting_params_default_values() -> None:
    params = SortingParams()

    normalized = normalize_sorting_params(params)

    assert normalized.sort_by == "title"
    assert normalized.sort_order == "asc"
```

