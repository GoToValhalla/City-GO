# Техническое задание

> Архивировано 2026-06-06 после ревизии документации.
>
> Причина: документ дублировал и частично устаревал относительно `docs/master_technical_spec.md` и `docs/implementation_status_and_next_steps.md`.
>
> Актуальные источники:
> - `docs/README.md`
> - `docs/master_technical_spec.md`
> - `docs/implementation_status_and_next_steps.md`

Краткая сводка по backend. **Актуальные статусы модулей и API** — в [`../master_technical_spec.md`](../master_technical_spec.md); навигация по `docs/` — в [`../README.md`](../README.md).

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

## 2. Текущий стек
- Python 3.11
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0
- Alembic
- Uvicorn

Документ сохранён для истории. Актуальная версия заменена master ТЗ.
