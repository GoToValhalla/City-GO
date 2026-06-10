# CITY GO — FULL PROJECT ARCHITECTURE

> Архивировано 2026-06-06 после ревизии документации.
>
> Причина: документ описывал устаревшее дерево `app/api/...`, которое не соответствует текущему репозиторию.
>
> Актуальные источники:
> - `docs/architecture/application_architecture_ru.md`
> - `docs/architecture/backend_file_map.md`
> - `docs/master_technical_spec.md`

Историческая заметка:

Ранее планировался единый документ как source of truth по структуре `app/`. Фактический backend живёт в корне репозитория:

- `main.py`
- `routers/`
- `services/`
- `schemas/`
- `models/`
- `db/`
- `core/`
- `tests/`
- `frontend/`
- `telegram_bot/`

Не использовать этот документ для навигации по текущему коду.
