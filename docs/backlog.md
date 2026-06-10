# City Go — Product Backlog

Живой список задач. Обновляется по мере появления новых требований.

Статусы: `✅ выполнено` | `🚧 в работе` | `📋 готово к взятию` | `💡 идея/планирование`

---

## P1 — Высокий приоритет (выполнено в июне 2026)

| ID | Задача | Статус |
|----|--------|--------|
| P1-1 | **Infinite Scroll / «Показать ещё»** — подгрузка всех мест (было 20 из 203). `usePlacesPagination`, `PlacesLoadMoreTrigger`, PAGE_SIZE=50 | ✅ |
| P1-2 | **Аудит всех рейтингов и метрик** — `confidence`, `existence_confidence_*`, `trust_score` (отсутствует), `quality_score`, `scoring_breakdown`, `image_confidence`, publication flags. Результат: `docs/audits/metrics_audit.md` | ✅ |
| P1-3 | **Статистика покрытия данных** — расширить `PlaceCoverageReport`: `with_address`, `without_address`, `with_photo`, `without_photo`, `verified`, `route_eligible`, `publication_status_breakdown`. Эндпоинт `/place-coverage/{city_slug}` | ✅ |
| P1-4 | **Проверка Address Backfill** — статус pipeline, интеграция в docker-compose. Уже интегрирован: сервис `address-backfill` в `docker-compose.yml`. Документация: `docs/architecture/deploy_pipeline.md` | ✅ |
| P1-5 | **Проверка Image Enrichment** — статус pipeline. Legacy JSON pipeline, не в docker-compose. Задокументировано как gap (→ P2+) | ✅ |
| P1-6 | **Автоматический запуск миграций после деплоя** — `alembic upgrade head` в CI + явная проверка в deploy-скрипте с fail-fast и логами | ✅ |

---

## P2 — Среднесрочные задачи (следующий цикл)

| ID | Задача | Приоритет | Статус |
|----|--------|-----------|--------|
| P2-1 | **Полноценная admin-панель** (`/admin`) — login, dashboard, places, images, verifications, import-jobs, coverage, audit-log | ВЫСОКИЙ | ✅ |
| P2-1b | **Place Enrichment GitHub workflow** — batch storage active/archive, export --git-artifact, import preview/apply CLI+admin, ChatGPT contract | ВЫСОКИЙ | ✅ |
| P2-2 | **Image enrichment → DB integration** — перевести image pipeline с JSON-файлов на прямую запись в БД | СРЕДНИЙ | 📋 |
| P2-3 | **Address recovery flow** — `run_address_recovery_flow.py`: coverage → dry-run → review → apply; cron после import/seed | СРЕДНИЙ | ✅ |
| P2-3b | **Address backfill cron на production** — автоматический `--apply` на сервере только после review/summary | СРЕДНИЙ | 📋 |
| P2-4 | **Leaflet map** — минимальная карта с пинами мест в `/places` или в карточке маршрута | СРЕДНИЙ | 📋 |
| P2-5 | **Bot UX** — кнопка extend_route, unified nearby, persistent FSM, city в `/context` | СРЕДНИЙ | 📋 |
| P2-6 | **Existence verification → route pipeline** — места с `existence_confidence_score < 30` должны иметь `is_route_eligible=false` (сейчас gap) | ВЫСОКИЙ | 📋 |
| P2-7 | **Two verify paths converge** — унифицировать `apply_place_verification` и `admin_service.verify_place` (сейчас расходятся по семантике score) | СРЕДНИЙ | 📋 |
| P2-8 | **`scoring_breakdown` cleanup** — удалить мёртвые ключи `distance`, `popularity`, `novelty` из breakdown, которые не участвуют в `combine_scores` | НИЗКИЙ | 📋 |
| P2-9 | **`match_confidence` (offline JSON) deprecation** — `shared/demo/categoryLabels` re-export временный; убрать offline JSON pipeline из фронтенда | НИЗКИЙ | 📋 |

---

### P2-10. PRODUCTION ADMIN AUTH HARDENING [ВЫСОКИЙ ПРИОРИТЕТ] 📋

**Причина:** Текущая реализация (`adminCredentials.ts`) допустима только для внутренней разработки:
- hardcoded credentials в JS bundle
- ADMIN_API_TOKEN виден в frontend bundle
- localStorage session без срока жизни
- единый токен для всех пользователей

