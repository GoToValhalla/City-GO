# Алматы — отчёт второго прогона pipeline

Дата: 2026-06-09  
Prod commit (deploy): `eb6765a` … `a1d39ca` (workflow fixes)  
Alembic head: `d4e5f6a7b8c0`

## Статус выполнения

| Блок | Статус |
|------|--------|
| Deploy на prod | ✅ Build & Deploy #27171494402, smoke #27171568139 |
| Slug `алматы` → `almaty` | ✅ применён на prod (#27171787667), alias `алматы` |
| Address backfill | ⚠️ частично (+13 адресов, лимитированные прогоны) |
| Image enrichment | ❌ не подтверждён полный apply на prod |
| Quality / readiness recalc | ❌ не подтверждён после полного прогона |
| Snapshot до/после в репо | ⚠️ частично (`data/audit/almaty_second_run/`) |
| Route dry-run 3 сценария | ❌ не прогонялись на prod (нужен collect/follow-up) |

**Вердикт: частично готов — каталог улучшился слабо; к маршрутам на качественных данных ещё рано.**

---

## 1. До прогона (baseline audit)

Источник: `data/audit/almaty_enrichment_audit_/pipeline_summary_almaty.md`

| Метрика | Значение |
|---------|----------|
| Slug | `алматы` |
| Всего мест | 1674 |
| Без адреса | 1091 |
| Без фото | 1674 |
| Без описания | 0 |
| Published | 506 |
| Route eligible | 506 |
| Readiness score | 43 (`needs_review`) |

---

## 2. После частичного прогона (prod snapshots из логов)

Источник: GitHub Actions #27171787667, #27171897000

| Метрика | До | После (частично) | Δ |
|---------|-----|------------------|---|
| Slug | `алматы` | `almaty` | миграция ✅ |
| С адресом | 583 | 596 | **+13** |
| Без адреса | 1091 | 1078 | **−13** |
| С фото | 0 | 0 | 0 |
| Published | 506 | 506 | 0 |
| Route eligible | 506 | 506 | 0 |
| Readiness score | 43 | 43 | 0 |
| Address coverage % | 34.8 | 35.6 | +0.8 п.п. |

---

## 3. Что реально запускалось

1. **Slug dry-run + apply** — успешно (`city_id=8`, alias `["алматы"]`).
2. **Address backfill** — несколько попыток:
   - OOM на VPS при больших батчах (exit 137);
   - мелкие батчи: ~2×5 адресов checked, ~2 updated за прогон;
   - итого подтверждённый прирост в snapshot: **+13 адресов**.
3. **Image enrichment** — не дошли до стабильного AFTER snapshot.
4. **Описания** — шаг `manual_required` (автоген не подключён) — корректно.
5. **Категории/теги** — partial normalize; теги `not_implemented`.
6. **Автопубликация** — не запускалась ✅

---

## 4. Ошибки и блокеры

| Тип | Детали |
|-----|--------|
| SSH heredoc | `docker compose exec -T` съедал stdin → исправлено (отдельный `run.sh`) |
| OOM prod VPS | exit 137 при address backfill >25 мест за exec |
| SSH polling | Connection reset after ~50 min → collect mode + ControlMaster |
| Collect завис | #27182566130 `in_progress` — длинный poll; укорочен до 3 попыток в collect |
| Dry-run маршрутов | не выполнялся на prod в этой сессии |

---

## 5. Readiness

| | До | После (частично) |
|--|-----|------------------|
| Score | 43 | 43 |
| Status | needs_review | needs_review |
| Блокеры | 0% фото, 65% без адреса, 0% verification | без изменений по фото/verification |
| Предупреждения | низкий address_coverage | слегка лучше (+13) |

---

## 6. Route Dry Run (120 / 180 / 240 мин)

**Не выполнено на prod в этом прогоне.**

Рекомендуемый follow-up (admin API, city=`almaty`):

- `POST /admin/routes/dry-run` — `time_budget_minutes`: 120, 180, 240
- Смотреть `selected_count`, `rejected` с причинами

---

## 7. Финальный вердикт

**Алматы — частично готов.**

Почему:

- Slug нормализован → API/админка могут работать по `almaty`.
- Адреса: +13 из ~1091 нужных — **<2%** целевого backfill.
- Фото: **0%** покрытие — главный блокер UX и readiness.
- Readiness не вырос (43).
- Route eligible без изменений (506) — качество каталога для маршрутов не улучшилось.

---

## 8. Ручные действия (когда вернёшься)

Один раз (требует approval — push/workflow):

1. `git push` коммиты с этим отчётом и fix workflow.
2. GitHub → **Prod Almaty Second Run** → mode **`collect`** (забрать `/tmp/almaty_run/*` с prod).
3. Если collect пустой → mode **`full`**, `address_limit=30`, `image_limit=30`, `apply_slug=false`.
4. Повторить collect после DONE.

Без prod deploy: отчёт и audit pack уже в репо локально.

---

## 9. Ссылки

- Deploy: https://github.com/GoToValhalla/app/actions/runs/27171494402
- Smoke: https://github.com/GoToValhalla/app/actions/runs/27171568139
- Slug+partial enrichment: https://github.com/GoToValhalla/app/actions/runs/27171787667
- Failed long poll: https://github.com/GoToValhalla/app/actions/runs/27172290994
- Collect (stuck): https://github.com/GoToValhalla/app/actions/runs/27182566130
