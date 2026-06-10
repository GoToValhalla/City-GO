# 04 — Telegram Bot Redesign Audit

Дата актуализации: 2026-06-10.

## 1. Executive Summary

Telegram-бот остаётся lite/conversational слоем City Go. Он не должен копировать web-каталог и админку. Его задача — быстрые сценарии:

- построить маршрут;
- стартовать от геолокации;
- показать места рядом;
- показать, что открыто сейчас;
- найти место;
- сменить город;
- сохранить контекст пользователя между сессиями;
- быстро скорректировать уже собранный маршрут.

В этом этапе бот подтянут к новому route quality layer, user geolocation flow и route correction UX.

## 2. Текущая архитектура

| Aspect | Value |
|---|---|
| Framework | aiogram 3.15 |
| Transport | long polling |
| Parse mode | HTML global |
| Context store | memory + DB `telegram_user_contexts` |
| Route build API | `POST /v1/user-routes/build` |
| Route correction API | `POST /v1/user-routes/correct` |

Entry point:

```text
telegram_bot_main.py
```

Основные файлы:

```text
telegram_bot/keyboards/main_menu.py
telegram_bot/keyboards/route_actions.py
telegram_bot/handlers/health.py
telegram_bot/handlers/route.py
telegram_bot/handlers/location.py
telegram_bot/handlers/menu.py
telegram_bot/handlers/route_correction.py
telegram_bot/services/recommendation_client.py
telegram_bot/services/route_formatter.py
telegram_bot/services/route_point_formatter.py
telegram_bot/services/route_start.py
telegram_bot/services/context_store/
tests/test_telegram_bot_route_ux.py
```

## 3. Что обновлено

### Main menu

`telegram_bot/keyboards/main_menu.py` теперь показывает:

```text
🗺 Построить маршрут
📍 Места
📡 Отправить геолокацию
☕ Открыто сейчас
🔎 Найти место
⚙️ Сменить город
ℹ️ Что умеет бот
```

Добавлена кнопка `request_location=True`, чтобы пользователь мог отправить геолокацию одним нажатием.

### Help handler

`telegram_bot/handlers/health.py` теперь дополнительно обрабатывает:

```text
/help
ℹ️ Что умеет бот
```

Ответ кратко объясняет быстрые сценарии бота.

### Route build payload

`telegram_bot/services/recommendation_client.py` теперь отправляет в backend:

```json
{
  "lat": 0,
  "lng": 0,
  "start_source": "current_location|city_center|address",
  "start": {
    "type": "current_location|city_center|address",
    "lat": 0,
    "lng": 0
  }
}
```

Это синхронизирует Telegram-бота с web route geolocation UX.

### Route handler

`telegram_bot/handlers/route.py` теперь:

- явно мапит source старта в backend `start_source`;
- логирует `quality_status`, `route_id`, count points;
- даёт пользователю recovery-действия при ошибке;
- не показывает технический backend URL пользователю в обычной ошибке;
- после успешной сборки показывает route action keyboard.

### Route action keyboard

Новый файл:

```text
telegram_bot/keyboards/route_actions.py
```

Кнопки после собранного маршрута:

```text
Добавить точку
Маршрут короче
Перестроить отсюда
Убрать первую точку
📡 Отправить геолокацию
🗺 Построить маршрут
⚙️ Сменить город
```

### Route correction

`telegram_bot/handlers/route_correction.py` теперь обрабатывает:

```text
Добавить точку
Маршрут длиннее
```

Обе команды отправляют action:

```text
extend_route
```

### Route formatter

`telegram_bot/services/route_formatter.py` теперь использует:

- `quality_status`;
- `quality_score`;
- warnings;
- empty/failed route fallback.

Статусы:

```text
good -> Маршрут готов
acceptable -> Маршрут готов
weak -> Маршрут собран с нюансами
failed -> Маршрут не собрался
```

### Route point formatter

`telegram_bot/services/route_point_formatter.py` теперь показывает точку как компактную карточку:

```text
1. Название
   категория · visit minutes
   адрес/координаты
   ссылка на карты
   время
   описание
   warning
```

## 4. User flows

| Flow | Current behavior |
|---|---|
| `/start` | выбор города / возврат в меню |
| `/help` | краткая справка по возможностям бота |
| `🗺 Построить маршрут` | строит маршрут по выбранному городу и последнему старту |
| `📡 Отправить геолокацию` | сохраняет lat/lng и показывает nearby |
| маршрут после геолокации | стартует от `current_location` |
| маршрут без геолокации | fallback на центр выбранного города |
| маршрут с weak status | показывается с предупреждениями, а не как silent fail |
| failed route | показывает понятную причину и recovery options |
| `Добавить точку` | вызывает `extend_route` |
| `Маршрут короче` | вызывает `shorten_route` |
| `Перестроить отсюда` | вызывает `rebuild_from_here` |
| `Убрать первую точку` | вызывает `remove_place` |

## 5. Tests

Добавлен файл:

```text
tests/test_telegram_bot_route_ux.py
```

Покрытие:

- `test_main_keyboard_exposes_location_new`;
- `test_route_actions_keyboard_exposes_extend_route_new`;
- `test_route_formatter_handles_weak_status_new`;
- `test_route_formatter_handles_failed_empty_route_new`.

Запуск:

```bash
python -m pytest tests/test_telegram_bot_route_ux.py -q
```

## 6. Что не должно быть в Telegram

Не переносить в Telegram:

- полную админку;
- массовые операции;
- сложный каталог;
- тяжелые фильтры;
- бизнес-кабинет;
- собственную карту внутри сообщения.

Telegram должен вести к web/mini app для тяжёлых сценариев.

## 7. Остаточные проблемы

P0/P1:

1. Нужно проверить, что все reply texts из клавиатуры имеют handlers.
2. Nearby rendering всё ещё отличается между raw location handler и place menu.
3. FSM storage всё ещё memory/default, не Redis/DB-backed.
4. Нет WebApp route map button.
5. Нет handler-level integration tests с реальным aiogram Dispatcher.
6. Нужно добавить тест payload `start_source` для `RecommendationApiClient` через mock httpx.

## 8. Следующий implementation slice

Следующий безопасный шаг:

```text
TG-NEXT-2: унифицировать nearby rendering и добавить WebApp/open route links.
```

Scope:

- `telegram_bot/handlers/location.py`;
- `telegram_bot/handlers/place_menu/nearby.py`;
- общий renderer карточек мест;
- route web link / mini app link config;
- tests.

Не трогать backend route engine в этом slice.
