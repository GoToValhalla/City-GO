# Документация City Go

Карта актуальной документации проекта. После ревизии 2026-06-06 source of truth разделён так:

## 1. Читать в первую очередь

| Документ | Назначение |
|---|---|
| [`master_technical_spec.md`](master_technical_spec.md) | Главный продуктово-технический документ: что есть, как устроено, что запланировано. |
| [`implementation_status_and_next_steps.md`](implementation_status_and_next_steps.md) | Короткий актуальный статус: реализовано / частично / не реализовано / ближайшие шаги. |
| [`route_generation_status_and_roadmap.md`](route_generation_status_and_roadmap.md) | Рабочая карта маршрутов: три route-слоя, текущая реализация, планы по Active Route Session и карте. |
| [`architecture/application_architecture_ru.md`](architecture/application_architecture_ru.md) | Архитектура приложения и слои backend/frontend/Telegram. |
| [`architecture/backend_file_map.md`](architecture/backend_file_map.md) | Рабочий реестр ключевых файлов backend и route pipeline. |
| [`architecture/frontend_design_system.md`](architecture/frontend_design_system.md) | Design System Foundation для Web App и Telegram App: токены, UI-компоненты и план миграции экранов. |

## 2. Операционные документы

| Документ | Назначение |
|---|---|
| [`admin_guide.md`](admin_guide.md) | Работа с отдельной админкой, публикация/снятие мест, фото, маршруты, аудит и логика добавления города для DevOps. |
| [`admin-city-operations.md`](admin-city-operations.md) | City Workspace, backend-driven taxonomy and safe admin operations. |
| [`testing-and-allure.md`](testing-and-allure.md) | Pytest/Vitest, Allure artifacts, CI summaries and Telegram notifications. |
| [`release_checklist.md`](release_checklist.md) | Release gates: tests, migrations, smoke, coverage, UI/Telegram checks. |
| [`backup_restore.md`](backup_restore.md) | Backup/restore процесс для PostgreSQL. |
| [`production_data_refresh.md`](production_data_refresh.md) | Безопасный refresh/import production data. |
| [`city_expansion_guide.md`](city_expansion_guide.md) | Расширение на новые города. |
| [`architecture/backend_quality_gate.md`](architecture/backend_quality_gate.md) | Custom backend quality gate. |

## 3. Route / recommendation документы

| Документ | Назначение |
|---|---|
| [`architecture/route_pipeline_observability.md`](architecture/route_pipeline_observability.md) | Trace/logging/observability route pipeline. |
| [`architecture/route_scoring_explanation.md`](architecture/route_scoring_explanation.md) | Scoring и explanation маршрутов. |
| [`architecture/route_assembly_quality.md`](architecture/route_assembly_quality.md) | Качество сборки маршрутов. |
| [`architecture/route_correction_engine.md`](architecture/route_correction_engine.md) | Correction engine: remove/shorten/rebuild/extend. |
| [`architecture/place_route_ui_data_contract.md`](architecture/place_route_ui_data_contract.md) | Контракт DB-backed карточек мест и route points: фото, `time_of_day`, visibility и runtime notes. |
| [`random-route-editor.md`](random-route-editor.md) | MVP Random Route + Route Draft Editor: API, fallback rules, category modes, frontend flow. |
| [`itinerary/`](itinerary/) | Legacy itinerary-документы. Использовать как историческую матрицу и тестовую базу, не как главный route source of truth. |

## 4. Reference

| Документ | Назначение |
|---|---|
| [`reference/city_timezone_policy.md`](reference/city_timezone_policy.md) | Политика таймзон городов. |
| [`reference/route_modes_policy.md`](reference/route_modes_policy.md) | Политика route modes. |
| [`commenting_policy.md`](commenting_policy.md) | Правила комментариев в коде. |
| [`cursor_master_prompt_strict.md`](cursor_master_prompt_strict.md) | Правила для агента в Cursor. |

## 5. Архив

Устаревшие и дублирующие документы перенесены в [`archive/`](archive/):

- `archive/technical_spec.md` — старое краткое ТЗ по backend; заменено `master_technical_spec.md`.
- `archive/project_status.md` — старый статус; заменён `implementation_status_and_next_steps.md`.
- `archive/project_structure.md` — устаревшая архитектура с неактуальным деревом `app/`.

## 6. Важное разделение route-слоёв

В проекте есть три разных route-слоя. Их нельзя смешивать:

1. **Editorial routes** — готовые маршруты из БД: `GET /routes/...`.
2. **Legacy itinerary** — старый контур генерации: `POST /routes/generate`, `POST /routes/replan`.
3. **Product route layer** — основной текущий слой для продукта: `POST /v1/user-routes/build`, `POST /v1/user-routes/correct`, поверх recommendation pipeline `POST /v1/recommendations/route`.

Для новой разработки по маршрутам приоритет: `user-routes` + recommendation pipeline. Legacy itinerary не удалять, но не развивать как главный SoT без отдельного решения.