**Backend (новое):**
- `POST /admin/auth/login` — bcrypt-хеширование пароля, выдача сессии
- `POST /admin/auth/logout` — инвалидация сессии
- `GET /admin/auth/me` — проверка активной сессии
- HttpOnly cookie session или короткоживущий access token + refresh token
- Middleware проверки admin session
- Audit log входов/выходов
- Защита от brute force (rate limiting, lockout)
- Logout invalidates session server-side

**Frontend (изменения):**
- Убрать `adminCredentials.ts` (и `ADMIN_API_TOKEN` из bundle)
- Убрать hardcoded credentials
- Login page работает через `POST /admin/auth/login`
- Session восстанавливается через `GET /admin/auth/me`
- Автоматический logout при истечении сессии
- Admin-страницы остаются на `/admin`

**Ограничения:** без JWT/OAuth/RBAC/регистрации пользователей.

---

### P2-11. DATA QUALITY UI [ВЫСОКИЙ ПРИОРИТЕТ] 📋

**Причина:** Служебная информация о качестве данных (confidence, verification status, coordinates, источник) нужна и полезна, но перегружает обычного пользователя.

**Что НЕ удалять:**
- confidence, verification_status, image_status
- route eligibility, quality metrics, coordinates
- publication status, источник данных

**Изменить отображение:**

По умолчанию — компактный пользовательский вид (без технических деталей).

Кнопка `[Показать техническую информацию]` раскрывает:
- полный блок качества данных
- все метрики и статусы
- координаты
- источник данных
- история верификации

**Результат:** обычный пользователь не перегружен; продвинутый получает полный доступ к данным.

---

### P2-12. ROUTE QUALITY LOGIC REWORK [ВЫСОКИЙ ПРИОРИТЕТ] 📋

**Причина:** Оценки маршрутов (`quality_score`, confidence, проценты) выглядят случайными и недоверенными.

**Задача — для каждого поля провести аудит:**
1. Кто считает, по какой формуле
2. Где используется, где отображается
3. Нужен ли вообще

**Поля в scope:** `quality_score`, `confidence`, `existence_confidence_score`, `image_confidence`, `verification_status`, `route eligibility`, `publication status`.

**После аудита:**
- Удалить мёртвые рейтинги
- Убрать декоративные оценки
- Оставить только реальные метрики с объяснимой формулой
- Сделать человекочитаемые объяснения качества маршрута

**Запрет:** никаких заглушек и фиктивных процентов. Любая оценка должна иметь понятную формулу и источник данных.

> Примечание: базовый аудит полей выполнен в P1-2 → `docs/audits/metrics_audit.md`. Задача P2-12 — рефакторинг и cleanup по итогам аудита.

---

### P2-13. ZERO PLACEHOLDER POLICY [ВЫСОКИЙ ПРИОРИТЕТ] 📋

**Причина:** В проекте неоднократно обнаруживались заглушки, фиктивные значения и временные решения без документирования.

**Новое правило проекта (enforcement):**

Запрещено:
- hardcoded рейтинги и случайные проценты
- fake confidence и временные значения без явной пометки `// TEMPORARY`
- demo-данные в production flow
- заглушки без задачи на удаление в backlog

Если данных нет — показывать честно:
- «Нет данных»
- «Требует проверки»
- «Информация уточняется»

Любая допустимая заглушка:
- согласовывается отдельно
- документируется в `docs/`
- имеет задачу на удаление в этом backlog

**Результат:** в системе не остаётся скрытых фейковых данных.

**Текущие известные заглушки → подлежат устранению:**
- `adminCredentials.ts` — временные hardcoded credentials (→ P2-10)
- `shared/demo/categoryLabels.ts` — re-export для backward compat (→ P2-9)
- `scoring_breakdown` мёртвые ключи (→ P2-8)

---

## P3 — Низкий приоритет / будущие функции

| ID | Задача |
|----|--------|
| P3-1 | Route constructor (пошаговый интерфейс) |
| P3-2 | Active route session (навигация в реальном времени) |
| P3-3 | Smart detours / Route recovery |
| P3-4 | Recommendations tuning (ML-эксперименты) |
| P3-5 | Admin routes/route-feedback страницы |
| P3-6 | Multi-city support (сейчас только Зеленоградск) |
| P3-7 | User accounts / персонализация |

---

*Последнее обновление: 2026-06-07*
